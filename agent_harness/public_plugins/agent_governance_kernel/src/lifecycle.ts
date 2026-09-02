import type {
  ProjectBinding,
  TaskLifecycleStatus,
  TurnJournalRecord,
  TurnJournalStatus,
  TurnStartGuardResult,
} from './contracts.js'

const IDENTIFIER_RE = /^[A-Za-z0-9._:@-]{1,200}$/

export function assertKernelIdentifier(label: string, value: string): void {
  if (!IDENTIFIER_RE.test(value)) {
    throw new Error(`${label} must be 1-200 characters using A-Z, a-z, 0-9, ., _, :, @ or -`)
  }
}

export function assertProjectBinding(binding: ProjectBinding): void {
  if (binding.kind === 'UNBOUND') return
  if (binding.kind !== 'BOUND') throw new Error(`Unsupported project binding kind: ${String((binding as { kind?: unknown }).kind)}`)
  assertKernelIdentifier('projectId', binding.projectId)
}

export function projectBindingEquals(left: ProjectBinding, right: ProjectBinding): boolean {
  if (left.kind !== right.kind) return false
  return left.kind === 'UNBOUND' || left.projectId === (right as { readonly projectId: string }).projectId
}

const TURN_TRANSITIONS: Readonly<Record<TurnJournalStatus, ReadonlySet<TurnJournalStatus>>> = {
  OPEN: new Set(['SEALED', 'ABORTED']),
  SEALED: new Set(['CLOSURE_PENDING', 'CLOSED']),
  CLOSURE_PENDING: new Set(['CLOSURE_PENDING', 'CLOSED']),
  CLOSED: new Set(['CLOSED']),
  ABORTED: new Set(['ABORTED']),
}

export function assertTurnTransition(from: TurnJournalStatus, to: TurnJournalStatus): void {
  if (!TURN_TRANSITIONS[from].has(to)) {
    throw new Error(`Illegal Turn lifecycle transition: ${from} -> ${to}`)
  }
}

const TASK_TRANSITIONS: Readonly<Record<TaskLifecycleStatus, ReadonlySet<TaskLifecycleStatus>>> = {
  ACTIVE: new Set(['ACTIVE', 'PAUSED', 'COMPLETED']),
  PAUSED: new Set(['PAUSED', 'ACTIVE', 'COMPLETED']),
  COMPLETED: new Set(['COMPLETED']),
}

export function assertTaskTransition(from: TaskLifecycleStatus, to: TaskLifecycleStatus): void {
  if (!TASK_TRANSITIONS[from].has(to)) {
    throw new Error(`Illegal Task lifecycle transition: ${from} -> ${to}`)
  }
}

export function unresolvedTurns(turns: readonly TurnJournalRecord[]): readonly TurnJournalRecord[] {
  return turns.filter(turn => turn.status !== 'CLOSED' && turn.status !== 'ABORTED')
}

export function closureReplayTurns(turns: readonly TurnJournalRecord[]): readonly TurnJournalRecord[] {
  return turns.filter(turn => turn.status === 'SEALED' || turn.status === 'CLOSURE_PENDING')
}

export function guardNewTurn(
  turns: readonly TurnJournalRecord[],
  requestedTurnId: string,
): TurnStartGuardResult {
  const blocking = unresolvedTurns(turns).filter(turn => turn.turnId !== requestedTurnId)
  if (blocking.length === 0) return { allowed: true, blockingTurnIds: [] }
  return {
    allowed: false,
    blockingTurnIds: blocking.map(turn => turn.turnId),
    reason: `Previous Turn closure is unresolved: ${blocking.map(turn => `${turn.turnId}(${turn.status})`).join(', ')}`,
  }
}
