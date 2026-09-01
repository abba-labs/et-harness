import { describe, expect, it, vi } from 'vitest'
import {
  HOST_CAPABILITY_CONTRACT_SCHEMA,
  TASK_SUPERVISION_CONTRACT_SCHEMA,
  type HostCapabilityContractV01,
  type TaskSupervisionContractV01,
} from '@agent-harness/execution-supervisor'
import GovernanceRuntimeService from '../src/service.js'

const host = (
  hostId: string,
  overrides: Partial<HostCapabilityContractV01['capabilities']> = {},
): HostCapabilityContractV01 => ({
  schema: HOST_CAPABILITY_CONTRACT_SCHEMA,
  hostId,
  adapterId: `adapter-${hostId}`,
  capabilities: {
    supportsPreflight: true,
    supportsToolInterception: true,
    supportsStableToolEventId: true,
    supportsResourceHash: true,
    supportsMessageRef: true,
    supportsCrossProcessResume: true,
    ...overrides,
  },
})

const contract = (level: 'AUDIT' | 'ENFORCE' = 'ENFORCE'): TaskSupervisionContractV01 => ({
  schema: TASK_SUPERVISION_CONTRACT_SCHEMA,
  projectId: 'project-1',
  taskId: 'task-1',
  agentId: 'agent-1',
  contextHash: 'a'.repeat(64),
  routeHash: 'b'.repeat(64),
  supervisionLevel: level,
  obligations: [{
    id: 'OBL-WRITE',
    kind: 'WRITE_SCOPE',
    severity: 'MUST',
    sourceRefs: [],
    target: { allowedResourceIds: ['resource-allowed'] },
    satisfaction: { requireInScope: true },
  }],
  evidencePolicies: [],
  completionPolicy: {
    requireAllMustSatisfied: true,
    requireNoViolations: true,
    requireReflection: true,
    requireKnowledgeDecision: true,
    requireContextUpdate: true,
    requireClosureReceipt: true,
    allowShouldWarnings: true,
    requiredClosureModuleIds: [],
  },
})

const servicePrototype = (): any => Object.create(GovernanceRuntimeService.prototype)

