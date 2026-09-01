import { describe, expect, it } from 'vitest'
import {
  ATP_CONTEXT_CONTRIBUTOR_PROVIDER_ID,
  ATP_PROJECT_ID,
  buildAtpIpAnalysisContribution,
  classifyAutomatedTestingPlatformTask,
  type AtpCompiledTaskContext,
} from '../src/context-contributor.js'
import { findAutomatedTestingPlatformRoot } from '../src/root-discovery.js'
import {
  PROJECT_CONTEXT_CONTRIBUTION_REQUEST_SCHEMA,
  PROJECT_CONTEXT_CONTRIBUTION_SCHEMA,
  normalizeProjectContextContribution,
  type ProjectContextContributionRequestV01,
} from '@agent-harness/auto-governance-engine'

const RAW_TASK = '分析6801芯片etimer这个IP。'

const requestFixture = (
  root: string,
  rawTask = RAW_TASK,
): ProjectContextContributionRequestV01 => ({
  schema: PROJECT_CONTEXT_CONTRIBUTION_REQUEST_SCHEMA,
  projectId: ATP_PROJECT_ID,
  taskId: 'ATP-ETIMER-CONTEXT-TEST',
  rawTask,
  phase: 'analysis',
  workspacePath: root,
  initialRoute: {
    architectureIds: ['A010.020.010'],
    ruleIds: ['R010.020.020'],
    knowledgeIds: [],
    gateIds: [],
  },
})

const compiledFixture = (): AtpCompiledTaskContext => ({
  schema: 'et.task-context.v1',
  generated_at: '2026-08-28T00:00:00+00:00',
  fingerprint: '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
  integrity_fingerprint: 'abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789',
  task: {
    id: 'ATP-ETIMER-CONTEXT-TEST',
    intent: RAW_TASK,
    modules: ['ip-package'],
    changes: ['analysis'],
    lanes: [],
    chip: 'et6801',
    ip: 'etimer',
    matched_changes_by_module: { 'ip-package': ['analysis'] },
  },
  repository: {
    available: true,
    branch: 'feat/atp-context-contributor-clean-v0.1',
    head: 'fixture-head',
    dirty: false,
  },
  architecture: [{
    module: 'ip-package',
    summary: 'IP package analysis',
    chain: ['Project', 'IP package'],
  }],
  must_read: [
    {
      path: 'AGENTS.md',
      reason: 'Project constitution',
      required: true,
      exists: true,
    },
    {
      path: 'project-governance/ip-analysis-sources.yaml',
      reason: 'IP analysis source map',
      required: true,
      exists: true,
    },
    {
      path: 'report/design/rules/R140_ip_analysis_workflow.md',
      reason: 'Active IP analysis Owner',
      required: true,
      exists: true,
    },
  ],
  rule_owners: [
    {
      owner_id: 'task_context_navigation',
      rule_id: 'ET-RULE-TASK-CONTEXT',
      source: 'report/design/rules/R002_task_context_navigation.md',
      heading: 'Task Context Navigation',
    },
    {
      owner_id: 'public_ip_semantics_and_chip_adaptation',
      rule_id: 'ET-RULE-PUBLIC-IP',
      source: 'report/design/rules/R100_public_ip_semantics_and_chip_adaptation.md',
      heading: 'Public IP Semantics And Chip Adaptation',
    },
    {
      owner_id: 'contract_document_sync',
      rule_id: 'ET-RULE-CONTRACT-SYNC',
      source: 'report/design/rules/R110_contract_document_sync.md',
      heading: 'Contract Document Sync',
    },
    {
      owner_id: 'public_ip_machine_contract',
      rule_id: 'ET-RULE-MACHINE-CONTRACT',
      source: 'report/design/rules/R120_public_ip_machine_contract.md',
      heading: 'Public IP Machine Contract',
    },
    {
      owner_id: 'canonical_result_evidence',
      rule_id: 'ET-RULE-EVIDENCE',
      source: 'report/design/rules/R130_canonical_result_evidence.md',
      heading: 'Canonical Result Evidence',
    },
    {
      owner_id: 'ip_analysis_workflow',
      rule_id: 'ET-RULE-IP-ANALYSIS',
      source: 'report/design/rules/R140_ip_analysis_workflow.md',
      heading: 'IP Analysis Workflow',
    },
  ],
  write_scope: {
    allowed: ['test_case_doc/etimer/**'],
    protected: ['pc/**', 'firmware/**'],
  },
  validation: [
    'python tools/quality/check_public_ip_contracts.py',
    'python tools/quality/validate_case_plans.py test_case_doc/etimer/etimer.md',
    'python tools/quality/validate_chip_ip_docs.py',
  ],
  source_inputs: [
    {
      path: 'project-governance/system-map.yaml',
      sha256: 'fixture-system-map-sha256',
    },
    {
      path: 'report/design/rules/R140_ip_analysis_workflow.md',
      sha256: 'fixture-r140-sha256',
    },
  ],
})

