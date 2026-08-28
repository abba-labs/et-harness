import {
  EXECUTION_SUPERVISOR_CONTRACT_VERSION,
  type EvidenceAuthority,
  type EvidenceOutcome,
  type ExecutionCorrelation,
  type ExecutionSupervisionMode,
  type ObligationKind,
  type ObligationSpec,
  type SupervisionBinding,
  type TaskSupervisionContract,
} from './contracts.js'
import { sha256Canonical } from './canonical.js'
import { createTaskSupervisionContract } from './factory.js'
import { EXECUTION_SUPERVISOR_LIMITS } from './limits.js'
import { assertValidTaskSupervisionContract } from './validation.js'

export const PROJECT_SUPERVISION_CONTRIBUTION_SCHEMA =
  'agent-harness.project-supervision-contribution.v0.1' as const
export const TASK_SUPERVISION_BUILD_RECEIPT_SCHEMA =
  'agent-harness.task-supervision-build-receipt.v0.1' as const
export const EXECUTION_SUPERVISOR_BUILDER_VERSION = '0.1.0' as const

export const PUBLIC_LIFECYCLE_OBLIGATION_IDS = Object.freeze({
  reflection: 'PUBLIC.REFLECTION',
  knowledgeClassification: 'PUBLIC.KNOWLEDGE_CLASSIFICATION',
  contextClosure: 'PUBLIC.CONTEXT_CLOSURE',
  knowledgeClosure: 'PUBLIC.KNOWLEDGE_CLOSURE',
  turnClosure: 'PUBLIC.TURN_CLOSURE',
  followUpReuse: 'PUBLIC.FOLLOW_UP_REUSE',
})

export interface ProjectSupervisionContribution {
  readonly schema: typeof PROJECT_SUPERVISION_CONTRIBUTION_SCHEMA
  readonly contractVersion: typeof EXECUTION_SUPERVISOR_CONTRACT_VERSION
  readonly contributionId: string
  readonly projectId: string
  readonly taskId: string
  readonly provenance: string
  readonly obligations: readonly ObligationSpec[]
  readonly requireFollowUpReuse?: boolean
}

export interface HostSupervisionCapabilities {
  readonly hostId: string
  readonly adapterId: string
  readonly executionEventStream: boolean
  readonly crossProcessReplay: boolean
  readonly preExecutionActionGuard: boolean
  readonly mechanicalToolInterception: boolean
}

export interface TaskSupervisionBuildInput {
  readonly requestedMode: ExecutionSupervisionMode
  readonly correlation: ExecutionCorrelation
  readonly binding: SupervisionBinding
  readonly authorizedSourceRefs: readonly string[]
  readonly projectContributions: readonly ProjectSupervisionContribution[]
  readonly hostCapabilities: HostSupervisionCapabilities
  readonly maxBatchEvents?: number
}

export interface TaskSupervisionBuildReceipt {
  readonly schema: typeof TASK_SUPERVISION_BUILD_RECEIPT_SCHEMA
  readonly contractVersion: typeof EXECUTION_SUPERVISOR_CONTRACT_VERSION
  readonly builderVersion: typeof EXECUTION_SUPERVISOR_BUILDER_VERSION
  readonly supervisionId: string
  readonly projectId: string
  readonly taskId: string
  readonly turnId: string
  readonly mode: ExecutionSupervisionMode
  readonly contractHash: string
  readonly contributionIds: readonly string[]
  readonly authorizedSourceRefsHash: string
  readonly projectObligationCount: number
  readonly publicLifecycleObligationCount: number
  readonly totalObligationCount: number
  readonly receiptHash: string
}

export interface TaskSupervisionBuildResult {
  readonly contract: TaskSupervisionContract
  readonly receipt: TaskSupervisionBuildReceipt
}

const IDENTIFIER_RE = /^[A-Za-z0-9][A-Za-z0-9._:-]*$/
const SHA256_RE = /^[0-9a-f]{64}$/
const PUBLIC_SOURCE_PREFIX = 'public-contract://execution-supervisor/'

const uniqueSorted = (values: readonly string[]): string[] =>
  [...new Set(values.map(value => value.trim()).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b),
  )

const assertIdentifier = (label: string, value: string): string => {
  const normalized = value.trim()
  if (
    !normalized
    || normalized.length > EXECUTION_SUPERVISOR_LIMITS.maxIdentifierChars
    || !IDENTIFIER_RE.test(normalized)
  ) {
    throw new Error(`${label} must be one bounded stable identifier`)
  }
  return normalized
}

