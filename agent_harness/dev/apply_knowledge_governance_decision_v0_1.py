from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str) -> str:
    return (ROOT / rel).read_text(encoding='utf-8')


def save(rel: str, text: str) -> None:
    (ROOT / rel).write_text(text, encoding='utf-8')


def replace_once(rel: str, old: str, new: str) -> None:
    text = load(rel)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{rel}: expected exactly one replacement, found {count}: {old[:80]!r}')
    save(rel, text.replace(old, new, 1))


def replace_all(rel: str, old: str, new: str, expected_min: int = 1) -> None:
    text = load(rel)
    count = text.count(old)
    if count < expected_min:
        raise RuntimeError(f'{rel}: expected at least {expected_min} replacements, found {count}: {old[:80]!r}')
    save(rel, text.replace(old, new))


# ---------------------------------------------------------------------------
# Knowledge status / source / verification contracts
# ---------------------------------------------------------------------------
rel = 'agent_harness/public_plugins/knowledge_manager/src/contracts.ts'
replace_once(
    rel,
    "export type KnowledgeStatus = 'CANDIDATE' | 'VALIDATED' | 'DEPRECATED'",
    "export type KnowledgeStatus = 'CANDIDATE' | 'VALIDATED' | 'FULL_VALIDATED' | 'DEPRECATED'",
)
replace_once(
    rel,
    "export type KnowledgeSourceKind = 'DOCUMENT' | 'SPEC' | 'CODE' | 'RTL' | 'WEB' | 'OTHER'",
    "export type KnowledgeSourceKind = 'DOCUMENT' | 'SPEC' | 'SVD' | 'CODE' | 'RTL' | 'WEB' | 'OTHER'",
)
replace_once(
    rel,
    "export type KnowledgeVerificationBasisKind = 'SOURCE' | 'EVIDENCE'\n",
    "export type KnowledgeVerificationBasisKind = 'SOURCE' | 'EVIDENCE'\n"
    "export type KnowledgeVerificationValidationClass = 'REFERENCE' | 'DOCUMENT' | 'REAL_TEST'\n",
)
replace_once(
    rel,
    "  readonly basisKind: KnowledgeVerificationBasisKind\n  readonly knowledgeFingerprint: string\n",
    "  readonly basisKind: KnowledgeVerificationBasisKind\n"
    "  readonly validationClass: KnowledgeVerificationValidationClass\n"
    "  readonly knowledgeFingerprint: string\n",
)
replace_once(
    rel,
    "  readonly distinctSupportCount: number\n  readonly contradictCount: number\n  readonly reasons: readonly string[]\n",
    "  readonly distinctSupportCount: number\n"
    "  readonly documentSupportCount: number\n"
    "  readonly realTestSupportCount: number\n"
    "  readonly contradictCount: number\n"
    "  readonly targetStatus?: Extract<KnowledgeStatus, 'VALIDATED' | 'FULL_VALIDATED'>\n"
    "  readonly reasons: readonly string[]\n",
)

rel = 'agent_harness/public_plugins/knowledge_manager/src/knowledge-parser.ts'
replace_once(
    rel,
    "const VALID_STATUSES = new Set<KnowledgeStatus>(['CANDIDATE', 'VALIDATED', 'DEPRECATED'])",
    "const VALID_STATUSES = new Set<KnowledgeStatus>(['CANDIDATE', 'VALIDATED', 'FULL_VALIDATED', 'DEPRECATED'])",
)
replace_once(
    rel,
    "`${fileName} Knowledge Leaf ${node.id} 缺少合法 Status: CANDIDATE | VALIDATED | DEPRECATED`,",
    "`${fileName} Knowledge Leaf ${node.id} 缺少合法 Status: CANDIDATE | VALIDATED | FULL_VALIDATED | DEPRECATED`,",
)

rel = 'agent_harness/public_plugins/knowledge_manager/src/knowledge-manager-engine.ts'
replace_once(
    rel,
    "const VALID_STATUSES = new Set<KnowledgeStatus>(['CANDIDATE', 'VALIDATED', 'DEPRECATED'])",
    "const VALID_STATUSES = new Set<KnowledgeStatus>(['CANDIDATE', 'VALIDATED', 'FULL_VALIDATED', 'DEPRECATED'])",
)
replace_once(
    rel,
    "if (raw === undefined) return new Set<KnowledgeStatus>(['VALIDATED'])",
    "if (raw === undefined) return new Set<KnowledgeStatus>(['VALIDATED', 'FULL_VALIDATED'])",
)
replace_all(
    rel,
    "      CANDIDATE: 0,\n      VALIDATED: 0,\n      DEPRECATED: 0,",
    "      CANDIDATE: 0,\n      VALIDATED: 0,\n      FULL_VALIDATED: 0,\n      DEPRECATED: 0,",
)

