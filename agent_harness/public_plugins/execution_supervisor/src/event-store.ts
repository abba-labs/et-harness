import {
  mkdir,
  open,
  readFile,
  stat,
  type FileHandle,
} from 'node:fs/promises'
import { isAbsolute, join } from 'node:path'
import {
  MAX_TASK_SUPERVISION_CONTRACT_BYTES,
  type CreateFileExecutionEventStoreInputV01,
  type ExecutionEventAcceptanceV01,
  type ExecutionEventEnvelopeV01,
  type ExecutionEventStoreBindingV01,
  type ExecutionEventStoreV01,
  type ExecutionReplayCursorV01,
  type ExecutionReplayPageV01,
  type ExecutionReplayRequestV01,
  type ExecutionStoreIssueV01,
  type OpenFileExecutionEventStoreInputV01,
} from './contracts.js'
import { hashCanonicalJson } from './hash.js'
import {
  assertEventBinding,
  fullEnvelopeHash,
  replayFromState,
  scanEventLog,
  type ReplayStateV01,
} from './internal/replay-state.js'
import {
  createStoreManifest,
  createStoreRecord,
  ExecutionEventStoreError,
  immutableCanonicalClone,
  parseStoreManifest,
  serializeStoreManifest,
  serializeStoreRecord,
  type StoreManifestV01,
  type StoreRecordV01,
} from './internal/store-format.js'
import {
  validateExecutionEventEnvelope,
  validateExecutionEventStoreBinding,
  validateExecutionEventStoreLimits,
} from './validation.js'

const MANIFEST_FILE = 'manifest.json'
const EVENTS_FILE = 'events.jsonl'
const MAX_MANIFEST_BYTES = MAX_TASK_SUPERVISION_CONTRACT_BYTES + (256 * 1024)

interface FileSnapshot {
  readonly size: number
  readonly mtimeMs: number
  readonly ctimeMs: number
  readonly ino: number
}

const errorCode = (error: unknown): string | undefined =>
  typeof error === 'object' && error !== null && 'code' in error
    ? String((error as { code?: unknown }).code)
    : undefined

const sourceCodeDetails = (error: unknown): { readonly sourceCode?: string } => {
  const code = errorCode(error)
  return code === undefined ? {} : { sourceCode: code }
}

const snapshotFile = async (file: string): Promise<FileSnapshot> => {
  const value = await stat(file)
  return {
    size: value.size,
    mtimeMs: value.mtimeMs,
    ctimeMs: value.ctimeMs,
    ino: value.ino,
  }
}

const sameSnapshot = (left: FileSnapshot, right: FileSnapshot): boolean =>
  left.size === right.size
  && left.mtimeMs === right.mtimeMs
  && left.ctimeMs === right.ctimeMs
  && left.ino === right.ino

const requireAbsoluteDirectory = (directory: unknown): string => {
  if (typeof directory !== 'string' || !directory || directory.includes('\0') || !isAbsolute(directory)) {
    throw new ExecutionEventStoreError(
      'STORE_INVALID_LOCATION',
      'Store directory must be a caller-controlled absolute path',
      { field: 'directory' },
    )
  }
  return directory
}

const durableExclusiveWrite = async (file: string, content: string): Promise<void> => {
  let handle: FileHandle | undefined
  try {
    handle = await open(file, 'wx')
    await handle.writeFile(content, 'utf8')
    await handle.sync()
  } finally {
    await handle?.close()
  }
}

const issueFromError = (error: ExecutionEventStoreError): ExecutionStoreIssueV01 => ({
  code: error.code,
  message: error.message,
  ...(error.field === undefined ? {} : { field: error.field }),
  ...(error.expected === undefined ? {} : { expected: error.expected }),
  ...(error.actual === undefined ? {} : { actual: error.actual }),
  ...(error.sequence === undefined ? {} : { sequence: error.sequence }),
  ...(error.offset === undefined ? {} : { offset: error.offset }),
  ...(error.sourceCode === undefined ? {} : { sourceCode: error.sourceCode }),
})

