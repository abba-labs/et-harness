export interface AutoGovernanceRouteSnapshot {
  readonly architectureIds: readonly string[]
  readonly ruleIds: readonly string[]
  readonly knowledgeIds: readonly string[]
  readonly gateIds: readonly string[]
}

export type AutoGovernanceReviewDecision = 'PENDING' | 'PASS' | 'BLOCK'

export interface AutoGovernancePendingReview {
  readonly packetId: string
  readonly projectId: string
  readonly taskId: string
  readonly gateId: string
  readonly capability: string
  readonly providerId: string
  readonly serviceName: string
  readonly decisionMethod: string
  readonly focus?: string
  readonly epoch: number
  readonly decision: AutoGovernanceReviewDecision
  readonly changeFiles: readonly string[]
}

export interface AutoGovernanceTaskStatus {
  readonly agentId: string
  readonly projectId: string
  readonly taskId: string
  readonly goal: string
  readonly codeChangeEpoch: number
  readonly codeChangeSeen: boolean
  readonly route: AutoGovernanceRouteSnapshot
  readonly applicableGateIds: readonly string[]
  readonly pendingReviews: readonly AutoGovernancePendingReview[]
  readonly lastInjectedStateVersion?: number
}

export interface AutoGovernanceReviewDecisionInput {
  readonly packetId: string
  readonly result: 'PASS' | 'BLOCK'
  readonly summary: string
  readonly reviewerId: string
  readonly findings?: readonly {
    readonly severity: 'INFO' | 'WARN' | 'BLOCK'
    readonly summary: string
    readonly location?: string
    readonly refs?: readonly string[]
  }[]
}

export interface AutoGovernanceReviewDecisionResult {
  readonly packetId: string
  readonly projectId: string
  readonly taskId: string
  readonly gateId: string
  readonly result: 'PASS' | 'BLOCK'
  readonly evidenceId?: string
  readonly allCurrentReviewsPass: boolean
  readonly gateSetSatisfied: boolean
}

export interface AutoGovernanceCompletionResult {
  readonly projectId: string
  readonly taskId: string
  readonly status: 'COMPLETED' | 'BLOCKED'
  readonly reason?: string
}
