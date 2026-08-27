import { randomUUID } from 'node:crypto'
import {
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  renameSync,
  writeFileSync,
} from 'node:fs'
import { dirname, join } from 'node:path'
import {
  AGENT_GOVERNANCE_KERNEL_CONTRACT_VERSION,
  type AppendTurnRefsInput,
  type AttachReflectionInput,
  type BeginTurnInput,
  type CloseTurnInput,
  type MarkClosurePendingInput,
  type ProjectBinding,
  type TurnJournalRecord,
} from './contracts.js'
import {
  assertKernelIdentifier,
  assertProjectBinding,
  assertTurnTransition,
  projectBindingEquals,
  unresolvedTurns,
} from './lifecycle.js'

const unique = (values: readonly string[]): string[] =>
  [...new Set(values.map(value => value.trim()).filter(Boolean))]

const now = (): string => new Date().toISOString()

const atomicWriteJson = (file: string, value: unknown): void => {
  mkdirSync(dirname(file), { recursive: true })
  const temp = `${file}.${process.pid}.${randomUUID()}.tmp`
  writeFileSync(temp, `${JSON.stringify(value, null, 2)}\n`, 'utf-8')
  renameSync(temp, file)
}

const isStringArray = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every(item => typeof item === 'string')

const isBinding = (value: unknown): value is ProjectBinding => {
  if (typeof value !== 'object' || value === null) return false
  const kind = (value as { kind?: unknown }).kind
  return kind === 'UNBOUND'
    || (kind === 'BOUND' && typeof (value as { projectId?: unknown }).projectId === 'string')
}

const parseRecord = (file: string): TurnJournalRecord => {
  const value = JSON.parse(readFileSync(file, 'utf-8')) as Partial<TurnJournalRecord>
  if (value.contractVersion !== AGENT_GOVERNANCE_KERNEL_CONTRACT_VERSION) {
    throw new Error(`Unsupported Turn Journal contract in ${file}: ${String(value.contractVersion)}`)
  }
  if (typeof value.taskId !== 'string' || typeof value.turnId !== 'string' || typeof value.agentId !== 'string') {
    throw new Error(`Invalid Turn Journal identity in ${file}`)
  }
  if (!isBinding(value.projectBinding)) throw new Error(`Invalid projectBinding in ${file}`)
  assertProjectBinding(value.projectBinding)
  if (!['OPEN', 'SEALED', 'CLOSURE_PENDING', 'CLOSED'].includes(String(value.status))) {
    throw new Error(`Invalid Turn Journal status in ${file}: ${String(value.status)}`)
  }
  if (!isStringArray(value.userMessageRefs)
      || !isStringArray(value.assistantMessageRefs)
      || !isStringArray(value.toolEventRefs)
      || !isStringArray(value.resourceTouchRefs)) {
    throw new Error(`Invalid Turn Journal refs in ${file}`)
  }
  if (!Number.isInteger(value.revision) || Number(value.revision) < 1
      || !Number.isInteger(value.closureAttemptCount) || Number(value.closureAttemptCount) < 0) {
    throw new Error(`Invalid Turn Journal revision metadata in ${file}`)
  }
  if (typeof value.startedAt !== 'string') throw new Error(`Invalid startedAt in ${file}`)
  if (value.status !== 'OPEN' && typeof value.closingAt !== 'string') {
    throw new Error(`Turn Journal ${value.status} is missing closingAt in ${file}`)
  }
  if ((value.reflectionRef === undefined) !== (value.reflectionInputFingerprint === undefined)) {
    throw new Error(`Turn Journal has incomplete Reflection metadata in ${file}`)
  }
  if (value.status === 'CLOSED'
      && (typeof value.closedAt !== 'string'
        || typeof value.closureReceiptRef !== 'string'
        || typeof value.reflectionRef !== 'string')) {
    throw new Error(`CLOSED Turn Journal is missing Reflection/Closure Receipt metadata in ${file}`)
  }
  return value as TurnJournalRecord
}

export class TurnJournalStore {
  constructor(private readonly storageRoot: string) {
    mkdirSync(storageRoot, { recursive: true })
  }

  getStorageRoot(): string {
    return this.storageRoot
  }

