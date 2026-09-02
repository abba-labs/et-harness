import { describe, expect, it } from 'vitest'
import {
  assertTaskTransition,
  assertTurnTransition,
  closureReplayTurns,
  guardNewTurn,
} from '../src/lifecycle.js'
import type { TurnJournalRecord } from '../src/contracts.js'

const turn = (turnId: string, status: TurnJournalRecord['status']): TurnJournalRecord => ({
  contractVersion: '0.1',
  taskId: 'TASK-1',
  turnId,
  agentId: 'AGENT-1',
  projectBinding: { kind: 'UNBOUND' },
  startedAt: `2026-08-25T00:00:0${turnId.at(-1) ?? '0'}.000Z`,
  ...(status === 'ABORTED'
    ? { abortedAt: '2026-08-25T00:01:00.000Z', abortReason: 'Begin failed' }
    : {}),
  userMessageRefs: [],
  assistantMessageRefs: [],
  toolEventRefs: [],
  resourceTouchRefs: [],
  status,
  revision: 1,
  closureAttemptCount: 0,
})

describe('Kernel lifecycle contracts', () => {
  it('enforces Turn transition order and keeps abort terminal', () => {
    expect(() => assertTurnTransition('OPEN', 'SEALED')).not.toThrow()
    expect(() => assertTurnTransition('OPEN', 'ABORTED')).not.toThrow()
    expect(() => assertTurnTransition('SEALED', 'CLOSED')).not.toThrow()
    expect(() => assertTurnTransition('CLOSURE_PENDING', 'CLOSED')).not.toThrow()
    expect(() => assertTurnTransition('OPEN', 'CLOSED')).toThrow('Illegal Turn lifecycle transition')
    expect(() => assertTurnTransition('ABORTED', 'OPEN')).toThrow('Illegal Turn lifecycle transition')
    expect(() => assertTurnTransition('CLOSED', 'OPEN')).toThrow('Illegal Turn lifecycle transition')
  })

  it('allows Task resume but never reopens a terminal Task', () => {
    expect(() => assertTaskTransition('PAUSED', 'ACTIVE')).not.toThrow()
    expect(() => assertTaskTransition('ACTIVE', 'COMPLETED')).not.toThrow()
    expect(() => assertTaskTransition('ACTIVE', 'ABORTED')).not.toThrow()
    expect(() => assertTaskTransition('COMPLETED', 'ACTIVE')).toThrow('Illegal Task lifecycle transition')
    expect(() => assertTaskTransition('ABORTED', 'ACTIVE')).toThrow('Illegal Task lifecycle transition')
  })

  it('fail-closes a new Turn while any previous non-terminal Turn is unresolved', () => {
    const guard = guardNewTurn([
      turn('TURN-1', 'CLOSED'),
      turn('TURN-2', 'ABORTED'),
      turn('TURN-3', 'CLOSURE_PENDING'),
    ], 'TURN-4')
    expect(guard.allowed).toBe(false)
    expect(guard.blockingTurnIds).toEqual(['TURN-3'])

    const afterAbort = guardNewTurn([
      turn('TURN-1', 'CLOSED'),
      turn('TURN-2', 'ABORTED'),
    ], 'TURN-4')
    expect(afterAbort.allowed).toBe(true)
  })

  it('identifies closure replay candidates independently of project binding or project actions', () => {
    const replay = closureReplayTurns([
      turn('TURN-1', 'OPEN'),
      turn('TURN-2', 'SEALED'),
      turn('TURN-3', 'CLOSURE_PENDING'),
      turn('TURN-4', 'CLOSED'),
      turn('TURN-5', 'ABORTED'),
    ])
    expect(replay.map(item => item.turnId)).toEqual(['TURN-2', 'TURN-3'])
  })
})
