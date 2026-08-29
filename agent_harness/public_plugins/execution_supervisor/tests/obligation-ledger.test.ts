import { afterEach, describe, expect, it } from 'vitest'
import {
  createExecutionObligationLedger,
  createFileExecutionEventStore,
  validateObligationLedgerContribution,
  type ResourceReceiptV01,
  type TaskSupervisionContractV01,
} from '../src/index.js'
import {
  HASH_C,
  SYNTHETIC_LIMITS,
  createSyntheticTempDirectory,
  removeSyntheticTempDirectory,
  syntheticBinding,
  syntheticContract,
  syntheticEvent,
} from './fixtures/synthetic-fixtures.js'

const directories: string[] = []

const createDirectory = async (): Promise<string> => {
  const directory = await createSyntheticTempDirectory('obligation-ledger-')
  directories.push(directory)
  return directory
}

afterEach(async () => {
  await Promise.all(directories.splice(0).map(removeSyntheticTempDirectory))
})

const requiredResourceContract = (): TaskSupervisionContractV01 => syntheticContract({
  obligations: [{
    id: 'OBL-READ-PRIMARY',
    kind: 'REQUIRED_RESOURCE',
    severity: 'MUST',
    sourceRefs: ['contract://synthetic/required-resource'],
    target: {
      resourceId: 'resource-required',
      revision: 'revision-required-001',
      contentHash: HASH_C,
    },
    satisfaction: {
      acceptedProviderIds: ['provider-trusted'],
      acceptedDispositions: ['FOUND'],
      requireContentHash: true,
    },
  }],
})

const resourceReceipt = (
  overrides: Partial<ResourceReceiptV01> = {},
): ResourceReceiptV01 => ({
  provider: 'provider-trusted',
  resourceId: 'resource-required',
  revision: 'revision-required-001',
  contentHash: HASH_C,
  disposition: 'FOUND',
  purpose: 'Satisfy the declared synthetic resource obligation.',
  claimRefs: [],
  ...overrides,
})

