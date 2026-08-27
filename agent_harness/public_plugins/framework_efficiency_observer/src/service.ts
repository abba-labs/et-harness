import { appendFile, mkdir, readFile } from 'node:fs/promises'
import { homedir } from 'node:os'
import { join } from 'node:path'
import { Service, type Context } from '@deepseek-ai/cordis'
import '@agent-harness/governance-core'
import type { FrameworkMetricEvent } from '@agent-harness/governance-core'
import { analyzeFrameworkMetrics } from './analyzer.js'
import { analyzeHarnessSessionEvents } from './session-analyzer.js'
import type {
  FrameworkEfficiencyQuery,
  FrameworkEfficiencyReport,
  FrameworkObserverRuntimeStats,
} from './contracts.js'

const numberFromEnv = (name: string, fallback: number, min: number, max: number): number => {
  const parsed = Number.parseInt(process.env[name] ?? '', 10)
  if (!Number.isFinite(parsed)) return fallback
  return Math.max(min, Math.min(max, parsed))
}

const storageRoot = (): string =>
  process.env.AGENT_HARNESS_METRICS_ROOT ?? join(homedir(), '.agent-harness', 'metrics')

const recordOf = (value: unknown): Record<string, unknown> | undefined =>
  typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : undefined

interface DynamicSessionStore {
  list(): readonly unknown[]
}

export class FrameworkEfficiencyObserverService extends Service {
  private readonly runtimeContext: Context
  private readonly buffer: FrameworkMetricEvent[] = []
  private readonly maxBuffer = numberFromEnv('AGENT_HARNESS_METRICS_BUFFER', 2048, 64, 65536)
  private readonly flushIntervalMs = numberFromEnv('AGENT_HARNESS_METRICS_FLUSH_MS', 500, 50, 60000)
  private readonly file = join(storageRoot(), 'framework-events.jsonl')
  private flushTimer?: NodeJS.Timeout
  private flushPromise?: Promise<void>
  private received = 0
  private dropped = 0
  private writeErrors = 0

  constructor(ctx: Context) {
    super(ctx, 'frameworkEfficiencyObserver')
    this.runtimeContext = ctx

    // Low-frequency framework metrics only. Agent/session logs are analyzed
    // offline so token-level assistant chunks add zero runtime callback cost.
    ctx.on('framework/metric', event => {
      this.capture(event)
    })

    ctx.effect(() => () => {
      if (this.flushTimer) clearTimeout(this.flushTimer)
      this.flushTimer = undefined
      void this.flush()
    })
  }

  getRuntimeStats(): FrameworkObserverRuntimeStats {
    return {
      storageFile: this.file,
      buffered: this.buffer.length,
      received: this.received,
      dropped: this.dropped,
      writeErrors: this.writeErrors,
    }
  }

  async flush(): Promise<void> {
    if (this.flushPromise) return this.flushPromise
    if (this.buffer.length === 0) return

    const batch = this.buffer.splice(0, this.buffer.length)
    this.flushPromise = (async () => {
      try {
        await mkdir(storageRoot(), { recursive: true })
        const content = `${batch.map(event => JSON.stringify(event)).join('\n')}\n`
        await appendFile(this.file, content, 'utf-8')
      } catch {
        this.writeErrors += 1
        this.dropped += batch.length
      } finally {
        this.flushPromise = undefined
        if (this.buffer.length > 0) this.scheduleFlush()
      }
    })()
    return this.flushPromise
  }

  async analyze(query: FrameworkEfficiencyQuery = {}): Promise<FrameworkEfficiencyReport> {
    await this.flush()
    return analyzeFrameworkMetrics(await this.readPersistedEvents(), query)
  }

  analyzeSessionEvents(sessionId: string, events: readonly unknown[]): FrameworkEfficiencyReport {
    return analyzeHarnessSessionEvents(sessionId, events)
  }

  analyzeLiveSession(sessionId: string): FrameworkEfficiencyReport {
    const sessions = (this.runtimeContext as unknown as {
      sessions?: DynamicSessionStore
    }).sessions
    if (!sessions) throw new Error('Harness Session Store 未加载；请提供持久化 Session Events 离线分析')

    const session = sessions.list().find(item => {
      const record = recordOf(item)
      const header = recordOf(record?.header)
      return header?.id === sessionId || record?.id === sessionId
    })
    if (!session) throw new Error(`Live Session 不存在: ${sessionId}`)
    const record = recordOf(session)
    const events = Array.isArray(record?.events) ? record.events : []
    return analyzeHarnessSessionEvents(sessionId, events)
  }

  private capture(event: FrameworkMetricEvent): void {
    this.received += 1
    if (this.buffer.length >= this.maxBuffer) {
      this.dropped += 1
      return
    }
    this.buffer.push(event)
    this.scheduleFlush()
  }

  private scheduleFlush(): void {
    if (this.flushTimer || this.flushPromise) return
    this.flushTimer = setTimeout(() => {
      this.flushTimer = undefined
      void this.flush()
    }, this.flushIntervalMs)
    this.flushTimer.unref?.()
  }

  private async readPersistedEvents(): Promise<FrameworkMetricEvent[]> {
    let content: string
    try {
      content = await readFile(this.file, 'utf-8')
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') return []
      return []
    }

    const events: FrameworkMetricEvent[] = []
    for (const line of content.split('\n')) {
      if (!line.trim()) continue
      try {
        const parsed = JSON.parse(line) as FrameworkMetricEvent
        if (parsed?.standard === 'framework-metric-v0.1') events.push(parsed)
      } catch {
        // Bad metric lines are ignored; observability never blocks execution.
      }
    }
    return events
  }
}

declare module '@deepseek-ai/cordis' {
  interface Context {
    frameworkEfficiencyObserver: FrameworkEfficiencyObserverService
  }
}

export default FrameworkEfficiencyObserverService
