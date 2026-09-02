import { randomUUID } from 'node:crypto'
import { Service, type Context } from '@deepseek-ai/cordis'
import '@agent-harness/project-manager'
import '@agent-harness/architecture-navigator'
import '@agent-harness/rule-manager'
import '@agent-harness/knowledge-manager'
import '@agent-harness/gate-manager'
import '@agent-harness/evidence-state-manager'
import {
  assertContextLint,
  lintContextSession,
  type ContextLintResult,
} from './context-lint.js'
import type {
  ContextCompass,
  ContextFrame,
  ContextHandle,
  ContextHandleInput,
  ContextHandoff,
  InlineContextItem,
  ContextLedgerEntry,
  ContextProgressLedger,
  ContextProgressLedgerPatch,
  ContextRecentEvent,
  ContextRecentEventInput,
  ContextReference,
  ContextRebuildInput,
  ContextSession,
  ContextSessionSnapshot,
  ContextStartTaskInput,
  ContextTaskLedger,
  ContextTaskLedgerPatch,
  ContextTurnClosureInput,
} from './contracts.js'

const DEFAULT_MAX_CHARS = 18000
const DEFAULT_RECENT_TAIL_LIMIT = 5
const MAX_RECENT_TAIL_LIMIT = 12
const MAX_WORKING_SET = 64
const MAX_HANDLES = 128
const MAX_INLINE_ITEMS = 24
const MAX_INLINE_ITEM_CHARS = 8_000
const MAX_INLINE_TOTAL_CHARS = 17_000
const MAX_INHERITED_CONTEXT_TASKS = 4
const MAX_INHERITED_CONTEXT_CHARS = 1_000
const MAX_INHERITED_ITEM_CHARS = 1_000
const PRIOR_CONTEXT_PREFIX = 'prior-context-'
const RESERVED_INLINE_IDS = new Set([
  'context-compass',
  'task-ledger',
  'progress-ledger',
  'recent-tail',
  'available-handles',
])
const MAX_LEDGER_ENTRIES = 64
const MAX_PLAN_ITEMS = 32
const ROUTE_MAP_LIMIT = 8

const PRIORITY_RANK = { required: 4, high: 3, normal: 2, low: 1 } as const

const now = (): string => new Date().toISOString()
const same = (left: unknown, right: unknown): boolean => JSON.stringify(left) === JSON.stringify(right)

const nonEmpty = (name: string, value: string): string => {
  const trimmed = value.trim()
  if (!trimmed) throw new Error(`${name} 不能为空`)
  return trimmed
}

const normalizeStringList = (values: readonly string[] | undefined, limit: number, name: string): string[] => {
  if (!values) return []
  const normalized = [...new Set(values.map(value => value.trim()).filter(Boolean))]
  if (normalized.length > limit) throw new Error(`${name} 超过上限 ${limit}`)
  return normalized
}

const normalizeEntries = (entries: readonly ContextLedgerEntry[] | undefined, name: string): ContextLedgerEntry[] => {
  if (!entries) return []
  if (entries.length > MAX_LEDGER_ENTRIES) throw new Error(`${name} 超过上限 ${MAX_LEDGER_ENTRIES}`)
  return entries.map(entry => ({
    text: nonEmpty(`${name}.text`, entry.text),
    refs: normalizeStringList(entry.refs, 32, `${name}.refs`),
  }))
}

const referenceKey = (reference: ContextReference): string => `${reference.kind}:${reference.id.trim()}`

const normalizeReferences = (references: readonly ContextReference[]): ContextReference[] => {
  const deduped = new Map<string, ContextReference>()
  for (const reference of references) {
    const id = nonEmpty('Context reference id', reference.id)
    const normalized: ContextReference = {
      kind: reference.kind,
      id,
      ...(reference.priority ? { priority: reference.priority } : {}),
    }
    const key = referenceKey(normalized)
    const current = deduped.get(key)
    if (!current
      || PRIORITY_RANK[normalized.priority ?? 'normal'] > PRIORITY_RANK[current.priority ?? 'normal']) {
      deduped.set(key, normalized)
    }
  }
  const result = [...deduped.values()]
  if (result.length > MAX_WORKING_SET) throw new Error(`Working Set 超过上限 ${MAX_WORKING_SET}`)
  return result
}

