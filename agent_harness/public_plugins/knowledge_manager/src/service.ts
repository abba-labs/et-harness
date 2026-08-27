import { resolve } from 'node:path'
import { Service, type Context } from '@deepseek-ai/cordis'
import '@agent-harness/project-manager'
import type { ProjectCandidateResult, ProjectQueryRequest } from '@agent-harness/project-contract'
import {
  GLOBAL_KNOWLEDGE_LIBRARY_ID,
  knowledgeLibraryKey,
  parseKnowledgeReference,
  qualifyKnowledgeId,
} from './knowledge-address.js'
import { KnowledgeManagerEngine } from './knowledge-manager-engine.js'
import { KnowledgeLibraryMutator } from './knowledge-library-mutator.js'
import {
  KnowledgeSourceVerificationStore,
  parseEvidenceReference,
  parseSourceReference,
} from './source-verification-store.js'
import type {
  KnowledgeCandidateInput,
  KnowledgeCandidateUpdate,
  KnowledgeCategory,
  KnowledgeCategoryCreateInput,
  KnowledgeCategoryMutationResult,
  KnowledgeCategoryUpdateInput,
  KnowledgeCombinedSearchRequest,
  KnowledgeLibraryScope,
  KnowledgeLibraryStats,
  KnowledgeLibraryValidationResult,
  KnowledgeMutationResult,
  KnowledgeNode,
  KnowledgeNodeResult,
  KnowledgeProjectIndex,
  KnowledgeRelatedResult,
  KnowledgeResolvedReference,
  KnowledgeResolvedSource,
  KnowledgeRouteFile,
  KnowledgeScopedCandidate,
  KnowledgeSearchInput,
  KnowledgeSourceInput,
  KnowledgeSourceRecord,
  KnowledgeTaxonomy,
  KnowledgeVerificationInput,
  KnowledgeVerificationRecord,
  KnowledgeVerificationSummary,
  KnowledgeVerificationValidationClass,
} from './contracts.js'

interface EvidenceLookupService {
  getEvidence(projectId: string, evidenceId: string): unknown | undefined
}

export class KnowledgeManagerService extends Service {
  private readonly runtimeContext: Context
  private readonly engine = new KnowledgeManagerEngine()
  private globalKnowledgeRoot?: string

  constructor(ctx: Context) {
    super(ctx, 'knowledgeManager')
    this.runtimeContext = ctx
    const configuredGlobalRoot = process.env.AGENT_HARNESS_GLOBAL_KNOWLEDGE_ROOT?.trim()
    if (configuredGlobalRoot) this.mountGlobalLibrary(configuredGlobalRoot)
    ctx.effect(() => () => this.engine.clear())
  }

  mountGlobalLibrary(resourcePath: string): KnowledgeProjectIndex {
    const root = resolve(resourcePath)
    const snapshot = this.engine.refreshProject(
      GLOBAL_KNOWLEDGE_LIBRARY_ID,
      root,
      'knowledge://global',
    )
    if (snapshot.libraryMode !== 'library-v0.2') {
      this.engine.removeProject(GLOBAL_KNOWLEDGE_LIBRARY_ID)
      throw new Error('Global Knowledge 必须使用 knowledge-library-v0.2')
    }
    this.globalKnowledgeRoot = root
    return snapshot
  }

  unmountGlobalLibrary(): boolean {
    this.globalKnowledgeRoot = undefined
    return this.engine.removeProject(GLOBAL_KNOWLEDGE_LIBRARY_ID)
  }

  isGlobalLibraryMounted(): boolean {
    return this.globalKnowledgeRoot !== undefined
  }

  refreshGlobalLibrary(): KnowledgeProjectIndex {
    return this.mountGlobalLibrary(this.requireGlobalRoot())
  }

  reindexGlobalLibrary(): KnowledgeProjectIndex {
    const root = this.requireGlobalRoot()
    const snapshot = this.engine.reindexProject(
      GLOBAL_KNOWLEDGE_LIBRARY_ID,
      root,
      'knowledge://global',
    )
    if (snapshot.libraryMode !== 'library-v0.2') {
      throw new Error('Global Knowledge 必须使用 knowledge-library-v0.2')
    }
    return snapshot
  }

  validateGlobalLibrary(): KnowledgeLibraryValidationResult {
    return this.validationResult(() => this.reindexGlobalLibrary())
  }

  getGlobalIndex(): KnowledgeProjectIndex {
    return this.ensureGlobalReady()
  }