# ---------------------------------------------------------------------------
# Verification class persistence
# ---------------------------------------------------------------------------
rel = 'agent_harness/public_plugins/knowledge_manager/src/source-verification-store.ts'
replace_once(
    rel,
    "  KnowledgeVerificationInput,\n  KnowledgeVerificationRecord,",
    "  KnowledgeVerificationInput,\n  KnowledgeVerificationRecord,\n  KnowledgeVerificationValidationClass,",
)
replace_once(
    rel,
    "const VALID_SOURCE_KINDS = new Set<KnowledgeSourceKind>(['DOCUMENT', 'SPEC', 'CODE', 'RTL', 'WEB', 'OTHER'])",
    "const VALID_SOURCE_KINDS = new Set<KnowledgeSourceKind>(['DOCUMENT', 'SPEC', 'SVD', 'CODE', 'RTL', 'WEB', 'OTHER'])",
)
replace_once(
    rel,
    "    basisKind: KnowledgeVerificationBasisKind,\n    knowledgeFingerprint?: string,\n  ): KnowledgeVerificationRecord {",
    "    basisKind: KnowledgeVerificationBasisKind,\n"
    "    knowledgeFingerprint?: string,\n"
    "    validationClass: KnowledgeVerificationValidationClass = 'REFERENCE',\n"
    "  ): KnowledgeVerificationRecord {",
)
replace_once(
    rel,
    "      basisKind,\n      knowledgeFingerprint: line('knowledgeFingerprint', fingerprint),",
    "      basisKind,\n      validationClass,\n      knowledgeFingerprint: line('knowledgeFingerprint', fingerprint),",
)
replace_once(
    rel,
    "          knowledgeFingerprint: typeof value.knowledgeFingerprint === 'string'\n            ? value.knowledgeFingerprint\n            : 'legacy:unbound',",
    "          validationClass: value.validationClass === 'DOCUMENT' || value.validationClass === 'REAL_TEST'\n"
    "            ? value.validationClass\n"
    "            : 'REFERENCE',\n"
    "          knowledgeFingerprint: typeof value.knowledgeFingerprint === 'string'\n"
    "            ? value.knowledgeFingerprint\n"
    "            : 'legacy:unbound',",
)

rel = 'agent_harness/public_plugins/knowledge_manager/src/service.ts'
replace_once(
    rel,
    "  KnowledgeVerificationRecord,\n  KnowledgeVerificationSummary,",
    "  KnowledgeVerificationRecord,\n  KnowledgeVerificationSummary,\n  KnowledgeVerificationValidationClass,",
)
replace_once(
    rel,
    "    let basisKind: 'SOURCE' | 'EVIDENCE'\n    if (input.basisRef.startsWith('source://')) {",
    "    let basisKind: 'SOURCE' | 'EVIDENCE'\n"
    "    let validationClass: KnowledgeVerificationValidationClass = 'REFERENCE'\n"
    "    if (input.basisRef.startsWith('source://')) {",
)
replace_once(
    rel,
    "      this.assertSourceCanVerify(target.libraryScope, sourceRef.scope)\n      basisKind = 'SOURCE'",
    "      this.assertSourceCanVerify(target.libraryScope, sourceRef.scope)\n"
    "      basisKind = 'SOURCE'\n"
    "      validationClass = source.source.kind === 'DOCUMENT' || source.source.kind === 'SPEC' || source.source.kind === 'SVD'\n"
    "        ? 'DOCUMENT'\n"
    "        : 'REFERENCE'",
)
replace_once(
    rel,
    "      if (!evidence) throw new Error(`Verification Evidence 不存在: ${input.basisRef}`)\n      basisKind = 'EVIDENCE'",
    "      if (!evidence) throw new Error(`Verification Evidence 不存在: ${input.basisRef}`)\n"
    "      basisKind = 'EVIDENCE'\n"
    "      const evidenceRecord = evidence as { result?: unknown; metadata?: unknown }\n"
    "      const metadata = evidenceRecord.metadata && typeof evidenceRecord.metadata === 'object'\n"
    "        ? evidenceRecord.metadata as Record<string, unknown>\n"
    "        : {}\n"
    "      validationClass = evidenceRecord.result === 'PASS'\n"
    "        && (metadata.knowledgeValidationClass === 'REAL_TEST' || metadata.validationClass === 'REAL_TEST')\n"
    "        ? 'REAL_TEST'\n"
    "        : 'REFERENCE'",
)
replace_once(
    rel,
    "    return this.sourceStore(target.libraryScope).appendVerification(input, basisKind)",
    "    return this.sourceStore(target.libraryScope).appendVerification(\n"
    "      input,\n"
    "      basisKind,\n"
    "      undefined,\n"
    "      validationClass,\n"
    "    )",
)

