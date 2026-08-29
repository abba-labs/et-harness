import { afterEach, describe, expect, it } from 'vitest'
import {
  ExecutionEventStoreError,
  createFileExecutionEventStore,
  openFileExecutionEventStore,
  type ExecutionEventStoreBindingV01,
} from '../src/index.js'
import {
  HASH_C,
  SYNTHETIC_LIMITS,
  createSyntheticTempDirectory,
  removeSyntheticTempDirectory,
  storeSnapshot,
  syntheticBinding,
  syntheticContract,
  syntheticEvent,
} from './fixtures/synthetic-fixtures.js'

const directories: string[] = []

const createDirectory = async (): Promise<string> => {
  const directory = await createSyntheticTempDirectory('replay-')
  directories.push(directory)
  return directory
}

afterEach(async () => {
  await Promise.all(directories.splice(0).map(removeSyntheticTempDirectory))
})

const expectStoreError = async (
  operation: Promise<unknown>,
  code: string,
): Promise<ExecutionEventStoreError> => {
  try {
    await operation
  } catch (error) {
    expect(error).toBeInstanceOf(ExecutionEventStoreError)
    const storeError = error as ExecutionEventStoreError
    expect(storeError.code).toBe(code)
    return storeError
  }
  throw new Error(`Expected ${code}`)
}

