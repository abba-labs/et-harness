import type {
  ProjectCandidateResult,
  ProjectQueryScope,
  ProjectResourceIndexEntryV01,
} from '@agent-harness/project-contract'

export type KnowledgeStatus = 'CANDIDATE' | 'VALIDATED' | 'FULL_VALIDATED' | 'DEPRECATED'
export type KnowledgeCategoryStatus = 'ACTIVE' | 'DEPRECATED'
export type KnowledgeLibraryMode = 'legacy-v0.1' | 'library-v0.2'

export type KnowledgeLibraryScope =
  | { readonly kind: 'global' }
  | { readonly kind: 'project'; readonly projectId: string }

export interface KnowledgeSearchInput {
  readonly query: string
  readonly scope?: ProjectQueryScope
  readonly filters?: Readonly<Record<string, unknown>>
  readonly limit?: number
}

export interface KnowledgeCombinedSearchRequest extends KnowledgeSearchInput {
  readonly projectId: string
  readonly globalLimit?: number
  readonly projectLimit?: number
}

export interface KnowledgeScopedCandidate {
  readonly libraryScope: KnowledgeLibraryScope
  readonly knowledgeUri: string
  readonly candidate: ProjectCandidateResult
}

export interface KnowledgeNode {
  readonly id: string
  readonly fileId: string
  readonly title: string
  readonly depth: number
  readonly parentId?: string
  readonly children: readonly string[]
  readonly location: string
  readonly directContent: string
  readonly isLeaf: boolean
  readonly status?: KnowledgeStatus
  readonly category?: string
  readonly fact?: string
  readonly scope?: string
  readonly provenance?: string
  readonly tags: readonly string[]
  readonly refs: readonly string[]
  readonly sources: readonly string[]
}

export interface KnowledgeCategory {
  readonly id: string
  readonly title: string
  readonly parentId?: string
  readonly children: readonly string[]
  readonly aliases: readonly string[]
  readonly summary?: string
  readonly status: KnowledgeCategoryStatus
}

export interface KnowledgeTaxonomy {
  readonly standard: 'knowledge-library-v0.2'
  readonly roots: readonly string[]
  readonly categories: Readonly<Record<string, KnowledgeCategory>>
}

export interface KnowledgeRouteFile extends ProjectResourceIndexEntryV01 {
  readonly nodes: readonly string[]
}

export interface KnowledgeLibraryStats {
  readonly categoryCount: number
  readonly knowledgeCount: number
  readonly statusCounts: Readonly<Record<KnowledgeStatus, number>>
  readonly categoryCounts: Readonly<Record<string, number>>
}

export interface KnowledgeProjectIndex {
  readonly projectId: string
  readonly state: 'ready'
  readonly libraryMode: KnowledgeLibraryMode
  readonly resourcePath: string
  readonly files: readonly KnowledgeRouteFile[]
  readonly nodeCount: number
  readonly knowledgeCount: number
  readonly statusCounts: Readonly<Record<KnowledgeStatus, number>>
  readonly taxonomy?: KnowledgeTaxonomy
  readonly categoryCounts?: Readonly<Record<string, number>>
  readonly sourceFingerprint?: string
  readonly warnings: readonly string[]
  readonly builtAt: string
}

export interface KnowledgeNodeResult {
  readonly projectId: string
  readonly node: KnowledgeNode
}

export interface KnowledgeResolvedReference {
  readonly libraryScope: KnowledgeLibraryScope
  readonly knowledgeUri: string
  readonly result: KnowledgeNodeResult
}

export interface KnowledgeRelatedResult {
  readonly projectId: string
  readonly sourceId: string
  readonly outgoing: readonly string[]
  readonly incoming: readonly string[]
}

export interface KnowledgeLibraryValidationResult {
  readonly valid: boolean
  readonly errors: readonly string[]
  readonly warnings: readonly string[]
  readonly sourceFingerprint?: string
}

