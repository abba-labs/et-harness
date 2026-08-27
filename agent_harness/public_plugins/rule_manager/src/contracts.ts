import type { ProjectResourceIndexEntryV01 } from '@agent-harness/project-contract'

export type RuleLevel = 'MUST' | 'MUST_NOT' | 'MAY'

export interface RuleNode {
  readonly id: string
  readonly fileId: string
  readonly title: string
  readonly depth: number
  readonly parentId?: string
  readonly children: readonly string[]
  readonly location: string
  readonly directContent: string
  readonly isLeaf: boolean
  readonly level?: RuleLevel
  readonly when?: string
  readonly rule?: string
  readonly refs: readonly string[]
}

export interface RuleRouteFile extends ProjectResourceIndexEntryV01 {
  readonly nodes: readonly string[]
}

export interface RuleProjectIndex {
  readonly projectId: string
  readonly state: 'ready'
  readonly resourcePath: string
  readonly files: readonly RuleRouteFile[]
  readonly nodeCount: number
  readonly ruleCount: number
  readonly warnings: readonly string[]
  readonly builtAt: string
}

export interface RuleNodeResult {
  readonly projectId: string
  readonly node: RuleNode
}
