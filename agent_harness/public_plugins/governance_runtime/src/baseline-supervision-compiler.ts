import type {
  AutoGovernanceContextEnvelope,
  ProjectSupervisionContributionV01,
} from '@agent-harness/auto-governance-engine'
import {
  MANDATORY_LIFECYCLE_CLOSURE_MODULE_IDS,
  TASK_SUPERVISION_CONTRACT_SCHEMA,
  hashCanonicalJson,
  validateObligationLedgerContribution,
  type SupervisionLevel,
  type TaskSupervisionContractV01,
} from '@agent-harness/execution-supervisor'

export const GOVERNANCE_BASELINE_SUPERVISION_PROFILE =
  'BASELINE_LIFECYCLE' as const

export interface GovernanceBaselineSupervisionInputV01 {
  readonly projectId: string
  readonly taskId: string
  readonly agentId: string
  readonly context: AutoGovernanceContextEnvelope
  readonly supervisionLevel?: SupervisionLevel
  readonly projectRevision?: string
}

const identityMismatch = (
  name: 'projectId' | 'taskId' | 'agentId',
  actual: string,
  expected: string,
): never => {
  throw new Error(
    `Baseline supervision ${name} does not match Context: ${actual} != ${expected}`,
  )
}

/**
 * Compiles only the Host-neutral lifecycle baseline.
 *
 * This deliberately contributes no project read, write, output, validation or
 * rule obligations. Full project supervision requires a structured Project
 * contribution and must not be inferred from Context prose.
 */
export const compileGovernanceBaselineSupervisionContractV01 = (
  input: GovernanceBaselineSupervisionInputV01,
): TaskSupervisionContractV01 => {
  if (input.context.projectId !== input.projectId) {
    identityMismatch('projectId', input.projectId, input.context.projectId)
  }
  if (input.context.taskId !== input.taskId) {
    identityMismatch('taskId', input.taskId, input.context.taskId)
  }
  if (input.context.actorId !== input.agentId) {
    identityMismatch('agentId', input.agentId, input.context.actorId)
  }

  const contract: TaskSupervisionContractV01 = {
    schema: TASK_SUPERVISION_CONTRACT_SCHEMA,
    projectId: input.projectId,
    taskId: input.taskId,
    agentId: input.agentId,
    contextHash: hashCanonicalJson(input.context),
    routeHash: hashCanonicalJson(input.context.route),
    ...(input.projectRevision === undefined
      ? {}
      : { projectRevision: input.projectRevision }),
    supervisionLevel: input.supervisionLevel ?? 'AUDIT',
    obligations: [{
      id: 'OBL-BASELINE-REFLECTION',
      kind: 'REFLECTION',
      severity: 'MUST',
      sourceRefs: [],
      target: {},
      satisfaction: {},
    }, {
      id: 'OBL-BASELINE-KNOWLEDGE-DECISION',
      kind: 'KNOWLEDGE_DECISION',
      severity: 'MUST',
      sourceRefs: [],
      target: {},
      satisfaction: {},
      dependencies: ['OBL-BASELINE-REFLECTION'],
    }, {
      id: 'OBL-BASELINE-CONTEXT-UPDATE',
      kind: 'CONTEXT_UPDATE',
      severity: 'MUST',
      sourceRefs: [],
      target: {},
      satisfaction: {},
      dependencies: ['OBL-BASELINE-KNOWLEDGE-DECISION'],
    }, {
      id: 'OBL-BASELINE-CLOSURE',
      kind: 'CLOSURE',
      severity: 'MUST',
      sourceRefs: [],
      target: {},
      satisfaction: {},
      dependencies: ['OBL-BASELINE-CONTEXT-UPDATE'],
    }],
    evidencePolicies: [],
    completionPolicy: {
      requireAllMustSatisfied: true,
      requireNoViolations: true,
      requireReflection: true,
      requireKnowledgeDecision: true,
      requireContextUpdate: true,
      requireClosureReceipt: true,
      allowShouldWarnings: true,
      requiredClosureModuleIds: [...MANDATORY_LIFECYCLE_CLOSURE_MODULE_IDS],
    },
  }

  const validation = validateObligationLedgerContribution(contract)
  if (!validation.valid) {
    throw new Error(
      `Invalid baseline supervision contract: ${validation.issues
        .map(issue => `${issue.path} ${issue.code}: ${issue.message}`)
        .join('; ')}`,
    )
  }
  return validation.value
}

const LIFECYCLE_KINDS = new Set(['REFLECTION', 'KNOWLEDGE_DECISION', 'CONTEXT_UPDATE', 'CLOSURE'])

const assertMandatoryCompletionPolicy = (
  contribution: ProjectSupervisionContributionV01,
  baseline: TaskSupervisionContractV01,
): void => {
  const policy = contribution.completionPolicy
  if (!policy.requireAllMustSatisfied
      || !policy.requireNoViolations
      || !policy.requireReflection
      || !policy.requireKnowledgeDecision
      || !policy.requireContextUpdate
      || !policy.requireClosureReceipt) {
    throw new Error('Project supervision cannot weaken the mandatory Runtime completion policy')
  }
  const expected = [...baseline.completionPolicy.requiredClosureModuleIds].sort()
  const actual = [...new Set(policy.requiredClosureModuleIds)].sort()
  if (actual.length !== policy.requiredClosureModuleIds.length
      || actual.length !== expected.length
      || actual.some((item, index) => item !== expected[index])) {
    throw new Error('Project supervision must preserve the eight frozen Closure modules')
  }
}

/**
 * Adds one validated Project-owned supervision contribution to the public
 * lifecycle baseline. The contribution is carried structurally in Context and
 * is never inferred from model-visible prose.
 */
export const compileGovernanceProjectSupervisionContractV01 = (
  input: GovernanceBaselineSupervisionInputV01,
): TaskSupervisionContractV01 => {
  const baseline = compileGovernanceBaselineSupervisionContractV01(input)
  const contributions = input.context.contextContributions
    .flatMap(receipt => receipt.supervision ? [receipt.supervision] : [])
  if (contributions.length === 0) return baseline
  if (contributions.length > 1) {
    throw new Error('Contract v0.1 accepts exactly one structured Project supervision contribution')
  }
  const contribution = contributions[0]!
  assertMandatoryCompletionPolicy(contribution, baseline)
  if (contribution.obligations.some(item => LIFECYCLE_KINDS.has(item.kind))) {
    throw new Error('Project supervision must not replace Runtime-owned lifecycle obligations')
  }
  if (input.projectRevision !== undefined && contribution.projectRevision !== undefined
      && input.projectRevision !== contribution.projectRevision) {
    throw new Error('Project supervision revision does not match the trusted deployment revision')
  }

  const contract: TaskSupervisionContractV01 = {
    ...baseline,
    ...(contribution.projectRevision === undefined
      ? {}
      : { projectRevision: contribution.projectRevision }),
    obligations: [...contribution.obligations, ...baseline.obligations],
    evidencePolicies: [...contribution.evidencePolicies],
    completionPolicy: {
      ...baseline.completionPolicy,
      allowShouldWarnings: contribution.completionPolicy.allowShouldWarnings,
    },
  }
  const validation = validateObligationLedgerContribution(contract)
  if (!validation.valid) {
    throw new Error(`Invalid combined project supervision contract: ${validation.issues
      .map(issue => `${issue.path} ${issue.code}: ${issue.message}`).join('; ')}`)
  }
  return validation.value
}
