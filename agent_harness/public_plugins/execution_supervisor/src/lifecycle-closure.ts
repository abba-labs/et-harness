import {
  EXECUTION_STORE_FINALIZATION_SCHEMA,
  SUPERVISION_LIFECYCLE_BINDING_SCHEMA,
  SUPERVISION_READINESS_RECEIPT_SCHEMA,
  type CompletionDecisionV01,
  type ExecutionEventStoreBindingV01,
  type ExecutionReplayCursorV01,
  type ExecutionStoreFinalizationV01,
  type ObligationLedgerStatusV01,
  type SupervisionLifecycleBindingV01,
  type SupervisionReadinessReceiptV01,
} from './contracts.js'
import { hashCanonicalJson } from './hash.js'

const HASH = /^[0-9a-f]{64}$/
const SHA256_FINGERPRINT = /^sha256:[0-9a-f]{64}$/
const SCOPES = new Set(['NONE', 'PROJECT', 'PUBLIC', 'BOTH'])

const requireText = (label: string, value: unknown): string => {
  if (typeof value !== 'string' || !value.trim()) throw new Error(`${label} cannot be empty`)
  return value
}

const requireHash = (label: string, value: unknown): string => {
  const text = requireText(label, value)
  if (!HASH.test(text)) throw new Error(`${label} must be a lowercase SHA-256 digest`)
  return text
}

export const supervisionFingerprint = (hash: string): string =>
  `sha256:${requireHash('hash', hash)}`

const readinessPreimage = (
  binding: ExecutionEventStoreBindingV01,
  cursor: ExecutionReplayCursorV01,
  ledgerStatusHash: string,
  decisionHash: string,
  taskEndEventId: string,
  taskEndTimestamp: string,
) => ({
  schema: SUPERVISION_READINESS_RECEIPT_SCHEMA,
  requestId: binding.requestId,
  runtimeId: binding.runtimeId,
  projectId: binding.contract.projectId,
  taskId: binding.contract.taskId,
  turnId: binding.turnId,
  agentId: binding.contract.agentId,
  contextHash: binding.contract.contextHash,
  contractHash: hashCanonicalJson(binding.contract),
  cursor,
  ledgerStatusHash,
  decisionHash,
  taskEndEventId,
  taskEndTimestamp,
})

export const createSupervisionReadinessReceipt = (input: {
  readonly binding: ExecutionEventStoreBindingV01
  readonly cursor: ExecutionReplayCursorV01
  readonly status: ObligationLedgerStatusV01
  readonly decision: CompletionDecisionV01
  readonly taskEndEventId: string
  readonly taskEndTimestamp: string
}): SupervisionReadinessReceiptV01 => {
  if (input.decision.status !== 'READY_TO_CLOSE') {
    throw new Error(`Supervision readiness requires READY_TO_CLOSE, got ${input.decision.status}`)
  }
  if (input.status.cursor.sequence !== input.cursor.sequence
      || input.status.cursor.stateHash !== input.cursor.stateHash) {
    throw new Error('Obligation Ledger status cursor does not match the Event Store cursor')
  }
  const taskEndEventId = requireText('taskEndEventId', input.taskEndEventId)
  const taskEndTimestamp = requireText('taskEndTimestamp', input.taskEndTimestamp)
  if (Number.isNaN(Date.parse(taskEndTimestamp))) {
    throw new Error('taskEndTimestamp must be an ISO-compatible persisted timestamp')
  }
  const ledgerStatusHash = hashCanonicalJson(input.status)
  const decisionHash = hashCanonicalJson(input.decision)
  const preimage = readinessPreimage(
    input.binding,
    input.cursor,
    ledgerStatusHash,
    decisionHash,
    taskEndEventId,
    taskEndTimestamp,
  )
  const receiptHash = hashCanonicalJson(preimage)
  return Object.freeze({
    ...preimage,
    receiptHash,
    receiptRef: `supervision-readiness://${supervisionFingerprint(receiptHash)}`,
  })
}

export const assertReadinessReceipt = (
  receipt: SupervisionReadinessReceiptV01,
  expected: SupervisionReadinessReceiptV01,
): void => {
  if (hashCanonicalJson(receipt) !== hashCanonicalJson(expected)) {
    throw new Error('Supervision readiness receipt does not match the latest durable Ledger state')
  }
  requireHash('receipt.receiptHash', receipt.receiptHash)
  if (receipt.receiptRef !== `supervision-readiness://${supervisionFingerprint(receipt.receiptHash)}`) {
    throw new Error('Supervision readiness receiptRef does not match receiptHash')
  }
}

export const lifecycleBindingHash = (binding: SupervisionLifecycleBindingV01): string =>
  hashCanonicalJson(binding)

export const lifecycleClosureRef = (binding: SupervisionLifecycleBindingV01): string =>
  `supervision-closure://${supervisionFingerprint(lifecycleBindingHash(binding))}`

export const assertLifecycleBindingShape = (
  binding: SupervisionLifecycleBindingV01,
): void => {
  if (binding.schema !== SUPERVISION_LIFECYCLE_BINDING_SCHEMA) {
    throw new Error(`Unsupported supervision lifecycle binding schema: ${String(binding.schema)}`)
  }
  for (const [label, value] of [
    ['readinessRef', binding.readinessRef],
    ['projectId', binding.projectId],
    ['taskId', binding.taskId],
    ['turnId', binding.turnId],
    ['agentId', binding.agentId],
    ['contextHash', binding.contextHash],
    ['journalRef', binding.journalRef],
    ['reflectionRef', binding.reflection.reflectionRef],
    ['reflectionInputFingerprint', binding.reflection.inputFingerprint],
    ['kernelClosureRef', binding.kernelClosureRef],
    ['kernelClosureInputFingerprint', binding.kernelClosureInputFingerprint],
  ] as const) requireText(label, value)
  requireHash('readinessHash', binding.readinessHash)
  if (Number.isNaN(Date.parse(binding.kernelClosureCreatedAt))) {
    throw new Error('kernelClosureCreatedAt must be an ISO-compatible persisted timestamp')
  }
  for (const [domain, scope] of Object.entries(binding.reflection.domainDecisions)) {
    if (!SCOPES.has(scope)) throw new Error(`Invalid ${domain} Reflection scope: ${scope}`)
  }
  const moduleIds = new Set<string>()
  for (const receipt of binding.moduleReceipts) {
    requireText('moduleId', receipt.moduleId)
    requireText('moduleVersion', receipt.moduleVersion)
    requireText('idempotencyKey', receipt.idempotencyKey)
    if (!['APPLIED', 'NO_CHANGE'].includes(receipt.status)) {
      throw new Error(`Closure module ${receipt.moduleId} is not successful: ${receipt.status}`)
    }
    if (moduleIds.has(receipt.moduleId)) throw new Error(`Duplicate Closure module receipt: ${receipt.moduleId}`)
    moduleIds.add(receipt.moduleId)
  }
}

export const createLifecycleFinalization = (
  binding: SupervisionLifecycleBindingV01,
  cursor: ExecutionReplayCursorV01,
): ExecutionStoreFinalizationV01 => {
  assertLifecycleBindingShape(binding)
  const finalizationHash = lifecycleBindingHash(binding)
  return Object.freeze({
    schema: EXECUTION_STORE_FINALIZATION_SCHEMA,
    cursor: Object.freeze({ ...cursor }),
    finalizationRef: lifecycleClosureRef(binding),
    finalizationHash,
    finalizedAt: binding.kernelClosureCreatedAt,
    payload: binding as unknown as Readonly<Record<string, unknown>>,
  })
}
