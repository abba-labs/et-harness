export const TASK_SUPERVISION_CONTRACT_SCHEMA =
  'agent-harness.task-supervision.v0.1' as const
export const EXECUTION_EVENT_SCHEMA =
  'agent-harness.execution-event.v0.1' as const
export const HOST_CAPABILITY_CONTRACT_SCHEMA =
  'agent-harness.host-capabilities.v0.1' as const
export const PERFORMANCE_BASELINE_REPORT_SCHEMA =
  'agent-harness.execution-supervisor-baseline.v0.1' as const
export const OBLIGATION_LEDGER_STATUS_SCHEMA =
  'agent-harness.obligation-ledger-status.v0.1' as const
export const EXECUTION_STORE_FINALIZATION_SCHEMA =
  'agent-harness.execution-store-finalization.v0.1' as const
export const SUPERVISION_READINESS_RECEIPT_SCHEMA =
  'agent-harness.supervision-readiness-receipt.v0.1' as const
export const SUPERVISION_LIFECYCLE_BINDING_SCHEMA =
  'agent-harness.supervision-lifecycle-binding.v0.1' as const

export const MANDATORY_LIFECYCLE_CLOSURE_MODULE_IDS = [
  'context-closure',
  'knowledge-closure',
  'experience-memory-closure',
  'architecture-closure',
  'rules-closure',
  'evidence-state-closure',
  'working-set-closure',
  'obligation-gate-reconcile',
] as const

export const MAX_EXECUTION_EVENT_PAYLOAD_BYTES = 64 * 1024
export const MAX_TASK_SUPERVISION_CONTRACT_BYTES = 512 * 1024
export const MAX_OBLIGATION_COUNT = 4096
export const MAX_EVIDENCE_POLICY_COUNT = 1024
export const MAX_IDENTIFIER_CHARS = 256
export const MAX_REFERENCE_CHARS = 2048

export const SUPERVISION_LEVELS = ['AUDIT', 'ENFORCE'] as const
export type SupervisionLevel = typeof SUPERVISION_LEVELS[number]

export const OBLIGATION_KINDS = [
  'REQUIRED_RESOURCE',
  'SOURCE_DISPOSITION',
  'OUTPUT',
  'WRITE_SCOPE',
  'VALIDATION',
  'CLAIM_EVIDENCE',
  'RULE_COMPLIANCE',
  'KNOWLEDGE_DECISION',
  'CONTEXT_UPDATE',
  'REFLECTION',
  'CLOSURE',
] as const
export type ObligationKind = typeof OBLIGATION_KINDS[number]

export const OBLIGATION_SEVERITIES = ['MUST', 'SHOULD'] as const
export type ObligationSeverity = typeof OBLIGATION_SEVERITIES[number]

export const OBLIGATION_STATES = [
  'PENDING',
  'SATISFIED',
  'BLOCKED',
  'VIOLATED',
  'NOT_APPLICABLE',
  'WAIVED',
] as const
export type ObligationState = typeof OBLIGATION_STATES[number]

export const EXECUTION_EVENT_KINDS = [
  'RESOURCE_SEARCH',
  'RESOURCE_READ',
  'RESOURCE_WRITE',
  'TOOL_CALL',
  'TOOL_RESULT',
  'SOURCE_DISPOSITION',
  'OUTPUT_EMITTED',
  'VALIDATION_RESULT',
  'ASSISTANT_MESSAGE',
  'USER_MESSAGE',
  'TASK_END_REQUEST',
] as const
export type ExecutionEventKind = typeof EXECUTION_EVENT_KINDS[number]

export const EVIDENCE_PROVIDER_KINDS = [
  'VALIDATOR',
  'CI',
  'TOOL_GATEWAY',
  'HARDWARE_ADAPTER',
  'HOST_ADAPTER',
  'OTHER',
] as const
export type EvidenceProviderKind = typeof EVIDENCE_PROVIDER_KINDS[number]