describe('Phase 2 Obligation Ledger required-resource evaluation', () => {
  it('rejects SOURCE_DISPOSITION semantics disguised as a required read', () => {
    const contract = requiredResourceContract()
    const obligation = contract.obligations[0]!
    const result = validateObligationLedgerContribution({
      ...contract,
      obligations: [{
        ...obligation,
        satisfaction: {
          acceptedProviderIds: ['provider-trusted'],
          acceptedDispositions: ['UNAVAILABLE'],
        },
      }],
    })

    expect(result.valid).toBe(false)
    if (!result.valid) {
      expect(result.issues.map(issue => issue.code))
        .toContain('LEDGER_REQUIRED_RESOURCE_REQUIRES_FOUND')
    }
  })

  it('rejects ambiguous multiple WRITE_SCOPE contributions', () => {
    const template = {
      id: 'OBL-WRITE-A',
      kind: 'WRITE_SCOPE',
      severity: 'MUST',
      sourceRefs: [],
      target: { allowedResourceIds: ['resource-a'] },
      satisfaction: { requireInScope: true },
    } as const
    const result = validateObligationLedgerContribution(syntheticContract({
      obligations: [template, { ...template, id: 'OBL-WRITE-B' }],
    }))

    expect(result.valid).toBe(false)
    if (!result.valid) {
      expect(result.issues.map(issue => issue.code))
        .toContain('LEDGER_MULTIPLE_WRITE_SCOPES_UNSUPPORTED')
    }
  })

  it('keeps missing and non-matching reads PENDING, then accepts only the matching receipt', async () => {
    const directory = await createDirectory()
    const binding = syntheticBinding({ contract: requiredResourceContract() })
    const eventStore = await createFileExecutionEventStore({
      directory,
      binding,
      limits: SYNTHETIC_LIMITS,
    })
    const ledger = await createExecutionObligationLedger({ eventStore })

    expect(ledger.getStatus()).toMatchObject({
      cursor: { sequence: 0 },
      pendingObligationIds: ['OBL-READ-PRIMARY'],
      blockedObligationIds: [],
      satisfiedObligationIds: [],
      violatedObligationIds: [],
      obligations: [{ obligationId: 'OBL-READ-PRIMARY', state: 'PENDING' }],
    })

    const nonMatchingReceipts: ResourceReceiptV01[] = [
      resourceReceipt({ provider: 'provider-untrusted' }),
      resourceReceipt({ resourceId: 'resource-other' }),
      resourceReceipt({ disposition: 'NO_MATCH' }),
      resourceReceipt({ revision: 'revision-other' }),
      resourceReceipt({ contentHash: 'd'.repeat(64) }),
    ]
    for (const [index, receipt] of nonMatchingReceipts.entries()) {
      await ledger.ingest(syntheticEvent(index + 1, {
        kind: 'RESOURCE_READ',
        payload: { receipt },
      }))
      expect(ledger.getStatus()).toMatchObject({
        cursor: { sequence: index + 1 },
        pendingObligationIds: ['OBL-READ-PRIMARY'],
        satisfiedObligationIds: [],
        obligations: [{ obligationId: 'OBL-READ-PRIMARY', state: 'PENDING' }],
      })
    }

    const beforeRejected = ledger.getStatus()
    const rejected = await ledger.ingest(syntheticEvent(6, {
      contextHash: 'e'.repeat(64),
      kind: 'RESOURCE_READ',
      payload: { receipt: resourceReceipt() },
    }))
    expect(rejected.status).toBe('REJECTED')
    expect(ledger.getStatus()).toEqual(beforeRejected)

    await ledger.ingest(syntheticEvent(6, {
      kind: 'RESOURCE_READ',
      payload: { receipt: resourceReceipt() },
    }))
    expect(ledger.getStatus()).toMatchObject({
      cursor: { sequence: 6 },
      pendingObligationIds: [],
      blockedObligationIds: [],
      satisfiedObligationIds: ['OBL-READ-PRIMARY'],
      violatedObligationIds: [],
      obligations: [{ obligationId: 'OBL-READ-PRIMARY', state: 'SATISFIED' }],
    })

    await eventStore.close()
  })

  it('ignores Assistant self-certification and unblocks dependents without auto-satisfying them', async () => {
    const directory = await createDirectory()
    const contract = syntheticContract({
      obligations: [
        {
          id: 'OBL-READ-PREREQUISITE',
          kind: 'REQUIRED_RESOURCE',
          severity: 'MUST',
          sourceRefs: [],
          target: { resourceId: 'resource-prerequisite' },
          satisfaction: {
            acceptedProviderIds: ['provider-trusted'],
            acceptedDispositions: ['FOUND'],
          },
        },
        {
          id: 'OBL-READ-DEPENDENT',
          kind: 'REQUIRED_RESOURCE',
          severity: 'MUST',
          sourceRefs: [],
          target: { resourceId: 'resource-dependent' },
          satisfaction: {
            acceptedProviderIds: ['provider-trusted'],
            acceptedDispositions: ['FOUND'],
          },
          dependencies: ['OBL-READ-PREREQUISITE'],
        },
      ],
    })
    const binding = syntheticBinding({ contract })
    const eventStore = await createFileExecutionEventStore({
      directory,
      binding,
      limits: SYNTHETIC_LIMITS,
    })
    const ledger = await createExecutionObligationLedger({ eventStore })

    expect(ledger.getStatus()).toMatchObject({
      pendingObligationIds: ['OBL-READ-PREREQUISITE'],
      blockedObligationIds: ['OBL-READ-DEPENDENT'],
    })

    await ledger.ingest(syntheticEvent(1, {
      kind: 'ASSISTANT_MESSAGE',
      payload: {
        obligationId: 'OBL-READ-PREREQUISITE',
        requestedState: 'SATISFIED',
      },
    }))
    expect(ledger.getStatus()).toMatchObject({
      pendingObligationIds: ['OBL-READ-PREREQUISITE'],
      blockedObligationIds: ['OBL-READ-DEPENDENT'],
      satisfiedObligationIds: [],
      obligations: [
        { obligationId: 'OBL-READ-PREREQUISITE', state: 'PENDING' },
        { obligationId: 'OBL-READ-DEPENDENT', state: 'BLOCKED' },
      ],
    })

    await ledger.ingest(syntheticEvent(2, {
      kind: 'RESOURCE_READ',
      payload: {
        receipt: {
          provider: 'provider-trusted',
          resourceId: 'resource-prerequisite',
          disposition: 'FOUND',
          purpose: 'Satisfy the declared prerequisite.',
          claimRefs: [],
        } satisfies ResourceReceiptV01,
      },
    }))
    expect(ledger.getStatus()).toMatchObject({
      pendingObligationIds: ['OBL-READ-DEPENDENT'],
      blockedObligationIds: [],
      satisfiedObligationIds: ['OBL-READ-PREREQUISITE'],
      obligations: [
        { obligationId: 'OBL-READ-PREREQUISITE', state: 'SATISFIED' },
        { obligationId: 'OBL-READ-DEPENDENT', state: 'PENDING' },
      ],
    })

    await eventStore.close()
  })
})
