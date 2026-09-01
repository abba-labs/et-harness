import { describe, expect, it } from 'vitest'
import {
  MANDATORY_LIFECYCLE_CLOSURE_MODULE_IDS,
  hashCanonicalJson,
  validateObligationLedgerContribution,
} from '@agent-harness/execution-supervisor'
import {
  GOVERNANCE_BASELINE_SUPERVISION_PROFILE,
  compileGovernanceBaselineSupervisionContractV01,
  compileGovernanceProjectSupervisionContractV01,
} from '../src/baseline-supervision-compiler.js'

const context = () => ({
  actorId: 'agent-1',
  projectId: 'project-1',
  taskId: 'task-1',
  goal: 'Run a governed task',
  stateVersion: 7,
  route: {
    architectureIds: ['architecture://public/runtime'],
    ruleIds: ['rule://public/governance'],
    knowledgeIds: [],
    gateIds: ['gate://public/closure'],
  },
  contextContributions: [],
  applicableGateIds: ['gate://public/closure'],
  pendingReviews: [],
  text: 'Bounded routed context',
})

const compile = (overrides: Record<string, unknown> = {}) =>
  compileGovernanceBaselineSupervisionContractV01({
    projectId: 'project-1',
    taskId: 'task-1',
    agentId: 'agent-1',
    context: context(),
    ...overrides,
  } as never)

describe('Governance baseline supervision compiler', () => {
  it('deterministically binds exact Context and Route identities', () => {
    const first = compile()
    const second = compile()

    expect(first).toEqual(second)
    expect(hashCanonicalJson(first)).toBe(hashCanonicalJson(second))
    expect(first).toMatchObject({
      projectId: 'project-1',
      taskId: 'task-1',
      agentId: 'agent-1',
      contextHash: hashCanonicalJson(context()),
      routeHash: hashCanonicalJson(context().route),
      supervisionLevel: 'AUDIT',
    })
    expect(validateObligationLedgerContribution(first)).toMatchObject({ valid: true })
  })

  it('merges a structured Project contribution without parsing Context text', () => {
    const routed = context() as ReturnType<typeof context> & { contextContributions: any[] }
    routed.contextContributions = [{
      providerId: 'project.provider', contributionId: 'project-task', fingerprint: `sha256:${'a'.repeat(64)}`,
      referenceIds: [], inlineItemIds: [],
      supervision: {
        schema: 'agent-harness.project-supervision-contribution.v0.1',
        obligations: [{
          id: 'OBL-PROJECT-READ', kind: 'REQUIRED_RESOURCE', severity: 'MUST', sourceRefs: ['R001'],
          target: { resourceId: 'project://resource/required' },
          satisfaction: { acceptedProviderIds: ['host.filesystem'], acceptedDispositions: ['FOUND'] },
        }],
        evidencePolicies: [],
        completionPolicy: {
          requireAllMustSatisfied: true, requireNoViolations: true, requireReflection: true,
          requireKnowledgeDecision: true, requireContextUpdate: true, requireClosureReceipt: true,
          allowShouldWarnings: true,
          requiredClosureModuleIds: [...MANDATORY_LIFECYCLE_CLOSURE_MODULE_IDS],
        },
      },
    }]

    const contract = compileGovernanceProjectSupervisionContractV01({
      projectId: 'project-1', taskId: 'task-1', agentId: 'agent-1', context: routed,
    })
    expect(contract.obligations.map(item => item.id)).toContain('OBL-PROJECT-READ')
    expect(contract.obligations.filter(item => item.kind === 'CLOSURE')).toHaveLength(1)
    expect(contract.contextHash).toBe(hashCanonicalJson(routed))
    expect(validateObligationLedgerContribution(contract)).toMatchObject({ valid: true })
  })

  it.each([
    ['projectId', 'project-other'],
    ['taskId', 'task-other'],
    ['agentId', 'agent-other'],
  ] as const)('rejects a %s that differs from the routed Context', (name, value) => {
    expect(() => compile({ [name]: value })).toThrow(`${name} does not match Context`)
  })

  it('emits only the public lifecycle baseline and never claims full project supervision', () => {
    const contract = compile()
    const executionKinds = new Set([
      'REQUIRED_RESOURCE', 'SOURCE_DISPOSITION', 'OUTPUT', 'WRITE_SCOPE',
      'VALIDATION', 'CLAIM_EVIDENCE', 'RULE_COMPLIANCE',
    ])

    expect(GOVERNANCE_BASELINE_SUPERVISION_PROFILE).toBe('BASELINE_LIFECYCLE')
    expect(contract.obligations.map(item => item.kind)).toEqual([
      'REFLECTION', 'KNOWLEDGE_DECISION', 'CONTEXT_UPDATE', 'CLOSURE',
    ])
    expect(contract.obligations.some(item => executionKinds.has(item.kind))).toBe(false)
    expect(contract.evidencePolicies).toEqual([])
    expect(contract.completionPolicy.requiredClosureModuleIds).toHaveLength(8)
    expect(contract).not.toHaveProperty('fullProjectSupervision')
  })
})