export const EVIDENCE_RESULT_STATUSES = [
  'PASS',
  'FAIL',
  'BLOCKED',
  'NOT_EXECUTED',
  'NOT_VERIFIED',
  'HISTORICAL',
] as const
export type EvidenceResultStatus = typeof EVIDENCE_RESULT_STATUSES[number]

export const COMPLETION_STATUSES = [
  'IN_PROGRESS',
  'READY_TO_CLOSE',
  'BLOCKED',
  'FAILED',
  'COMPLETE',
] as const
export type CompletionStatus = typeof COMPLETION_STATUSES[number]

export const SOURCE_DISPOSITIONS = [
  'FOUND',
  'NO_MATCH',
  'UNAVAILABLE',
] as const
export type SourceDisposition = typeof SOURCE_DISPOSITIONS[number]

export const RECEIPT_ACCEPTANCE_STATUSES = [
  'ACCEPTED',
  'DUPLICATE',
  'REJECTED',
] as const
export type ReceiptAcceptanceStatus =
  typeof RECEIPT_ACCEPTANCE_STATUSES[number]

export const EXECUTION_STORE_ISSUE_CODES = [
  'EVENT_INVALID',
  'EVENT_ID_INTEGRITY_CONFLICT',
  'SEQUENCE_GAP',
  'EVENT_BINDING_MISMATCH',
  'STORE_BINDING_MISMATCH',
  'STORE_ALREADY_EXISTS',
  'STORE_NOT_FOUND',
  'STORE_INVALID_LOCATION',
  'STORE_LIMIT_EXCEEDED',
  'STORE_TRUNCATED_RECORD',
  'STORE_INVALID_CANONICAL_JSON',
  'STORE_STATE_HASH_MISMATCH',
  'STORE_CURSOR_INVALID',
  'STORE_EVENT_CHAIN_MISMATCH',
  'STORE_CHANGED',
  'STORE_CLOSED',
  'STORE_FINALIZED',
  'STORE_FINALIZATION_CONFLICT',
  'STORE_WRITE_FAILED',
] as const
export type ExecutionStoreIssueCode =
  typeof EXECUTION_STORE_ISSUE_CODES[number]

export type JsonRecord = Readonly<Record<string, unknown>>

export const AGENT_CLAIM_KINDS = [
  'OUTPUT',
  'VALIDATION',
  'RULE_COMPLIANCE',
] as const
export type AgentClaimKind = typeof AGENT_CLAIM_KINDS[number]

export interface AgentClaimV01 {
  readonly id: string
  readonly kind: AgentClaimKind
  readonly targetIdentity: string
  readonly resultStatus: EvidenceResultStatus
  readonly validationId?: string
  readonly outputContractId?: string
  readonly evidenceRefs: readonly string[]
}

export interface ObligationDefinitionV01 {
  readonly id: string
  readonly kind: ObligationKind
  readonly severity: ObligationSeverity
  readonly sourceRefs: readonly string[]
  readonly target: JsonRecord
  readonly satisfaction: JsonRecord
  readonly dependencies?: readonly string[]
}

export interface EvidencePolicyV01 {
  readonly id: string
  readonly obligationIds: readonly string[]
  readonly acceptedProviderIds: readonly string[]
  readonly acceptedProviderKinds: readonly EvidenceProviderKind[]
  readonly acceptedResultStatuses: readonly EvidenceResultStatus[]
  readonly requireExactContextHash: boolean
  readonly requireExactProjectRevision: boolean
  readonly requireExactTargetIdentity: boolean
  readonly maxAgeSeconds?: number
}

export interface CompletionPolicyV01 {
  readonly requireAllMustSatisfied: boolean
  readonly requireNoViolations: boolean
  readonly requireReflection: boolean
  readonly requireKnowledgeDecision: boolean
  readonly requireContextUpdate: boolean
  readonly requireClosureReceipt: boolean
  readonly allowShouldWarnings: boolean
  readonly requiredClosureModuleIds: readonly string[]
}