  getGlobalTaxonomy(): KnowledgeTaxonomy {
    const taxonomy = this.ensureGlobalReady().taxonomy
    if (!taxonomy) throw new Error('Global Knowledge 缺少 TAXONOMY')
    return taxonomy
  }

  listGlobalCategories(parentId?: string): readonly KnowledgeCategory[] {
    this.ensureGlobalReady()
    return this.engine.listCategories(GLOBAL_KNOWLEDGE_LIBRARY_ID, parentId)
  }

  getGlobalLibraryStats(): KnowledgeLibraryStats {
    this.ensureGlobalReady()
    return this.engine.getLibraryStats(GLOBAL_KNOWLEDGE_LIBRARY_ID)
  }

  searchGlobalKnowledge(request: KnowledgeSearchInput): readonly KnowledgeScopedCandidate[] {
    this.ensureGlobalReady()
    return this.engine.search({
      projectId: GLOBAL_KNOWLEDGE_LIBRARY_ID,
      query: request.query,
      ...(request.scope ? { scope: request.scope } : {}),
      ...(request.filters ? { filters: request.filters } : {}),
      ...(request.limit !== undefined ? { limit: request.limit } : {}),
    }).map(candidate => this.toScopedCandidate({ kind: 'global' }, candidate))
  }

  searchKnowledgeCombined(request: KnowledgeCombinedSearchRequest): readonly KnowledgeScopedCandidate[] {
    const global = this.searchGlobalKnowledge({
      query: request.query,
      ...(request.scope ? { scope: request.scope } : {}),
      ...(request.filters ? { filters: request.filters } : {}),
      limit: request.globalLimit ?? request.limit ?? 8,
    })
    const project = this.searchKnowledge({
      projectId: request.projectId,
      query: request.query,
      ...(request.scope ? { scope: request.scope } : {}),
      ...(request.filters ? { filters: request.filters } : {}),
      limit: request.projectLimit ?? request.limit ?? 8,
    }).map(candidate => this.toScopedCandidate(
      { kind: 'project', projectId: request.projectId },
      candidate,
    ))
    return [...global, ...project]
  }

  resolveKnowledgeReference(reference: string, currentProjectId?: string): KnowledgeResolvedReference | undefined {
    const parsed = parseKnowledgeReference(reference, currentProjectId)
    const key = knowledgeLibraryKey(parsed.scope)
    this.ensureScopeReady(parsed.scope)
    const result = this.engine.getNode(key, parsed.knowledgeId)
    return result
      ? {
          libraryScope: parsed.scope,
          knowledgeUri: qualifyKnowledgeId(parsed.scope, parsed.knowledgeId),
          result,
        }
      : undefined
  }

  getGlobalNode(knowledgeId: string): KnowledgeNodeResult | undefined {
    this.ensureGlobalReady()
    return this.engine.getNode(GLOBAL_KNOWLEDGE_LIBRARY_ID, knowledgeId)
  }

  getGlobalRelated(knowledgeId: string): KnowledgeRelatedResult {
    this.ensureGlobalReady()
    return this.engine.getRelated(GLOBAL_KNOWLEDGE_LIBRARY_ID, knowledgeId)
  }

  submitGlobalKnowledgeCandidate(input: KnowledgeCandidateInput): KnowledgeMutationResult {
    return this.globalMutator().submitCandidate(input)
  }

  updateGlobalKnowledgeCandidate(
    knowledgeId: string,
    update: KnowledgeCandidateUpdate,
  ): KnowledgeMutationResult {
    return this.globalMutator().updateCandidate(knowledgeId, update)
  }

  reclassifyGlobalKnowledge(knowledgeId: string, categoryId: string): KnowledgeMutationResult {
    return this.globalMutator().reclassify(knowledgeId, categoryId)
  }

  deprecateGlobalKnowledge(knowledgeId: string): KnowledgeMutationResult {
    return this.globalMutator().deprecateKnowledge(knowledgeId)
  }

  addGlobalCategory(input: KnowledgeCategoryCreateInput): KnowledgeCategoryMutationResult {
    return this.globalMutator().addCategory(input)
  }

  renameGlobalCategory(
    categoryId: string,
    update: KnowledgeCategoryUpdateInput,
  ): KnowledgeCategoryMutationResult {
    return this.globalMutator().renameCategory(categoryId, update)
  }

  deprecateGlobalCategory(categoryId: string): KnowledgeCategoryMutationResult {
    return this.globalMutator().deprecateCategory(categoryId)
  }