export const normalizeInlineContextItems = (
  items: readonly InlineContextItem[] | undefined,
): InlineContextItem[] => {
  if (!items) return []
  if (items.length > MAX_INLINE_ITEMS) throw new Error(`Inline Context Items 超过上限 ${MAX_INLINE_ITEMS}`)
  const deduped = new Map<string, InlineContextItem>()
  let totalChars = 0
  for (const item of items) {
    const id = nonEmpty('Inline Context item id', item.id)
    if (!/^[A-Za-z0-9._:-]+$/.test(id)) throw new Error(`Inline Context item id 非法: ${id}`)
    if (RESERVED_INLINE_IDS.has(id)) throw new Error(`Inline Context item id 与 Runtime 保留项冲突: ${id}`)
    if (deduped.has(id)) throw new Error(`Inline Context item id 重复: ${id}`)
    const content = nonEmpty(`Inline Context ${id} content`, item.content)
    if (content.length > MAX_INLINE_ITEM_CHARS) {
      throw new Error(`Inline Context ${id} 超过 ${MAX_INLINE_ITEM_CHARS} 字符上限`)
    }
    totalChars += content.length
    if (totalChars > MAX_INLINE_TOTAL_CHARS) {
      throw new Error(`Inline Context 总内容超过 ${MAX_INLINE_TOTAL_CHARS} 字符上限`)
    }
    deduped.set(id, {
      id,
      title: nonEmpty(`Inline Context ${id} title`, item.title),
      content,
      priority: item.priority ?? 'high',
      provenance: nonEmpty(`Inline Context ${id} provenance`, item.provenance),
    })
  }
  return [...deduped.values()]
}

const normalizeHandles = (handles: readonly ContextHandleInput[]): ContextHandle[] => {
  const stamp = now()
  const deduped = new Map<string, ContextHandle>()
  for (const handle of handles) {
    const reference = nonEmpty('Context handle reference', handle.reference)
    deduped.set(reference, {
      kind: handle.kind,
      reference,
      ...(handle.title?.trim() ? { title: handle.title.trim() } : {}),
      ...(handle.summary?.trim() ? { summary: handle.summary.trim() } : {}),
      addedAt: stamp,
    })
  }
  const result = [...deduped.values()]
  if (result.length > MAX_HANDLES) throw new Error(`Context Handles 超过上限 ${MAX_HANDLES}`)
  return result
}

const isContextSession = (value: unknown): value is ContextSession => {
  if (!value || typeof value !== 'object') return false
  const item = value as Partial<ContextSession>
  return typeof item.projectId === 'string'
    && typeof item.taskId === 'string'
    && typeof item.status === 'string'
    && typeof item.generation === 'number'
    && typeof item.maxChars === 'number'
    && typeof item.recentTailLimit === 'number'
    && !!item.taskLedger
    && !!item.progressLedger
    && Array.isArray(item.workingSet)
    && (item.inlineItems === undefined || Array.isArray(item.inlineItems))
    && Array.isArray(item.handles)
    && Array.isArray(item.recentTail)
}

export interface ContextStateRecordLike {
  readonly scope: string
  readonly key: string
  readonly value: unknown
  readonly version: number
  readonly updatedAt: string
}

