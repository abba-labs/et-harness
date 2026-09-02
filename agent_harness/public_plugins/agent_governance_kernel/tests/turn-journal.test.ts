import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'
import { TurnJournalStore } from '../src/turn-journal-store.js'

const roots: string[] = []
const createStore = (): TurnJournalStore => {
  const root = mkdtempSync(join(tmpdir(), 'agent-governance-kernel-'))
  roots.push(root)
  return new TurnJournalStore(root)
}

afterEach(() => {
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true })
})

describe('Turn Journal persistence', () => {
  it('supports UNBOUND -> BOUND and persists a complete reflected closure chain', () => {
    const store = createStore()
    const open = store.beginTurn({
      taskId: 'TASK-1',
      turnId: 'TURN-1',
      agentId: 'AGENT-1',
      userMessageRefs: ['msg://user/1'],
      stateVersionBefore: 7,
    })
    expect(open.projectBinding).toEqual({ kind: 'UNBOUND' })
    expect(open.status).toBe('OPEN')

    store.appendRefs('TASK-1', 'TURN-1', {
      assistantMessageRefs: ['msg://assistant/1'],
      toolEventRefs: ['tool://read/1'],
      resourceTouchRefs: ['knowledge://global/K001.001'],
      sessionRef: 'session://S1',
    })
    const bound = store.bindProject('TASK-1', 'TURN-1', 'et-tool')
    expect(bound.projectBinding).toEqual({ kind: 'BOUND', projectId: 'et-tool' })

    const sealed = store.sealTurn('TASK-1', 'TURN-1', '2026-08-25T00:00:00.000Z')
    expect(sealed.status).toBe('SEALED')
    const pending = store.markClosurePending('TASK-1', 'TURN-1', {
      attemptId: 'ATTEMPT-1',
      reason: 'reflection provider unavailable',
    })
    expect(pending.status).toBe('CLOSURE_PENDING')
    expect(pending.closureAttemptCount).toBe(1)
    expect(store.markClosurePending('TASK-1', 'TURN-1', {
      attemptId: 'ATTEMPT-1',
      reason: 'reflection provider unavailable',
    }).closureAttemptCount).toBe(1)

    store.attachReflection('TASK-1', 'TURN-1', {
      reflectionRef: 'governance-reflection://task/TASK-1/turn/TURN-1',
      inputFingerprint: 'sha256:test',
    })
    const closed = store.closeTurn('TASK-1', 'TURN-1', {
      closureReceiptRef: 'closure://TASK-1/TURN-1',
      closedAt: '2026-08-25T00:01:00.000Z',
    })
    expect(closed.status).toBe('CLOSED')
    expect(closed.closureReceiptRef).toBe('closure://TASK-1/TURN-1')
    expect(closed.reflectionRef).toContain('governance-reflection://')

    const reloaded = new TurnJournalStore(store.getStorageRoot()).getTurn('TASK-1', 'TURN-1')
    expect(reloaded?.status).toBe('CLOSED')
    expect(reloaded?.assistantMessageRefs).toEqual(['msg://assistant/1'])
    expect(reloaded?.reflectionInputFingerprint).toBe('sha256:test')
  })

  it('persists an append-only, idempotent ABORTED terminal record', () => {
    const store = createStore()
    store.beginTurn({
      taskId: 'TASK-ABORT',
      turnId: 'TURN-1',
      agentId: 'AGENT-ABORT',
      projectBinding: { kind: 'BOUND', projectId: 'et-tool' },
    })
    const aborted = store.abortTurn('TASK-ABORT', 'TURN-1', {
      reason: 'Gateway Context projection failed',
      abortedAt: '2026-08-25T00:02:00.000Z',
    })
    expect(aborted.status).toBe('ABORTED')
    expect(aborted.abortReason).toBe('Gateway Context projection failed')
    expect(store.listUnresolvedTurns('TASK-ABORT')).toEqual([])

    const replay = store.abortTurn('TASK-ABORT', 'TURN-1', {
      reason: 'Gateway Context projection failed',
    })
    expect(replay).toEqual(aborted)
    expect(() => store.abortTurn('TASK-ABORT', 'TURN-1', {
      reason: 'A different failure',
    })).toThrow('different reason')
    expect(() => store.appendRefs('TASK-ABORT', 'TURN-1', {
      toolEventRefs: ['tool://late'],
    })).toThrow('sealed')
    expect(() => store.sealTurn('TASK-ABORT', 'TURN-1')).toThrow('Illegal Turn lifecycle transition')

    const reloaded = new TurnJournalStore(store.getStorageRoot()).getTurn('TASK-ABORT', 'TURN-1')
    expect(reloaded).toEqual(aborted)
  })

  it('rejects project rebinding and mutations after seal', () => {
    const store = createStore()
    store.beginTurn({ taskId: 'TASK-2', turnId: 'TURN-1', agentId: 'AGENT-2' })
    store.bindProject('TASK-2', 'TURN-1', 'project-a')
    expect(() => store.bindProject('TASK-2', 'TURN-1', 'project-b')).toThrow('already bound')
    store.sealTurn('TASK-2', 'TURN-1')
    expect(() => store.appendRefs('TASK-2', 'TURN-1', { toolEventRefs: ['tool://late'] })).toThrow('sealed')
  })

  it('requires a sealed Turn, Unified Reflection and Closure Receipt before CLOSED', () => {
    const store = createStore()
    store.beginTurn({ taskId: 'TASK-3', turnId: 'TURN-1', agentId: 'AGENT-3' })
    expect(() => store.closeTurn('TASK-3', 'TURN-1', { closureReceiptRef: 'closure://x' })).toThrow('must be sealed')
    store.sealTurn('TASK-3', 'TURN-1')
    expect(() => store.closeTurn('TASK-3', 'TURN-1', { closureReceiptRef: 'closure://x' })).toThrow('requires Unified Reflection')
    store.attachReflection('TASK-3', 'TURN-1', {
      reflectionRef: 'governance-reflection://task/TASK-3/turn/TURN-1',
      inputFingerprint: 'sha256:test-3',
    })
    expect(() => store.closeTurn('TASK-3', 'TURN-1', { closureReceiptRef: '   ' })).toThrow('cannot be empty')
  })
})
