import { randomUUID } from 'node:crypto'
import {
  mkdir,
  open,
  readFile,
  rename,
  rmdir,
  stat,
  unlink,
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
  type ExecutionStoreFinalizationV01,
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
  parseStoreFinalization,
  serializeStoreFinalization,
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
const FINALIZATION_FILE = 'finalization.json'
const MUTATION_LOCK_FILE = 'mutation.lock'
const MUTATION_LOCK_OWNER_FILE = 'owner.json'
const MUTATION_RECOVERY_GUARD_SUFFIX = '.guard'
const MAX_MANIFEST_BYTES = MAX_TASK_SUPERVISION_CONTRACT_BYTES + (256 * 1024)
const MUTATION_LOCK_SCHEMA = 'agent-harness.execution-mutation-lock.v0.1'

interface MutationLockOwnerV01 {
  readonly schema: typeof MUTATION_LOCK_SCHEMA
  readonly pid: number
  readonly generation: string
}

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

const readOptionalFinalization = async (
  file: string,
): Promise<{
  readonly finalization: ExecutionStoreFinalizationV01
  readonly snapshot: FileSnapshot
} | undefined> => {
  let before: FileSnapshot
  try {
    before = await snapshotFile(file)
  } catch (cause) {
    if (errorCode(cause) === 'ENOENT') return undefined
    throw new ExecutionEventStoreError(
      'STORE_CHANGED',
      'Execution Event Store finalization could not be inspected',
      { cause, ...sourceCodeDetails(cause) },
    )
  }
  let content: string
  try {
    content = await readFile(file, 'utf8')
  } catch (cause) {
    throw new ExecutionEventStoreError(
      'STORE_CHANGED',
      'Execution Event Store finalization could not be read',
      { cause, ...sourceCodeDetails(cause) },
    )
  }
  const after = await snapshotFile(file)
  if (!sameSnapshot(before, after)) {
    throw new ExecutionEventStoreError(
      'STORE_CHANGED',
      'Execution Event Store finalization changed while it was being read',
    )
  }
  return {
    finalization: parseStoreFinalization(content),
    snapshot: after,
  }
}

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

const processIsAlive = (pid: number): boolean => {
  try {
    process.kill(pid, 0)
    return true
  } catch (cause) {
    return errorCode(cause) !== 'ESRCH'
  }
}

const parseMutationLockOwner = (content: string): MutationLockOwnerV01 | undefined => {
  try {
    const value = JSON.parse(content) as Partial<MutationLockOwnerV01>
    if (value.schema !== MUTATION_LOCK_SCHEMA
        || !Number.isSafeInteger(value.pid)
        || (value.pid ?? 0) <= 0
        || typeof value.generation !== 'string'
        || !/^[0-9a-f-]{36}$/.test(value.generation)) return undefined
    return value as MutationLockOwnerV01
  } catch {
    return undefined
  }
}

const cleanupKnownMutationLockDirectory = async (directory: string): Promise<void> => {
  try {
    await unlink(join(directory, MUTATION_LOCK_OWNER_FILE))
  } catch (cause) {
    if (errorCode(cause) !== 'ENOENT') throw cause
  }
  await rmdir(directory)
}

const acquireMutationLockWhileGuarded = async (
  directory: string,
): Promise<MutationLockOwnerV01> => {
  const owner: MutationLockOwnerV01 = {
    schema: MUTATION_LOCK_SCHEMA,
    pid: process.pid,
    generation: randomUUID(),
  }
  try {
    await mkdir(directory)
    try {
      await durableExclusiveWrite(
        join(directory, MUTATION_LOCK_OWNER_FILE),
        `${JSON.stringify(owner)}\n`,
      )
      return owner
    } catch (cause) {
      try {
        await cleanupKnownMutationLockDirectory(directory)
      } catch {
        // The original lock initialization error is authoritative.
      }
      throw cause
    }
  } catch (cause) {
    if (errorCode(cause) !== 'EEXIST') throw cause
  }

  let persisted: MutationLockOwnerV01 | undefined
  try {
    persisted = parseMutationLockOwner(await readFile(
      join(directory, MUTATION_LOCK_OWNER_FILE),
      'utf8',
    ))
  } catch (cause) {
    if (errorCode(cause) === 'ENOENT') {
      throw new ExecutionEventStoreError(
        'STORE_CHANGED',
        'Execution Event Store has an incomplete unresolved mutation lock',
        { cause, ...sourceCodeDetails(cause) },
      )
    }
    throw new ExecutionEventStoreError(
      'STORE_CHANGED',
      'Execution Event Store mutation lock could not be inspected',
      { cause, ...sourceCodeDetails(cause) },
    )
  }
  if (persisted === undefined || processIsAlive(persisted.pid)) {
    throw new ExecutionEventStoreError(
      'STORE_CHANGED',
      'Execution Event Store has another active mutation or an unresolved mutation lock',
    )
  }
  const isolated = `${directory}.stale-${randomUUID()}`
  try {
    await rename(directory, isolated)
  } catch (cause) {
    if (errorCode(cause) === 'ENOENT') return acquireMutationLockWhileGuarded(directory)
    if (errorCode(cause) !== 'ENOENT') {
      throw new ExecutionEventStoreError(
        'STORE_CHANGED',
        'Dead mutation owner was detected but its lock could not be isolated',
        { cause, ...sourceCodeDetails(cause) },
      )
    }
  }
  const isolatedOwner = parseMutationLockOwner(await readFile(
    join(isolated, MUTATION_LOCK_OWNER_FILE),
    'utf8',
  ))
  if (isolatedOwner?.generation !== persisted.generation) {
    throw new ExecutionEventStoreError(
      'STORE_CHANGED',
      'Isolated mutation lock generation changed during recovery',
    )
  }
  try {
    await cleanupKnownMutationLockDirectory(isolated)
  } catch (cause) {
    throw new ExecutionEventStoreError(
      'STORE_CHANGED',
      'Dead mutation lock was isolated but could not be safely cleaned',
      { cause, ...sourceCodeDetails(cause) },
    )
  }
  return acquireMutationLockWhileGuarded(directory)
}

const acquireMutationLock = async (directory: string): Promise<MutationLockOwnerV01> => {
  const guard = `${directory}${MUTATION_RECOVERY_GUARD_SUFFIX}`
  let guarded = false
  try {
    await mkdir(guard)
    guarded = true
  } catch (cause) {
    if (errorCode(cause) === 'EEXIST') {
      throw new ExecutionEventStoreError(
        'STORE_CHANGED',
        'Execution Event Store has another lock acquisition or an unresolved recovery guard',
        { cause, ...sourceCodeDetails(cause) },
      )
    }
    throw cause
  }
  try {
    return await acquireMutationLockWhileGuarded(directory)
  } finally {
    if (guarded) {
      try {
        await rmdir(guard)
      } catch (cause) {
        throw new ExecutionEventStoreError(
          'STORE_WRITE_FAILED',
          'Execution Event Store lock acquisition completed but its recovery guard could not be released',
          { cause, ...sourceCodeDetails(cause) },
        )
      }
    }
  }
}

const releaseMutationLock = async (
  directory: string,
  owner: MutationLockOwnerV01,
): Promise<void> => {
  const persisted = parseMutationLockOwner(await readFile(
    join(directory, MUTATION_LOCK_OWNER_FILE),
    'utf8',
  ))
  if (persisted?.generation !== owner.generation || persisted.pid !== owner.pid) {
    throw new ExecutionEventStoreError(
      'STORE_WRITE_FAILED',
      'Execution Event Store mutation lock ownership changed before release',
    )
  }
  await cleanupKnownMutationLockDirectory(directory)
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
  readonly #finalizationPath: string
  readonly #mutationLockPath: string
  readonly #records: StoreRecordV01[]
  readonly #eventHashesById: Map<string, string>
  #manifestSnapshot: FileSnapshot
  #eventsSnapshot: FileSnapshot
  #finalizationSnapshot: FileSnapshot | undefined
  #cursor: ExecutionReplayCursorV01
  #finalization: ExecutionStoreFinalizationV01 | undefined
  #closed = false

  constructor(input: {
    manifest: StoreManifestV01
    manifestPath: string
    eventsPath: string
    finalizationPath: string
    mutationLockPath: string
    finalization?: ExecutionStoreFinalizationV01
    state: ReplayStateV01
    manifestSnapshot: FileSnapshot
    eventsSnapshot: FileSnapshot
    finalizationSnapshot?: FileSnapshot
  }) {
    this.#manifest = input.manifest
    this.binding = input.manifest.binding
    this.limits = input.manifest.limits
    this.#manifestPath = input.manifestPath
    this.#eventsPath = input.eventsPath
    this.#finalizationPath = input.finalizationPath
    this.#mutationLockPath = input.mutationLockPath
    this.#records = [...input.state.records]
    this.#eventHashesById = new Map(input.state.eventHashesById)
    this.#cursor = { ...input.state.cursor }
    this.#finalization = input.finalization
    this.#manifestSnapshot = input.manifestSnapshot
    this.#eventsSnapshot = input.eventsSnapshot
    this.#finalizationSnapshot = input.finalizationSnapshot
  }

  get cursor(): ExecutionReplayCursorV01 {
    return { ...this.#cursor }
  }

  get eventCount(): number {
    return this.#records.length
  }

  get finalization(): ExecutionStoreFinalizationV01 | undefined {
    return this.#finalization === undefined
      ? undefined
      : immutableCanonicalClone(this.#finalization)
  }

  async #withMutationLock<T>(operation: () => Promise<T>): Promise<T> {
    let owner: MutationLockOwnerV01 | undefined
    try {
      owner = await acquireMutationLock(this.#mutationLockPath)
      return await operation()
    } finally {
      if (owner) {
        try {
          await releaseMutationLock(this.#mutationLockPath, owner)
        } catch (cause) {
          throw new ExecutionEventStoreError(
            'STORE_WRITE_FAILED',
            'Execution Event Store mutation completed but its lock could not be released',
            { cause, ...sourceCodeDetails(cause) },
          )
        }
      }
    }
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
    if (this.#finalizationSnapshot !== undefined) {
      let finalizationNow: FileSnapshot
      try {
        finalizationNow = await snapshotFile(this.#finalizationPath)
      } catch (cause) {
        throw new ExecutionEventStoreError(
          'STORE_CHANGED',
          'Execution Event Store durable finalization is missing or inaccessible',
          { cause, ...sourceCodeDetails(cause) },
        )
      }
      if (!sameSnapshot(finalizationNow, this.#finalizationSnapshot)) {
        throw new ExecutionEventStoreError(
          'STORE_CHANGED',
          'Execution Event Store durable finalization changed outside this process',
        )
      }
    }
  }

  async append(event: ExecutionEventEnvelopeV01): Promise<ExecutionEventAcceptanceV01> {
    return this.#withMutationLock(() => this.#appendLocked(event))
  }

  async #appendLocked(event: ExecutionEventEnvelopeV01): Promise<ExecutionEventAcceptanceV01> {
    const rejectionIdentity = {
      eventId: typeof event?.eventId === 'string' ? event.eventId : '<invalid>',
      sequence: Number.isSafeInteger(event?.sequence) ? event.sequence : 0,
    }
    const validation = validateExecutionEventEnvelope(event)
    const eventSnapshot = validation.valid
      ? immutableCanonicalClone(validation.value)
      : undefined
    await this.#assertUsable()
    if (this.#finalization !== undefined) {
      throw new ExecutionEventStoreError(
        'STORE_FINALIZED',
        `Execution Event Store is finalized at ${this.#finalization.finalizationRef}`,
        { field: 'finalization.finalizationRef', actual: this.#finalization.finalizationRef },
      )
    }
    const persistedRead = await readOptionalFinalization(this.#finalizationPath)
    if (persistedRead !== undefined) {
      const persisted = persistedRead.finalization
      this.#finalization = persisted
      this.#finalizationSnapshot = persistedRead.snapshot
      throw new ExecutionEventStoreError(
        'STORE_FINALIZED',
        `Execution Event Store is finalized at ${persisted.finalizationRef}`,
        { field: 'finalization.finalizationRef', actual: persisted.finalizationRef },
      )
    }
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

  async finalize(
    finalization: ExecutionStoreFinalizationV01,
  ): Promise<ExecutionStoreFinalizationV01> {
    const snapshot = parseStoreFinalization(serializeStoreFinalization(
      immutableCanonicalClone(finalization),
    ))
    return this.#withMutationLock(async () => {
      await this.#assertUsable()
      if (this.#finalization !== undefined) {
        if (hashCanonicalJson(this.#finalization) === hashCanonicalJson(snapshot)) {
          return immutableCanonicalClone(this.#finalization)
        }
        throw new ExecutionEventStoreError(
          'STORE_FINALIZATION_CONFLICT',
          'Execution Event Store is already finalized with different content',
          {
            field: 'finalization.finalizationHash',
            expected: this.#finalization.finalizationHash,
            actual: snapshot.finalizationHash,
          },
        )
      }
      const existingRead = await readOptionalFinalization(this.#finalizationPath)
      if (existingRead !== undefined) {
        const existing = existingRead.finalization
        this.#finalization = existing
        this.#finalizationSnapshot = existingRead.snapshot
        if (hashCanonicalJson(existing) === hashCanonicalJson(snapshot)) {
          return immutableCanonicalClone(existing)
        }
        throw new ExecutionEventStoreError(
          'STORE_FINALIZATION_CONFLICT',
          'Execution Event Store has a different durable finalization',
          {
            field: 'finalization.finalizationHash',
            expected: existing.finalizationHash,
            actual: snapshot.finalizationHash,
          },
        )
      }
      if (snapshot.cursor.sequence !== this.#cursor.sequence
          || snapshot.cursor.stateHash !== this.#cursor.stateHash) {
        throw new ExecutionEventStoreError(
          'STORE_FINALIZATION_CONFLICT',
          'Finalization cursor does not match the durable Event Store tail',
          {
            field: 'finalization.cursor',
            expected: `${this.#cursor.sequence}:${this.#cursor.stateHash}`,
            actual: `${snapshot.cursor.sequence}:${snapshot.cursor.stateHash}`,
          },
        )
      }
      const serialized = serializeStoreFinalization(snapshot)
      const totalBytes = this.#manifestSnapshot.size
        + this.#eventsSnapshot.size
        + Buffer.byteLength(serialized, 'utf8')
      if (totalBytes > this.limits.maxStoreBytes) {
        throw new ExecutionEventStoreError(
          'STORE_LIMIT_EXCEEDED',
          'Finalizing the store would exceed maxStoreBytes',
          {
            field: 'limits.maxStoreBytes',
            expected: this.limits.maxStoreBytes,
            actual: totalBytes,
          },
        )
      }
      try {
        await durableExclusiveWrite(this.#finalizationPath, serialized)
      } catch (cause) {
        if (errorCode(cause) === 'EEXIST') {
          throw new ExecutionEventStoreError(
            'STORE_FINALIZATION_CONFLICT',
            'Execution Event Store was finalized by another writer',
            { cause, ...sourceCodeDetails(cause) },
          )
        }
        throw new ExecutionEventStoreError(
          'STORE_WRITE_FAILED',
          'Failed to durably finalize the Execution Event Store',
          { cause, ...sourceCodeDetails(cause) },
        )
      }
      const durable = await readOptionalFinalization(this.#finalizationPath)
      if (durable === undefined
          || hashCanonicalJson(durable.finalization) !== hashCanonicalJson(snapshot)) {
        throw new ExecutionEventStoreError(
          'STORE_WRITE_FAILED',
          'Execution Event Store finalization write-back does not match the requested seal',
        )
      }
      this.#finalization = durable.finalization
      this.#finalizationSnapshot = durable.snapshot
      return immutableCanonicalClone(durable.finalization)
    })
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
  const finalizationPath = join(directory, FINALIZATION_FILE)
  const mutationLockPath = join(directory, MUTATION_LOCK_FILE)
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
    finalizationPath,
    mutationLockPath,
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
  const finalizationPath = join(directory, FINALIZATION_FILE)
  const mutationLockPath = join(directory, MUTATION_LOCK_FILE)
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
  const finalizationRead = await readOptionalFinalization(finalizationPath)
  const finalization = finalizationRead?.finalization
  const finalizationSnapshot = finalizationRead?.snapshot
  if (finalizationSnapshot !== undefined) {
    const finalizedBytes = totalBytes + finalizationSnapshot.size
    if (finalizedBytes > manifest.limits.maxStoreBytes) {
      throw new ExecutionEventStoreError(
        'STORE_LIMIT_EXCEEDED',
        'Persisted finalized store exceeds maxStoreBytes',
        {
          field: 'limits.maxStoreBytes',
          expected: manifest.limits.maxStoreBytes,
          actual: finalizedBytes,
        },
      )
    }
  }
  if (finalization
      && (finalization.cursor.sequence !== state.cursor.sequence
        || finalization.cursor.stateHash !== state.cursor.stateHash)) {
    throw new ExecutionEventStoreError(
      'STORE_FINALIZATION_CONFLICT',
      'Persisted finalization cursor does not match the durable Event Store tail',
      {
        field: 'finalization.cursor',
        expected: `${state.cursor.sequence}:${state.cursor.stateHash}`,
        actual: `${finalization.cursor.sequence}:${finalization.cursor.stateHash}`,
      },
    )
  }
  return new FileExecutionEventStore({
    manifest,
    manifestPath,
    eventsPath,
    finalizationPath,
    mutationLockPath,
    ...(finalization === undefined ? {} : { finalization }),
    ...(finalizationSnapshot === undefined ? {} : { finalizationSnapshot }),
    state,
    manifestSnapshot: afterManifest,
    eventsSnapshot: afterEvents,
  })
}

export { ExecutionEventStoreError }