# ---------------------------------------------------------------------------
# Validation policy + promotion tiers
# ---------------------------------------------------------------------------
rel = 'agent_harness/public_plugins/knowledge_manager/src/validation-policy.ts'
text = load(rel)
start = text.index('export function evaluateKnowledgeValidationPolicy')
new_fn = r'''export function evaluateKnowledgeValidationPolicy(input: {
  readonly knowledgeUri: string
  readonly libraryScope: KnowledgeLibraryScope
  readonly currentStatus: KnowledgeStatus
  readonly knowledgeFingerprint: string
  readonly records: readonly KnowledgeVerificationRecord[]
}): KnowledgeValidationEvaluation {
  const currentRecords = input.records.filter(
    record => record.knowledgeFingerprint === input.knowledgeFingerprint,
  )
  const supports = currentRecords.filter(record => record.relation === 'SUPPORT')
  const contradictions = currentRecords.filter(record => record.relation === 'CONTRADICT')
  const distinctSupportCount = new Set(supports.map(record => record.basisRef)).size
  const documentSupportCount = new Set(
    supports.filter(record => record.validationClass === 'DOCUMENT').map(record => record.basisRef),
  ).size
  const realTestSupportCount = new Set(
    supports.filter(record => record.validationClass === 'REAL_TEST').map(record => record.basisRef),
  ).size
  const requiredSupportCount = input.libraryScope.kind === 'global' ? 2 : 1
  const reasons: string[] = []

  let decision: KnowledgeValidationEvaluation['decision']
  let targetStatus: KnowledgeValidationEvaluation['targetStatus']
  if (input.currentStatus === 'DEPRECATED') {
    decision = 'BLOCKED'
    reasons.push('DEPRECATED Knowledge 不允许晋级')
  } else if (input.currentStatus === 'FULL_VALIDATED') {
    decision = 'BLOCKED'
    reasons.push('FULL_VALIDATED 已是最高验证等级')
  } else if (contradictions.length > 0) {
    decision = 'BLOCKED'
    reasons.push(`存在 ${contradictions.length} 条当前 Claim 的 CONTRADICT；不得自动晋级`)
  } else if (realTestSupportCount >= 1) {
    decision = 'READY'
    targetStatus = 'FULL_VALIDATED'
    reasons.push('存在实际验证 PASS Evidence，可晋级 FULL_VALIDATED')
  } else if (input.currentStatus === 'VALIDATED') {
    decision = 'INSUFFICIENT'
    reasons.push('已是文档验证级 VALIDATED；尚缺实际验证 Evidence')
  } else if (documentSupportCount >= requiredSupportCount) {
    decision = 'READY'
    targetStatus = 'VALIDATED'
    reasons.push(
      `${input.libraryScope.kind === 'global' ? 'Global' : 'Project'} Knowledge 已满足 ${requiredSupportCount} 个文档级 SUPPORT`,
    )
  } else {
    decision = 'INSUFFICIENT'
    reasons.push(`当前只有 ${documentSupportCount}/${requiredSupportCount} 个文档级 SUPPORT，且无实际验证 Evidence`)
  }

  const staleCount = input.records.length - currentRecords.length
  if (staleCount > 0) reasons.push(`${staleCount} 条旧 Claim Verification 不计入当前判断`)

  return {
    knowledgeUri: input.knowledgeUri,
    libraryScope: input.libraryScope,
    currentStatus: input.currentStatus,
    knowledgeFingerprint: input.knowledgeFingerprint,
    decision,
    requiredSupportCount,
    distinctSupportCount,
    documentSupportCount,
    realTestSupportCount,
    contradictCount: contradictions.length,
    ...(targetStatus ? { targetStatus } : {}),
    reasons,
    records: currentRecords,
  }
}
'''
save(rel, text[:start] + new_fn)

rel = 'agent_harness/public_plugins/knowledge_manager/src/knowledge-promotion.ts'
text = load(rel)
start = text.index('export function promoteKnowledgeCandidate')
prefix = text[:start]
new_tail = r'''export function promoteKnowledgeStatus(input: {
  readonly engine: KnowledgeManagerEngine
  readonly libraryKey: string
  readonly root: string
  readonly knowledgeId: string
  readonly targetStatus: 'VALIDATED' | 'FULL_VALIDATED'
  readonly reindex: () => KnowledgeProjectIndex
}): KnowledgeMutationResult {
  const node = input.engine.getNode(input.libraryKey, input.knowledgeId)?.node
  if (!node?.isLeaf || !node.category || !node.status) {
    throw new Error(`Knowledge 不存在: ${input.knowledgeId}`)
  }
  const validTransition = (node.status === 'CANDIDATE'
      && (input.targetStatus === 'VALIDATED' || input.targetStatus === 'FULL_VALIDATED'))
    || (node.status === 'VALIDATED' && input.targetStatus === 'FULL_VALIDATED')
  if (!validTransition) {
    throw new Error(`非法 Knowledge 晋级: ${node.status} -> ${input.targetStatus}: ${input.knowledgeId}`)
  }
  const route = input.engine.listFiles(input.libraryKey).find(file => file.id === node.fileId)
  if (!route) throw new Error(`Knowledge File 不存在: ${node.fileId}`)
  const file = join(input.root, route.file)
  const original = readFileSync(file, 'utf-8')

  atomicWrite(file, replaceStatus(original, input.knowledgeId, input.targetStatus))
  try {
    const snapshot = input.reindex()
    const promoted = input.engine.getNode(input.libraryKey, input.knowledgeId)?.node
    if (!promoted?.isLeaf || promoted.status !== input.targetStatus) {
      throw new Error(`Knowledge 晋级后未得到 ${input.targetStatus}: ${input.knowledgeId}`)
    }
    return {
      knowledgeId: input.knowledgeId,
      file: route.file,
      status: promoted.status,
      categoryId: promoted.category ?? node.category,
      ...(snapshot.sourceFingerprint ? { sourceFingerprint: snapshot.sourceFingerprint } : {}),
    }
  } catch (error) {
    atomicWrite(file, original)
    try { input.reindex() } catch { /* preserve original error */ }
    throw error
  }
}

/** Backward-compatible document-level promotion helper. */
export function promoteKnowledgeCandidate(input: {
  readonly engine: KnowledgeManagerEngine
  readonly libraryKey: string
  readonly root: string
  readonly knowledgeId: string
  readonly reindex: () => KnowledgeProjectIndex
}): KnowledgeMutationResult {
  return promoteKnowledgeStatus({ ...input, targetStatus: 'VALIDATED' })
}
'''
save(rel, prefix + new_tail)