const rejected = (
  identity: { readonly eventId: string; readonly sequence: number },
  issues: readonly ExecutionStoreIssueV01[],
): ExecutionEventAcceptanceV01 => ({
  eventId: identity.eventId,
  sequence: identity.sequence,
  status: 'REJECTED',
  acceptedAt: new Date().toISOString(),
  reasons: issues.map(item => item.message),
  issues,
})

class FileExecutionEventStore implements ExecutionEventStoreV01 {
  readonly binding: ExecutionEventStoreBindingV01
  readonly limits: StoreManifestV01['limits']

  readonly #manifest: StoreManifestV01
  readonly #manifestPath: string
  readonly #eventsPath: string
  readonly #records: StoreRecordV01[]
  readonly #eventHashesById: Map<string, string>
  #manifestSnapshot: FileSnapshot
  #eventsSnapshot: FileSnapshot
  #cursor: ExecutionReplayCursorV01
  #closed = false

  constructor(input: {
    manifest: StoreManifestV01
    manifestPath: string
    eventsPath: string
    state: ReplayStateV01
    manifestSnapshot: FileSnapshot
    eventsSnapshot: FileSnapshot
  }) {
    this.#manifest = input.manifest
    this.binding = input.manifest.binding
    this.limits = input.manifest.limits
    this.#manifestPath = input.manifestPath
    this.#eventsPath = input.eventsPath
    this.#records = [...input.state.records]
    this.#eventHashesById = new Map(input.state.eventHashesById)
    this.#cursor = { ...input.state.cursor }
    this.#manifestSnapshot = input.manifestSnapshot
    this.#eventsSnapshot = input.eventsSnapshot
  }

