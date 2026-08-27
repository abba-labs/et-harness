import { describe, expect, it } from 'vitest'
import type { ClosureModuleInput, ReflectionCandidate, ScopedReflectionSection } from '@agent-harness/agent-governance-kernel'
import {
  createContextClosureModule,
  createExperienceMemoryClosureModule,
  createKnowledgeClosureModule,
} from '../src/modules.js'

const none = (): ScopedReflectionSection => ({ scopeDecision: 'NONE', rationale: 'No change', candidates: [] })

const baseInput = (): ClosureModuleInput => ({
  taskId: 'TASK-1',
  turnId: 'TURN-1',
  projectBinding: { kind: 'BOUND', projectId: 'et-tool' },
  journalRef: 'governance-journal://task/TASK-1/turn/TURN-1',
  idempotencyKey: 'closure:test',
  reflection: {
    contractVersion: '0.1',
    taskId: 'TASK-1',
    turnId: 'TURN-1',
    context: {
      progress: 'Completed the turn.',
      decisions: ['Keep semantic judgment in the Agent'],
      confirmed: ['Adapter path is deterministic'],
      assumptions: [],
      openIssues: [],
      next: ['Continue closure wiring'],
      touchedRefs: ['architecture://A050', 'rule://R300.600.020'],
    },
    knowledge: none(),
    experience: none(),
    architecture: none(),
    rules: none(),
    evidence: none(),
    workingSet: {
      keep: ['architecture://A050'],
      add: ['rule://R300.600.020'],
      remove: [],
    },
    obligations: { opened: [], resolved: [], unchanged: [] },
  },
})

const withSection = (
  input: ClosureModuleInput,
  key: 'knowledge' | 'experience',
  section: ScopedReflectionSection,
): ClosureModuleInput => ({
  ...input,
  reflection: { ...input.reflection, [key]: section },
})

const knowledgeCandidate = (scope: 'PROJECT' | 'PUBLIC' | 'BOTH', relatedRefs: string[]): ReflectionCandidate => ({
  domain: 'knowledge',
  title: `Knowledge ${scope}`,
  factOrProposal: `Fact ${scope}`,
  scopeDecision: scope,
  rationale: 'Explicit Agent classification',
  provenanceRefs: ['governance-reflection://TASK-1/TURN-1'],
  evidenceRefs: [],
  relatedRefs,
  confidence: 0.95,
})

