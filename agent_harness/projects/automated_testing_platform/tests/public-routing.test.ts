import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import {
  loadProjectManifestFile,
  ProjectRegistryEngine,
} from '@agent-harness/project-manager'
import { ArchitectureNavigatorEngine } from '@agent-harness/architecture-navigator'
import { RuleManagerEngine } from '@agent-harness/rule-manager'
import { KnowledgeManagerEngine } from '@agent-harness/knowledge-manager'
import { GateManagerEngine } from '@agent-harness/gate-manager'
import {
  ATP_CONTEXT_CONTRIBUTOR_PROVIDER_ID,
  ATP_PROJECT_ID,
} from '../src/context-contributor.js'
import {
  AUTOMATED_TESTING_PLATFORM_PROJECT_MANIFEST,
  findAutomatedTestingPlatformRoot,
} from '../src/root-discovery.js'

const requiredPath = (
  registry: ProjectRegistryEngine,
  kind: 'architecture' | 'rules' | 'knowledge' | 'gates',
): string => {
  const path = registry.getResourcePath(ATP_PROJECT_ID, kind)
  if (!path) throw new Error(`missing ${kind} resource path`)
  return path
}

describe('Automated Testing Platform public manager integration', () => {
  it('registers the project and routes A/R/K/G through the real public engines', () => {
    const root = findAutomatedTestingPlatformRoot()
    const manifest = loadProjectManifestFile(
      resolve(root, AUTOMATED_TESTING_PLATFORM_PROJECT_MANIFEST),
    )
    const registry = new ProjectRegistryEngine()
    const disposeProject = registry.register(manifest, root)
    const context = registry.get(ATP_PROJECT_ID)

    expect(context).toBeDefined()
    expect(context?.projectRoot).toBe(root)
    expect(context?.adapters.task_context).toMatchObject({
      provider: ATP_CONTEXT_CONTRIBUTOR_PROVIDER_ID,
      capability: 'context.contribute',
    })
    expect(registry.resolve('ATP')[0]?.projectId).toBe(ATP_PROJECT_ID)

    const architecture = new ArchitectureNavigatorEngine()
    const rules = new RuleManagerEngine()
    const knowledge = new KnowledgeManagerEngine()
    const gates = new GateManagerEngine()

    const architectureIndex = architecture.refreshProject(
      ATP_PROJECT_ID,
      requiredPath(registry, 'architecture'),
      context!.resources.architecture,
    )
    const ruleIndex = rules.refreshProject(
      ATP_PROJECT_ID,
      requiredPath(registry, 'rules'),
      context!.resources.rules,
    )
    const knowledgeIndex = knowledge.refreshProject(
      ATP_PROJECT_ID,
      requiredPath(registry, 'knowledge'),
      context!.resources.knowledge,
    )
    const gateIndex = gates.refreshProject(
      ATP_PROJECT_ID,
      requiredPath(registry, 'gates'),
      context!.resources.gates,
    )

    expect(architectureIndex.nodeCount).toBeGreaterThanOrEqual(20)
    expect(ruleIndex.ruleCount).toBeGreaterThanOrEqual(24)
    expect(knowledgeIndex.libraryMode).toBe('library-v0.2')
    expect(knowledgeIndex.knowledgeCount).toBe(13)
    expect(gateIndex.gateCount).toBe(4)

    expect(
      architecture.search({
        projectId: ATP_PROJECT_ID,
        query: 'Task Context governance',
      }).some(item => item.id === 'A010.010.020'),
    ).toBe(true)
    expect(
      architecture.search({
        projectId: ATP_PROJECT_ID,
        query: 'IP analysis contract',
      }).some(item => item.id === 'A010.020.010'),
    ).toBe(true)

    expect(
      rules.search({
        projectId: ATP_PROJECT_ID,
        query: 'scope check validation',
      }).some(item => item.id === 'R010.010.030'),
    ).toBe(true)
    expect(
      rules.search({
        projectId: ATP_PROJECT_ID,
        query: 'IP analysis source disposition output contract',
      }).map(item => item.id),
    ).toEqual(expect.arrayContaining([
      'R020.010',
      'R020.020',
      'R020.030',
      'R020.040',
    ]))

    const branchKnowledge = knowledge.search({
      projectId: ATP_PROJECT_ID,
      query: 'project branch public main',
    })
    expect(branchKnowledge.some(item => item.id === 'K001.011')).toBe(true)
    expect(
      branchKnowledge.find(item => item.id === 'K001.011')?.metadata?.trustTier,
    ).toBe('SUPPORTED')
    expect(
      knowledge.search({
        projectId: ATP_PROJECT_ID,
        query: 'compiled Task Context missing route fail closed evidence',
      }).map(item => item.id),
    ).toEqual(expect.arrayContaining([
      'K001.003',
      'K001.004',
      'K001.008',
    ]))

    expect(
      gates.search({
        projectId: ATP_PROJECT_ID,
        query: 'scope check',
      }).some(item => item.id === 'G010.010.020'),
    ).toBe(true)
    expect(gates.getExecutionPlan(ATP_PROJECT_ID, 'G010.010.020')?.steps[0]?.tool)
      .toBe('governance.scope.check')
    expect(gates.getExecutionPlan(ATP_PROJECT_ID, 'G010.010.010')?.steps[0]?.tool)
      .toBe('governance.context.compile')

    const sources = readFileSync(
      resolve(requiredPath(registry, 'knowledge'), 'SOURCES.yaml'),
      'utf-8',
    )
    const sourceLocations = [...sources.matchAll(/^\s+location:\s+(.+)$/gm)]
      .map(match => match[1]?.trim())
      .filter((value): value is string => Boolean(value))

    expect(sourceLocations.length).toBeGreaterThanOrEqual(10)
    for (const location of sourceLocations) {
      expect(existsSync(resolve(root, location))).toBe(true)
    }

    expect(architecture.removeProject(ATP_PROJECT_ID)).toBe(true)
    expect(rules.removeProject(ATP_PROJECT_ID)).toBe(true)
    expect(knowledge.removeProject(ATP_PROJECT_ID)).toBe(true)
    expect(gates.removeProject(ATP_PROJECT_ID)).toBe(true)
    disposeProject()

    expect(registry.get(ATP_PROJECT_ID)).toBeUndefined()
    expect(architecture.getIndex(ATP_PROJECT_ID)).toBeUndefined()
    expect(rules.getIndex(ATP_PROJECT_ID)).toBeUndefined()
    expect(knowledge.getIndex(ATP_PROJECT_ID)).toBeUndefined()
    expect(gates.getIndex(ATP_PROJECT_ID)).toBeUndefined()
  })

  it('keeps generated Knowledge indexing deterministic', () => {
    const root = findAutomatedTestingPlatformRoot()
    const manifest = loadProjectManifestFile(
      resolve(root, AUTOMATED_TESTING_PLATFORM_PROJECT_MANIFEST),
    )
    const registry = new ProjectRegistryEngine()
    const disposeProject = registry.register(manifest, root)
    const context = registry.get(ATP_PROJECT_ID)!
    const engine = new KnowledgeManagerEngine()
    const knowledgePath = requiredPath(registry, 'knowledge')
    const indexPath = resolve(knowledgePath, '00_INDEX.md')

    engine.refreshProject(ATP_PROJECT_ID, knowledgePath, context.resources.knowledge)
    const first = readFileSync(indexPath, 'utf-8')
    engine.refreshProject(ATP_PROJECT_ID, knowledgePath, context.resources.knowledge)
    const second = readFileSync(indexPath, 'utf-8')

    expect(second).toBe(first)
    expect(second).toContain('source_fingerprint: "sha256:')
    expect(second).toContain('- Knowledge: 13')

    engine.removeProject(ATP_PROJECT_ID)
    disposeProject()
  })
})
