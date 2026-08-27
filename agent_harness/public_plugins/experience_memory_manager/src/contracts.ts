import type {
  KnowledgeLibraryScope,
  KnowledgeValidationEvaluation,
  KnowledgeVerificationRecord,
} from '@agent-harness/knowledge-manager'

export type ExperienceStatus =
  | 'CANDIDATE'
  | 'KNOWLEDGE_CANDIDATE'
  | 'PROMOTED'
  | 'REJECTED'

export interface ExperienceCandidateInput {
  readonly projectId: string
  readonly taskId: string
  readonly title: string
  readonly fact: string
  readonly scope?: string
  readonly evidenceRefs: readonly string[]
  readonly refs?: readonly string[]
}

export interface ExperienceCandidate extends ExperienceCandidateInput {
  readonly candidateId: string
  readonly status: ExperienceStatus
  readonly createdAt: string
  readonly knowledgeCandidateId?: string
  readonly knowledgeCandidateUri?: string
  readonly knowledgeCandidateScope?: KnowledgeLibraryScope
  readonly promotedKnowledgeId?: string
  readonly promotedKnowledgeUri?: string
  readonly rejectedReason?: string
}

export interface ExperienceSearchRequest {
  readonly projectId: string
  readonly query: string
  readonly statuses?: readonly ExperienceStatus[]
  readonly limit?: number
}

export interface ExperienceKnowledgeCandidateTarget {
  readonly candidateId: string
  readonly targetScope: 'project' | 'global'
  readonly categoryId: string
  readonly title?: string
  readonly tags?: readonly string[]
  readonly refs?: readonly string[]
}

export interface ExperienceKnowledgeCandidateResult {
  readonly candidateId: string
  readonly knowledgeId: string
  readonly knowledgeUri: string
  readonly libraryScope: KnowledgeLibraryScope
  readonly verificationRecords: readonly KnowledgeVerificationRecord[]
  readonly evaluation: KnowledgeValidationEvaluation
}

export interface ExperienceKnowledgePromotionResult {
  readonly candidateId: string
  readonly knowledgeId: string
  readonly knowledgeUri: string
  readonly status: 'PROMOTED'
  readonly evaluation: KnowledgeValidationEvaluation
}

/** @deprecated legacy knowledge-v0.1 direct writer only */
export interface KnowledgePromotionTarget {
  readonly candidateId: string
  readonly fileId: string
  readonly parentNodeId: string
  readonly nodeId: string
  readonly title: string
}

/** @deprecated legacy knowledge-v0.1 direct writer only */
export interface KnowledgePromotionResult {
  readonly candidateId: string
  readonly knowledgeId: string
  readonly fileId: string
  readonly file: string
}
