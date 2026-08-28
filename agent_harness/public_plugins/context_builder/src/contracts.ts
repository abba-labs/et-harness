export type ContextResourceKind = 'architecture' | 'rule' | 'knowledge' | 'gate' | 'inline'
export type ContextPriority = 'required' | 'high' | 'normal' | 'low'

export interface ContextReference {
  readonly kind: Exclude<ContextResourceKind, 'inline'>
  readonly id: string
  readonly priority?: ContextPriority
}

export interface InlineContextItem {
  readonly id: string
  readonly title: string
  readonly content: string
  readonly priority?: ContextPriority
  readonly provenance: string
}

export interface ContextBuildRequest {
  readonly projectId: string
  readonly taskSummary?: string
  readonly references: readonly ContextReference[]
  readonly inlineItems?: readonly InlineContextItem[]
  readonly maxChars?: number
}

export interface ContextResolvedItem {
  readonly projectId: string
  readonly kind: ContextResourceKind
  readonly id: string
  readonly title: string
  readonly content: string
  readonly priority: ContextPriority
  readonly required: boolean
  readonly provenance: string
  readonly warnings: readonly string[]
}

export interface ContextPack {
  readonly projectId: string
  readonly taskSummary?: string
  readonly items: readonly ContextResolvedItem[]
  readonly omitted: readonly string[]
  readonly warnings: readonly string[]
  readonly maxChars: number
  readonly charCount: number
  readonly overBudget: boolean
  readonly text: string
}

export type ContextLifecyclePhase =
  | 'bootstrap'
  | 'analysis'
  | 'implementation'
  | 'validation'
  | 'handoff'
  | 'complete'

export type ContextSessionStatus = 'ACTIVE' | 'PAUSED' | 'COMPLETED'

export interface ContextLedgerEntry {
  readonly text: string
  readonly refs: readonly string[]
}

export interface ContextTaskLedger {
  readonly goal: string
  readonly phase: ContextLifecyclePhase
  readonly scopeRefs: readonly string[]
  readonly constraintRefs: readonly string[]
  readonly confirmed: readonly ContextLedgerEntry[]
  readonly assumptions: readonly ContextLedgerEntry[]
  readonly openIssues: readonly ContextLedgerEntry[]
  readonly plan: readonly string[]
  readonly updatedAt: string
}

export interface ContextTaskLedgerPatch {
  readonly goal?: string
  readonly phase?: ContextLifecyclePhase
  readonly scopeRefs?: readonly string[]
  readonly constraintRefs?: readonly string[]
  readonly confirmed?: readonly ContextLedgerEntry[]
  readonly assumptions?: readonly ContextLedgerEntry[]
  readonly openIssues?: readonly ContextLedgerEntry[]
  readonly plan?: readonly string[]
}

export interface ContextProgressLedger {
  readonly lastAction?: string
  readonly lastResult?: string
  readonly touchedRefs: readonly string[]
  readonly currentProblem?: string
  readonly blockers: readonly string[]
  readonly next: readonly string[]
  readonly evidenceRefs: readonly string[]
  readonly updatedAt: string
}

export interface ContextProgressLedgerPatch {
  readonly lastAction?: string
  readonly lastResult?: string
  readonly touchedRefs?: readonly string[]
  readonly currentProblem?: string
  readonly blockers?: readonly string[]
  readonly next?: readonly string[]
  readonly evidenceRefs?: readonly string[]
}

export type ContextRecentEventKind = 'ACTION' | 'OBSERVATION' | 'DECISION' | 'ERROR'

export interface ContextRecentEventInput {
  readonly kind: ContextRecentEventKind
  readonly summary: string
  readonly refs?: readonly string[]
  readonly evidenceRefs?: readonly string[]
}

export interface ContextRecentEvent extends ContextRecentEventInput {
  readonly eventId: string
  readonly recordedAt: string
  readonly refs: readonly string[]
  readonly evidenceRefs: readonly string[]
}

export type ContextHandleKind =
  | 'architecture'
  | 'rule'
  | 'knowledge'
  | 'gate'
  | 'file'
  | 'source'
  | 'evidence'
  | 'other'

export interface ContextHandleInput {
  readonly kind: ContextHandleKind
  readonly reference: string
  readonly title?: string
  readonly summary?: string
}

export interface ContextHandle extends ContextHandleInput {
  readonly addedAt: string
}

export interface ContextSession {
  readonly projectId: string
  readonly taskId: string
  readonly status: ContextSessionStatus
  readonly generation: number
  readonly maxChars: number
  readonly recentTailLimit: number
  readonly createdAt: string
  readonly updatedAt: string
  readonly taskLedger: ContextTaskLedger
  readonly progressLedger: ContextProgressLedger
  readonly workingSet: readonly ContextReference[]
  readonly inlineItems: readonly InlineContextItem[]
  readonly handles: readonly ContextHandle[]
  readonly recentTail: readonly ContextRecentEvent[]
}

export interface ContextSessionSnapshot {
  readonly stateVersion: number
  readonly session: ContextSession
}

export interface ContextStartTaskInput {
  readonly projectId: string
  readonly taskId: string
  readonly goal: string
  readonly maxChars?: number
  readonly recentTailLimit?: number
  readonly inlineItems?: readonly InlineContextItem[]
}

export interface ContextRebuildInput {
  readonly projectId: string
  readonly taskId: string
  readonly phase?: ContextLifecyclePhase
  readonly workingSet?: readonly ContextReference[]
  readonly inlineItems?: readonly InlineContextItem[]
  readonly clearRecentTail?: boolean
  readonly evidenceRefs?: readonly string[]
}

export interface ContextCompass {
  readonly projectId: string
  readonly displayName: string
  readonly projectType?: string
  readonly resourceHandles: readonly string[]
  readonly routeMap: readonly string[]
  readonly builtAt: string
}

export interface ContextFrame {
  readonly taskId: string
  readonly generation: number
  readonly stateVersion: number
  readonly builtAt: string
  readonly sessionStatus: ContextSessionStatus
  readonly pack: ContextPack
}

export interface ContextHandoff {
  readonly projectId: string
  readonly taskId: string
  readonly generation: number
  readonly createdAt: string
  readonly taskLedger: ContextTaskLedger
  readonly progressLedger: ContextProgressLedger
  readonly workingSet: readonly ContextReference[]
  readonly inlineItems: readonly InlineContextItem[]
  readonly handles: readonly ContextHandle[]
}
