import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'
import {
  MANDATORY_CLOSURE_MODULE_IDS,
  type ContentAddressedReadinessBinding,
  type ClosureModule,
  type ClosureModuleInput,
  type ClosureModuleReceipt,
  type ClosureModuleStatus,
  type ReflectionDomain,
  type TurnReflectionProviderInput,
} from '../src/contracts.js'
import { ClosureCoordinator } from '../src/closure-coordinator.js'
import { ClosureModuleRegistry } from '../src/closure-module-registry.js'
import { TurnClosureStore } from '../src/turn-closure-store.js'
import { TurnJournalStore } from '../src/turn-journal-store.js'
import { TurnReflectionController } from '../src/turn-reflection-controller.js'
import { TurnReflectionStore } from '../src/turn-reflection-store.js'

const roots: string[] = []

const none = (domain: ReflectionDomain) => ({
  scopeDecision: 'NONE' as const,
  rationale: `No ${domain} update from this Turn`,
  candidates: [],
})

const noChangeResult = (input: TurnReflectionProviderInput) => ({
  contractVersion: '0.1' as const,
  taskId: input.journal.taskId,
  turnId: input.journal.turnId,
  context: {
    progress: 'Turn work completed and is ready for deterministic closure.',
    decisions: [],
    confirmed: ['Unified Reflection completed'],
    assumptions: [],
    openIssues: [],
    next: ['Apply mandatory closure modules'],
    touchedRefs: input.journal.resourceTouchRefs,
  },
  knowledge: none('knowledge'),
  experience: none('experience'),
  architecture: none('architecture'),
  rules: none('rules'),
  evidence: none('evidence'),
  workingSet: { keep: input.journal.resourceTouchRefs, add: [], remove: [] },
  obligations: { opened: [], resolved: [], unchanged: [] },
})

const readinessBinding = (hex = 'c'): ContentAddressedReadinessBinding => ({
  ref: `supervision-readiness://TASK-1/TURN-1/${hex}`,
  fingerprint: `sha256:${hex.repeat(64)}`,
})

const createRuntime = () => {
  const root = mkdtempSync(join(tmpdir(), 'agent-governance-kernel-closure-'))
  roots.push(root)
  const journal = new TurnJournalStore(root)
  const reflectionStore = new TurnReflectionStore(root)
  const reflection = new TurnReflectionController(journal, reflectionStore)
  const registry = new ClosureModuleRegistry()
  const closureStore = new TurnClosureStore(root)
  const closure = new ClosureCoordinator(journal, reflectionStore, registry, closureStore)
  return { root, journal, reflection, registry, closureStore, closure }
}

const receipt = (
  module: ClosureModule,
  input: ClosureModuleInput,
  status: ClosureModuleStatus = 'NO_CHANGE',
  reason?: string,
): ClosureModuleReceipt => ({
  moduleId: module.id,
  moduleVersion: module.version,
  taskId: input.taskId,
  turnId: input.turnId,
  idempotencyKey: input.idempotencyKey,
  status,
  writes: status === 'APPLIED' ? [`state://${module.id}/${input.turnId}`] : [],
  candidateRefs: [],
  evidenceRefs: [],
  ...(reason ? { reason } : {}),
})

const domainsByModule = {
  'context-closure': ['context'],
  'knowledge-closure': ['knowledge'],
  'experience-memory-closure': ['experience'],
  'architecture-closure': ['architecture'],
  'rules-closure': ['rules'],
  'evidence-state-closure': ['evidence'],
  'working-set-closure': ['working-set'],
  'obligation-gate-reconcile': ['obligations'],
} as const

const registerMandatory = (
  registry: ClosureModuleRegistry,
  calls: Map<string, number>,
  override?: (module: ClosureModule, input: ClosureModuleInput, call: number) => ClosureModuleReceipt,
): void => {
  for (const id of MANDATORY_CLOSURE_MODULE_IDS) {
    const module: ClosureModule = {
      id,
      version: '0.1.0',
      mandatory: true,
      domains: domainsByModule[id],
      apply(input) {
        const call = (calls.get(id) ?? 0) + 1
        calls.set(id, call)
        return override?.(module, input, call) ?? receipt(module, input)
      },
    }
    registry.register(module)
  }
}