  beginTurn(input: BeginTurnInput): TurnJournalRecord {
    this.assertIdentity(input.taskId, input.turnId, input.agentId)
    const binding = input.projectBinding ?? { kind: 'UNBOUND' as const }
    assertProjectBinding(binding)
    const existing = this.getTurn(input.taskId, input.turnId)
    if (existing) {
      if (existing.agentId !== input.agentId) {
        throw new Error(`Turn ${input.turnId} already exists with a different agent identity`)
      }
      if (projectBindingEquals(existing.projectBinding, binding) || binding.kind === 'UNBOUND') return existing
      if (existing.status === 'OPEN' && existing.projectBinding.kind === 'UNBOUND' && binding.kind === 'BOUND') {
        return this.bindProject(input.taskId, input.turnId, binding.projectId)
      }
      throw new Error(`Turn ${input.turnId} already exists with a different project binding`)
    }

    const record: TurnJournalRecord = {
      contractVersion: AGENT_GOVERNANCE_KERNEL_CONTRACT_VERSION,
      taskId: input.taskId,
      turnId: input.turnId,
      agentId: input.agentId,
      projectBinding: binding,
      startedAt: input.startedAt ?? now(),
      userMessageRefs: unique(input.userMessageRefs ?? []),
      assistantMessageRefs: [],
      toolEventRefs: [],
      resourceTouchRefs: [],
      ...(input.stateVersionBefore !== undefined ? { stateVersionBefore: input.stateVersionBefore } : {}),
      ...(input.sessionRef?.trim() ? { sessionRef: input.sessionRef.trim() } : {}),
      status: 'OPEN',
      revision: 1,
      closureAttemptCount: 0,
    }
    this.write(record)
    return record
  }

  getTurn(taskId: string, turnId: string): TurnJournalRecord | undefined {
    assertKernelIdentifier('taskId', taskId)
    assertKernelIdentifier('turnId', turnId)
    const file = this.turnFile(taskId, turnId)
    return existsSync(file) ? parseRecord(file) : undefined
  }

  listTurns(taskId: string): readonly TurnJournalRecord[] {
    assertKernelIdentifier('taskId', taskId)
    const dir = this.taskDir(taskId)
    if (!existsSync(dir)) return []
    return readdirSync(dir, { withFileTypes: true })
      .filter(entry => entry.isFile() && entry.name.endsWith('.json'))
      .map(entry => parseRecord(join(dir, entry.name)))
      .sort((a, b) => a.startedAt.localeCompare(b.startedAt) || a.turnId.localeCompare(b.turnId))
  }

  listUnresolvedTurns(taskId: string): readonly TurnJournalRecord[] {
    return unresolvedTurns(this.listTurns(taskId))
  }

  appendRefs(taskId: string, turnId: string, input: AppendTurnRefsInput): TurnJournalRecord {
    const current = this.requireTurn(taskId, turnId)
    if (current.status !== 'OPEN') throw new Error(`Turn ${turnId} is ${current.status}; Journal refs are sealed`)
    if (input.sessionRef?.trim() && current.sessionRef && current.sessionRef !== input.sessionRef.trim()) {
      throw new Error(`Turn ${turnId} sessionRef is immutable once set`)
    }
    const updated: TurnJournalRecord = {
      ...current,
      userMessageRefs: unique([...current.userMessageRefs, ...(input.userMessageRefs ?? [])]),
      assistantMessageRefs: unique([...current.assistantMessageRefs, ...(input.assistantMessageRefs ?? [])]),
      toolEventRefs: unique([...current.toolEventRefs, ...(input.toolEventRefs ?? [])]),
      resourceTouchRefs: unique([...current.resourceTouchRefs, ...(input.resourceTouchRefs ?? [])]),
      ...(input.sessionRef?.trim() && !current.sessionRef ? { sessionRef: input.sessionRef.trim() } : {}),
      revision: current.revision + 1,
    }
    this.write(updated)
    return updated
  }

  bindProject(taskId: string, turnId: string, projectId: string): TurnJournalRecord {
    assertKernelIdentifier('projectId', projectId)
    const current = this.requireTurn(taskId, turnId)
    if (current.status !== 'OPEN') throw new Error(`Turn ${turnId} project binding is sealed at ${current.status}`)
    if (current.projectBinding.kind === 'BOUND') {
      if (current.projectBinding.projectId === projectId) return current
      throw new Error(`Turn ${turnId} is already bound to project ${current.projectBinding.projectId}`)
    }
    const updated: TurnJournalRecord = {
      ...current,
      projectBinding: { kind: 'BOUND', projectId },
      revision: current.revision + 1,
    }
    this.write(updated)
    return updated
  }

