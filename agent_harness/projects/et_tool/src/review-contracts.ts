export const ET_TOOL_REVIEW_CAPABILITIES = [
  'change.analyze',
  'code.review',
  'architecture.review',
  'rule.review',
  'lifecycle.review',
  'contract.review',
  'validation.plan',
] as const

export type EtToolReviewCapability = (typeof ET_TOOL_REVIEW_CAPABILITIES)[number]

export interface EtToolReviewChangeInput {
  readonly files: readonly string[]
  readonly patch: string
}

export interface EtToolReviewRequest {
  readonly projectId: 'et-tool'
  readonly taskId: string
  readonly gateId: string
  readonly capability: EtToolReviewCapability
  readonly taskIntent: string
  readonly reviewEpoch?: number
  readonly focus?: string
  readonly change?: EtToolReviewChangeInput
}

export interface EtToolChangeSet {
  readonly source: 'git-working-tree' | 'provided'
  readonly files: readonly string[]
  readonly patch: string
  readonly truncated: boolean
  readonly fingerprint: string
}

export interface EtToolChangeScopeHints {
  readonly chips: readonly string[]
  readonly routes: readonly string[]
  readonly layers: readonly string[]
  readonly sharedLayerChange: boolean
  readonly unknownPaths: readonly string[]
}

export interface EtToolReviewCandidate {
  readonly id: string
  readonly title: string
  readonly location: string
  readonly summary?: string
  readonly relevance?: number
}

export interface EtToolValidationPlanHint {
  readonly kind: string
  readonly scope: string
  readonly reason: string
}

export interface EtToolReviewPacket {
  readonly packetId: string
  readonly projectId: 'et-tool'
  readonly taskId: string
  readonly gateId: string
  readonly capability: EtToolReviewCapability
  readonly focus: string
  readonly taskIntent: string
  readonly reviewEpoch?: number
  readonly change: EtToolChangeSet
  readonly scopeHints: EtToolChangeScopeHints
  readonly architectureCandidates: readonly EtToolReviewCandidate[]
  readonly ruleCandidates: readonly EtToolReviewCandidate[]
  readonly knowledgeCandidates: readonly EtToolReviewCandidate[]
  readonly gateRefs: readonly string[]
  readonly reviewGuidance: readonly string[]
  readonly validationPlanHints: readonly EtToolValidationPlanHint[]
  readonly decisionPolicy: string
}

export type EtToolReviewFindingSeverity = 'INFO' | 'WARN' | 'BLOCK'

export interface EtToolReviewFinding {
  readonly severity: EtToolReviewFindingSeverity
  readonly summary: string
  readonly location?: string
  readonly refs?: readonly string[]
}

export interface EtToolReviewDecisionInput {
  readonly packetId: string
  readonly result: 'PASS' | 'BLOCK'
  readonly summary: string
  readonly reviewer: 'agent' | 'human'
  readonly reviewerId: string
  readonly findings?: readonly EtToolReviewFinding[]
}

export interface EtToolReviewDecisionResult {
  readonly packetId: string
  readonly gateId: string
  readonly taskId: string
  readonly result: 'PASS' | 'BLOCK'
  readonly evidenceId: string
}
