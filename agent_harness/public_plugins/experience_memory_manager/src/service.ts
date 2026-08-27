import { randomUUID } from 'node:crypto'
import { readFileSync, renameSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { Service, type Context } from '@deepseek-ai/cordis'
import '@agent-harness/project-manager'
import '@agent-harness/knowledge-manager'
import '@agent-harness/evidence-state-manager'
import type { ProjectCandidateResult } from '@agent-harness/project-contract'
import type { StateRecord } from '@agent-harness/evidence-state-manager'
import {
  qualifyEvidenceId,
  type KnowledgeMutationResult,
} from '@agent-harness/knowledge-manager'
import { insertKnowledgeLeaf } from './knowledge-writer.js'
import type {
  ExperienceCandidate,
  ExperienceCandidateInput,
  ExperienceKnowledgeCandidateResult,
  ExperienceKnowledgeCandidateTarget,
  ExperienceKnowledgePromotionResult,
  ExperienceSearchRequest,
  ExperienceStatus,
  KnowledgePromotionResult,
  KnowledgePromotionTarget,
} from './contracts.js'

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

const normalize = (value: string): string =>
  value.toLowerCase().replace(/[^a-z0-9\u4e00-\u9fff]+/g, '')

const unique = (values: readonly string[]): string[] =>
  [...new Set(values.map(value => value.trim()).filter(Boolean))]

const isExperienceCandidate = (value: unknown): value is ExperienceCandidate =>
  isRecord(value)
  && typeof value.candidateId === 'string'
  && typeof value.projectId === 'string'
  && typeof value.taskId === 'string'
  && typeof value.title === 'string'
  && typeof value.fact === 'string'
  && Array.isArray(value.evidenceRefs)
  && typeof value.status === 'string'

const atomicWrite = (file: string, content: string): void => {
  const temp = `${file}.${process.pid}.${randomUUID()}.tmp`
  writeFileSync(temp, content, 'utf-8')
  renameSync(temp, file)
}

interface CandidateState {
  readonly record: StateRecord
  readonly candidate: ExperienceCandidate
}

export class ExperienceMemoryManagerService extends Service {
  private readonly runtimeContext: Context

  constructor(ctx: Context) {
    super(ctx, 'experienceMemoryManager')
    this.runtimeContext = ctx
  }

  recordCandidate(input: ExperienceCandidateInput): ExperienceCandidate {
    this.assertProject(input.projectId)
    if (!input.taskId.trim()) throw new Error('experience taskId 不能为空')
    if (!input.title.trim()) throw new Error('experience title 不能为空')
    if (!input.fact.trim()) throw new Error('experience fact 不能为空')
    if (input.evidenceRefs.length === 0) throw new Error('experience 必须至少引用一个 Evidence')

    for (const evidenceId of input.evidenceRefs) {
      if (!this.runtimeContext.evidenceStateManager.getEvidence(input.projectId, evidenceId)) {
        throw new Error(`Experience 引用不存在或不属于当前项目的 Evidence: ${evidenceId}`)
      }
    }

    const duplicate = this.listCandidates(input.projectId)
      .find(item => item.status !== 'REJECTED' && normalize(item.fact) === normalize(input.fact))
    if (duplicate) throw new Error(`重复经验候选: ${duplicate.candidateId}`)

    const candidate: ExperienceCandidate = {
      ...input,
      candidateId: `EXP-${randomUUID()}`,
      status: 'CANDIDATE',
      createdAt: new Date().toISOString(),
      refs: unique(input.refs ?? []),
      evidenceRefs: unique(input.evidenceRefs),
    }

    this.runtimeContext.evidenceStateManager.updateState({
      projectId: input.projectId,
      scope: `experience:${candidate.candidateId}`,
      key: 'candidate',
      value: candidate,
      reason: `Agent 提交任务 ${input.taskId} 的经验候选`,
      evidenceRefs: candidate.evidenceRefs,
      expectedVersion: 0,
    })
    return candidate
  }

  listCandidates(projectId: string, statuses?: readonly ExperienceStatus[]): readonly ExperienceCandidate[] {
    this.assertProject(projectId)
    const allowed = statuses ? new Set(statuses) : undefined
    return this.runtimeContext.evidenceStateManager.snapshot(projectId).records
      .filter(record => record.scope.startsWith('experience:') && record.key === 'candidate')
      .map(record => record.value)
      .filter(isExperienceCandidate)
      .filter(candidate => !allowed || allowed.has(candidate.status))
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
  }

  getCandidate(projectId: string, candidateId: string): ExperienceCandidate | undefined {
    return this.getCandidateState(projectId, candidateId)?.candidate
  }

  searchMemory(request: ExperienceSearchRequest): readonly ProjectCandidateResult[] {
    const query = request.query.trim()
    if (!query) return []
    const statuses = request.statuses ?? ['CANDIDATE', 'KNOWLEDGE_CANDIDATE']
    const needle = normalize(query)

    const scored = this.listCandidates(request.projectId, statuses)
      .map(candidate => {
        const fields = [candidate.title, candidate.fact, candidate.scope ?? '', ...(candidate.refs ?? [])]
        const normalizedFields = fields.map(normalize)
        let relevance = 0
        const reasons: string[] = []
        if (normalize(candidate.title) === needle) {
          relevance = 0.98
          reasons.push('experience title 精确匹配')
        } else if (normalizedFields.some(field => field.includes(needle) || needle.includes(field))) {
          relevance = 0.85
          reasons.push('experience 内容包含匹配')
        } else {
          const terms = query.toLowerCase().match(/[a-z0-9]+|[\u4e00-\u9fff]{2,}/g) ?? []
          const matched = terms.filter(term => normalizedFields.some(field => field.includes(normalize(term))))
          if (matched.length > 0) {
            relevance = 0.45 + 0.45 * (matched.length / Math.max(1, terms.length))
            reasons.push(`experience terms 命中 ${matched.length}/${terms.length}`)
          }
        }
        return { candidate, relevance, reasons }
      })
      .filter(item => item.relevance > 0)
      .sort((a, b) => b.relevance - a.relevance || a.candidate.candidateId.localeCompare(b.candidate.candidateId))
      .slice(0, Math.max(1, request.limit ?? 8))

    return scored.map(({ candidate, relevance, reasons }) => ({
      projectId: request.projectId,
      id: candidate.candidateId,
      title: candidate.title,
      type: 'experience-candidate',
      location: `runtime://experience/${candidate.candidateId}`,
      summary: candidate.fact,
      relevance,
      matchReasons: reasons,
      provenance: {
        resource: `runtime://${request.projectId}/experience`,
        location: candidate.candidateId,
      },
      metadata: {
        taskId: candidate.taskId,
        status: candidate.status,
        scope: candidate.scope,
        evidenceRefs: candidate.evidenceRefs,
        refs: candidate.refs,
        knowledgeCandidateUri: candidate.knowledgeCandidateUri,
        promotedKnowledgeId: candidate.promotedKnowledgeId,
        promotedKnowledgeUri: candidate.promotedKnowledgeUri,
      },
      warnings: candidate.status === 'CANDIDATE'
        ? ['Experience Candidate 尚未提交到 Knowledge Library']
        : candidate.status === 'KNOWLEDGE_CANDIDATE'
          ? [`Experience 已关联 Knowledge Candidate ${candidate.knowledgeCandidateUri ?? ''}，尚未成为 VALIDATED Knowledge`]
          : [],
    }))
  }

  rejectCandidate(projectId: string, candidateId: string, reason: string): ExperienceCandidate {
    if (!reason.trim()) throw new Error('reject reason 不能为空')
    const current = this.requireCandidateState(projectId, candidateId)
    if (current.candidate.status !== 'CANDIDATE') {
      throw new Error(`Experience ${candidateId} 当前状态不可拒绝: ${current.candidate.status}`)
    }
    const updated: ExperienceCandidate = {
      ...current.candidate,
      status: 'REJECTED',
      rejectedReason: reason.trim(),
    }
    this.runtimeContext.evidenceStateManager.updateState({
      projectId,
      scope: current.record.scope,
      key: 'candidate',
      value: updated,
      reason: `Experience rejected: ${reason.trim()}`,
      evidenceRefs: current.candidate.evidenceRefs,
      expectedVersion: current.record.version,
    })
    return updated
  }

  submitToKnowledge(
    projectId: string,
    target: ExperienceKnowledgeCandidateTarget,
  ): ExperienceKnowledgeCandidateResult {
    const current = this.requireCandidateState(projectId, target.candidateId)
    if (current.candidate.status !== 'CANDIDATE') {
      throw new Error(`Experience ${target.candidateId} 当前状态不可提交 Knowledge Candidate: ${current.candidate.status}`)
    }
    if (target.targetScope !== 'project' && target.targetScope !== 'global') {
      throw new Error(`非法 Knowledge targetScope: ${String(target.targetScope)}`)
    }
    if (!target.categoryId.trim()) throw new Error('Knowledge categoryId 不能为空')

    const libraryScope = target.targetScope === 'global'
      ? { kind: 'global' as const }
      : { kind: 'project' as const, projectId }
    const title = target.title?.trim() || current.candidate.title.trim()
    if (!title) throw new Error('Knowledge title 不能为空')
    const experienceRef = `experience://project/${projectId}/${target.candidateId}`
    const refs = unique([...(current.candidate.refs ?? []), ...(target.refs ?? []), experienceRef])

    let mutation: KnowledgeMutationResult | undefined
    let knowledgeUri: string | undefined
    try {
      const input = {
        categoryId: target.categoryId.trim(),
        title,
        fact: current.candidate.fact.trim(),
        provenance: experienceRef,
        ...(current.candidate.scope?.trim() ? { scope: current.candidate.scope.trim() } : {}),
        ...(target.tags ? { tags: unique(target.tags) } : {}),
        refs,
      }
      mutation = libraryScope.kind === 'global'
        ? this.runtimeContext.knowledgeManager.submitGlobalKnowledgeCandidate(input)
        : this.runtimeContext.knowledgeManager.submitKnowledgeCandidate(projectId, input)
      knowledgeUri = libraryScope.kind === 'global'
        ? `knowledge://global/${mutation.knowledgeId}`
        : `knowledge://project/${projectId}/${mutation.knowledgeId}`

      const verificationRecords = current.candidate.evidenceRefs.map(evidenceId =>
        this.runtimeContext.knowledgeManager.recordVerification({
          knowledgeUri: knowledgeUri!,
          basisRef: qualifyEvidenceId(projectId, evidenceId),
          relation: 'SUPPORT',
          note: `Supporting Evidence from ${experienceRef}`,
        }),
      )
      const evaluation = this.runtimeContext.knowledgeValidationPolicy.evaluate(knowledgeUri)

      const updated: ExperienceCandidate = {
        ...current.candidate,
        status: 'KNOWLEDGE_CANDIDATE',
        knowledgeCandidateId: mutation.knowledgeId,
        knowledgeCandidateUri: knowledgeUri,
        knowledgeCandidateScope: libraryScope,
      }
      this.runtimeContext.evidenceStateManager.updateState({
        projectId,
        scope: current.record.scope,
        key: 'candidate',
        value: updated,
        reason: `Experience submitted to Knowledge Candidate ${knowledgeUri}`,
        evidenceRefs: current.candidate.evidenceRefs,
        expectedVersion: current.record.version,
      })

      return {
        candidateId: target.candidateId,
        knowledgeId: mutation.knowledgeId,
        knowledgeUri,
        libraryScope,
        verificationRecords,
        evaluation,
      }
    } catch (error) {
      if (mutation) {
        try {
          if (libraryScope.kind === 'global') {
            this.runtimeContext.knowledgeManager.deprecateGlobalKnowledge(mutation.knowledgeId)
          } else {
            this.runtimeContext.knowledgeManager.deprecateKnowledge(projectId, mutation.knowledgeId)
          }
        } catch (rollbackError) {
          throw new Error(
            `${error instanceof Error ? error.message : String(error)}; Knowledge Candidate 回滚失败: ${rollbackError instanceof Error ? rollbackError.message : String(rollbackError)}`,
          )
        }
      }
      throw error
    }
  }

  evaluateKnowledgeCandidate(projectId: string, candidateId: string) {
    const current = this.requireCandidateState(projectId, candidateId)
    const uri = current.candidate.knowledgeCandidateUri ?? current.candidate.promotedKnowledgeUri
    if (!uri) throw new Error(`Experience ${candidateId} 尚未关联 Knowledge Candidate`)
    return this.runtimeContext.knowledgeValidationPolicy.evaluate(uri)
  }

  promoteKnowledgeCandidate(
    projectId: string,
    candidateId: string,
  ): ExperienceKnowledgePromotionResult {
    const current = this.requireCandidateState(projectId, candidateId)
    if (current.candidate.status === 'PROMOTED') {
      const uri = current.candidate.promotedKnowledgeUri ?? current.candidate.knowledgeCandidateUri
      if (!uri) throw new Error(`Experience ${candidateId} PROMOTED 状态缺少 Knowledge URI`)
      const resolved = this.runtimeContext.knowledgeManager.resolveKnowledgeReference(uri)
      if (!resolved?.result.node.isLeaf) throw new Error(`Knowledge 不存在: ${uri}`)
      return {
        candidateId,
        knowledgeId: resolved.result.node.id,
        knowledgeUri: uri,
        status: 'PROMOTED',
        evaluation: this.runtimeContext.knowledgeValidationPolicy.evaluate(uri),
      }
    }
    if (current.candidate.status !== 'KNOWLEDGE_CANDIDATE') {
      throw new Error(`Experience ${candidateId} 当前状态不可晋级: ${current.candidate.status}`)
    }

    const uri = current.candidate.knowledgeCandidateUri
    if (!uri) throw new Error(`Experience ${candidateId} 缺少 Knowledge Candidate URI`)
    const resolved = this.runtimeContext.knowledgeManager.resolveKnowledgeReference(uri)
    const node = resolved?.result.node
    if (!resolved || !node?.isLeaf || !node.status) throw new Error(`Knowledge Candidate 不存在: ${uri}`)
    if (node.status === 'DEPRECATED') throw new Error(`Knowledge Candidate 已 DEPRECATED: ${uri}`)

    const evaluation = node.status === 'CANDIDATE'
      ? this.runtimeContext.knowledgeValidationPolicy.promote(uri).evaluation
      : this.runtimeContext.knowledgeValidationPolicy.evaluate(uri)

    const after = this.runtimeContext.knowledgeManager.resolveKnowledgeReference(uri)?.result.node
    if (!after?.isLeaf || after.status !== 'VALIDATED') {
      throw new Error(`Knowledge 晋级后不是 VALIDATED: ${uri}`)
    }

    const promoted: ExperienceCandidate = {
      ...current.candidate,
      status: 'PROMOTED',
      promotedKnowledgeId: after.id,
      promotedKnowledgeUri: uri,
    }
    this.runtimeContext.evidenceStateManager.updateState({
      projectId,
      scope: current.record.scope,
      key: 'candidate',
      value: promoted,
      reason: `Experience promoted through Knowledge Validation Policy: ${uri}`,
      evidenceRefs: current.candidate.evidenceRefs,
      expectedVersion: current.record.version,
    })

    return {
      candidateId,
      knowledgeId: after.id,
      knowledgeUri: uri,
      status: 'PROMOTED',
      evaluation,
    }
  }

  /**
   * Legacy knowledge-v0.1 compatibility path only.
   * knowledge-library-v0.2 always rejects this direct VALIDATED writer.
   */
  promoteToKnowledge(
    projectId: string,
    target: KnowledgePromotionTarget,
  ): KnowledgePromotionResult {
    const current = this.requireCandidateState(projectId, target.candidateId)
    if (current.candidate.status !== 'CANDIDATE') {
      throw new Error(`Experience ${target.candidateId} 当前状态不可晋级: ${current.candidate.status}`)
    }
    if (!target.title.trim()) throw new Error('Knowledge title 不能为空')

    const knowledgeIndex = this.runtimeContext.knowledgeManager.getIndex(projectId)
    if (knowledgeIndex.libraryMode === 'library-v0.2') {
      throw new Error(
        'knowledge-library-v0.2 禁止 Experience Manager 直接写入 VALIDATED Knowledge；请使用 submitToKnowledge()，记录 Verification，并由 promoteKnowledgeCandidate() 显式晋级',
      )
    }

    const targetFile = this.runtimeContext.knowledgeManager.listFiles(projectId)
      .find(file => file.id === target.fileId)
    if (!targetFile) throw new Error(`Knowledge File ID 不存在: ${target.fileId}`)

    const parent = this.runtimeContext.knowledgeManager.getNode(projectId, target.parentNodeId)?.node
    if (!parent) throw new Error(`Knowledge 父节点不存在: ${target.parentNodeId}`)
    if (parent.fileId !== target.fileId) throw new Error('Knowledge 父节点与目标 File ID 不一致')
    if (parent.isLeaf) throw new Error(`Knowledge 父节点必须是 Branch: ${target.parentNodeId}`)
    if (this.runtimeContext.knowledgeManager.getNode(projectId, target.nodeId)) {
      throw new Error(`Knowledge Node 已存在: ${target.nodeId}`)
    }

    const resourceRoot = this.runtimeContext.projectManager.getResourcePath(projectId, 'knowledge')
    if (!resourceRoot) throw new Error(`无法解析 ${projectId} Knowledge 路径`)
    const filePath = join(resourceRoot, targetFile.file)
    const original = readFileSync(filePath, 'utf-8')
    const updatedText = insertKnowledgeLeaf(
      original,
      target.parentNodeId,
      target.nodeId,
      target.title,
      current.candidate,
    )

    atomicWrite(filePath, updatedText)
    try {
      this.runtimeContext.knowledgeManager.refreshProject(projectId)
      const promotedNode = this.runtimeContext.knowledgeManager.getNode(projectId, target.nodeId)?.node
      if (!promotedNode?.isLeaf || promotedNode.status !== 'VALIDATED') {
        throw new Error(`Knowledge 晋级后校验未得到 VALIDATED Leaf: ${target.nodeId}`)
      }

      const promoted: ExperienceCandidate = {
        ...current.candidate,
        status: 'PROMOTED',
        promotedKnowledgeId: target.nodeId,
        promotedKnowledgeUri: `knowledge://project/${projectId}/${target.nodeId}`,
      }
      this.runtimeContext.evidenceStateManager.updateState({
        projectId,
        scope: current.record.scope,
        key: 'candidate',
        value: promoted,
        reason: `Promoted to legacy Knowledge ${target.nodeId}`,
        evidenceRefs: current.candidate.evidenceRefs,
        expectedVersion: current.record.version,
      })
    } catch (error) {
      atomicWrite(filePath, original)
      this.runtimeContext.knowledgeManager.refreshProject(projectId)
      throw error
    }

    return {
      candidateId: target.candidateId,
      knowledgeId: target.nodeId,
      fileId: target.fileId,
      file: targetFile.file,
    }
  }

  private getCandidateState(projectId: string, candidateId: string): CandidateState | undefined {
    this.assertProject(projectId)
    const record = this.runtimeContext.evidenceStateManager.readState(
      projectId,
      `experience:${candidateId}`,
      'candidate',
    )
    if (!record || !isExperienceCandidate(record.value)) return undefined
    return { record, candidate: record.value }
  }

  private requireCandidateState(projectId: string, candidateId: string): CandidateState {
    const state = this.getCandidateState(projectId, candidateId)
    if (!state) throw new Error(`Experience Candidate 不存在: ${candidateId}`)
    return state
  }

  private assertProject(projectId: string): void {
    if (!this.runtimeContext.projectManager.getProjectContext(projectId)) {
      throw new Error(`Experience / Memory Manager 找不到项目: ${projectId}`)
    }
  }
}

declare module '@deepseek-ai/cordis' {
  interface Context {
    experienceMemoryManager: ExperienceMemoryManagerService
  }
}

export default ExperienceMemoryManagerService