export interface KnowledgeCandidateInput {
  readonly categoryId: string
  readonly title: string
  readonly fact: string
  readonly provenance: string
  readonly scope?: string
  readonly tags?: readonly string[]
  readonly refs?: readonly string[]
}

export interface KnowledgeCandidateUpdate {
  readonly title?: string
  readonly fact?: string
  readonly provenance?: string
  readonly scope?: string
  readonly tags?: readonly string[]
  readonly refs?: readonly string[]
}

export interface KnowledgeMutationResult {
  readonly knowledgeId: string
  readonly file: string
  readonly status: KnowledgeStatus
  readonly categoryId: string
  readonly sourceFingerprint?: string
}

export interface KnowledgeCategoryCreateInput {
  readonly parentId?: string
  readonly title: string
  readonly aliases?: readonly string[]
  readonly summary?: string
}

export interface KnowledgeCategoryUpdateInput {
  readonly title?: string
  readonly aliases?: readonly string[]
  readonly summary?: string
}

export interface KnowledgeCategoryMutationResult {
  readonly categoryId: string
  readonly status: KnowledgeCategoryStatus
  readonly sourceFingerprint?: string
}

export type KnowledgeSourceKind = 'DOCUMENT' | 'SPEC' | 'SVD' | 'CODE' | 'RTL' | 'WEB' | 'OTHER'
export type KnowledgeSourceStatus = 'ACTIVE' | 'DEPRECATED'

export interface KnowledgeSourceInput {
  readonly kind: KnowledgeSourceKind
  readonly title: string
  readonly location: string
  readonly revision?: string
  readonly contentHash?: string
  readonly note?: string
}

export interface KnowledgeSourceRecord extends KnowledgeSourceInput {
  readonly sourceId: string
  readonly status: KnowledgeSourceStatus
  readonly registeredAt: string
}

export interface KnowledgeResolvedSource {
  readonly libraryScope: KnowledgeLibraryScope
  readonly sourceUri: string
  readonly source: KnowledgeSourceRecord
}

export type KnowledgeVerificationRelation = 'SUPPORT' | 'CONTRADICT'
export type KnowledgeVerificationBasisKind = 'SOURCE' | 'EVIDENCE'
export type KnowledgeVerificationValidationClass = 'REFERENCE' | 'DOCUMENT' | 'REAL_TEST'

export interface KnowledgeVerificationInput {
  readonly knowledgeUri: string
  readonly basisRef: string
  readonly relation: KnowledgeVerificationRelation
  readonly note?: string
}

export interface KnowledgeVerificationRecord extends KnowledgeVerificationInput {
  readonly verificationId: string
  readonly basisKind: KnowledgeVerificationBasisKind
  readonly validationClass: KnowledgeVerificationValidationClass
  readonly knowledgeFingerprint: string
  readonly recordedAt: string
}

export interface KnowledgeVerificationSummary {
  readonly knowledgeUri: string
  readonly supportCount: number
  readonly contradictCount: number
  readonly records: readonly KnowledgeVerificationRecord[]
}

export type KnowledgeValidationDecision = 'INSUFFICIENT' | 'READY' | 'BLOCKED'

export interface KnowledgeValidationEvaluation {
  readonly knowledgeUri: string
  readonly libraryScope: KnowledgeLibraryScope
  readonly currentStatus: KnowledgeStatus
  readonly knowledgeFingerprint: string
  readonly decision: KnowledgeValidationDecision
  readonly requiredSupportCount: number
  readonly distinctSupportCount: number
  readonly documentSupportCount: number
  readonly realTestSupportCount: number
  readonly contradictCount: number
  readonly targetStatus?: Extract<KnowledgeStatus, 'VALIDATED' | 'FULL_VALIDATED'>
  readonly reasons: readonly string[]
  readonly records: readonly KnowledgeVerificationRecord[]
}

export interface KnowledgePromotionResult {
  readonly evaluation: KnowledgeValidationEvaluation
  readonly mutation: KnowledgeMutationResult
}