describe('ATP project-scoped Context Contributor', () => {
  it('classifies generic chip/IP analysis wording without eTimer-specific routing code', () => {
    const root = findAutomatedTestingPlatformRoot()
    expect(classifyAutomatedTestingPlatformTask(RAW_TASK, root)).toEqual({
      kind: 'ip-analysis',
      module: 'ip-package',
      change: 'analysis',
      chip: 'et6801',
      chipUpper: 'ET6801',
      ip: 'etimer',
    })
    expect(
      classifyAutomatedTestingPlatformTask('分析6003芯片dma这个IP。', root),
    ).toMatchObject({ chip: 'et6003', ip: 'dma' })
    expect(
      classifyAutomatedTestingPlatformTask('Analyze ET6801 eTimer IP', root),
    ).toMatchObject({ chip: 'et6801', ip: 'etimer' })
    expect(
      classifyAutomatedTestingPlatformTask('修复PC串口超时。', root),
    ).toBeUndefined()
    expect(() =>
      classifyAutomatedTestingPlatformTask('分析未知芯片timer这个IP。', root),
    ).toThrow(/did not resolve one registered chip/)
  })

  it('maps compiled project truth into the provider-neutral public contract', () => {
    const root = findAutomatedTestingPlatformRoot()
    const request = requestFixture(root)
    const task = classifyAutomatedTestingPlatformTask(RAW_TASK, root)
    expect(task).toBeDefined()

    const contribution = buildAtpIpAnalysisContribution(
      root,
      request,
      task!,
      compiledFixture(),
    )
    expect(contribution.schema).toBe(PROJECT_CONTEXT_CONTRIBUTION_SCHEMA)
    expect(contribution.projectId).toBe(ATP_PROJECT_ID)
    expect(contribution.provenance).toContain(ATP_CONTEXT_CONTRIBUTOR_PROVIDER_ID)
    expect(contribution.references).toEqual(expect.arrayContaining([
      { kind: 'architecture', id: 'A010.020.010', priority: 'required' },
      { kind: 'rule', id: 'R020.030', priority: 'required' },
      { kind: 'knowledge', id: 'K001.008', priority: 'required' },
      { kind: 'gate', id: 'G010.010.010', priority: 'required' },
    ]))
    expect(contribution.readScope).toContain(
      'project-governance/ip-analysis-sources.yaml',
    )
    expect(contribution.writeScope?.allowed).toContain(
      'test_case_doc/etimer/**',
    )
    expect(contribution.outputContract?.content).toContain(
      'test_case_doc/etimer/etimer.md',
    )
    expect(contribution.outputContract?.content).toContain(
      'test_case_doc/etimer/ET6801_etimer.md',
    )
    expect(contribution.supervision?.obligations.some(item =>
      item.kind === 'REQUIRED_RESOURCE' && item.target.resourceId === 'AGENTS.md')).toBe(true)
    expect(contribution.supervision?.obligations).toContainEqual(expect.objectContaining({
      id: 'OBL-ATP-WRITE-SCOPE',
      kind: 'WRITE_SCOPE',
    }))
    expect(contribution.supervision?.obligations.some(item => item.kind === 'VALIDATION')).toBe(true)
    expect(contribution.supervision?.completionPolicy.requiredClosureModuleIds).toHaveLength(8)
    expect(contribution.inlineItems?.map(item => item.id)).toContain(
      'external-source-disposition-contract',
    )

    const normalized = normalizeProjectContextContribution(
      ATP_CONTEXT_CONTRIBUTOR_PROVIDER_ID,
      request,
      contribution,
    )
    expect(normalized.references.length).toBeGreaterThan(0)
    expect(normalized.inlineItems.some(item =>
      item.content.includes('integrity_fingerprint'),
    )).toBe(true)
    expect(normalized.inlineItems.some(item =>
      item.content.includes('FOUND | NO_MATCH | UNAVAILABLE'),
    )).toBe(true)
  })

  it('fails closed when compiled scope does not authorize the two-document analysis area', () => {
    const root = findAutomatedTestingPlatformRoot()
    const request = requestFixture(root)
    const task = classifyAutomatedTestingPlatformTask(RAW_TASK, root)
    expect(task).toBeDefined()
    const compiled = compiledFixture()
    const invalid: AtpCompiledTaskContext = {
      ...compiled,
      write_scope: {
        allowed: ['tmp/**'],
        protected: compiled.write_scope.protected,
      },
    }
    expect(() =>
      buildAtpIpAnalysisContribution(root, request, task!, invalid),
    ).toThrow(/did not authorize/)
  })
})
