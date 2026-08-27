import { createHash } from 'node:crypto'
import type {
  KnowledgeLibraryScope,
  KnowledgeNode,
  KnowledgeStatus,
  KnowledgeValidationEvaluation,
  KnowledgeVerificationRecord,
} from './contracts.js'

export function knowledgeClaimFingerprint(node: Pick<KnowledgeNode, 'fact' | 'scope'>): string {
  if (!node.fact?.trim()) throw new Error('Knowledge Claim 缺少 Fact')
  return `sha256:${createHash('sha256')
    .update(node.fact.trim())
    .update('\0')
    .update(node.scope?.trim() ?? '')
    .digest('hex')}`
}

export function evaluateKnowledgeValidationPolicy(input: {
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
  const projectRealTestReady = input.libraryScope.kind === 'project' && realTestSupportCount >= 1
  const globalProjectEvidenceObserved = input.libraryScope.kind === 'global' && realTestSupportCount >= 1
  const reasons: string[] = []

  let decision: KnowledgeValidationEvaluation['decision']
  let targetStatus: KnowledgeValidationEvaluation['targetStatus']
  if (input.currentStatus === 'DEPRECATED') {
    decision = 'BLOCKED'
    reasons.push('DEPRECATED Knowledge 不允许晋级')
  } else if (contradictions.length > 0) {
    decision = 'BLOCKED'
    reasons.push(`存在 ${contradictions.length} 条当前 Claim 的 CONTRADICT；不得自动晋级`)
  } else if (input.currentStatus === 'FULL_VALIDATED') {
    decision = 'BLOCKED'
    reasons.push('FULL_VALIDATED 已是最高验证等级')
  } else if (projectRealTestReady) {
    decision = 'READY'
    targetStatus = 'FULL_VALIDATED'
    reasons.push('Project Knowledge 存在本项目实际验证 PASS Evidence，可晋级 FULL_VALIDATED')
  } else if (input.currentStatus === 'VALIDATED') {
    decision = 'INSUFFICIENT'
    reasons.push(
      globalProjectEvidenceObserved
        ? 'Global Knowledge 的单项目 REAL_TEST 不能证明跨项目适用性；不得晋级 FULL_VALIDATED'
        : '已是文档验证级 VALIDATED；尚缺符合 Scope 的实际验证 Evidence',
    )
  } else if (documentSupportCount >= requiredSupportCount) {
    decision = 'READY'
    targetStatus = 'VALIDATED'
    reasons.push(
      `${input.libraryScope.kind === 'global' ? 'Global' : 'Project'} Knowledge 已满足 ${requiredSupportCount} 个文档级 SUPPORT`,
    )
  } else {
    decision = 'INSUFFICIENT'
    reasons.push(`当前只有 ${documentSupportCount}/${requiredSupportCount} 个文档级 SUPPORT`)
    if (globalProjectEvidenceObserved) {
      reasons.push('已观察到 Project REAL_TEST，但它不能把 Global Knowledge 晋级为 FULL_VALIDATED')
    }
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
