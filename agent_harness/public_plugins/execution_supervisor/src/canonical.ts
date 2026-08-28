import { createHash } from 'node:crypto'
import type {
  ExecutionEvent,
  ExecutionEventDraft,
  TaskSupervisionContract,
} from './contracts.js'

const canonicalize = (value: unknown, seen: Set<object>): unknown => {
  if (
    value === null
    || typeof value === 'string'
    || typeof value === 'boolean'
  ) {
    return value
  }
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) {
      throw new TypeError('Canonical JSON does not support non-finite numbers')
    }
    return value
  }
  if (
    typeof value === 'undefined'
    || typeof value === 'bigint'
    || typeof value === 'function'
    || typeof value === 'symbol'
  ) {
    throw new TypeError(`Canonical JSON does not support ${typeof value}`)
  }
  if (typeof value !== 'object') return String(value)
  if (seen.has(value)) throw new TypeError('Canonical JSON does not support cycles')
  seen.add(value)
  try {
    if (Array.isArray(value)) {
      return value.map(item => canonicalize(item, seen))
    }
    const record = value as Record<string, unknown>
    const output: Record<string, unknown> = {}
    for (const key of Object.keys(record).sort()) {
      const item = record[key]
      if (item === undefined) continue
      output[key] = canonicalize(item, seen)
    }
    return output
  } finally {
    seen.delete(value)
  }
}

export const canonicalJson = (value: unknown): string =>
  JSON.stringify(canonicalize(value, new Set<object>()))

export const sha256Text = (value: string): string =>
  createHash('sha256').update(value).digest('hex')

export const sha256Canonical = (value: unknown): string =>
  sha256Text(canonicalJson(value))

export const taskSupervisionContractHash = (
  contract: Omit<TaskSupervisionContract, 'contractHash'>,
): string => sha256Canonical(contract)

export const executionEventPayloadHash = (
  payload: ExecutionEventDraft['payload'],
): string => sha256Canonical(payload)

export const executionEventHash = (
  event: Omit<ExecutionEvent, 'eventHash'>,
): string => sha256Canonical(event)

export const sealExecutionEvent = (
  draft: Omit<ExecutionEventDraft, 'payloadHash'> & { readonly payloadHash?: string },
): ExecutionEvent => {
  const payloadHash = draft.payloadHash ?? executionEventPayloadHash(draft.payload)
  const normalized: ExecutionEventDraft = {
    ...draft,
    payloadHash,
  }
  return {
    ...normalized,
    eventHash: executionEventHash(normalized),
  }
}

export const verifyExecutionEventIntegrity = (
  event: ExecutionEvent,
): boolean => event.payloadHash === executionEventPayloadHash(event.payload)
  && event.eventHash === executionEventHash({
    schema: event.schema,
    contractVersion: event.contractVersion,
    correlation: event.correlation,
    contractHash: event.contractHash,
    eventId: event.eventId,
    sequence: event.sequence,
    emittedAt: event.emittedAt,
    source: event.source,
    kind: event.kind,
    ...(event.previousEventHash
      ? { previousEventHash: event.previousEventHash }
      : {}),
    payload: event.payload,
    payloadHash: event.payloadHash,
  })