  registerGlobalSource(input: KnowledgeSourceInput): KnowledgeResolvedSource {
    return this.sourceStore({ kind: 'global' }).registerSource(input)
  }

  listGlobalSources(): readonly KnowledgeSourceRecord[] {
    return this.sourceStore({ kind: 'global' }).listSources()
  }

  registerProjectSource(projectId: string, input: KnowledgeSourceInput): KnowledgeResolvedSource {
    return this.sourceStore({ kind: 'project', projectId }).registerSource(input)
  }

  listProjectSources(projectId: string): readonly KnowledgeSourceRecord[] {
    return this.sourceStore({ kind: 'project', projectId }).listSources()
  }

  resolveSourceReference(reference: string): KnowledgeResolvedSource | undefined {
    const parsed = parseSourceReference(reference)
    return this.sourceStore(parsed.scope).resolveSource(reference)
  }

  recordVerification(input: KnowledgeVerificationInput): KnowledgeVerificationRecord {
    if (input.relation !== 'SUPPORT' && input.relation !== 'CONTRADICT') {
      throw new Error(`非法 Verification relation: ${String(input.relation)}`)
    }
    const target = this.resolveKnowledgeReference(input.knowledgeUri)
    if (!target?.result.node.isLeaf) {
      throw new Error(`Verification target Knowledge 不存在: ${input.knowledgeUri}`)
    }

    let basisKind: 'SOURCE' | 'EVIDENCE'
    let validationClass: KnowledgeVerificationValidationClass = 'REFERENCE'
    if (input.basisRef.startsWith('source://')) {
      const sourceRef = parseSourceReference(input.basisRef)
      const source = this.resolveSourceReference(input.basisRef)
      if (!source) throw new Error(`Verification Source 不存在: ${input.basisRef}`)
      this.assertSourceCanVerify(target.libraryScope, sourceRef.scope)
      basisKind = 'SOURCE'
      validationClass = source.source.kind === 'DOCUMENT' || source.source.kind === 'SPEC' || source.source.kind === 'SVD'
        ? 'DOCUMENT'
        : 'REFERENCE'
    } else if (input.basisRef.startsWith('evidence://')) {
      const evidenceRef = parseEvidenceReference(input.basisRef)
      this.assertEvidenceCanVerify(target.libraryScope, evidenceRef.projectId)
      const evidenceManager = this.evidenceLookupService()
      const evidence = evidenceManager.getEvidence(evidenceRef.projectId, evidenceRef.evidenceId)
      if (!evidence) throw new Error(`Verification Evidence 不存在: ${input.basisRef}`)
      basisKind = 'EVIDENCE'
      const evidenceRecord = evidence as { result?: unknown; metadata?: unknown }
      const metadata = evidenceRecord.metadata && typeof evidenceRecord.metadata === 'object'
        ? evidenceRecord.metadata as Record<string, unknown>
        : {}
      validationClass = evidenceRecord.result === 'PASS'
        && (metadata.knowledgeValidationClass === 'REAL_TEST' || metadata.validationClass === 'REAL_TEST')
        ? 'REAL_TEST'
        : 'REFERENCE'
    } else {
      throw new Error(`Verification basis 只支持 source:// 或 evidence://: ${input.basisRef}`)
    }

    return this.sourceStore(target.libraryScope).appendVerification(
      input,
      basisKind,
      undefined,
      validationClass,
    )
  }

  listVerifications(knowledgeUri: string): readonly KnowledgeVerificationRecord[] {
    const target = this.requireKnowledgeLeaf(knowledgeUri)
    return this.sourceStore(target.libraryScope).listVerifications(target.knowledgeUri)
  }

  getVerificationSummary(knowledgeUri: string): KnowledgeVerificationSummary {
    const target = this.requireKnowledgeLeaf(knowledgeUri)
    return this.sourceStore(target.libraryScope).verificationSummary(target.knowledgeUri)
  }

  refreshProject(projectId: string): KnowledgeProjectIndex {
    const { resourcePath, resourceHandle } = this.resolveKnowledgeResource(projectId)
    try {
      return this.engine.refreshProject(projectId, resourcePath, resourceHandle)
    } catch (error) {
      this.engine.removeProject(projectId)
      throw error
    }
  }

  reindexProject(projectId: string): KnowledgeProjectIndex {
    const { resourcePath, resourceHandle } = this.resolveKnowledgeResource(projectId)
    try {
      return this.engine.reindexProject(projectId, resourcePath, resourceHandle)
    } catch (error) {
      this.engine.removeProject(projectId)
      throw error
    }
  }

