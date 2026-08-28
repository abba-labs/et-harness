import {
  EXECUTION_RECEIPT_SCHEMA,
  EXECUTION_SUPERVISOR_CONTRACT_VERSION,
  EXECUTION_SUPERVISOR_LIMITS,
  SUPERVISION_VIOLATION_SCHEMA,
  type ExecutionReceiptV01,
  type SupervisionViolationV01,
} from './contracts.js'
import type { SupervisionValidationResult } from './validation.js'

const IDENTIFIER_RE = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$/
const SHA256_RE = /^[0-9a-f]{64}$/

const recordOf = (value: unknown): Record<string, unknown> | undefined =>
  typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : undefined

const push = (errors: string[], condition: boolean, message: string): void => {
  if (!condition) errors.push(message)
}

const isIdentifier = (value: unknown): value is string =>
  typeof value === 'string' && IDENTIFIER_RE.test(value)

const isSha256 = (value: unknown): value is string =>
  typeof value === 'string' && SHA256_RE.test(value)

const isIsoTimestamp = (value: unknown): value is string =>
  typeof value === 'string'
  && /^\d{4}-\d{2}-\d{2}T/.test(value)
  && Number.isFinite(Date.parse(value))

const isStringArray = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every(item => typeof item === 'string')

const validateIdentity = (
  value: unknown,
  path: string,
  errors: string[],
): void => {
  const identity = recordOf(value)
  push(errors, Boolean(identity), `${path} must be an object`)
  if (!identity) return
  for (const field of ['runtimeId', 'taskId', 'turnId', 'agentId', 'projectId'] as const) {
    push(errors, isIdentifier(identity[field]), `${path}.${field} must be a stable identifier`)
  }
}

const validateRefs = (
  value: unknown,
  path: string,
  errors: string[],
  limit = 256,
): void => {
  push(errors, isStringArray(value), `${path} must be a string array`)
  if (!isStringArray(value)) return
  push(errors, value.length <= limit, `${path} exceeds limit ${limit}`)
  push(errors, value.every(item => item.length > 0 && item.length <= 1_024),
    `${path} contains an invalid reference`)
}

export const validateExecutionReceipt = (
  value: unknown,
): SupervisionValidationResult => {
  const errors: string[] = []
  const receipt = recordOf(value)
  push(errors, Boolean(receipt), 'receipt must be an object')
  if (!receipt) return { valid: false, errors }
  push(errors, receipt.schema === EXECUTION_RECEIPT_SCHEMA, 'receipt.schema is unsupported')
  push(errors, receipt.contractVersion === EXECUTION_SUPERVISOR_CONTRACT_VERSION,
    'receipt.contractVersion is unsupported')
  push(errors, isIdentifier(receipt.receiptId), 'receipt.receiptId is invalid')
  validateIdentity(receipt.identity, 'receipt.identity', errors)
  push(errors, isIdentifier(receipt.eventId), 'receipt.eventId is invalid')
  push(errors, Number.isSafeInteger(receipt.sequence) && Number(receipt.sequence) > 0,
    'receipt.sequence is invalid')
  push(errors, isSha256(receipt.eventHash), 'receipt.eventHash must be SHA-256')
  push(errors, ['ACCEPTED', 'DUPLICATE', 'REJECTED'].includes(String(receipt.disposition)),
    'receipt.disposition is invalid')
  push(errors, Number.isSafeInteger(receipt.ledgerVersionBefore)
    && Number(receipt.ledgerVersionBefore) >= 0,
  'receipt.ledgerVersionBefore is invalid')
  push(errors, Number.isSafeInteger(receipt.ledgerVersionAfter)
    && Number(receipt.ledgerVersionAfter) >= 0,
  'receipt.ledgerVersionAfter is invalid')
  validateRefs(receipt.changedObligationIds, 'receipt.changedObligationIds', errors)
  validateRefs(receipt.violationIds, 'receipt.violationIds', errors)
  push(errors, isIsoTimestamp(receipt.receivedAt), 'receipt.receivedAt must be ISO-8601')
  if (receipt.reason !== undefined) {
    push(errors, typeof receipt.reason === 'string'
      && receipt.reason.length <= EXECUTION_SUPERVISOR_LIMITS.maxViolationDetailsChars,
    'receipt.reason is invalid')
  }
  if (receipt.disposition === 'REJECTED') {
    push(errors, typeof receipt.reason === 'string' && receipt.reason.length > 0,
      'REJECTED receipt requires a reason')
  }
  if (receipt.disposition === 'DUPLICATE') {
    push(errors, receipt.ledgerVersionAfter === receipt.ledgerVersionBefore,
      'DUPLICATE receipt cannot advance the Ledger')
  }
  return { valid: errors.length === 0, errors }
}

export const validateSupervisionViolation = (
  value: unknown,
): SupervisionValidationResult => {
  const errors: string[] = []
  const violation = recordOf(value)
  push(errors, Boolean(violation), 'violation must be an object')
  if (!violation) return { valid: false, errors }
  push(errors, violation.schema === SUPERVISION_VIOLATION_SCHEMA,
    'violation.schema is unsupported')
  push(errors, isIdentifier(violation.violationId), 'violation.violationId is invalid')
  validateIdentity(violation.identity, 'violation.identity', errors)
  push(errors, typeof violation.kind === 'string' && violation.kind.length > 0,
    'violation.kind is required')
  push(errors, ['WARNING', 'ERROR', 'FATAL'].includes(String(violation.severity)),
    'violation.severity is invalid')
  push(errors, isIsoTimestamp(violation.detectedAt),
    'violation.detectedAt must be ISO-8601')
  validateRefs(violation.eventRefs, 'violation.eventRefs', errors)
  validateRefs(violation.obligationIds, 'violation.obligationIds', errors)
  push(errors, typeof violation.details === 'string'
    && violation.details.length > 0
    && violation.details.length <= EXECUTION_SUPERVISOR_LIMITS.maxViolationDetailsChars,
  'violation.details is invalid')
  push(errors, typeof violation.blocking === 'boolean', 'violation.blocking must be boolean')
  if (violation.severity === 'WARNING') {
    push(errors, violation.blocking === false,
      'WARNING violation cannot block completion in v0.1')
  }
  return { valid: errors.length === 0, errors }
}

export const assertExecutionReceipt = (value: unknown): ExecutionReceiptV01 => {
  const result = validateExecutionReceipt(value)
  if (!result.valid) throw new Error(`Execution Receipt validation failed: ${result.errors.join('; ')}`)
  return value as ExecutionReceiptV01
}

export const assertSupervisionViolation = (value: unknown): SupervisionViolationV01 => {
  const result = validateSupervisionViolation(value)
  if (!result.valid) throw new Error(`Supervision Violation validation failed: ${result.errors.join('; ')}`)
  return value as SupervisionViolationV01
}
