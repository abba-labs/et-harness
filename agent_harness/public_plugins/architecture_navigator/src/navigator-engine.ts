import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import type {
  ProjectCandidateResult,
  ProjectQueryRequest,
  ProjectResourceIndexV01,
} from '@agent-harness/project-contract'
import {
  assertProjectResourceIndex,
  parseYamlFrontMatter,
} from '@agent-harness/project-contract'
import { parseArchitectureFile } from './architecture-parser.js'
import type {
  ArchitectureNode,
  ArchitectureNodeResult,
  ArchitectureProjectIndex,
  ArchitectureRouteFile,
} from './contracts.js'

interface ProjectCache {
  readonly snapshot: ArchitectureProjectIndex
  readonly resourceHandle: string
  readonly files: ReadonlyMap<string, ArchitectureRouteFile>
  readonly nodes: ReadonlyMap<string, ArchitectureNode>
}

interface ScoredFile {
  readonly file: ArchitectureRouteFile
  readonly score: number
  readonly reasons: readonly string[]
}

const ARCHITECTURE_RELATION_RE = /^A\d{3}(?:\.\d{3})*$/

const normalize = (value: string): string =>
  value.toLowerCase().replace(/[^a-z0-9\u4e00-\u9fff]+/g, '')

const extractTerms = (value: string): string[] => {
  const raw = value.toLowerCase().match(/[a-z0-9]+|[\u4e00-\u9fff]+/g) ?? []
  const terms = new Set<string>()

  for (const token of raw) {
    if (/^[\u4e00-\u9fff]+$/.test(token) && token.length > 4) {
      terms.add(token)
      for (let index = 0; index < token.length - 1; index += 1) {
        terms.add(token.slice(index, index + 2))
      }
    } else {
      terms.add(token)
    }
  }

  return [...terms].filter(Boolean)
}

const scopeTerms = (scope: ProjectQueryRequest['scope']): string[] => {
  if (!scope) return []
  return Object.values(scope)
    .flatMap(value => {
      if (typeof value === 'string') return extractTerms(value)
      if (Array.isArray(value)) {
        return value.flatMap(item => typeof item === 'string' ? extractTerms(item) : [])
      }
      return []
    })
}

const termCoverage = (terms: readonly string[], fields: readonly string[]): number => {
  if (terms.length === 0) return 0
  const normalizedFields = fields.map(normalize)
  const matched = terms.filter(term => {
    const normalizedTerm = normalize(term)
    return normalizedTerm && normalizedFields.some(field => field.includes(normalizedTerm))
  })
  return matched.length / terms.length
}

const firstLine = (value: string): string | undefined =>
  value.split('\n').map(line => line.trim()).find(Boolean)

export class ArchitectureNavigatorEngine {
  private readonly projects = new Map<string, ProjectCache>()