  sealTurn(taskId: string, turnId: string, closingAt = now()): TurnJournalRecord {
    const current = this.requireTurn(taskId, turnId)
    if (current.status === 'SEALED' || current.status === 'CLOSURE_PENDING' || current.status === 'CLOSED') return current
    assertTurnTransition(current.status, 'SEALED')
    const updated: TurnJournalRecord = {
      ...current,
      status: 'SEALED',
      closingAt,
      revision: current.revision + 1,
    }
    this.write(updated)
    return updated
  }

  attachReflection(taskId: string, turnId: string, input: AttachReflectionInput): TurnJournalRecord {
    if (!input.reflectionRef.trim()) throw new Error('reflectionRef cannot be empty')
    if (!input.inputFingerprint.trim()) throw new Error('reflection inputFingerprint cannot be empty')
    const current = this.requireTurn(taskId, turnId)
    if (current.status === 'OPEN') throw new Error(`Turn ${turnId} must be sealed before Reflection can be attached`)
    if (current.reflectionRef) {
      if (current.reflectionRef === input.reflectionRef.trim()
          && current.reflectionInputFingerprint === input.inputFingerprint.trim()) return current
      throw new Error(`Turn ${turnId} already has different Reflection metadata`)
    }
    const updated: TurnJournalRecord = {
      ...current,
      reflectionRef: input.reflectionRef.trim(),
      reflectionInputFingerprint: input.inputFingerprint.trim(),
      revision: current.revision + 1,
    }
    this.write(updated)
    return updated
  }

  markClosurePending(
    taskId: string,
    turnId: string,
    input: MarkClosurePendingInput,
  ): TurnJournalRecord {
    if (!input.attemptId.trim()) throw new Error('closure attemptId cannot be empty')
    if (!input.reason.trim()) throw new Error('closure pending reason cannot be empty')
    const current = this.requireTurn(taskId, turnId)
    if (current.status === 'OPEN') throw new Error(`Turn ${turnId} must be sealed before closure can become pending`)
    if (current.status === 'CLOSED') throw new Error(`Turn ${turnId} is already CLOSED`)
    if (current.lastClosureAttemptId === input.attemptId) return current
    assertTurnTransition(current.status, 'CLOSURE_PENDING')
    const updated: TurnJournalRecord = {
      ...current,
      status: 'CLOSURE_PENDING',
      closureAttemptCount: current.closureAttemptCount + 1,
      lastClosureAttemptId: input.attemptId.trim(),
      lastClosureError: input.reason.trim(),
      revision: current.revision + 1,
    }
    this.write(updated)
    return updated
  }

  closeTurn(taskId: string, turnId: string, input: CloseTurnInput): TurnJournalRecord {
    if (!input.closureReceiptRef.trim()) throw new Error('closureReceiptRef cannot be empty')
    const current = this.requireTurn(taskId, turnId)
    if (current.status === 'OPEN') throw new Error(`Turn ${turnId} must be sealed before it can be CLOSED`)
    if (!current.reflectionRef) throw new Error(`Turn ${turnId} requires Unified Reflection before it can be CLOSED`)
    if (current.status === 'CLOSED') {
      if (current.closureReceiptRef === input.closureReceiptRef.trim()) return current
      throw new Error(`Turn ${turnId} is already CLOSED with a different Closure Receipt`)
    }
    assertTurnTransition(current.status, 'CLOSED')
    const updated: TurnJournalRecord = {
      ...current,
      status: 'CLOSED',
      closedAt: input.closedAt ?? now(),
      closureReceiptRef: input.closureReceiptRef.trim(),
      lastClosureError: undefined,
      revision: current.revision + 1,
    }
    this.write(updated)
    return updated
  }

  private requireTurn(taskId: string, turnId: string): TurnJournalRecord {
    const record = this.getTurn(taskId, turnId)
    if (!record) throw new Error(`Turn Journal not found: ${taskId}/${turnId}`)
    return record
  }

  private assertIdentity(taskId: string, turnId: string, agentId: string): void {
    assertKernelIdentifier('taskId', taskId)
    assertKernelIdentifier('turnId', turnId)
    assertKernelIdentifier('agentId', agentId)
  }

  private taskDir(taskId: string): string {
    return join(this.storageRoot, 'turn-journal', taskId)
  }

  private turnFile(taskId: string, turnId: string): string {
    return join(this.taskDir(taskId), `${turnId}.json`)
  }

  private write(record: TurnJournalRecord): void {
    atomicWriteJson(this.turnFile(record.taskId, record.turnId), record)
  }
}