export interface TaskSupervisionContractV01 {
  readonly schema: typeof TASK_SUPERVISION_CONTRACT_SCHEMA
  readonly projectId: string
  readonly taskId: string
  readonly agentId: string
  readonly contextHash: string
  readonly routeHash: string
  readonly projectRevision?: string
  readonly supervisionLevel: SupervisionLevel
  readonly obligations: readonly ObligationDefinitionV01[]
  readonly evidencePolicies: readonly EvidencePolicyV01[]
  readonly completionPolicy: CompletionPolicyV01
}

export interface ObligationWaiverV01 {
  readonly authorizedBy: string
  readonly reason: string
  readonly receiptRef: string
  readonly timestamp: string
}

export interface ObligationStateRecordV01 {
  readonly obligationId: string
  readonly state: ObligationState
  readonly updatedAt: string
  readonly eventRefs: readonly string[]
  readonly evidenceRefs: readonly string[]
  readonly blockerRefs: readonly string[]
  readonly violationRefs: readonly string[]
  readonly reason?: string
  readonly waiver?: ObligationWaiverV01
}

export interface ExecutionEventEnvelopeV01<
  TPayload extends JsonRecord = JsonRecord,
> {
  readonly schema: typeof EXECUTION_EVENT_SCHEMA
  readonly requestId: string
  readonly runtimeId: string
  readonly projectId: string
  readonly taskId: string
  readonly turnId: string
  readonly agentId: string
  readonly contextHash: string
  readonly sequence: number
  readonly eventId: string
  readonly timestamp: string
  readonly kind: ExecutionEventKind
  readonly payloadHash: string
  readonly payload: TPayload
}

export interface ResourceReceiptV01 {
  readonly provider: string
  readonly resourceId: string
  readonly path?: string
  readonly revision?: string
  readonly modifiedAt?: string
  readonly contentHash?: string
  readonly disposition: SourceDisposition
  readonly purpose: string
  readonly claimRefs: readonly string[]
  readonly error?: string
}

export interface SourceDispositionTargetV01 {
  readonly resourceId: string
}

export interface SourceDispositionSatisfactionV01 {
  readonly acceptedProviderIds: readonly string[]
  readonly acceptedDispositions: readonly ('NO_MATCH' | 'UNAVAILABLE')[]
}

export interface RequiredResourceTargetV01 {
  readonly resourceId: string
  readonly revision?: string
  readonly contentHash?: string
}

export interface RequiredResourceSatisfactionV01 {
  readonly acceptedProviderIds: readonly string[]
  readonly acceptedDispositions: readonly SourceDisposition[]
  readonly requireContentHash?: boolean
}

export type ResourceReadEventPayloadV01 = JsonRecord & {
  readonly receipt: ResourceReceiptV01
}

export interface MutationReceiptV01 {
  readonly resourceId: string
  readonly path?: string
  readonly beforeHash?: string
  readonly afterHash?: string
  readonly action: 'CREATE' | 'UPDATE' | 'DELETE' | 'MOVE' | 'COPY'
  readonly scopeDecision:
    | 'ALLOWED'
    | 'PROTECTED'
    | 'OUTSIDE_SCOPE'
    | 'UNKNOWN'
  readonly executorId: string
}

export interface WriteScopeTargetV01 {
  readonly allowedResourceIds: readonly string[]
  readonly allowedPathPrefixes?: readonly string[]
}

export interface WriteScopeSatisfactionV01 {
  readonly requireInScope: true
}

export type ResourceWriteEventPayloadV01 = JsonRecord & {
  readonly receipt: MutationReceiptV01
}

export interface ValidationReceiptV01 {
  readonly providerId: string
  readonly providerKind: EvidenceProviderKind
  readonly validationId: string
  readonly commandOrTestIdentity: string
  readonly projectRevision?: string
  readonly contextHash: string
  readonly targetIdentity: string
  readonly resultStatus: EvidenceResultStatus
  readonly artifactRefs: readonly string[]
  readonly evidenceRefs: readonly string[]
  readonly claimRefs: readonly string[]
  readonly timestamp: string
}

