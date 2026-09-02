import { describe, expect, it } from 'vitest'
import { ContextManagementService } from '../src/context-management-service.js'

type StateRecord = {
  projectId: string
  scope: string
  key: string
  value: unknown
  version: number
  updatedAt: string
  evidenceRefs: readonly string[]
}

const createManager = () => {
  const records = new Map<string, StateRecord>()
  let updateCount = 0
  const keyOf = (projectId: string, scope: string, key: string) => `${projectId}\0${scope}\0${key}`
  const evidenceStateManager = {
    readState(projectId: string, scope: string, key: string) {
      return records.get(keyOf(projectId, scope, key))
    },
    updateState(input: any) {
      const key = keyOf(input.projectId, input.scope, input.key)
      const current = records.get(key)
      expect(input.expectedVersion).toBe(current?.version ?? 0)
      updateCount += 1
      const next: StateRecord = {
        projectId: input.projectId,
        scope: input.scope,
        key: input.key,
        value: structuredClone(input.value),
        version: (current?.version ?? 0) + 1,
        updatedAt: new Date().toISOString(),
        evidenceRefs: [...(input.evidenceRefs ?? [])],
      }
      records.set(key, next)
      return next
    },
    snapshot(projectId: string) {
      return {
        records: [...records.values()]
          .filter(record => record.projectId === projectId)
          .map(record => ({
            scope: record.scope,
            key: record.key,
            value: structuredClone(record.value),
            version: record.version,
            updatedAt: record.updatedAt,
          })),
      }
    },
  }
  const manager = Object.create(ContextManagementService.prototype) as ContextManagementService
  Object.defineProperty(manager, 'runtimeContext', {
    value: {
      projectManager: {
        getProjectContext: (projectId: string) => projectId === 'p1'
          ? { projectId, displayName: 'Project One', adapters: {} }
          : undefined,
      },
      evidenceStateManager,
    },
  })
  return { manager, updates: () => updateCount }
}

const closure = {
  turnId: 'TURN-1',
  confirmed: [{ text: 'Confirmed source fact', refs: ['source://spec/a'] }],
  assumptions: [],
  openIssues: [{ text: 'Follow-up remains', refs: ['source://driver/a'] }],
  plan: ['Continue validation'],
  progress: 'Turn work completed.',
  touchedRefs: ['A010'],
  evidenceRefs: ['evidence://project/p1/EV-1'],
  workingSet: [{ kind: 'architecture' as const, id: 'A010' }],
}

describe('Context lifecycle repair', () => {
  it('commits Turn closure once and replays without another version', () => {
    const { manager, updates } = createManager()
    manager.beginTask({ projectId: 'p1', taskId: 'TASK-1', goal: 'Analyze a bounded task' })

    const applied = manager.applyTurnClosure('p1', 'TASK-1', closure)
    expect(applied.stateVersion).toBe(2)
    expect(applied.session.taskLedger.confirmed).toEqual(closure.confirmed)
    expect(applied.session.progressLedger.lastAction).toBe('Close governed Turn TURN-1')
    expect(applied.session.workingSet).toEqual(closure.workingSet)

    const replay = manager.applyTurnClosure('p1', 'TASK-1', closure)
    expect(replay.stateVersion).toBe(2)
    expect(updates()).toBe(2)
  })

  it('validates the complete closure state before its single CAS', () => {
    const { manager, updates } = createManager()
    manager.beginTask({ projectId: 'p1', taskId: 'TASK-INVALID', goal: 'Analyze a bounded task' })
    expect(() => manager.applyTurnClosure('p1', 'TASK-INVALID', {
      ...closure,
      confirmed: [{ text: 'Untraceable confirmed fact', refs: [] }],
    })).toThrow('CONFIRMED_WITHOUT_REF')
    expect(manager.getTask('p1', 'TASK-INVALID').stateVersion).toBe(1)
    expect(updates()).toBe(1)
  })

  it('completes or aborts idempotently through the existing Context owner', () => {
    const completedState = createManager()
    completedState.manager.beginTask({ projectId: 'p1', taskId: 'TASK-COMPLETE', goal: 'Complete me' })
    const completed = completedState.manager.complete('p1', 'TASK-COMPLETE')
    expect(completed.session.status).toBe('COMPLETED')
    expect(completed.session.taskLedger.phase).toBe('complete')
    expect(completedState.manager.complete('p1', 'TASK-COMPLETE').stateVersion).toBe(2)
    expect(completedState.updates()).toBe(2)

    const abortedState = createManager()
    abortedState.manager.beginTask({ projectId: 'p1', taskId: 'TASK-ABORT', goal: 'Abort me' })
    const aborted = abortedState.manager.abort('p1', 'TASK-ABORT', 'Begin projection failed')
    expect(aborted.session.status).toBe('ABORTED')
    expect(abortedState.manager.abort('p1', 'TASK-ABORT', 'Begin projection failed').stateVersion).toBe(2)
    expect(abortedState.updates()).toBe(2)
    expect(() => abortedState.manager.resume('p1', 'TASK-ABORT')).toThrow('terminal Context task')
    expect(() => abortedState.manager.complete('p1', 'TASK-ABORT')).toThrow('Cannot complete aborted')
  })
})
