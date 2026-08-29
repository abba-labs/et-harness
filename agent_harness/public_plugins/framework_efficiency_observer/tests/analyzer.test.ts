import { describe, expect, it, vi } from 'vitest'
import {
  activateFrameworkMetrics,
  observeFrameworkOperation,
  type FrameworkMetricEvent,
} from '@agent-harness/governance-core'
import { analyzeFrameworkMetrics } from '../src/analyzer.js'

const event = (overrides: Partial<FrameworkMetricEvent>): FrameworkMetricEvent => ({
  standard: 'framework-metric-v0.1',
  at: '2026-08-22T03:00:00.000Z',
  component: 'architecture',
  operation: 'search',
  projectId: 'p1',
  taskId: 'T1',
  durationMs: 2,
  outcome: 'OK',
  ...overrides,
})

describe('Framework Efficiency Analyzer', () => {
  it('按任务汇总 component、耗时和问题信号', () => {
    const events = [
      event({ component: 'architecture', durationMs: 3, outcome: 'OK' }),
      event({ component: 'rule', durationMs: 7, outcome: 'MISS' }),
      event({ component: 'context', operation: 'buildFrame', durationMs: 4, values: { contextChars: 12000, overBudgetCount: 0 } }),
      event({ component: 'gate', operation: 'checkSetEvidence', durationMs: 5, outcome: 'FAIL' }),
      event({ taskId: 'OTHER', component: 'rule', durationMs: 100, outcome: 'ERROR' }),
    ]

    const report = analyzeFrameworkMetrics(events, { projectId: 'p1', taskId: 'T1' })
    expect(report.eventCount).toBe(4)
    expect(report.observedFrameworkDurationMs).toBe(19)
    expect(report.components[0]?.component).toBe('rule')
    expect(report.components.find(item => item.component === 'rule')?.missCount).toBe(1)
    expect(report.findings.some(item => item.includes('route miss 1/1'))).toBe(true)
    expect(report.findings.some(item => item.includes('gate: 1 FAIL'))).toBe(true)
  })

  it('reports bounded Supervisor metrics without becoming completion authority', () => {
    const report = analyzeFrameworkMetrics([
      event({
        component: 'runtime',
        operation: 'execution-supervisor-phase7-benchmark',
        durationMs: 142.801,
        values: {
          eventCount: 1_000,
          compactedAccessCount: 1_000,
          eventIngestP50Micros: 37_423.946,
          eventIngestP95Micros: 42_162.611,
          ledgerTransitionP50Micros: 2_389.324,
          ledgerTransitionP95Micros: 3_609.911,
          replayMillis: 142.801,
          persistedBytesPerEvent: 1_158.416,
          ledgerProjectionBytes: 1_101,
          contextDeltaBytes: 1_278,
          rerouteCount: 0,
          semanticCallCount: 0,
          reflectionCount: 1,
        },
      }),
    ])

    expect(report.components[0]).toMatchObject({
      component: 'runtime',
      operationCounts: { 'execution-supervisor-phase7-benchmark': 1 },
      values: {
        eventCount: 1_000,
        compactedAccessCount: 1_000,
        eventIngestP50Micros: 37_423.946,
        eventIngestP95Micros: 42_162.611,
        ledgerTransitionP50Micros: 2_389.324,
        ledgerTransitionP95Micros: 3_609.911,
        replayMillis: 142.801,
        persistedBytesPerEvent: 1_158.416,
        ledgerProjectionBytes: 1_101,
        contextDeltaBytes: 1_278,
        rerouteCount: 0,
        semanticCallCount: 0,
        reflectionCount: 1,
      },
    })
    expect(report).not.toHaveProperty('completionStatus')
  })

  it('keeps the same supervision result with metrics off, on or throwing', () => {
    const action = () => ({ status: 'SATISFIED' as const, violationCount: 0 })
    const input = { component: 'runtime' as const, operation: 'execution-supervisor-ingest' }
    const withoutObserver = observeFrameworkOperation({ emit: vi.fn() } as any, input, action)
    const dispose = activateFrameworkMetrics()
    try {
      const withObserver = observeFrameworkOperation({ emit: vi.fn() } as any, input, action)
      const withBrokenObserver = observeFrameworkOperation({
        emit: vi.fn(() => { throw new Error('observer unavailable') }),
      } as any, input, action)
      expect(withObserver).toEqual(withoutObserver)
      expect(withBrokenObserver).toEqual(withoutObserver)
    } finally {
      dispose()
    }
  })
})
