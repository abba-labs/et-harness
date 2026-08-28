import {
  COMPLETION_EVALUATION_SCHEMA,
  EXECUTION_SUPERVISOR_CONTRACT_VERSION,
  OBLIGATION_LEDGER_SCHEMA,
  type CompletionEvaluation,
  type EvidenceBinding,
  type ObligationKind,
  type ObligationLedger,
  type ObligationLedgerEntry,
  type ObligationSpec,
  type ObligationStatus,
  type TaskSupervisionContract,
  type ViolationRecord,
} from './contracts.js'
import { sha256Canonical } from './canonical.js'
import { EXECUTION_SUPERVISOR_LIMITS } from './limits.js'

const unique = (values: readonly string[]): string[] =>
  [...new Set(values.map(value => value.trim()).filter(Boolean))]

const byObligationId = (
  contract: TaskSupervisionContract,
): ReadonlyMap<string, ObligationSpec> =>
  new Map(contract.obligations.map(item => [item.obligationId, item]))

export const createObligationLedger = (
  contract: TaskSupervisionContract,
): ObligationLedger => ({
  schema: OBLIGATION_LEDGER_SCHEMA,
  contractVersion: EXECUTION_SUPERVISOR_CONTRACT_VERSION,
  supervisionId: contract.correlation.supervisionId,
  contractHash: contract.contractHash,
  stateVersion: 1,
  lastSequence: -1,
  obligations: contract.obligations.map(item => ({
    obligationId: item.obligationId,
    kind: item.kind,
    level: item.level,
    status: 'PENDING',
    evidence: [],
    eventRefs: [],
    lastSequence: -1,
  })),
  violations: [],
})

export interface ObligationUpdate {
  readonly obligationId: string
  readonly status: ObligationStatus
  readonly sequence: number
  readonly eventRef?: string
  readonly evidence?: readonly EvidenceBinding[]
  readonly reason?: string
}

export const updateObligationLedgerEntry = (
  ledger: ObligationLedger,
  contract: TaskSupervisionContract,
  update: ObligationUpdate,
): ObligationLedger => {
  if (ledger.contractHash !== contract.contractHash) {
    throw new Error('Obligation Ledger and Task Supervision Contract do not match')
  }
  const specs = byObligationId(contract)
  const spec = specs.get(update.obligationId)
  if (!spec) throw new Error(`Unknown obligation: ${update.obligationId}`)
  if (!Number.isSafeInteger(update.sequence) || update.sequence < 0) {
    throw new Error('Obligation update sequence must be one non-negative safe integer')
  }
  if (update.status === 'NOT_APPLICABLE' && spec.allowNotApplicable !== true) {
    throw new Error(`Obligation ${update.obligationId} does not allow NOT_APPLICABLE`)
  }
  const index = ledger.obligations.findIndex(
    item => item.obligationId === update.obligationId,
  )
  if (index < 0) {
    throw new Error(`Obligation Ledger entry is missing: ${update.obligationId}`)
  }
  const current = ledger.obligations[index]!
  if (update.sequence < current.lastSequence) {
    throw new Error(
      `Stale obligation update ${update.sequence} < ${current.lastSequence}`,
    )
  }
  const evidence = [
    ...current.evidence,
    ...(update.evidence ?? []),
  ]
  const deduplicatedEvidence = [
    ...new Map(evidence.map(item => [item.receiptRef, item])).values(),
  ]
  if (
    deduplicatedEvidence.length
      > EXECUTION_SUPERVISOR_LIMITS.maxEvidenceBindingsPerObligation
  ) {
    throw new Error(
      `Obligation ${update.obligationId} exceeds its Evidence binding budget`,
    )
  }
  const next: ObligationLedgerEntry = {
    obligationId: current.obligationId,
    kind: current.kind,
    level: current.level,
    status: update.status,
    evidence: deduplicatedEvidence,
    eventRefs: unique([
      ...current.eventRefs,
      ...(update.eventRef ? [update.eventRef] : []),
    ]),
    lastSequence: update.sequence,
    ...(update.reason ? { reason: update.reason } : {}),
  }
  const obligations = [...ledger.obligations]
  obligations[index] = next
  return {
    ...ledger,
    stateVersion: ledger.stateVersion + 1,
    lastSequence: Math.max(ledger.lastSequence, update.sequence),
    obligations,
  }
}