  refreshProject(
    projectId: string,
    resourcePath: string,
    resourceHandle: string,
  ): ArchitectureProjectIndex {
    const indexPath = join(resourcePath, '00_INDEX.md')
    if (!existsSync(indexPath)) {
      throw new Error(`${projectId} Architecture 接口拒绝接入: 缺少 architecture/00_INDEX.md`)
    }

    const indexText = readFileSync(indexPath, 'utf-8')
    const parsedIndex = parseYamlFrontMatter<ProjectResourceIndexV01>(indexText)
    const availableFiles = readdirSync(resourcePath, { withFileTypes: true })
      .filter(entry => entry.isFile())
      .map(entry => entry.name)

    assertProjectResourceIndex('architecture', parsedIndex.data, availableFiles)

    const files = new Map<string, ArchitectureRouteFile>()
    const nodes = new Map<string, ArchitectureNode>()
    const warnings: string[] = []

    for (const entry of parsedIndex.data.files) {
      const filePath = join(resourcePath, entry.file)
      const text = readFileSync(filePath, 'utf-8')
      const parsed = parseArchitectureFile(entry.id, entry.file, text)

      for (const node of parsed.nodes) {
        if (nodes.has(node.id)) {
          throw new Error(`${projectId} Architecture 接口拒绝接入: Node ID 重复 ${node.id}`)
        }
        nodes.set(node.id, node)
      }

      warnings.push(...parsed.warnings)
      files.set(entry.id, {
        ...entry,
        nodes: parsed.nodes.map(node => node.id),
      })
    }

    for (const node of nodes.values()) {
      for (const relation of node.relations) {
        if (ARCHITECTURE_RELATION_RE.test(relation) && !nodes.has(relation)) {
          throw new Error(
            `${projectId} Architecture 接口拒绝接入: Relation 目标不存在 ${node.id} -> ${relation}`,
          )
        }
      }
    }

    const snapshot: ArchitectureProjectIndex = {
      projectId,
      state: 'ready',
      resourcePath,
      files: [...files.values()],
      nodeCount: nodes.size,
      warnings,
      builtAt: new Date().toISOString(),
    }

    this.projects.set(projectId, {
      snapshot,
      resourceHandle,
      files,
      nodes,
    })

    return snapshot
  }

  removeProject(projectId: string): boolean {
    return this.projects.delete(projectId)
  }

  clear(): void {
    this.projects.clear()
  }

  getIndex(projectId: string): ArchitectureProjectIndex | undefined {
    return this.projects.get(projectId)?.snapshot
  }

  listFiles(projectId: string): readonly ArchitectureRouteFile[] {
    return this.requireProject(projectId).snapshot.files
  }

  getNode(projectId: string, nodeId: string): ArchitectureNodeResult | undefined {
    const cache = this.projects.get(projectId)
    const node = cache?.nodes.get(nodeId)
    return node ? { projectId, node } : undefined
  }

  listChildren(projectId: string, nodeId: string): readonly ArchitectureNode[] {
    const cache = this.requireProject(projectId)
    const node = cache.nodes.get(nodeId)
    if (!node) return []
    return node.children
      .map(id => cache.nodes.get(id))
      .filter((item): item is ArchitectureNode => item !== undefined)
  }

  search(request: ProjectQueryRequest): readonly ProjectCandidateResult[] {
    const cache = this.requireProject(request.projectId)
    const query = request.query.trim()
    if (!query) return []

    const exactNode = cache.nodes.get(query.toUpperCase())
    if (exactNode) {
      const file = cache.files.get(exactNode.fileId)
      return [this.toCandidate(request.projectId, cache, exactNode, file?.summary ?? '', 1, [
        'Node ID 精确寻址',
      ])]
    }

    const terms = [...new Set([...extractTerms(query), ...scopeTerms(request.scope)])]
    const fileCandidates = this.scoreFiles(cache, query, terms)
    if (fileCandidates.length === 0) return []

    const candidates: ProjectCandidateResult[] = []

    for (const scoredFile of fileCandidates) {
      for (const nodeId of scoredFile.file.nodes) {
        const node = cache.nodes.get(nodeId)
        if (!node) continue

        const nodeScore = this.scoreNode(node, query, terms)
        const isRoot = node.id === scoredFile.file.id
        if (nodeScore.score <= 0 && !isRoot) continue

        const relevance = Math.min(
          1,
          isRoot
            ? Math.max(scoredFile.score, nodeScore.score)
            : 0.35 * scoredFile.score + 0.65 * nodeScore.score,
        )

        if (relevance <= 0) continue

        candidates.push(this.toCandidate(
          request.projectId,
          cache,
          node,
          scoredFile.file.summary,
          relevance,
          [...scoredFile.reasons, ...nodeScore.reasons],
        ))
      }
    }

    const deduped = new Map<string, ProjectCandidateResult>()
    for (const candidate of candidates) {
      const current = deduped.get(candidate.id)
      if (!current || (candidate.relevance ?? 0) > (current.relevance ?? 0)) {
        deduped.set(candidate.id, candidate)
      }
    }

    return [...deduped.values()]
      .sort((a, b) => (b.relevance ?? 0) - (a.relevance ?? 0) || a.id.localeCompare(b.id))
      .slice(0, Math.max(1, request.limit ?? 8))
  }

