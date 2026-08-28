export const EXECUTION_SUPERVISOR_LIMITS = Object.freeze({
  maxIdentifierChars: 128,
  maxTitleChars: 240,
  maxDescriptionChars: 4_000,
  maxSummaryChars: 4_000,
  maxReferenceChars: 1_024,
  maxReferencesPerField: 64,
  maxObligations: 512,
  maxEvidenceBindingsPerObligation: 64,
  maxViolations: 512,
  maxBatchEvents: 256,
  maxContractBytes: 512 * 1_024,
  maxEventBytes: 64 * 1_024,
  maxReceiptBytes: 64 * 1_024,
  maxLedgerBytes: 2 * 1_024 * 1_024,
  maxCustomPayloadBytes: 16 * 1_024,
})

export type ExecutionSupervisorLimitName = keyof typeof EXECUTION_SUPERVISOR_LIMITS

/**
 * Phase 0 performance policy.
 *
 * These values are intentionally generous CI guardrails, not product latency
 * promises. Their purpose is to catch accidental LLM/network/file-system work,
 * quadratic scans, or unbounded payload handling in the deterministic hot path.
 */
export const EXECUTION_SUPERVISOR_PERFORMANCE_BASELINE = Object.freeze({
  contractValidationIterations: 2_000,
  eventSealAndValidationIterations: 5_000,
  completionEvaluationIterations: 5_000,
  maxContractValidationMs: 2_500,
  maxEventSealAndValidationMs: 3_500,
  maxCompletionEvaluationMs: 2_500,
  hotPathLlmCallsAllowed: 0,
  hotPathNetworkCallsAllowed: 0,
  hotPathProjectFileReadsAllowed: 0,
  hotPathFullReroutesAllowed: 0,
})