const assertBoundedReference = (label: string, value: string): string => {
  const normalized = value.trim()
  if (
    !normalized
    || normalized.length > EXECUTION_SUPERVISOR_LIMITS.maxReferenceChars
    || /[\r\n]/.test(normalized)
  ) {
    throw new Error(`${label} must be one bounded single-line reference`)
  }
  return normalized
}

const assertHash = (label: string, value: string): string => {
  if (!SHA256_RE.test(value)) throw new Error(`${label} must be SHA-256`)
  return value
}

const assertCorrelation = (correlation: ExecutionCorrelation): void => {
  for (const [key, value] of Object.entries(correlation)) {
    assertIdentifier(`correlation.${key}`, value)
  }
}

const assertBinding = (binding: SupervisionBinding): void => {
  for (const key of [
    'taskContextHash',
    'contextHash',
    'routeHash',
    'scopeHash',
    'outputContractHash',
  ] as const) {
    assertHash(`binding.${key}`, binding[key])
  }
  if (binding.sourceHead !== undefined) {
    assertBoundedReference('binding.sourceHead', binding.sourceHead)
  }
}

const assertHostCapabilities = (
  requestedMode: ExecutionSupervisionMode,
  capabilities: HostSupervisionCapabilities,
): void => {
  assertIdentifier('hostCapabilities.hostId', capabilities.hostId)
  assertIdentifier('hostCapabilities.adapterId', capabilities.adapterId)
  for (const key of [
    'executionEventStream',
    'crossProcessReplay',
    'preExecutionActionGuard',
    'mechanicalToolInterception',
  ] as const) {
    if (typeof capabilities[key] !== 'boolean') {
      throw new Error(`hostCapabilities.${key} must be boolean`)
    }
  }
  if (!capabilities.executionEventStream) {
    throw new Error(
      'Task supervision requires a Host Adapter that can return a bounded execution event stream',
    )
  }
  if (requestedMode === 'ENFORCE') {
    if (!capabilities.preExecutionActionGuard) {
      throw new Error(
        'ENFORCE mode requires a Host Adapter with pre-execution action guarding',
      )
    }
    if (!capabilities.mechanicalToolInterception) {
      throw new Error(
        'ENFORCE mode requires mechanical tool interception; AUDIT must be used otherwise',
      )
    }
  }
}

const frameworkEvidencePolicy = (): ObligationSpec['evidencePolicy'] => ({
  acceptableAuthorities: ['FRAMEWORK'],
  acceptedOutcomes: ['RECORDED'],
  minimumReceipts: 1,
  allowAgentDeclaration: false,
})

const publicLifecycleObligation = (
  obligationId: string,
  kind: ObligationKind,
  title: string,
  description: string,
  dependsOn: readonly string[] = [],
): ObligationSpec => ({
  obligationId,
  kind,
  level: 'MUST',
  title,
  description,
  sourceRefs: [`${PUBLIC_SOURCE_PREFIX}${kind.toLowerCase()}`],
  ...(dependsOn.length > 0 ? { dependsOn } : {}),
  evidencePolicy: frameworkEvidencePolicy(),
})

const publicLifecycleObligations = (
  requireFollowUpReuse: boolean,
): ObligationSpec[] => {
  const ids = PUBLIC_LIFECYCLE_OBLIGATION_IDS
  const obligations: ObligationSpec[] = [
    publicLifecycleObligation(
      ids.reflection,
      'REFLECTION',
      'Framework-owned unified Reflection',
      'The public Governance Runtime must execute one bounded unified Reflection for the exact governed Turn.',
    ),
    publicLifecycleObligation(
      ids.knowledgeClassification,
      'KNOWLEDGE_CLASSIFICATION',
      'Mandatory knowledge scope and category classification',
      'Reflection must explicitly choose NONE, PROJECT, PUBLIC or BOTH and provide valid category references for every emitted Knowledge Candidate.',
      [ids.reflection],
    ),
    publicLifecycleObligation(
      ids.contextClosure,
      'CONTEXT_CLOSURE',
      'Mandatory Context Closure',
      'The Context Closure module must persist progress, decisions, open issues, next actions and the reconciled Working Set.',
      [ids.reflection],
    ),
    publicLifecycleObligation(
      ids.knowledgeClosure,
      'KNOWLEDGE_CLOSURE',
      'Mandatory Knowledge Closure',
      'The Knowledge Closure module must persist valid candidates or record a deterministic NO_CHANGE result.',
      [ids.knowledgeClassification],
    ),
    publicLifecycleObligation(
      ids.turnClosure,
      'TURN_CLOSURE',
      'Mandatory Turn Closure Receipt',
      'The public Kernel must produce one COMPLETE Closure Receipt after every mandatory Closure module returns APPLIED or NO_CHANGE.',
      [ids.contextClosure, ids.knowledgeClosure],
    ),
  ]
  if (requireFollowUpReuse) {
    obligations.push(publicLifecycleObligation(
      ids.followUpReuse,
      'FOLLOW_UP_REUSE',
      'Follow-up Context and Knowledge reuse',
      'A later governed Turn must prove that persisted Context and eligible Knowledge are routed and reused without replaying the full prior conversation.',
      [ids.turnClosure],
    ))
  }
  return obligations
}