export interface ValidationTargetV01 {
  readonly validationId: string
  readonly targetIdentity: string
}

export interface ValidationSatisfactionV01 {
  readonly requiredResultStatus: 'PASS'
}

export type ValidationResultEventPayloadV01 = JsonRecord & {
  readonly receipt: ValidationReceiptV01
}

export interface OutputReceiptV01 {
  readonly providerId: string
  readonly providerKind: EvidenceProviderKind
  readonly outputContractId: string
  readonly resourceId: string
  readonly path?: string
  readonly contentHash: string
  readonly projectRevision?: string
  readonly contextHash: string
  readonly targetIdentity: string
  readonly structuralValidationStatus:
    | 'PASS'
    | 'FAIL'
    | 'NOT_EXECUTED'
  readonly ruleValidationRefs: readonly string[]
  readonly evidenceRefs: readonly string[]
  readonly claimRefs: readonly string[]
  readonly timestamp: string
}

export interface OutputTargetV01 {
  readonly outputContractId: string
  readonly resourceId: string
  readonly contentHash: string
}

export interface OutputSatisfactionV01 {
  readonly requiredStructuralStatus: 'PASS'
  readonly requiredResultStatus: 'PASS'
}

export type OutputEmittedEventPayloadV01 = JsonRecord & {
  readonly receipt: OutputReceiptV01
}

export interface ClaimEvidenceTargetV01 {
  readonly claimKinds: readonly AgentClaimKind[]
  readonly targetIdentities?: readonly string[]
}

export interface ClaimEvidenceSatisfactionV01 {
  readonly requireEvidenceForPassClaims: true
}

export interface ExecutionEventAcceptanceV01 {
  readonly eventId: string
  readonly sequence: number
  readonly status: ReceiptAcceptanceStatus
  readonly acceptedAt: string
  readonly reasons: readonly string[]
  readonly issues?: readonly ExecutionStoreIssueV01[]
  readonly stateHash?: string
}

export interface ExecutionStoreIssueV01 {
  readonly code: ExecutionStoreIssueCode
  readonly message: string
  readonly field?: string
  readonly expected?: string | number
  readonly actual?: string | number
  readonly sequence?: number
  readonly offset?: number
  readonly sourceCode?: string
}

export interface ExecutionEventStoreBindingV01 {
  readonly requestId: string
  readonly runtimeId: string
  readonly turnId: string
  readonly contract: TaskSupervisionContractV01
}

export interface ExecutionEventStoreLimitsV01 {
  readonly maxEvents: number
  readonly maxStoreBytes: number
  readonly maxReplayEvents: number
}

export interface ExecutionReplayCursorV01 {
  readonly sequence: number
  readonly stateHash: string
}

export interface ExecutionStoreFinalizationV01 {
  readonly schema: typeof EXECUTION_STORE_FINALIZATION_SCHEMA
  readonly cursor: ExecutionReplayCursorV01
  readonly finalizationRef: string
  readonly finalizationHash: string
  readonly finalizedAt: string
  readonly payload: JsonRecord
}

export interface ExecutionReplayPageV01 {
  readonly events: readonly ExecutionEventEnvelopeV01[]
  readonly cursor: ExecutionReplayCursorV01
  readonly hasMore: boolean
}

export interface ExecutionReplayRequestV01 {
  readonly after?: ExecutionReplayCursorV01
  readonly limit: number
}

export interface ExecutionEventStoreV01 {
  readonly binding: ExecutionEventStoreBindingV01
  readonly limits: ExecutionEventStoreLimitsV01
  readonly cursor: ExecutionReplayCursorV01
  readonly eventCount: number
  readonly finalization: ExecutionStoreFinalizationV01 | undefined
  append(event: ExecutionEventEnvelopeV01): Promise<ExecutionEventAcceptanceV01>
  replay(request: ExecutionReplayRequestV01): Promise<ExecutionReplayPageV01>
  finalize(finalization: ExecutionStoreFinalizationV01): Promise<ExecutionStoreFinalizationV01>
  close(): Promise<void>
}

