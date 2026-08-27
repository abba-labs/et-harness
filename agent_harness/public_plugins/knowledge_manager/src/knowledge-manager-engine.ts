import { createHash } from 'node:crypto'
import { existsSync, readFileSync, readdirSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import type {
  ProjectCandidateResult,
  ProjectQueryRequest,
  ProjectResourceIndexV01,
} from '@agent-harness/project-contract'
import {
  assertProjectResourceIndex,
  parseNumberedResourceFileName,
  parseYamlFrontMatter,
} from '@agent-harness/project-contract'
import { renderGeneratedKnowledgeIndex } from './knowledge-index-generator.js'
import { parseKnowledgeFile } from './knowledge-parser.js'
import {
  categoryPathTitles,
  listCategoryDescendants,
  parseKnowledgeTaxonomy,
} from './taxonomy-parser.js'
import type {
  KnowledgeCategory,
  KnowledgeLibraryStats,
  KnowledgeNode,
  KnowledgeNodeResult,
  KnowledgeProjectIndex,
  KnowledgeRelatedResult,
  KnowledgeRouteFile,
  KnowledgeStatus,
  KnowledgeTaxonomy,
} from './contracts.js'

interface ProjectCache {
  readonly snapshot: KnowledgeProjectIndex
  readonly resourceHandle: string
  readonly files: ReadonlyMap<string, KnowledgeRouteFile>
  readonly nodes: ReadonlyMap<string, KnowledgeNode>
  readonly termIndex: ReadonlyMap<string, ReadonlySet<string>>
  readonly categoryIndex: ReadonlyMap<string, ReadonlySet<string>>
  readonly outgoingRefs: ReadonlyMap<string, ReadonlySet<string>>
  readonly incomingRefs: ReadonlyMap<string, ReadonlySet<string>>
}

interface ScoredFile {
  readonly file: KnowledgeRouteFile
  readonly score: number
  readonly reasons: readonly string[]
}

const KNOWLEDGE_ID_RE = /^K\d{3}(?:\.\d{3})*$/
const VALID_STATUSES = new Set<KnowledgeStatus>(['CANDIDATE', 'VALIDATED', 'FULL_VALIDATED', 'DEPRECATED'])
const DEFAULT_SEARCH_STATUSES = new Set<KnowledgeStatus>([
  'FULL_VALIDATED',
  'VALIDATED',
  'CANDIDATE',
  'DEPRECATED',
])
const STATUS_RANK: Readonly<Record<KnowledgeStatus, number>> = {
  FULL_VALIDATED: 4,
  VALIDATED: 3,
  CANDIDATE: 2,
  DEPRECATED: 1,
}

const knowledgeTrustTier = (status: KnowledgeStatus): string => {
  if (status === 'FULL_VALIDATED') return 'VERIFIED'
  if (status === 'VALIDATED') return 'SUPPORTED'
  if (status === 'CANDIDATE') return 'EXPLORATORY'
  return 'HISTORICAL'
}

const knowledgeUsagePolicy = (status: KnowledgeStatus): string => {
  if (status === 'FULL_VALIDATED') return 'PRIMARY_REFERENCE'
  if (status === 'VALIDATED') return 'PRIMARY_REFERENCE_WITH_SCOPE'
  if (status === 'CANDIDATE') return 'HYPOTHESIS_AND_TEST_LEAD_ONLY'
  return 'HISTORY_AND_ANTI_PATTERN_ONLY'
}

const knowledgeWarnings = (status: KnowledgeStatus): string[] | undefined => {
  if (status === 'CANDIDATE') {
    return [
      'Knowledge status = CANDIDATE; 可作为假设、排查方向和测试线索，但不得独立支持确定性结论或高风险操作',
    ]
  }
  if (status === 'DEPRECATED') {
    return [
      'Knowledge status = DEPRECATED; 仅用于历史背景、反例和迁移线索，不得作为当前实现依据',
    ]
  }
  return undefined
}

const candidateKnowledgeStatus = (candidate: ProjectCandidateResult): KnowledgeStatus | undefined => {
  const status = candidate.metadata?.status
  return typeof status === 'string' && VALID_STATUSES.has(status as KnowledgeStatus)
    ? status as KnowledgeStatus
    : undefined
}

const selectKnowledgeResults = (
  candidates: readonly ProjectCandidateResult[],
  limit: number,
  explicitStatusFilter: boolean,
): readonly ProjectCandidateResult[] => {
  const ordered = [...candidates].sort((left, right) => {
    const relevance = (right.relevance ?? 0) - (left.relevance ?? 0)
    if (relevance !== 0) return relevance
    const leftStatus = candidateKnowledgeStatus(left)
    const rightStatus = candidateKnowledgeStatus(right)
    const trust = (rightStatus ? STATUS_RANK[rightStatus] : 0) - (leftStatus ? STATUS_RANK[leftStatus] : 0)
    return trust !== 0 ? trust : left.id.localeCompare(right.id)
  })
  if (explicitStatusFilter) return ordered.slice(0, limit)

  const reliable = ordered.filter(item => {
    const status = candidateKnowledgeStatus(item)
    return status === 'FULL_VALIDATED' || status === 'VALIDATED'
  })
  const exploratory = ordered.filter(item => candidateKnowledgeStatus(item) === 'CANDIDATE')
  const historical = ordered.filter(item => candidateKnowledgeStatus(item) === 'DEPRECATED')
  const selected: ProjectCandidateResult[] = []
  const add = (items: readonly ProjectCandidateResult[], maximum: number) => {
    for (const item of items.slice(0, Math.max(0, maximum))) {
      if (!selected.some(existing => existing.id === item.id)) selected.push(item)
    }
  }

  add(reliable, Math.max(1, Math.ceil(limit * 0.625)))
  if (limit >= 2) add(exploratory, Math.max(1, Math.floor(limit * 0.25)))
  if (limit >= 6) add(historical, 1)
  add(ordered, limit)
  return selected.slice(0, limit)
}

const normalize = (value: string): string =>
  value.toLowerCase().replace(/[^a-z0-9\u4e00-\u9fff]+/g, '')

const extractTerms = (value: string): string[] => {
  const raw = value.toLowerCase().match(/[a-z0-9_.-]+|[\u4e00-\u9fff]+/g) ?? []
  const terms = new Set<string>()

  for (const token of raw) {
    const normalizedToken = normalize(token)
    if (!normalizedToken) continue
    terms.add(normalizedToken)
    if (/^[\u4e00-\u9fff]+$/.test(token) && token.length > 2) {
      for (let index = 0; index < token.length - 1; index += 1) {
        terms.add(token.slice(index, index + 2))
      }
    }
  }
  return [...terms]
}

const scopeTerms = (scope: ProjectQueryRequest['scope']): string[] => {
  if (!scope) return []
  return Object.values(scope).flatMap(value => {
    if (typeof value === 'string') return extractTerms(value)
    if (Array.isArray(value)) {
      return value.flatMap(item => typeof item === 'string' ? extractTerms(item) : [])
    }
    return []
  })
}

const requestedStatuses = (filters: ProjectQueryRequest['filters']): ReadonlySet<KnowledgeStatus> => {
  const raw = filters?.status
  if (raw === undefined) return DEFAULT_SEARCH_STATUSES

  const values = Array.isArray(raw) ? raw : [raw]
  if (values.length === 0) throw new Error('filters.status 不能为空数组')

  const statuses: KnowledgeStatus[] = []
  for (const value of values) {
    if (typeof value !== 'string') throw new Error('filters.status 必须是字符串或字符串数组')
    const normalized = value.toUpperCase()
    if (!VALID_STATUSES.has(normalized as KnowledgeStatus)) {
      throw new Error(`非法 Knowledge status filter: ${value}`)
    }
    statuses.push(normalized as KnowledgeStatus)
  }
  return new Set(statuses)
}

const requestedTags = (filters: ProjectQueryRequest['filters']): readonly string[] => {
  const raw = filters?.tags
  if (raw === undefined) return []
  const values = Array.isArray(raw) ? raw : [raw]
  if (values.some(value => typeof value !== 'string' || !value.trim())) {
    throw new Error('filters.tags 必须是非空字符串或字符串数组')
  }
  return values.map(value => normalize(String(value))).filter(Boolean)
}

const addIndexValue = (
  index: Map<string, Set<string>>,
  key: string,
  value: string,
): void => {
  const values = index.get(key) ?? new Set<string>()
  values.add(value)
  index.set(key, values)
}

const fingerprintSources = (sources: readonly [string, string][]): string => {
  const hash = createHash('sha256')
  for (const [name, content] of [...sources].sort((a, b) => a[0].localeCompare(b[0]))) {
    hash.update(name)
    hash.update('\0')
    hash.update(content)
    hash.update('\0')
  }
  return `sha256:${hash.digest('hex')}`
}

export class KnowledgeManagerEngine {
  private readonly projects = new Map<string, ProjectCache>()

  refreshProject(
    projectId: string,
    resourcePath: string,
    resourceHandle: string,
  ): KnowledgeProjectIndex {
    this.projects.delete(projectId)
    return existsSync(join(resourcePath, 'TAXONOMY.yaml'))
      ? this.refreshLibraryV02(projectId, resourcePath, resourceHandle)
      : this.refreshLegacyV01(projectId, resourcePath, resourceHandle)
  }

  reindexProject(
    projectId: string,
    resourcePath: string,
    resourceHandle: string,
  ): KnowledgeProjectIndex {
    return this.refreshProject(projectId, resourcePath, resourceHandle)
  }

  removeProject(projectId: string): boolean {
    return this.projects.delete(projectId)
  }

  clear(): void {
    this.projects.clear()
  }

  getIndex(projectId: string): KnowledgeProjectIndex | undefined {
    return this.projects.get(projectId)?.snapshot
  }

  getTaxonomy(projectId: string): KnowledgeTaxonomy | undefined {
    return this.requireProject(projectId).snapshot.taxonomy
  }

  listCategories(projectId: string, parentId?: string): readonly KnowledgeCategory[] {
    const taxonomy = this.requireProject(projectId).snapshot.taxonomy
    if (!taxonomy) return []
    const ids = parentId
      ? taxonomy.categories[parentId]?.children ?? []
      : taxonomy.roots
    return ids
      .map(id => taxonomy.categories[id])
      .filter((item): item is KnowledgeCategory => item !== undefined)
  }

  getLibraryStats(projectId: string): KnowledgeLibraryStats {
    const snapshot = this.requireProject(projectId).snapshot
    return {
      categoryCount: snapshot.taxonomy ? Object.keys(snapshot.taxonomy.categories).length : 0,
      knowledgeCount: snapshot.knowledgeCount,
      statusCounts: snapshot.statusCounts,
      categoryCounts: snapshot.categoryCounts ?? {},
    }
  }

  listFiles(projectId: string): readonly KnowledgeRouteFile[] {
    return this.requireProject(projectId).snapshot.files
  }

  getNode(projectId: string, nodeId: string): KnowledgeNodeResult | undefined {
    const cache = this.projects.get(projectId)
    const node = cache?.nodes.get(nodeId)
    return node ? { projectId, node } : undefined
  }

  listChildren(projectId: string, nodeId: string): readonly KnowledgeNode[] {
    const cache = this.requireProject(projectId)
    const node = cache.nodes.get(nodeId)
    if (!node) return []
    return node.children
      .map(id => cache.nodes.get(id))
      .filter((item): item is KnowledgeNode => item !== undefined)
  }

  getRelated(projectId: string, knowledgeId: string): KnowledgeRelatedResult {
    const cache = this.requireProject(projectId)
    if (!cache.nodes.has(knowledgeId)) throw new Error(`Knowledge Node 不存在: ${knowledgeId}`)
    return {
      projectId,
      sourceId: knowledgeId,
      outgoing: [...(cache.outgoingRefs.get(knowledgeId) ?? [])].sort(),
      incoming: [...(cache.incomingRefs.get(knowledgeId) ?? [])].sort(),
    }
  }

  search(request: ProjectQueryRequest): readonly ProjectCandidateResult[] {
    const cache = this.requireProject(request.projectId)
    const query = request.query.trim()
    const exactId = query.toUpperCase()
    if (query && KNOWLEDGE_ID_RE.test(exactId)) {
      const node = cache.nodes.get(exactId)
      return node
        ? [this.toCandidate(request.projectId, cache, node, 1, ['Knowledge Node ID 精确匹配'])]
        : []
    }

    return cache.snapshot.libraryMode === 'library-v0.2'
      ? this.searchLibraryV02(cache, request)
      : this.searchLegacyV01(cache, request)
  }

  private refreshLibraryV02(
    projectId: string,
    resourcePath: string,
    resourceHandle: string,
  ): KnowledgeProjectIndex {
    const taxonomyPath = join(resourcePath, 'TAXONOMY.yaml')
    const taxonomyText = readFileSync(taxonomyPath, 'utf-8')
    const taxonomy = parseKnowledgeTaxonomy(taxonomyText)
    const numbered = readdirSync(resourcePath, { withFileTypes: true })
      .filter(entry => entry.isFile())
      .map(entry => entry.name)
      .map(file => ({ file, parsed: parseNumberedResourceFileName('knowledge', file) }))
      .filter((item): item is { file: string; parsed: NonNullable<typeof item.parsed> } => item.parsed !== undefined)
      .sort((a, b) => a.parsed.number.localeCompare(b.parsed.number))

    const files = new Map<string, KnowledgeRouteFile>()
    const nodes = new Map<string, KnowledgeNode>()
    const termIndex = new Map<string, Set<string>>()
    const categoryIndex = new Map<string, Set<string>>()
    const outgoingRefs = new Map<string, Set<string>>()
    const incomingRefs = new Map<string, Set<string>>()
    const categoryCounts: Record<string, number> = {}
    const statusCounts: Record<KnowledgeStatus, number> = {
      CANDIDATE: 0,
      VALIDATED: 0,
      FULL_VALIDATED: 0,
      DEPRECATED: 0,
    }
    const warnings: string[] = []
    const sources: Array<[string, string]> = [['TAXONOMY.yaml', taxonomyText]]
    let knowledgeCount = 0

    for (const item of numbered) {
      const text = readFileSync(join(resourcePath, item.file), 'utf-8')
      sources.push([item.file, text])
      const parsed = parseKnowledgeFile(item.parsed.fileId, item.file, text)
      const root = parsed.nodes.find(node => node.id === item.parsed.fileId)
      if (!root) throw new Error(`${item.file} 缺少根 Knowledge Node ${item.parsed.fileId}`)

      const usedCategories = new Set<string>()
      let leafCount = 0
      for (const node of parsed.nodes) {
        if (nodes.has(node.id)) throw new Error(`${projectId} Knowledge Node ID 重复: ${node.id}`)
        nodes.set(node.id, node)
        if (!node.isLeaf) continue
        leafCount += 1
        knowledgeCount += 1
        if (!node.status) throw new Error(`${node.id} 缺少 Status`)
        statusCounts[node.status] += 1
        if (!node.category) {
          throw new Error(`${item.file} Knowledge Leaf ${node.id} 在 library-v0.2 下必须提供 Category`)
        }

        const category = taxonomy.categories[node.category]
        if (!category) throw new Error(`${node.id} Category 不存在: ${node.category}`)
        if (category.status !== 'ACTIVE' && node.status !== 'DEPRECATED') {
          throw new Error(`${node.id} 非 DEPRECATED Knowledge 不允许挂载到 DEPRECATED Category: ${node.category}`)
        }
        usedCategories.add(node.category)
        categoryCounts[node.category] = (categoryCounts[node.category] ?? 0) + 1
        addIndexValue(categoryIndex, node.category, node.id)

        const searchable = [
          node.title,
          node.fact ?? '',
          node.scope ?? '',
          ...node.tags,
          ...categoryPathTitles(taxonomy, node.category),
        ]
        for (const field of searchable) {
          for (const term of extractTerms(field)) addIndexValue(termIndex, term, node.id)
        }

        const outgoing = new Set(node.refs)
        outgoingRefs.set(node.id, outgoing)
        for (const ref of outgoing) addIndexValue(incomingRefs, ref, node.id)
      }

      const aliases = [...usedCategories]
        .flatMap(categoryId => {
          const category = taxonomy.categories[categoryId]
          return category ? [category.title, ...category.aliases] : []
        })
        .filter((value, index, array) => array.indexOf(value) === index)
        .slice(0, 24)

      warnings.push(...parsed.warnings)
      files.set(item.parsed.fileId, {
        id: item.parsed.fileId,
        file: item.file,
        title: root.title,
        summary: `${leafCount} knowledge leaves`,
        aliases,
        nodes: parsed.nodes.map(node => node.id),
      })
    }

    const sourceFingerprint = fingerprintSources(sources)
    const snapshot: KnowledgeProjectIndex = {
      projectId,
      state: 'ready',
      libraryMode: 'library-v0.2',
      resourcePath,
      files: [...files.values()],
      nodeCount: nodes.size,
      knowledgeCount,
      statusCounts,
      taxonomy,
      categoryCounts,
      sourceFingerprint,
      warnings,
      builtAt: new Date().toISOString(),
    }

    const cache: ProjectCache = {
      snapshot,
      resourceHandle,
      files,
      nodes,
      termIndex,
      categoryIndex,
      outgoingRefs,
      incomingRefs,
    }
    this.projects.set(projectId, cache)

    writeFileSync(join(resourcePath, '00_INDEX.md'), renderGeneratedKnowledgeIndex(snapshot), 'utf-8')
    return snapshot
  }

  private refreshLegacyV01(
    projectId: string,
    resourcePath: string,
    resourceHandle: string,
  ): KnowledgeProjectIndex {
    const indexPath = join(resourcePath, '00_INDEX.md')
    if (!existsSync(indexPath)) {
      throw new Error(`${projectId} Knowledge 接口拒绝接入: 缺少 knowledge/00_INDEX.md`)
    }

    const parsedIndex = parseYamlFrontMatter<ProjectResourceIndexV01>(readFileSync(indexPath, 'utf-8'))
    const availableFiles = readdirSync(resourcePath, { withFileTypes: true })
      .filter(entry => entry.isFile())
      .map(entry => entry.name)
    assertProjectResourceIndex('knowledge', parsedIndex.data, availableFiles)

    const files = new Map<string, KnowledgeRouteFile>()
    const nodes = new Map<string, KnowledgeNode>()
    const statusCounts: Record<KnowledgeStatus, number> = {
      CANDIDATE: 0,
      VALIDATED: 0,
      FULL_VALIDATED: 0,
      DEPRECATED: 0,
    }
    const warnings: string[] = []
    let knowledgeCount = 0

    for (const entry of parsedIndex.data.files) {
      const parsed = parseKnowledgeFile(entry.id, entry.file, readFileSync(join(resourcePath, entry.file), 'utf-8'))
      for (const node of parsed.nodes) {
        if (nodes.has(node.id)) throw new Error(`${projectId} Knowledge Node ID 重复: ${node.id}`)
        nodes.set(node.id, node)
        if (node.isLeaf && node.status) {
          knowledgeCount += 1
          statusCounts[node.status] += 1
        }
      }
      warnings.push(...parsed.warnings)
      files.set(entry.id, { ...entry, nodes: parsed.nodes.map(node => node.id) })
    }

    const snapshot: KnowledgeProjectIndex = {
      projectId,
      state: 'ready',
      libraryMode: 'legacy-v0.1',
      resourcePath,
      files: [...files.values()],
      nodeCount: nodes.size,
      knowledgeCount,
      statusCounts,
      warnings,
      builtAt: new Date().toISOString(),
    }
    this.projects.set(projectId, {
      snapshot,
      resourceHandle,
      files,
      nodes,
      termIndex: new Map(),
      categoryIndex: new Map(),
      outgoingRefs: new Map(),
      incomingRefs: new Map(),
    })
    return snapshot
  }

  private searchLibraryV02(
    cache: ProjectCache,
    request: ProjectQueryRequest,
  ): readonly ProjectCandidateResult[] {
    const taxonomy = cache.snapshot.taxonomy
    if (!taxonomy) throw new Error('library-v0.2 缺少 taxonomy cache')
    const allowedStatuses = requestedStatuses(request.filters)
    const tags = requestedTags(request.filters)
    const queryTerms = [...new Set([
      ...extractTerms(request.query),
      ...scopeTerms(request.scope),
    ])]

    const rawCategory = request.filters?.category
    if (rawCategory !== undefined && typeof rawCategory !== 'string') {
      throw new Error('filters.category 必须是 C-ID 字符串')
    }
    const categoryId = typeof rawCategory === 'string' ? rawCategory : undefined
    let allowedCategories: ReadonlySet<string> | undefined
    if (categoryId) {
      if (!taxonomy.categories[categoryId]) throw new Error(`Category 不存在: ${categoryId}`)
      const includeDescendants = request.filters?.includeDescendants !== false
      allowedCategories = new Set(
        includeDescendants
          ? listCategoryDescendants(taxonomy, categoryId)
          : [categoryId],
      )
    }

    const candidateIds = new Set<string>()
    if (queryTerms.length > 0) {
      for (const term of queryTerms) {
        for (const id of cache.termIndex.get(term) ?? []) candidateIds.add(id)
      }
      if (candidateIds.size === 0) return []
    } else if (allowedCategories) {
      for (const allowed of allowedCategories) {
        for (const id of cache.categoryIndex.get(allowed) ?? []) candidateIds.add(id)
      }
    } else {
      throw new Error('knowledge search 至少需要 query 或 filters.category')
    }

    const candidates: ProjectCandidateResult[] = []
    const normalizedQuery = normalize(request.query)
    for (const id of candidateIds) {
      const node = cache.nodes.get(id)
      if (!node?.isLeaf || !node.status || !allowedStatuses.has(node.status)) continue
      if (allowedCategories && (!node.category || !allowedCategories.has(node.category))) continue
      if (tags.length > 0) {
        const nodeTags = new Set(node.tags.map(normalize))
        if (!tags.every(tag => nodeTags.has(tag))) continue
      }

      const fields = [node.title, node.fact ?? '', node.scope ?? '', ...node.tags]
      const fieldTerms = new Set(fields.flatMap(extractTerms))
      if (node.category) {
        for (const term of categoryPathTitles(taxonomy, node.category).flatMap(extractTerms)) {
          fieldTerms.add(term)
        }
      }
      const matched = queryTerms.filter(term => fieldTerms.has(term))
      let relevance = queryTerms.length > 0
        ? 0.45 + 0.5 * (matched.length / queryTerms.length)
        : 0.65
      const reasons: string[] = []
      if (matched.length > 0) reasons.push(`Machine index terms 命中 ${matched.length}/${queryTerms.length}`)
      if (normalizedQuery && normalize(node.title) === normalizedQuery) {
        relevance = 0.99
        reasons.push('Knowledge title 精确匹配')
      }
      if (categoryId) reasons.push(`Category filter: ${categoryId}`)
      candidates.push(this.toCandidate(request.projectId, cache, node, Math.min(1, relevance), reasons))
    }

    return selectKnowledgeResults(
      candidates,
      Math.max(1, request.limit ?? 8),
      request.filters?.status !== undefined,
    )
  }

  private searchLegacyV01(
    cache: ProjectCache,
    request: ProjectQueryRequest,
  ): readonly ProjectCandidateResult[] {
    const query = request.query.trim()
    if (!query) return []
    const allowedStatuses = requestedStatuses(request.filters)
    const terms = [...new Set([...extractTerms(query), ...scopeTerms(request.scope)])]
    const fileCandidates = this.scoreLegacyFiles(cache, query, terms)
    if (fileCandidates.length === 0) return []

    const candidates: ProjectCandidateResult[] = []
    for (const scoredFile of fileCandidates) {
      for (const nodeId of scoredFile.file.nodes) {
        const node = cache.nodes.get(nodeId)
        if (!node) continue
        const nodeScore = this.scoreLegacyNode(cache, node, query, terms)
        const isFileRoot = node.id === scoredFile.file.id
        if (node.isLeaf) {
          if (!node.status || !allowedStatuses.has(node.status) || nodeScore.score <= 0) continue
          candidates.push(this.toCandidate(
            request.projectId,
            cache,
            node,
            Math.min(1, 0.3 * scoredFile.score + 0.7 * nodeScore.score),
            [...scoredFile.reasons, ...nodeScore.reasons],
          ))
        } else if (nodeScore.score >= 0.75 || isFileRoot) {
          candidates.push(this.toCandidate(
            request.projectId,
            cache,
            node,
            Math.min(0.9, isFileRoot ? Math.max(scoredFile.score, nodeScore.score) : nodeScore.score),
            [...scoredFile.reasons, ...nodeScore.reasons],
          ))
        }
      }
    }

    return selectKnowledgeResults(
      candidates,
      Math.max(1, request.limit ?? 8),
      request.filters?.status !== undefined,
    )
  }

  private toCandidate(
    projectId: string,
    cache: ProjectCache,
    node: KnowledgeNode,
    relevance: number,
    reasons: readonly string[],
  ): ProjectCandidateResult {
    const warnings = node.status ? knowledgeWarnings(node.status) : undefined
    return {
      projectId,
      id: node.id,
      title: node.title,
      type: node.isLeaf ? 'knowledge-leaf' : 'knowledge-branch',
      location: node.location,
      summary: node.fact ?? `Knowledge branch: ${node.title}`,
      relevance,
      matchReasons: reasons,
      provenance: {
        resource: cache.resourceHandle,
        location: node.location,
      },
      metadata: {
        fileId: node.fileId,
        parentId: node.parentId,
        children: node.children,
        isLeaf: node.isLeaf,
        status: node.status,
        trustTier: node.status ? knowledgeTrustTier(node.status) : undefined,
        usagePolicy: node.status ? knowledgeUsagePolicy(node.status) : undefined,
        category: node.category,
        fact: node.fact,
        scope: node.scope,
        sourceProvenance: node.provenance,
        tags: node.tags,
        refs: node.refs,
      },
      ...(warnings ? { warnings } : {}),
    }
  }

  private requireProject(projectId: string): ProjectCache {
    const cache = this.projects.get(projectId)
    if (!cache) throw new Error(`Knowledge Manager 尚未为项目建立索引: ${projectId}`)
    return cache
  }

  private scoreLegacyFiles(
    cache: ProjectCache,
    query: string,
    terms: readonly string[],
  ): readonly ScoredFile[] {
    const normalizedQuery = normalize(query)
    const scored: ScoredFile[] = []
    for (const file of cache.files.values()) {
      const reasons: string[] = []
      let score = 0
      if (normalize(file.id) === normalizedQuery) {
        score = 1
        reasons.push('File ID 精确匹配')
      }
      if (file.aliases.some(alias => normalize(alias) === normalizedQuery)) {
        score = Math.max(score, 0.96)
        reasons.push('Index alias 精确匹配')
      }
      if (normalizedQuery && normalize(file.title).includes(normalizedQuery)) {
        score = Math.max(score, 0.9)
        reasons.push('Index title 匹配')
      }
      const coverage = this.termCoverage(terms, [file.title, file.summary, ...file.aliases])
      if (coverage > 0) {
        score = Math.max(score, 0.45 + 0.45 * coverage)
        reasons.push(`Index route terms 覆盖 ${(coverage * 100).toFixed(0)}%`)
      }
      if (score > 0) scored.push({ file, score, reasons })
    }
    return scored.sort((a, b) => b.score - a.score || a.file.id.localeCompare(b.file.id)).slice(0, 4)
  }

  private scoreLegacyNode(
    cache: ProjectCache,
    node: KnowledgeNode,
    query: string,
    terms: readonly string[],
  ): { readonly score: number; readonly reasons: readonly string[] } {
    const normalizedQuery = normalize(query)
    const reasons: string[] = []
    let score = 0
    if (normalize(node.title) === normalizedQuery) {
      score = 0.98
      reasons.push('Knowledge title 精确匹配')
    } else if (normalizedQuery && normalize(node.title).includes(normalizedQuery)) {
      score = 0.9
      reasons.push('Knowledge title 包含匹配')
    }
    const fields = [
      node.title,
      ...this.ancestorTitles(cache, node),
      node.fact ?? '',
      node.scope ?? '',
      ...node.tags,
      ...node.refs,
    ]
    const coverage = this.termCoverage(terms, fields)
    if (coverage > 0) {
      score = Math.max(score, 0.35 + 0.6 * coverage)
      reasons.push(`Knowledge tree terms 覆盖 ${(coverage * 100).toFixed(0)}%`)
    }
    return { score, reasons }
  }

  private ancestorTitles(cache: ProjectCache, node: KnowledgeNode): string[] {
    const titles: string[] = []
    let parentId = node.parentId
    while (parentId) {
      const parent = cache.nodes.get(parentId)
      if (!parent) break
      titles.push(parent.title)
      parentId = parent.parentId
    }
    return titles
  }

  private termCoverage(terms: readonly string[], fields: readonly string[]): number {
    if (terms.length === 0) return 0
    const fieldTerms = new Set(fields.flatMap(extractTerms))
    return terms.filter(term => fieldTerms.has(term)).length / terms.length
  }
}