const assertProjectContribution = (
  contribution: ProjectSupervisionContribution,
  input: TaskSupervisionBuildInput,
  authorizedSourceRefs: ReadonlySet<string>,
): void => {
  if (contribution.schema !== PROJECT_SUPERVISION_CONTRIBUTION_SCHEMA) {
    throw new Error(`Unsupported Project Supervision Contribution schema: ${contribution.schema}`)
  }
  if (contribution.contractVersion !== EXECUTION_SUPERVISOR_CONTRACT_VERSION) {
    throw new Error(
      `Unsupported Project Supervision Contribution version: ${contribution.contractVersion}`,
    )
  }
  assertIdentifier('contributionId', contribution.contributionId)
  if (contribution.projectId !== input.correlation.projectId) {
    throw new Error(
      `Project Supervision Contribution project mismatch: ${contribution.projectId}`,
    )
  }
  if (contribution.taskId !== input.correlation.taskId) {
    throw new Error(
      `Project Supervision Contribution task mismatch: ${contribution.taskId}`,
    )
  }
  assertBoundedReference('contribution.provenance', contribution.provenance)
  if (!Array.isArray(contribution.obligations)) {
    throw new Error('Project Supervision Contribution obligations must be an array')
  }
  for (const obligation of contribution.obligations) {
    if (Object.values(PUBLIC_LIFECYCLE_OBLIGATION_IDS).includes(obligation.obligationId)) {
      throw new Error(
        `Project Contribution cannot override public lifecycle obligation ${obligation.obligationId}`,
      )
    }
    if (obligation.sourceRefs.length === 0) {
      throw new Error(
        `Project obligation ${obligation.obligationId} requires at least one routed or contributed sourceRef`,
      )
    }
    for (const reference of obligation.sourceRefs) {
      const normalized = assertBoundedReference(
        `obligation ${obligation.obligationId} sourceRef`,
        reference,
      )
      if (!authorizedSourceRefs.has(normalized)) {
        throw new Error(
          `Project obligation ${obligation.obligationId} references unauthorized source ${normalized}`,
        )
      }
    }
  }
}

const stableObligationCopy = (obligation: ObligationSpec): ObligationSpec => ({
  ...obligation,
  sourceRefs: uniqueSorted(obligation.sourceRefs),
  ...(obligation.dependsOn
    ? { dependsOn: uniqueSorted(obligation.dependsOn) }
    : {}),
  evidencePolicy: {
    ...obligation.evidencePolicy,
    acceptableAuthorities: uniqueSorted(
      obligation.evidencePolicy.acceptableAuthorities,
    ) as EvidenceAuthority[],
    acceptedOutcomes: uniqueSorted(
      obligation.evidencePolicy.acceptedOutcomes,
    ) as EvidenceOutcome[],
  },
  ...(obligation.target
    ? {
        target: {
          ...obligation.target,
          ...(obligation.target.resourceRefs
            ? { resourceRefs: uniqueSorted(obligation.target.resourceRefs) }
            : {}),
          ...(obligation.target.pathPatterns
            ? { pathPatterns: uniqueSorted(obligation.target.pathPatterns) }
            : {}),
          ...(obligation.target.outputIds
            ? { outputIds: uniqueSorted(obligation.target.outputIds) }
            : {}),
          ...(obligation.target.validationIds
            ? { validationIds: uniqueSorted(obligation.target.validationIds) }
            : {}),
          ...(obligation.target.claimIds
            ? { claimIds: uniqueSorted(obligation.target.claimIds) }
            : {}),
        },
      }
    : {}),
})

const buildReceipt = (
  contract: TaskSupervisionContract,
  contributionIds: readonly string[],
  authorizedSourceRefs: readonly string[],
  projectObligationCount: number,
  publicLifecycleObligationCount: number,
): TaskSupervisionBuildReceipt => {
  const unsigned: Omit<TaskSupervisionBuildReceipt, 'receiptHash'> = {
    schema: TASK_SUPERVISION_BUILD_RECEIPT_SCHEMA,
    contractVersion: EXECUTION_SUPERVISOR_CONTRACT_VERSION,
    builderVersion: EXECUTION_SUPERVISOR_BUILDER_VERSION,
    supervisionId: contract.correlation.supervisionId,
    projectId: contract.correlation.projectId,
    taskId: contract.correlation.taskId,
    turnId: contract.correlation.turnId,
    mode: contract.mode,
    contractHash: contract.contractHash,
    contributionIds: uniqueSorted(contributionIds),
    authorizedSourceRefsHash: sha256Canonical(uniqueSorted(authorizedSourceRefs)),
    projectObligationCount,
    publicLifecycleObligationCount,
    totalObligationCount: contract.obligations.length,
  }
  return {
    ...unsigned,
    receiptHash: sha256Canonical(unsigned),
  }
}

