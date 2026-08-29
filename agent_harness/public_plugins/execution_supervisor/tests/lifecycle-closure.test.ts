import { unlink } from 'node:fs/promises'
import { join } from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'
import {
  SUPERVISION_LIFECYCLE_BINDING_SCHEMA,
  createExecutionObligationLedger,
  createFileExecutionEventStore,
  openFileExecutionEventStore,
  supervisionFingerprint,
  type ExecutionEventStoreV01,
  type ExecutionLifecycleAuthorityV01,
  type ResourceReceiptV01,
  type SupervisionLifecycleBindingV01,
  type SupervisionReadinessReceiptV01,
  type TaskSupervisionContractV01,
} from '../src/index.js'
import {
  HASH_A,
  HASH_C,
  SYNTHETIC_LIMITS,
  createSyntheticTempDirectory,
  removeSyntheticTempDirectory,
  syntheticBinding,
  syntheticContract,
  syntheticEvent,
} from './fixtures/synthetic-fixtures.js'

const MODULE_IDS = [
  'context-closure',
  'knowledge-closure',
  'experience-memory-closure',
  'architecture-closure',
  'rules-closure',
  'evidence-state-closure',
  'working-set-closure',
  'obligation-gate-reconcile',
] as const

const directories: string[] = []

afterEach(async () => {
  await Promise.all(directories.splice(0).map(removeSyntheticTempDirectory))
})

const lifecycleContract = (): TaskSupervisionContractV01 => syntheticContract({
  obligations: [{
    id: 'OBL-READ',
    kind: 'REQUIRED_RESOURCE',
    severity: 'MUST',
    sourceRefs: [],
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
  }, {
    id: 'OBL-REFLECTION',
    kind: 'REFLECTION',
    severity: 'MUST',
    sourceRefs: [],
    target: {},
    satisfaction: {},
  }, {
    id: 'OBL-KNOWLEDGE',
    kind: 'KNOWLEDGE_DECISION',
    severity: 'MUST',
    sourceRefs: [],
    target: {},
    satisfaction: {},
    dependencies: ['OBL-REFLECTION'],
  }, {
    id: 'OBL-CONTEXT',
    kind: 'CONTEXT_UPDATE',
    severity: 'MUST',
    sourceRefs: [],
    target: {},
    satisfaction: {},
    dependencies: ['OBL-KNOWLEDGE'],
  }, {
    id: 'OBL-CLOSURE',
    kind: 'CLOSURE',
    severity: 'MUST',
    sourceRefs: [],
    target: {},
    satisfaction: {},
    dependencies: ['OBL-CONTEXT'],
  }],
  completionPolicy: {
    requireAllMustSatisfied: true,
    requireNoViolations: true,
    requireReflection: true,
    requireKnowledgeDecision: true,
    requireContextUpdate: true,
    requireClosureReceipt: true,
    allowShouldWarnings: true,
    requiredClosureModuleIds: MODULE_IDS,
  },
})

const receipt: ResourceReceiptV01 = {
  provider: 'provider-trusted',
  resourceId: 'resource-required',
  revision: 'revision-required-001',
  contentHash: HASH_C,
  disposition: 'FOUND',
  purpose: 'phase5 lifecycle fixture',
  claimRefs: [],
}

const reachReadiness = async (
  ledger: Awaited<ReturnType<typeof createExecutionObligationLedger>>,
): Promise<SupervisionReadinessReceiptV01> => {
  await ledger.ingest(syntheticEvent(1, {
    kind: 'RESOURCE_READ',
    payload: { receipt },
  }))
  await ledger.ingest(syntheticEvent(2, {
    kind: 'TASK_END_REQUEST',
    payload: { requestedBy: 'agent-synthetic' },
  }))
  expect(ledger.getCompletionDecision().status).toBe('READY_TO_CLOSE')
  return ledger.getReadinessReceipt()!
}

