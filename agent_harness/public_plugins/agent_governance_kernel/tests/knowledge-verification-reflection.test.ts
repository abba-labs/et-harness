import { describe, expect, it } from 'vitest'
import type { TurnJournalRecord } from '../src/contracts.js'
import { validateTurnReflectionResult } from '../src/reflection.js'

const journal: TurnJournalRecord = {
  contractVersion: '0.1',
  taskId: 'TASK-1',
  turnId: 'TURN-1',
  agentId: 'agent-1',
  projectBinding: { kind: 'BOUND', projectId: 'et-tool' },
  startedAt: '2026-08-26T00:00:00.000Z',
  userMessageRefs: [],
  assistantMessageRefs: [],
  toolEventRefs: [],
  resourceTouchRefs: [],
  status: 'OPEN',
  revision: 1,
  closureAttemptCount: 0,
}

const empty = (rationale: string) => ({ scopeDecision: 'NONE', rationale, candidates: [] })
const base = {
  contractVersion: '0.1',
  taskId: 'TASK-1',
  turnId: 'TURN-1',
  context: {
    progress: 'tested candidate knowledge',
    decisions: [], confirmed: [], assumptions: [], openIssues: [], next: [], touchedRefs: [],
  },
  knowledge: empty('No new Knowledge candidate.'),
  experience: empty('None.'),
  architecture: empty('None.'),
  rules: empty('None.'),
  evidence: empty('None.'),
  workingSet: { keep: [], add: [], remove: [] },
  obligations: { opened: [], resolved: [], unchanged: [] },
}

describe('Knowledge verification reflection', () => {
  it('accepts evidence-backed SUPPORT/CONTRADICT proposals', () => {
    const result = validateTurnReflectionResult({
      ...base,
      knowledgeVerifications: [{
        knowledgeRef: 'knowledge://project/et-tool/K001.001',
        relation: 'SUPPORT',
        basisRefs: ['evidence://project/et-tool/EV-1'],
        rationale: 'A real test exercised the candidate claim.',
      }],
    }, journal)
    expect(result.knowledgeVerifications).toHaveLength(1)
    expect(result.knowledgeVerifications?.[0]?.relation).toBe('SUPPORT')
  })

  it('rejects prose-only or unsupported basis references', () => {
    expect(() => validateTurnReflectionResult({
      ...base,
      knowledgeVerifications: [{
        knowledgeRef: 'K001.001',
        relation: 'SUPPORT',
        basisRefs: ['model-says://pass'],
        rationale: 'Unsupported basis.',
      }],
    }, journal)).toThrow('source:// or evidence://')
  })
})