  private toCandidate(
    projectId: string,
    cache: ProjectCache,
    node: ArchitectureNode,
    fileSummary: string,
    relevance: number,
    reasons: readonly string[],
  ): ProjectCandidateResult {
    return {
      projectId,
      id: node.id,
      title: node.title,
      type: 'architecture-node',
      location: node.location,
      summary: node.role ?? firstLine(node.directContent) ?? fileSummary,
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
        role: node.role,
        boundary: node.boundary,
        resources: node.resources,
        relations: node.relations,
      },
    }
  }

  private requireProject(projectId: string): ProjectCache {
    const cache = this.projects.get(projectId)
    if (!cache) {
      throw new Error(`Architecture Navigator 尚未为项目建立索引: ${projectId}`)
    }
    return cache
  }

  private scoreFiles(
    cache: ProjectCache,
    query: string,
    terms: readonly string[],
  ): readonly ScoredFile[] {
    const normalizedQuery = normalize(query)
    const scored: ScoredFile[] = []

    for (const file of cache.files.values()) {
      const reasons: string[] = []
      let score = 0
      const normalizedFileId = normalize(file.id)

      if (normalizedFileId === normalizedQuery) {
        score = 1
        reasons.push('File ID 精确匹配')
      } else if (normalizedQuery.startsWith(normalizedFileId) && normalizedQuery.length > normalizedFileId.length) {
        score = 0.99
        reasons.push('Node 地址前缀命中 File ID')
      }

      if (file.aliases.some(alias => normalize(alias) === normalizedQuery)) {
        score = Math.max(score, 0.96)
        reasons.push('Index alias 精确匹配')
      }

      if (normalize(file.title).includes(normalizedQuery) && normalizedQuery) {
        score = Math.max(score, 0.9)
        reasons.push('Index title 匹配')
      }

      const coverage = termCoverage(terms, [file.id, file.title, file.summary, ...file.aliases])
      if (coverage > 0) {
        score = Math.max(score, 0.45 + 0.45 * coverage)
        reasons.push(`Index route terms 覆盖 ${(coverage * 100).toFixed(0)}%`)
      }

      if (score > 0) scored.push({ file, score, reasons })
    }

    return scored
      .sort((a, b) => b.score - a.score || a.file.id.localeCompare(b.file.id))
      .slice(0, 4)
  }

  private scoreNode(
    node: ArchitectureNode,
    query: string,
    terms: readonly string[],
  ): { readonly score: number; readonly reasons: readonly string[] } {
    const normalizedQuery = normalize(query)
    const reasons: string[] = []
    let score = 0

    if (normalize(node.id) === normalizedQuery) {
      score = 1
      reasons.push('Node ID 精确匹配')
    }

    if (normalize(node.title) === normalizedQuery) {
      score = Math.max(score, 0.98)
      reasons.push('Node title 精确匹配')
    } else if (normalizedQuery && normalize(node.title).includes(normalizedQuery)) {
      score = Math.max(score, 0.9)
      reasons.push('Node title 包含匹配')
    }

    const fields = [
      node.id,
      node.title,
      node.role ?? '',
      node.boundary ?? '',
      ...node.resources,
      ...node.relations,
      node.directContent,
    ]
    const coverage = termCoverage(terms, fields)
    if (coverage > 0) {
      score = Math.max(score, 0.35 + 0.55 * coverage)
      reasons.push(`Node terms 覆盖 ${(coverage * 100).toFixed(0)}%`)
    }

    return { score, reasons }
  }
}