rel = 'agent_harness/public_plugins/knowledge_manager/src/validation-service.ts'
replace_once(
    rel,
    "import { promoteKnowledgeCandidate } from './knowledge-promotion.js'",
    "import { promoteKnowledgeStatus } from './knowledge-promotion.js'",
)
replace_once(
    rel,
    "        if (node.status !== 'CANDIDATE') throw new Error(`只有 CANDIDATE 可以晋级: ${target.knowledgeUri}`)\n\n        const evaluation = this.evaluate(target.knowledgeUri)\n        if (evaluation.decision !== 'READY') {",
    "        if (node.status !== 'CANDIDATE' && node.status !== 'VALIDATED') {\n"
    "          throw new Error(`只有 CANDIDATE / VALIDATED 可以晋级: ${target.knowledgeUri}`)\n"
    "        }\n\n"
    "        const evaluation = this.evaluate(target.knowledgeUri)\n"
    "        if (evaluation.decision !== 'READY' || !evaluation.targetStatus) {",
)
replace_once(
    rel,
    "        const mutation = promoteKnowledgeCandidate({\n          engine: localEngine,\n          libraryKey,\n          root,\n          knowledgeId: node.id,\n          reindex: () => localEngine.reindexProject(libraryKey, root, resourceHandle),\n        })",
    "        const mutation = promoteKnowledgeStatus({\n"
    "          engine: localEngine,\n"
    "          libraryKey,\n"
    "          root,\n"
    "          knowledgeId: node.id,\n"
    "          targetStatus: evaluation.targetStatus,\n"
    "          reindex: () => localEngine.reindexProject(libraryKey, root, resourceHandle),\n"
    "        })",
)
replace_once(
    rel,
    "        outcome: result.mutation.status === 'VALIDATED' ? 'PASS' : 'FAIL',\n        values: { promotionCount: result.mutation.status === 'VALIDATED' ? 1 : 0 },",
    "        outcome: result.mutation.status === result.evaluation.targetStatus ? 'PASS' : 'FAIL',\n"
    "        values: { promotionCount: result.mutation.status === result.evaluation.targetStatus ? 1 : 0 },",
)

# ---------------------------------------------------------------------------
# Knowledge Governance Decision pure policy (mixed deterministic + Reflection)
# ---------------------------------------------------------------------------
decision_file = ROOT / 'agent_harness/public_plugins/governance_runtime/src/knowledge-governance-decision.ts'
decision_file.write_text(r'''import type { TurnReflectionResult } from '@agent-harness/agent-governance-kernel'
import type { AutoGovernanceContextEnvelope } from '@agent-harness/auto-governance-engine'
import type {
  GovernanceKnowledgeDecision,
  GovernanceTurnObservation,
} from './contracts.js'

const unique = (values: readonly string[]): string[] =>
  [...new Set(values.map(value => value.trim()).filter(Boolean))]

const rankConsult = { NONE: 0, OPTIONAL: 1, REQUIRED: 2 } as const
const rankCapture = { NONE: 0, CHECK: 1, REQUIRED: 2 } as const
const rankValidation = { NONE: 0, DOCUMENT: 1, EVIDENCE_CHECK: 2, REAL_TEST: 3 } as const

const maxByRank = <T extends string>(left: T, right: T, rank: Readonly<Record<T, number>>): T =>
  rank[right] > rank[left] ? right : left

const refsFromCandidate = (candidate: TurnReflectionResult['knowledge']['candidates'][number]): string[] =>
  unique([...candidate.provenanceRefs, ...candidate.evidenceRefs, ...candidate.relatedRefs])

export function evaluateKnowledgeGovernanceDecision(input: {
  readonly stage: GovernanceKnowledgeDecision['stage']
  readonly context: AutoGovernanceContextEnvelope
  readonly observations: readonly GovernanceTurnObservation[]
  readonly reflection?: TurnReflectionResult
}): GovernanceKnowledgeDecision {
  let consultMode: GovernanceKnowledgeDecision['consultMode'] = 'NONE'
  let captureMode: GovernanceKnowledgeDecision['captureMode'] = 'NONE'
  let validationMode: GovernanceKnowledgeDecision['validationMode'] = 'NONE'
  const deterministicSignals: string[] = []
  const semanticSignals: string[] = []
  const reasons: string[] = []

  if (input.context.route.knowledgeIds.length > 0) {
    consultMode = 'OPTIONAL'
    deterministicSignals.push('ROUTED_KNOWLEDGE_AVAILABLE')
    reasons.push('Knowledge Router found relevant validated knowledge; Agent may use it when helpful.')
  }
  if (input.context.applicableGateIds.length > 0
      && (input.context.route.architectureIds.length > 0 || input.context.route.ruleIds.length > 0)
      && input.context.route.knowledgeIds.length > 0) {
    consultMode = 'REQUIRED'
    deterministicSignals.push('GOVERNED_CHANGE_WITH_KNOWLEDGE')
    reasons.push('Governed architecture/rule/gate work has relevant knowledge; consideration is required, acceptance is not.')
  }

  for (const observation of input.observations) {
    const refs = observation.refs
    if (refs.some(ref => ref.startsWith('source://'))) {
      captureMode = maxByRank(captureMode, 'CHECK', rankCapture)
      validationMode = maxByRank(validationMode, 'DOCUMENT', rankValidation)
      deterministicSignals.push('DOCUMENT_SOURCE_OBSERVED')
    }
    if (refs.some(ref => ref.startsWith('evidence://'))) {
      captureMode = maxByRank(captureMode, 'CHECK', rankCapture)
      validationMode = maxByRank(validationMode, 'EVIDENCE_CHECK', rankValidation)
      deterministicSignals.push('EVIDENCE_OBSERVED')
    }
    if (observation.kind === 'TOOL_RESULT' && observation.isError) {
      captureMode = maxByRank(captureMode, 'CHECK', rankCapture)
      deterministicSignals.push('TOOL_ERROR_OBSERVED')
    }
  }

  const knowledge = input.reflection?.knowledge
  if (knowledge) {
    if (knowledge.scopeDecision !== 'NONE' || knowledge.candidates.length > 0) {
      captureMode = maxByRank(captureMode, 'CHECK', rankCapture)
      semanticSignals.push('REFLECTION_RECOMMENDS_KNOWLEDGE_CAPTURE')
      reasons.push('Unified Reflection identified a possible durable knowledge contribution.')
    } else {
      semanticSignals.push('REFLECTION_RECOMMENDS_NO_KNOWLEDGE')
    }
    for (const candidate of knowledge.candidates) {
      const refs = refsFromCandidate(candidate)
      if (refs.some(ref => ref.startsWith('source://'))) {
        validationMode = maxByRank(validationMode, 'DOCUMENT', rankValidation)
        semanticSignals.push('REFLECTION_CITES_DOCUMENT_SOURCE')
      }
      if (refs.some(ref => ref.startsWith('evidence://'))) {
        validationMode = maxByRank(validationMode, 'EVIDENCE_CHECK', rankValidation)
        semanticSignals.push('REFLECTION_CITES_EVIDENCE')
      }
    }
  }

  if (captureMode === 'REQUIRED' && (knowledge?.candidates.length ?? 0) === 0) {
    reasons.push('Framework deterministic floor requires Knowledge capture, but Reflection emitted no candidate.')
  }

  return {
    stage: input.stage,
    consultMode,
    captureMode,
    validationMode,
    deterministicSignals: unique(deterministicSignals),
    semanticSignals: unique(semanticSignals),
    reasons: unique(reasons),
  }
}
''', encoding='utf-8')