export interface CreateFileExecutionEventStoreInputV01 {
  readonly directory: string
  readonly binding: ExecutionEventStoreBindingV01
  readonly limits: ExecutionEventStoreLimitsV01
}

export interface OpenFileExecutionEventStoreInputV01 {
  readonly directory: string
  readonly binding: ExecutionEventStoreBindingV01
}

export const OBLIGATION_VIOLATION_CODES = [
  'OUT_OF_SCOPE_WRITE',
  'UNSUPPORTED_PASS_CLAIM',
  'TRUSTED_VALIDATION_FAILED',
] as const
export type ObligationViolationCode =
  typeof OBLIGATION_VIOLATION_CODES[number]

export interface ObligationViolationRecordV01 {
  readonly id: string
  readonly code: ObligationViolationCode
  readonly obligationId: string
  readonly severity: ObligationSeverity
  readonly eventId: string
  readonly sequence: number
  readonly observedAt: string
  readonly resourceId?: string
  readonly path?: string
  readonly action?: MutationReceiptV01['action']
  readonly executorId?: string
  readonly claimId?: string
  readonly targetIdentity?: string
  readonly providerId?: string
  readonly evidenceRef?: string
}

export interface ObligationLedgerStatusV01 {
  readonly schema: typeof OBLIGATION_LEDGER_STATUS_SCHEMA
  readonly binding: ExecutionEventStoreBindingV01
  readonly contractHash: string
  readonly cursor: ExecutionReplayCursorV01
  readonly obligations: readonly ObligationStateRecordV01[]
  readonly violations: readonly ObligationViolationRecordV01[]
  readonly pendingObligationIds: readonly string[]
  readonly blockedObligationIds: readonly string[]
  readonly satisfiedObligationIds: readonly string[]
  readonly violatedObligationIds: readonly string[]
}

export interface SupervisionReadinessReceiptV01 {
  readonly schema: typeof SUPERVISION_READINESS_RECEIPT_SCHEMA
  readonly requestId: string
  readonly runtimeId: string
  readonly projectId: string
  readonly taskId: string
  readonly turnId: string
  readonly agentId: string
  readonly contextHash: string
  readonly contractHash: string
  readonly cursor: ExecutionReplayCursorV01
  readonly ledgerStatusHash: string
  readonly decisionHash: string
  readonly taskEndEventId: string
  readonly taskEndTimestamp: string
  readonly receiptHash: string
  readonly receiptRef: string
}

export interface SupervisionReflectionBindingV01 {
  readonly reflectionRef: string
  readonly inputFingerprint: string
  readonly domainDecisions: Readonly<{
    knowledge: 'NONE' | 'PROJECT' | 'PUBLIC' | 'BOTH'
    experience: 'NONE' | 'PROJECT' | 'PUBLIC' | 'BOTH'
    architecture: 'NONE' | 'PROJECT' | 'PUBLIC' | 'BOTH'
    rules: 'NONE' | 'PROJECT' | 'PUBLIC' | 'BOTH'
    evidence: 'NONE' | 'PROJECT' | 'PUBLIC' | 'BOTH'
  }>
}

export interface SupervisionClosureModuleBindingV01 {
  readonly moduleId: string
  readonly moduleVersion: string
  readonly status: 'APPLIED' | 'NO_CHANGE'
  readonly idempotencyKey: string
}

export interface SupervisionLifecycleBindingV01 {
  readonly schema: typeof SUPERVISION_LIFECYCLE_BINDING_SCHEMA
  readonly readinessRef: string
  readonly readinessHash: string
  readonly projectId: string
  readonly taskId: string
  readonly turnId: string
  readonly agentId: string
  readonly contextHash: string
  readonly journalRef: string
  readonly reflection: SupervisionReflectionBindingV01
  readonly kernelClosureRef: string
  readonly kernelClosureInputFingerprint: string
  readonly kernelClosureCreatedAt: string
  readonly moduleReceipts: readonly SupervisionClosureModuleBindingV01[]
}

