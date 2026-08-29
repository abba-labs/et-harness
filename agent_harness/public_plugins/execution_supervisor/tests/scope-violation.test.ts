import { afterEach, describe, expect, it } from 'vitest'
import {
  createExecutionObligationLedger,
  createFileExecutionEventStore,
  type MutationReceiptV01,
  type TaskSupervisionContractV01,
} from '../src/index.js'
import {
  SYNTHETIC_LIMITS,
  createSyntheticTempDirectory,
  removeSyntheticTempDirectory,
  syntheticBinding,
  syntheticContract,
  syntheticEvent,
} from './fixtures/synthetic-fixtures.js'

const directories: string[] = []

const createDirectory = async (): Promise<string> => {
  const directory = await createSyntheticTempDirectory('scope-violation-')
  directories.push(directory)
  return directory
}

afterEach(async () => {
  await Promise.all(directories.splice(0).map(removeSyntheticTempDirectory))
})

const writeScopeContract = (): TaskSupervisionContractV01 => syntheticContract({
  obligations: [{
    id: 'OBL-WRITE-SCOPE',
    kind: 'WRITE_SCOPE',
    severity: 'MUST',
    sourceRefs: ['contract://synthetic/write-scope'],
    target: {
      allowedResourceIds: ['resource-allowed'],
      allowedPathPrefixes: ['workspace/allowed/'],
    },
    satisfaction: { requireInScope: true },
  }],
})

const mutationReceipt = (
  overrides: Partial<MutationReceiptV01> = {},
): MutationReceiptV01 => ({
  resourceId: 'resource-allowed',
  path: 'workspace/allowed/result.json',
  action: 'UPDATE',
  scopeDecision: 'ALLOWED',
  executorId: 'executor-synthetic',
  ...overrides,
})

describe('Phase 2 Obligation Ledger write-scope violations', () => {
  it('derives one OUT_OF_SCOPE_WRITE violation instead of trusting an ALLOWED assertion', async () => {
    const directory = await createDirectory()
    const binding = syntheticBinding({ contract: writeScopeContract() })
    const eventStore = await createFileExecutionEventStore({
      directory,
      binding,
      limits: SYNTHETIC_LIMITS,
    })
    const ledger = await createExecutionObligationLedger({ eventStore })
    const maliciousEvent = syntheticEvent(1, {
      kind: 'RESOURCE_WRITE',
      payload: {
        receipt: mutationReceipt({
          resourceId: 'resource-unauthorized',
          path: 'workspace/forbidden/result.json',
          scopeDecision: 'ALLOWED',
        }),
      },
    })

    await ledger.ingest(maliciousEvent)
    await ledger.ingest(maliciousEvent)

    const status = ledger.getStatus()
    expect(status).toMatchObject({
      cursor: { sequence: 1 },
      pendingObligationIds: [],
      blockedObligationIds: [],
      satisfiedObligationIds: [],
      violatedObligationIds: ['OBL-WRITE-SCOPE'],
      obligations: [{ obligationId: 'OBL-WRITE-SCOPE', state: 'VIOLATED' }],
    })
    expect(status.violations).toHaveLength(1)
    expect(status.violations[0]).toMatchObject({
      code: 'OUT_OF_SCOPE_WRITE',
      obligationId: 'OBL-WRITE-SCOPE',
    })

    await ledger.synchronize()
    expect(ledger.getStatus().violations).toEqual(status.violations)
    await eventStore.close()
  })

  it('does not create a violation for a write inside the contributed scope', async () => {
    const directory = await createDirectory()
    const binding = syntheticBinding({ contract: writeScopeContract() })
    const eventStore = await createFileExecutionEventStore({
      directory,
      binding,
      limits: SYNTHETIC_LIMITS,
    })
    const ledger = await createExecutionObligationLedger({ eventStore })

    await ledger.ingest(syntheticEvent(1, {
      kind: 'RESOURCE_WRITE',
      payload: { receipt: mutationReceipt() },
    }))

    expect(ledger.getStatus()).toMatchObject({
      cursor: { sequence: 1 },
      violatedObligationIds: [],
      violations: [],
    })
    await eventStore.close()
  })

  it('fails closed for MOVE when the one-ended receipt cannot prove both endpoints', async () => {
    const directory = await createDirectory()
    const binding = syntheticBinding({ contract: writeScopeContract() })
    const eventStore = await createFileExecutionEventStore({
      directory,
      binding,
      limits: SYNTHETIC_LIMITS,
    })
    const ledger = await createExecutionObligationLedger({ eventStore })

    await ledger.ingest(syntheticEvent(1, {
      kind: 'RESOURCE_WRITE',
      payload: {
        receipt: mutationReceipt({
          action: 'MOVE',
          path: 'workspace/allowed/moved.json',
        }),
      },
    }))

    expect(ledger.getStatus()).toMatchObject({
      violatedObligationIds: ['OBL-WRITE-SCOPE'],
      violations: [{ code: 'OUT_OF_SCOPE_WRITE' }],
    })
    await eventStore.close()
  })
})
