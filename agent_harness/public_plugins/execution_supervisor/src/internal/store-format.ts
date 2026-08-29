import {
  type ExecutionEventEnvelopeV01,
  type ExecutionEventStoreBindingV01,
  type ExecutionEventStoreLimitsV01,
  type ExecutionStoreIssueCode,
} from '../contracts.js'
import { canonicalJson, hashCanonicalJson } from '../hash.js'
import {
  validateExecutionEventEnvelope,
  validateExecutionEventStoreBinding,
  validateExecutionEventStoreLimits,
} from '../validation.js'

export const STORE_MANIFEST_SCHEMA =
  'agent-harness.execution-event-store-manifest.v0.1' as const
export const STORE_RECORD_SCHEMA =
  'agent-harness.execution-event-store-record.v0.1' as const
const STORE_GENESIS_SCHEMA =
  'agent-harness.execution-event-store-genesis.v0.1' as const

export interface StoreErrorDetails {
  readonly field?: string
  readonly expected?: string | number
  readonly actual?: string | number
  readonly sequence?: number
  readonly offset?: number
  readonly sourceCode?: string
  readonly cause?: unknown
}

export class ExecutionEventStoreError extends Error {
  readonly code: ExecutionStoreIssueCode
  readonly field?: string
  readonly expected?: string | number
  readonly actual?: string | number
  readonly sequence?: number
  readonly offset?: number
  readonly sourceCode?: string

  constructor(
    code: ExecutionStoreIssueCode,
    message: string,
    details: StoreErrorDetails = {},
  ) {
    super(message, 'cause' in details ? { cause: details.cause } : undefined)
    this.name = 'ExecutionEventStoreError'
    this.code = code
    if (details.field !== undefined) this.field = details.field
    if (details.expected !== undefined) this.expected = details.expected
    if (details.actual !== undefined) this.actual = details.actual
    if (details.sequence !== undefined) this.sequence = details.sequence
    if (details.offset !== undefined) this.offset = details.offset
    if (details.sourceCode !== undefined) this.sourceCode = details.sourceCode
  }
}

export interface StoreManifestV01 {
  readonly schema: typeof STORE_MANIFEST_SCHEMA
  readonly binding: ExecutionEventStoreBindingV01
  readonly bindingHash: string
  readonly contractHash: string
  readonly limits: ExecutionEventStoreLimitsV01
  readonly genesisStateHash: string
}

interface StoreRecordCoreV01 {
  readonly schema: typeof STORE_RECORD_SCHEMA
  readonly event: ExecutionEventEnvelopeV01
  readonly envelopeHash: string
  readonly previousStateHash: string
  readonly acceptedAt: string
}

export interface StoreRecordV01 extends StoreRecordCoreV01 {
  readonly stateHash: string
}

const objectRecord = (value: unknown): Record<string, unknown> | undefined =>
  typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : undefined

const deepFreeze = <T>(value: T): T => {
  if (typeof value !== 'object' || value === null || Object.isFrozen(value)) return value
  for (const item of Object.values(value as Record<string, unknown>)) deepFreeze(item)
  return Object.freeze(value)
}

export const immutableCanonicalClone = <T>(value: T): T =>
  deepFreeze(JSON.parse(canonicalJson(value)) as T)

const requireExactKeys = (
  value: Record<string, unknown>,
  expected: readonly string[],
  label: string,
  offset?: number,
): void => {
  const actual = Object.keys(value).sort()
  const wanted = [...expected].sort()
  if (actual.length !== wanted.length || actual.some((key, index) => key !== wanted[index])) {
    throw new ExecutionEventStoreError(
      'STORE_INVALID_CANONICAL_JSON',
      `${label} has unsupported or missing fields`,
      {
        field: label,
        expected: wanted.join(','),
        actual: actual.join(','),
        ...(offset === undefined ? {} : { offset }),
      },
    )
  }
}

const requireHash = (
  value: unknown,
  field: string,
  offset?: number,
): string => {
  if (typeof value !== 'string' || !/^[0-9a-f]{64}$/.test(value)) {
    throw new ExecutionEventStoreError(
      'STORE_INVALID_CANONICAL_JSON',
      `${field} must be a lowercase SHA-256 digest`,
      { field, ...(offset === undefined ? {} : { offset }) },
    )
  }
  return value
}

