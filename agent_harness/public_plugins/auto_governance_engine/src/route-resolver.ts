import type { ProjectCandidateResult } from '@agent-harness/project-contract'

export type GovernanceRouteResourceKind =
  | 'architecture'
  | 'rule'
  | 'knowledge'
  | 'gate'

export interface GovernanceRouteCandidateSet {
  readonly architecture: readonly ProjectCandidateResult[]
  readonly rule: readonly ProjectCandidateResult[]
  readonly knowledge: readonly ProjectCandidateResult[]
  readonly gate: readonly ProjectCandidateResult[]
}

export interface GovernanceRouteLimits {
  readonly architecture: number
  readonly rule: number
  readonly knowledge: number
  readonly gate: number
}

export interface GovernanceRouteTraceEntry {
  readonly kind: GovernanceRouteResourceKind
  readonly id: string
  readonly source: 'semantic-search' | 'explicit-relation'
  readonly depth: number
  readonly fromId?: string
}

export interface GovernanceRouteOmission {
  readonly id: string
  readonly reason: 'invalid-id' | 'missing-target' | 'project-mismatch' | 'kind-mismatch' | 'budget'
  readonly fromId?: string
}

export interface GovernanceRouteResolution {
  readonly candidates: GovernanceRouteCandidateSet
  readonly trace: readonly GovernanceRouteTraceEntry[]
  readonly omissions: readonly GovernanceRouteOmission[]
}

export interface ResolveGovernanceRouteGraphInput {
  readonly projectId: string
  readonly seeds: GovernanceRouteCandidateSet
  readonly limits: GovernanceRouteLimits
  readonly maxDepth?: number
  readonly exactLookup: (
    kind: GovernanceRouteResourceKind,
    id: string,
  ) => ProjectCandidateResult | undefined
}

const RESOURCE_ID_RE = /^([ARKG])\d{3}(?:\.\d{3})*$/
const KIND_BY_PREFIX: Readonly<Record<string, GovernanceRouteResourceKind>> = {
  A: 'architecture',
  R: 'rule',
  K: 'knowledge',
  G: 'gate',
}

const recordOf = (value: unknown): Record<string, unknown> | undefined =>
  typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : undefined

const uniqueStrings = (values: readonly string[]): string[] =>
  [...new Set(values.map(value => value.trim()).filter(Boolean))]

export const parseGovernanceResourceId = (
  value: string,
): { readonly kind: GovernanceRouteResourceKind; readonly id: string } | undefined => {
  const id = value.trim().toUpperCase()
  const match = RESOURCE_ID_RE.exec(id)
  if (!match?.[1]) return undefined
  const kind = KIND_BY_PREFIX[match[1]]
  return kind ? { kind, id } : undefined
}

export const candidateExplicitRelationIds = (
  candidate: ProjectCandidateResult,
): string[] => {
  const metadata = recordOf(candidate.metadata)
  const values = [metadata?.relations, metadata?.refs].flatMap(value =>
    Array.isArray(value)
      ? value.filter((item): item is string => typeof item === 'string')
      : [],
  )
  return uniqueStrings(values)
}

export function resolveGovernanceRouteGraph(
  input: ResolveGovernanceRouteGraphInput,
): GovernanceRouteResolution {
  const maxDepth = Math.max(0, input.maxDepth ?? 2)
  const maps: Record<GovernanceRouteResourceKind, Map<string, ProjectCandidateResult>> = {
    architecture: new Map(),
    rule: new Map(),
    knowledge: new Map(),
    gate: new Map(),
  }
  const order: Record<GovernanceRouteResourceKind, string[]> = {
    architecture: [],
    rule: [],
    knowledge: [],
    gate: [],
  }
  const trace: GovernanceRouteTraceEntry[] = []
  const omissions: GovernanceRouteOmission[] = []
  const queue: Array<{
    readonly kind: GovernanceRouteResourceKind
    readonly candidate: ProjectCandidateResult
    readonly depth: number
  }> = []

  const add = (
    kind: GovernanceRouteResourceKind,
    candidate: ProjectCandidateResult,
    source: GovernanceRouteTraceEntry['source'],
    depth: number,
    fromId?: string,
  ): boolean => {
    const parsed = parseGovernanceResourceId(candidate.id)
    if (!parsed || parsed.kind !== kind) {
      omissions.push({ id: candidate.id, reason: 'kind-mismatch', ...(fromId ? { fromId } : {}) })
      return false
    }
    if (candidate.projectId !== input.projectId) {
      omissions.push({ id: parsed.id, reason: 'project-mismatch', ...(fromId ? { fromId } : {}) })
      return false
    }
    if (maps[kind].has(parsed.id)) return false
    if (order[kind].length >= Math.max(1, input.limits[kind])) {
      omissions.push({ id: parsed.id, reason: 'budget', ...(fromId ? { fromId } : {}) })
      return false
    }

    const normalized = candidate.id === parsed.id ? candidate : { ...candidate, id: parsed.id }
    maps[kind].set(parsed.id, normalized)
    order[kind].push(parsed.id)
    trace.push({ kind, id: parsed.id, source, depth, ...(fromId ? { fromId } : {}) })
    queue.push({ kind, candidate: normalized, depth })
    return true
  }

  const seedKinds: readonly GovernanceRouteResourceKind[] = [
    'architecture',
    'rule',
    'knowledge',
    'gate',
  ]
  for (const kind of seedKinds) {
    for (const candidate of input.seeds[kind]) add(kind, candidate, 'semantic-search', 0)
  }

  for (let cursor = 0; cursor < queue.length; cursor += 1) {
    const current = queue[cursor]!
    if (current.depth >= maxDepth) continue

    for (const rawId of candidateExplicitRelationIds(current.candidate)) {
      const parsed = parseGovernanceResourceId(rawId)
      if (!parsed) {
        omissions.push({ id: rawId, reason: 'invalid-id', fromId: current.candidate.id })
        continue
      }
      if (maps[parsed.kind].has(parsed.id)) continue
      const candidate = input.exactLookup(parsed.kind, parsed.id)
      if (!candidate || candidate.id.toUpperCase() !== parsed.id) {
        omissions.push({ id: parsed.id, reason: 'missing-target', fromId: current.candidate.id })
        continue
      }
      add(parsed.kind, candidate, 'explicit-relation', current.depth + 1, current.candidate.id)
    }
  }

  const candidates: GovernanceRouteCandidateSet = {
    architecture: order.architecture.map(id => maps.architecture.get(id)!),
    rule: order.rule.map(id => maps.rule.get(id)!),
    knowledge: order.knowledge.map(id => maps.knowledge.get(id)!),
    gate: order.gate.map(id => maps.gate.get(id)!),
  }
  return { candidates, trace, omissions }
}
