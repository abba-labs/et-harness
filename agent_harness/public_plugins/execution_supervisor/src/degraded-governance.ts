export const GOVERNANCE_DEGRADED_STATUS = 'GOVERNANCE_DEGRADED' as const

export interface GovernanceDegradedNoticeV01 {
  readonly status: typeof GOVERNANCE_DEGRADED_STATUS
  readonly formalPassCloseAllowed: false
  readonly reason: string
}

const boundedReason = (value: unknown): string => {
  const raw = value instanceof Error ? value.message : String(value ?? '')
  return raw.replace(/\s+/g, ' ').trim().slice(0, 1200) || 'Framework unavailable'
}

/**
 * Host-side marker for the narrow case where the Framework entry path itself
 * is unavailable. It does not create a new normal lifecycle state and does not
 * authorize completion. Formal PASS/CLOSE remains owned by the existing
 * Framework lifecycle authority and durable Closure/finalization path.
 */
export const createGovernanceDegradedNotice = (
  reason: unknown,
): GovernanceDegradedNoticeV01 => Object.freeze({
  status: GOVERNANCE_DEGRADED_STATUS,
  formalPassCloseAllowed: false,
  reason: boundedReason(reason),
})
