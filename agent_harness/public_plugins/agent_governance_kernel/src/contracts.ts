export const AGENT_GOVERNANCE_KERNEL_CONTRACT_VERSION = '0.1' as const
export const TURN_REFLECTION_CONTRACT_VERSION = '0.1' as const
export const TURN_CLOSURE_CONTRACT_VERSION = '0.1' as const

export const MANDATORY_CLOSURE_MODULE_IDS = [
  'context-closure',
  'knowledge-closure',
  'experience-memory-closure',
  'architecture-closure',
  'rules-closure',
  'evidence-state-closure',
  'working-set-closure',
  'obligation-gate-reconcile',
] as const

export type MandatoryClosureModuleId = typeof MANDATORY_CLOSURE_MODULE_IDS[number]

export type AgentLifecycleState = 'INACTIVE' | 'ACTIVE' | 'ENDED'
export type TaskLifecycleStatus = 'ACTIVE' | 'PAUSED' | 'COMPLETED'
export type TurnJournalStatus = 'OPEN' | 'SEALED' | 'CLOSURE_PENDING' | 'CLOSED'

export type ProjectBinding =
  | { readonly kind: 'UNBOUND' }
  | { readonly kind: 'BOUND'; readonly projectId: string }

export type ReflectionScopeDecision = 'NONE' | 'PROJECT' | 'PUBLIC' | 'BOTH'
export type ReflectionCandidateScope = Exclude<ReflectionScopeDecision, 'NONE'>
export type ReflectionDomain = 'knowledge' | 'experience' | 'architecture' | 'rules' | 'evidence'

export interface ReflectionCandidate {
  readonly domain: ReflectionDomain
  readonly title: string
  readonly factOrProposal: string
  readonly scopeDecision: ReflectionCandidateScope
  readonly rationale: string
  readonly provenanceRefs: readonly string[]
  readonly evidenceRefs: readonly string[]
  readonly relatedRefs: readonly string[]
  readonly confidence: number
}

export type KnowledgeVerificationReflectionRelation = 'SUPPORT' | 'CONTRADICT'

export interface KnowledgeVerificationReflection {
  readonly knowledgeRef: string
  readonly relation: KnowledgeVerificationReflectionRelation
  readonly basisRefs: readonly string[]
  readonly rationale: string
}

export interface ScopedReflectionSection {
  readonly scopeDecision: ReflectionScopeDecision
  readonly rationale: string
  readonly candidates: readonly ReflectionCandidate[]
}

export interface TurnContextReflection {
  readonly progress: string
  readonly decisions: readonly string[]
  readonly confirmed: readonly string[]
  readonly assumptions: readonly string[]
  readonly openIssues: readonly string[]
  readonly next: readonly string[]
  readonly touchedRefs: readonly string[]
}

export interface WorkingSetReflection {
  readonly keep: readonly string[]
  readonly add: readonly string[]
  readonly remove: readonly string[]
}

export interface ObligationReflection {
  readonly opened: readonly string[]
  readonly resolved: readonly string[]
  readonly unchanged: readonly string[]
}

export interface TurnReflectionResult {
  readonly contractVersion: typeof TURN_REFLECTION_CONTRACT_VERSION
  readonly taskId: string
  readonly turnId: string
  readonly context: TurnContextReflection
  readonly knowledge: ScopedReflectionSection
  readonly knowledgeVerifications?: readonly KnowledgeVerificationReflection[]
  readonly experience: ScopedReflectionSection
  readonly architecture: ScopedReflectionSection
  readonly rules: ScopedReflectionSection
  readonly evidence: ScopedReflectionSection
  readonly workingSet: WorkingSetReflection
  readonly obligations: ObligationReflection
}

export interface ContentAddressedReadinessBinding {
  readonly ref: string
  readonly fingerprint: string
}

export interface TurnReflectionRequest {
  readonly taskContextRef?: string
  readonly publicCandidateRefs?: readonly string[]
  readonly projectCandidateRefs?: readonly string[]
  readonly readinessBinding?: ContentAddressedReadinessBinding
}

export interface TurnReflectionProviderInput {
  readonly journal: TurnJournalRecord
  readonly taskContextRef?: string
  readonly publicCandidateRefs: readonly string[]
  readonly projectCandidateRefs: readonly string[]
  readonly readinessBinding?: ContentAddressedReadinessBinding
}

export interface TurnReflectionProvider {
  readonly providerId: string
  readonly priority?: number
  reflect(input: TurnReflectionProviderInput): Promise<unknown> | unknown
}

