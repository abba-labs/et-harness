import {
  COMPLETION_DECISION_SCHEMA,
  EXECUTION_SUPERVISOR_CONTRACT_VERSION,
  OBLIGATION_LEDGER_SCHEMA,
  SUPERVISION_VIOLATION_SCHEMA,
  type CompletionDecisionV01,
  type ExecutionEventV01,
  type ObligationLedgerSnapshotV01,
  type SupervisionIdentityV01,
  type SupervisionViolationKind,
  type SupervisionViolationV01,
  type TaskSupervisionContractV01,
} from './contracts.js'
import {
  computeTaskSupervisionContractHash,
} from './canonical-json.js'

const unique = (values: readonly string[]): string[] =>
  [...new Set(values.map(value => value.trim()).filter(Boolean))]

const sameIdentity = (
  left: SupervisionIdentityV01,
  right: SupervisionIdentityV01,
): boolean => left.runtimeId === right.runtimeId
  && left.taskId === right.taskId
  && left.turnId === right.turnId
  && left.agentId === right.agentId
  && left.projectId === right.projectId

export const createInitialObligationLedger = (
  contract: TaskSupervisionContractV01,
  now: string,
): ObligationLedgerSnapshotV01 => ({
  schema: OBLIGATION_LEDGER_SCHEMA,
  contractVersion: EXECUTION_SUPERVISOR_CONTRACT_VERSION,
  contractId: contract.contractId,
  contractHash: computeTaskSupervisionContractHash(contract),
  identity: contract.identity,
  ledgerVersion: 0,
  lastAcceptedSequence: 0,
  obligations: contract.obligations.map(obligation => ({
    obligationId: obligation.obligationId,
    status: 'PENDING',
    eventRefs: [],
    evidenceRefs: [],
  })),
  violations: [],
  updatedAt: now,
})

export const createSupervisionViolation = (input: {
  readonly violationId: string
  readonly identity: SupervisionIdentityV01
  readonly kind: SupervisionViolationKind
  readonly severity: SupervisionViolationV01['severity']
  readonly detectedAt: string
  readonly eventRefs?: readonly string[]
  readonly obligationIds?: readonly string[]
  readonly details: string
  readonly blocking?: boolean
}): SupervisionViolationV01 => ({
  schema: SUPERVISION_VIOLATION_SCHEMA,
  violationId: input.violationId,
  identity: input.identity,
  kind: input.kind,
  severity: input.severity,
  detectedAt: input.detectedAt,
  eventRefs: unique(input.eventRefs ?? []),
  obligationIds: unique(input.obligationIds ?? []),
  details: input.details,
  blocking: input.blocking ?? input.severity !== 'WARNING',
})

/**
 * Phase 0 protocol checks only. Obligation matching and event persistence are
 * implemented in later phases; identity and hash-chain invariants are frozen
 * here so every Host Adapter follows the same rules.
 */
export const checkExecutionEventProtocol = (input: {
  readonly contract: TaskSupervisionContractV01
  readonly ledger: ObligationLedgerSnapshotV01
  readonly event: ExecutionEventV01
  readonly detectedAt: string
}): readonly SupervisionViolationV01[] => {
  const { contract, ledger, event, detectedAt } = input
  const violations: SupervisionViolationV01[] = []
  const eventRef = `execution-event://${event.eventId}`
  const append = (
    kind: SupervisionViolationKind,
    details: string,
    severity: SupervisionViolationV01['severity'] = 'FATAL',
  ) => {
    violations.push(createSupervisionViolation({
      violationId: `V-${event.eventId}-${String(violations.length + 1).padStart(2, '0')}`,
      identity: contract.identity,
      kind,
      severity,
      detectedAt,
      eventRefs: [eventRef],
      details,
    }))
  }

  if (!sameIdentity(contract.identity, event.identity)
      || !sameIdentity(ledger.identity, event.identity)) {
    append('IDENTITY_MISMATCH', 'Execution Event identity does not match the bound Task Supervision Contract and Ledger.')
  }
  const expectedContractHash = computeTaskSupervisionContractHash(contract)
  if (ledger.contractHash !== expectedContractHash
      || event.integrity.contractHash !== expectedContractHash) {
    append('CONTRACT_HASH_MISMATCH', 'Execution Event or Ledger is not bound to the exact Task Supervision Contract.')
  }
  const expectedSequence = ledger.lastAcceptedSequence + 1
  if (event.sequence !== expectedSequence) {
    append(
      'EVENT_SEQUENCE_GAP',
      `Expected execution sequence ${expectedSequence}, received ${event.sequence}.`,
    )
  }
  if (ledger.lastAcceptedSequence > 0
      && event.integrity.previousEventHash !== ledger.lastEventHash) {
    append('EVENT_TAMPERING', 'Execution Event previousEventHash does not match the accepted event chain.')
  }
  if (ledger.lastAcceptedSequence === 0 && event.integrity.previousEventHash !== undefined) {
    append('EVENT_TAMPERING', 'The first Execution Event must not declare previousEventHash.')
  }
  return violations
}

