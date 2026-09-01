import type { ProjectResourceIndexEntryV01 } from '@agent-harness/project-contract'

export type GateLevel = 'MUST' | 'MAY'
export type GateStepRole = 'REVIEW' | 'EVIDENCE_PRODUCER'

export interface GateStep {
  readonly id: string
  readonly tool: string
  /** Optional for gate-v0.1 compatibility; new Gate plans should declare it explicitly. */
  readonly role?: GateStepRole
  readonly args?: Readonly<Record<string, unknown>>
}

export interface GateExecution {
  readonly level: GateLevel
  readonly when: string
  readonly steps: readonly GateStep[]
  readonly pass: unknown
  readonly refs: readonly string[]
}

export interface GateNode {
  readonly id: string
  readonly fileId: string
  readonly title: string
  readonly depth: number
  readonly parentId?: string
  readonly children: readonly string[]
  readonly location: string
  readonly isGate: boolean
  readonly gate?: GateExecution
}

export interface GateRouteFile extends ProjectResourceIndexEntryV01 {
  readonly nodes: readonly string[]
}

export interface GateProjectIndex {
  readonly projectId: string
  readonly state: 'ready'
  readonly resourcePath: string
  readonly files: readonly GateRouteFile[]
  readonly nodeCount: number
  readonly gateCount: number
  readonly warnings: readonly string[]
  readonly builtAt: string
}

export interface GateNodeResult {
  readonly projectId: string
  readonly node: GateNode
}

export interface GateExecutionPlan {
  readonly projectId: string
  readonly gateId: string
  readonly level: GateLevel
  readonly when: string
  readonly steps: readonly GateStep[]
  readonly pass: unknown
  readonly refs: readonly string[]
}

export interface GateEvidenceStatus {
  readonly projectId: string
  readonly taskId: string
  readonly gateId: string
  readonly level: GateLevel
  readonly satisfied: boolean
  readonly blocksCompletion: boolean
  readonly evidenceRefs: readonly string[]
}

export interface GateSetEvidenceStatus {
  readonly projectId: string
  readonly taskId: string
  readonly gates: readonly GateEvidenceStatus[]
  readonly blockingGateIds: readonly string[]
  readonly canComplete: boolean
}
