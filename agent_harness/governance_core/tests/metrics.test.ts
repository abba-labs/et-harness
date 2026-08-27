import { describe, expect, it } from 'vitest'
import type { Context } from '@deepseek-ai/cordis'
import {
  activateFrameworkMetrics,
  frameworkMetricsActive,
  observeFrameworkOperation,
} from '../src/metrics.js'

describe('framework metrics fail-open fast path', () => {
  it('observer 未激活时直接执行 action，不调用 summarize / emit', () => {
    expect(frameworkMetricsActive()).toBe(false)
    let emitted = 0
    let summarized = 0
    const ctx = {
      emit: () => { emitted += 1 },
    } as unknown as Context

    const result = observeFrameworkOperation(
      ctx,
      { component: 'rule', operation: 'search' },
      () => 42,
      () => {
        summarized += 1
        return { outcome: 'OK' }
      },
    )

    expect(result).toBe(42)
    expect(summarized).toBe(0)
    expect(emitted).toBe(0)
  })

  it('observer 激活后采集，listener 抛错也不影响 action', () => {
    const dispose = activateFrameworkMetrics()
    expect(frameworkMetricsActive()).toBe(true)
    let emitted = 0
    const ctx = {
      emit: () => {
        emitted += 1
        throw new Error('BROKEN_OBSERVER')
      },
    } as unknown as Context

    const result = observeFrameworkOperation(
      ctx,
      { component: 'architecture', operation: 'search' },
      () => 'RESULT',
      () => ({ outcome: 'OK', values: { resultCount: 1 } }),
    )

    expect(result).toBe('RESULT')
    expect(emitted).toBe(1)
    dispose()
    dispose()
    expect(frameworkMetricsActive()).toBe(false)
  })
})
