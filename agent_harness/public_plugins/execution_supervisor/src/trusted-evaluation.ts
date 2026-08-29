import type {
  EvidencePolicyV01,
  EvidenceProviderKind,
  EvidenceResultStatus,
  TaskSupervisionContractV01,
} from './contracts.js'

export const TRUSTED_EVIDENCE_REASON_CODES = [
  'PROVIDER_ID_NOT_ACCEPTED',
  'PROVIDER_KIND_NOT_ACCEPTED',
  'RESULT_STATUS_NOT_ACCEPTED',
  'CONTEXT_HASH_MISMATCH',
  'PROJECT_REVISION_UNAVAILABLE',
  'PROJECT_REVISION_MISMATCH',
  'TARGET_IDENTITY_UNAVAILABLE',
  'TARGET_IDENTITY_MISMATCH',
  'INVALID_RECEIPT_TIMESTAMP',
  'INVALID_EVALUATION_TIMESTAMP',
  'EVIDENCE_FROM_FUTURE',
  'EVIDENCE_STALE',
  'REQUIRED_RESULT_STATUS_MISMATCH',
] as const

export type TrustedEvidenceReasonCode =
  typeof TRUSTED_EVIDENCE_REASON_CODES[number]

export interface EvaluateTrustedEvidenceInputV01 {
  readonly policy: EvidencePolicyV01
  readonly contract: TaskSupervisionContractV01
  readonly providerId: string
  readonly providerKind: EvidenceProviderKind
  readonly resultStatus: EvidenceResultStatus
  readonly contextHash: string
  readonly projectRevision?: string
  readonly targetIdentity: string
  readonly timestamp: string
  readonly evaluationAt: string
  readonly requiredResultStatus: 'PASS'
  /**
   * The caller may supply the exact obligation target explicitly. When omitted,
   * the evaluator derives it from the policy's referenced obligation targets.
   */
  readonly expectedTargetIdentity?: string
}

export interface TrustedEvidenceEvaluationV01 {
  /** The receipt matches every trust, identity, status and freshness rule. */
  readonly accepted: boolean
  /** Accepted Evidence satisfies the caller's required PASS result. */
  readonly satisfying: boolean
  /** An accepted FAIL is a trusted failure, never satisfying Evidence. */
  readonly trustedFailure: boolean
  readonly reasons: readonly TrustedEvidenceReasonCode[]
}

const parseTimestamp = (value: string): number | undefined => {
  const parsed = Date.parse(value)
  return Number.isFinite(parsed) ? parsed : undefined
}

const deriveExpectedTargetIdentity = (
  policy: EvidencePolicyV01,
  contract: TaskSupervisionContractV01,
): string | undefined => {
  const targetIdentities = new Set<string>()
  for (const obligationId of policy.obligationIds) {
    const obligation = contract.obligations.find(item => item.id === obligationId)
    const targetIdentity = obligation?.target.targetIdentity
    if (typeof targetIdentity === 'string' && targetIdentity.length > 0) {
      targetIdentities.add(targetIdentity)
    }
  }
  return targetIdentities.size === 1
    ? targetIdentities.values().next().value
    : undefined
}

/**
 * Applies only deterministic, Project-contributed Evidence Policy rules.
 * Provider strings are declarations already admitted by the trusted Bridge;
 * this function does not authenticate a Host or provider cryptographically.
 */
export const evaluateTrustedEvidence = (
  input: EvaluateTrustedEvidenceInputV01,
): TrustedEvidenceEvaluationV01 => {
  const reasons: TrustedEvidenceReasonCode[] = []

  if (input.policy.acceptedProviderIds.length > 0
      && !input.policy.acceptedProviderIds.includes(input.providerId)) {
    reasons.push('PROVIDER_ID_NOT_ACCEPTED')
  }
  if (input.policy.acceptedProviderKinds.length > 0
      && !input.policy.acceptedProviderKinds.includes(input.providerKind)) {
    reasons.push('PROVIDER_KIND_NOT_ACCEPTED')
  }
  if (!input.policy.acceptedResultStatuses.includes(input.resultStatus)) {
    reasons.push('RESULT_STATUS_NOT_ACCEPTED')
  }
  if (input.policy.requireExactContextHash
      && input.contextHash !== input.contract.contextHash) {
    reasons.push('CONTEXT_HASH_MISMATCH')
  }
  if (input.policy.requireExactProjectRevision) {
    if (input.contract.projectRevision === undefined) {
      reasons.push('PROJECT_REVISION_UNAVAILABLE')
    } else if (input.projectRevision !== input.contract.projectRevision) {
      reasons.push('PROJECT_REVISION_MISMATCH')
    }
  }
  if (input.policy.requireExactTargetIdentity) {
    const expectedTargetIdentity = input.expectedTargetIdentity
      ?? deriveExpectedTargetIdentity(input.policy, input.contract)
    if (expectedTargetIdentity === undefined) {
      reasons.push('TARGET_IDENTITY_UNAVAILABLE')
    } else if (input.targetIdentity !== expectedTargetIdentity) {
      reasons.push('TARGET_IDENTITY_MISMATCH')
    }
  }

  const receiptTimestamp = parseTimestamp(input.timestamp)
  const evaluationTimestamp = parseTimestamp(input.evaluationAt)
  if (receiptTimestamp === undefined) reasons.push('INVALID_RECEIPT_TIMESTAMP')
  if (evaluationTimestamp === undefined) reasons.push('INVALID_EVALUATION_TIMESTAMP')
  if (receiptTimestamp !== undefined && evaluationTimestamp !== undefined) {
    if (receiptTimestamp > evaluationTimestamp) {
      reasons.push('EVIDENCE_FROM_FUTURE')
    } else if (input.policy.maxAgeSeconds !== undefined
        && evaluationTimestamp - receiptTimestamp
          > input.policy.maxAgeSeconds * 1_000) {
      reasons.push('EVIDENCE_STALE')
    }
  }

  const trustReasons = reasons.filter(reason => reason !== 'RESULT_STATUS_NOT_ACCEPTED')
  const trusted = trustReasons.length === 0
  const accepted = trusted && !reasons.includes('RESULT_STATUS_NOT_ACCEPTED')
  const satisfying = accepted
    && input.policy.acceptedResultStatuses.includes(input.resultStatus)
    && input.resultStatus === input.requiredResultStatus
    && input.resultStatus === 'PASS'
  if (accepted && !satisfying) {
    reasons.push('REQUIRED_RESULT_STATUS_MISMATCH')
  }

  return {
    accepted,
    satisfying,
    trustedFailure: trusted && input.resultStatus === 'FAIL',
    reasons,
  }
}
