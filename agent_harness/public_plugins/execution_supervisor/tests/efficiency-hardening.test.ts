import { afterEach, describe, expect, it } from 'vitest'
import {
  EXTERNAL_AGENT_REQUEST_MANIFEST_SCHEMA,
  createExecutionObligationLedger,
  createFileExecutionEventStore,
  createSupervisionReadinessReceipt,
  hashCanonicalJson,
  openFileExecutionEventStore,
  type ResourceReceiptV01,
} from '../src/index.js'
import {
  HASH_C,
  createSyntheticTempDirectory,
  removeSyntheticTempDirectory,
  syntheticBinding,
  syntheticContract,
  syntheticEvent,
} from './fixtures/synthetic-fixtures.js'

const directories: string[] = []

afterEach(async () => {
  await Promise.all(directories.splice(0).map(removeSyntheticTempDirectory))
})

const receipt: ResourceReceiptV01 = {
  provider: 'provider-trusted',
  resourceId: 'resource-required',
  revision: 'revision-required-001',
  contentHash: HASH_C,
  disposition: 'FOUND',
  purpose: 'Exercise deterministic repeated-read compaction.',
  claimRefs: [],
}

describe('Phase 7 bounded incremental Ledger projection', () => {
  it('compacts 1000 identical accepted reads to one representative ref plus access count', async () => {
    const directory = await createSyntheticTempDirectory('phase7-compaction-')
    directories.push(directory)
    const binding = syntheticBinding({
      contract: syntheticContract({
        obligations: [{
          id: 'OBL-READ-PRIMARY',
          kind: 'REQUIRED_RESOURCE',
          severity: 'MUST',
          sourceRefs: [],
          target: {
            resourceId: receipt.resourceId,
            revision: receipt.revision,
            contentHash: receipt.contentHash,
          },
          satisfaction: {
            acceptedProviderIds: [receipt.provider],
            acceptedDispositions: ['FOUND'],
            requireContentHash: true,
          },
        }],
      }),
    })
    const store = await createFileExecutionEventStore({
      directory,
      binding,
      limits: {
        maxEvents: 1_000,
        maxStoreBytes: 32 * 1024 * 1024,
        maxReplayEvents: 127,
      },
    })
    for (let index = 0; index < 1_000; index += 1) {
      const accepted = await store.append(syntheticEvent(index + 1, {
        kind: 'RESOURCE_READ',
        payload: {
          receipt: {
            ...receipt,
            claimRefs: [`claim-${index.toString().padStart(4, '0')}`],
          },
        },
      }))
      expect(accepted.status).toBe('ACCEPTED')
    }
    const ledger = await createExecutionObligationLedger({ eventStore: store })
    const status = ledger.getStatus()
    expect(status.satisfiedObligationIds).toEqual(['OBL-READ-PRIMARY'])
    expect(status.obligations[0]).toMatchObject({
      obligationId: 'OBL-READ-PRIMARY',
      state: 'SATISFIED',
      accessCount: 1_000,
      evidenceRefsTruncated: true,
      eventRefs: ['event-001000'],
    })
    expect(status.obligations[0]?.evidenceRefs).toHaveLength(64)
    expect(JSON.stringify(status.obligations[0]).length).toBeLessThan(2_500)

    await store.close()
    const reopenedStore = await openFileExecutionEventStore({ directory, binding })
    const replayed = await createExecutionObligationLedger({ eventStore: reopenedStore })
    expect(replayed.getStatus()).toEqual(status)
    await reopenedStore.close()
  }, 120_000)

  it('does not count non-matching resource, hash or disposition as compacted access', async () => {
    const directory = await createSyntheticTempDirectory('phase7-identity-')
    directories.push(directory)
    const binding = syntheticBinding({
      contract: syntheticContract({
        obligations: [{
          id: 'OBL-READ-PRIMARY',
          kind: 'REQUIRED_RESOURCE',
          severity: 'MUST',
          sourceRefs: [],
          target: { resourceId: receipt.resourceId, contentHash: receipt.contentHash },
          satisfaction: {
            acceptedProviderIds: [receipt.provider],
            acceptedDispositions: ['FOUND'],
            requireContentHash: true,
          },
        }],
      }),
    })
    const store = await createFileExecutionEventStore({
      directory,
      binding,
      limits: { maxEvents: 4, maxStoreBytes: 1024 * 1024, maxReplayEvents: 4 },
    })
    const variants: ResourceReceiptV01[] = [
      { ...receipt, resourceId: 'resource-other' },
      { ...receipt, contentHash: 'd'.repeat(64) },
      { ...receipt, disposition: 'NO_MATCH' },
      receipt,
    ]
    for (const [index, value] of variants.entries()) {
      await store.append(syntheticEvent(index + 1, {
        kind: 'RESOURCE_READ',
        payload: { receipt: value },
      }))
    }
    const ledger = await createExecutionObligationLedger({ eventStore: store })
    expect(ledger.getStatus().obligations[0]).toMatchObject({
      state: 'SATISFIED',
      accessCount: 1,
      eventRefs: ['event-000004'],
    })
    await store.close()
  })

  it('keeps the Phase 6 readiness identity while exposing a compact Phase 7 status', async () => {
    const directory = await createSyntheticTempDirectory('phase7-readiness-compatibility-')
    directories.push(directory)
    const binding = syntheticBinding({
      contract: syntheticContract({
        obligations: [{
          id: 'OBL-READ-PRIMARY',
          kind: 'REQUIRED_RESOURCE',
          severity: 'MUST',
          sourceRefs: [],
          target: { resourceId: receipt.resourceId, contentHash: receipt.contentHash },
          satisfaction: {
            acceptedProviderIds: [receipt.provider],
            acceptedDispositions: ['FOUND'],
            requireContentHash: true,
          },
        }],
      }),
    })
    const store = await createFileExecutionEventStore({
      directory,
      binding,
      limits: { maxEvents: 3, maxStoreBytes: 1024 * 1024, maxReplayEvents: 3 },
    })
    for (let sequence = 1; sequence <= 2; sequence += 1) {
      await store.append(syntheticEvent(sequence, {
        kind: 'RESOURCE_READ',
        payload: { receipt: { ...receipt, claimRefs: [`claim-${sequence}`] } },
      }))
    }
    const taskEnd = syntheticEvent(3, {
      kind: 'TASK_END_REQUEST',
      payload: { requestedBy: 'agent-synthetic' },
    })
    await store.append(taskEnd)
    const ledger = await createExecutionObligationLedger({ eventStore: store })
    const compactStatus = ledger.getStatus()
    const decision = ledger.getCompletionDecision()
    expect(decision.status).toBe('READY_TO_CLOSE')
    expect(compactStatus.obligations[0]).toMatchObject({
      accessCount: 2,
      eventRefs: ['event-000002'],
      evidenceRefs: ['claim-1', 'claim-2'],
    })

    const compactObligation = compactStatus.obligations[0]!
    const {
      accessCount: _accessCount,
      evidenceRefsTruncated: _evidenceRefsTruncated,
      ...legacyObligation
    } = compactObligation
    const legacyStatus = {
      ...compactStatus,
      obligations: [{
        ...legacyObligation,
        eventRefs: ['event-000001', 'event-000002'],
      }],
    }
    const expected = createSupervisionReadinessReceipt({
      binding,
      cursor: ledger.cursor,
      status: legacyStatus,
      decision,
      taskEndEventId: taskEnd.eventId,
      taskEndTimestamp: taskEnd.timestamp,
    })
    expect(ledger.getReadinessReceipt()).toEqual(expected)
    expect(expected.ledgerStatusHash).not.toBe(hashCanonicalJson(compactStatus))
    await store.close()
  })

  it('blocks a previously ready decision while a durable external span is incomplete after replay', async () => {
    const directory = await createSyntheticTempDirectory('phase7-open-span-')
    directories.push(directory)
    const binding = syntheticBinding({
      contract: syntheticContract({
        obligations: [{
          id: 'OBL-READ-PRIMARY',
          kind: 'REQUIRED_RESOURCE',
          severity: 'MUST',
          sourceRefs: [],
          target: { resourceId: receipt.resourceId, contentHash: receipt.contentHash },
          satisfaction: {
            acceptedProviderIds: [receipt.provider],
            acceptedDispositions: ['FOUND'],
            requireContentHash: true,
          },
        }],
      }),
    })
    const store = await createFileExecutionEventStore({
      directory,
      binding,
      limits: { maxEvents: 3, maxStoreBytes: 1024 * 1024, maxReplayEvents: 2 },
    })
    const ledger = await createExecutionObligationLedger({ eventStore: store })
    await ledger.ingest(syntheticEvent(1, {
      kind: 'RESOURCE_READ',
      payload: { receipt },
    }))
    await ledger.ingest(syntheticEvent(2, {
      kind: 'TASK_END_REQUEST',
      payload: { requestedBy: 'agent-synthetic' },
    }))
    expect(ledger.getCompletionDecision().status).toBe('READY_TO_CLOSE')
    await ledger.ingest(syntheticEvent(3, {
      kind: 'USER_MESSAGE',
      payload: {
        requestManifest: { schema: EXTERNAL_AGENT_REQUEST_MANIFEST_SCHEMA },
      },
    }))
    expect(ledger.getCompletionDecision()).toMatchObject({
      status: 'BLOCKED',
      blockerRefs: ['external-agent-span://incomplete'],
    })

    await store.close()
    const reopenedStore = await openFileExecutionEventStore({ directory, binding })
    const replayed = await createExecutionObligationLedger({ eventStore: reopenedStore })
    expect(replayed.getCompletionDecision()).toEqual(ledger.getCompletionDecision())
    await reopenedStore.close()
  })
})
