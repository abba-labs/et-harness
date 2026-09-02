import type {
  ContextBuildRequest,
  ContextPack,
  ContextPriority,
  ContextResolvedItem,
  ContextResourceKind,
} from './contracts.js'

const PRIORITY_RANK: Readonly<Record<ContextPriority, number>> = {
  required: 4,
  high: 3,
  normal: 2,
  low: 1,
}

const KIND_RANK: Readonly<Record<ContextResourceKind, number>> = {
  rule: 5,
  gate: 4,
  architecture: 3,
  knowledge: 2,
  inline: 1,
}

const itemRank = (item: ContextResolvedItem): number =>
  item.kind === 'inline' && item.id.startsWith('prior-context-')
    ? 6
    : KIND_RANK[item.kind]

const renderItem = (item: ContextResolvedItem): string => {
  const warnings = item.warnings.length > 0
    ? `\nWarnings: ${item.warnings.join(' | ')}`
    : ''
  return `## [${item.kind}] ${item.id} ${item.title}\nProvenance: ${item.provenance}${warnings}\n\n${item.content.trim()}\n`
}

const renderHeader = (projectId: string, taskSummary?: string): string =>
  `# Context Pack\nProject: ${projectId}${taskSummary ? `\nTask: ${taskSummary.trim()}` : ''}\n`

export class ContextBuilderEngine {
  build(
    request: ContextBuildRequest,
    resolvedItems: readonly ContextResolvedItem[],
  ): ContextPack {
    const maxChars = Math.max(1000, request.maxChars ?? 24000)
    const warnings: string[] = []

    for (const item of resolvedItems) {
      if (item.projectId !== request.projectId) {
        throw new Error(
          `Context Builder 拒绝跨项目内容: request=${request.projectId}, item=${item.projectId}/${item.id}`,
        )
      }
    }

    const deduped = new Map<string, ContextResolvedItem>()
    for (const item of resolvedItems) {
      const key = `${item.kind}:${item.id}`
      const current = deduped.get(key)
      const normalized = item.required || item.priority === 'required'
        ? { ...item, required: true, priority: 'required' as const }
        : item

      if (!current || PRIORITY_RANK[normalized.priority] > PRIORITY_RANK[current.priority]) {
        deduped.set(key, normalized)
      }
    }

    const ordered = [...deduped.values()].sort((a, b) =>
      PRIORITY_RANK[b.priority] - PRIORITY_RANK[a.priority]
      || itemRank(b) - itemRank(a)
      || a.id.localeCompare(b.id),
    )

    const header = renderHeader(request.projectId, request.taskSummary)
    let charCount = header.length
    const included: ContextResolvedItem[] = []
    const omitted: string[] = []

    for (const item of ordered) {
      const rendered = renderItem(item)
      if (item.required) {
        included.push(item)
        charCount += rendered.length
        continue
      }

      if (charCount + rendered.length <= maxChars) {
        included.push(item)
        charCount += rendered.length
      } else {
        omitted.push(`${item.kind}:${item.id}`)
      }
    }

    const overBudget = charCount > maxChars
    if (overBudget) {
      warnings.push('Required Context 已超过预算；未静默删除 MUST Rule / MUST Gate / required item')
    }
    if (omitted.length > 0) {
      warnings.push(`因预算省略 ${omitted.length} 个非 required item`)
    }

    for (const item of included) warnings.push(...item.warnings)

    const text = [header, ...included.map(renderItem)].join('\n')

    return {
      projectId: request.projectId,
      ...(request.taskSummary ? { taskSummary: request.taskSummary } : {}),
      items: included,
      omitted,
      warnings: [...new Set(warnings)],
      maxChars,
      charCount: text.length,
      overBudget: text.length > maxChars,
      text,
    }
  }
}
