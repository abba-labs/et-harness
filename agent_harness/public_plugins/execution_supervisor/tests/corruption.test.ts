import { readFile, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'
import {
  ExecutionEventStoreError,
  canonicalJson,
  hashCanonicalJson,
  createFileExecutionEventStore,
  openFileExecutionEventStore,
} from '../src/index.js'
import {
  HASH_C,
  SYNTHETIC_LIMITS,
  createSyntheticTempDirectory,
  removeSyntheticTempDirectory,
  storeSnapshot,
  syntheticBinding,
  syntheticEvent,
} from './fixtures/synthetic-fixtures.js'

const directories: string[] = []

const createDirectory = async (): Promise<string> => {
  const directory = await createSyntheticTempDirectory('corruption-')
  directories.push(directory)
  return directory
}

afterEach(async () => {
  await Promise.all(directories.splice(0).map(removeSyntheticTempDirectory))
})

type MutableRecord = Record<string, unknown>

const readRecords = async (directory: string): Promise<MutableRecord[]> => {
  const text = await readFile(resolve(directory, 'events.jsonl'), 'utf8')
  return text.trimEnd().split('\n').map(line => JSON.parse(line) as MutableRecord)
}

const writeRecords = async (
  directory: string,
  records: readonly MutableRecord[],
): Promise<void> => {
  const text = records.map(record => canonicalJson(record)).join('\n') + '\n'
  await writeFile(resolve(directory, 'events.jsonl'), text, 'utf8')
}

const envelopeOf = (record: MutableRecord): MutableRecord => {
  const envelope = record.envelope ?? record.event
  if (typeof envelope !== 'object' || envelope === null || Array.isArray(envelope)) {
    throw new Error('Phase 1 record did not contain an envelope object')
  }
  return envelope as MutableRecord
}

const setEnvelopeHash = (record: MutableRecord, value: string): void => {
  if ('envelopeHash' in record) {
    record.envelopeHash = value
    return
  }
  if ('eventHash' in record) {
    record.eventHash = value
    return
  }
  throw new Error('Phase 1 record did not contain an envelope hash')
}

const recomputeStateHash = (record: MutableRecord): void => {
  const { stateHash: _stateHash, ...core } = record
  record.stateHash = hashCanonicalJson(core)
}

const corruptAndExpect = async (input: {
  readonly mutate: (directory: string) => Promise<void>
  readonly code: string
  readonly field?: string
  readonly requireOffset?: boolean
}): Promise<void> => {
  const directory = await createDirectory()
  const binding = syntheticBinding()
  const store = await createFileExecutionEventStore({
    directory,
    binding,
    limits: SYNTHETIC_LIMITS,
  })
  for (let sequence = 1; sequence <= 3; sequence += 1) {
    await store.append(syntheticEvent(sequence))
  }
  await store.close()
  await input.mutate(directory)
  const corrupted = await storeSnapshot(directory)

  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      await openFileExecutionEventStore({ directory, binding })
      throw new Error(`Expected ${input.code}`)
    } catch (error) {
      expect(error).toBeInstanceOf(ExecutionEventStoreError)
      const storeError = error as ExecutionEventStoreError
      expect(storeError.code).toBe(input.code)
      expect(storeError.message.length).toBeGreaterThan(0)
      if (input.field !== undefined) expect(storeError.field).toContain(input.field)
      if (input.requireOffset !== false) {
        expect(storeError.offset).toEqual(expect.any(Number))
        expect(storeError.offset).toBeGreaterThanOrEqual(0)
      }
      expect(await storeSnapshot(directory)).toEqual(corrupted)
    }
  }
}

