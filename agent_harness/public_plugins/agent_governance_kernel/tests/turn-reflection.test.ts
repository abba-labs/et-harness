import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'
import type { ReflectionDomain, TurnReflectionProviderInput } from '../src/contracts.js'
import { TurnJournalStore } from '../src/turn-journal-store.js'
import { TurnReflectionController } from '../src/turn-reflection-controller.js'
import { TurnReflectionStore } from '../src/turn-reflection-store.js'

const roots: string[] = []
const createRuntime = () => {
  const root = mkdtempSync(join(tmpdir(), 'agent-governance-kernel-reflection-'))
  roots.push(root)
  const journal = new TurnJournalStore(root)
  return {
    root,
    journal,
    controller: new TurnReflectionController(journal, new TurnReflectionStore(root)),
  }
}

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
    progress: 'Read and analyzed the requested material.',
    decisions: [],
    confirmed: ['Turn analysis completed'],
    assumptions: [],
    openIssues: [],
    next: ['Continue from the persisted Turn state'],
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

afterEach(() => {
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true })
})

describe('Unified Turn Reflection', () => {
  it('seals the Turn, reflects exactly once, persists the result and attaches reflectionRef', async () => {
    const { root, journal, controller } = createRuntime()
    journal.beginTurn({ taskId: 'TASK-1', turnId: 'TURN-1', agentId: 'AGENT-1' })
    journal.appendRefs('TASK-1', 'TURN-1', { resourceTouchRefs: ['architecture://A010'] })

    let calls = 0
    controller.registerProvider({
      providerId: 'agent-reflector',
      priority: 100,
      reflect(input) {
        calls += 1
        return noChangeResult(input)
      },
    })

    const first = await controller.reflectTurn('TASK-1', 'TURN-1', {
      publicCandidateRefs: ['knowledge://global/K001'],
    })
    const second = await controller.reflectTurn('TASK-1', 'TURN-1', {
      publicCandidateRefs: ['knowledge://global/K001'],
    })

    expect(calls).toBe(1)
    expect(second.inputFingerprint).toBe(first.inputFingerprint)
    expect(journal.getTurn('TASK-1', 'TURN-1')?.status).toBe('SEALED')
    expect(journal.getTurn('TASK-1', 'TURN-1')?.reflectionRef).toContain('governance-reflection://')

    const reloaded = new TurnReflectionStore(root).get(
      'TASK-1',
      'TURN-1',
      journal.getTurn('TASK-1', 'TURN-1')!,
    )
    expect(reloaded?.result.context.progress).toContain('analyzed')
  })

  it('requires explicit coverage of every reflection domain even when the result is NO_CHANGE', async () => {
    const { journal, controller } = createRuntime()
    journal.beginTurn({ taskId: 'TASK-2', turnId: 'TURN-1', agentId: 'AGENT-2' })
    controller.registerProvider({
      providerId: 'incomplete-reflector',
      reflect(input) {
        const result = noChangeResult(input) as Record<string, unknown>
        delete result.rules
        return result
      },
    })

    await expect(controller.reflectTurn('TASK-2', 'TURN-1')).rejects.toThrow('rules reflection section is required')
    expect(journal.getTurn('TASK-2', 'TURN-1')?.status).toBe('CLOSURE_PENDING')
  })

  it('rejects PROJECT/BOTH semantic candidates while a Turn is UNBOUND', async () => {
    const { journal, controller } = createRuntime()
    journal.beginTurn({ taskId: 'TASK-3', turnId: 'TURN-1', agentId: 'AGENT-3' })
    controller.registerProvider({
      providerId: 'bad-scope-reflector',
      reflect(input) {
        return {
          ...noChangeResult(input),
          knowledge: {
            scopeDecision: 'PROJECT',
            rationale: 'Incorrectly claims project-bound knowledge while no project is bound',
            candidates: [{
              domain: 'knowledge',
              title: 'Project-only fact',
              factOrProposal: 'This must not be accepted for an UNBOUND Turn.',
              scopeDecision: 'PROJECT',
              rationale: 'Invalid scope for this lifecycle state',
              provenanceRefs: [],
              evidenceRefs: [],
              relatedRefs: [],
              confidence: 0.9,
            }],
          },
        }
      },
    })

    await expect(controller.reflectTurn('TASK-3', 'TURN-1')).rejects.toThrow('cannot emit PROJECT/BOTH')
    expect(journal.getTurn('TASK-3', 'TURN-1')?.status).toBe('CLOSURE_PENDING')
    expect(journal.getTurn('TASK-3', 'TURN-1')?.reflectionRef).toBeUndefined()
  })

  it('fails closed when no Agent Reflection Provider exists', async () => {
    const { journal, controller } = createRuntime()
    journal.beginTurn({ taskId: 'TASK-4', turnId: 'TURN-1', agentId: 'AGENT-4' })

    await expect(controller.reflectTurn('TASK-4', 'TURN-1')).rejects.toThrow('provider unavailable')
    const turn = journal.getTurn('TASK-4', 'TURN-1')
    expect(turn?.status).toBe('CLOSURE_PENDING')
    expect(turn?.lastClosureError).toContain('provider unavailable')
  })

  it('uses the highest-priority provider and accepts PUBLIC reflection while UNBOUND', async () => {
    const { journal, controller } = createRuntime()
    journal.beginTurn({ taskId: 'TASK-5', turnId: 'TURN-1', agentId: 'AGENT-5' })
    controller.registerProvider({ providerId: 'low', priority: 1, reflect: noChangeResult })
    controller.registerProvider({
      providerId: 'high',
      priority: 10,
      reflect(input) {
        return {
          ...noChangeResult(input),
          experience: {
            scopeDecision: 'PUBLIC',
            rationale: 'A cross-project governance lesson was learned.',
            candidates: [{
              domain: 'experience',
              title: 'Turn closure must be project-independent',
              factOrProposal: 'Public lifecycle governance must run even without a bound project.',
              scopeDecision: 'PUBLIC',
              rationale: 'The lesson applies to every project and harness adapter.',
              provenanceRefs: ['governance-journal://task/TASK-5/turn/TURN-1'],
              evidenceRefs: [],
              relatedRefs: [],
              confidence: 0.95,
            }],
          },
        }
      },
    })

    const reflected = await controller.reflectTurn('TASK-5', 'TURN-1')
    expect(reflected.providerId).toBe('high')
    expect(reflected.result.experience.scopeDecision).toBe('PUBLIC')
  })
})
