import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { resolve } from 'node:path'
import { afterAll, describe, expect, it } from 'vitest'
import {
  ATP_PROJECT_ID,
  classifyAutomatedTestingPlatformTask,
  compileAtpTaskContext,
  loadCurrentAtpTaskContext,
} from '../src/context-contributor.js'
import { findAutomatedTestingPlatformRoot } from '../src/root-discovery.js'
import {
  PROJECT_CONTEXT_CONTRIBUTION_REQUEST_SCHEMA,
  type ProjectContextContributionRequestV01,
} from '@agent-harness/auto-governance-engine'

const integrationIt = process.env.ATP_CONTEXT_CONTRIBUTOR_INTEGRATION === '1'
  ? it
  : it.skip
const temporaryRoot = mkdtempSync(resolve(tmpdir(), 'atp-context-contributor-'))

afterAll(() => {
  rmSync(temporaryRoot, { recursive: true, force: true })
})

describe('ATP Context Contributor compiler integration', () => {
  integrationIt('compiles and reuses the existing project Task Context without a second context system', () => {
    const root = findAutomatedTestingPlatformRoot()
    const rawTask = '分析6801芯片etimer这个IP。'
    const task = classifyAutomatedTestingPlatformTask(rawTask, root)
    expect(task).toBeDefined()
    const request: ProjectContextContributionRequestV01 = {
      schema: PROJECT_CONTEXT_CONTRIBUTION_REQUEST_SCHEMA,
      projectId: ATP_PROJECT_ID,
      taskId: 'ATP-ETIMER-COMPILER-INTEGRATION',
      rawTask,
      phase: 'analysis',
      workspacePath: root,
      initialRoute: {
        architectureIds: ['A010.020.010'],
        ruleIds: ['R010.020.020'],
        knowledgeIds: [],
        gateIds: [],
      },
    }
    const outputPath = resolve(temporaryRoot, 'current_task_context.json')

    const compiled = compileAtpTaskContext(root, request, task!, { outputPath })
    expect(compiled.schema).toBe('et.task-context.v1')
    expect(compiled.task).toMatchObject({
      modules: ['ip-package'],
      changes: ['analysis'],
      chip: 'et6801',
      ip: 'etimer',
    })
    expect(compiled.must_read.some(item =>
      item.path === 'project-governance/ip-analysis-sources.yaml',
    )).toBe(true)
    expect(compiled.rule_owners.map(item => item.owner_id)).toEqual(
      expect.arrayContaining([
        'public_ip_semantics_and_chip_adaptation',
        'contract_document_sync',
        'public_ip_machine_contract',
        'canonical_result_evidence',
        'ip_analysis_workflow',
      ]),
    )
    expect(compiled.write_scope.allowed).toContain('test_case_doc/etimer/**')

    const reused = loadCurrentAtpTaskContext(
      root,
      { ...request, phase: 'implementation' },
      task!,
      { outputPath },
    )
    expect(reused.fingerprint).toBe(compiled.fingerprint)
    expect(reused.integrity_fingerprint).toBe(compiled.integrity_fingerprint)
  })
})
