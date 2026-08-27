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
  AUTOMATED_TESTING_PLATFORM_PROJECT_MANIFEST,
  findAutomatedTestingPlatformRoot,
} from '../src/root-discovery.js'

const PROJECT_ID = 'et-automated-testing-platform'

const requiredPath = (
  registry: ProjectRegistryEngine,
  kind: 'architecture' | 'rules' | 'knowledge' | 'gates',
): string => {
  const path = registry.getResourcePath(PROJECT_ID, kind)
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
    const context = registry.get(PROJECT_ID)

    expect(context).toBeDefined()
    expect(context?.projectRoot).toBe(root)
    expect(context?.adapters).toEqual({})
    expect(registry.resolve('ATP')[0]?.projectId).toBe(PROJECT_ID)

    const architecture = new ArchitectureNavigatorEngine()
    const rules = new RuleManagerEngine()
    const knowledge = new KnowledgeManagerEngine()
    const gates = new GateManagerEngine()

    const architectureIndex = architecture.refreshProject(
      PROJECT_ID,
      requiredPath(registry, 'architecture'),
      context!.resources.architecture,
    )
    const ruleIndex = rules.refreshProject(
      PROJECT_ID,
      requiredPath(registry, 'rules'),
      context!.resources.rules,
    )
    const knowledgeIndex = knowledge.refreshProject(
      PROJECT_ID,
      requiredPath(registry, 'knowledge'),
      context!.resources.knowledge,
    )
    const gateIndex = gates.refreshProject(
      PROJECT_ID,
      requiredPath(registry, 'gates'),
      context!.resources.gates,
    )

    expect(architectureIndex.nodeCount).toBeGreaterThanOrEqual(20)
    expect(ruleIndex.ruleCount).toBeGreaterThanOrEqual(20)
    expect(knowledgeIndex.libraryMode).toBe('library-v0.2')
    expect(knowledgeIndex.knowledgeCount).toBe(13)
    expect(gateIndex.gateCount).toBe(4)

    expect(
      architecture.search({
        projectId: PROJECT_ID,
        query: 'Task Context governance',
      }).some(item => item.id === 'A010.010.020'),
    ).toBe(true)

    expect(
      rules.search({
        projectId: PROJECT_ID,
        query: 'scope check validation',
      }).some(item => item.id === 'R010.010.030'),
    ).toBe(true)

    const branchKnowledge = knowledge.search({
      projectId: PROJECT_ID,
      query: 'project branch public main',
    })
    expect(branchKnowledge.some(item => item.id === 'K001.011')).toBe(true)
    expect(
      branchKnowledge.find(item => item.id === 'K001.011')?.metadata?.trustTier,
    ).toBe('SUPPORTED')

    expect(
      gates.search({
        projectId: PROJECT_ID,
        query: 'scope check',
      }).some(item => item.id === 'G010.010.020'),
    ).toBe(true)
    expect(gates.getExecutionPlan(PROJECT_ID, 'G010.010.020')?.steps[0]?.tool)
      .toBe('governance.scope.check')

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

    expect(architecture.removeProject(PROJECT_ID)).toBe(true)
    expect(rules.removeProject(PROJECT_ID)).toBe(true)
    expect(knowledge.removeProject(PROJECT_ID)).toBe(true)
    expect(gates.removeProject(PROJECT_ID)).toBe(true)
    disposeProject()

    expect(registry.get(PROJECT_ID)).toBeUndefined()
    expect(architecture.getIndex(PROJECT_ID)).toBeUndefined()
    expect(rules.getIndex(PROJECT_ID)).toBeUndefined()
    expect(knowledge.getIndex(PROJECT_ID)).toBeUndefined()
    expect(gates.getIndex(PROJECT_ID)).toBeUndefined()
  })

  it('keeps generated Knowledge indexing deterministic', () => {
    const root = findAutomatedTestingPlatformRoot()
    const manifest = loadProjectManifestFile(
      resolve(root, AUTOMATED_TESTING_PLATFORM_PROJECT_MANIFEST),
    )
    const registry = new ProjectRegistryEngine()
    const disposeProject = registry.register(manifest, root)
    const context = registry.get(PROJECT_ID)!
    const engine = new KnowledgeManagerEngine()
    const knowledgePath = requiredPath(registry, 'knowledge')
    const indexPath = resolve(knowledgePath, '00_INDEX.md')

    engine.refreshProject(PROJECT_ID, knowledgePath, context.resources.knowledge)
    const first = readFileSync(indexPath, 'utf-8')
    engine.refreshProject(PROJECT_ID, knowledgePath, context.resources.knowledge)
    const second = readFileSync(indexPath, 'utf-8')

    expect(second).toBe(first)
    expect(second).toContain('source_fingerprint: "sha256:')
    expect(second).toContain('- Knowledge: 13')

    engine.removeProject(PROJECT_ID)
    disposeProject()
  })
})
