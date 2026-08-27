import { describe, expect, it } from 'vitest'
import type { FrameworkMetricEvent } from '@agent-harness/governance-core'
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
})
