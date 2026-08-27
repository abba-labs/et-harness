import { createHash } from 'node:crypto'
import {
  TURN_REFLECTION_CONTRACT_VERSION,
  type KnowledgeVerificationReflection,
  type ProjectBinding,
  type ReflectionCandidate,
  type ReflectionCandidateScope,
  type ReflectionDomain,
  type ReflectionScopeDecision,
  type ScopedReflectionSection,
  type TurnJournalRecord,
  type TurnReflectionProviderInput,
  type TurnReflectionResult,
} from './contracts.js'

const SCOPES = new Set<ReflectionScopeDecision>(['NONE', 'PROJECT', 'PUBLIC', 'BOTH'])
const CANDIDATE_SCOPES = new Set<ReflectionCandidateScope>(['PROJECT', 'PUBLIC', 'BOTH'])
const DOMAINS = ['knowledge', 'experience', 'architecture', 'rules', 'evidence'] as const satisfies readonly ReflectionDomain[]
const KNOWLEDGE_VERIFICATION_RELATIONS = new Set(['SUPPORT', 'CONTRADICT'])

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

const asString = (value: unknown, path: string): string => {
  if (typeof value !== 'string' || !value.trim()) throw new Error(`${path} must be a non-empty string`)
  return value.trim()
}

const asStringArray = (value: unknown, path: string): string[] => {
  if (!Array.isArray(value) || value.some(item => typeof item !== 'string' || !item.trim())) {
    throw new Error(`${path} must be an array of non-empty strings`)
  }
  return [...new Set(value.map(item => item.trim()))]
}

const asConfidence = (value: unknown, path: string): number => {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > 1) {
    throw new Error(`${path} must be a number in [0, 1]`)
  }
  return value
}

const candidate = (value: unknown, expectedDomain: ReflectionDomain, path: string): ReflectionCandidate => {
  if (!isRecord(value)) throw new Error(`${path} must be an object`)
  const domain = asString(value.domain, `${path}.domain`) as ReflectionDomain
  if (!DOMAINS.includes(domain)) throw new Error(`${path}.domain is unsupported: ${domain}`)
  if (domain !== expectedDomain) throw new Error(`${path}.domain must be ${expectedDomain}`)
  const scopeDecision = asString(value.scopeDecision, `${path}.scopeDecision`) as ReflectionCandidateScope
  if (!CANDIDATE_SCOPES.has(scopeDecision)) throw new Error(`${path}.scopeDecision must be PROJECT, PUBLIC or BOTH`)
  return {
    domain,
    title: asString(value.title, `${path}.title`),
    factOrProposal: asString(value.factOrProposal, `${path}.factOrProposal`),
    scopeDecision,
    rationale: asString(value.rationale, `${path}.rationale`),
    provenanceRefs: asStringArray(value.provenanceRefs, `${path}.provenanceRefs`),
    evidenceRefs: asStringArray(value.evidenceRefs, `${path}.evidenceRefs`),
    relatedRefs: asStringArray(value.relatedRefs, `${path}.relatedRefs`),
    confidence: asConfidence(value.confidence, `${path}.confidence`),
  }
}

const knowledgeVerification = (value: unknown, path: string): KnowledgeVerificationReflection => {
  if (!isRecord(value)) throw new Error(`${path} must be an object`)
  const relation = asString(value.relation, `${path}.relation`)
  if (!KNOWLEDGE_VERIFICATION_RELATIONS.has(relation)) {
    throw new Error(`${path}.relation must be SUPPORT or CONTRADICT`)
  }
  const basisRefs = asStringArray(value.basisRefs, `${path}.basisRefs`)
  if (basisRefs.length === 0) throw new Error(`${path}.basisRefs must not be empty`)
  for (const basisRef of basisRefs) {
    if (!basisRef.startsWith('source://') && !basisRef.startsWith('evidence://')) {
      throw new Error(`${path}.basisRefs only supports source:// or evidence:// references`)
    }
  }
  return {
    knowledgeRef: asString(value.knowledgeRef, `${path}.knowledgeRef`),
    relation: relation as KnowledgeVerificationReflection['relation'],
    basisRefs,
    rationale: asString(value.rationale, `${path}.rationale`),
  }
}

const expectedSectionScope = (items: readonly ReflectionCandidate[]): ReflectionScopeDecision => {
  if (items.length === 0) return 'NONE'
  let project = false
  let publicScope = false
  for (const item of items) {
    if (item.scopeDecision === 'PROJECT' || item.scopeDecision === 'BOTH') project = true
    if (item.scopeDecision === 'PUBLIC' || item.scopeDecision === 'BOTH') publicScope = true
  }
  if (project && publicScope) return 'BOTH'
  return project ? 'PROJECT' : 'PUBLIC'
}

