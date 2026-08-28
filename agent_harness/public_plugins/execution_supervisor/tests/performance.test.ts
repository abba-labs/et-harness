import { performance } from 'node:perf_hooks'
import { describe, expect, it } from 'vitest'
import {
  EXECUTION_SUPERVISOR_LIMITS,
  EXECUTION_SUPERVISOR_PHASE0_PERFORMANCE_BASELINE,
} from '../src/contracts.js'
import {
  createInitialObligationLedger,
  evaluateCompletionDecision,
} from '../src/phase0-runtime.js'
import { validateExecutionEvent } from '../src/validation.js'
import { contractFixture, eventFixture, FIXED_TIME } from './fixtures.js'

const percentile = (values: readonly number[], fraction: number): number => {
  const sorted = [...values].sort((left, right) => left - right)
  return sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * fraction))] ?? 0
}

describe('Execution Supervisor Phase 0 efficiency baseline', () => {
  it('keeps one ordinary event bounded and free of large content payloads', () => {
    const event = eventFixture()
    const bytes = Buffer.byteLength(JSON.stringify(event), 'utf8')
    expect(bytes).toBeLessThan(EXECUTION_SUPERVISOR_LIMITS.maxEventBytes)
    expect(EXECUTION_SUPERVISOR_PHASE0_PERFORMANCE_BASELINE.hotPathLlmCallsAllowed).toBe(0)
    expect(EXECUTION_SUPERVISOR_PHASE0_PERFORMANCE_BASELINE.fullRouteRefreshPerOrdinaryReadAllowed)
      .toBe(false)
    expect(EXECUTION_SUPERVISOR_PHASE0_PERFORMANCE_BASELINE.synchronousExternalIoOnIngestAllowed)
      .toBe(false)
  })

  it('validates ordinary events within a conservative CI p95 guardrail', () => {
    const event = eventFixture()
    for (let index = 0; index < 200; index += 1) validateExecutionEvent(event)

    const samples: number[] = []
    for (let index = 0; index < 2_000; index += 1) {
      const started = performance.now()
      const result = validateExecutionEvent(event)
      samples.push(performance.now() - started)
      if (!result.valid) throw new Error(result.errors.join('; '))
    }

    // Phase 0 target is 1 ms p95. The CI gate allows 5 ms to avoid runner
    // scheduling noise while still detecting accidental I/O or heavyweight work.
    expect(percentile(samples, 0.95)).toBeLessThan(5)
  })

  it('evaluates completion without routing, I/O or model calls', () => {
    const contract = contractFixture()
    const pending = createInitialObligationLedger(contract, FIXED_TIME)
    const ledger = {
      ...pending,
      obligations: pending.obligations.map(state => ({
        ...state,
        status: 'SATISFIED' as const,
      })),
    }
    const started = performance.now()
    for (let index = 0; index < 5_000; index += 1) {
      const decision = evaluateCompletionDecision({
        decisionId: `DECISION-${index}`,
        contract,
        ledger,
        lifecycle: {
          reflectionComplete: true,
          knowledgeDecisionComplete: true,
          contextReconciliationComplete: true,
          closureComplete: true,
        },
        decidedAt: FIXED_TIME,
      })
      if (decision.status !== 'COMPLETE') throw new Error(decision.reason)
    }
    expect(performance.now() - started).toBeLessThan(2_500)
  })
})
