import type { FrameworkMetricEvent } from '@agent-harness/governance-core'
import { analyzeFrameworkMetrics } from './analyzer.js'
import type { FrameworkEfficiencyReport } from './contracts.js'

const recordOf = (value: unknown): Record<string, unknown> | undefined =>
  typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : undefined

const finiteNumber = (value: unknown): number | undefined =>
  typeof value === 'number' && Number.isFinite(value) ? value : undefined

const stringValue = (value: unknown): string | undefined =>
  typeof value === 'string' && value.length > 0 ? value : undefined

interface StartedTool {
  readonly at: number
  readonly name?: string
}

export function extractHarnessSessionMetrics(
  sessionId: string,
  events: readonly unknown[],
): FrameworkMetricEvent[] {
  const result: FrameworkMetricEvent[] = []
  const turnStarted = new Map<number, number>()
  const stepStarted = new Map<string, number>()
  const toolStarted = new Map<string, StartedTool>()
  const usageSeen = new Set<string>()

  const push = (event: Omit<FrameworkMetricEvent, 'standard' | 'sessionId'>): void => {
    result.push({
      standard: 'framework-metric-v0.1',
      sessionId,
      ...event,
    })
  }

  for (const rawEvent of events) {
    const event = recordOf(rawEvent)
    const type = stringValue(event?.type)
    const data = recordOf(event?.data)
    if (!type || !data) continue
    const time = finiteNumber(event?.time) ?? 0
    const at = new Date(Math.max(0, time)).toISOString()
    const turn = finiteNumber(data.turn)
    const step = finiteNumber(data.step)
    const stepKey = turn !== undefined && step !== undefined ? `${turn}:${step}` : undefined

    if (type === 'turn/start' && turn !== undefined) {
      turnStarted.set(turn, time)
      continue
    }
    if (type === 'turn/end' && turn !== undefined) {
      const started = turnStarted.get(turn)
      turnStarted.delete(turn)
      const reason = recordOf(data.reason)
      const reasonKind = stringValue(reason?.kind)
      push({
        at,
        component: 'runtime',
        operation: 'agentTurn',
        ...(started !== undefined ? { durationMs: Math.max(0, time - started) } : {}),
        outcome: reasonKind === 'error' || reasonKind === 'aborted' || reasonKind === 'interrupted' ? 'FAIL' : 'OK',
        tags: { turn, ...(reasonKind ? { endReason: reasonKind } : {}) },
      })
      continue
    }
    if (type === 'step/start' && stepKey) {
      stepStarted.set(stepKey, time)
      continue
    }
    if (type === 'step/end' && stepKey) {
      const started = stepStarted.get(stepKey)
      stepStarted.delete(stepKey)
      push({
        at,
        component: 'runtime',
        operation: 'agentStep',
        ...(started !== undefined ? { durationMs: Math.max(0, time - started) } : {}),
        outcome: 'OK',
        tags: { turn: turn!, step: step! },
      })
      continue
    }
    if (type === 'assistant/chunk' && stepKey) {
      const chunk = recordOf(data.chunk)
      if (chunk?.type === 'usage') {
        const usage = recordOf(chunk.usage)
        if (usage) {
          pushUsage(push, at, turn!, step!, usage)
          usageSeen.add(stepKey)
        }
      }
      continue
    }
    if (type === 'assistant/message' && stepKey) {
      const usage = recordOf(data.usage)
      if (usage && !usageSeen.has(stepKey)) pushUsage(push, at, turn!, step!, usage)
      usageSeen.delete(stepKey)
      continue
    }
    if (type === 'tool/call') {
      const callId = stringValue(data.callId)
      if (!callId) continue
      toolStarted.set(callId, { at: time, name: stringValue(data.name) })
      continue
    }
    if (type === 'tool/result') {
      const message = recordOf(data.message)
      const source = recordOf(message?.source)
      const content = Array.isArray(message?.content) ? message.content : []
      const block = recordOf(content[0])
      const callId = stringValue(source?.callId) ?? stringValue(block?.toolCallId)
      if (!callId) continue
      const started = toolStarted.get(callId)
      toolStarted.delete(callId)
      const error = recordOf(data.error)
      const isError = error !== undefined || block?.isError === true
      push({
        at,
        component: 'tool',
        operation: 'execute',
        ...(started ? { durationMs: Math.max(0, time - started.at) } : {}),
        outcome: isError ? 'FAIL' : 'OK',
        values: { toolCallCount: 1 },
        tags: {
          ...(started?.name ? { tool: started.name } : {}),
          ...(turn !== undefined ? { turn } : {}),
          ...(step !== undefined ? { step } : {}),
        },
      })
    }
  }

  return result
}

export function analyzeHarnessSessionEvents(
  sessionId: string,
  events: readonly unknown[],
): FrameworkEfficiencyReport {
  return analyzeFrameworkMetrics(extractHarnessSessionMetrics(sessionId, events), { sessionId })
}

function pushUsage(
  push: (event: Omit<FrameworkMetricEvent, 'standard' | 'sessionId'>) => void,
  at: string,
  turn: number,
  step: number,
  usage: Record<string, unknown>,
): void {
  const values: Record<string, number> = {}
  for (const name of ['inputTokens', 'outputTokens', 'cacheReadTokens', 'cacheWriteTokens', 'reasoningTokens'] as const) {
    const value = finiteNumber(usage[name])
    if (value !== undefined) values[name] = value
  }
  if (Object.keys(values).length === 0) return
  push({
    at,
    component: 'runtime',
    operation: 'llmUsage',
    outcome: 'OK',
    values,
    tags: { turn, step },
  })
}