const reflectReadyTurn = async (
  journal: TurnJournalStore,
  reflection: TurnReflectionController,
  taskId = 'TASK-1',
  turnId = 'TURN-1',
): Promise<void> => {
  journal.beginTurn({ taskId, turnId, agentId: 'AGENT-1' })
  reflection.registerProvider({ providerId: `reflector-${taskId}-${turnId}`, reflect: noChangeResult })
  await reflection.reflectTurn(taskId, turnId)
}

afterEach(() => {
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true })
})

describe('Closure Coordinator', () => {
  it('fails closed before writes when any fixed Mandatory Closure Module is unavailable', async () => {
    const { journal, reflection, closure } = createRuntime()
    await reflectReadyTurn(journal, reflection)

    const result = await closure.closeTurn('TASK-1', 'TURN-1')

    expect(result.status).toBe('PENDING')
    expect(result.moduleReceipts).toHaveLength(0)
    expect(result.missingMandatoryModuleIds).toEqual(MANDATORY_CLOSURE_MODULE_IDS)
    expect(journal.getTurn('TASK-1', 'TURN-1')?.status).toBe('CLOSURE_PENDING')
    expect(journal.getTurn('TASK-1', 'TURN-1')?.closureReceiptRef).toBeUndefined()
  })

  it('runs every Mandatory Closure Module, persists one COMPLETE receipt, then closes the Turn', async () => {
    const { root, journal, reflection, registry, closure } = createRuntime()
    await reflectReadyTurn(journal, reflection)
    const calls = new Map<string, number>()
    registerMandatory(registry, calls)

    const first = await closure.closeTurn('TASK-1', 'TURN-1')
    const second = await closure.closeTurn('TASK-1', 'TURN-1')

    expect(first.status).toBe('COMPLETE')
    expect(first.moduleReceipts).toHaveLength(MANDATORY_CLOSURE_MODULE_IDS.length)
    expect(second.attemptId).toBe(first.attemptId)
    expect(journal.getTurn('TASK-1', 'TURN-1')?.status).toBe('CLOSED')
    expect(journal.getTurn('TASK-1', 'TURN-1')?.closureReceiptRef).toBe(
      'governance-closure://task/TASK-1/turn/TURN-1',
    )
    for (const id of MANDATORY_CLOSURE_MODULE_IDS) expect(calls.get(id)).toBe(1)

    const reloaded = new TurnClosureStore(root).get('TASK-1', 'TURN-1')
    expect(reloaded?.status).toBe('COMPLETE')
    expect(reloaded?.moduleReceipts).toHaveLength(MANDATORY_CLOSURE_MODULE_IDS.length)
  })

  it('persists the exact Reflection readiness binding in Closure and rejects CLOSED rebinding', async () => {
    const { root, journal, reflection, registry, closure } = createRuntime()
    journal.beginTurn({ taskId: 'TASK-1', turnId: 'TURN-BOUND', agentId: 'AGENT-1' })
    reflection.registerProvider({ providerId: 'bound-reflector', reflect: noChangeResult })
    const binding = readinessBinding()
    await reflection.reflectTurn('TASK-1', 'TURN-BOUND', { readinessBinding: binding })

    const calls = new Map<string, number>()
    let observed: ContentAddressedReadinessBinding | undefined
    registerMandatory(registry, calls, (module, input) => {
      observed = input.readinessBinding
      return receipt(module, input)
    })
    const completed = await closure.closeTurn('TASK-1', 'TURN-BOUND')

    expect(completed.status).toBe('COMPLETE')
    expect(completed.readinessBinding).toEqual(binding)
    expect(observed).toEqual(binding)
    expect(new TurnClosureStore(root).get('TASK-1', 'TURN-BOUND')?.readinessBinding).toEqual(binding)

    await expect(reflection.reflectTurn('TASK-1', 'TURN-BOUND', {
      readinessBinding: readinessBinding('d'),
    })).rejects.toThrow('different sealed input')
    for (const id of MANDATORY_CLOSURE_MODULE_IDS) expect(calls.get(id)).toBe(1)
  })

  it('replays only failed modules and reuses successful idempotent receipts', async () => {
    const { journal, reflection, registry, closure } = createRuntime()
    await reflectReadyTurn(journal, reflection)
    const calls = new Map<string, number>()
    registerMandatory(registry, calls, (module, input, call) => {
      if (module.id === 'knowledge-closure' && call === 1) {
        return receipt(module, input, 'FAILED', 'synthetic Knowledge Manager outage')
      }
      return receipt(module, input, 'APPLIED')
    })

    const first = await closure.closeTurn('TASK-1', 'TURN-1')
    expect(first.status).toBe('PENDING')
    expect(journal.getTurn('TASK-1', 'TURN-1')?.status).toBe('CLOSURE_PENDING')

    const second = await closure.closeTurn('TASK-1', 'TURN-1')
    expect(second.status).toBe('COMPLETE')
    expect(journal.getTurn('TASK-1', 'TURN-1')?.status).toBe('CLOSED')
    expect(calls.get('knowledge-closure')).toBe(2)
    for (const id of MANDATORY_CLOSURE_MODULE_IDS) {
      if (id !== 'knowledge-closure') expect(calls.get(id)).toBe(1)
    }
  })

  it('normalizes an invalid module receipt into FAILED and keeps Closure pending', async () => {
    const { journal, reflection, registry, closure } = createRuntime()
    await reflectReadyTurn(journal, reflection)
    const calls = new Map<string, number>()
    registerMandatory(registry, calls, (module, input) => {
      if (module.id !== 'rules-closure') return receipt(module, input)
      return {
        ...receipt(module, input, 'APPLIED'),
        moduleId: 'wrong-module',
      }
    })

    const result = await closure.closeTurn('TASK-1', 'TURN-1')
    const failed = result.moduleReceipts.find(item => item.moduleId === 'rules-closure')

    expect(result.status).toBe('PENDING')
    expect(failed?.status).toBe('FAILED')
    expect(failed?.reason).toContain('moduleId mismatch')
    expect(journal.getTurn('TASK-1', 'TURN-1')?.status).toBe('CLOSURE_PENDING')
  })

  it('requires Unified Reflection before the Coordinator can execute modules', async () => {
    const { journal, registry, closure } = createRuntime()
    journal.beginTurn({ taskId: 'TASK-2', turnId: 'TURN-1', agentId: 'AGENT-2' })
    journal.sealTurn('TASK-2', 'TURN-1')
    registerMandatory(registry, new Map())

    await expect(closure.closeTurn('TASK-2', 'TURN-1')).rejects.toThrow('requires Unified Reflection')
    expect(journal.getTurn('TASK-2', 'TURN-1')?.status).toBe('CLOSURE_PENDING')
  })

  it('executes optional modules for audit but does not let optional failure block a complete mandatory closure', async () => {
    const { journal, reflection, registry, closure } = createRuntime()
    await reflectReadyTurn(journal, reflection)
    registerMandatory(registry, new Map())
    let optionalCalls = 0
    const optional: ClosureModule = {
      id: 'optional-audit-hook',
      version: '0.1.0',
      mandatory: false,
      domains: ['evidence'],
      apply(input) {
        optionalCalls += 1
        return receipt(optional, input, 'FAILED', 'optional audit sink unavailable')
      },
    }
    registry.register(optional)

    const result = await closure.closeTurn('TASK-1', 'TURN-1')

    expect(result.status).toBe('COMPLETE')
    expect(optionalCalls).toBe(1)
    expect(result.moduleReceipts.find(item => item.moduleId === optional.id)?.status).toBe('FAILED')
    expect(journal.getTurn('TASK-1', 'TURN-1')?.status).toBe('CLOSED')
  })

  it('prevents project or optional code from extending or downgrading the fixed mandatory set', () => {
    const { registry } = createRuntime()
    const fake = (id: string, mandatory: boolean): ClosureModule => ({
      id,
      version: '0.1.0',
      mandatory,
      domains: ['context'],
      apply(input) { return receipt(this, input) },
    })

    expect(() => registry.register(fake('context-closure', false))).toThrow('cannot be registered as optional')
    expect(() => registry.register(fake('project-extra-mandatory', true))).toThrow('cannot extend the fixed Kernel mandatory set')
  })
})