const lifecycleBinding = (
  readiness: SupervisionReadinessReceiptV01,
  overrides: Partial<SupervisionLifecycleBindingV01> = {},
): SupervisionLifecycleBindingV01 => ({
  schema: SUPERVISION_LIFECYCLE_BINDING_SCHEMA,
  readinessRef: readiness.receiptRef,
  readinessHash: readiness.receiptHash,
  projectId: 'project-synthetic',
  taskId: 'task-synthetic',
  turnId: 'turn-synthetic',
  agentId: 'agent-synthetic',
  contextHash: HASH_A,
  journalRef: 'governance-journal://task/task-synthetic/turn/turn-synthetic',
  reflection: {
    reflectionRef: 'governance-reflection://task/task-synthetic/turn/turn-synthetic',
    inputFingerprint: 'reflection-input-fingerprint',
    domainDecisions: {
      knowledge: 'NONE',
      experience: 'NONE',
      architecture: 'NONE',
      rules: 'NONE',
      evidence: 'NONE',
    },
  },
  kernelClosureRef: 'governance-closure://task/task-synthetic/turn/turn-synthetic',
  kernelClosureInputFingerprint: 'kernel-closure-input-fingerprint',
  kernelClosureCreatedAt: '2026-08-29T00:00:03.000Z',
  moduleReceipts: MODULE_IDS.map((moduleId, index) => ({
    moduleId,
    moduleVersion: '0.1',
    status: index === 1 ? 'NO_CHANGE' : 'APPLIED',
    idempotencyKey: `closure-module-${index}`,
  })),
  ...overrides,
})

const createStore = async (
  contract: TaskSupervisionContractV01 = lifecycleContract(),
): Promise<{
  directory: string
  store: ExecutionEventStoreV01
}> => {
  const directory = await createSyntheticTempDirectory('phase5-lifecycle-')
  directories.push(directory)
  return {
    directory,
    store: await createFileExecutionEventStore({
      directory,
      binding: syntheticBinding({ contract }),
      limits: SYNTHETIC_LIMITS,
    }),
  }
}