const section = (
  value: unknown,
  domain: ReflectionDomain,
  binding: ProjectBinding,
): ScopedReflectionSection => {
  if (!isRecord(value)) throw new Error(`${domain} reflection section is required`)
  const scopeDecision = asString(value.scopeDecision, `${domain}.scopeDecision`) as ReflectionScopeDecision
  if (!SCOPES.has(scopeDecision)) throw new Error(`${domain}.scopeDecision is invalid`)
  const rationale = asString(value.rationale, `${domain}.rationale`)
  if (!Array.isArray(value.candidates)) throw new Error(`${domain}.candidates must be an array`)
  const candidates = value.candidates.map((item, index) => candidate(item, domain, `${domain}.candidates[${index}]`))
  const expected = expectedSectionScope(candidates)
  if (scopeDecision !== expected) {
    throw new Error(`${domain}.scopeDecision ${scopeDecision} does not match candidates (${expected})`)
  }
  if (binding.kind === 'UNBOUND' && candidates.some(item => item.scopeDecision !== 'PUBLIC')) {
    throw new Error(`${domain} cannot emit PROJECT/BOTH candidates while the Turn is UNBOUND`)
  }
  return { scopeDecision, rationale, candidates }
}

export function validateTurnReflectionResult(
  value: unknown,
  journal: TurnJournalRecord,
): TurnReflectionResult {
  if (!isRecord(value)) throw new Error('TurnReflectionResult must be an object')
  if (value.contractVersion !== TURN_REFLECTION_CONTRACT_VERSION) {
    throw new Error(`Unsupported TurnReflectionResult contractVersion: ${String(value.contractVersion)}`)
  }
  if (asString(value.taskId, 'taskId') !== journal.taskId) throw new Error('Reflection taskId does not match Journal')
  if (asString(value.turnId, 'turnId') !== journal.turnId) throw new Error('Reflection turnId does not match Journal')

  if (!isRecord(value.context)) throw new Error('context reflection section is required')
  const context = {
    progress: asString(value.context.progress, 'context.progress'),
    decisions: asStringArray(value.context.decisions, 'context.decisions'),
    confirmed: asStringArray(value.context.confirmed, 'context.confirmed'),
    assumptions: asStringArray(value.context.assumptions, 'context.assumptions'),
    openIssues: asStringArray(value.context.openIssues, 'context.openIssues'),
    next: asStringArray(value.context.next, 'context.next'),
    touchedRefs: asStringArray(value.context.touchedRefs, 'context.touchedRefs'),
  }

  if (!isRecord(value.workingSet)) throw new Error('workingSet reflection section is required')
  const workingSet = {
    keep: asStringArray(value.workingSet.keep, 'workingSet.keep'),
    add: asStringArray(value.workingSet.add, 'workingSet.add'),
    remove: asStringArray(value.workingSet.remove, 'workingSet.remove'),
  }

  if (!isRecord(value.obligations)) throw new Error('obligations reflection section is required')
  const obligations = {
    opened: asStringArray(value.obligations.opened, 'obligations.opened'),
    resolved: asStringArray(value.obligations.resolved, 'obligations.resolved'),
    unchanged: asStringArray(value.obligations.unchanged, 'obligations.unchanged'),
  }

  const rawKnowledgeVerifications = value.knowledgeVerifications ?? []
  if (!Array.isArray(rawKnowledgeVerifications)) {
    throw new Error('knowledgeVerifications must be an array')
  }
  const knowledgeVerifications = rawKnowledgeVerifications.map((item, index) =>
    knowledgeVerification(item, `knowledgeVerifications[${index}]`),
  )

  return {
    contractVersion: TURN_REFLECTION_CONTRACT_VERSION,
    taskId: journal.taskId,
    turnId: journal.turnId,
    context,
    knowledge: section(value.knowledge, 'knowledge', journal.projectBinding),
    knowledgeVerifications,
    experience: section(value.experience, 'experience', journal.projectBinding),
    architecture: section(value.architecture, 'architecture', journal.projectBinding),
    rules: section(value.rules, 'rules', journal.projectBinding),
    evidence: section(value.evidence, 'evidence', journal.projectBinding),
    workingSet,
    obligations,
  }
}

const sorted = (values: readonly string[]): string[] => [...new Set(values)].sort()

export function reflectionInputFingerprint(input: TurnReflectionProviderInput): string {
  const journal = input.journal
  const stable = {
    contractVersion: journal.contractVersion,
    taskId: journal.taskId,
    turnId: journal.turnId,
    agentId: journal.agentId,
    projectBinding: journal.projectBinding,
    startedAt: journal.startedAt,
    closingAt: journal.closingAt,
    userMessageRefs: sorted(journal.userMessageRefs),
    assistantMessageRefs: sorted(journal.assistantMessageRefs),
    toolEventRefs: sorted(journal.toolEventRefs),
    resourceTouchRefs: sorted(journal.resourceTouchRefs),
    stateVersionBefore: journal.stateVersionBefore,
    sessionRef: journal.sessionRef,
    taskContextRef: input.taskContextRef,
    publicCandidateRefs: sorted(input.publicCandidateRefs),
    projectCandidateRefs: sorted(input.projectCandidateRefs),
  }
  return `sha256:${createHash('sha256').update(JSON.stringify(stable)).digest('hex')}`
}
