import { describe, expect, it } from 'vitest'
import type { ProjectCandidateResult } from '@agent-harness/project-contract'
import {
  candidateExplicitRelationIds,
  parseGovernanceResourceId,
  resolveGovernanceRouteGraph,
  type GovernanceRouteResourceKind,
} from '../src/route-resolver.js'

const PROJECT = 'synthetic-project'

const candidate = (
  id: string,
  metadata: Readonly<Record<string, unknown>> = {},
  projectId = PROJECT,
): ProjectCandidateResult => ({
  projectId,
  id,
  title: id,
  type: 'synthetic',
  location: `synthetic://${id}`,
  relevance: 1,
  matchReasons: ['fixture'],
  provenance: { resource: `project://${projectId}`, location: `synthetic://${id}` },
  metadata,
})

const emptySeeds = () => ({
  architecture: [] as ProjectCandidateResult[],
  rule: [] as ProjectCandidateResult[],
  knowledge: [] as ProjectCandidateResult[],
  gate: [] as ProjectCandidateResult[],
})

const limits = { architecture: 8, rule: 8, knowledge: 8, gate: 8 }

describe('bounded cross-resource governance route resolver', () => {
  it('parses only stable A/R/K/G identifiers', () => {
    expect(parseGovernanceResourceId('a010.020')).toEqual({ kind: 'architecture', id: 'A010.020' })
    expect(parseGovernanceResourceId('R140')).toEqual({ kind: 'rule', id: 'R140' })
    expect(parseGovernanceResourceId('file://rule.md')).toBeUndefined()
    expect(parseGovernanceResourceId('K001/../../other')).toBeUndefined()
  })

  it('extracts explicit relations and refs without treating ordinary text as a route', () => {
    expect(candidateExplicitRelationIds(candidate('A010', {
      relations: ['R010', 'K001', 'not-an-id'],
      refs: ['G010', 'R010'],
    }))).toEqual(['R010', 'K001', 'not-an-id', 'G010'])
  })

  it('expands all resource kinds for two bounded hops and terminates cycles', () => {
    const nodes = new Map<string, ProjectCandidateResult>([
      ['A010', candidate('A010', { relations: ['R010', 'K001', 'G010'] })],
      ['R010', candidate('R010', { refs: ['A010', 'K001.003', 'G010.010'] })],
      ['K001', candidate('K001', { refs: ['R010'] })],
      ['K001.003', candidate('K001.003')],
      ['G010', candidate('G010', { refs: ['R010'] })],
      ['G010.010', candidate('G010.010')],
    ])
    const seeds = emptySeeds()
    seeds.architecture.push(nodes.get('A010')!)

    const resolution = resolveGovernanceRouteGraph({
      projectId: PROJECT,
      seeds,
      limits,
      maxDepth: 2,
      exactLookup: (_kind, id) => nodes.get(id),
    })

    expect(resolution.candidates.architecture.map(item => item.id)).toEqual(['A010'])
    expect(resolution.candidates.rule.map(item => item.id)).toEqual(['R010'])
    expect(resolution.candidates.knowledge.map(item => item.id)).toEqual(['K001', 'K001.003'])
    expect(resolution.candidates.gate.map(item => item.id)).toEqual(['G010', 'G010.010'])
    expect(resolution.trace.find(item => item.id === 'R010')).toMatchObject({
      source: 'explicit-relation',
      fromId: 'A010',
      depth: 1,
    })
    expect(resolution.omissions).toEqual([])
  })

  it('rejects cross-project and kind-mismatched exact targets', () => {
    const seeds = emptySeeds()
    seeds.architecture.push(candidate('A010', { relations: ['K001', 'G010'] }))
    const targets = new Map<string, ProjectCandidateResult>([
      ['K001', candidate('K001', {}, 'other-project')],
      ['G010', candidate('R010')],
    ])

    const resolution = resolveGovernanceRouteGraph({
      projectId: PROJECT,
      seeds,
      limits,
      exactLookup: (_kind, id) => targets.get(id),
    })

    expect(resolution.candidates.knowledge).toEqual([])
    expect(resolution.candidates.gate).toEqual([])
    expect(resolution.omissions.map(item => item.reason)).toEqual([
      'project-mismatch',
      'missing-target',
    ])
  })

  it('keeps deterministic per-kind budgets', () => {
    const seeds = emptySeeds()
    seeds.architecture.push(candidate('A010', { relations: ['R001', 'R002', 'R003'] }))
    const lookup = (_kind: GovernanceRouteResourceKind, id: string) => candidate(id)

    const resolution = resolveGovernanceRouteGraph({
      projectId: PROJECT,
      seeds,
      limits: { ...limits, rule: 2 },
      exactLookup: lookup,
    })

    expect(resolution.candidates.rule.map(item => item.id)).toEqual(['R001', 'R002'])
    expect(resolution.omissions).toContainEqual({ id: 'R003', reason: 'budget', fromId: 'A010' })
  })
})