describe('Phase 1 replay and reconstruction', () => {
  it('paginates from exact cursors without skipping or duplicating events', async () => {
    const directory = await createDirectory()
    const store = await createFileExecutionEventStore({
      directory,
      binding: syntheticBinding(),
      limits: { ...SYNTHETIC_LIMITS, maxReplayEvents: 2 },
    })
    const events = Array.from({ length: 5 }, (_, index) => syntheticEvent(index + 1))
    for (const event of events) await store.append(event)

    const first = await store.replay({ limit: 2 })
    expect(first.events).toEqual(events.slice(0, 2))
    expect(first.cursor.sequence).toBe(2)
    expect(first.hasMore).toBe(true)

    const second = await store.replay({ after: first.cursor, limit: 2 })
    expect(second.events).toEqual(events.slice(2, 4))
    expect(second.cursor.sequence).toBe(4)
    expect(second.hasMore).toBe(true)

    const third = await store.replay({ after: second.cursor, limit: 2 })
    expect(third.events).toEqual(events.slice(4))
    expect(third.cursor).toEqual(store.cursor)
    expect(third.hasMore).toBe(false)

    const tail = await store.replay({ after: third.cursor, limit: 1 })
    expect(tail).toEqual({ events: [], cursor: third.cursor, hasMore: false })
    await store.close()
  })

  it('restores the persisted limits, indexes, cursor and next sequence across instances', async () => {
    const directory = await createDirectory()
    const binding = syntheticBinding()
    const first = await createFileExecutionEventStore({
      directory,
      binding,
      limits: SYNTHETIC_LIMITS,
    })
    const events = [syntheticEvent(1), syntheticEvent(2), syntheticEvent(3)]
    await first.append(events[0]!)
    await first.append(events[1]!)
    const handoffCursor = first.cursor
    await first.close()

    const second = await openFileExecutionEventStore({ directory, binding })
    expect(second.binding).toEqual(binding)
    expect(second.limits).toEqual(SYNTHETIC_LIMITS)
    expect(second.eventCount).toBe(2)
    expect(second.cursor).toEqual(handoffCursor)
    await expect(second.append(events[2]!)).resolves.toMatchObject({ status: 'ACCEPTED' })
    await second.close()

    const third = await openFileExecutionEventStore({ directory, binding })
    expect(third.eventCount).toBe(3)
    expect((await third.replay({ limit: 3 })).events).toEqual(events)
    await third.close()
  })

  it('reconstructs the same Phase 1 semantic projection as uninterrupted execution', async () => {
    const reconstructedDirectory = await createDirectory()
    const uninterruptedDirectory = await createDirectory()
    const binding = syntheticBinding()
    const events = Array.from({ length: 8 }, (_, index) => syntheticEvent(index + 1))

    const first = await createFileExecutionEventStore({
      directory: reconstructedDirectory,
      binding,
      limits: SYNTHETIC_LIMITS,
    })
    for (const event of events.slice(0, 3)) await first.append(event)
    await first.close()
    const second = await openFileExecutionEventStore({
      directory: reconstructedDirectory,
      binding,
    })
    for (const event of events.slice(3)) await second.append(event)
    const reconstructed = await second.replay({ limit: events.length })
    await second.close()

    const uninterrupted = await createFileExecutionEventStore({
      directory: uninterruptedDirectory,
      binding,
      limits: SYNTHETIC_LIMITS,
    })
    for (const event of events) await uninterrupted.append(event)
    const direct = await uninterrupted.replay({ limit: events.length })
    await uninterrupted.close()

    expect(reconstructed.events).toEqual(direct.events)
    expect(reconstructed.events).toEqual(events)
    expect(reconstructed.cursor.sequence).toBe(direct.cursor.sequence)
    expect(reconstructed.hasMore).toBe(false)
    expect(direct.hasMore).toBe(false)
  })

  it.each([
    ['requestId', (binding: ExecutionEventStoreBindingV01) => ({ ...binding, requestId: 'request-other' })],
    ['runtimeId', (binding: ExecutionEventStoreBindingV01) => ({ ...binding, runtimeId: 'runtime-other' })],
    ['turnId', (binding: ExecutionEventStoreBindingV01) => ({ ...binding, turnId: 'turn-other' })],
    ['projectId', (binding: ExecutionEventStoreBindingV01) => ({
      ...binding,
      contract: syntheticContract({ projectId: 'project-other' }),
    })],
    ['taskId', (binding: ExecutionEventStoreBindingV01) => ({
      ...binding,
      contract: syntheticContract({ taskId: 'task-other' }),
    })],
    ['agentId', (binding: ExecutionEventStoreBindingV01) => ({
      ...binding,
      contract: syntheticContract({ agentId: 'agent-other' }),
    })],
    ['contextHash', (binding: ExecutionEventStoreBindingV01) => ({
      ...binding,
      contract: syntheticContract({ contextHash: HASH_C }),
    })],
    ['routeHash', (binding: ExecutionEventStoreBindingV01) => ({
      ...binding,
      contract: syntheticContract({ routeHash: HASH_C }),
    })],
    ['projectRevision', (binding: ExecutionEventStoreBindingV01) => ({
      ...binding,
      contract: syntheticContract({ projectRevision: 'revision-other' }),
    })],
    ['contract', (binding: ExecutionEventStoreBindingV01) => ({
      ...binding,
      contract: syntheticContract({ supervisionLevel: 'ENFORCE' }),
    })],
  ] as const)('fails repeated open with wrong %s binding without rewriting the store', async (field, mutate) => {
    const directory = await createDirectory()
    const binding = syntheticBinding()
    const store = await createFileExecutionEventStore({
      directory,
      binding,
      limits: SYNTHETIC_LIMITS,
    })
    await store.append(syntheticEvent(1))
    await store.close()
    const wrongBinding = mutate(binding)
    const before = await storeSnapshot(directory)

    for (let attempt = 0; attempt < 2; attempt += 1) {
      const error = await expectStoreError(openFileExecutionEventStore({
        directory,
        binding: wrongBinding,
      }), 'STORE_BINDING_MISMATCH')
      expect(error.field).toBe('binding')
      expect(error.expected).toMatch(/^[0-9a-f]{64}$/)
      expect(error.actual).toMatch(/^[0-9a-f]{64}$/)
      expect(error.actual).not.toBe(error.expected)
      expect(await storeSnapshot(directory)).toEqual(before)
    }
  })

  it('rejects invalid, foreign and out-of-range replay cursors without state mutation', async () => {
    const directory = await createDirectory()
    const binding = syntheticBinding()
    const store = await createFileExecutionEventStore({
      directory,
      binding,
      limits: SYNTHETIC_LIMITS,
    })
    await store.append(syntheticEvent(1))
    await store.append(syntheticEvent(2))
    const beforeCount = store.eventCount
    const beforeCursor = store.cursor
    const beforeFiles = await storeSnapshot(directory)

    const invalidCursors = [
      { after: { sequence: -1, stateHash: beforeCursor.stateHash }, limit: 1 },
      { after: { sequence: 1, stateHash: HASH_C }, limit: 1 },
      { after: { sequence: 99, stateHash: beforeCursor.stateHash }, limit: 1 },
    ]
    for (const input of invalidCursors) {
      await expectStoreError(store.replay(input), 'STORE_CURSOR_INVALID')
      expect(store.eventCount).toBe(beforeCount)
      expect(store.cursor).toEqual(beforeCursor)
      expect(await storeSnapshot(directory)).toEqual(beforeFiles)
    }
    for (const input of [
      { limit: 0 },
      { limit: SYNTHETIC_LIMITS.maxReplayEvents + 1 },
    ]) {
      await expectStoreError(store.replay(input), 'STORE_LIMIT_EXCEEDED')
      expect(store.eventCount).toBe(beforeCount)
      expect(store.cursor).toEqual(beforeCursor)
      expect(await storeSnapshot(directory)).toEqual(beforeFiles)
    }
    await store.close()
  })
})