  get cursor(): ExecutionReplayCursorV01 {
    return { ...this.#cursor }
  }

  get eventCount(): number {
    return this.#records.length
  }

  async #assertUsable(): Promise<void> {
    if (this.#closed) {
      throw new ExecutionEventStoreError('STORE_CLOSED', 'Execution Event Store is closed')
    }
    let manifestNow: FileSnapshot
    let eventsNow: FileSnapshot
    try {
      [manifestNow, eventsNow] = await Promise.all([
        snapshotFile(this.#manifestPath),
        snapshotFile(this.#eventsPath),
      ])
    } catch (cause) {
      throw new ExecutionEventStoreError(
        'STORE_CHANGED',
        'Execution Event Store files are missing or inaccessible',
        { cause, ...sourceCodeDetails(cause) },
      )
    }
    if (!sameSnapshot(manifestNow, this.#manifestSnapshot)
        || !sameSnapshot(eventsNow, this.#eventsSnapshot)) {
      throw new ExecutionEventStoreError(
        'STORE_CHANGED',
        'Execution Event Store changed outside this active writer',
      )
    }
  }

  async append(event: ExecutionEventEnvelopeV01): Promise<ExecutionEventAcceptanceV01> {
    const rejectionIdentity = {
      eventId: typeof event?.eventId === 'string' ? event.eventId : '<invalid>',
      sequence: Number.isSafeInteger(event?.sequence) ? event.sequence : 0,
    }
    const validation = validateExecutionEventEnvelope(event)
    const eventSnapshot = validation.valid
      ? immutableCanonicalClone(validation.value)
      : undefined
    await this.#assertUsable()
    if (!validation.valid) {
      return rejected(rejectionIdentity, validation.issues.map(item => ({
        code: 'EVENT_INVALID',
        message: item.message,
        field: item.path,
        sourceCode: item.code,
      })))
    }
    const validEvent = eventSnapshot!
    try {
      assertEventBinding(validEvent, this.#manifest)
    } catch (error) {
      if (error instanceof ExecutionEventStoreError) {
        return rejected(validEvent, [issueFromError(error)])
      }
      throw error
    }
    const envelopeHash = fullEnvelopeHash(validEvent)
    const priorEnvelopeHash = this.#eventHashesById.get(validEvent.eventId)
    if (priorEnvelopeHash !== undefined) {
      if (priorEnvelopeHash !== envelopeHash) {
        return rejected(validEvent, [{
          code: 'EVENT_ID_INTEGRITY_CONFLICT',
          message: 'eventId already identifies a different full event envelope',
          field: 'event.eventId',
          expected: priorEnvelopeHash,
          actual: envelopeHash,
          sequence: validEvent.sequence,
        }])
      }
      const prior = this.#records.find(record => record.event.eventId === validEvent.eventId)!
      return {
        eventId: validEvent.eventId,
        sequence: prior.event.sequence,
        status: 'DUPLICATE',
        acceptedAt: prior.acceptedAt,
        reasons: ['The identical full event envelope is already durable.'],
        stateHash: prior.stateHash,
      }
    }
    const expectedSequence = this.#records.length + 1
    if (validEvent.sequence !== expectedSequence) {
      return rejected(validEvent, [{
        code: 'SEQUENCE_GAP',
        message: 'Event sequence must append exactly at the durable tail',
        field: 'event.sequence',
        expected: expectedSequence,
        actual: validEvent.sequence,
        sequence: validEvent.sequence,
      }])
    }
    if (expectedSequence > this.limits.maxEvents) {
      return rejected(validEvent, [{
        code: 'STORE_LIMIT_EXCEEDED',
        message: 'Appending the event would exceed maxEvents',
        field: 'limits.maxEvents',
        expected: this.limits.maxEvents,
        actual: expectedSequence,
        sequence: validEvent.sequence,
      }])
    }
    const acceptedAt = new Date().toISOString()
    const record = createStoreRecord(validEvent, this.#cursor.stateHash, acceptedAt)
    const line = serializeStoreRecord(record)
    const nextBytes = this.#manifestSnapshot.size
      + this.#eventsSnapshot.size
      + Buffer.byteLength(line, 'utf8')
    if (nextBytes > this.limits.maxStoreBytes) {
      return rejected(validEvent, [{
        code: 'STORE_LIMIT_EXCEEDED',
        message: 'Appending the event would exceed maxStoreBytes',
        field: 'limits.maxStoreBytes',
        expected: this.limits.maxStoreBytes,
        actual: nextBytes,
        sequence: validEvent.sequence,
      }])
    }
    let handle: FileHandle | undefined
    let writeFailed = false
    let writeFailure: unknown
    try {
      handle = await open(this.#eventsPath, 'a')
      await handle.writeFile(line, 'utf8')
      await handle.sync()
    } catch (cause) {
      writeFailed = true
      writeFailure = cause
    } finally {
      try {
        await handle?.close()
      } catch (cause) {
        if (!writeFailed) {
          writeFailed = true
          writeFailure = cause
        }
      }
    }
    if (writeFailed) {
      throw new ExecutionEventStoreError(
        'STORE_WRITE_FAILED',
        'Failed to durably append the execution event',
        {
          cause: writeFailure,
          ...sourceCodeDetails(writeFailure),
          sequence: validEvent.sequence,
        },
      )
    }
    try {
      this.#eventsSnapshot = await snapshotFile(this.#eventsPath)
    } catch (cause) {
      throw new ExecutionEventStoreError(
        'STORE_WRITE_FAILED',
        'Event append completed but the durable tail could not be verified',
        { cause, ...sourceCodeDetails(cause), sequence: validEvent.sequence },
      )
    }
    this.#records.push(record)
    this.#eventHashesById.set(validEvent.eventId, envelopeHash)
    this.#cursor = { sequence: validEvent.sequence, stateHash: record.stateHash }
    return {
      eventId: validEvent.eventId,
      sequence: validEvent.sequence,
      status: 'ACCEPTED',
      acceptedAt,
      reasons: [],
      stateHash: record.stateHash,
    }
  }

  async replay(request: ExecutionReplayRequestV01): Promise<ExecutionReplayPageV01> {
    const requestSnapshot = immutableCanonicalClone(request)
    await this.#assertUsable()
    return replayFromState(requestSnapshot, {
      records: this.#records,
      eventHashesById: this.#eventHashesById,
      cursor: this.#cursor,
    }, this.#manifest)
  }

  async close(): Promise<void> {
    this.#closed = true
  }
}

const validateBindingForOperation = (
  binding: unknown,
): ExecutionEventStoreBindingV01 => {
  const result = validateExecutionEventStoreBinding(binding)
  if (!result.valid) {
    const first = result.issues[0]
    throw new ExecutionEventStoreError(
      'STORE_BINDING_MISMATCH',
      'Execution Event Store binding is invalid',
      {
        field: first?.path ?? 'binding',
        ...(first === undefined ? {} : { sourceCode: first.code }),
      },
    )
  }
  return immutableCanonicalClone(result.value)
}

export const createFileExecutionEventStore = async (
  input: CreateFileExecutionEventStoreInputV01,
): Promise<ExecutionEventStoreV01> => {
  const directory = requireAbsoluteDirectory(input?.directory)
  const binding = validateBindingForOperation(input?.binding)
  const limitsValidation = validateExecutionEventStoreLimits(input?.limits)
  if (!limitsValidation.valid) {
    const first = limitsValidation.issues[0]
    throw new ExecutionEventStoreError(
      'STORE_LIMIT_EXCEEDED',
      'Execution Event Store limits are invalid',
      {
        field: first?.path ?? 'limits',
        ...(first === undefined ? {} : { sourceCode: first.code }),
      },
    )
  }
  const manifest = createStoreManifest(binding, limitsValidation.value)
  const manifestContent = serializeStoreManifest(manifest)
  const manifestBytes = Buffer.byteLength(manifestContent, 'utf8')
  if (manifestBytes > MAX_MANIFEST_BYTES || manifestBytes > manifest.limits.maxStoreBytes) {
    throw new ExecutionEventStoreError(
      'STORE_LIMIT_EXCEEDED',
      'Store manifest does not fit within the configured byte budget',
      {
        field: 'limits.maxStoreBytes',
        expected: manifest.limits.maxStoreBytes,
        actual: manifestBytes,
      },
    )
  }
  try {
    await stat(directory)
    throw new ExecutionEventStoreError(
      'STORE_ALREADY_EXISTS',
      'Execution Event Store directory already exists',
      { field: 'directory', actual: directory },
    )
  } catch (error) {
    if (error instanceof ExecutionEventStoreError) throw error
    if (errorCode(error) !== 'ENOENT') {
      throw new ExecutionEventStoreError(
        'STORE_INVALID_LOCATION',
        'Execution Event Store location could not be inspected',
        { field: 'directory', cause: error, ...sourceCodeDetails(error) },
      )
    }
  }
  const manifestPath = join(directory, MANIFEST_FILE)
  const eventsPath = join(directory, EVENTS_FILE)
  try {
    await mkdir(directory)
    await durableExclusiveWrite(manifestPath, manifestContent)
    await durableExclusiveWrite(eventsPath, '')
  } catch (cause) {
    throw new ExecutionEventStoreError(
      'STORE_WRITE_FAILED',
      'Failed to create the durable Execution Event Store',
      { cause, ...sourceCodeDetails(cause) },
    )
  }
  const [manifestSnapshot, eventsSnapshot] = await Promise.all([
    snapshotFile(manifestPath),
    snapshotFile(eventsPath),
  ])
  return new FileExecutionEventStore({
    manifest,
    manifestPath,
    eventsPath,
    state: scanEventLog('', manifest),
    manifestSnapshot,
    eventsSnapshot,
  })
}

export const openFileExecutionEventStore = async (
  input: OpenFileExecutionEventStoreInputV01,
): Promise<ExecutionEventStoreV01> => {
  const directory = requireAbsoluteDirectory(input?.directory)
  const expectedBinding = validateBindingForOperation(input?.binding)
  const manifestPath = join(directory, MANIFEST_FILE)
  const eventsPath = join(directory, EVENTS_FILE)
  let beforeManifest: FileSnapshot
  let beforeEvents: FileSnapshot
  try {
    [beforeManifest, beforeEvents] = await Promise.all([
      snapshotFile(manifestPath),
      snapshotFile(eventsPath),
    ])
  } catch (cause) {
    throw new ExecutionEventStoreError(
      'STORE_NOT_FOUND',
      'Execution Event Store files were not found',
      { cause, ...sourceCodeDetails(cause) },
    )
  }
  if (beforeManifest.size > MAX_MANIFEST_BYTES) {
    throw new ExecutionEventStoreError(
      'STORE_LIMIT_EXCEEDED',
      'Store manifest exceeds its fixed read budget',
      { field: 'manifest', expected: MAX_MANIFEST_BYTES, actual: beforeManifest.size },
    )
  }
  let manifestContent: string
  try {
    manifestContent = await readFile(manifestPath, 'utf8')
  } catch (cause) {
    throw new ExecutionEventStoreError(
      'STORE_NOT_FOUND',
      'Execution Event Store manifest could not be read',
      { cause, ...sourceCodeDetails(cause) },
    )
  }
  const [manifestReadSnapshot, eventsBeforeRead] = await Promise.all([
    snapshotFile(manifestPath),
    snapshotFile(eventsPath),
  ])
  if (!sameSnapshot(beforeManifest, manifestReadSnapshot)
      || !sameSnapshot(beforeEvents, eventsBeforeRead)) {
    throw new ExecutionEventStoreError(
      'STORE_CHANGED',
      'Execution Event Store changed while it was being opened',
    )
  }
  const manifest = parseStoreManifest(manifestContent)
  if (hashCanonicalJson(expectedBinding) !== manifest.bindingHash) {
    throw new ExecutionEventStoreError(
      'STORE_BINDING_MISMATCH',
      'Requested binding does not match the immutable store binding',
      {
        field: 'binding',
        expected: manifest.bindingHash,
        actual: hashCanonicalJson(expectedBinding),
      },
    )
  }
  const totalBytes = manifestReadSnapshot.size + eventsBeforeRead.size
  if (totalBytes > manifest.limits.maxStoreBytes) {
    throw new ExecutionEventStoreError(
      'STORE_LIMIT_EXCEEDED',
      'Persisted store exceeds maxStoreBytes',
      {
        field: 'limits.maxStoreBytes',
        expected: manifest.limits.maxStoreBytes,
        actual: totalBytes,
      },
    )
  }
  let eventsContent: string
  try {
    eventsContent = await readFile(eventsPath, 'utf8')
  } catch (cause) {
    throw new ExecutionEventStoreError(
      'STORE_NOT_FOUND',
      'Execution Event Store event log could not be read',
      { cause, ...sourceCodeDetails(cause) },
    )
  }
  const [afterManifest, afterEvents] = await Promise.all([
    snapshotFile(manifestPath),
    snapshotFile(eventsPath),
  ])
  if (!sameSnapshot(manifestReadSnapshot, afterManifest)
      || !sameSnapshot(eventsBeforeRead, afterEvents)) {
    throw new ExecutionEventStoreError(
      'STORE_CHANGED',
      'Execution Event Store changed while its event log was being read',
    )
  }
  const state = scanEventLog(eventsContent, manifest)
  return new FileExecutionEventStore({
    manifest,
    manifestPath,
    eventsPath,
    state,
    manifestSnapshot: afterManifest,
    eventsSnapshot: afterEvents,
  })
}

export { ExecutionEventStoreError }