# ---------------------------------------------------------------------------
# Governance Runtime contracts + lifecycle integration
# ---------------------------------------------------------------------------
rel = 'agent_harness/public_plugins/governance_runtime/src/contracts.ts'
replace_once(
    rel,
    "export interface GovernanceKnowledgeCategoryOption {",
    "export type GovernanceKnowledgeConsultMode = 'NONE' | 'OPTIONAL' | 'REQUIRED'\n"
    "export type GovernanceKnowledgeCaptureMode = 'NONE' | 'CHECK' | 'REQUIRED'\n"
    "export type GovernanceKnowledgeValidationMode = 'NONE' | 'DOCUMENT' | 'EVIDENCE_CHECK' | 'REAL_TEST'\n\n"
    "export interface GovernanceKnowledgeDecision {\n"
    "  readonly stage: 'OPEN' | 'OBSERVE' | 'CLOSE'\n"
    "  readonly consultMode: GovernanceKnowledgeConsultMode\n"
    "  readonly captureMode: GovernanceKnowledgeCaptureMode\n"
    "  readonly validationMode: GovernanceKnowledgeValidationMode\n"
    "  readonly deterministicSignals: readonly string[]\n"
    "  readonly semanticSignals: readonly string[]\n"
    "  readonly reasons: readonly string[]\n"
    "}\n\n"
    "export interface GovernanceKnowledgePromotion {\n"
    "  readonly knowledgeUri: string\n"
    "  readonly fromStatus: string\n"
    "  readonly toStatus: 'VALIDATED' | 'FULL_VALIDATED'\n"
    "  readonly basisRefs: readonly string[]\n"
    "}\n\n"
    "export interface GovernanceKnowledgeSourceOption {\n"
    "  readonly sourceRef: string\n"
    "  readonly kind: string\n"
    "  readonly title: string\n"
    "  readonly location: string\n"
    "  readonly revision?: string\n"
    "}\n\n"
    "export interface GovernanceKnowledgeCategoryOption {",
)
replace_once(
    rel,
    "  readonly knowledgeClassification: {\n    readonly projectCategories:",
    "  readonly knowledgeValidation: {\n"
    "    readonly projectSources: readonly GovernanceKnowledgeSourceOption[]\n"
    "    readonly publicSources: readonly GovernanceKnowledgeSourceOption[]\n"
    "  }\n"
    "  readonly knowledgeClassification: {\n    readonly projectCategories:",
)
replace_once(
    rel,
    "  readonly taskObservation: GovernanceTurnObservation\n}",
    "  readonly taskObservation: GovernanceTurnObservation\n  readonly knowledgeDecision: GovernanceKnowledgeDecision\n}",
)
replace_once(
    rel,
    "export interface GovernanceWorkObservationResult {\n  readonly context: AutoGovernanceContextEnvelope\n  readonly journal: TurnJournalRecord\n  readonly observation: GovernanceTurnObservation\n}",
    "export interface GovernanceWorkObservationResult {\n"
    "  readonly context: AutoGovernanceContextEnvelope\n"
    "  readonly journal: TurnJournalRecord\n"
    "  readonly observation: GovernanceTurnObservation\n"
    "  readonly knowledgeDecision: GovernanceKnowledgeDecision\n"
    "}",
)
replace_once(
    rel,
    "  readonly closure: TurnClosureReceipt\n  readonly context: AutoGovernanceContextEnvelope\n}",
    "  readonly closure: TurnClosureReceipt\n"
    "  readonly context: AutoGovernanceContextEnvelope\n"
    "  readonly knowledgeDecision: GovernanceKnowledgeDecision\n"
    "  readonly knowledgePromotions: readonly GovernanceKnowledgePromotion[]\n"
    "}",
)