const parseCanonicalObject = (
  text: string,
  label: string,
  offset?: number,
): Record<string, unknown> => {
  let parsed: unknown
  try {
    parsed = JSON.parse(text) as unknown
  } catch (cause) {
    throw new ExecutionEventStoreError(
      'STORE_INVALID_CANONICAL_JSON',
      `${label} is not valid JSON`,
      { field: label, ...(offset === undefined ? {} : { offset }), cause },
    )
  }
  const record = objectRecord(parsed)
  if (!record) {
    throw new ExecutionEventStoreError(
      'STORE_INVALID_CANONICAL_JSON',
      `${label} must be a JSON object`,
      { field: label, ...(offset === undefined ? {} : { offset }) },
    )
  }
  let canonical: string
  try {
    canonical = canonicalJson(record)
  } catch (cause) {
    throw new ExecutionEventStoreError(
      'STORE_INVALID_CANONICAL_JSON',
      `${label} is not canonical JSON`,
      { field: label, ...(offset === undefined ? {} : { offset }), cause },
    )
  }
  if (canonical !== text) {
    throw new ExecutionEventStoreError(
      'STORE_INVALID_CANONICAL_JSON',
      `${label} is not in canonical JSON form`,
      { field: label, ...(offset === undefined ? {} : { offset }) },
    )
  }
  return record
}

export const createStoreManifest = (
  binding: ExecutionEventStoreBindingV01,
  limits: ExecutionEventStoreLimitsV01,
): StoreManifestV01 => {
  const immutableBinding = immutableCanonicalClone(binding)
  const immutableLimits = immutableCanonicalClone(limits)
  const bindingHash = hashCanonicalJson(immutableBinding)
  const contractHash = hashCanonicalJson(immutableBinding.contract)
  const genesisStateHash = hashCanonicalJson({
    schema: STORE_GENESIS_SCHEMA,
    bindingHash,
    contractHash,
    limits: immutableLimits,
  })
  return deepFreeze({
    schema: STORE_MANIFEST_SCHEMA,
    binding: immutableBinding,
    bindingHash,
    contractHash,
    limits: immutableLimits,
    genesisStateHash,
  })
}

export const serializeStoreManifest = (manifest: StoreManifestV01): string =>
  `${canonicalJson(manifest)}\n`

export const parseStoreManifest = (text: string): StoreManifestV01 => {
  if (!text.endsWith('\n')) {
    throw new ExecutionEventStoreError(
      'STORE_TRUNCATED_RECORD',
      'Store manifest is missing its terminating newline',
      { field: 'manifest' },
    )
  }
  const body = text.slice(0, -1)
  if (!body || body.includes('\n') || body.includes('\r')) {
    throw new ExecutionEventStoreError(
      'STORE_INVALID_CANONICAL_JSON',
      'Store manifest must contain exactly one canonical JSON record',
      { field: 'manifest' },
    )
  }
  const record = parseCanonicalObject(body, 'manifest')
  requireExactKeys(record, [
    'schema',
    'binding',
    'bindingHash',
    'contractHash',
    'limits',
    'genesisStateHash',
  ], 'manifest')
  if (record.schema !== STORE_MANIFEST_SCHEMA) {
    throw new ExecutionEventStoreError(
      'STORE_INVALID_CANONICAL_JSON',
      `Unsupported store manifest schema ${String(record.schema)}`,
      { field: 'manifest.schema' },
    )
  }
  const bindingValidation = validateExecutionEventStoreBinding(record.binding)
  if (!bindingValidation.valid) {
    const first = bindingValidation.issues[0]
    throw new ExecutionEventStoreError(
      'STORE_BINDING_MISMATCH',
      'Persisted store binding is invalid',
      {
        field: first?.path ?? 'manifest.binding',
        ...(first === undefined ? {} : { sourceCode: first.code }),
      },
    )
  }
  const limitsValidation = validateExecutionEventStoreLimits(record.limits)
  if (!limitsValidation.valid) {
    const first = limitsValidation.issues[0]
    throw new ExecutionEventStoreError(
      'STORE_LIMIT_EXCEEDED',
      'Persisted store limits are invalid',
      {
        field: first?.path ?? 'manifest.limits',
        ...(first === undefined ? {} : { sourceCode: first.code }),
      },
    )
  }
  const bindingHash = requireHash(record.bindingHash, 'manifest.bindingHash')
  const contractHash = requireHash(record.contractHash, 'manifest.contractHash')
  const genesisStateHash = requireHash(record.genesisStateHash, 'manifest.genesisStateHash')
  const manifest: StoreManifestV01 = {
    schema: STORE_MANIFEST_SCHEMA,
    binding: bindingValidation.value,
    bindingHash,
    contractHash,
    limits: limitsValidation.value,
    genesisStateHash,
  }
  const expected = createStoreManifest(manifest.binding, manifest.limits)
  for (const field of ['bindingHash', 'contractHash', 'genesisStateHash'] as const) {
    if (manifest[field] !== expected[field]) {
      throw new ExecutionEventStoreError(
        'STORE_STATE_HASH_MISMATCH',
        `Persisted ${field} does not match the canonical manifest content`,
        { field: `manifest.${field}`, expected: expected[field], actual: manifest[field] },
      )
    }
  }
  return immutableCanonicalClone(manifest)
}

