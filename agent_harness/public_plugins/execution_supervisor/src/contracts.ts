export const TASK_SUPERVISION_CONTRACT_SCHEMA =
  'agent-harness.task-supervision.v0.1' as const
export const EXECUTION_EVENT_SCHEMA =
  'agent-harness.execution-event.v0.1' as const
export const HOST_CAPABILITY_CONTRACT_SCHEMA =
  'agent-harness.host-capabilities.v0.1' as const
export const PERFORMANCE_BASELINE_REPORT_SCHEMA =
  'agent-harness.execution-supervisor-baseline.v0.1' as const

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

export type JsonRecord = Readonly<Record<string, unknown>>

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
  readonly timestamp: string
}

export interface OutputReceiptV01 {
  readonly outputContractId: string
  readonly resourceId: string
  readonly path?: string
  readonly contentHash: string
  readonly structuralValidationStatus:
    | 'PASS'
    | 'FAIL'
    | 'NOT_EXECUTED'
  readonly ruleValidationRefs: readonly string[]
  readonly evidenceRefs: readonly string[]
}

export interface ExecutionEventAcceptanceV01 {
  readonly eventId: string
  readonly sequence: number
  readonly status: ReceiptAcceptanceStatus
  readonly acceptedAt: string
  readonly reasons: readonly string[]
  readonly stateHash?: string
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