  validateProjectLibrary(projectId: string): KnowledgeLibraryValidationResult {
    return this.validationResult(() => this.reindexProject(projectId))
  }

  getIndex(projectId: string): KnowledgeProjectIndex {
    return this.ensureReady(projectId)
  }

  getTaxonomy(projectId: string): KnowledgeTaxonomy | undefined {
    this.ensureReady(projectId)
    return this.engine.getTaxonomy(projectId)
  }

  listCategories(projectId: string, parentId?: string): readonly KnowledgeCategory[] {
    this.ensureReady(projectId)
    return this.engine.listCategories(projectId, parentId)
  }

  getLibraryStats(projectId: string): KnowledgeLibraryStats {
    this.ensureReady(projectId)
    return this.engine.getLibraryStats(projectId)
  }

  listFiles(projectId: string): readonly KnowledgeRouteFile[] {
    this.ensureReady(projectId)
    return this.engine.listFiles(projectId)
  }

  searchKnowledge(request: ProjectQueryRequest): readonly ProjectCandidateResult[] {
    this.ensureReady(request.projectId)
    return this.engine.search(request)
  }

  getNode(projectId: string, knowledgeId: string): KnowledgeNodeResult | undefined {
    this.ensureReady(projectId)
    return this.engine.getNode(projectId, knowledgeId)
  }

  listChildren(projectId: string, nodeId: string): readonly KnowledgeNode[] {
    this.ensureReady(projectId)
    return this.engine.listChildren(projectId, nodeId)
  }

  getRelated(projectId: string, knowledgeId: string): KnowledgeRelatedResult {
    this.ensureReady(projectId)
    return this.engine.getRelated(projectId, knowledgeId)
  }

  submitKnowledgeCandidate(projectId: string, input: KnowledgeCandidateInput): KnowledgeMutationResult {
    return this.projectMutator(projectId).submitCandidate(input)
  }

  updateKnowledgeCandidate(
    projectId: string,
    knowledgeId: string,
    update: KnowledgeCandidateUpdate,
  ): KnowledgeMutationResult {
    return this.projectMutator(projectId).updateCandidate(knowledgeId, update)
  }

  reclassifyKnowledge(projectId: string, knowledgeId: string, categoryId: string): KnowledgeMutationResult {
    return this.projectMutator(projectId).reclassify(knowledgeId, categoryId)
  }

  deprecateKnowledge(projectId: string, knowledgeId: string): KnowledgeMutationResult {
    return this.projectMutator(projectId).deprecateKnowledge(knowledgeId)
  }

  addCategory(projectId: string, input: KnowledgeCategoryCreateInput): KnowledgeCategoryMutationResult {
    return this.projectMutator(projectId).addCategory(input)
  }

  renameCategory(
    projectId: string,
    categoryId: string,
    update: KnowledgeCategoryUpdateInput,
  ): KnowledgeCategoryMutationResult {
    return this.projectMutator(projectId).renameCategory(categoryId, update)
  }

  deprecateCategory(projectId: string, categoryId: string): KnowledgeCategoryMutationResult {
    return this.projectMutator(projectId).deprecateCategory(categoryId)
  }

  removeProject(projectId: string): boolean {
    return this.engine.removeProject(projectId)
  }

  private validationResult(action: () => KnowledgeProjectIndex): KnowledgeLibraryValidationResult {
    try {
      const snapshot = action()
      return {
        valid: true,
        errors: [],
        warnings: snapshot.warnings,
        ...(snapshot.sourceFingerprint ? { sourceFingerprint: snapshot.sourceFingerprint } : {}),
      }
    } catch (error) {
      return {
        valid: false,
        errors: [error instanceof Error ? error.message : String(error)],
        warnings: [],
      }
    }
  }

  private requireKnowledgeLeaf(reference: string): KnowledgeResolvedReference {
    const target = this.resolveKnowledgeReference(reference)
    if (!target?.result.node.isLeaf) throw new Error(`Knowledge 不存在: ${reference}`)
    return target
  }

  private toScopedCandidate(
    libraryScope: KnowledgeLibraryScope,
    candidate: ProjectCandidateResult,
  ): KnowledgeScopedCandidate {
    return {
      libraryScope,
      knowledgeUri: qualifyKnowledgeId(libraryScope, candidate.id),
      candidate,
    }
  }

