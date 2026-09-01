import { describe, expect, it, vi } from 'vitest'
import AutoGovernanceEngineService from '../src/service.js'

const emptyRoute = () => ({
  architectureIds: [] as string[],
  ruleIds: [] as string[],
  knowledgeIds: [] as string[],
  gateIds: ['G010.010.010'],
})

const runtimeTask = () => ({
  actorId: 'agent-1',
  projectId: 'project-1',
  taskId: 'task-1',
  goal: 'change governed code',
  codeChangeEpoch: 1,
  codeChangeSeen: true,
  route: emptyRoute(),
  contextContributions: [],
  applicableGateIds: ['G010.010.010'],
  currentPacketIds: [],
})

describe('Gate capability readiness and evidence-producer admission', () => {
  it('fails at task bootstrap when an explicit REVIEW step has no usable provider', () => {
    const runtime = runtimeTask()
    const service = Object.create(AutoGovernanceEngineService.prototype) as any
    service.runtimeContext = {
      contextManager: {
        updateProgressLedger: vi.fn(),
        recordRecent: vi.fn(),
      },
      gateManager: {
        getExecutionPlan: vi.fn(() => ({
          gateId: 'G010.010.010',
          steps: [{ id: 'review', tool: 'review.code', role: 'REVIEW' }],
        })),
      },
      governanceCatalog: {
        listProviders: vi.fn(() => [{
          providerId: 'project.other.review-provider',
          metadata: {
            projectId: 'other-project',
            service: 'otherReviewProvider',
            prepareMethod: 'prepare',
            decisionMethod: 'decide',
          },
        }]),
      },
      get: vi.fn(() => ({ prepare: vi.fn(), decide: vi.fn() })),
    }
    service.resolveProject = vi.fn(() => ({ projectId: 'project-1' }))
    service.ensureRuntimeTask = vi.fn(() => runtime)
    service.routeTask = vi.fn(() => emptyRoute())
    service.buildContextEnvelope = vi.fn(() => ({ text: 'unreachable' }))

    expect(() => service.bootstrapTask({
      actorId: 'agent-1',
      taskId: 'task-1',
      goal: runtime.goal,
      projectId: 'project-1',
    })).toThrow('review.code')
  })

  it('allows only a trusted, applicable EVIDENCE_PRODUCER step to run before Gate PASS', () => {
    const runtime = runtimeTask()
    const service = Object.create(AutoGovernanceEngineService.prototype) as any
    service.runtimeContext = {
      ruleManager: { guardAction: vi.fn(() => ({ allowed: true })) },
      gateManager: {
        getExecutionPlan: vi.fn(() => ({
          gateId: 'G010.010.010',
          steps: [{ id: 'unit', tool: 'test.execute', role: 'EVIDENCE_PRODUCER' }],
        })),
      },
    }
    service.tasks = new Map([['agent-1', runtime]])
    service.pendingReviews = new Map()

    expect(service.guardGateEvidenceProducer({
      actorId: 'agent-1',
      name: 'pytest',
      arguments: ['tests/unit'],
      gateId: 'G010.010.010',
      stepId: 'unit',
      capability: 'test.execute',
    })).toBeUndefined()
    expect(service.guardAction({
      actorId: 'agent-1',
      name: 'pytest',
      arguments: ['tests/unit'],
    })).toContain('no current review packet')
  })

  it('keeps a legacy gate-v0.1 step on the existing Review Packet path', () => {
    const runtime = runtimeTask()
    const prepare = vi.fn(() => ({
      packetId: 'packet-legacy',
      change: { files: ['src/legacy.ts'] },
    }))
    const service = Object.create(AutoGovernanceEngineService.prototype) as any
    service.runtimeContext = {
      gateManager: {
        getExecutionPlan: vi.fn(() => ({
          gateId: 'G010.010.010',
          steps: [{ id: 'legacy-review', tool: 'review.code' }],
        })),
      },
      governanceCatalog: {
        listProviders: vi.fn(() => [{
          providerId: 'public.review-provider',
          metadata: {
            service: 'reviewProvider',
            prepareMethod: 'prepare',
            decisionMethod: 'decide',
          },
        }]),
      },
      contextManager: { addHandles: vi.fn() },
      get: vi.fn(() => ({ prepare, decide: vi.fn() })),
    }
    service.pendingReviews = new Map()
    service.attachPacketContext = vi.fn()

    expect(service.prepareReviewPackets(runtime)).toEqual(['packet-legacy'])
    expect(prepare).toHaveBeenCalledOnce()
    expect(service.pendingReviews.get('packet-legacy')).toMatchObject({
      decision: 'PENDING',
      capability: 'review.code',
    })
  })
})
