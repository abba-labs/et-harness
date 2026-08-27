import type { ProjectCandidateResult, ProjectResourceIndexEntryV01 } from '@agent-harness/project-contract'

export type ArchitectureIndexState = 'ready' | 'rejected'

export interface ArchitectureNode {
  readonly id: string
  readonly fileId: string
  readonly title: string
  readonly depth: number
  readonly parentId?: string
  readonly children: readonly string[]
  readonly location: string
  readonly directContent: string
  readonly role?: string
  readonly boundary?: string
  readonly resources: readonly string[]
  readonly relations: readonly string[]
}

export interface ArchitectureRouteFile extends ProjectResourceIndexEntryV01 {
  readonly nodes: readonly string[]
}

export interface ArchitectureProjectIndex {
  readonly projectId: string
  readonly state: ArchitectureIndexState
  readonly resourcePath: string
  readonly files: readonly ArchitectureRouteFile[]
  readonly nodeCount: number
  readonly warnings: readonly string[]
  readonly builtAt: string
}

export interface ArchitectureNodeResult {
  readonly projectId: string
  readonly node: ArchitectureNode
}

export type ArchitectureCandidate = ProjectCandidateResult