describe('Phase 1 persisted store corruption', () => {
  it('fails repeatedly on a truncated manifest without repairing it', async () => {
    await corruptAndExpect({
      code: 'STORE_TRUNCATED_RECORD',
      field: 'manifest',
      requireOffset: false,
      mutate: async directory => {
        const path = resolve(directory, 'manifest.json')
        const bytes = await readFile(path)
        await writeFile(path, bytes.subarray(0, bytes.length - 1))
      },
    })
  })

  it('fails repeatedly on invalid manifest JSON', async () => {
    await corruptAndExpect({
      code: 'STORE_INVALID_CANONICAL_JSON',
      field: 'manifest',
      requireOffset: false,
      mutate: async directory => {
        await writeFile(resolve(directory, 'manifest.json'), '{"broken":true\n', 'utf8')
      },
    })
  })

  it('fails repeatedly on valid but non-canonical manifest JSON', async () => {
    await corruptAndExpect({
      code: 'STORE_INVALID_CANONICAL_JSON',
      field: 'manifest',
      requireOffset: false,
      mutate: async directory => {
        const path = resolve(directory, 'manifest.json')
        const text = await readFile(path, 'utf8')
        await writeFile(path, ` ${text}`, 'utf8')
      },
    })
  })

  it.each([
    'bindingHash',
    'contractHash',
    'genesisStateHash',
  ] as const)('fails repeatedly on a mismatched manifest %s', async field => {
    await corruptAndExpect({
      code: 'STORE_STATE_HASH_MISMATCH',
      field: `manifest.${field}`,
      requireOffset: false,
      mutate: async directory => {
        const path = resolve(directory, 'manifest.json')
        const manifest = JSON.parse((await readFile(path, 'utf8')).trimEnd()) as MutableRecord
        manifest[field] = HASH_C
        await writeFile(path, `${canonicalJson(manifest)}\n`, 'utf8')
      },
    })
  })

  it('fails repeatedly on a truncated final record without repairing it', async () => {
    await corruptAndExpect({
      code: 'STORE_TRUNCATED_RECORD',
      mutate: async directory => {
        const path = resolve(directory, 'events.jsonl')
        const bytes = await readFile(path)
        await writeFile(path, bytes.subarray(0, bytes.length - 20))
      },
    })
  })

  it('fails repeatedly on invalid JSON with structured offset metadata', async () => {
    await corruptAndExpect({
      code: 'STORE_INVALID_CANONICAL_JSON',
      mutate: async directory => {
        const path = resolve(directory, 'events.jsonl')
        const lines = (await readFile(path, 'utf8')).trimEnd().split('\n')
        lines[1] = '{"broken":true'
        await writeFile(path, lines.join('\n') + '\n', 'utf8')
      },
    })
  })

  it('fails repeatedly on valid but non-canonical JSON', async () => {
    await corruptAndExpect({
      code: 'STORE_INVALID_CANONICAL_JSON',
      mutate: async directory => {
        const path = resolve(directory, 'events.jsonl')
        const lines = (await readFile(path, 'utf8')).trimEnd().split('\n')
        lines[0] = ` ${lines[0]}`
        await writeFile(path, lines.join('\n') + '\n', 'utf8')
      },
    })
  })

  it('detects a wrong complete-envelope hash', async () => {
    await corruptAndExpect({
      code: 'EVENT_ID_INTEGRITY_CONFLICT',
      field: 'envelopeHash',
      mutate: async directory => {
        const records = await readRecords(directory)
        setEnvelopeHash(records[1]!, HASH_C)
        await writeRecords(directory, records)
      },
    })
  })

  it('detects a wrong previous state hash', async () => {
    await corruptAndExpect({
      code: 'STORE_EVENT_CHAIN_MISMATCH',
      field: 'previousStateHash',
      mutate: async directory => {
        const records = await readRecords(directory)
        records[1]!.previousStateHash = HASH_C
        recomputeStateHash(records[1]!)
        await writeRecords(directory, records)
      },
    })
  })

  it('detects a wrong current state hash', async () => {
    await corruptAndExpect({
      code: 'STORE_STATE_HASH_MISMATCH',
      field: 'stateHash',
      mutate: async directory => {
        const records = await readRecords(directory)
        records[1]!.stateHash = HASH_C
        await writeRecords(directory, records)
      },
    })
  })

  it('detects a missing middle record', async () => {
    await corruptAndExpect({
      code: 'SEQUENCE_GAP',
      mutate: async directory => {
        const records = await readRecords(directory)
        records.splice(1, 1)
        await writeRecords(directory, records)
      },
    })
  })

  it('detects reordered records', async () => {
    await corruptAndExpect({
      code: 'SEQUENCE_GAP',
      mutate: async directory => {
        const records = await readRecords(directory)
        const first = records[0]!
        records[0] = records[1]!
        records[1] = first
        await writeRecords(directory, records)
      },
    })
  })

  it('detects a modified otherwise valid event envelope', async () => {
    await corruptAndExpect({
      code: 'EVENT_ID_INTEGRITY_CONFLICT',
      mutate: async directory => {
        const records = await readRecords(directory)
        const envelope = envelopeOf(records[1]!)
        const payload = {
          ...(envelope.payload as MutableRecord),
          summary: 'modified persisted observation',
        }
        envelope.payload = payload
        envelope.payloadHash = hashCanonicalJson(payload)
        await writeRecords(directory, records)
      },
    })
  })

  it('detects an invalid persisted sequence/cursor', async () => {
    await corruptAndExpect({
      code: 'SEQUENCE_GAP',
      field: 'sequence',
      mutate: async directory => {
        const records = await readRecords(directory)
        const envelope = envelopeOf(records[1]!)
        envelope.sequence = 9
        setEnvelopeHash(records[1]!, hashCanonicalJson(envelope))
        recomputeStateHash(records[1]!)
        await writeRecords(directory, records)
      },
    })
  })
})