describe('Governance Runtime Phase 6 Host enforcement profiles', () => {
  it('binds multiple Hosts to the same public contract with truthful claims', () => {
    const service = servicePrototype()
    const first = service.resolveHostProfile('AUDIT', host('host-a'), false)
    const second = service.resolveHostProfile('AUDIT', host('host-b'), false)
    expect(first).toMatchObject({
      capabilities: { hostId: 'host-a' },
      negotiation: { requestedLevel: 'AUDIT', effectiveLevel: 'AUDIT' },
      claimsMechanicalInterception: false,
    })
    expect(second).toMatchObject({
      capabilities: { hostId: 'host-b' },
      negotiation: { effectiveLevel: 'AUDIT' },
      claimsMechanicalInterception: false,
    })
  })

  it('reports an ENFORCE downgrade and rejects malformed or non-resumable profiles', () => {
    const service = servicePrototype()
    expect(service.resolveHostProfile('ENFORCE', host('audit-host', {
      supportsToolInterception: false,
    }), false)).toMatchObject({
      negotiation: { requestedLevel: 'ENFORCE', effectiveLevel: 'AUDIT' },
      claimsMechanicalInterception: false,
    })
    expect(() => service.resolveHostProfile('ENFORCE', {
      ...host('bad-host'), capabilities: { supportsPreflight: true },
    }, false)).toThrow('Invalid Host capability contract')
    expect(() => service.resolveHostProfile('ENFORCE', host('no-resume', {
      supportsCrossProcessResume: false,
    }), true)).toThrow('does not support cross-process resume')
  })

  it('snapshots Host facts and rejects live profile replacement', async () => {
    const service = servicePrototype()
    const mutable = host('host-a') as any
    const profile = service.resolveHostProfile('ENFORCE', mutable, false)
    mutable.capabilities.supportsPreflight = false
    expect(profile.capabilities.capabilities.supportsPreflight).toBe(true)

    const eventStore: any = {
      binding: {
        runtimeId: 'runtime-1', turnId: 'turn-1', contract: contract(),
      },
    }
    const runtimeSession: any = {
      runtimeId: 'runtime-1', actorId: 'agent-1', projectId: 'project-1', taskId: 'task-1',
      activeTurnId: 'turn-1', contextHash: 'a'.repeat(64),
      supervision: { eventStore, ledger: {}, hostProfile: profile },
    }
    await expect(service.bindSupervision(
      runtimeSession, eventStore, undefined, host('host-a'), true,
    )).resolves.toBeUndefined()
    await expect(service.bindSupervision(
      runtimeSession, eventStore, undefined, host('host-b'), true,
    )).rejects.toThrow('another Host profile')

    const auditEventStore: any = {
      binding: {
        runtimeId: 'runtime-audit', turnId: 'turn-1', contract: contract('AUDIT'),
      },
    }
    const auditProfile = service.resolveHostProfile('AUDIT', host('audit-host'), false)
    const auditSession: any = {
      runtimeId: 'runtime-audit', actorId: 'agent-1', projectId: 'project-1', taskId: 'task-1',
      activeTurnId: 'turn-1', contextHash: 'a'.repeat(64),
      supervision: { eventStore: auditEventStore, ledger: {}, hostProfile: auditProfile },
    }
    await expect(service.bindSupervision(
      auditSession, auditEventStore, undefined, undefined, false,
    )).resolves.toBeUndefined()
    expect(auditSession.supervision.hostProfile).toBe(auditProfile)

    const legacyAuditSession: any = {
      ...auditSession,
      supervision: { eventStore: auditEventStore, ledger: {} },
    }
    await expect(service.bindSupervision(
      legacyAuditSession, auditEventStore, undefined, host('audit-host'), false,
    )).rejects.toThrow('another Host profile')
  })

  it('rejects Host replacement before recovering or closing an active Turn', async () => {
    const service = servicePrototype()
    const eventStore: any = {
      binding: {
        runtimeId: 'runtime-1', turnId: 'turn-1', contract: contract(),
      },
    }
    const runtimeSession: any = {
      runtimeId: 'runtime-1', actorId: 'agent-1', projectId: 'project-1', taskId: 'task-1',
      activeTurnId: 'turn-1', contextHash: 'a'.repeat(64),
      supervision: {
        eventStore,
        ledger: { binding: { turnId: 'turn-1' } },
        hostProfile: service.resolveHostProfile('ENFORCE', host('host-a'), false),
      },
    }
    service.sessions = new Map([['runtime-1', runtimeSession]])
    service.runtimeContext = {
      autoGovernanceEngine: {
        resolveProject: vi.fn(() => ({ projectId: 'project-1' })),
      },
    }
    service.closeKnownTurn = vi.fn()
    service.recoverUnresolvedTurns = vi.fn()

    await expect(service.openTurn({
      runtimeId: 'runtime-1', actorId: 'agent-1', projectId: 'project-1', taskId: 'task-1',
      turnId: 'turn-1', taskText: 'continue task', supervisionEventStore: eventStore,
      hostCapabilities: host('host-b'),
    })).rejects.toThrow('another Host profile')
    expect(service.closeKnownTurn).not.toHaveBeenCalled()
    expect(service.recoverUnresolvedTurns).not.toHaveBeenCalled()
    expect(runtimeSession.activeTurnId).toBe('turn-1')
  })

  it('uses Supervisor scope before Auto Governance only for effective ENFORCE', () => {
    const guardAction = vi.fn(() => undefined)
    const service = servicePrototype()
    const enforceProfile = service.resolveHostProfile('ENFORCE', host('host-a'), false)
    const runtimeSession: any = {
      runtimeId: 'runtime-1', actorId: 'agent-1', projectId: 'project-1', taskId: 'task-1',
      activeTurnId: 'turn-1',
      supervision: {
        eventStore: {},
        ledger: { binding: { contract: contract() } },
        hostProfile: enforceProfile,
      },
    }
    service.sessions = new Map([['runtime-1', runtimeSession]])
    service.runtimeContext = {
      autoGovernanceEngine: {
        guardAction,
        guardGateEvidenceProducer: guardAction,
      },
    }

    expect(service.preflightAction({
      runtimeId: 'runtime-1', turnId: 'turn-1', name: 'write_file', eventRef: 'host-event-1',
      effect: { kind: 'MUTATION', intent: { resourceId: 'resource-forbidden', action: 'UPDATE' } },
    })).toMatchObject({ allowed: false, reason: expect.stringContaining('outside WRITE_SCOPE') })
    expect(guardAction).not.toHaveBeenCalled()

    expect(service.preflightGateEvidenceProducer({
      runtimeId: 'runtime-1', turnId: 'turn-1', name: 'pytest', eventRef: 'host-event-gate',
      capability: 'test.execute', gateId: 'G010.010.010', stepId: 'unit',
    })).toEqual({ allowed: true })
    expect(guardAction).toHaveBeenCalledWith(expect.objectContaining({
      capability: 'test.execute', gateId: 'G010.010.010', stepId: 'unit',
    }))

    runtimeSession.supervision.hostProfile = service.resolveHostProfile('AUDIT', host('host-a'), false)
    expect(service.preflightAction({
      runtimeId: 'runtime-1', turnId: 'turn-1', name: 'write_file',
    })).toEqual({ allowed: true })
    expect(guardAction).toHaveBeenCalledTimes(2)
  })

  it('rejects cross-process recovery when the durable Kernel sessionRef names another Runtime', async () => {
    const service = servicePrototype()
    service.sessions = new Map()
    service.runtimeContext = {
      agentGovernanceKernel: {
        getTurn: vi.fn(() => ({
          agentId: 'agent-1',
          projectBinding: { kind: 'BOUND', projectId: 'project-1' },
          sessionRef: 'governance-runtime://runtime-original',
        })),
        getReflection: vi.fn(() => undefined),
      },
    }
    const eventStore: any = {
      binding: {
        runtimeId: 'runtime-forged',
        turnId: 'turn-1',
        contract: contract('AUDIT'),
      },
    }

    await expect(service.rehydrateSupervisedTurn({
      runtimeId: 'runtime-forged', eventStore,
    })).rejects.toThrow('sessionRef does not match')
  })

  it('fails closed when a Host event targets the wrong Turn or lacks supervision binding', async () => {
    const service = servicePrototype()
    service.sessions = new Map([['runtime-1', {
      runtimeId: 'runtime-1', actorId: 'agent-1', projectId: 'project-1', taskId: 'task-1',
      activeTurnId: 'turn-1',
    }]])
    service.runtimeContext = {
      agentGovernanceKernel: { getTurn: vi.fn(() => ({ status: 'OPEN' })) },
    }

    await expect(service.ingestExecutionEvent({
      runtimeId: 'runtime-1', turnId: 'turn-other', eventId: 'event-1',
      kind: 'TOOL_RESULT', payload: {},
    })).rejects.toThrow('active Turn')
    await expect(service.ingestExecutionEvent({
      runtimeId: 'runtime-1', turnId: 'turn-1', eventId: 'event-1',
      kind: 'TOOL_RESULT', payload: {},
    })).rejects.toThrow('Execution supervision is not bound')
  })
})
