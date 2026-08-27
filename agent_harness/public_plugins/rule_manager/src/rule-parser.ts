import type { RuleLevel, RuleNode } from './contracts.js'

const ROUTABLE_HEADING_RE = /^(#{1,6})\s+\[(R\d{3}(?:\.\d{3})*)\]\s+(.+?)\s*$/
const MARKDOWN_HEADING_RE = /^#{1,6}\s+/
const VALID_LEVELS = new Set<RuleLevel>(['MUST', 'MUST_NOT', 'MAY'])
const FUZZY_TERMS = ['尽量', '最好', '一般来说', '看情况', '适当', '原则上']

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
  level?: RuleLevel
  when?: string
  rule?: string
  refs: string[]
}

export interface RuleFileParseResult {
  readonly nodes: readonly RuleNode[]
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
  return unwrapped
    .split(/[,;，；]/)
    .map(item => item.trim())
    .filter(Boolean)
}

const fuzzyTermsIn = (value: string): string[] =>
  FUZZY_TERMS.filter(term => value.includes(term))

export function parseRuleFile(
  fileId: string,
  fileName: string,
  text: string,
): RuleFileParseResult {
  const lines = text.replaceAll('\r\n', '\n').split('\n')
  const headings: Array<{ line: number; level: number; id: string; title: string }> = []

  for (const [index, line] of lines.entries()) {
    if (!MARKDOWN_HEADING_RE.test(line)) continue

    const match = ROUTABLE_HEADING_RE.exec(line)
    if (!match) {
      throw new Error(`${fileName}:${index + 1} 标题缺少合法 Rule Node ID`)
    }

    headings.push({
      line: index,
      level: match[1]!.length,
      id: match[2]!,
      title: match[3]!.trim(),
    })
  }

  if (headings.length === 0) {
    throw new Error(`${fileName} 无法解析 Rule Tree`)
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
      throw new Error(`${fileName} Rule Node ID 重复: ${heading.id}`)
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
      refs: [],
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

    const rawLevel = extractField(node.directContent, 'Level')?.toUpperCase()
    const when = extractField(node.directContent, 'When')
    const rule = extractField(node.directContent, 'Rule')
    const refs = parseListValue(extractField(node.directContent, 'Refs') ?? '')

    if (!rawLevel || !VALID_LEVELS.has(rawLevel as RuleLevel)) {
      throw new Error(`${fileName} Rule Leaf ${node.id} 缺少合法 Level: MUST | MUST_NOT | MAY`)
    }
    if (!when) {
      throw new Error(`${fileName} Rule Leaf ${node.id} 缺少 When`)
    }
    if (!rule) {
      throw new Error(`${fileName} Rule Leaf ${node.id} 缺少 Rule`)
    }

    node.level = rawLevel as RuleLevel
    node.when = when
    node.rule = rule
    node.refs = refs

    if (node.directContent.length > 700) {
      warnings.push(`${node.id} Rule Leaf 正文过长；应保持 Agent-first 最小规则`)
    }

    const fuzzy = [...new Set([...fuzzyTermsIn(when), ...fuzzyTermsIn(rule)])]
    if (fuzzy.length > 0) {
      warnings.push(`${node.id} 包含模糊表达: ${fuzzy.join(', ')}`)
    }
  }

  return {
    nodes: [...nodes.values()].map(node => ({ ...node, children: [...node.children], refs: [...node.refs] })),
    warnings,
  }
}
