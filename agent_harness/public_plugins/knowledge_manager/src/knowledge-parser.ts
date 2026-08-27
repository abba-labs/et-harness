import type { KnowledgeNode, KnowledgeStatus } from './contracts.js'

const ROUTABLE_HEADING_RE = /^(#{1,6})\s+\[(K\d{3}(?:\.\d{3})*)\]\s+(.+?)\s*$/
const MARKDOWN_HEADING_RE = /^#{1,6}\s+/
const VALID_STATUSES = new Set<KnowledgeStatus>(['CANDIDATE', 'VALIDATED', 'FULL_VALIDATED', 'DEPRECATED'])

interface MutableNode {
  id: string
  fileId: string
  title: string
  depth: number
  parentId?: string
  children: string[]
  location: string
  directContent: string
  isLeaf: boolean
  status?: KnowledgeStatus
  category?: string
  fact?: string
  scope?: string
  provenance?: string
  tags: string[]
  refs: string[]
  sources: string[]
}

export interface KnowledgeFileParseResult {
  readonly nodes: readonly KnowledgeNode[]
  readonly warnings: readonly string[]
}

const nodeDepth = (id: string): number => id.split('.').length

const parentNodeId = (id: string): string | undefined => {
  const parts = id.split('.')
  return parts.length <= 1 ? undefined : parts.slice(0, -1).join('.')
}

const extractField = (content: string, name: string): string | undefined => {
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = new RegExp(`^${escaped}:\\s*(.+)$`, 'im').exec(content)
  return match?.[1]?.trim()
}

const parseListValue = (value: string): string[] => {
  const trimmed = value.trim()
  if (!trimmed) return []
  const unwrapped = trimmed.startsWith('[') && trimmed.endsWith(']')
    ? trimmed.slice(1, -1)
    : trimmed
  return [...new Set(
    unwrapped
      .split(/[,;，；]/)
      .map(item => item.trim())
      .filter(Boolean),
  )]
}

export function parseKnowledgeFile(
  fileId: string,
  fileName: string,
  text: string,
): KnowledgeFileParseResult {
  const lines = text.replaceAll('\r\n', '\n').split('\n')
  const headings: Array<{ line: number; level: number; id: string; title: string }> = []

  for (const [index, line] of lines.entries()) {
    if (!MARKDOWN_HEADING_RE.test(line)) continue
    const match = ROUTABLE_HEADING_RE.exec(line)
    if (!match) {
      throw new Error(`${fileName}:${index + 1} 标题缺少合法 Knowledge Node ID`)
    }
    headings.push({
      line: index,
      level: match[1]!.length,
      id: match[2]!,
      title: match[3]!.trim(),
    })
  }

  if (headings.length === 0) {
    throw new Error(`${fileName} 无法解析 Knowledge Tree`)
  }

  const seen = new Set<string>()
  const nodes = new Map<string, MutableNode>()
  const warnings: string[] = []

  for (const [index, heading] of headings.entries()) {
    const depth = nodeDepth(heading.id)
    if (depth !== heading.level) {
      throw new Error(
        `${fileName}:${heading.line + 1} 标题层级 ${heading.level} 与 Node 深度 ${depth} 不一致: ${heading.id}`,
      )
    }

    if (heading.id.split('.')[0] !== fileId) {
      throw new Error(`${fileName}:${heading.line + 1} Node ${heading.id} 不属于 File ID ${fileId}`)
    }

    if (seen.has(heading.id)) {
      throw new Error(`${fileName} Knowledge Node ID 重复: ${heading.id}`)
    }
    seen.add(heading.id)

    const parentId = parentNodeId(heading.id)
    if (parentId && !nodes.has(parentId)) {
      throw new Error(`${fileName}:${heading.line + 1} 父 Node 不存在: ${parentId}`)
    }

    const nextHeadingLine = headings[index + 1]?.line ?? lines.length
    const directContent = lines.slice(heading.line + 1, nextHeadingLine).join('\n').trim()

    const node: MutableNode = {
      id: heading.id,
      fileId,
      title: heading.title,
      depth,
      children: [],
      location: `${fileName}#${heading.id}`,
      directContent,
      isLeaf: false,
      tags: [],
      refs: [],
      sources: [],
      ...(parentId ? { parentId } : {}),
    }

    nodes.set(node.id, node)
    if (parentId) nodes.get(parentId)!.children.push(node.id)
  }

  const root = nodes.get(fileId)
  if (!root || root.depth !== 1) {
    throw new Error(`${fileName} 必须以 # [${fileId}] 作为根 Node`)
  }

  for (const node of nodes.values()) {
    node.isLeaf = node.children.length === 0
    if (!node.isLeaf) continue

    const rawStatus = extractField(node.directContent, 'Status')?.toUpperCase()
    const category = extractField(node.directContent, 'Category')
    const fact = extractField(node.directContent, 'Fact')
    const scope = extractField(node.directContent, 'Scope')
    const provenance = extractField(node.directContent, 'Provenance')
    const tags = parseListValue(extractField(node.directContent, 'Tags') ?? '')
    const refs = parseListValue(extractField(node.directContent, 'Refs') ?? '')
    const sources = parseListValue(extractField(node.directContent, 'Sources') ?? '')

    if (!rawStatus || !VALID_STATUSES.has(rawStatus as KnowledgeStatus)) {
      throw new Error(
        `${fileName} Knowledge Leaf ${node.id} 缺少合法 Status: CANDIDATE | VALIDATED | FULL_VALIDATED | DEPRECATED`,
      )
    }
    if (!fact) {
      throw new Error(`${fileName} Knowledge Leaf ${node.id} 缺少 Fact`)
    }
    if (!provenance) {
      throw new Error(`${fileName} Knowledge Leaf ${node.id} 缺少 Provenance`)
    }

    node.status = rawStatus as KnowledgeStatus
    node.category = category
    node.fact = fact
    node.scope = scope
    node.provenance = provenance
    node.tags = tags
    node.refs = refs
    node.sources = sources

    if (fact.length > 420) {
      warnings.push(`${node.id} Fact 过长；应保持 Agent-first 最小知识`)
    }
    if (node.directContent.length > 1200) {
      warnings.push(`${node.id} Knowledge Leaf 正文过长；长证据应通过引用访问`)
    }
  }

  return {
    nodes: [...nodes.values()].map(node => ({
      ...node,
      children: [...node.children],
      tags: [...node.tags],
      refs: [...node.refs],
      sources: [...node.sources],
    })),
    warnings,
  }
}
