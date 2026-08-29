import { describe, expect, it, vi } from 'vitest'
import {
  SUPERVISION_READINESS_RECEIPT_SCHEMA,
  canonicalJson,
  supervisionFingerprint,
  type ExecutionEventEnvelopeV01,
  type SupervisionReadinessReceiptV01,
} from '@agent-harness/execution-supervisor'
import GovernanceRuntimeService from '../src/service.js'
import { GovernanceTurnObservationStore } from '../src/turn-observation-store.js'

const readiness = (): SupervisionReadinessReceiptV01 => ({
  schema: SUPERVISION_READINESS_RECEIPT_SCHEMA,
  requestId: 'request-1',
  runtimeId: 'runtime-1',
  projectId: 'project-1',
  taskId: 'task-1',
  turnId: 'turn-1',
  agentId: 'agent-1',
  contextHash: 'a'.repeat(64),
  contractHash: 'b'.repeat(64),
  cursor: { sequence: 2, stateHash: 'c'.repeat(64) },
  ledgerStatusHash: 'd'.repeat(64),
  decisionHash: 'e'.repeat(64),
  taskEndEventId: 'event-2',
  taskEndTimestamp: '2026-08-29T10:00:00.000Z',
  receiptHash: 'f'.repeat(64),
  receiptRef: `supervision-readiness://sha256:${'f'.repeat(64)}`,
})

const reflection = (receipt = readiness()) => ({
  contractVersion: '0.1',
  taskId: receipt.taskId,
  turnId: receipt.turnId,
  providerId: 'runtime-provider',
  createdAt: '2026-08-29T10:00:01.000Z',
  journalRef: 'governance-journal://task/task-1/turn/turn-1',
  inputFingerprint: 'reflection-input',
  readinessBinding: {
    ref: receipt.receiptRef,
    fingerprint: supervisionFingerprint(receipt.receiptHash),
  },
  result: {
    contractVersion: '0.1',
    taskId: receipt.taskId,
    turnId: receipt.turnId,
    context: { progress: '', decisions: [], confirmed: [], assumptions: [], openIssues: [], next: [], touchedRefs: [] },
    knowledge: { scopeDecision: 'NONE', rationale: '', candidates: [] },
    experience: { scopeDecision: 'NONE', rationale: '', candidates: [] },
    architecture: { scopeDecision: 'NONE', rationale: '', candidates: [] },
    rules: { scopeDecision: 'NONE', rationale: '', candidates: [] },
    evidence: { scopeDecision: 'NONE', rationale: '', candidates: [] },
    workingSet: { keep: [], add: [], remove: [] },
    obligations: { opened: [], resolved: [], unchanged: [] },
  },
} as const)

const closure = (receipt = readiness()) => ({
  contractVersion: '0.1',
  taskId: receipt.taskId,
  turnId: receipt.turnId,
  attemptId: 'attempt-1',
  createdAt: '2026-08-29T10:00:02.000Z',
  journalRef: 'governance-journal://task/task-1/turn/turn-1',
  reflectionRef: 'governance-reflection://task/task-1/turn/turn-1',
  inputFingerprint: 'closure-input',
  readinessBinding: {
    ref: receipt.receiptRef,
    fingerprint: supervisionFingerprint(receipt.receiptHash),
  },
  status: 'COMPLETE',
  moduleReceipts: [
    'context-closure', 'knowledge-closure', 'experience-memory-closure', 'architecture-closure',
    'rules-closure', 'evidence-state-closure', 'working-set-closure', 'obligation-gate-reconcile',
  ].map(moduleId => ({
    moduleId,
    moduleVersion: '0.1.0',
    taskId: receipt.taskId,
    turnId: receipt.turnId,
    idempotencyKey: `key-${moduleId}`,
    status: 'NO_CHANGE' as const,
    writes: [], candidateRefs: [], evidenceRefs: [],
  })),
  missingMandatoryModuleIds: [],
  blockingReasons: [],
} as const)

const session = () => ({
  runtimeId: 'runtime-1', actorId: 'agent-1', projectId: 'project-1', taskId: 'task-1', activeTurnId: 'turn-1',
})

