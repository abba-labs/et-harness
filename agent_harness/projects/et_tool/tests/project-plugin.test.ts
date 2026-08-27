import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { loadProjectManifestFile } from '@agent-harness/project-manager'
import {
  ET_TOOL_PROJECT_MANIFEST,
  ET_TOOL_PROJECT_SHELL_REQUIRED_PATHS,
  findEtToolProjectRoot,
  inject,
  validateEtToolProjectResources,
} from '../src/index.js'
import {
  ET_TOOL_REVIEW_CAPABILITIES,
  governanceManifest as reviewGovernanceManifest,
  inject as reviewAdapterInject,
} from '../src/review-adapter.js'

describe('ET-TOOL Project Plugin Shell v0.1', () => {
  it('主 Project Plugin 仍只通过 Public Project Manager 接入公共层', () => {
    expect(inject).toEqual(['projectManager'])
  })

  it('项目根标记与四类标准资源入口完整', () => {
    const root = findEtToolProjectRoot()
    const result = validateEtToolProjectResources(root)

    expect(result.valid, `missing: ${result.missing.join(', ')}`).toBe(true)
    expect(result.missing).toEqual([])
    expect(ET_TOOL_PROJECT_SHELL_REQUIRED_PATHS).toEqual([
      'agent_harness/projects/et_tool/project.yaml',
      'agent_harness/projects/et_tool/architecture/00_INDEX.md',
      'agent_harness/projects/et_tool/rules/00_INDEX.md',
      'agent_harness/projects/et_tool/knowledge/00_INDEX.md',
      'agent_harness/projects/et_tool/gates/00_INDEX.md',
    ])
  })

  it('project.yaml 符合 Project Contract v0.1 并声明 7 个 review adapter capability', () => {
    const root = findEtToolProjectRoot()
    const manifest = loadProjectManifestFile(resolve(root, ET_TOOL_PROJECT_MANIFEST))

    expect(manifest.contract_version).toBe('0.1')
    expect(manifest.project.id).toBe('et-tool')
    expect(manifest.resources).toEqual({
      architecture: {
        path: 'agent_harness/projects/et_tool/architecture/',
        standard: 'architecture-v0.1',
      },
      rules: {
        path: 'agent_harness/projects/et_tool/rules/',
        standard: 'rule-v0.1',
      },
      knowledge: {
        path: 'agent_harness/projects/et_tool/knowledge/',
        standard: 'knowledge-v0.1',
      },
      gates: {
        path: 'agent_harness/projects/et_tool/gates/',
        standard: 'gate-v0.1',
      },
    })
    expect(Object.values(manifest.adapters ?? {}).map(item => item.capability).sort()).toEqual(
      [...ET_TOOL_REVIEW_CAPABILITIES].sort(),
    )
  })

  it('Code Review Adapter 是独立可选插件并声明全部 Gate review capabilities', () => {
    expect(reviewAdapterInject).toEqual([
      'governanceCatalog',
      'projectManager',
      'architectureNavigator',
      'ruleManager',
      'knowledgeManager',
      'gateManager',
      'evidenceStateManager',
    ])
    expect(reviewGovernanceManifest.scope).toEqual({ kind: 'project', id: 'et-tool' })
    expect(reviewGovernanceManifest.provides.map(item => item.capability)).toEqual(
      ET_TOOL_REVIEW_CAPABILITIES,
    )
  })
})
