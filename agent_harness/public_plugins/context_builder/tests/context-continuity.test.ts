import { describe, expect, it } from 'vitest'
import {
  selectRelevantContextHistory,
} from '../src/context-management-service.js'
import type {
  ContextReference,
  ContextSession,
} from '../src/contracts.js'

const session = (
  taskId: string,
  status: ContextSession['status'],
  refs: readonly string[],
  openIssue: string,
  closedTurn = false,
): ContextSession => ({
  projectId: 'p1',
  taskId,
  status,
  generation: 2,
  maxChars: 18_000,
  recentTailLimit: 5,
  createdAt: '2026-09-01T00:00:00.000Z',
  updatedAt: '2026-09-02T00:00:00.000Z',
  taskLedger: {
    goal: `Goal for ${taskId}`,
    phase: status === 'COMPLETED' ? 'complete' : 'handoff',
    scopeRefs: [...refs],
    constraintRefs: [],
    confirmed: [{ text: `Confirmed ${taskId}`, refs: [...refs] }],
    assumptions: [],
    openIssues: [{ text: openIssue, refs: [...refs] }],
    plan: [`Continue ${taskId}`],
    updatedAt: '2026-09-02T00:00:00.000Z',
  },
  progressLedger: {
    ...(closedTurn ? { lastAction: 'Close governed Turn TURN-1' } : {}),
    touchedRefs: [...refs],
    currentProblem: openIssue,
    blockers: [],
    next: [`Next ${taskId}`],
    evidenceRefs: [],
    updatedAt: '2026-09-02T00:00:00.000Z',
  },
  workingSet: refs.map(id => ({ kind: 'architecture' as const, id })),
  inlineItems: [],
  handles: [],
  recentTail: [],
})

const record = (value: ContextSession, version = 3) => ({
  scope: `context:${value.taskId}`,
  key: 'session',
  value,
  version,
  updatedAt: value.updatedAt,
})

describe('cross-task Context continuity', () => {
  it('inherits only relevant completed/paused or legacy closed-turn task facts and open issues', () => {
    const references: ContextReference[] = [{ kind: 'architecture', id: 'A010.020', priority: 'high' }]
    const items = selectRelevantContextHistory({
      projectId: 'p1',
      currentTaskId: 'TASK-NOW',
      references,
      records: [
        record(session('TASK-RELATED', 'COMPLETED', ['architecture://project/p1/A010.020'], 'Carry this issue forward')),
        record(session('TASK-CLOSED-TURN', 'ACTIVE', ['A010.020'], 'Turn-closed issue must be inherited', true)),
        record(session('TASK-UNRELATED', 'COMPLETED', ['A099'], 'Do not inherit this issue')),
        record(session('TASK-ACTIVE', 'ACTIVE', ['A010.020'], 'Do not inherit live active task state')),
        record(session('TASK-ABORTED', 'ABORTED', ['A010.020'], 'Do not inherit aborted task state')),
      ],
    })

    expect(items).toHaveLength(2)
    expect(items.map(item => item.id)).toContain('prior-context-TASK-RELATED')
    expect(items.map(item => item.id)).toContain('prior-context-TASK-CLOSED-TURN')
    expect(items.map(item => item.id)).not.toContain('prior-context-TASK-ACTIVE')
    expect(items.map(item => item.id)).not.toContain('prior-context-TASK-ABORTED')
    expect(items.some(item => item.content.includes('Carry this issue forward'))).toBe(true)
    expect(items.some(item => item.content.includes('Turn-closed issue must be inherited'))).toBe(true)
    expect(items.every(item => !item.content.includes('Do not inherit live active task state'))).toBe(true)
    expect(items.every(item => !item.content.includes('Do not inherit aborted task state'))).toBe(true)
  })

  it('keeps bounded source-backed facts after a task-level route match', () => {
    const prior = session('TASK-SOURCE-FACTS', 'COMPLETED', ['A010.020'], 'Driver result needs follow-up')
    prior.taskLedger.confirmed = [{
      text: 'Source-backed hardware fact',
      refs: ['source://firmware/svd/ET6801.svd'],
    }]
    prior.taskLedger.openIssues = [{
      text: 'Source-backed driver gap',
      refs: ['source://firmware/driver/srpwm.c'],
    }]

    const items = selectRelevantContextHistory({
      projectId: 'p1',
      currentTaskId: 'TASK-NOW',
      references: [{ kind: 'architecture', id: 'A010.020' }],
      records: [record(prior)],
    })

    expect(items).toHaveLength(1)
    expect(items[0]?.content).toContain('Source-backed hardware fact')
    expect(items[0]?.content).toContain('Source-backed driver gap')
  })

  it('does not inherit when the current route has no shared refs', () => {
    const items = selectRelevantContextHistory({
      projectId: 'p1',
      currentTaskId: 'TASK-NOW',
      references: [{ kind: 'knowledge', id: 'K010' }],
      records: [record(session('TASK-OLD', 'COMPLETED', ['A010'], 'Unrelated'))],
    })
    expect(items).toEqual([])
  })

  it('respects the existing inline-context budget instead of making bootstrap fail', () => {
    const items = selectRelevantContextHistory({
      projectId: 'p1',
      currentTaskId: 'TASK-NOW',
      references: [{ kind: 'architecture', id: 'A010' }],
      records: [record(session('TASK-OLD', 'COMPLETED', ['A010'], 'Relevant'))],
      existingInlineItems: [{
        id: 'project-contribution',
        title: 'Existing contribution',
        content: 'X'.repeat(16_000),
        priority: 'high',
        provenance: 'project://p1/contribution',
      }],
    })
    expect(items).toEqual([])
  })
})
