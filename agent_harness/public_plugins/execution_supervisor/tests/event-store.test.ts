import { readFileSync, readdirSync } from 'node:fs'
import { access } from 'node:fs/promises'
import { join, resolve } from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'
import {
  ExecutionEventStoreError,
  MAX_EXECUTION_EVENT_PAYLOAD_BYTES,
  MAX_IDENTIFIER_CHARS,
  createFileExecutionEventStore,
  openFileExecutionEventStore,
  type ExecutionEventAcceptanceV01,
  type ExecutionEventEnvelopeV01,
  type ExecutionEventStoreV01,
} from '../src/index.js'
import {
  HASH_C,
  SYNTHETIC_LIMITS,
  createSyntheticTempDirectory,
  expectSha256,
  removeSyntheticTempDirectory,
  storeSnapshot,
  syntheticBinding,
  syntheticContract,
  syntheticEvent,
} from './fixtures/synthetic-fixtures.js'

const directories: string[] = []

const createDirectory = async (): Promise<string> => {
  const directory = await createSyntheticTempDirectory('event-store-')
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
    expect(storeError.message.length).toBeGreaterThan(0)
    return storeError
  }
  throw new Error(`Expected ${code}`)
}

const expectRejectedWithoutMutation = async (
  store: ExecutionEventStoreV01,
  directory: string,
  event: ExecutionEventEnvelopeV01,
  code: string,
): Promise<ExecutionEventAcceptanceV01> => {
  const beforeCount = store.eventCount
  const beforeCursor = store.cursor
  const beforeFiles = await storeSnapshot(directory)
  const result = await store.append(event)
  expect(result.status).toBe('REJECTED')
  expect(result.issues?.map(issue => issue.code)).toContain(code)
  expect(store.eventCount).toBe(beforeCount)
  expect(store.cursor).toEqual(beforeCursor)
  expect(await storeSnapshot(directory)).toEqual(beforeFiles)
  return result
}