describe('first mandatory Closure Manager adapters', () => {
  it('synchronizes BOUND Context and blocks UNBOUND Context instead of inventing a project', async () => {
    let version = 1
    let workingSet: unknown[] = []
    const manager = {
      getTask() { return { stateVersion: version, session: {} } },
      updateTaskLedger() { version += 1; return { stateVersion: version, session: {} } },
      updateProgressLedger() { version += 1; return { stateVersion: version, session: {} } },
      replaceWorkingSet(_projectId: string, _taskId: string, refs: unknown[]) {
        workingSet = refs
        version += 1
        return { stateVersion: version, session: {} }
      },
    }
    const module = createContextClosureModule(manager as never)
    const result = await module.apply(baseInput())
    expect(result.status).toBe('APPLIED')
    expect(result.stateVersionAfter).toBe(4)
    expect(workingSet).toEqual([
      { kind: 'architecture', id: 'A050' },
      { kind: 'rule', id: 'R300.600.020' },
    ])

    const unbound: ClosureModuleInput = { ...baseInput(), projectBinding: { kind: 'UNBOUND' } }
    const blocked = await module.apply(unbound)
    expect(blocked.status).toBe('BLOCKED')
    expect(blocked.reason).toContain('UNBOUND')
  })

  it('requires explicit project/public Knowledge category classification before any write', async () => {
    const writes: string[] = []
    const projectNodes = new Map<string, any>()
    const globalNodes = new Map<string, any>()
    const projectIndex = () => ({
      files: [{ nodes: [...projectNodes.keys()] }],
      taxonomy: { categories: { C010: { status: 'ACTIVE' } } },
    })
    const globalIndex = () => ({
      files: [{ nodes: [...globalNodes.keys()] }],
      taxonomy: { categories: { C020: { status: 'ACTIVE' } } },
    })
    let projectSeq = 1
    let globalSeq = 1
    const manager = {
      isGlobalLibraryMounted: () => true,
      getIndex: () => projectIndex(),
      getNode: (_projectId: string, id: string) => projectNodes.get(id) ? { node: projectNodes.get(id) } : undefined,
      getGlobalIndex: () => globalIndex(),
      getGlobalNode: (id: string) => globalNodes.get(id) ? { node: globalNodes.get(id) } : undefined,
      submitKnowledgeCandidate: (_projectId: string, input: any) => {
        const id = `K001.${String(projectSeq++).padStart(3, '0')}`
        projectNodes.set(id, { id, isLeaf: true, status: 'CANDIDATE', fact: input.fact })
        writes.push(`project:${id}`)
        return { knowledgeId: id, file: '001_library.md', status: 'CANDIDATE', categoryId: input.categoryId }
      },
      submitGlobalKnowledgeCandidate: (input: any) => {
        const id = `K001.${String(globalSeq++).padStart(3, '0')}`
        globalNodes.set(id, { id, isLeaf: true, status: 'CANDIDATE', fact: input.fact })
        writes.push(`global:${id}`)
        return { knowledgeId: id, file: '001_library.md', status: 'CANDIDATE', categoryId: input.categoryId }
      },
    }
    const module = createKnowledgeClosureModule(manager as never)

    const missingCategory = withSection(baseInput(), 'knowledge', {
      scopeDecision: 'PROJECT',
      rationale: 'Project knowledge exists',
      candidates: [knowledgeCandidate('PROJECT', [])],
    })
    const blocked = await module.apply(missingCategory)
    expect(blocked.status).toBe('BLOCKED')
    expect(writes).toHaveLength(0)

    const both = withSection(baseInput(), 'knowledge', {
      scopeDecision: 'BOTH',
      rationale: 'Both scopes are useful',
      candidates: [knowledgeCandidate('BOTH', [
        'knowledge-category://project/C010',
        'knowledge-category://public/C020',
      ])],
    })
    const first = await module.apply(both)
    expect(first.status).toBe('APPLIED')
    expect(first.candidateRefs).toHaveLength(2)
    expect(writes).toHaveLength(2)

    const replay = await module.apply(both)
    expect(replay.status).toBe('NO_CHANGE')
    expect(replay.candidateRefs).toHaveLength(2)
    expect(writes).toHaveLength(2)
  })

  it('records evidence-backed PROJECT Experience and blocks PUBLIC Experience until a global store exists', async () => {
    const stored: any[] = []
    const manager = {
      listCandidates: () => stored,
      recordCandidate(input: any) {
        const candidate = { ...input, candidateId: `EXP-${stored.length + 1}`, status: 'CANDIDATE', createdAt: 'now' }
        stored.push(candidate)
        return candidate
      },
    }
    const module = createExperienceMemoryClosureModule(manager as never)
    const projectCandidate: ReflectionCandidate = {
      domain: 'experience',
      title: 'Evidence-backed lesson',
      factOrProposal: 'Use the validated release path.',
      scopeDecision: 'PROJECT',
      rationale: 'Project workflow lesson',
      provenanceRefs: [],
      evidenceRefs: ['evidence://project/et-tool/EV-001'],
      relatedRefs: [],
      confidence: 0.9,
    }
    const project = withSection(baseInput(), 'experience', {
      scopeDecision: 'PROJECT',
      rationale: 'Project-specific lesson',
      candidates: [projectCandidate],
    })
    const first = await module.apply(project)
    expect(first.status).toBe('APPLIED')
    expect(stored).toHaveLength(1)

    const replay = await module.apply(project)
    expect(replay.status).toBe('NO_CHANGE')
    expect(stored).toHaveLength(1)

    const publicInput = withSection(baseInput(), 'experience', {
      scopeDecision: 'PUBLIC',
      rationale: 'Cross-project lesson',
      candidates: [{ ...projectCandidate, scopeDecision: 'PUBLIC' }],
    })
    const blocked = await module.apply(publicInput)
    expect(blocked.status).toBe('BLOCKED')
    expect(blocked.reason).toContain('global Experience store')
  })
})