  private projectMutator(projectId: string): KnowledgeLibraryMutator {
    this.ensureReady(projectId)
    const { resourcePath } = this.resolveKnowledgeResource(projectId)
    return new KnowledgeLibraryMutator(
      this.engine,
      projectId,
      resourcePath,
      () => this.reindexProject(projectId),
    )
  }

  private globalMutator(): KnowledgeLibraryMutator {
    const root = this.requireGlobalRoot()
    this.ensureGlobalReady()
    return new KnowledgeLibraryMutator(
      this.engine,
      GLOBAL_KNOWLEDGE_LIBRARY_ID,
      root,
      () => this.reindexGlobalLibrary(),
    )
  }

  private sourceStore(scope: KnowledgeLibraryScope): KnowledgeSourceVerificationStore {
    return new KnowledgeSourceVerificationStore(this.libraryRoot(scope), scope)
  }

  private libraryRoot(scope: KnowledgeLibraryScope): string {
    this.ensureScopeReady(scope)
    return scope.kind === 'global'
      ? this.requireGlobalRoot()
      : this.resolveKnowledgeResource(scope.projectId).resourcePath
  }

  private ensureScopeReady(scope: KnowledgeLibraryScope): void {
    if (scope.kind === 'global') this.ensureGlobalReady()
    else this.ensureReady(scope.projectId)
  }

  private evidenceLookupService(): EvidenceLookupService {
    const service = this.runtimeContext.get('evidenceStateManager') as EvidenceLookupService | undefined
    if (!service) {
      throw new Error('Evidence / State Manager 未加载；无法建立 Evidence Verification')
    }
    return service
  }

  private assertSourceCanVerify(target: KnowledgeLibraryScope, source: KnowledgeLibraryScope): void {
    if (target.kind === 'global') {
      if (source.kind !== 'global') {
        throw new Error('Global Knowledge 的 Source Verification 必须引用 Global Source')
      }
      return
    }
    if (source.kind === 'project' && source.projectId !== target.projectId) {
      throw new Error('Project Knowledge 不能引用其他 Project 的私有 Source 作为 Verification')
    }
  }

  private assertEvidenceCanVerify(target: KnowledgeLibraryScope, evidenceProjectId: string): void {
    if (target.kind === 'project' && target.projectId !== evidenceProjectId) {
      throw new Error('Project Knowledge 只能引用本 Project Evidence 作为 Verification')
    }
  }

  private resolveKnowledgeResource(projectId: string): {
    readonly resourcePath: string
    readonly resourceHandle: string
  } {
    const project = this.runtimeContext.projectManager.getProjectContext(projectId)
    if (!project) {
      this.engine.removeProject(projectId)
      throw new Error(`Knowledge Manager 找不到项目: ${projectId}`)
    }
    if (project.resourceStandards.knowledge !== 'knowledge-v0.1') {
      this.engine.removeProject(projectId)
      throw new Error(
        `${projectId} Knowledge 接口拒绝接入: 不支持 Node 标准 ${project.resourceStandards.knowledge}`,
      )
    }
    const resourcePath = this.runtimeContext.projectManager.getResourcePath(projectId, 'knowledge')
    if (!resourcePath) {
      this.engine.removeProject(projectId)
      throw new Error(`${projectId} Knowledge 接口拒绝接入: 无法解析资源路径`)
    }
    return {
      resourcePath,
      resourceHandle: project.resources.knowledge,
    }
  }

  private requireGlobalRoot(): string {
    if (!this.globalKnowledgeRoot) {
      throw new Error('Global Knowledge 尚未挂载；请配置 AGENT_HARNESS_GLOBAL_KNOWLEDGE_ROOT 或调用 mountGlobalLibrary')
    }
    return this.globalKnowledgeRoot
  }

  private ensureGlobalReady(): KnowledgeProjectIndex {
    const root = this.requireGlobalRoot()
    return this.engine.getIndex(GLOBAL_KNOWLEDGE_LIBRARY_ID) ?? this.mountGlobalLibrary(root)
  }

  private ensureReady(projectId: string): KnowledgeProjectIndex {
    const project = this.runtimeContext.projectManager.getProjectContext(projectId)
    if (!project) {
      this.engine.removeProject(projectId)
      throw new Error(`Knowledge Manager 找不到项目: ${projectId}`)
    }
    return this.engine.getIndex(projectId) ?? this.refreshProject(projectId)
  }
}

declare module '@deepseek-ai/cordis' {
  interface Context {
    knowledgeManager: KnowledgeManagerService
  }
}

export default KnowledgeManagerService
