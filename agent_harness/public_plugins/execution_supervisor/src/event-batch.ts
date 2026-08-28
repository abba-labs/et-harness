import {
  EXECUTION_SUPERVISOR_CONTRACT_VERSION,
  EXECUTION_SUPERVISOR_LIMITS,
  type ExecutionEventV01,
  type SupervisionIdentityV01,
} from './contracts.js'
import {
  validateExecutionEvent,
  type SupervisionValidationResult,
} from './validation.js'

export const EXECUTION_EVENT_BATCH_SCHEMA =
  'agent-harness.execution-event-batch.v0.1' as const

export interface ExecutionEventBatchV01 {
  readonly schema: typeof EXECUTION_EVENT_BATCH_SCHEMA
  readonly contractVersion: typeof EXECUTION_SUPERVISOR_CONTRACT_VERSION
  readonly batchId: string
  readonly identity: SupervisionIdentityV01
  readonly contractHash: string
  readonly firstSequence: number
  readonly lastSequence: number
  readonly events: readonly ExecutionEventV01[]
  readonly createdAt: string
}

const IDENTIFIER_RE = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$/
const SHA256_RE = /^[0-9a-f]{64}$/

const recordOf = (value: unknown): Record<string, unknown> | undefined =>
  typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : undefined

const sameIdentity = (
  left: SupervisionIdentityV01,
  right: SupervisionIdentityV01,
): boolean => left.runtimeId === right.runtimeId
  && left.taskId === right.taskId
  && left.turnId === right.turnId
  && left.agentId === right.agentId
  && left.projectId === right.projectId

export const validateExecutionEventBatch = (
  value: unknown,
): SupervisionValidationResult => {
  const errors: string[] = []
  const batch = recordOf(value)
  if (!batch) return { valid: false, errors: ['batch must be an object'] }
  if (batch.schema !== EXECUTION_EVENT_BATCH_SCHEMA) errors.push('batch.schema is unsupported')
  if (batch.contractVersion !== EXECUTION_SUPERVISOR_CONTRACT_VERSION) {
    errors.push('batch.contractVersion is unsupported')
  }
  if (typeof batch.batchId !== 'string' || !IDENTIFIER_RE.test(batch.batchId)) {
    errors.push('batch.batchId is invalid')
  }
  if (typeof batch.contractHash !== 'string' || !SHA256_RE.test(batch.contractHash)) {
    errors.push('batch.contractHash must be SHA-256')
  }
  if (!Number.isSafeInteger(batch.firstSequence) || Number(batch.firstSequence) <= 0) {
    errors.push('batch.firstSequence must be a positive safe integer')
  }
  if (!Number.isSafeInteger(batch.lastSequence) || Number(batch.lastSequence) <= 0) {
    errors.push('batch.lastSequence must be a positive safe integer')
  }
  if (typeof batch.createdAt !== 'string' || !Number.isFinite(Date.parse(batch.createdAt))) {
    errors.push('batch.createdAt must be ISO-8601')
  }
  const identity = batch.identity as SupervisionIdentityV01 | undefined
  if (!recordOf(identity)) errors.push('batch.identity must be an object')
  const events = Array.isArray(batch.events) ? batch.events : []
  if (!Array.isArray(batch.events)) errors.push('batch.events must be an array')
  if (events.length === 0) errors.push('batch.events cannot be empty')
  if (events.length > EXECUTION_SUPERVISOR_LIMITS.maxBatchEvents) {
    errors.push(`batch.events exceeds ${EXECUTION_SUPERVISOR_LIMITS.maxBatchEvents}`)
  }

  for (const [index, candidate] of events.entries()) {
    const validation = validateExecutionEvent(candidate)
    if (!validation.valid) {
      errors.push(...validation.errors.map(error => `batch.events[${index}]: ${error}`))
      continue
    }
    const event = candidate as ExecutionEventV01
    if (identity && !sameIdentity(identity, event.identity)) {
      errors.push(`batch.events[${index}] identity mismatch`)
    }
    if (event.integrity.contractHash !== batch.contractHash) {
      errors.push(`batch.events[${index}] contractHash mismatch`)
    }
    const expectedSequence = Number(batch.firstSequence) + index
    if (event.sequence !== expectedSequence) {
      errors.push(`batch.events[${index}] expected sequence ${expectedSequence}, received ${event.sequence}`)
    }
    if (index > 0) {
      const previous = events[index - 1] as ExecutionEventV01
      if (event.integrity.previousEventHash !== previous.integrity.eventHash) {
        errors.push(`batch.events[${index}] breaks the event hash chain`)
      }
    }
  }
  if (events.length > 0) {
    const expectedLast = Number(batch.firstSequence) + events.length - 1
    if (batch.lastSequence !== expectedLast) {
      errors.push(`batch.lastSequence must equal ${expectedLast}`)
    }
  }
  return { valid: errors.length === 0, errors }
}

export const assertExecutionEventBatch = (value: unknown): ExecutionEventBatchV01 => {
  const result = validateExecutionEventBatch(value)
  if (!result.valid) throw new Error(`Execution Event Batch validation failed: ${result.errors.join('; ')}`)
  return value as ExecutionEventBatchV01
}
