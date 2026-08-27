import type { Context } from '@deepseek-ai/cordis'

export type FrameworkMetricComponent =
  | 'project'
  | 'context'
  | 'architecture'
  | 'rule'
  | 'knowledge'
  | 'gate'
  | 'evidence'
  | 'state'
  | 'experience'
  | 'tool'
  | 'runtime'

export type FrameworkMetricOutcome = 'OK' | 'MISS' | 'PASS' | 'FAIL' | 'ERROR'

export interface FrameworkMetricEvent {
  readonly standard: 'framework-metric-v0.1'
  readonly at: string
  readonly component: FrameworkMetricComponent
  readonly operation: string
  readonly projectId?: string
  readonly taskId?: string
  readonly sessionId?: string
  readonly durationMs?: number
  readonly outcome?: FrameworkMetricOutcome
  readonly values?: Readonly<Record<string, number>>
  readonly tags?: Readonly<Record<string, string | number | boolean>>
}

export type FrameworkMetricInput = Omit<FrameworkMetricEvent, 'standard' | 'at'>

let activeObservers = 0

/**
 * Activate framework metric emission for one optional observer.
 * Returns an idempotent disposer. The execution plane never calls this API.
 */
export function activateFrameworkMetrics(): () => void {
  activeObservers += 1
  let active = true
  return () => {
    if (!active) return
    active = false
    activeObservers = Math.max(0, activeObservers - 1)
  }
}

export function frameworkMetricsActive(): boolean {
  return activeObservers > 0
}

/**
 * Best-effort, fail-open metric emission.
 *
 * With no observer installed this is an immediate no-op. If a listener throws,
 * the execution plane continues unchanged.
 */
export function emitFrameworkMetric(ctx: Context, input: FrameworkMetricInput): void {
  if (!frameworkMetricsActive()) return
  const event: FrameworkMetricEvent = {
    standard: 'framework-metric-v0.1',
    at: new Date().toISOString(),
    ...input,
  }
  try {
    ctx.emit('framework/metric', event)
  } catch {
    // Observability is strictly fail-open.
  }
}

export function observeFrameworkOperation<T>(
  ctx: Context,
  input: Omit<FrameworkMetricInput, 'durationMs' | 'outcome' | 'values'>,
  action: () => T,
  summarize?: (result: T) => {
    readonly outcome?: FrameworkMetricOutcome
    readonly values?: Readonly<Record<string, number>>
  },
): T {
  if (!frameworkMetricsActive()) return action()

  const started = Date.now()
  try {
    const result = action()
    const summary = summarize?.(result)
    emitFrameworkMetric(ctx, {
      ...input,
      durationMs: Math.max(0, Date.now() - started),
      outcome: summary?.outcome ?? 'OK',
      ...(summary?.values ? { values: summary.values } : {}),
    })
    return result
  } catch (error) {
    emitFrameworkMetric(ctx, {
      ...input,
      durationMs: Math.max(0, Date.now() - started),
      outcome: 'ERROR',
    })
    throw error
  }
}
