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
import { parseGateFile } from './gate-parser.js'
import type {
  GateExecutionPlan,
  GateNode,
  GateNodeResult,
  GateProjectIndex,
  GateRouteFile,
} from './contracts.js'

interface ProjectCache {
  readonly snapshot: GateProjectIndex
  readonly resourceHandle: string
  readonly files: ReadonlyMap<string, GateRouteFile>
  readonly nodes: ReadonlyMap<string, GateNode>
}

interface ScoredFile {
  readonly file: GateRouteFile
  readonly score: number
  readonly reasons: readonly string[]
}

const GATE_ID_RE = /^G\d{3}(?:\.\d{3})*$/

const normalize = (value: string): string =>
  value.toLowerCase().replace(/[^a-z0-9\u4e00-\u9fff]+/g, '')

const extractTerms = (value: string): string[] => {
  const raw = value.toLowerCase().match(/[a-z0-9_.-]+|[\u4e00-\u9fff]+/g) ?? []
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
  return Object.values(scope).flatMap(value => {
    if (typeof value === 'string') return extractTerms(value)
    if (Array.isArray(value)) return value.flatMap(item => typeof item === 'string' ? extractTerms(item) : [])
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

export class GateManagerEngine {
  private readonly projects = new Map<string, ProjectCache>()

  refreshProject(
    projectId: string,
    resourcePath: string,
    resourceHandle: string,
  ): GateProjectIndex {
    this.projects.delete(projectId)

    const indexPath = join(resourcePath, '00_INDEX.md')
    if (!existsSync(indexPath)) {
      throw new Error(`${projectId} Gate 接口拒绝接入: 缺少 gates/00_INDEX.md`)
    }

    const indexText = readFileSync(indexPath, 'utf-8')
    const parsedIndex = parseYamlFrontMatter<ProjectResourceIndexV01>(indexText)
    const availableFiles = readdirSync(resourcePath, { withFileTypes: true })
      .filter(entry => entry.isFile())
      .map(entry => entry.name)

    assertProjectResourceIndex('gates', parsedIndex.data, availableFiles)

    const files = new Map<string, GateRouteFile>()
    const nodes = new Map<string, GateNode>()
    const warnings: string[] = []
    let gateCount = 0

    for (const entry of parsedIndex.data.files) {
      const parsed = parseGateFile(entry.id, entry.file, readFileSync(join(resourcePath, entry.file), 'utf-8'))
      for (const node of parsed.nodes) {
        if (nodes.has(node.id)) throw new Error(`${projectId} Gate 接口拒绝接入: Node ID 重复 ${node.id}`)
        nodes.set(node.id, node)
        if (node.isGate) gateCount += 1
      }
      warnings.push(...parsed.warnings)
      files.set(entry.id, { ...entry, nodes: parsed.nodes.map(node => node.id) })
    }

    const snapshot: GateProjectIndex = {
      projectId,
      state: 'ready',
      resourcePath,
      files: [...files.values()],
      nodeCount: nodes.size,
      gateCount,
      warnings,
      builtAt: new Date().toISOString(),
    }

    this.projects.set(projectId, { snapshot, resourceHandle, files, nodes })
    return snapshot
  }

  removeProject(projectId: string): boolean {
    return this.projects.delete(projectId)
  }

  clear(): void {
    this.projects.clear()
  }

  getIndex(projectId: string): GateProjectIndex | undefined {
    return this.projects.get(projectId)?.snapshot
  }

  listFiles(projectId: string): readonly GateRouteFile[] {
    return this.requireProject(projectId).snapshot.files
  }

  getNode(projectId: string, nodeId: string): GateNodeResult | undefined {
    const cache = this.projects.get(projectId)
    const node = cache?.nodes.get(nodeId)
    return node ? { projectId, node } : undefined
  }

  listChildren(projectId: string, nodeId: string): readonly GateNode[] {
    const cache = this.requireProject(projectId)
    const node = cache.nodes.get(nodeId)
    if (!node) return []
    return node.children.map(id => cache.nodes.get(id)).filter((item): item is GateNode => item !== undefined)
  }

  getExecutionPlan(projectId: string, gateId: string): GateExecutionPlan | undefined {
    const cache = this.requireProject(projectId)
    const node = cache.nodes.get(gateId)
    if (!node?.isGate || !node.gate) return undefined
    return {
      projectId,
      gateId,
      level: node.gate.level,
      when: node.gate.when,
      steps: node.gate.steps,
      pass: node.gate.pass,
      refs: node.gate.refs,
    }
  }

  search(request: ProjectQueryRequest): readonly ProjectCandidateResult[] {
    const cache = this.requireProject(request.projectId)
    const query = request.query.trim()
    if (!query) return []

    const exactId = query.toUpperCase()
    if (GATE_ID_RE.test(exactId)) {
      const node = cache.nodes.get(exactId)
      return node ? [this.toCandidate(request.projectId, cache, node, 1, ['Gate Node ID 精确匹配'])] : []
    }

    const terms = [...new Set([...extractTerms(query), ...scopeTerms(request.scope)])]
    const fileCandidates = this.scoreFiles(cache, query, terms)
    if (fileCandidates.length === 0) return []

    const candidates: ProjectCandidateResult[] = []
    for (const scoredFile of fileCandidates) {
      for (const nodeId of scoredFile.file.nodes) {
        const node = cache.nodes.get(nodeId)
        if (!node) continue
        const nodeScore = this.scoreNode(cache, node, query, terms)
        const isRoot = node.id === scoredFile.file.id

        if (node.isGate) {
          if (nodeScore.score <= 0) continue
          candidates.push(this.toCandidate(
            request.projectId,
            cache,
            node,
            Math.min(1, 0.3 * scoredFile.score + 0.7 * nodeScore.score),
            [...scoredFile.reasons, ...nodeScore.reasons],
          ))
        } else if (nodeScore.score >= 0.75 || isRoot) {
          candidates.push(this.toCandidate(
            request.projectId,
            cache,
            node,
            Math.min(0.9, isRoot ? Math.max(scoredFile.score, nodeScore.score) : nodeScore.score),
            [...scoredFile.reasons, ...nodeScore.reasons],
          ))
        }
      }
    }

    const deduped = new Map<string, ProjectCandidateResult>()
    for (const candidate of candidates) {
      const current = deduped.get(candidate.id)
      if (!current || (candidate.relevance ?? 0) > (current.relevance ?? 0)) deduped.set(candidate.id, candidate)
    }

    return [...deduped.values()]
      .sort((a, b) => {
        const scoreDiff = (b.relevance ?? 0) - (a.relevance ?? 0)
        if (Math.abs(scoreDiff) > 0.05) return scoreDiff
        const aMust = a.metadata?.level === 'MUST' ? 1 : 0
        const bMust = b.metadata?.level === 'MUST' ? 1 : 0
        return bMust - aMust || a.id.localeCompare(b.id)
      })
      .slice(0, Math.max(1, request.limit ?? 8))
  }

  private toCandidate(
    projectId: string,
    cache: ProjectCache,
    node: GateNode,
    relevance: number,
    reasons: readonly string[],
  ): ProjectCandidateResult {
    return {
      projectId,
      id: node.id,
      title: node.title,
      type: node.isGate ? 'gate-leaf' : 'gate-branch',
      location: node.location,
      summary: node.gate?.when ?? `Gate branch: ${node.title}`,
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
        isGate: node.isGate,
        level: node.gate?.level,
        when: node.gate?.when,
        steps: node.gate?.steps,
        pass: node.gate?.pass,
        refs: node.gate?.refs,
      },
    }
  }

  private requireProject(projectId: string): ProjectCache {
    const cache = this.projects.get(projectId)
    if (!cache) throw new Error(`Gate Manager 尚未为项目建立索引: ${projectId}`)
    return cache
  }

  private scoreFiles(cache: ProjectCache, query: string, terms: readonly string[]): readonly ScoredFile[] {
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
      const coverage = termCoverage(terms, [file.title, file.summary, ...file.aliases])
      if (coverage > 0) {
        score = Math.max(score, 0.45 + 0.45 * coverage)
        reasons.push(`Index route terms 覆盖 ${(coverage * 100).toFixed(0)}%`)
      }
      if (score > 0) scored.push({ file, score, reasons })
    }
    return scored.sort((a, b) => b.score - a.score || a.file.id.localeCompare(b.file.id)).slice(0, 4)
  }

  private scoreNode(
    cache: ProjectCache,
    node: GateNode,
    query: string,
    terms: readonly string[],
  ): { readonly score: number; readonly reasons: readonly string[] } {
    const normalizedQuery = normalize(query)
    const reasons: string[] = []
    let score = 0
    if (normalize(node.title) === normalizedQuery) {
      score = 0.98
      reasons.push('Gate title 精确匹配')
    } else if (normalizedQuery && normalize(node.title).includes(normalizedQuery)) {
      score = 0.9
      reasons.push('Gate title 包含匹配')
    }

    const ancestors = this.ancestorTitles(cache, node)
    const fields = [
      node.title,
      ...ancestors,
      node.gate?.when ?? '',
      ...(node.gate?.steps.map(step => step.tool) ?? []),
      ...(node.gate?.refs ?? []),
    ]
    const coverage = termCoverage(terms, fields)
    if (coverage > 0) {
      score = Math.max(score, 0.35 + 0.6 * coverage)
      reasons.push(`Gate tree terms 覆盖 ${(coverage * 100).toFixed(0)}%`)
    }
    return { score, reasons }
  }

  private ancestorTitles(cache: ProjectCache, node: GateNode): string[] {
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
}