export interface TurnReflectionRecord {
  readonly contractVersion: typeof TURN_REFLECTION_CONTRACT_VERSION
  readonly taskId: string
  readonly turnId: string
  readonly providerId: string
  readonly createdAt: string
  readonly journalRef: string
  readonly inputFingerprint: string
  readonly readinessBinding?: ContentAddressedReadinessBinding
  readonly result: TurnReflectionResult
}

export type ClosureModuleDomain =
  | 'context'
  | ReflectionDomain
  | 'working-set'
  | 'obligations'

export type ClosureModuleStatus = 'APPLIED' | 'NO_CHANGE' | 'BLOCKED' | 'FAILED'
export type TurnClosureStatus = 'COMPLETE' | 'PENDING'

export interface ClosureModuleInput {
  readonly taskId: string
  readonly turnId: string
  readonly projectBinding: ProjectBinding
  readonly journalRef: string
  readonly reflection: TurnReflectionResult
  readonly idempotencyKey: string
  readonly readinessBinding?: ContentAddressedReadinessBinding
}

export interface ClosureModuleReceipt {
  readonly moduleId: string
  readonly moduleVersion: string
  readonly taskId: string
  readonly turnId: string
  readonly idempotencyKey: string
  readonly status: ClosureModuleStatus
  readonly writes: readonly string[]
  readonly candidateRefs: readonly string[]
  readonly evidenceRefs: readonly string[]
  readonly stateVersionAfter?: number
  readonly reason?: string
}

export interface ClosureModule {
  readonly id: string
  readonly version: string
  readonly mandatory: boolean
  readonly domains: readonly ClosureModuleDomain[]
  apply(input: ClosureModuleInput): Promise<ClosureModuleReceipt> | ClosureModuleReceipt
}

export interface TurnClosureReceipt {
  readonly contractVersion: typeof TURN_CLOSURE_CONTRACT_VERSION
  readonly taskId: string
  readonly turnId: string
  readonly attemptId: string
  readonly createdAt: string
  readonly journalRef: string
  readonly reflectionRef: string
  readonly inputFingerprint: string
  readonly readinessBinding?: ContentAddressedReadinessBinding
  readonly status: TurnClosureStatus
  readonly moduleReceipts: readonly ClosureModuleReceipt[]
  readonly missingMandatoryModuleIds: readonly MandatoryClosureModuleId[]
  readonly blockingReasons: readonly string[]
}

export interface TurnJournalRecord {
  readonly contractVersion: typeof AGENT_GOVERNANCE_KERNEL_CONTRACT_VERSION
  readonly taskId: string
  readonly turnId: string
  readonly agentId: string
  readonly projectBinding: ProjectBinding
  readonly startedAt: string
  readonly closingAt?: string
  readonly closedAt?: string
  readonly userMessageRefs: readonly string[]
  readonly assistantMessageRefs: readonly string[]
  readonly toolEventRefs: readonly string[]
  readonly resourceTouchRefs: readonly string[]
  readonly stateVersionBefore?: number
  readonly sessionRef?: string
  readonly status: TurnJournalStatus
  readonly revision: number
  readonly closureAttemptCount: number
  readonly lastClosureAttemptId?: string
  readonly lastClosureError?: string
  readonly reflectionRef?: string
  readonly reflectionInputFingerprint?: string
  readonly closureReceiptRef?: string
}

export interface BeginTurnInput {
  readonly taskId: string
  readonly turnId: string
  readonly agentId: string
  readonly projectBinding?: ProjectBinding
  readonly startedAt?: string
  readonly stateVersionBefore?: number
  readonly sessionRef?: string
  readonly userMessageRefs?: readonly string[]
}

export interface AppendTurnRefsInput {
  readonly userMessageRefs?: readonly string[]
  readonly assistantMessageRefs?: readonly string[]
  readonly toolEventRefs?: readonly string[]
  readonly resourceTouchRefs?: readonly string[]
  readonly sessionRef?: string
}

export interface AttachReflectionInput {
  readonly reflectionRef: string
  readonly inputFingerprint: string
}

export interface MarkClosurePendingInput {
  readonly attemptId: string
  readonly reason: string
}

export interface CloseTurnInput {
  readonly closureReceiptRef: string
  readonly closedAt?: string
}

export interface TurnStartGuardResult {
  readonly allowed: boolean
  readonly blockingTurnIds: readonly string[]
  readonly reason?: string
}

export interface ClosureReplayRequirement {
  readonly required: boolean
  readonly turnIds: readonly string[]
  readonly statuses: readonly TurnJournalStatus[]
}
