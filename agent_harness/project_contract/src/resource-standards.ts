import type { ProjectResourceKind, ProjectResourceStandardId } from './contracts.js'

export interface ProjectResourceRoutingSpec {
  readonly standard: ProjectResourceStandardId
  readonly nodePrefix: 'A' | 'R' | 'K' | 'G'
  readonly indexFile: '00_INDEX.md'
  readonly fileExtension: 'md' | 'yaml'
}

export const PROJECT_RESOURCE_ROUTING_SPECS: Readonly<
  Record<ProjectResourceKind, ProjectResourceRoutingSpec>
> = {
  architecture: {
    standard: 'architecture-v0.1',
    nodePrefix: 'A',
    indexFile: '00_INDEX.md',
    fileExtension: 'md',
  },
  rules: {
    standard: 'rule-v0.1',
    nodePrefix: 'R',
    indexFile: '00_INDEX.md',
    fileExtension: 'md',
  },
  knowledge: {
    standard: 'knowledge-v0.1',
    nodePrefix: 'K',
    indexFile: '00_INDEX.md',
    fileExtension: 'md',
  },
  gates: {
    standard: 'gate-v0.1',
    nodePrefix: 'G',
    indexFile: '00_INDEX.md',
    fileExtension: 'yaml',
  },
} as const

export const PROJECT_RESOURCE_STANDARDS: Readonly<
  Record<ProjectResourceKind, ProjectResourceStandardId>
> = Object.fromEntries(
  Object.entries(PROJECT_RESOURCE_ROUTING_SPECS).map(([kind, spec]) => [kind, spec.standard]),
) as Readonly<Record<ProjectResourceKind, ProjectResourceStandardId>>

export function expectedProjectResourceStandard(
  kind: ProjectResourceKind,
): ProjectResourceStandardId {
  return PROJECT_RESOURCE_ROUTING_SPECS[kind].standard
}

export function getProjectResourceRoutingSpec(
  kind: ProjectResourceKind,
): ProjectResourceRoutingSpec {
  return PROJECT_RESOURCE_ROUTING_SPECS[kind]
}

export interface ParsedNumberedResourceFile {
  readonly number: string
  readonly slug: string
  readonly fileId: string
}

export function parseNumberedResourceFileName(
  kind: ProjectResourceKind,
  fileName: string,
): ParsedNumberedResourceFile | undefined {
  const spec = PROJECT_RESOURCE_ROUTING_SPECS[kind]
  const escapedExtension = spec.fileExtension.replace('.', '\\.')
  const match = new RegExp(`^(\\d{3})_([a-z0-9][a-z0-9_-]*)\\.${escapedExtension}$`).exec(fileName)
  if (!match) return undefined

  const [, number, slug] = match
  if (!number || !slug || number === '000') return undefined

  return {
    number,
    slug,
    fileId: `${spec.nodePrefix}${number}`,
  }
}

export function isValidResourceNodeId(
  kind: ProjectResourceKind,
  nodeId: string,
  expectedFileNumber?: string,
): boolean {
  const spec = PROJECT_RESOURCE_ROUTING_SPECS[kind]
  const match = new RegExp(`^${spec.nodePrefix}(\\d{3})(?:\\.\\d{3})*$`).exec(nodeId)
  if (!match) return false
  if (expectedFileNumber !== undefined && match[1] !== expectedFileNumber) return false
  return true
}