rel = 'agent_harness/public_plugins/governance_runtime/src/index.ts'
replace_once(
    rel,
    "export * from './turn-observation-store.js'\nexport * from './service.js'",
    "export * from './turn-observation-store.js'\n"
    "export * from './knowledge-governance-decision.js'\n"
    "export * from './service.js'",
)

rel = 'agent_harness/public_plugins/governance_runtime/src/service.ts'
replace_once(
    rel,
    "import type { KnowledgeCategory, KnowledgeTaxonomy } from '@agent-harness/knowledge-manager'",
    "import type { KnowledgeCategory, KnowledgeTaxonomy } from '@agent-harness/knowledge-manager'\n"
    "import { evaluateKnowledgeGovernanceDecision } from './knowledge-governance-decision.js'",
)
replace_once(
    rel,
    "  type GovernanceKnowledgeCategoryOption,\n",
    "  type GovernanceKnowledgeCategoryOption,\n"
    "  type GovernanceKnowledgeDecision,\n"
    "  type GovernanceKnowledgePromotion,\n"
    "  type GovernanceKnowledgeSourceOption,\n",
)
replace_once(
    rel,
    "    session.activeTurnId = turnId\n\n    return {",
    "    session.activeTurnId = turnId\n"
    "    const knowledgeDecision = evaluateKnowledgeGovernanceDecision({\n"
    "      stage: 'OPEN',\n"
    "      context,\n"
    "      observations: this.observations.list(taskId, turnId),\n"
    "    })\n\n"
    "    return {",
)
replace_once(
    rel,
    "      journal,\n      taskObservation,\n    }",
    "      journal,\n"
    "      taskObservation,\n"
    "      knowledgeDecision,\n"
    "    }",
)
replace_once(
    rel,
    "    return { context, journal, observation }\n  }",
    "    const knowledgeDecision = evaluateKnowledgeGovernanceDecision({\n"
    "      stage: 'OBSERVE',\n"
    "      context,\n"
    "      observations: this.observations.list(session.taskId, input.turnId),\n"
    "    })\n"
    "    return { context, journal, observation, knowledgeDecision }\n"
    "  }",
)
replace_once(
    rel,
    "      const closure = await this.runtimeContext.agentGovernanceKernel.closeTurn(session.taskId, turnId)\n      const context = this.runtimeContext.autoGovernanceEngine.buildContextEnvelope(session.actorId)",
    "      const decisionContext = this.runtimeContext.autoGovernanceEngine.buildContextEnvelope(session.actorId)\n"
    "      const knowledgeDecision = evaluateKnowledgeGovernanceDecision({\n"
    "        stage: 'CLOSE',\n"
    "        context: decisionContext,\n"
    "        observations: this.observations.list(session.taskId, turnId),\n"
    "        reflection: reflection.result,\n"
    "      })\n"
    "      if (knowledgeDecision.captureMode === 'REQUIRED' && reflection.result.knowledge.candidates.length === 0) {\n"
    "        throw new Error(`Knowledge Governance requires capture for Turn ${turnId}, but Reflection emitted NONE`)\n"
    "      }\n"
    "      const closure = await this.runtimeContext.agentGovernanceKernel.closeTurn(session.taskId, turnId)\n"
    "      const knowledgePromotions = closure.status === 'COMPLETE'\n"
    "        ? this.autoValidateKnowledgeCandidates(session.projectId, closure)\n"
    "        : []\n"
    "      const context = this.runtimeContext.autoGovernanceEngine.buildContextEnvelope(session.actorId)",
)
replace_once(
    rel,
    "        reflection,\n        closure,\n        context,\n      }",
    "        reflection,\n"
    "        closure,\n"
    "        context,\n"
    "        knowledgeDecision,\n"
    "        knowledgePromotions,\n"
    "      }",
)
replace_once(
    rel,
    "      turnObservations: this.observations.list(job.taskId, job.turnId),\n      knowledgeClassification:",
    "      turnObservations: this.observations.list(job.taskId, job.turnId),\n"
    "      knowledgeValidation: {\n"
    "        projectSources: this.sourceOptions(this.runtimeContext.knowledgeManager.listProjectSources(job.projectId), 'PROJECT', job.projectId),\n"
    "        publicSources: publicMounted\n"
    "          ? this.sourceOptions(this.runtimeContext.knowledgeManager.listGlobalSources(), 'PUBLIC')\n"
    "          : [],\n"
    "      },\n"
    "      knowledgeClassification:",
)
replace_once(
    rel,
    "        'Every Knowledge candidate must include knowledge-category://project/<categoryId> and/or knowledge-category://public/<categoryId> in relatedRefs for every selected persistence scope.',",
    "        'Every Knowledge candidate must include knowledge-category://project/<categoryId> and/or knowledge-category://public/<categoryId> in relatedRefs for every selected persistence scope.',\n"
    "        'When a Knowledge candidate is directly supported by an observed registered document/spec/SVD source, include its source:// reference in provenanceRefs or relatedRefs; do not cite a source merely because it exists.',\n"
    "        'When a Knowledge candidate is directly supported by pre-existing PASS validation evidence, include its evidence:// reference; Runtime, not the model, decides the resulting validation tier.',",
)
marker = "  private categoryOptions(\n"
idx = load(rel).index(marker)
text = load(rel)
helpers = r'''  private autoValidateKnowledgeCandidates(
    projectId: string,
    closure: import('@agent-harness/agent-governance-kernel').TurnClosureReceipt,
  ): GovernanceKnowledgePromotion[] {
    const receipt = closure.moduleReceipts.find(item => item.moduleId === 'knowledge-closure')
    if (!receipt) return []
    const manager = this.runtimeContext.knowledgeManager
    const policy = (this.runtimeContext as unknown as {
      knowledgeValidationPolicy?: {
        evaluate(reference: string, currentProjectId?: string): import('@agent-harness/knowledge-manager').KnowledgeValidationEvaluation
        promote(reference: string, currentProjectId?: string): import('@agent-harness/knowledge-manager').KnowledgePromotionResult
      }
    }).knowledgeValidationPolicy
    if (!policy) return []
    const promotions: GovernanceKnowledgePromotion[] = []

    for (const knowledgeUri of unique(receipt.candidateRefs)) {
      const target = manager.resolveKnowledgeReference(knowledgeUri, projectId)
      const node = target?.result.node
      if (!target || !node?.isLeaf || !node.status || node.status === 'DEPRECATED' || node.status === 'FULL_VALIDATED') continue
      const basisRefs = unique(node.refs.filter(ref => ref.startsWith('source://') || ref.startsWith('evidence://')))
      const existing = manager.listVerifications(target.knowledgeUri)
      for (const basisRef of basisRefs) {
        if (existing.some(record => record.basisRef === basisRef && record.relation === 'SUPPORT')) continue
        try {
          manager.recordVerification({
            knowledgeUri: target.knowledgeUri,
            basisRef,
            relation: 'SUPPORT',
            note: `Auto-recorded by Governance Runtime closure ${closure.attemptId}`,
          })
        } catch {
          // A cited ref may be stale or non-verifying; fail closed by leaving the Knowledge at its current tier.
        }
      }
      const evaluation = policy.evaluate(target.knowledgeUri, projectId)
      if (evaluation.decision !== 'READY' || !evaluation.targetStatus) continue
      const fromStatus = node.status
      const promoted = policy.promote(target.knowledgeUri, projectId)
      if (promoted.mutation.status !== evaluation.targetStatus) continue
      promotions.push({
        knowledgeUri: target.knowledgeUri,
        fromStatus,
        toStatus: evaluation.targetStatus,
        basisRefs,
      })
    }
    return promotions
  }

  private sourceOptions(
    sources: readonly import('@agent-harness/knowledge-manager').KnowledgeSourceRecord[],
    scope: 'PROJECT' | 'PUBLIC',
    projectId?: string,
  ): GovernanceKnowledgeSourceOption[] {
    return sources
      .filter(source => source.status === 'ACTIVE')
      .map(source => ({
        sourceRef: scope === 'PROJECT'
          ? `source://project/${projectId}/${source.sourceId}`
          : `source://global/${source.sourceId}`,
        kind: source.kind,
        title: source.title,
        location: source.location,
        ...(source.revision ? { revision: source.revision } : {}),
      }))
  }

'''
save(rel, text[:idx] + helpers + text[idx:])

