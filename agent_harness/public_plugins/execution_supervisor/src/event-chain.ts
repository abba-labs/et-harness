import type {
  ContractValidationIssue,
  ExecutionEvent,
  TaskSupervisionContract,
} from './contracts.js'
import { EXECUTION_SUPERVISOR_LIMITS } from './limits.js'
import { validateExecutionEvent } from './validation.js'

export interface ExecutionReplayCursor {
  readonly nextSequence: number
  readonly chainHead?: string
}

export interface ExecutionEventBatchValidation {
  readonly valid: boolean
  readonly acceptedEvents: readonly ExecutionEvent[]
  readonly nextCursor: ExecutionReplayCursor
  readonly issues: readonly ContractValidationIssue[]
}

export const validateExecutionEventBatch = (
  events: readonly ExecutionEvent[],
  contract: TaskSupervisionContract,
  cursor: ExecutionReplayCursor,
): ExecutionEventBatchValidation => {
  const issues: ContractValidationIssue[] = []
  if (!Number.isSafeInteger(cursor.nextSequence) || cursor.nextSequence < 0) {
    return {
      valid: false,
      acceptedEvents: [],
      nextCursor: cursor,
      issues: [{
        path: 'cursor.nextSequence',
        code: 'RANGE',
        message: 'nextSequence must be one non-negative safe integer',
      }],
    }
  }
  if (events.length > EXECUTION_SUPERVISOR_LIMITS.maxBatchEvents) {
    return {
      valid: false,
      acceptedEvents: [],
      nextCursor: cursor,
      issues: [{
        path: 'events',
        code: 'LIMIT',
        message: `event batch exceeds maximum ${EXECUTION_SUPERVISOR_LIMITS.maxBatchEvents}`,
      }],
    }
  }

  const eventIds = new Set<string>()
  let expectedSequence = cursor.nextSequence
  let expectedPreviousHash = cursor.chainHead
  const accepted: ExecutionEvent[] = []

  for (let index = 0; index < events.length; index += 1) {
    const event = events[index]!
    const validation = validateExecutionEvent(event, contract)
    for (const item of validation.issues) {
      issues.push({
        path: `events[${index}].${item.path}`,
        code: item.code,
        message: item.message,
      })
    }
    if (eventIds.has(event.eventId)) {
      issues.push({
        path: `events[${index}].eventId`,
        code: 'DUPLICATE',
        message: `duplicate eventId in batch: ${event.eventId}`,
      })
    }
    eventIds.add(event.eventId)
    if (event.sequence !== expectedSequence) {
      issues.push({
        path: `events[${index}].sequence`,
        code: event.sequence < expectedSequence ? 'REPLAY' : 'EVENT_GAP',
        message: `expected sequence ${expectedSequence}, received ${event.sequence}`,
      })
    }
    if (expectedPreviousHash) {
      if (event.previousEventHash !== expectedPreviousHash) {
        issues.push({
          path: `events[${index}].previousEventHash`,
          code: 'EVENT_CONFLICT',
          message: 'event does not extend the accepted hash chain',
        })
      }
    } else if (event.previousEventHash !== undefined) {
      issues.push({
        path: `events[${index}].previousEventHash`,
        code: 'EVENT_CONFLICT',
        message: 'first event for an empty cursor must not claim a previous hash',
      })
    }
    if (validation.valid && event.sequence === expectedSequence) {
      accepted.push(event)
      expectedSequence += 1
      expectedPreviousHash = event.eventHash
    }
  }

  return {
    valid: issues.length === 0,
    acceptedEvents: issues.length === 0 ? accepted : [],
    nextCursor: issues.length === 0
      ? {
          nextSequence: expectedSequence,
          ...(expectedPreviousHash ? { chainHead: expectedPreviousHash } : {}),
        }
      : cursor,
    issues,
  }
}
