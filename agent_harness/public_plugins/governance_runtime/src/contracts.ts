import type {
  TurnClosureReceipt,
  TurnJournalRecord,
  TurnReflectionRecord,
} from '@agent-harness/agent-governance-kernel'
import type {
  AutoGovernanceContextEnvelope,
  AutoGovernanceReviewDecisionInput,
  AutoGovernanceReviewDecisionResult,
  AutoGovernanceTaskStatus,
} from '@agent-harness/auto-governance-engine'
import type {
  CompletionDecisionV01,
  ExecutionEventAcceptanceV01,
  ExecutionEventKind,
  ExecutionEventStoreV01,
  HostCapabilityContractV01,
  JsonRecord,
  MutationIntentV01,
  ObligationLedgerStatusV01,
  SupervisionNegotiationV01,
  SupervisionReadinessReceiptV01,
} from '@agent-harness/execution-supervisor'

export const GOVERNANCE_RUNTIME_CONTRACT_VERSION = '0.1' as const

export type GovernanceKnowledgeConsultMode = 'NONE' | 'OPTIONAL' | 'REQUIRED'
export type GovernanceKnowledgeCaptureMode = 'NONE' | 'CHECK' | 'REQUIRED'
export type GovernanceKnowledgeValidationMode = 'NONE' | 'DOCUMENT' | 'EVIDENCE_CHECK' | 'REAL_TEST'

export interface GovernanceKnowledgeDecision {
  readonly stage: 'OPEN' | 'OBSERVE' | 'CLOSE'
  readonly consultMode: GovernanceKnowledgeConsultMode
  readonly captureMode: GovernanceKnowledgeCaptureMode
  readonly validationMode: GovernanceKnowledgeValidationMode
  readonly deterministicSignals: readonly string[]
  readonly semanticSignals: readonly string[]
  readonly reasons: readonly string[]
}

export interface GovernanceKnowledgePromotion {
  readonly knowledgeUri: string
  readonly fromStatus: string
  readonly toStatus: 'VALIDATED' | 'FULL_VALIDATED'
  readonly basisRefs: readonly string[]
}

export interface GovernanceKnowledgeVerificationResult {
  readonly knowledgeUri: string
  readonly relation: 'SUPPORT' | 'CONTRADICT'
  readonly basisRefs: readonly string[]
  readonly decision: 'INSUFFICIENT' | 'READY' | 'BLOCKED'
  readonly resultingStatus: string
}

export interface GovernanceKnowledgeSourceOption {
  readonly sourceRef: string
  readonly kind: string
  readonly title: string
  readonly location: string
  readonly revision?: string
}

export interface GovernanceKnowledgeCategoryOption {
  readonly scope: 'PROJECT' | 'PUBLIC'
  readonly categoryId: string
  readonly categoryRef: string
  readonly title: string
  readonly parentId?: string
  readonly summary?: string
}

export type GovernanceTurnObservationKind =
  | 'TASK_INPUT'
  | 'USER_MESSAGE'
  | 'ASSISTANT_MESSAGE'
  | 'TOOL_RESULT'
  | 'RESOURCE_TOUCH'

/**
 * Bounded, model-visible Turn evidence used by semantic Reflection.
 *
 * This record intentionally contains only user-visible/task/tool-summary facts.
 * It must never contain hidden chain-of-thought or private model reasoning.
 */
export interface GovernanceTurnObservation {
  readonly observationId: string
  readonly observationRef: string
  readonly kind: GovernanceTurnObservationKind
  readonly text: string
  readonly refs: readonly string[]
  readonly sourceName?: string
  readonly isError?: boolean
  readonly truncated: boolean
}

export interface GovernanceSemanticRequest {
  readonly contractVersion: typeof GOVERNANCE_RUNTIME_CONTRACT_VERSION
  readonly runtimeId: string
  readonly actorId: string
  readonly projectId: string
  readonly taskId: string
  readonly turnId: string
  readonly journal: TurnJournalRecord
  readonly context: AutoGovernanceContextEnvelope
  readonly turnObservations: readonly GovernanceTurnObservation[]
  readonly knowledgeValidation: {
    readonly projectSources: readonly GovernanceKnowledgeSourceOption[]
    readonly publicSources: readonly GovernanceKnowledgeSourceOption[]
  }
  readonly knowledgeClassification: {
    readonly projectCategories: readonly GovernanceKnowledgeCategoryOption[]
    readonly publicLibraryMounted: boolean
    readonly publicCategories: readonly GovernanceKnowledgeCategoryOption[]
  }
  readonly requirements: readonly string[]
}

export interface GovernanceSemanticExecutor {
  readonly executorId: string
  reflect(request: GovernanceSemanticRequest): Promise<unknown> | unknown
}

export interface GovernanceOpenTurnInput {
  readonly runtimeId: string
  readonly turnId: string
  readonly taskText: string
  readonly actorId?: string
  readonly taskId?: string
  readonly projectId?: string
  readonly workspacePath?: string
  readonly userMessageRefs?: readonly string[]
  readonly semanticExecutor?: GovernanceSemanticExecutor
  /** Framework-owned durable execution stream. Agents must never receive this capability. */
  readonly supervisionEventStore?: ExecutionEventStoreV01
  /** Trusted Host wiring facts. Agent/model output is never a capability source. */
  readonly hostCapabilities?: HostCapabilityContractV01
}

export interface GovernanceRehydrateSupervisedTurnInput {
  readonly runtimeId: string
  readonly eventStore: ExecutionEventStoreV01
  readonly hostCapabilities?: HostCapabilityContractV01
  readonly semanticExecutor?: GovernanceSemanticExecutor
}