describe('Phase 1 file Execution Event Store', () => {
  it('creates an empty store with deterministic genesis state and reopens it exactly', async () => {
    const directory = await createDirectory()
    const binding = syntheticBinding()
    const store = await createFileExecutionEventStore({
      directory,
      binding,
      limits: SYNTHETIC_LIMITS,
    })

    expect(store.binding).toEqual(binding)
    expect(store.limits).toEqual(SYNTHETIC_LIMITS)
    expect(store.eventCount).toBe(0)
    expect(store.cursor.sequence).toBe(0)
    expectSha256(store.cursor.stateHash)
    const genesis = store.cursor
    await expect(access(resolve(directory, 'manifest.json'))).resolves.toBeUndefined()
    await expect(access(resolve(directory, 'events.jsonl'))).resolves.toBeUndefined()

    const emptyPage = await store.replay({ limit: 1 })
    expect(emptyPage).toEqual({ events: [], cursor: genesis, hasMore: false })

    const secondDirectory = await createDirectory()
    const secondStore = await createFileExecutionEventStore({
      directory: secondDirectory,
      binding: syntheticBinding(),
      limits: { ...SYNTHETIC_LIMITS },
    })
    expect(secondStore.cursor).toEqual(genesis)
    await secondStore.close()
    await store.close()

    const reopened = await openFileExecutionEventStore({ directory, binding })
    expect(reopened.eventCount).toBe(0)
    expect(reopened.cursor).toEqual(genesis)
    await reopened.close()
    await expectStoreError(reopened.append(syntheticEvent(1)), 'STORE_CLOSED')
    await expectStoreError(reopened.replay({ limit: 1 }), 'STORE_CLOSED')
  })

  it('separates create from open and fails closed for an existing or absent target', async () => {
    const existing = await createDirectory()
    const binding = syntheticBinding()
    const store = await createFileExecutionEventStore({
      directory: existing,
      binding,
      limits: SYNTHETIC_LIMITS,
    })
    await store.close()
    const before = await storeSnapshot(existing)
    await expectStoreError(createFileExecutionEventStore({
      directory: existing,
      binding,
      limits: SYNTHETIC_LIMITS,
    }), 'STORE_ALREADY_EXISTS')
    expect(await storeSnapshot(existing)).toEqual(before)

    const absent = await createDirectory()
    await expectStoreError(openFileExecutionEventStore({
      directory: resolve(absent, 'missing-store'),
      binding,
    }), 'STORE_NOT_FOUND')
  })

  it('rejects an invalid bound contract before creating persistent files', async () => {
    const parent = await createDirectory()
    const directory = resolve(parent, 'invalid-binding')
    const binding = syntheticBinding({
      contract: syntheticContract({ projectId: 'x'.repeat(MAX_IDENTIFIER_CHARS + 1) }),
    })
    const error = await expectStoreError(createFileExecutionEventStore({
      directory,
      binding,
      limits: SYNTHETIC_LIMITS,
    }), 'STORE_BINDING_MISMATCH')
    expect(error.sourceCode).toBe('INVALID_IDENTIFIER')
    await expect(access(resolve(directory, 'manifest.json'))).rejects.toBeDefined()

    const baseContract = syntheticContract()
    const template = baseContract.obligations[0]!
    const oversizedContract = syntheticContract({
      obligations: Array.from({ length: 9 }, (_, index) => ({
        ...template,
        id: `OBL-SYNTHETIC-${index.toString().padStart(3, '0')}`,
        target: {
          resourceId: `resource-synthetic-${index}`,
          padding: 'x'.repeat(60 * 1024),
        },
      })),
    })
    const oversizedDirectory = resolve(parent, 'oversized-contract')
    const oversizedError = await expectStoreError(createFileExecutionEventStore({
      directory: oversizedDirectory,
      binding: syntheticBinding({ contract: oversizedContract }),
      limits: SYNTHETIC_LIMITS,
    }), 'STORE_BINDING_MISMATCH')
    expect(oversizedError.sourceCode).toBe('CONTRACT_BUDGET_EXCEEDED')
    await expect(access(resolve(oversizedDirectory, 'manifest.json'))).rejects.toBeDefined()
  })

  it('appends sequences one and two and replays the exact envelopes in order', async () => {
    const directory = await createDirectory()
    const store = await createFileExecutionEventStore({
      directory,
      binding: syntheticBinding(),
      limits: SYNTHETIC_LIMITS,
    })
    const first = syntheticEvent(1)
    const second = syntheticEvent(2)

    await expect(store.append(first)).resolves.toMatchObject({
      eventId: first.eventId,
      sequence: 1,
      status: 'ACCEPTED',
    })
    await expect(store.append(second)).resolves.toMatchObject({
      eventId: second.eventId,
      sequence: 2,
      status: 'ACCEPTED',
    })
    expect(store.eventCount).toBe(2)
    expect(store.cursor.sequence).toBe(2)
    expectSha256(store.cursor.stateHash)

    const page = await store.replay({ limit: 2 })
    expect(page.events).toEqual([first, second])
    expect(page.cursor).toEqual(store.cursor)
    expect(page.hasMore).toBe(false)
    await store.close()
  })

  it('treats an exact full-envelope duplicate as a durable no-op', async () => {
    const directory = await createDirectory()
    const binding = syntheticBinding()
    const store = await createFileExecutionEventStore({
      directory,
      binding,
      limits: SYNTHETIC_LIMITS,
    })
    const event = syntheticEvent(1)
    await store.append(event)
    const beforeCount = store.eventCount
    const beforeCursor = store.cursor
    const beforeFiles = await storeSnapshot(directory)

    const duplicate = await store.append(event)
    expect(duplicate).toMatchObject({
      eventId: event.eventId,
      sequence: 1,
      status: 'DUPLICATE',
      stateHash: beforeCursor.stateHash,
    })
    expect(store.eventCount).toBe(beforeCount)
    expect(store.cursor).toEqual(beforeCursor)
    expect(await storeSnapshot(directory)).toEqual(beforeFiles)
    await store.close()

    const reopened = await openFileExecutionEventStore({ directory, binding })
    expect(reopened.eventCount).toBe(1)
    expect((await reopened.replay({ limit: 1 })).events).toEqual([event])
    await reopened.close()
  })

  it('rejects a changed full envelope reusing an accepted eventId', async () => {
    const directory = await createDirectory()
    const binding = syntheticBinding()
    const store = await createFileExecutionEventStore({
      directory,
      binding,
      limits: SYNTHETIC_LIMITS,
    })
    const original = syntheticEvent(1)
    await store.append(original)
    const tampered = syntheticEvent(1, {
      eventId: original.eventId,
      payload: { operation: 'synthetic-observation', ordinal: 1, summary: 'changed' },
    })
    expect(tampered.payloadHash).not.toBe(original.payloadHash)
    await expectRejectedWithoutMutation(
      store,
      directory,
      tampered,
      'EVENT_ID_INTEGRITY_CONFLICT',
    )
    const samePayloadChangedTimestamp = syntheticEvent(1, {
      eventId: original.eventId,
      timestamp: '2026-08-29T00:05:00.000Z',
      payload: original.payload,
    })
    expect(samePayloadChangedTimestamp.payloadHash).toBe(original.payloadHash)
    await expectRejectedWithoutMutation(
      store,
      directory,
      samePayloadChangedTimestamp,
      'EVENT_ID_INTEGRITY_CONFLICT',
    )
    await store.close()

    const reopened = await openFileExecutionEventStore({ directory, binding })
    expect((await reopened.replay({ limit: 1 })).events).toEqual([original])
    await reopened.close()
  })

  it('rejects a sequence gap without preventing the missing sequence from arriving', async () => {
    const directory = await createDirectory()
    const binding = syntheticBinding()
    const store = await createFileExecutionEventStore({
      directory,
      binding,
      limits: SYNTHETIC_LIMITS,
    })
    await store.append(syntheticEvent(1))
    await expectRejectedWithoutMutation(store, directory, syntheticEvent(3), 'SEQUENCE_GAP')
    await store.close()

    const reopened = await openFileExecutionEventStore({ directory, binding })
    expect(reopened.eventCount).toBe(1)
    expect(reopened.cursor.sequence).toBe(1)
    await expect(reopened.append(syntheticEvent(2))).resolves.toMatchObject({ status: 'ACCEPTED' })
    await expect(reopened.append(syntheticEvent(3))).resolves.toMatchObject({ status: 'ACCEPTED' })
    expect((await reopened.replay({ limit: 3 })).events.map(event => event.sequence)).toEqual([1, 2, 3])
    await reopened.close()
  })

  it.each([
    ['requestId', { requestId: 'request-other' }],
    ['runtimeId', { runtimeId: 'runtime-other' }],
    ['projectId', { projectId: 'project-other' }],
    ['taskId', { taskId: 'task-other' }],
    ['turnId', { turnId: 'turn-other' }],
    ['agentId', { agentId: 'agent-other' }],
    ['contextHash', { contextHash: HASH_C }],
  ] as const)('rejects an event with mismatched %s identity', async (field, overrides) => {
    const directory = await createDirectory()
    const binding = syntheticBinding()
    const store = await createFileExecutionEventStore({
      directory,
      binding,
      limits: SYNTHETIC_LIMITS,
    })
    const before = await storeSnapshot(directory)
    const result = await store.append(syntheticEvent(1, overrides))
    expect(result.status).toBe('REJECTED')
    expect(result.issues).toEqual(expect.arrayContaining([
      expect.objectContaining({
        code: 'EVENT_BINDING_MISMATCH',
        field: `event.${field}`,
        sequence: 1,
      }),
    ]))
    expect(store.eventCount).toBe(0)
    expect(store.cursor.sequence).toBe(0)
    expect(await storeSnapshot(directory)).toEqual(before)
    await store.close()
    const reopened = await openFileExecutionEventStore({ directory, binding })
    expect(reopened.eventCount).toBe(0)
    expect(reopened.cursor.sequence).toBe(0)
    expect(await storeSnapshot(directory)).toEqual(before)
    await reopened.close()
  })

  it('rejects Phase 0 identifier and payload bounds before persistence', async () => {
    const directory = await createDirectory()
    const binding = syntheticBinding()
    const store = await createFileExecutionEventStore({
      directory,
      binding,
      limits: SYNTHETIC_LIMITS,
    })
    const invalidIdentifier = syntheticEvent(1, {
      eventId: 'x'.repeat(MAX_IDENTIFIER_CHARS + 1),
    })
    const identifierResult = await expectRejectedWithoutMutation(
      store,
      directory,
      invalidIdentifier,
      'EVENT_INVALID',
    )
    expect(identifierResult.issues).toEqual(expect.arrayContaining([
      expect.objectContaining({ code: 'EVENT_INVALID', sourceCode: 'INVALID_IDENTIFIER' }),
    ]))

    const oversizedPayload = {
      summary: 'x'.repeat(MAX_EXECUTION_EVENT_PAYLOAD_BYTES + 1),
    }
    const payloadResult = await expectRejectedWithoutMutation(
      store,
      directory,
      syntheticEvent(1, { payload: oversizedPayload }),
      'EVENT_INVALID',
    )
    expect(payloadResult.issues).toEqual(expect.arrayContaining([
      expect.objectContaining({ code: 'EVENT_INVALID', sourceCode: 'JSON_BUDGET_EXCEEDED' }),
    ]))
    expect(store.eventCount).toBe(0)
    const expectedCursor = store.cursor
    const expectedFiles = await storeSnapshot(directory)
    expect((await store.replay({ limit: 1 })).events).toEqual([])
    await store.close()
    const reopened = await openFileExecutionEventStore({ directory, binding })
    expect(reopened.eventCount).toBe(0)
    expect(reopened.cursor).toEqual(expectedCursor)
    expect(await storeSnapshot(directory)).toEqual(expectedFiles)
    await reopened.close()
  })

  it('enforces maxEvents with no partial durable write', async () => {
    const directory = await createDirectory()
    const binding = syntheticBinding()
    const store = await createFileExecutionEventStore({
      directory,
      binding,
      limits: { ...SYNTHETIC_LIMITS, maxEvents: 1, maxReplayEvents: 1 },
    })
    await store.append(syntheticEvent(1))
    await expectRejectedWithoutMutation(store, directory, syntheticEvent(2), 'STORE_LIMIT_EXCEEDED')
    await store.close()
    const reopened = await openFileExecutionEventStore({ directory, binding })
    expect(reopened.eventCount).toBe(1)
    expect((await reopened.replay({ limit: 1 })).events).toEqual([syntheticEvent(1)])
    await reopened.close()
  })

  it('enforces maxStoreBytes with no partial durable write', async () => {
    const directory = await createDirectory()
    const binding = syntheticBinding()
    const store = await createFileExecutionEventStore({
      directory,
      binding,
      limits: { ...SYNTHETIC_LIMITS, maxStoreBytes: 4 * 1024 },
    })
    const largeButContractValid = syntheticEvent(1, {
      payload: { summary: 'x'.repeat(4 * 1024) },
    })
    await expectRejectedWithoutMutation(
      store,
      directory,
      largeButContractValid,
      'STORE_LIMIT_EXCEEDED',
    )
    await store.close()
    const reopened = await openFileExecutionEventStore({ directory, binding })
    expect(reopened.eventCount).toBe(0)
    expect(reopened.cursor.sequence).toBe(0)
    await reopened.close()
  })

  it('fails a stale writer closed after another instance advances durable state', async () => {
    const directory = await createDirectory()
    const binding = syntheticBinding()
    const stale = await createFileExecutionEventStore({
      directory,
      binding,
      limits: SYNTHETIC_LIMITS,
    })
    const current = await openFileExecutionEventStore({ directory, binding })
    await current.append(syntheticEvent(1))
    await expectStoreError(stale.append(syntheticEvent(1)), 'STORE_CHANGED')
    expect(stale.eventCount).toBe(0)
    expect(stale.cursor.sequence).toBe(0)
    await stale.close()
    await current.close()
    const reopened = await openFileExecutionEventStore({ directory, binding })
    expect(reopened.eventCount).toBe(1)
    expect((await reopened.replay({ limit: 1 })).events).toEqual([syntheticEvent(1)])
    await reopened.close()
  })

  it('defensively snapshots mutable create inputs and appended envelopes', async () => {
    const directory = await createDirectory()
    const binding = syntheticBinding()
    const limits = { ...SYNTHETIC_LIMITS, maxEvents: 2, maxReplayEvents: 2 }
    const expectedBinding = structuredClone(binding)
    const expectedLimits = structuredClone(limits)
    const first = syntheticEvent(1)
    const expectedFirst = structuredClone(first)
    const store = await createFileExecutionEventStore({ directory, binding, limits })

    const mutableBinding = binding as unknown as Record<string, unknown>
    mutableBinding.requestId = 'request-mutated'
    const mutableContract = binding.contract as unknown as Record<string, unknown>
    mutableContract.projectId = 'project-mutated'
    const mutableLimits = limits as Record<string, number>
    mutableLimits.maxEvents = 1
    mutableLimits.maxReplayEvents = 1

    expect(store.binding).toEqual(expectedBinding)
    expect(store.limits).toEqual(expectedLimits)
    await expect(store.append(first)).resolves.toMatchObject({ status: 'ACCEPTED' })

    const mutableFirst = first as unknown as Record<string, unknown>
    mutableFirst.requestId = 'request-mutated'
    mutableFirst.sequence = 99
    const mutablePayload = first.payload as unknown as Record<string, unknown>
    mutablePayload.summary = 'mutated after append'

    expect((await store.replay({ limit: 2 })).events).toEqual([expectedFirst])
    await expect(store.append(syntheticEvent(2))).resolves.toMatchObject({ status: 'ACCEPTED' })
    expect(store.eventCount).toBe(2)
    expect(store.binding).toEqual(expectedBinding)
    expect(store.limits).toEqual(expectedLimits)
    await store.close()

    const reopened = await openFileExecutionEventStore({
      directory,
      binding: expectedBinding,
    })
    expect(reopened.binding).toEqual(expectedBinding)
    expect(reopened.limits).toEqual(expectedLimits)
    expect((await reopened.replay({ limit: 2 })).events).toEqual([
      expectedFirst,
      syntheticEvent(2),
    ])
    await reopened.close()
  })

  it('does not expose mutable binding, limits, cursor or replay event state', async () => {
    const directory = await createDirectory()
    const binding = syntheticBinding()
    const limits = { ...SYNTHETIC_LIMITS, maxEvents: 2, maxReplayEvents: 2 }
    const expectedBinding = structuredClone(binding)
    const expectedLimits = structuredClone(limits)
    const first = syntheticEvent(1)
    const expectedFirst = structuredClone(first)
    const store = await createFileExecutionEventStore({ directory, binding, limits })
    await store.append(first)

    const attemptMutation = (action: () => void): void => {
      try {
        action()
      } catch (error) {
        expect(error).toBeInstanceOf(TypeError)
      }
    }
    attemptMutation(() => {
      const exposed = store.binding as unknown as Record<string, unknown>
      exposed.runtimeId = 'runtime-mutated'
    })
    attemptMutation(() => {
      const exposed = store.binding.contract as unknown as Record<string, unknown>
      exposed.taskId = 'task-mutated'
    })
    attemptMutation(() => {
      const exposed = store.limits as unknown as Record<string, number>
      exposed.maxEvents = 1
      exposed.maxReplayEvents = 1
    })

    const firstPage = await store.replay({ limit: 2 })
    const expectedFirstCursor = structuredClone(firstPage.cursor)
    attemptMutation(() => {
      const exposed = firstPage.events[0] as unknown as Record<string, unknown>
      exposed.eventId = 'event-mutated'
      const payload = exposed.payload as Record<string, unknown>
      payload.summary = 'mutated through replay output'
    })
    attemptMutation(() => {
      const exposed = firstPage.cursor as unknown as Record<string, unknown>
      exposed.sequence = 99
      exposed.stateHash = HASH_C
    })

    expect(store.binding).toEqual(expectedBinding)
    expect(store.limits).toEqual(expectedLimits)
    expect(store.cursor).toEqual(expectedFirstCursor)
    expect((await store.replay({ limit: 2 })).events).toEqual([expectedFirst])
    await expect(store.append(syntheticEvent(2))).resolves.toMatchObject({ status: 'ACCEPTED' })
    expect((await store.replay({ limit: 2 })).events).toEqual([
      expectedFirst,
      syntheticEvent(2),
    ])
    await store.close()

    const reopened = await openFileExecutionEventStore({ directory, binding: expectedBinding })
    expect(reopened.binding).toEqual(expectedBinding)
    expect(reopened.limits).toEqual(expectedLimits)
    expect((await reopened.replay({ limit: 2 })).events).toEqual([
      expectedFirst,
      syntheticEvent(2),
    ])
    await reopened.close()
  })

  it('keeps all Phase 1 source, fixtures and benchmark free of project or model specialization', () => {
    const packageRoot = resolve(import.meta.dirname, '..')
    const collect = (directory: string): string[] => readdirSync(directory, {
      withFileTypes: true,
    }).flatMap(entry => {
      const path = join(directory, entry.name)
      return entry.isDirectory()
        ? collect(path)
        : /\.(?:ts|mjs)$/.test(entry.name) ? [path] : []
    })
    const files = [
      ...collect(resolve(packageRoot, 'src')),
      ...collect(resolve(packageRoot, 'tests')),
      resolve(packageRoot, 'benchmarks/phase1-event-store.mjs'),
    ]
    const productionFiles = collect(resolve(packageRoot, 'src'))
    const productionText = productionFiles.map(path => readFileSync(path, 'utf8')).join('\n')
    const text = files.map(path => readFileSync(path, 'utf8')).join('\n')
    const forbidden = [
      ['A', 'T', 'P'].join(''),
      ['E', 'T', '6', '8', '0', '1'].join(''),
      ['e', 'T', 'i', 'm', 'e', 'r'].join(''),
      ['M', 'C', 'U'].join(''),
      ['O', 'p', 'e', 'n', 'A', 'I'].join(''),
      ['C', 'h', 'a', 't', 'G', 'P', 'T'].join(''),
      ['C', 'l', 'a', 'u', 'd', 'e'].join(''),
      ['D', 'e', 'e', 'p', 'S', 'e', 'e', 'k'].join(''),
      ['G', 'e', 'm', 'i', 'n', 'i'].join(''),
      ['C', 'o', 'd', 'e', 'x'].join(''),
      ['G', 'i', 't', 'H', 'u', 'b'].join(''),
      ['G', 'o', 'o', 'g', 'l', 'e'].join(''),
    ]
    for (const term of forbidden) expect(text).not.toContain(term)

    expect(productionText).not.toMatch(/\bfetch\b/)
    const moduleSpecifiers = [...productionText.matchAll(
      /(?:from\s+|import\s*(?:\(\s*)?)['"]([^'"]+)['"]/g,
    )].map(match => match[1]!.toLowerCase())
    for (const specifier of moduleSpecifiers) {
      expect(specifier).not.toMatch(/^node:https?(?:\/|$)/)
      expect(specifier).not.toMatch(
        /(?:governance[-_]?runtime|architecture|rule|knowledge|gate|context)/,
      )
    }
  })
})