export interface ExecutionObligationLedgerV01 {
  readonly binding: ExecutionEventStoreBindingV01
  readonly cursor: ExecutionReplayCursorV01
  ingest(
    event: ExecutionEventEnvelopeV01,
  ): Promise<ExecutionEventAcceptanceV01>
  synchronize(): Promise<void>
  getStatus(): ObligationLedgerStatusV01
  getCompletionDecision(): CompletionDecisionV01
  getReadinessReceipt(): SupervisionReadinessReceiptV01 | undefined
  attachLifecycleClosure(
    binding: SupervisionLifecycleBindingV01,
  ): Promise<CompletionDecisionV01>
}

export interface CreateExecutionObligationLedgerInputV01 {
  readonly eventStore: ExecutionEventStoreV01
  readonly lifecycleAuthority?: ExecutionLifecycleAuthorityV01
}

export interface ExecutionLifecycleAuthorityV01 {
  verifyLifecycleClosure(
    binding: SupervisionLifecycleBindingV01,
  ): Promise<void> | void
}

export interface CompletionDecisionV01 {
  readonly status: CompletionStatus
  readonly pendingObligationIds: readonly string[]
  readonly violatedObligationIds: readonly string[]
  readonly blockerRefs: readonly string[]
  readonly evidenceRefs: readonly string[]
  readonly closureRef?: string
}

export interface HostCapabilityFlagsV01 {
  readonly supportsPreflight: boolean
  readonly supportsToolInterception: boolean
  readonly supportsStableToolEventId: boolean
  readonly supportsResourceHash: boolean
  readonly supportsMessageRef: boolean
  readonly supportsCrossProcessResume: boolean
}

export interface HostCapabilityContractV01 {
  readonly schema: typeof HOST_CAPABILITY_CONTRACT_SCHEMA
  readonly hostId: string
  readonly adapterId: string
  readonly capabilities: HostCapabilityFlagsV01
}

export interface SupervisionNegotiationV01 {
  readonly requestedLevel: SupervisionLevel
  readonly effectiveLevel: SupervisionLevel
  readonly reasons: readonly string[]
}

export interface PerformanceBaselineSampleV01 {
  readonly scenario: string
  readonly warmupIterations: number
  readonly sampleIterations: number
  readonly inputBytes: number
  readonly p50Micros: number
  readonly p95Micros: number
  readonly p99Micros: number
  readonly meanMicros: number
  readonly maxMicros: number
}

export interface PerformanceBaselineReportV01 {
  readonly schema: typeof PERFORMANCE_BASELINE_REPORT_SCHEMA
  readonly baselineId: string
  readonly capturedAt: string
  readonly sourceRevision: string
  readonly environment: {
    readonly nodeVersion: string
    readonly platform: string
    readonly architecture: string
  }
  readonly thresholdsFrozen: false
  readonly invariants: {
    readonly noSemanticCallOnHotPath: true
    readonly noFullRerouteForOrdinaryRead: true
    readonly maxUnifiedReflectionsPerTurn: 1
    readonly maxEventPayloadBytes: typeof MAX_EXECUTION_EVENT_PAYLOAD_BYTES
    readonly maxTaskContractBytes:
      typeof MAX_TASK_SUPERVISION_CONTRACT_BYTES
  }
  readonly samples: readonly PerformanceBaselineSampleV01[]
  readonly notes: readonly string[]
}

export interface ContractValidationIssue {
  readonly path: string
  readonly code: string
  readonly message: string
}

export type ContractValidationResult<T> =
  | {
      readonly valid: true
      readonly issues: readonly []
      readonly value: T
    }
  | {
      readonly valid: false
      readonly issues: readonly ContractValidationIssue[]
    }