export const buildTaskSupervisionContract = (
  input: TaskSupervisionBuildInput,
): TaskSupervisionBuildResult => {
  assertCorrelation(input.correlation)
  assertBinding(input.binding)
  assertHostCapabilities(input.requestedMode, input.hostCapabilities)
  if (
    input.projectContributions.length
      > EXECUTION_SUPERVISOR_LIMITS.maxProjectContributions
  ) {
    throw new Error(
      `Project contributions exceed maximum ${EXECUTION_SUPERVISOR_LIMITS.maxProjectContributions}`,
    )
  }
  if (
    input.authorizedSourceRefs.length
      > EXECUTION_SUPERVISOR_LIMITS.maxAuthorizedSourceRefs
  ) {
    throw new Error(
      `Authorized source refs exceed maximum ${EXECUTION_SUPERVISOR_LIMITS.maxAuthorizedSourceRefs}`,
    )
  }
  const authorizedSourceRefs = uniqueSorted(
    input.authorizedSourceRefs.map((reference, index) =>
      assertBoundedReference(`authorizedSourceRefs[${index}]`, reference),
    ),
  )
  if (authorizedSourceRefs.length !== input.authorizedSourceRefs.length) {
    throw new Error('authorizedSourceRefs must be unique and non-empty')
  }
  const authorizedSourceSet = new Set(authorizedSourceRefs)
  const contributionIds = new Set<string>()
  let requireFollowUpReuse = false
  const projectObligations: ObligationSpec[] = []

  for (const contribution of input.projectContributions) {
    assertProjectContribution(contribution, input, authorizedSourceSet)
    if (contributionIds.has(contribution.contributionId)) {
      throw new Error(
        `Duplicate Project Supervision Contribution: ${contribution.contributionId}`,
      )
    }
    contributionIds.add(contribution.contributionId)
    requireFollowUpReuse ||= contribution.requireFollowUpReuse === true
    projectObligations.push(...contribution.obligations.map(stableObligationCopy))
  }

  const publicObligations = publicLifecycleObligations(requireFollowUpReuse)
  const allObligations = [...projectObligations, ...publicObligations]
    .sort((left, right) => left.obligationId.localeCompare(right.obligationId))
  if (allObligations.length > EXECUTION_SUPERVISOR_LIMITS.maxObligations) {
    throw new Error(
      `Task Supervision Contract exceeds maximum ${EXECUTION_SUPERVISOR_LIMITS.maxObligations} obligations`,
    )
  }

  const contract = assertValidTaskSupervisionContract(
    createTaskSupervisionContract({
      mode: input.requestedMode,
      correlation: input.correlation,
      binding: input.binding,
      obligations: allObligations,
      completionPolicy: {
        requiredLevels: ['MUST'],
        blockingViolationSeverities: ['BLOCKING'],
        requireReflection: true,
        requireKnowledgeClassification: true,
        requireContextClosure: true,
        requireKnowledgeClosure: true,
        requireTurnClosure: true,
        requireFollowUpReuse,
      },
      efficiencyPolicy: {
        ingestion: 'INCREMENTAL',
        maxBatchEvents: Math.min(
          Math.max(Math.floor(input.maxBatchEvents ?? 128), 1),
          EXECUTION_SUPERVISOR_LIMITS.maxBatchEvents,
        ),
        hotPathLlmAllowed: false,
        hotPathNetworkAllowed: false,
        hotPathProjectFileReadsAllowed: false,
        fullRerouteTriggers: [
          'PROJECT_BINDING_CHANGED',
          'TASK_CONTRACT_CHANGED',
          'MUTATING_ACTION',
          'EXPLICIT_FRAMEWORK_REQUEST',
        ],
        semanticCheckpoints: [
          'TURN_CLOSING',
          'BLOCKING_CONFLICT',
          'EXPLICIT_FRAMEWORK_REQUEST',
        ],
      },
    }),
  )

  return {
    contract,
    receipt: buildReceipt(
      contract,
      [...contributionIds],
      authorizedSourceRefs,
      projectObligations.length,
      publicObligations.length,
    ),
  }
}