export interface GovernanceBindSupervisedTurnInput {
  readonly runtimeId: string
  readonly eventStore: ExecutionEventStoreV01
  readonly hostCapabilities?: HostCapabilityContractV01
}

export interface GovernanceHostSupervisionProfile {
  readonly capabilities: HostCapabilityContractV01
  readonly negotiation: SupervisionNegotiationV01
  readonly claimsMechanicalInterception: boolean
}

export interface GovernanceSupervisionStatus {
  readonly hostProfile?: GovernanceHostSupervisionProfile
  readonly ledger: ObligationLedgerStatusV01
  readonly decision: CompletionDecisionV01
  readonly readiness?: SupervisionReadinessReceiptV01
}

/**
 * Host-observed execution fact. Runtime supplies every supervision identity and
 * the canonical sequence; adapters cannot forge Project, Agent or Context data.
 */
export interface GovernanceHostExecutionEventInput {
  readonly runtimeId: string
  readonly turnId: string
  readonly eventId: string
  readonly kind: ExecutionEventKind
  readonly payload: JsonRecord
}

export interface GovernanceHostExecutionEventResult {
  readonly eventRef: string
  readonly acceptance: ExecutionEventAcceptanceV01
  readonly supervision: GovernanceSupervisionStatus
}

export interface GovernanceOpenTurnResult {
  readonly contractVersion: typeof GOVERNANCE_RUNTIME_CONTRACT_VERSION
  readonly runtimeId: string
  readonly actorId: string
  readonly projectId: string
  readonly taskId: string
  readonly turnId: string
  readonly context: AutoGovernanceContextEnvelope
  readonly journal: TurnJournalRecord
  readonly taskObservation: GovernanceTurnObservation
  readonly knowledgeDecision: GovernanceKnowledgeDecision
}

export type GovernanceWorkObservation =
  | {
      readonly kind: 'tool-result'
      readonly runtimeId: string
      readonly turnId: string
      readonly name: string
      readonly arguments?: unknown
      readonly isError?: boolean
      readonly eventRef?: string
      readonly resourceRefs?: readonly string[]
      /** Bounded model-visible result summary; never hidden reasoning. */
      readonly summary?: string
    }
  | {
      readonly kind: 'resource-touch'
      readonly runtimeId: string
      readonly turnId: string
      readonly resourceRefs: readonly string[]
      readonly summary?: string
    }
  | {
      readonly kind: 'assistant-message'
      readonly runtimeId: string
      readonly turnId: string
      readonly messageRefs: readonly string[]
      /** Final/user-visible assistant output or other durable visible content. */
      readonly text?: string
    }
  | {
      readonly kind: 'user-message'
      readonly runtimeId: string
      readonly turnId: string
      readonly messageRefs: readonly string[]
      readonly text?: string
    }

export interface GovernanceWorkObservationResult {
  readonly context: AutoGovernanceContextEnvelope
  readonly journal: TurnJournalRecord
  readonly observation: GovernanceTurnObservation
  readonly knowledgeDecision: GovernanceKnowledgeDecision
}

export interface GovernanceActionPreflightInput {
  readonly runtimeId: string
  readonly turnId: string
  readonly name: string
  readonly arguments?: unknown
  readonly eventRef?: string
  readonly effect?: GovernanceActionEffect
}

export type GovernanceActionEffect =
  | { readonly kind: 'READ_ONLY' }
  | { readonly kind: 'MUTATION'; readonly intent: MutationIntentV01 }

/** Runtime-side Gate execution input. It is intentionally absent from the Host Runtime Port. */
export interface GovernanceGateEvidenceProducerPreflightInput {
  readonly runtimeId: string
  readonly turnId: string
  readonly name: string
  readonly arguments?: unknown
  readonly eventRef?: string
  readonly gateId: string
  readonly stepId: string
  readonly capability: string
}

export interface GovernanceActionPreflightResult {
  readonly allowed: boolean
  readonly reason?: string
}

export interface GovernanceCloseTurnInput {
  readonly runtimeId: string
  readonly turnId: string
  readonly assistantMessageRefs?: readonly string[]
  readonly publicCandidateRefs?: readonly string[]
  readonly projectCandidateRefs?: readonly string[]
  readonly semanticExecutor?: GovernanceSemanticExecutor
}

export interface GovernanceCloseTurnResult {
  readonly contractVersion: typeof GOVERNANCE_RUNTIME_CONTRACT_VERSION
  readonly runtimeId: string
  readonly taskId: string
  readonly turnId: string
  readonly reflection: TurnReflectionRecord
  readonly closure: TurnClosureReceipt
  readonly context: AutoGovernanceContextEnvelope
  readonly knowledgeDecision: GovernanceKnowledgeDecision
  readonly knowledgeVerifications: readonly GovernanceKnowledgeVerificationResult[]
  readonly knowledgeVerificationWarnings: readonly string[]
  readonly knowledgePromotions: readonly GovernanceKnowledgePromotion[]
  readonly knowledgePromotionWarnings: readonly string[]
  readonly supervision?: GovernanceSupervisionStatus
}

export interface GovernanceRuntimeStatus {
  /** Last synchronized snapshot; completion admission must call Runtime completeTask(). */
  readonly runtimeId: string
  readonly actorId: string
  readonly projectId: string
  readonly taskId: string
  readonly activeTurnId?: string
  readonly autoGovernance: AutoGovernanceTaskStatus
  readonly unresolvedTurnIds: readonly string[]
  readonly supervision?: GovernanceSupervisionStatus
}

export interface GovernanceRuntimeReviewDecisionInput extends AutoGovernanceReviewDecisionInput {
  readonly runtimeId: string
}

export type GovernanceRuntimeReviewDecisionResult = AutoGovernanceReviewDecisionResult
