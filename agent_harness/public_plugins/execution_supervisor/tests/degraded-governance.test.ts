import { describe, expect, it } from 'vitest'
import {
  GOVERNANCE_DEGRADED_STATUS,
  createGovernanceDegradedNotice,
} from '../src/degraded-governance.js'

describe('minimal degraded governance marker', () => {
  it('marks Framework entry failure as degraded and forbids formal PASS/CLOSE', () => {
    const notice = createGovernanceDegradedNotice(
      new Error('health/capabilities unavailable'),
    )

    expect(notice).toEqual({
      status: GOVERNANCE_DEGRADED_STATUS,
      formalPassCloseAllowed: false,
      reason: 'health/capabilities unavailable',
    })
  })

  it('keeps the failure reason bounded and non-empty', () => {
    expect(createGovernanceDegradedNotice('').reason).toBe('Framework unavailable')
    expect(createGovernanceDegradedNotice('x'.repeat(2_000)).reason).toHaveLength(1_200)
  })
})