export const addViolation = (
  ledger: ObligationLedger,
  violation: ViolationRecord,
): ObligationLedger => {
  const existingIndex = ledger.violations.findIndex(
    item => item.violationId === violation.violationId,
  )
  const violations = [...ledger.violations]
  if (existingIndex >= 0) {
    const existing = violations[existingIndex]!
    if (existing.code !== violation.code) {
      throw new Error(`Violation ID conflict: ${violation.violationId}`)
    }
    violations[existingIndex] = {
      ...violation,
      firstSequence: Math.min(existing.firstSequence, violation.firstSequence),
      lastSequence: Math.max(existing.lastSequence, violation.lastSequence),
      relatedRefs: unique([...existing.relatedRefs, ...violation.relatedRefs]),
    }
  } else {
    if (violations.length >= EXECUTION_SUPERVISOR_LIMITS.maxViolations) {
      throw new Error('Obligation Ledger exceeds its violation budget')
    }
    violations.push(violation)
  }
  return {
    ...ledger,
    stateVersion: ledger.stateVersion + 1,
    lastSequence: Math.max(ledger.lastSequence, violation.lastSequence),
    violations,
  }
}

const acceptedEvidence = (
  spec: ObligationSpec,
  entry: ObligationLedgerEntry,
): EvidenceBinding[] => entry.evidence.filter(binding => {
  if (!spec.evidencePolicy.acceptableAuthorities.includes(binding.authority)) {
    return false
  }
  if (!spec.evidencePolicy.acceptedOutcomes.includes(binding.outcome)) {
    return false
  }
  if (
    binding.authority === 'AGENT_DECLARATION'
    && spec.evidencePolicy.allowAgentDeclaration === false
  ) {
    return false
  }
  if (spec.evidencePolicy.requireCurrentRevision && !binding.revision) {
    return false
  }
  if (spec.evidencePolicy.requireContentHash && !binding.contentHash) {
    return false
  }
  return true
})

const obligationSatisfied = (
  spec: ObligationSpec,
  entry: ObligationLedgerEntry,
): boolean => {
  if (entry.status === 'NOT_APPLICABLE') return spec.allowNotApplicable === true
  if (entry.status !== 'SATISFIED') return false
  return acceptedEvidence(spec, entry).length
    >= spec.evidencePolicy.minimumReceipts
}

const REFLECTION_KINDS = new Set<ObligationKind>([
  'REFLECTION',
  'KNOWLEDGE_CLASSIFICATION',
])
const CLOSURE_KINDS = new Set<ObligationKind>([
  'CONTEXT_CLOSURE',
  'KNOWLEDGE_CLOSURE',
  'TURN_CLOSURE',
])

const hashEvaluation = (
  evaluation: Omit<CompletionEvaluation, 'evaluationHash'>,
): CompletionEvaluation => ({
  ...evaluation,
  evaluationHash: sha256Canonical(evaluation),
})