export const createStoreRecord = (
  event: ExecutionEventEnvelopeV01,
  previousStateHash: string,
  acceptedAt: string,
): StoreRecordV01 => {
  const immutableEvent = immutableCanonicalClone(event)
  const core: StoreRecordCoreV01 = {
    schema: STORE_RECORD_SCHEMA,
    event: immutableEvent,
    envelopeHash: hashCanonicalJson(immutableEvent),
    previousStateHash,
    acceptedAt,
  }
  return deepFreeze({ ...core, stateHash: hashCanonicalJson(core) })
}

export const serializeStoreRecord = (record: StoreRecordV01): string =>
  `${canonicalJson(record)}\n`

export const parseStoreRecord = (
  text: string,
  offset: number,
): StoreRecordV01 => {
  const record = parseCanonicalObject(text, 'event record', offset)
  requireExactKeys(record, [
    'schema',
    'event',
    'envelopeHash',
    'previousStateHash',
    'acceptedAt',
    'stateHash',
  ], 'event record', offset)
  if (record.schema !== STORE_RECORD_SCHEMA) {
    throw new ExecutionEventStoreError(
      'STORE_INVALID_CANONICAL_JSON',
      `Unsupported store record schema ${String(record.schema)}`,
      { field: 'record.schema', offset },
    )
  }
  const eventValidation = validateExecutionEventEnvelope(record.event)
  if (!eventValidation.valid) {
    const first = eventValidation.issues[0]
    throw new ExecutionEventStoreError(
      'EVENT_INVALID',
      'Persisted execution event is invalid',
      {
        field: first?.path ?? 'record.event',
        offset,
        ...(first === undefined ? {} : { sourceCode: first.code }),
      },
    )
  }
  const envelopeHash = requireHash(record.envelopeHash, 'record.envelopeHash', offset)
  const previousStateHash = requireHash(record.previousStateHash, 'record.previousStateHash', offset)
  const stateHash = requireHash(record.stateHash, 'record.stateHash', offset)
  if (typeof record.acceptedAt !== 'string' || Number.isNaN(Date.parse(record.acceptedAt))) {
    throw new ExecutionEventStoreError(
      'STORE_INVALID_CANONICAL_JSON',
      'record.acceptedAt must be an ISO-compatible timestamp',
      { field: 'record.acceptedAt', offset },
    )
  }
  const result: StoreRecordV01 = {
    schema: STORE_RECORD_SCHEMA,
    event: eventValidation.value,
    envelopeHash,
    previousStateHash,
    acceptedAt: record.acceptedAt,
    stateHash,
  }
  const expectedEnvelopeHash = hashCanonicalJson(result.event)
  if (result.envelopeHash !== expectedEnvelopeHash) {
    throw new ExecutionEventStoreError(
      'EVENT_ID_INTEGRITY_CONFLICT',
      'Persisted envelope hash does not match its full event envelope',
      {
        field: 'record.envelopeHash',
        expected: expectedEnvelopeHash,
        actual: result.envelopeHash,
        sequence: result.event.sequence,
        offset,
      },
    )
  }
  const core: StoreRecordCoreV01 = {
    schema: result.schema,
    event: result.event,
    envelopeHash: result.envelopeHash,
    previousStateHash: result.previousStateHash,
    acceptedAt: result.acceptedAt,
  }
  const expectedStateHash = hashCanonicalJson(core)
  if (result.stateHash !== expectedStateHash) {
    throw new ExecutionEventStoreError(
      'STORE_STATE_HASH_MISMATCH',
      'Persisted state hash does not match its canonical record',
      {
        field: 'record.stateHash',
        expected: expectedStateHash,
        actual: result.stateHash,
        sequence: result.event.sequence,
        offset,
      },
    )
  }
  return immutableCanonicalClone(result)
}
