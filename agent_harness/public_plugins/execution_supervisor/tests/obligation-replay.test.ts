import { afterEach, describe, expect, it } from 'vitest'
import {
  createExecutionObligationLedger,
  createFileExecutionEventStore,
  openFileExecutionEventStore,
  type MutationReceiptV01,
  type ResourceReceiptV01,
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
  const directory = await createSyntheticTempDirectory('obligation-replay-')
  directories.push(directory)
  return directory
}

afterEach(async () => {
  await Promise.all(directories.splice(0).map(removeSyntheticTempDirectory))
})

const attemptMutation = (action: () => void): void => {
  try {
    action()
  } catch (error) {
    expect(error).toBeInstanceOf(TypeError)
  }
}

describe('Phase 2 Obligation Ledger replay', () => {
  it('reconstructs the same status and keeps returned snapshots isolated', async () => {
    const directory = await createDirectory()
    const contract = syntheticContract({
      obligations: [
        {
          id: 'OBL-READ-REPLAY',
          kind: 'REQUIRED_RESOURCE',
          severity: 'MUST',
          sourceRefs: [],
          target: { resourceId: 'resource-replay' },
          satisfaction: {
            acceptedProviderIds: ['provider-trusted'],
            acceptedDispositions: ['FOUND'],
          },
        },
        {
          id: 'OBL-WRITE-REPLAY',
          kind: 'WRITE_SCOPE',
          severity: 'MUST',
          sourceRefs: [],
          target: { allowedResourceIds: ['resource-allowed'] },
          satisfaction: { requireInScope: true },
        },
      ],
    })
    const binding = syntheticBinding({ contract })
    const firstStore = await createFileExecutionEventStore({
      directory,
      binding,
      limits: SYNTHETIC_LIMITS,
    })
    const firstLedger = await createExecutionObligationLedger({ eventStore: firstStore })
    const readReceipt: ResourceReceiptV01 = {
      provider: 'provider-trusted',
      resourceId: 'resource-replay',
      disposition: 'FOUND',
      purpose: 'Exercise deterministic replay.',
      claimRefs: [],
    }
    const writeReceipt: MutationReceiptV01 = {
      resourceId: 'resource-outside-scope',
      path: 'workspace/outside/result.json',
      action: 'CREATE',
      scopeDecision: 'ALLOWED',
      executorId: 'executor-synthetic',
    }

    await firstLedger.ingest(syntheticEvent(1, {
      kind: 'RESOURCE_READ',
      payload: { receipt: readReceipt },
    }))
    await firstLedger.ingest(syntheticEvent(2, {
      kind: 'RESOURCE_WRITE',
      payload: { receipt: writeReceipt },
    }))
    const uninterruptedStatus = firstLedger.getStatus()
    expect(uninterruptedStatus).toMatchObject({
      cursor: { sequence: 2 },
      satisfiedObligationIds: ['OBL-READ-REPLAY'],
      violatedObligationIds: ['OBL-WRITE-REPLAY'],
    })
    expect(uninterruptedStatus.violations).toHaveLength(1)
    await firstStore.close()

    const reopenedStore = await openFileExecutionEventStore({ directory, binding })
    const replayedLedger = await createExecutionObligationLedger({ eventStore: reopenedStore })
    await replayedLedger.synchronize()
    const replayedStatus = replayedLedger.getStatus()
    expect(replayedStatus).toEqual(uninterruptedStatus)

    const expectedStatus = structuredClone(replayedStatus)
    attemptMutation(() => {
      const cursor = replayedStatus.cursor as unknown as Record<string, unknown>
      cursor.sequence = 999
    })
    attemptMutation(() => {
      const obligations = replayedStatus.obligations as unknown as Array<Record<string, unknown>>
      obligations[0]!.state = 'VIOLATED'
      obligations.push({ obligationId: 'OBL-INJECTED', state: 'SATISFIED' })
    })
    attemptMutation(() => {
      const violations = replayedStatus.violations as unknown as Array<Record<string, unknown>>
      violations[0]!.code = 'MUTATED'
      violations.push({ code: 'INJECTED' })
    })
    attemptMutation(() => {
      const satisfied = replayedStatus.satisfiedObligationIds as unknown as string[]
      satisfied.push('OBL-INJECTED')
    })

    expect(replayedLedger.getStatus()).toEqual(expectedStatus)
    await replayedLedger.synchronize()
    expect(replayedLedger.getStatus()).toEqual(expectedStatus)
    await reopenedStore.close()
  })
})