# ---------------------------------------------------------------------------
# Generic work prompt: knowledge is considered according to Framework mode,
# but the Agent is never forced to agree with a Knowledge item.
# ---------------------------------------------------------------------------
rel = 'agent_harness/model_adapters/generic_model/src/contracts.ts'
replace_once(
    rel,
    "import type { GovernanceOpenTurnResult } from '@agent-harness/governance-runtime'",
    "import type { GovernanceKnowledgeDecision, GovernanceOpenTurnResult } from '@agent-harness/governance-runtime'",
)
replace_once(
    rel,
    "  readonly context: GovernanceOpenTurnResult['context']\n}",
    "  readonly context: GovernanceOpenTurnResult['context']\n"
    "  readonly knowledgeDecision: GovernanceKnowledgeDecision\n"
    "}",
)

rel = 'agent_harness/model_adapters/generic_model/src/prompt.ts'
replace_once(
    rel,
    "    'Do not perform Governance Reflection or persistence classification here; the Runtime performs that automatically after work.',",
    "    'Knowledge consultation is governed by the supplied Knowledge Decision: OPTIONAL means use only when useful; REQUIRED means consider the routed knowledge, but you may reject it when evidence or task context shows it is not applicable.',\n"
    "    'Do not perform Governance Reflection or persistence classification here; the Runtime performs that automatically after work.',",
)
replace_once(
    rel,
    "    'AUTOMATIC GOVERNANCE CONTEXT:',\n    request.context.text,",
    "    'KNOWLEDGE ENGAGEMENT DECISION:',\n"
    "    JSON.stringify(request.knowledgeDecision),\n"
    "    '',\n"
    "    'AUTOMATIC GOVERNANCE CONTEXT:',\n"
    "    request.context.text,",
)

rel = 'agent_harness/pilots/generic_model/src/index.ts'
replace_once(
    rel,
    "  readonly actorId?: string\n}",
    "  readonly actorId?: string\n"
    "  readonly additionalToolResults?: readonly {\n"
    "    readonly name: string\n"
    "    readonly summary: string\n"
    "    readonly resourceRefs?: readonly string[]\n"
    "    readonly isError?: boolean\n"
    "  }[]\n"
    "}",
)
replace_once(
    rel,
    "      taskText: input.taskText,\n      context: open.context,\n    })",
    "      taskText: input.taskText,\n"
    "      context: open.context,\n"
    "      knowledgeDecision: open.knowledgeDecision,\n"
    "    })",
)
replace_once(
    rel,
    "    const close = await this.runtime.closeTurn({",
    "    for (const extra of input.additionalToolResults ?? []) {\n"
    "      this.runtime.observeWork({\n"
    "        kind: 'tool-result',\n"
    "        runtimeId: open.runtimeId,\n"
    "        turnId: open.turnId,\n"
    "        name: extra.name,\n"
    "        summary: extra.summary,\n"
    "        ...(extra.resourceRefs ? { resourceRefs: extra.resourceRefs } : {}),\n"
    "        ...(extra.isError !== undefined ? { isError: extra.isError } : {}),\n"
    "      })\n"
    "    }\n"
    "    const close = await this.runtime.closeTurn({",
)