describe('Phase 5 trusted lifecycle Closure attachment', () => {
  it('does not let execution events or an authority-free caller complete lifecycle obligations', async () => {
    const { store } = await createStore()
    const ledger = await createExecutionObligationLedger({ eventStore: store })
    const readiness = await reachReadiness(ledger)

    expect(ledger.getStatus().pendingObligationIds).toContain('OBL-REFLECTION')
    await expect(ledger.attachLifecycleClosure(lifecycleBinding(readiness)))
      .rejects.toThrow('Framework lifecycle authority')
    expect(ledger.getCompletionDecision().status).toBe('READY_TO_CLOSE')
    expect(store.finalization).toBeUndefined()
    await store.close()
  })

  it('binds exact readiness to successful modules, finalizes once and replays COMPLETE', async () => {
    const { directory, store } = await createStore()
    let authorityCalls = 0
    const authority: ExecutionLifecycleAuthorityV01 = {
      verifyLifecycleClosure: binding => {
        authorityCalls += 1
        expect(binding.kernelClosureRef).toContain('governance-closure://')
      },
    }
    const ledger = await createExecutionObligationLedger({
      eventStore: store,
      lifecycleAuthority: authority,
    })
    const readiness = await reachReadiness(ledger)
    const binding = lifecycleBinding(readiness)

    await expect(ledger.attachLifecycleClosure(binding)).resolves.toMatchObject({
      status: 'COMPLETE',
      closureRef: expect.stringMatching(/^supervision-closure:\/\/sha256:[0-9a-f]{64}$/),
    })
    expect(authorityCalls).toBe(1)
    expect(store.finalization?.cursor).toEqual(readiness.cursor)
    expect(ledger.getStatus().satisfiedObligationIds).toEqual(expect.arrayContaining([
      'OBL-REFLECTION', 'OBL-KNOWLEDGE', 'OBL-CONTEXT', 'OBL-CLOSURE',
    ]))

    await expect(ledger.attachLifecycleClosure(binding)).resolves.toMatchObject({ status: 'COMPLETE' })
    expect(authorityCalls).toBe(2)
    await expect(store.append(syntheticEvent(3))).rejects.toMatchObject({ code: 'STORE_FINALIZED' })
    await store.close()

    const reopenedStore = await openFileExecutionEventStore({
      directory,
      binding: syntheticBinding({ contract: lifecycleContract() }),
    })
    await expect(createExecutionObligationLedger({ eventStore: reopenedStore }))
      .rejects.toThrow('Framework lifecycle authority')
    const reopenedLedger = await createExecutionObligationLedger({
      eventStore: reopenedStore,
      lifecycleAuthority: authority,
    })
    expect(reopenedLedger.getCompletionDecision()).toMatchObject({ status: 'COMPLETE' })
    await expect(reopenedStore.append(syntheticEvent(3))).rejects.toMatchObject({ code: 'STORE_FINALIZED' })
    await reopenedStore.close()
  })

  it('rejects a stale readiness cursor and an incomplete mandatory module set', async () => {
    const { store } = await createStore()
    const authority: ExecutionLifecycleAuthorityV01 = {
      verifyLifecycleClosure: () => undefined,
    }
    const ledger = await createExecutionObligationLedger({
      eventStore: store,
      lifecycleAuthority: authority,
    })
    const stale = await reachReadiness(ledger)
    await ledger.ingest(syntheticEvent(3, {
      kind: 'TOOL_RESULT',
      payload: { result: 'new durable tail' },
    }))

    await expect(ledger.attachLifecycleClosure(lifecycleBinding(stale)))
      .rejects.toThrow('exact readiness binding')
    const current = ledger.getReadinessReceipt()!
    await expect(ledger.attachLifecycleClosure(lifecycleBinding(current, {
      moduleReceipts: lifecycleBinding(current).moduleReceipts.slice(0, -1),
    }))).rejects.toThrow('exactly the required Closure modules')
    expect(store.finalization).toBeUndefined()
    await store.close()
  })

  it('does not seal when an ignored SHOULD dependency still blocks lifecycle projection', async () => {
    const base = lifecycleContract()
    const contract: TaskSupervisionContractV01 = {
      ...base,
      obligations: [
        ...base.obligations.map(item => item.id === 'OBL-REFLECTION'
          ? { ...item, dependencies: ['OBL-SHOULD-READ'] }
          : item),
        {
          id: 'OBL-SHOULD-READ',
          kind: 'REQUIRED_RESOURCE',
          severity: 'SHOULD',
          sourceRefs: [],
          target: { resourceId: 'optional-resource' },
          satisfaction: {
            acceptedProviderIds: ['provider-trusted'],
            acceptedDispositions: ['FOUND'],
          },
        },
      ],
    }
    const { store } = await createStore(contract)
    const authority: ExecutionLifecycleAuthorityV01 = {
      verifyLifecycleClosure: () => undefined,
    }
    const ledger = await createExecutionObligationLedger({
      eventStore: store,
      lifecycleAuthority: authority,
    })
    const readiness = await reachReadiness(ledger)

    await expect(ledger.attachLifecycleClosure(lifecycleBinding(readiness)))
      .rejects.toThrow('unresolved dependencies')
    expect(store.finalization).toBeUndefined()
    expect(ledger.getCompletionDecision().status).toBe('READY_TO_CLOSE')
    await store.close()
  })

  it('rejects a reduced mandatory Closure module policy before finalization', async () => {
    const base = lifecycleContract()
    const contract: TaskSupervisionContractV01 = {
      ...base,
      completionPolicy: {
        ...base.completionPolicy,
        requiredClosureModuleIds: MODULE_IDS.slice(0, -1),
      },
    }
    const { store } = await createStore(contract)
    const authority: ExecutionLifecycleAuthorityV01 = {
      verifyLifecycleClosure: () => undefined,
    }
    const ledger = await createExecutionObligationLedger({
      eventStore: store,
      lifecycleAuthority: authority,
    })
    const readiness = await reachReadiness(ledger)

    await expect(ledger.attachLifecycleClosure(lifecycleBinding(readiness)))
      .rejects.toThrow('all eight frozen Closure modules')
    expect(store.finalization).toBeUndefined()
    await store.close()
  })

  it('fails closed if a durable finalization disappears after attachment', async () => {
    const { directory, store } = await createStore()
    const authority: ExecutionLifecycleAuthorityV01 = {
      verifyLifecycleClosure: () => undefined,
    }
    const ledger = await createExecutionObligationLedger({
      eventStore: store,
      lifecycleAuthority: authority,
    })
    const readiness = await reachReadiness(ledger)
    await ledger.attachLifecycleClosure(lifecycleBinding(readiness))

    await unlink(join(directory, 'finalization.json'))
    await expect(store.replay({ limit: 10 })).rejects.toMatchObject({ code: 'STORE_CHANGED' })
    await expect(ledger.attachLifecycleClosure(lifecycleBinding(readiness)))
      .rejects.toMatchObject({ code: 'STORE_CHANGED' })
    await store.close()
  })

  it('revalidates the Kernel lifecycle authority on every durable synchronize', async () => {
    const { store } = await createStore()
    let kernelReceiptAvailable = true
    const authority: ExecutionLifecycleAuthorityV01 = {
      verifyLifecycleClosure: () => {
        if (!kernelReceiptAvailable) throw new Error('Kernel Closure receipt is unavailable')
      },
    }
    const ledger = await createExecutionObligationLedger({
      eventStore: store,
      lifecycleAuthority: authority,
    })
    const readiness = await reachReadiness(ledger)
    await ledger.attachLifecycleClosure(lifecycleBinding(readiness))
    kernelReceiptAvailable = false

    await expect(ledger.synchronize()).rejects.toThrow('Kernel Closure receipt is unavailable')
    await store.close()
  })

})
