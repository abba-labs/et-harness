import type { ArchitectureNode } from './contracts.js'

const ROUTABLE_HEADING_RE = /^(#{1,6})\s+\[([A]\d{3}(?:\.\d{3})*)\]\s+(.+?)\s*$/
const MARKDOWN_HEADING_RE = /^#{1,6}\s+/

interface MutableNode {
  id: string
  fileId: string
  title: string
  depth: number
  parentId?: string
  children: string[]
  location: string
  directContent: string
  role?: string
  boundary?: string
  resources: string[]
  relations: string[]
}

export interface ArchitectureFileParseResult {
  readonly nodes: readonly ArchitectureNode[]
  readonly warnings: readonly string[]
}

const nodeDepth = (id: string): number => id.split('.').length

const parentNodeId = (id: string): string | undefined => {
  const parts = id.split('.')
  if (parts.length <= 1) return undefined
  return parts.slice(0, -1).join('.')
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

const escapeRegExp = (value: string): string =>
  value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

const extractField = (content: string, name: string): string | undefined => {
  const match = new RegExp(`^${escapeRegExp(name)}:\\s*(.+)$`, 'im').exec(content)
  return match?.[1]?.trim()
}

export function parseArchitectureFile(
  fileId: string,
  fileName: string,
  text: string,
): ArchitectureFileParseResult {
  const lines = text.replaceAll('\r\n', '\n').split('\n')
  const headings: Array<{
    line: number
    level: number
    id: string
    title: string
  }> = []

  for (const [index, line] of lines.entries()) {
    if (!MARKDOWN_HEADING_RE.test(line)) continue

    const match = ROUTABLE_HEADING_RE.exec(line)
    if (!match) {
      throw new Error(`${fileName}:${index + 1} 标题缺少合法 Architecture Node ID`)
    }

    headings.push({
      line: index,
      level: match[1]!.length,
      id: match[2]!,
      title: match[3]!.trim(),
    })
  }

  if (headings.length === 0) {
    throw new Error(`${fileName} 无法解析 Architecture Tree`)
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

    const rootSegment = heading.id.split('.')[0]
    if (rootSegment !== fileId) {
      throw new Error(`${fileName}:${heading.line + 1} Node ${heading.id} 不属于 File ID ${fileId}`)
    }

    if (seen.has(heading.id)) {
      throw new Error(`${fileName} Architecture Node ID 重复: ${heading.id}`)
    }
    seen.add(heading.id)

    const parentId = parentNodeId(heading.id)
    if (parentId && !nodes.has(parentId)) {
      throw new Error(`${fileName}:${heading.line + 1} 父 Node 不存在: ${parentId}`)
    }

    const nextHeadingLine = headings[index + 1]?.line ?? lines.length
    const directContent = lines
      .slice(heading.line + 1, nextHeadingLine)
      .join('\n')
      .trim()

    if (directContent.length > 1200) {
      warnings.push(`${heading.id} 直接正文过长；建议拆分或通过引用继续路由`)
    }

    const role = extractField(directContent, 'Role')
    const boundary = extractField(directContent, 'Boundary')
    const resources = parseListValue(extractField(directContent, 'Resources') ?? '')
    const relations = parseListValue(extractField(directContent, 'Relations') ?? '')

    const node: MutableNode = {
      id: heading.id,
      fileId,
      title: heading.title,
      depth,
      children: [],
      location: `${fileName}#${heading.id}`,
      directContent,
      resources,
      relations,
      ...(parentId ? { parentId } : {}),
      ...(role ? { role } : {}),
      ...(boundary ? { boundary } : {}),
    }

    nodes.set(node.id, node)
    if (parentId) nodes.get(parentId)!.children.push(node.id)
  }

  const root = nodes.get(fileId)
  if (!root || root.depth !== 1) {
    throw new Error(`${fileName} 必须以 # [${fileId}] 作为根 Node`)
  }

  return {
    nodes: [...nodes.values()].map(node => ({ ...node, children: [...node.children] })),
    warnings,
  }
}
