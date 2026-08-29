import {
  type ExecutionEventEnvelopeV01,
  type ExecutionReplayCursorV01,
  type ExecutionReplayPageV01,
  type ExecutionReplayRequestV01,
} from '../contracts.js'
import { hashCanonicalJson } from '../hash.js'
import { validateExecutionReplayCursor } from '../validation.js'
import {
  ExecutionEventStoreError,
  parseStoreRecord,
  type StoreManifestV01,
  type StoreRecordV01,
} from './store-format.js'

export interface ReplayStateV01 {
  readonly records: readonly StoreRecordV01[]
  readonly eventHashesById: ReadonlyMap<string, string>
  readonly cursor: ExecutionReplayCursorV01
}

const assertEventBinding = (
  event: ExecutionEventEnvelopeV01,
  manifest: StoreManifestV01,
  offset?: number,
): void => {
  const expected = {
    requestId: manifest.binding.requestId,
    runtimeId: manifest.binding.runtimeId,
    turnId: manifest.binding.turnId,
    projectId: manifest.binding.contract.projectId,
    taskId: manifest.binding.contract.taskId,
    agentId: manifest.binding.contract.agentId,
    contextHash: manifest.binding.contract.contextHash,
  }
  for (const [field, wanted] of Object.entries(expected)) {
    const actual = event[field as keyof typeof expected]
    if (actual !== wanted) {
      throw new ExecutionEventStoreError(
        'EVENT_BINDING_MISMATCH',
        `Execution event ${field} does not match the immutable store binding`,
        {
          field: `event.${field}`,
          expected: wanted,
          actual,
          sequence: event.sequence,
          ...(offset === undefined ? {} : { offset }),
        },
      )
    }
  }
}

export const scanEventLog = (
  content: string,
  manifest: StoreManifestV01,
): ReplayStateV01 => {
  if (content.length > 0 && !content.endsWith('\n')) {
    const lastNewline = content.lastIndexOf('\n')
    const offset = Buffer.byteLength(content.slice(0, lastNewline + 1), 'utf8')
    throw new ExecutionEventStoreError(
      'STORE_TRUNCATED_RECORD',
      'Event log ends with a partial record',
      { field: 'events', offset },
    )
  }
  const lines = content.length === 0 ? [] : content.slice(0, -1).split('\n')
  if (lines.length > manifest.limits.maxEvents) {
    throw new ExecutionEventStoreError(
      'STORE_LIMIT_EXCEEDED',
      'Persisted event count exceeds maxEvents',
      {
        field: 'events',
        expected: manifest.limits.maxEvents,
        actual: lines.length,
      },
    )
  }
  const records: StoreRecordV01[] = []
  const eventHashesById = new Map<string, string>()
  let offset = 0
  let previousStateHash = manifest.genesisStateHash
  lines.forEach((line, index) => {
    if (!line) {
      throw new ExecutionEventStoreError(
        'STORE_INVALID_CANONICAL_JSON',
        'Event log contains an empty record',
        { field: 'events', offset },
      )
    }
    const record = parseStoreRecord(line, offset)
    const expectedSequence = index + 1
    if (record.event.sequence !== expectedSequence) {
      throw new ExecutionEventStoreError(
        'SEQUENCE_GAP',
        'Persisted event sequence is not contiguous',
        {
          field: 'event.sequence',
          expected: expectedSequence,
          actual: record.event.sequence,
          sequence: record.event.sequence,
          offset,
        },
      )
    }
    assertEventBinding(record.event, manifest, offset)
    const priorHash = eventHashesById.get(record.event.eventId)
    if (priorHash !== undefined) {
      throw new ExecutionEventStoreError(
        'EVENT_ID_INTEGRITY_CONFLICT',
        'Persisted eventId is not unique',
        {
          field: 'event.eventId',
          actual: record.event.eventId,
          sequence: record.event.sequence,
          offset,
        },
      )
    }
    if (record.previousStateHash !== previousStateHash) {
      throw new ExecutionEventStoreError(
        'STORE_EVENT_CHAIN_MISMATCH',
        'Persisted record does not continue the state hash chain',
        {
          field: 'record.previousStateHash',
          expected: previousStateHash,
          actual: record.previousStateHash,
          sequence: record.event.sequence,
          offset,
        },
      )
    }
    records.push(record)
    eventHashesById.set(record.event.eventId, record.envelopeHash)
    previousStateHash = record.stateHash
    offset += Buffer.byteLength(line, 'utf8') + 1
  })
  return {
    records,
    eventHashesById,
    cursor: {
      sequence: records.length,
      stateHash: previousStateHash,
    },
  }
}

const assertReplayCursor = (
  cursor: ExecutionReplayCursorV01,
  state: ReplayStateV01,
  genesisStateHash: string,
): void => {
  const validation = validateExecutionReplayCursor(cursor)
  if (!validation.valid) {
    const first = validation.issues[0]
    throw new ExecutionEventStoreError(
      'STORE_CURSOR_INVALID',
      'Replay cursor is invalid',
      {
        field: first?.path ?? 'cursor',
        ...(first === undefined ? {} : { sourceCode: first.code }),
      },
    )
  }
  if (cursor.sequence > state.records.length) {
    throw new ExecutionEventStoreError(
      'STORE_CURSOR_INVALID',
      'Replay cursor sequence is beyond the durable event tail',
      {
        field: 'cursor.sequence',
        expected: state.records.length,
        actual: cursor.sequence,
      },
    )
  }
  const expectedHash = cursor.sequence === 0
    ? genesisStateHash
    : state.records[cursor.sequence - 1]!.stateHash
  if (cursor.stateHash !== expectedHash) {
    throw new ExecutionEventStoreError(
      'STORE_CURSOR_INVALID',
      'Replay cursor stateHash does not identify the requested sequence',
      {
        field: 'cursor.stateHash',
        expected: expectedHash,
        actual: cursor.stateHash,
        sequence: cursor.sequence,
      },
    )
  }
}

export const replayFromState = (
  request: ExecutionReplayRequestV01,
  state: ReplayStateV01,
  manifest: StoreManifestV01,
): ExecutionReplayPageV01 => {
  if (!Number.isSafeInteger(request.limit) || request.limit < 1
      || request.limit > manifest.limits.maxReplayEvents) {
    throw new ExecutionEventStoreError(
      'STORE_LIMIT_EXCEEDED',
      'Replay limit must be a positive safe integer within maxReplayEvents',
      {
        field: 'request.limit',
        expected: manifest.limits.maxReplayEvents,
        actual: request.limit,
      },
    )
  }
  const after = request.after ?? {
    sequence: 0,
    stateHash: manifest.genesisStateHash,
  }
  assertReplayCursor(after, state, manifest.genesisStateHash)
  const selected = state.records.slice(after.sequence, after.sequence + request.limit)
  const last = selected.at(-1)
  const cursor = last === undefined
    ? after
    : { sequence: last.event.sequence, stateHash: last.stateHash }
  return {
    events: selected.map(record => record.event),
    cursor,
    hasMore: cursor.sequence < state.records.length,
  }
}

export const fullEnvelopeHash = (event: ExecutionEventEnvelopeV01): string =>
  hashCanonicalJson(event)

export { assertEventBinding }
