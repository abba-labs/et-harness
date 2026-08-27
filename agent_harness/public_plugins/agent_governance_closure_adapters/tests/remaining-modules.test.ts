import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'
import type {
  ClosureModuleInput,
  ReflectionCandidate,
} from '@agent-harness/agent-governance-kernel'
import { GovernanceChangeCandidateStore } from '../src/change-candidate-store.js'
import {
  createArchitectureClosureModule,
  createContextLedgerClosureModule,
  createEvidenceStateClosureModule,
  createObligationGateReconcileModule,
  createRulesClosureModule,
  createWorkingSetClosureModule,
} from '../src/remaining-modules.js'

const roots: string[] = []
const tempRoot = (): string => {
  const root = mkdtempSync(join(tmpdir(), 'closure-step5-'))
  roots.push(root)
  return root
}

afterEach(() => {
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true })
})

const none = () => ({ scopeDecision: 'NONE' as const, rationale: 'No change', candidates: [] })

const baseInput = (): ClosureModuleInput => ({
  taskId: 'TASK-1',
  turnId: 'TURN-1',
  projectBinding: { kind: 'BOUND', projectId: 'et-tool' },
  journalRef: 'governance-journal://task/TASK-1/turn/TURN-1',
  idempotencyKey: 'closure:step5:test',
  reflection: {
    contractVersion: '0.1',
    taskId: 'TASK-1',
    turnId: 'TURN-1',
    context: {
      progress: 'Completed deterministic closure work.',
      decisions: ['Keep formal Architecture and Rules immutable during Turn Closure'],
      confirmed: ['All semantic classifications came from the Agent Reflection'],
      assumptions: [],
      openIssues: [],
      next: ['Run a pure-analysis pilot'],
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

const semanticCandidate = (
  domain: 'architecture' | 'rules' | 'evidence',
  scopeDecision: 'PROJECT' | 'PUBLIC' | 'BOTH',
  fact: string,
): ReflectionCandidate => ({
  domain,
  title: `${domain} candidate`,
  factOrProposal: fact,
  scopeDecision,
  rationale: 'Agent classified this semantic result explicitly.',
  provenanceRefs: ['session://turn/1'],
  evidenceRefs: [],
  relatedRefs: [],
  confidence: 0.95,
})

describe('Step 5 remaining Mandatory Closure Modules', () => {
  it('stores Architecture and Rule changes as PROJECT/PUBLIC candidates without touching formal resources', async () => {
    const store = new GovernanceChangeCandidateStore(tempRoot())
    const architecture = createArchitectureClosureModule(store)
    const rules = createRulesClosureModule(store)
    const input = baseInput()
    input.reflection.architecture = {
      scopeDecision: 'BOTH',
      rationale: 'Project fact has a reusable public lesson.',
      candidates: [semanticCandidate('architecture', 'BOTH', 'Introduce a stable closure boundary.')],
    }
    input.reflection.rules = {
      scopeDecision: 'PROJECT',
      rationale: 'Project-specific rule candidate.',
      candidates: [semanticCandidate('rules', 'PROJECT', 'A local route change must remain isolated.')],
    }

    const archFirst = await architecture.apply(input)
    const ruleFirst = await rules.apply(input)
    expect(archFirst.status).toBe('APPLIED')
    expect(archFirst.candidateRefs).toEqual(expect.arrayContaining([
      expect.stringMatching(/^architecture-change:\/\/project\/et-tool\/ARCHC-/),
      expect.stringMatching(/^architecture-change:\/\/public\/ARCHC-/),
    ]))
    expect(ruleFirst.status).toBe('APPLIED')
    expect(ruleFirst.candidateRefs[0]).toMatch(/^rule-change:\/\/project\/et-tool\/RULEC-/)

    const archReplay = await architecture.apply(input)
    const ruleReplay = await rules.apply(input)
    expect(archReplay.status).toBe('NO_CHANGE')
    expect(ruleReplay.status).toBe('NO_CHANGE')
    expect(archReplay.candidateRefs).toEqual(archFirst.candidateRefs)
    expect(ruleReplay.candidateRefs).toEqual(ruleFirst.candidateRefs)
  })

  it('keeps Context Ledger and Working Set as separate idempotent responsibilities', async () => {
    let version = 1
    const session: any = {
      taskLedger: { confirmed: [], assumptions: [], openIssues: [], plan: [] },
      progressLedger: { touchedRefs: [], next: [], evidenceRefs: [] },
      workingSet: [],
    }
    const context = {
      getTask() { return { stateVersion: version, session } },
      updateTaskLedger(_projectId: string, _taskId: string, patch: any) {
        session.taskLedger = { ...session.taskLedger, ...patch }
        version += 1
        return { stateVersion: version, session }
      },
      updateProgressLedger(_projectId: string, _taskId: string, patch: any) {
        session.progressLedger = { ...session.progressLedger, ...patch }
        version += 1
        return { stateVersion: version, session }
      },
      replaceWorkingSet(_projectId: string, _taskId: string, refs: any[]) {
        session.workingSet = refs
        version += 1
        return { stateVersion: version, session }
      },
    }
    const contextModule = createContextLedgerClosureModule(context as never)
    const workingSetModule = createWorkingSetClosureModule(context as never)
    const input = baseInput()

    const contextFirst = await contextModule.apply(input)
    expect(contextFirst.status).toBe('APPLIED')
    expect(session.workingSet).toEqual([])
    const workingFirst = await workingSetModule.apply(input)
    expect(workingFirst.status).toBe('APPLIED')
    expect(session.workingSet).toEqual([
      { kind: 'architecture', id: 'A050' },
      { kind: 'rule', id: 'R300.600.020' },
    ])

    const contextReplay = await contextModule.apply(input)
    const workingReplay = await workingSetModule.apply(input)
    expect(contextReplay.status).toBe('NO_CHANGE')
    expect(workingReplay.status).toBe('NO_CHANGE')
  })

  it('records Reflection Evidence as INFO with replay fingerprint and never auto-PASSes it', async () => {
    const records: any[] = []
    const manager = {
      listEvidence: () => records,
      recordEvidence(input: any) {
        const record = { ...input, evidenceId: `EV-${records.length + 1}`, recordedAt: 'now' }
        records.push(record)
        return record
      },
    }
    const module = createEvidenceStateClosureModule(manager as never)
    const input = baseInput()
    input.reflection.evidence = {
      scopeDecision: 'PROJECT',
      rationale: 'A project runtime fact was observed.',
      candidates: [semanticCandidate('evidence', 'PROJECT', 'The Adapter registered all required closure modules.')],
    }

    const first = await module.apply(input)
    expect(first.status).toBe('APPLIED')
    expect(records).toHaveLength(1)
    expect(records[0].result).toBe('INFO')
    expect(records[0].result).not.toBe('PASS')

    const replay = await module.apply(input)
    expect(replay.status).toBe('NO_CHANGE')
    expect(records).toHaveLength(1)

    const publicInput = baseInput()
    publicInput.reflection.evidence = {
      scopeDecision: 'PUBLIC',
      rationale: 'Public Evidence is requested.',
      candidates: [semanticCandidate('evidence', 'PUBLIC', 'A cross-project fact.')],
    }
    const blocked = await module.apply(publicInput)
    expect(blocked.status).toBe('BLOCKED')
  })

  it('blocks a false MUST Gate resolution and persists real obligation reconciliation', async () => {
    let state: any
    let version = 0
    let gatePass = false
    const stateManager = {
      readState: () => state,
      updateState(input: any) {
        version += 1
        state = {
          projectId: input.projectId,
          scope: input.scope,
          key: input.key,
          value: input.value,
          version,
          reason: input.reason,
          evidenceRefs: input.evidenceRefs ?? [],
          updatedAt: 'now',
        }
        return state
      },
    }
    const gateManager = {
      getExecutionPlan(_projectId: string, gateId: string) {
        return gateId === 'G010.010.010' ? { gateId, level: 'MUST' } : undefined
      },
      checkGateEvidence(_projectId: string, _taskId: string, gateId: string) {
        return {
          projectId: 'et-tool',
          taskId: 'TASK-1',
          gateId,
          level: 'MUST',
          satisfied: gatePass,
          blocksCompletion: !gatePass,
          evidenceRefs: gatePass ? ['EV-GATE-PASS'] : [],
        }
      },
    }
    const module = createObligationGateReconcileModule(stateManager as never, gateManager as never)

    const falseResolution = baseInput()
    falseResolution.reflection.obligations = {
      opened: [],
      resolved: ['Resolve gate G010.010.010'],
      unchanged: [],
    }
    const blocked = await module.apply(falseResolution)
    expect(blocked.status).toBe('BLOCKED')
    expect(blocked.reason).toContain('without PASS Evidence')
    expect(state).toBeUndefined()

    gatePass = true
    const resolved = await module.apply(falseResolution)
    expect(resolved.status).toBe('APPLIED')
    expect(resolved.evidenceRefs).toContain('evidence://project/et-tool/EV-GATE-PASS')
    expect(state.value.openObligations).toEqual([])

    const replay = await module.apply(falseResolution)
    expect(replay.status).toBe('NO_CHANGE')
    expect(version).toBe(1)
  })
})