export interface CompletionLifecycleStateV01 {
  readonly reflectionComplete: boolean
  readonly knowledgeDecisionComplete: boolean
  readonly contextReconciliationComplete: boolean
  readonly closureComplete: boolean
  readonly evidenceRefs?: readonly string[]
}

export const evaluateCompletionDecision = (input: {
  readonly decisionId: string
  readonly contract: TaskSupervisionContractV01
  readonly ledger: ObligationLedgerSnapshotV01
  readonly lifecycle: CompletionLifecycleStateV01
  readonly decidedAt: string
}): CompletionDecisionV01 => {
  const { contract, ledger, lifecycle, decidedAt } = input
  const mustIds = new Set(
    contract.obligations
      .filter(obligation => obligation.level === 'MUST')
      .map(obligation => obligation.obligationId),
  )
  const satisfiedMustObligationIds = ledger.obligations
    .filter(state => mustIds.has(state.obligationId)
      && (state.status === 'SATISFIED' || state.status === 'NOT_APPLICABLE'))
    .map(state => state.obligationId)
  const outstandingMustObligationIds = ledger.obligations
    .filter(state => mustIds.has(state.obligationId)
      && state.status !== 'SATISFIED'
      && state.status !== 'NOT_APPLICABLE')
    .map(state => state.obligationId)
  const blockingViolationIds = ledger.violations
    .filter(violation => violation.blocking
      && (violation.severity === 'ERROR' || violation.severity === 'FATAL'))
    .map(violation => violation.violationId)

  const missingLifecycle: string[] = []
  if (contract.completionPolicy.reflectionRequired && !lifecycle.reflectionComplete) {
    missingLifecycle.push('Reflection')
  }
  if (contract.completionPolicy.knowledgeDecisionRequired
      && !lifecycle.knowledgeDecisionComplete) {
    missingLifecycle.push('KnowledgeDecision')
  }
  if (contract.completionPolicy.contextReconciliationRequired
      && !lifecycle.contextReconciliationComplete) {
    missingLifecycle.push('ContextReconciliation')
  }
  if (contract.completionPolicy.closureRequired && !lifecycle.closureComplete) {
    missingLifecycle.push('Closure')
  }

  const hasBlockedObligation = ledger.obligations.some(state =>
    mustIds.has(state.obligationId)
    && (state.status === 'BLOCKED' || state.status === 'VIOLATED'))
  const status: CompletionDecisionV01['status'] =
    blockingViolationIds.length > 0 || hasBlockedObligation
      ? 'BLOCKED'
      : outstandingMustObligationIds.length > 0 || missingLifecycle.length > 0
        ? 'INCOMPLETE'
        : 'COMPLETE'
  const reason = status === 'COMPLETE'
    ? 'All MUST obligations and required lifecycle closures are satisfied.'
    : status === 'BLOCKED'
      ? `Completion is blocked by violations or blocked obligations: ${[
          ...blockingViolationIds,
          ...outstandingMustObligationIds,
        ].join(', ') || 'unspecified blocker'}.`
      : `Completion is incomplete; outstanding obligations/lifecycle: ${[
          ...outstandingMustObligationIds,
          ...missingLifecycle,
        ].join(', ')}.`

  return {
    schema: COMPLETION_DECISION_SCHEMA,
    contractVersion: EXECUTION_SUPERVISOR_CONTRACT_VERSION,
    decisionId: input.decisionId,
    identity: contract.identity,
    contractId: contract.contractId,
    contractHash: computeTaskSupervisionContractHash(contract),
    ledgerVersion: ledger.ledgerVersion,
    status,
    decidedAt,
    satisfiedMustObligationIds: unique(satisfiedMustObligationIds),
    outstandingMustObligationIds: unique(outstandingMustObligationIds),
    blockingViolationIds: unique(blockingViolationIds),
    reflectionComplete: lifecycle.reflectionComplete,
    knowledgeDecisionComplete: lifecycle.knowledgeDecisionComplete,
    contextReconciliationComplete: lifecycle.contextReconciliationComplete,
    closureComplete: lifecycle.closureComplete,
    evidenceRefs: unique(lifecycle.evidenceRefs ?? []),
    reason,
  }
}