# ---------------------------------------------------------------------------
# Closed-loop pilot: document-backed candidate should auto-promote and route.
# ---------------------------------------------------------------------------
rel = 'agent_harness/pilots/external_chat_agent/src/closed-loop.ts'
replace_once(
    rel,
    "    const beforeIndex = knowledge.getIndex('et-tool')",
    "    const validationSource = knowledge.registerProjectSource('et-tool', {\n"
    "      kind: 'DOCUMENT',\n"
    "      title: 'Public Governance Runtime and External Boundaries v0.1',\n"
    "      location: 'agent_harness/design/21_PUBLIC_GOVERNANCE_RUNTIME_AND_EXTERNAL_BOUNDARIES_V0_1.md',\n"
    "      note: 'Authoritative project governance design source for the external-agent mailbox boundary.',\n"
    "    })\n\n"
    "    const beforeIndex = knowledge.getIndex('et-tool')",
)
replace_once(
    rel,
    "      actorId,\n    })\n\n    const afterTurn1Index",
    "      actorId,\n"
    "      additionalToolResults: [{\n"
    "        name: 'governance-document-consult',\n"
    "        summary: 'The authoritative project governance design states that the External Chat Agent GitHub Issue mailbox is transport only; governance routing and lifecycle decisions belong to Public Governance Runtime.',\n"
    "        resourceRefs: [validationSource.sourceUri],\n"
    "      }],\n"
    "    })\n\n"
    "    const afterTurn1Index",
)
replace_once(
    rel,
    "    const candidate = newNodes.find(node => node.status === 'CANDIDATE')",
    "    const learnedKnowledge = newNodes.find(node => node.status !== 'DEPRECATED')",
)
replace_once(
    rel,
    "    const candidateSearch = candidate\n      ? knowledge.searchKnowledge({\n          projectId: 'et-tool',\n          query: task2,\n          filters: { status: 'CANDIDATE' },\n          limit: 16,\n        })\n      : []",
    "    const learnedSearch = learnedKnowledge\n"
    "      ? knowledge.searchKnowledge({\n"
    "          projectId: 'et-tool',\n"
    "          query: task2,\n"
    "          limit: 16,\n"
    "        })\n"
    "      : []",
)
replace_all(rel, 'candidateRouted', 'learnedKnowledgeRouted')
replace_all(rel, 'candidateSearchable', 'learnedKnowledgeSearchable')
replace_all(rel, 'categoryIsActive', 'learnedCategoryIsActive')
replace_once(
    rel,
    "    const learnedKnowledgeRouted = !!candidate && autoRoutedIds.includes(candidate.id)\n    const learnedKnowledgeSearchable = !!candidate && candidateSearch.some(item => item.id === candidate.id)\n    const learnedCategoryIsActive = !!candidate && activeCategory(afterTurn1Index, candidate.category)",
    "    const learnedKnowledgeRouted = !!learnedKnowledge && autoRoutedIds.includes(learnedKnowledge.id)\n"
    "    const learnedKnowledgeSearchable = !!learnedKnowledge && learnedSearch.some(item => item.id === learnedKnowledge.id)\n"
    "    const learnedCategoryIsActive = !!learnedKnowledge && activeCategory(afterTurn1Index, learnedKnowledge.category)",
)
replace_all(rel, 'candidate?.id', 'learnedKnowledge?.id')
replace_all(rel, 'candidate?.status', 'learnedKnowledge?.status')
replace_all(rel, 'candidate?.category', 'learnedKnowledge?.category')
replace_all(rel, '!!candidate', '!!learnedKnowledge')
replace_all(rel, 'candidateSearch', 'learnedSearch')
replace_once(
    rel,
    "        knowledgeCandidateCreated: !!learnedKnowledge,\n        knowledgeCategoryForcedActive: learnedCategoryIsActive,\n        knowledgeIndexRefreshed: fingerprintChanged && learnedKnowledgeSearchable,",
    "        knowledgeCandidateCreated: !!learnedKnowledge,\n"
    "        knowledgeCategoryForcedActive: learnedCategoryIsActive,\n"
    "        knowledgeAutomaticallyValidated: learnedKnowledge?.status === 'VALIDATED' || learnedKnowledge?.status === 'FULL_VALIDATED',\n"
    "        knowledgeIndexRefreshed: fingerprintChanged && learnedKnowledgeSearchable,",
)
replace_once(
    rel,
    "      && report.assertions.knowledgeCategoryForcedActive\n      && report.assertions.knowledgeIndexRefreshed",
    "      && report.assertions.knowledgeCategoryForcedActive\n"
    "      && report.assertions.knowledgeAutomaticallyValidated\n"
    "      && report.assertions.knowledgeIndexRefreshed",
)

print('KNOWLEDGE_GOVERNANCE_DECISION_V0_1_PATCH=APPLIED')