const refToken = (value: string): string => {
  const trimmed = value.trim()
  if (!trimmed) return ''
  const tail = trimmed.split(/[\/#]/).filter(Boolean).at(-1) ?? trimmed
  return tail.toUpperCase()
}

const sessionRefTokens = (session: ContextSession): Set<string> => new Set([
  ...session.workingSet.map(reference => reference.id),
  ...session.taskLedger.scopeRefs,
  ...session.taskLedger.constraintRefs,
  ...session.taskLedger.confirmed.flatMap(entry => entry.refs),
  ...session.taskLedger.openIssues.flatMap(entry => entry.refs),
  ...session.progressLedger.touchedRefs,
].map(refToken).filter(Boolean))

const matchingEntries = (
  entries: readonly ContextLedgerEntry[],
  currentRefs: ReadonlySet<string>,
): ContextLedgerEntry[] => entries.filter(entry =>
  entry.refs.some(ref => currentRefs.has(refToken(ref))),
)

const boundedLines = (lines: readonly string[], maxChars: number): string => {
  const selected: string[] = []
  let used = 0
  for (const line of lines) {
    const addition = (selected.length > 0 ? 1 : 0) + line.length
    if (used + addition > maxChars) break
    selected.push(line)
    used += addition
  }
  return selected.join('\n')
}

const hasClosedTurnContext = (session: ContextSession): boolean =>
  session.progressLedger.lastAction?.startsWith('Close governed Turn ') === true

export const selectRelevantContextHistory = (input: {
  readonly projectId: string
  readonly currentTaskId: string
  readonly references: readonly ContextReference[]
  readonly records: readonly ContextStateRecordLike[]
  readonly existingInlineItems?: readonly InlineContextItem[]
}): InlineContextItem[] => {
  const currentRefs = new Set(input.references.map(reference => refToken(reference.id)).filter(Boolean))
  if (currentRefs.size === 0) return []

  const existingChars = (input.existingInlineItems ?? []).reduce((total, item) => total + item.content.length, 0)
  let remaining = Math.min(
    MAX_INHERITED_CONTEXT_CHARS,
    Math.max(0, MAX_INLINE_TOTAL_CHARS - existingChars),
  )
  if (remaining <= 0) return []

  const candidates = input.records
    .filter(record => record.key === 'session' && record.scope.startsWith('context:') && isContextSession(record.value))
    .map(record => ({ record, session: record.value as ContextSession }))
    .filter(({ session }) => session.projectId === input.projectId
      && session.taskId !== input.currentTaskId
      && (
        session.status === 'COMPLETED'
        || session.status === 'PAUSED'
        || (session.status === 'ACTIVE' && hasClosedTurnContext(session))
      ))
    .map(item => {
      const historicalRefs = sessionRefTokens(item.session)
      const matchedRefs = [...currentRefs].filter(ref => historicalRefs.has(ref))
      return { ...item, matchedRefs }
    })
    .filter(item => item.matchedRefs.length > 0)
    .sort((left, right) =>
      right.matchedRefs.length - left.matchedRefs.length
      || right.record.updatedAt.localeCompare(left.record.updatedAt),
    )
    .slice(0, MAX_INHERITED_CONTEXT_TASKS)

  const result: InlineContextItem[] = []
  for (const { record, session, matchedRefs } of candidates) {
    const confirmed = matchingEntries(session.taskLedger.confirmed, currentRefs).slice(0, 4)
    const openIssues = matchingEntries(session.taskLedger.openIssues, currentRefs).slice(0, 4)
    const next = [...new Set([...session.taskLedger.plan, ...session.progressLedger.next])].slice(0, 4)
    const lines = [
      `SourceTask: ${session.taskId}`,
      `MatchedRefs: ${matchedRefs.join(', ')}`,
      `Goal: ${session.taskLedger.goal}`,
      ...confirmed.map(entry => `Confirmed: ${entry.text}`),
      ...openIssues.map(entry => `OpenIssue: ${entry.text}`),
      ...(session.progressLedger.currentProblem?.trim()
        ? [`CurrentProblem: ${session.progressLedger.currentProblem.trim()}`]
        : []),
      ...next.map(item => `Next: ${item}`),
    ]
    const content = boundedLines(lines, Math.min(MAX_INHERITED_ITEM_CHARS, remaining))
    if (!content || (!confirmed.length && !openIssues.length && !session.progressLedger.currentProblem?.trim())) continue
    result.push({
      id: `${PRIOR_CONTEXT_PREFIX}${session.taskId}`,
      title: `Relevant Prior Context — ${session.taskId}`,
      content,
      priority: 'high',
      provenance: `context://project/${input.projectId}/task/${session.taskId}/state/${record.version}`,
    })
    remaining -= content.length
    if (remaining <= 0) break
  }
  return result
}

const stateScope = (taskId: string): string => `context:${taskId}`

export class ContextManagementService extends Service {
  static inject = ['contextBuilder']

  private readonly runtimeContext: Context

  constructor(ctx: Context) {
    super(ctx, 'contextManager')
    this.runtimeContext = ctx
  }

  beginTask(input: ContextStartTaskInput): ContextSessionSnapshot {
    this.requireProject(input.projectId)
    const taskId = nonEmpty('taskId', input.taskId)
    const goal = nonEmpty('goal', input.goal)
    if (this.runtimeContext.evidenceStateManager.readState(input.projectId, stateScope(taskId), 'session')) {
      throw new Error(`Context task 已存在: ${input.projectId}/${taskId}`)
    }
    const stamp = now()
    const session: ContextSession = {
      projectId: input.projectId,
      taskId,
      status: 'ACTIVE',
      generation: 1,
      maxChars: input.maxChars ?? DEFAULT_MAX_CHARS,
      recentTailLimit: Math.min(Math.max(input.recentTailLimit ?? DEFAULT_RECENT_TAIL_LIMIT, 1), MAX_RECENT_TAIL_LIMIT),
      taskLedger: {
        goal,
        phase: 'bootstrap',
        scopeRefs: [],
        constraintRefs: [],
        confirmed: [],
        assumptions: [],
        openIssues: [],
        plan: [],
        updatedAt: stamp,
      },
      progressLedger: {
        touchedRefs: [],
        blockers: [],
        next: [],
        evidenceRefs: [],
        updatedAt: stamp,
      },
      workingSet: [],
      inlineItems: normalizeInlineContextItems(input.inlineItems),
      handles: [],
      recentTail: [],
      createdAt: stamp,
      updatedAt: stamp,
    }
    const lint = lintContextSession(session)
    assertContextLint(lint)
    const record = this.runtimeContext.evidenceStateManager.updateState({
      projectId: input.projectId,
      scope: stateScope(taskId),
      key: 'session',
      value: session,
      reason: `Begin Context task ${taskId}`,
      evidenceRefs: [],
      expectedVersion: 0,
    })
    return { stateVersion: record.version, session }
  }

  getTask(projectId: string, taskId: string): ContextSessionSnapshot {
    this.requireProject(projectId)
    const record = this.runtimeContext.evidenceStateManager.readState(projectId, stateScope(nonEmpty('taskId', taskId)), 'session')
    if (!record || !isContextSession(record.value)) throw new Error(`Context task 不存在: ${projectId}/${taskId}`)
    if (record.value.projectId !== projectId || record.value.taskId !== taskId) {
      throw new Error(`Context task 项目隔离失败: ${projectId}/${taskId}`)
    }
    const session: ContextSession = record.value.inlineItems === undefined
      ? { ...record.value, inlineItems: [] }
      : record.value
    return { stateVersion: record.version, session }
  }

  lintTask(projectId: string, taskId: string): ContextLintResult {
    return lintContextSession(this.getTask(projectId, taskId).session)
  }

  updateTaskLedger(projectId: string, taskId: string, patch: ContextTaskLedgerPatch): ContextSessionSnapshot {
    const snapshot = this.getTask(projectId, taskId)
    const current = snapshot.session.taskLedger
    const stamp = now()
    const taskLedger: ContextTaskLedger = {
      goal: patch.goal !== undefined ? nonEmpty('Task Ledger goal', patch.goal) : current.goal,
      phase: patch.phase ?? current.phase,
      scopeRefs: patch.scopeRefs !== undefined
        ? normalizeStringList(patch.scopeRefs, MAX_LEDGER_ENTRIES, 'scopeRefs')
        : current.scopeRefs,
      constraintRefs: patch.constraintRefs !== undefined
        ? normalizeStringList(patch.constraintRefs, MAX_LEDGER_ENTRIES, 'constraintRefs')
        : current.constraintRefs,
      confirmed: patch.confirmed !== undefined
        ? normalizeEntries(patch.confirmed, 'confirmed')
        : current.confirmed,
      assumptions: patch.assumptions !== undefined
        ? normalizeEntries(patch.assumptions, 'assumptions')
        : current.assumptions,
      openIssues: patch.openIssues !== undefined
        ? normalizeEntries(patch.openIssues, 'openIssues')
        : current.openIssues,
      plan: patch.plan !== undefined
        ? normalizeStringList(patch.plan, MAX_PLAN_ITEMS, 'plan')
        : current.plan,
      updatedAt: stamp,
    }
    return this.commit(snapshot, { ...snapshot.session, taskLedger, updatedAt: stamp }, 'Update Task Ledger')
  }

  updateProgressLedger(projectId: string, taskId: string, patch: ContextProgressLedgerPatch): ContextSessionSnapshot {
    const snapshot = this.getTask(projectId, taskId)
    const current = snapshot.session.progressLedger
    const stamp = now()
    const progressLedger: ContextProgressLedger = {
      ...(patch.lastAction !== undefined
        ? patch.lastAction.trim() ? { lastAction: patch.lastAction.trim() } : {}
        : current.lastAction ? { lastAction: current.lastAction } : {}),
      ...(patch.lastResult !== undefined
        ? patch.lastResult.trim() ? { lastResult: patch.lastResult.trim() } : {}
        : current.lastResult ? { lastResult: current.lastResult } : {}),
      touchedRefs: patch.touchedRefs !== undefined
        ? normalizeStringList(patch.touchedRefs, MAX_LEDGER_ENTRIES, 'touchedRefs')
        : current.touchedRefs,
      ...(patch.currentProblem !== undefined
        ? patch.currentProblem.trim() ? { currentProblem: patch.currentProblem.trim() } : {}
        : current.currentProblem ? { currentProblem: current.currentProblem } : {}),
      blockers: patch.blockers !== undefined
        ? normalizeStringList(patch.blockers, MAX_LEDGER_ENTRIES, 'blockers')
        : current.blockers,
      next: patch.next !== undefined
        ? normalizeStringList(patch.next, MAX_PLAN_ITEMS, 'next')
        : current.next,
      evidenceRefs: patch.evidenceRefs !== undefined
        ? normalizeStringList(patch.evidenceRefs, MAX_LEDGER_ENTRIES, 'evidenceRefs')
        : current.evidenceRefs,
      updatedAt: stamp,
    }
    return this.commit(
      snapshot,
      { ...snapshot.session, progressLedger, updatedAt: stamp },
      'Update Progress Ledger',
      progressLedger.evidenceRefs,
    )
  }

  applyTurnClosure(
    projectId: string,
    taskId: string,
    input: ContextTurnClosureInput,
  ): ContextSessionSnapshot {
    const snapshot = this.getTask(projectId, taskId)
    if (snapshot.session.status === 'COMPLETED' || snapshot.session.status === 'ABORTED') {
      throw new Error(`Context task is terminal: ${projectId}/${taskId}/${snapshot.session.status}`)
    }
    const turnId = nonEmpty('turnId', input.turnId)
    const confirmed = normalizeEntries(input.confirmed, 'confirmed')
    const assumptions = normalizeEntries(input.assumptions, 'assumptions')
    const openIssues = normalizeEntries(input.openIssues, 'openIssues')
    const plan = normalizeStringList(input.plan, MAX_PLAN_ITEMS, 'plan')
    const touchedRefs = normalizeStringList(input.touchedRefs, MAX_LEDGER_ENTRIES, 'touchedRefs')
    const evidenceRefs = normalizeStringList(input.evidenceRefs, MAX_LEDGER_ENTRIES, 'evidenceRefs')
    const workingSet = normalizeReferences(input.workingSet)
    const lastAction = `Close governed Turn ${turnId}`
    const lastResult = nonEmpty('Context closure progress', input.progress)
    const current = snapshot.session
    if (current.progressLedger.lastAction === lastAction
        && current.progressLedger.lastResult === lastResult
        && same(current.taskLedger.confirmed, confirmed)
        && same(current.taskLedger.assumptions, assumptions)
        && same(current.taskLedger.openIssues, openIssues)
        && same(current.taskLedger.plan, plan)
        && same(current.progressLedger.touchedRefs, touchedRefs)
        && same(current.progressLedger.next, plan)
        && same(current.progressLedger.evidenceRefs, evidenceRefs)
        && same(current.workingSet, workingSet)) {
      return snapshot
    }
    const stamp = now()
    const taskLedger: ContextTaskLedger = {
      ...current.taskLedger,
      confirmed,
      assumptions,
      openIssues,
      plan,
      updatedAt: stamp,
    }
    const progressLedger: ContextProgressLedger = {
      ...(current.progressLedger.currentProblem ? { currentProblem: current.progressLedger.currentProblem } : {}),
      lastAction,
      lastResult,
      touchedRefs,
      blockers: current.progressLedger.blockers,
      next: plan,
      evidenceRefs,
      updatedAt: stamp,
    }
    return this.commit(
      snapshot,
      {
        ...current,
        taskLedger,
        progressLedger,
        workingSet,
        updatedAt: stamp,
      },
      `Apply governed Turn ${turnId} Context closure`,
      evidenceRefs,
    )
  }

  attach(projectId: string, taskId: string, references: readonly ContextReference[]): ContextSessionSnapshot {
    const snapshot = this.getTask(projectId, taskId)
    const workingSet = normalizeReferences([...snapshot.session.workingSet, ...references])
    return this.commit(
      snapshot,
      { ...snapshot.session, workingSet, updatedAt: now() },
      `Attach ${references.length} context reference(s)`,
    )
  }

  detach(projectId: string, taskId: string, references: readonly ContextReference[]): ContextSessionSnapshot {
    const snapshot = this.getTask(projectId, taskId)
    const remove = new Set(references.map(referenceKey))
    const workingSet = snapshot.session.workingSet.filter(reference => !remove.has(referenceKey(reference)))
    return this.commit(
      snapshot,
      { ...snapshot.session, workingSet, updatedAt: now() },
      `Detach ${references.length} context reference(s)`,
    )
  }

  replaceWorkingSet(projectId: string, taskId: string, references: readonly ContextReference[]): ContextSessionSnapshot {
    const snapshot = this.getTask(projectId, taskId)
    const workingSet = normalizeReferences(references)
    const baseInlineItems = (snapshot.session.inlineItems ?? [])
      .filter(item => !item.id.startsWith(PRIOR_CONTEXT_PREFIX))
    const inherited = selectRelevantContextHistory({
      projectId,
      currentTaskId: taskId,
      references: workingSet,
      records: this.runtimeContext.evidenceStateManager.snapshot(projectId).records,
      existingInlineItems: baseInlineItems,
    })
    const inlineItems = normalizeInlineContextItems([...baseInlineItems, ...inherited])
    return this.commit(
      snapshot,
      { ...snapshot.session, workingSet, inlineItems, updatedAt: now() },
      'Replace Context Working Set',
    )
  }

  replaceInlineItems(
    projectId: string,
    taskId: string,
    items: readonly InlineContextItem[],
  ): ContextSessionSnapshot {
    const snapshot = this.getTask(projectId, taskId)
    const inlineItems = normalizeInlineContextItems(items)
    return this.commit(
      snapshot,
      { ...snapshot.session, inlineItems, updatedAt: now() },
      `Replace ${inlineItems.length} Inline Context Item(s)`,
    )
  }

  attachInlineItems(
    projectId: string,
    taskId: string,
    items: readonly InlineContextItem[],
  ): ContextSessionSnapshot {
    const snapshot = this.getTask(projectId, taskId)
    const inlineItems = normalizeInlineContextItems([...(snapshot.session.inlineItems ?? []), ...items])
    return this.commit(
      snapshot,
      { ...snapshot.session, inlineItems, updatedAt: now() },
      `Attach ${items.length} Inline Context Item(s)`,
    )
  }

  addHandles(projectId: string, taskId: string, inputs: readonly ContextHandleInput[]): ContextSessionSnapshot {
    const snapshot = this.getTask(projectId, taskId)
    const existing = new Map(snapshot.session.handles.map(handle => [handle.reference, handle]))
    for (const handle of normalizeHandles(inputs)) existing.set(handle.reference, handle)
    const handles = [...existing.values()]
    if (handles.length > MAX_HANDLES) throw new Error(`Context Handles 超过上限 ${MAX_HANDLES}`)
    return this.commit(snapshot, { ...snapshot.session, handles, updatedAt: now() }, `Add ${inputs.length} Context Handle(s)`)
  }

  removeHandles(projectId: string, taskId: string, references: readonly string[]): ContextSessionSnapshot {
    const snapshot = this.getTask(projectId, taskId)
    const remove = new Set(references.map(value => value.trim()).filter(Boolean))
    const handles = snapshot.session.handles.filter(handle => !remove.has(handle.reference))
    return this.commit(snapshot, { ...snapshot.session, handles, updatedAt: now() }, `Remove ${remove.size} Context Handle(s)`)
  }

  recordRecent(projectId: string, taskId: string, input: ContextRecentEventInput): ContextSessionSnapshot {
    const snapshot = this.getTask(projectId, taskId)
    const event: ContextRecentEvent = {
      kind: input.kind,
      summary: nonEmpty('Recent event summary', input.summary),
      refs: normalizeStringList(input.refs, 32, 'recent.refs'),
      evidenceRefs: normalizeStringList(input.evidenceRefs, 32, 'recent.evidenceRefs'),
      eventId: `CTX-${randomUUID()}`,
      recordedAt: now(),
    }
    const recentTail = [...snapshot.session.recentTail, event].slice(-snapshot.session.recentTailLimit)
    return this.commit(
      snapshot,
      { ...snapshot.session, recentTail, updatedAt: now() },
      `Record Context recent event ${event.kind}`,
      event.evidenceRefs,
    )
  }

  rebuild(input: ContextRebuildInput): ContextSessionSnapshot {
    const snapshot = this.getTask(input.projectId, input.taskId)
    if (snapshot.session.status === 'COMPLETED' || snapshot.session.status === 'ABORTED') {
      throw new Error(`Cannot rebuild terminal Context task: ${input.projectId}/${input.taskId}`)
    }
    const stamp = now()
    const taskLedger = input.phase
      ? { ...snapshot.session.taskLedger, phase: input.phase, updatedAt: stamp }
      : snapshot.session.taskLedger
    const workingSet = input.workingSet !== undefined
      ? normalizeReferences(input.workingSet)
      : snapshot.session.workingSet
    const inlineItems = input.inlineItems !== undefined
      ? normalizeInlineContextItems(input.inlineItems)
      : snapshot.session.inlineItems ?? []
    const next: ContextSession = {
      ...snapshot.session,
      status: 'ACTIVE',
      generation: snapshot.session.generation + 1,
      taskLedger,
      workingSet,
      inlineItems,
      recentTail: input.clearRecentTail === false ? snapshot.session.recentTail : [],
      updatedAt: stamp,
    }
    return this.commit(snapshot, next, `Rebuild Context generation ${next.generation}`, input.evidenceRefs ?? [])
  }

  pause(projectId: string, taskId: string): ContextSessionSnapshot {
    const snapshot = this.getTask(projectId, taskId)
    if (snapshot.session.status !== 'ACTIVE') return snapshot
    return this.commit(snapshot, { ...snapshot.session, status: 'PAUSED', updatedAt: now() }, 'Pause context task')
  }

  resume(projectId: string, taskId: string): ContextFrame {
    const snapshot = this.getTask(projectId, taskId)
    if (snapshot.session.status === 'COMPLETED' || snapshot.session.status === 'ABORTED') {
      throw new Error(`Cannot resume terminal Context task: ${projectId}/${taskId}/${snapshot.session.status}`)
    }
    const updated = snapshot.session.status === 'ACTIVE'
      ? snapshot
      : this.commit(snapshot, { ...snapshot.session, status: 'ACTIVE', updatedAt: now() }, 'Resume context task')
    return this.buildFrame(updated.session.projectId, updated.session.taskId)
  }

  complete(projectId: string, taskId: string): ContextSessionSnapshot {
    const snapshot = this.getTask(projectId, taskId)
    if (snapshot.session.status === 'COMPLETED') return snapshot
    if (snapshot.session.status === 'ABORTED') {
      throw new Error(`Cannot complete aborted Context task: ${projectId}/${taskId}`)
    }
    const stamp = now()
    const session: ContextSession = {
      ...snapshot.session,
      status: 'COMPLETED',
      generation: snapshot.session.generation + 1,
      taskLedger: { ...snapshot.session.taskLedger, phase: 'complete', updatedAt: stamp },
      recentTail: [],
      updatedAt: stamp,
    }
    return this.commit(snapshot, session, 'Complete context task')
  }

  abort(projectId: string, taskId: string, reasonInput: string): ContextSessionSnapshot {
    const snapshot = this.getTask(projectId, taskId)
    if (snapshot.session.status === 'ABORTED') return snapshot
    if (snapshot.session.status === 'COMPLETED') {
      throw new Error(`Cannot abort completed Context task: ${projectId}/${taskId}`)
    }
    const reason = nonEmpty('abort reason', reasonInput)
    const stamp = now()
    const progressLedger: ContextProgressLedger = {
      lastAction: 'Governance task aborted.',
      lastResult: reason,
      touchedRefs: snapshot.session.progressLedger.touchedRefs,
      currentProblem: reason,
      blockers: [],
      next: [],
      evidenceRefs: snapshot.session.progressLedger.evidenceRefs,
      updatedAt: stamp,
    }
    return this.commit(
      snapshot,
      {
        ...snapshot.session,
        status: 'ABORTED',
        generation: snapshot.session.generation + 1,
        progressLedger,
        recentTail: [],
        updatedAt: stamp,
      },
      'Abort context task',
      progressLedger.evidenceRefs,
    )
  }

  createHandoff(projectId: string, taskId: string): ContextHandoff {
    const { session } = this.getTask(projectId, taskId)
    assertContextLint(lintContextSession(session))
    return {
      projectId,
      taskId,
      generation: session.generation,
      createdAt: now(),
      taskLedger: session.taskLedger,
      progressLedger: session.progressLedger,
      workingSet: session.workingSet,
      inlineItems: session.inlineItems ?? [],
      handles: session.handles,
    }
  }

  buildCompass(projectId: string): ContextCompass {
    const project = this.requireProject(projectId)
    const resourceHandles = [
      `project://${projectId}/architecture`,
      `project://${projectId}/rules`,
      `project://${projectId}/knowledge`,
      `knowledge://global`,
      `project://${projectId}/gates`,
    ]
    const routeMap: string[] = []

    const appendFiles = (label: string, files: readonly { id: string; title: string; summary: string }[]) => {
      for (const file of files.slice(0, ROUTE_MAP_LIMIT)) {
        routeMap.push(`${label} ${file.id} ${file.title}${file.summary ? ` — ${file.summary}` : ''}`)
      }
      if (files.length > ROUTE_MAP_LIMIT) routeMap.push(`${label} ... +${files.length - ROUTE_MAP_LIMIT} more`)
    }

    appendFiles('ARCH', this.runtimeContext.architectureNavigator.listFiles(projectId))
    appendFiles('RULE', this.runtimeContext.ruleManager.listFiles(projectId))
    appendFiles('PROJECT-KNOWLEDGE', this.runtimeContext.knowledgeManager.listFiles(projectId))
    appendFiles('GATE', this.runtimeContext.gateManager.listFiles(projectId))

    try {
      const roots = this.runtimeContext.knowledgeManager.listGlobalCategories()
      for (const category of roots.slice(0, ROUTE_MAP_LIMIT)) {
        routeMap.push(`GLOBAL-KNOWLEDGE ${category.id} ${category.title}`)
      }
      if (roots.length > ROUTE_MAP_LIMIT) routeMap.push(`GLOBAL-KNOWLEDGE ... +${roots.length - ROUTE_MAP_LIMIT} more`)
    } catch {
      // Global Knowledge is optional for a standalone Context Builder runtime.
    }

    return {
      projectId,
      displayName: project.displayName,
      ...(project.projectType ? { projectType: project.projectType } : {}),
      resourceHandles,
      routeMap,
      builtAt: now(),
    }
  }

  buildFrame(projectId: string, taskId: string, maxChars?: number): ContextFrame {
    const snapshot = this.getTask(projectId, taskId)
    const session = snapshot.session
    const lint = lintContextSession(session)
    assertContextLint(lint)
    const compass = this.buildCompass(projectId)
    const basePack = this.runtimeContext.contextBuilder.buildContext({
      projectId,
      taskSummary: session.taskLedger.goal,
      references: session.workingSet,
      maxChars: maxChars ?? session.maxChars,
      inlineItems: [
        {
          id: 'context-compass',
          title: 'Project Compass',
          content: this.renderCompass(compass),
          priority: 'required',
          provenance: `runtime://${projectId}/context/compass`,
        },
        {
          id: 'task-ledger',
          title: 'Task Ledger',
          content: this.renderTaskLedger(session.taskLedger),
          priority: 'required',
          provenance: `runtime://${projectId}/context/${taskId}/task-ledger`,
        },
        {
          id: 'progress-ledger',
          title: 'Progress Ledger',
          content: this.renderProgressLedger(session.progressLedger),
          priority: 'high',
          provenance: `runtime://${projectId}/context/${taskId}/progress-ledger`,
        },
        ...(session.inlineItems ?? []),
        ...(session.recentTail.length > 0 ? [{
          id: 'recent-tail',
          title: 'Recent Tail',
          content: session.recentTail.map(event =>
            `${event.kind}: ${event.summary}${event.refs.length > 0 ? ` | Refs: ${event.refs.join(', ')}` : ''}`,
          ).join('\n'),
          priority: 'normal' as const,
          provenance: `runtime://${projectId}/context/${taskId}/recent-tail`,
        }] : []),
        ...(session.handles.length > 0 ? [{
          id: 'available-handles',
          title: 'Available Handles',
          content: session.handles.map(handle =>
            `${handle.kind}: ${handle.reference}${handle.title ? ` | ${handle.title}` : ''}${handle.summary ? ` — ${handle.summary}` : ''}`,
          ).join('\n'),
          priority: 'low' as const,
          provenance: `runtime://${projectId}/context/${taskId}/handles`,
        }] : []),
      ],
    })
    const pack = lint.warnings.length === 0
      ? basePack
      : {
          ...basePack,
          warnings: [...new Set([
            ...basePack.warnings,
            ...lint.warnings.map(item => `Context Lint ${item.code}@${item.field}: ${item.message}`),
          ])],
        }

    return {
      taskId,
      generation: session.generation,
      stateVersion: snapshot.stateVersion,
      builtAt: now(),
      sessionStatus: session.status,
      pack,
    }
  }

  private renderCompass(compass: ContextCompass): string {
    return [
      `Project: ${compass.displayName} (${compass.projectId})`,
      compass.projectType ? `Type: ${compass.projectType}` : '',
      `Resources: ${compass.resourceHandles.join(', ')}`,
      compass.routeMap.length > 0 ? `Route Map:\n${compass.routeMap.map(line => `- ${line}`).join('\n')}` : '',
      `BuiltAt: ${compass.builtAt}`,
    ].filter(Boolean).join('\n')
  }

  private renderTaskLedger(ledger: ContextTaskLedger): string {
    const entries = (name: string, values: readonly ContextLedgerEntry[]): string =>
      values.length > 0
        ? `${name}:\n${values.map(value => `- ${value.text}${value.refs.length > 0 ? ` | Refs: ${value.refs.join(', ')}` : ''}`).join('\n')}`
        : `${name}: -`
    return [
      `Goal: ${ledger.goal}`,
      `Phase: ${ledger.phase}`,
      `ScopeRefs: ${ledger.scopeRefs.join(', ') || '-'}`,
      `ConstraintRefs: ${ledger.constraintRefs.join(', ') || '-'}`,
      entries('Confirmed', ledger.confirmed),
      entries('Assumptions', ledger.assumptions),
      entries('OpenIssues', ledger.openIssues),
      `Plan: ${ledger.plan.join(' -> ') || '-'}`,
      `UpdatedAt: ${ledger.updatedAt}`,
    ].join('\n')
  }

  private renderProgressLedger(ledger: ContextProgressLedger): string {
    return [
      `LastAction: ${ledger.lastAction ?? '-'}`,
      `LastResult: ${ledger.lastResult ?? '-'}`,
      `Touched: ${ledger.touchedRefs.join(', ') || '-'}`,
      `CurrentProblem: ${ledger.currentProblem ?? '-'}`,
      `Blockers: ${ledger.blockers.join(' | ') || '-'}`,
      `Next: ${ledger.next.join(' -> ') || '-'}`,
      `EvidenceRefs: ${ledger.evidenceRefs.join(', ') || '-'}`,
      `UpdatedAt: ${ledger.updatedAt}`,
    ].join('\n')
  }

  private commit(
    snapshot: ContextSessionSnapshot,
    session: ContextSession,
    reason: string,
    evidenceRefs: readonly string[] = [],
  ): ContextSessionSnapshot {
    assertContextLint(lintContextSession(session))
    const record = this.runtimeContext.evidenceStateManager.updateState({
      projectId: session.projectId,
      scope: stateScope(session.taskId),
      key: 'session',
      value: session,
      reason,
      evidenceRefs,
      expectedVersion: snapshot.stateVersion,
    })
    return { stateVersion: record.version, session }
  }

  private requireProject(projectId: string) {
    const project = this.runtimeContext.projectManager.getProjectContext(projectId)
    if (!project) throw new Error(`Context Manager 找不到项目: ${projectId}`)
    return project
  }
}

declare module '@deepseek-ai/cordis' {
  interface Context {
    contextManager: ContextManagementService
  }
}

export default ContextManagementService