describe('Governance Runtime supervised lifecycle', () => {
  it('accepts canonical reopened bindings but requires exact persisted Kernel readiness', () => {
    const receipt = readiness()
    const storedReflection = reflection(receipt)
    const storedClosure = closure(receipt)
    const service = Object.create(GovernanceRuntimeService.prototype) as any
    service.runtimeContext = {
      agentGovernanceKernel: {
        getReflection: () => storedReflection,
        getClosureReceipt: () => storedClosure,
        getTurn: () => ({ closureReceiptRef: 'governance-closure://task/task-1/turn/turn-1' }),
      },
    }
    const binding = service.buildLifecycleBinding(session(), receipt, storedReflection, storedClosure)
    const reopenedWithCanonicalKeyOrder = JSON.parse(canonicalJson(binding))
    expect(() => service.verifyKernelLifecycleBinding(reopenedWithCanonicalKeyOrder)).not.toThrow()

    storedReflection.readinessBinding.fingerprint = `sha256:${'0'.repeat(64)}`
    expect(() => service.verifyKernelLifecycleBinding(binding)).toThrow('exact supervision readiness')
  })

  it('projects one bounded cursor observation without clearing or duplicating prior observations', async () => {
    const receipt = readiness()
    const events = [1, 2].map(sequence => ({
      sequence,
      eventId: `event-${sequence}`,
      kind: sequence === 1 ? 'TASK_START' : 'TASK_END',
      payloadHash: `${sequence}`.repeat(64),
      payload: {},
    })) as unknown as ExecutionEventEnvelopeV01[]
    const eventStore: any = {
      cursor: { ...receipt.cursor }, eventCount: events.length,
      limits: { maxReplayEvents: 1 },
      replay: vi.fn(({ after }: any) => {
        const start = after?.sequence ?? 0
        const pageEvents = events.filter(event => event.sequence > start).slice(0, 1)
        const cursor = pageEvents.length > 0
          ? { sequence: pageEvents[0]!.sequence, stateHash: receipt.cursor.stateHash }
          : receipt.cursor
        return { events: pageEvents, cursor, hasMore: cursor.sequence < events.length }
      }),
    }
    const service = Object.create(GovernanceRuntimeService.prototype) as any
    service.observations = new GovernanceTurnObservationStore()
    service.runtimeContext = { agentGovernanceKernel: { appendTurnRefs: vi.fn() } }
    service.observations.put({ taskId: 'task-1', turnId: 'turn-1', kind: 'TASK_INPUT', text: 'keep me' })

    await service.projectTrustedExecutionObservations(session(), 'turn-1', eventStore, receipt)
    await service.projectTrustedExecutionObservations(session(), 'turn-1', eventStore, receipt)

    expect(service.observations.list('task-1', 'turn-1')).toHaveLength(2)
    expect(service.observations.list('task-1', 'turn-1')[0].text).toBe('keep me')
    expect(service.runtimeContext.agentGovernanceKernel.appendTurnRefs).toHaveBeenCalledTimes(1)
  })

  it('keeps the Turn active when the Event Store advances during close', async () => {
    const receipt = readiness()
    const storedReflection = reflection(receipt)
    const storedClosure = closure(receipt)
    const eventStore: any = {
      binding: { turnId: 'turn-1' },
      cursor: { ...receipt.cursor },
      finalization: undefined,
    }
    const ledger: any = {
      binding: { turnId: 'turn-1' },
      synchronize: vi.fn(),
      getCompletionDecision: vi.fn(() => ({
        status: 'READY_TO_CLOSE', pendingObligationIds: [], violatedObligationIds: [], blockerRefs: [], evidenceRefs: [],
      })),
      prepareReadiness: vi.fn(async () => receipt),
      getReadinessReceipt: vi.fn(() => receipt),
      attachLifecycleClosure: vi.fn(() => {
        if (eventStore.cursor.sequence !== receipt.cursor.sequence) {
          throw new Error('latest durable cursor changed')
        }
        return { status: 'COMPLETE' }
      }),
    }
    const runtimeSession: any = { ...session(), supervision: { eventStore, ledger } }
    const service = Object.create(GovernanceRuntimeService.prototype) as any
    service.sessions = new Map([['runtime-1', runtimeSession]])
    service.reflectionJobs = new Map()
    service.closeJobs = new Map()
    service.observations = new GovernanceTurnObservationStore()
    service.runtimeContext = {
      agentGovernanceKernel: {
        getReflection: () => storedReflection,
        closeTurn: vi.fn(() => {
          eventStore.cursor = { sequence: 3, stateHash: '9'.repeat(64) }
          return storedClosure
        }),
        getTurn: () => ({ closureReceiptRef: 'governance-closure://task/task-1/turn/turn-1' }),
        getUnresolvedTurns: () => [],
      },
      autoGovernanceEngine: {
        buildContextEnvelope: () => ({ route: { knowledgeIds: [], architectureIds: [], ruleIds: [] }, applicableGateIds: [] }),
        completeTask: vi.fn(),
      },
    }

    await expect(service.closeTurn({ runtimeId: 'runtime-1', turnId: 'turn-1' }))
      .rejects.toThrow('latest durable cursor changed')
    expect(ledger.prepareReadiness).toHaveBeenCalledTimes(1)
    expect(ledger.attachLifecycleClosure).toHaveBeenCalledTimes(1)
    expect(runtimeSession.activeTurnId).toBe('turn-1')
    expect(service.completeTask('runtime-1')).toMatchObject({ status: 'BLOCKED' })
  })

  it('revalidates the durable seal before task completion admission', async () => {
    const autoComplete = vi.fn(() => ({ status: 'COMPLETED' }))
    const eventStore: any = { finalization: { finalizationRef: 'closure-ref' } }
    const ledger: any = {
      synchronize: vi.fn(() => { eventStore.finalization = undefined }),
      getCompletionDecision: () => ({ status: 'COMPLETE', closureRef: 'closure-ref' }),
    }
    const service = Object.create(GovernanceRuntimeService.prototype) as any
    service.sessions = new Map([['runtime-1', {
      ...session(), activeTurnId: undefined, supervision: { eventStore, ledger },
    }]])
    service.runtimeContext = {
      agentGovernanceKernel: { getUnresolvedTurns: () => [] },
      autoGovernanceEngine: { completeTask: autoComplete },
    }

    await expect(service.completeTask('runtime-1')).resolves.toMatchObject({ status: 'BLOCKED' })
    expect(ledger.synchronize).toHaveBeenCalledOnce()
    expect(autoComplete).not.toHaveBeenCalled()
  })

  it('never lets an old supervised Turn authorize a newer active Turn', async () => {
    const closeKernel = vi.fn()
    const service = Object.create(GovernanceRuntimeService.prototype) as any
    service.sessions = new Map([['runtime-1', {
      ...session(),
      activeTurnId: 'turn-2',
      supervision: {
        eventStore: { binding: { turnId: 'turn-1' } },
        ledger: {
          binding: { turnId: 'turn-1' },
          getCompletionDecision: () => ({ status: 'COMPLETE' }),
        },
      },
    }]])
    service.runtimeContext = { agentGovernanceKernel: { closeTurn: closeKernel } }

    await expect(service.closeTurn({ runtimeId: 'runtime-1', turnId: 'turn-2' }))
      .rejects.toThrow('cannot authorize a different Turn')
    expect(closeKernel).not.toHaveBeenCalled()
  })

  it('rejects an existing Runtime session with a different contextHash', async () => {
    const service = Object.create(GovernanceRuntimeService.prototype) as any
    const runtimeSession = { ...session(), contextHash: 'a'.repeat(64) }
    const eventStore: any = {
      binding: {
        runtimeId: 'runtime-1', turnId: 'turn-1',
        contract: {
          projectId: 'project-1', taskId: 'task-1', agentId: 'agent-1',
          contextHash: 'b'.repeat(64),
        },
      },
    }

    await expect(service.bindSupervision(runtimeSession, eventStore, undefined, true))
      .rejects.toThrow('session Context')
  })
})