export const evaluateCompletion = (
  contract: TaskSupervisionContract,
  ledger: ObligationLedger,
): CompletionEvaluation => {
  if (ledger.contractHash !== contract.contractHash) {
    throw new Error('Completion evaluation rejected a mismatched Obligation Ledger')
  }
  if (ledger.supervisionId !== contract.correlation.supervisionId) {
    throw new Error('Completion evaluation rejected a mismatched supervisionId')
  }
  const specs = byObligationId(contract)
  const requiredLevels = new Set(contract.completionPolicy.requiredLevels)
  const requiredEntries = ledger.obligations.filter(entry =>
    requiredLevels.has(entry.level),
  )
  const pendingMustObligationIds: string[] = []
  const blockedObligationIds: string[] = []
  const missingEvidenceObligationIds: string[] = []
  const unsatisfiedPreReflection: string[] = []
  const unsatisfiedReflection: string[] = []
  const unsatisfiedClosure: string[] = []
  const unsatisfiedReuse: string[] = []

  for (const entry of requiredEntries) {
    const spec = specs.get(entry.obligationId)
    if (!spec) {
      blockedObligationIds.push(entry.obligationId)
      continue
    }
    const satisfied = obligationSatisfied(spec, entry)
    if (satisfied) continue
    pendingMustObligationIds.push(entry.obligationId)
    if (entry.status === 'BLOCKED' || entry.status === 'VIOLATED') {
      blockedObligationIds.push(entry.obligationId)
    }
    if (
      entry.status === 'SATISFIED'
      && acceptedEvidence(spec, entry).length
        < spec.evidencePolicy.minimumReceipts
    ) {
      missingEvidenceObligationIds.push(entry.obligationId)
    }
    if (spec.kind === 'FOLLOW_UP_REUSE') {
      unsatisfiedReuse.push(entry.obligationId)
    } else if (CLOSURE_KINDS.has(spec.kind)) {
      unsatisfiedClosure.push(entry.obligationId)
    } else if (REFLECTION_KINDS.has(spec.kind)) {
      unsatisfiedReflection.push(entry.obligationId)
    } else {
      unsatisfiedPreReflection.push(entry.obligationId)
    }
  }

  const blockingSeverities = new Set(
    contract.completionPolicy.blockingViolationSeverities,
  )
  const blockingViolationIds = ledger.violations
    .filter(item => item.status === 'OPEN' && blockingSeverities.has(item.severity))
    .map(item => item.violationId)
  const reasons: string[] = []
  let status: CompletionEvaluation['status']

  if (
    blockingViolationIds.length > 0
    || blockedObligationIds.length > 0
  ) {
    status = 'BLOCKED'
    if (blockingViolationIds.length > 0) {
      reasons.push(
        `${blockingViolationIds.length} open blocking violation(s) remain.`,
      )
    }
    if (blockedObligationIds.length > 0) {
      reasons.push(
        `${blockedObligationIds.length} required obligation(s) are BLOCKED or VIOLATED.`,
      )
    }
  } else if (unsatisfiedPreReflection.length > 0) {
    status = 'IN_PROGRESS'
    reasons.push(
      `${unsatisfiedPreReflection.length} execution obligation(s) remain before Reflection.`,
    )
  } else if (unsatisfiedReflection.length > 0) {
    status = 'READY_FOR_REFLECTION'
    reasons.push(
      'Execution obligations are satisfied; Framework-owned Reflection and classification must run.',
    )
  } else if (unsatisfiedClosure.length > 0) {
    status = 'READY_FOR_CLOSURE'
    reasons.push(
      'Reflection obligations are satisfied; mandatory Context/Knowledge/Turn Closure must run.',
    )
  } else if (unsatisfiedReuse.length > 0) {
    status = 'IN_PROGRESS'
    reasons.push(
      'The contract requires a follow-up Turn proving Context/Knowledge reuse.',
    )
  } else if (pendingMustObligationIds.length > 0) {
    status = 'IN_PROGRESS'
    reasons.push(
      `${pendingMustObligationIds.length} required obligation(s) remain unresolved.`,
    )
  } else {
    status = 'COMPLETE'
    reasons.push(
      'All required obligations have acceptable Evidence and no blocking violation remains.',
    )
  }

  if (missingEvidenceObligationIds.length > 0) {
    reasons.push(
      `${missingEvidenceObligationIds.length} obligation(s) were marked SATISFIED without sufficient acceptable Evidence.`,
    )
  }

  return hashEvaluation({
    schema: COMPLETION_EVALUATION_SCHEMA,
    contractVersion: EXECUTION_SUPERVISOR_CONTRACT_VERSION,
    supervisionId: contract.correlation.supervisionId,
    contractHash: contract.contractHash,
    ledgerStateVersion: ledger.stateVersion,
    status,
    pendingMustObligationIds: unique(pendingMustObligationIds),
    blockedObligationIds: unique(blockedObligationIds),
    blockingViolationIds: unique(blockingViolationIds),
    missingEvidenceObligationIds: unique(missingEvidenceObligationIds),
    reasons: unique(reasons),
  })
}
