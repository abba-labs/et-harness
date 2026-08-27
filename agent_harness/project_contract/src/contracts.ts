export type ProjectResourceKind = 'architecture' | 'rules' | 'knowledge' | 'gates'

export type ProjectResourceStandardId =
  | 'architecture-v0.1'
  | 'rule-v0.1'
  | 'knowledge-v0.1'
  | 'gate-v0.1'

export interface ProjectIdentity {
  readonly id: string
  readonly name: string
  readonly type?: string
  readonly aliases?: readonly string[]
  readonly description?: string
}

export interface ProjectRootConfig {
  readonly markers: readonly string[]
}

export interface ProjectResourceSource {
  readonly path: string
  readonly standard: ProjectResourceStandardId
  readonly metadata?: Readonly<Record<string, unknown>>
}

export interface ProjectAdapterSource {
  readonly provider: string
  readonly capability?: string
  readonly metadata?: Readonly<Record<string, unknown>>
}

export interface ProjectManifestV01 {
  readonly contract_version: '0.1'
  readonly project: ProjectIdentity
  readonly root: ProjectRootConfig
  readonly resources: Readonly<Record<ProjectResourceKind, ProjectResourceSource>>
  readonly adapters?: Readonly<Record<string, ProjectAdapterSource>>
  readonly metadata?: Readonly<Record<string, unknown>>
}

export interface ProjectContext {
  readonly contractVersion: '0.1'
  readonly projectId: string
  readonly displayName: string
  readonly projectType?: string
  readonly aliases: readonly string[]
  readonly projectRoot: string
  readonly resources: Readonly<Record<ProjectResourceKind, string>>
  readonly resourceStandards: Readonly<Record<ProjectResourceKind, ProjectResourceStandardId>>
  readonly adapters: Readonly<Record<string, ProjectAdapterSource>>
  readonly metadata?: Readonly<Record<string, unknown>>
}

export interface ProjectResourceIndexEntryV01 {
  readonly id: string
  readonly file: string
  readonly title: string
  readonly summary: string
  readonly aliases: readonly string[]
}

export interface ProjectResourceIndexV01 {
  readonly interface: 'project-resource-index-v0.1'
  readonly resource: ProjectResourceKind
  readonly standard: ProjectResourceStandardId
  readonly files: readonly ProjectResourceIndexEntryV01[]
}

export interface ProjectResourceInterfaceValidationResult {
  readonly valid: boolean
  readonly errors: readonly string[]
  readonly warnings: readonly string[]
}

export interface ProjectQueryScope {
  readonly module?: string
  readonly concern?: string
  readonly resource?: string
  readonly action?: string
  readonly [key: string]: unknown
}

export interface ProjectQueryRequest {
  readonly projectId: string
  readonly query: string
  readonly scope?: ProjectQueryScope
  readonly filters?: Readonly<Record<string, unknown>>
  readonly limit?: number
}

export interface CandidateProvenance {
  readonly resource: string
  readonly location: string
}

export interface ProjectCandidateResult {
  readonly projectId: string
  readonly id: string
  readonly title: string
  readonly type: string
  readonly location: string
  readonly summary?: string
  readonly relevance?: number
  readonly matchReasons: readonly string[]
  readonly provenance: CandidateProvenance
  readonly metadata?: Readonly<Record<string, unknown>>
  readonly warnings?: readonly string[]
}

export interface ProjectResolutionCandidate {
  readonly projectId: string
  readonly displayName: string
  readonly relevance: number
  readonly matchReasons: readonly string[]
}

export interface ProjectManifestValidationResult {
  readonly valid: boolean
  readonly errors: readonly string[]
}
