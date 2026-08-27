import { parse } from 'yaml'
import type {
  KnowledgeCategory,
  KnowledgeCategoryStatus,
  KnowledgeTaxonomy,
} from './contracts.js'

const CATEGORY_ID_RE = /^C\d{3}(?:\.\d{3})*$/
const VALID_STATUS = new Set<KnowledgeCategoryStatus>(['ACTIVE', 'DEPRECATED'])

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

const nonEmpty = (value: unknown): value is string =>
  typeof value === 'string' && value.trim().length > 0

const parseStringArray = (value: unknown, path: string): string[] => {
  if (value === undefined) return []
  if (!Array.isArray(value) || value.some(item => !nonEmpty(item))) {
    throw new Error(`${path} 必须是字符串数组`)
  }
  return [...new Set(value.map(item => String(item).trim()))]
}

const parentIdOf = (id: string): string | undefined => {
  const parts = id.split('.')
  return parts.length <= 1 ? undefined : parts.slice(0, -1).join('.')
}

export function parseKnowledgeTaxonomy(text: string): KnowledgeTaxonomy {
  const raw: unknown = parse(text)
  if (!isRecord(raw)) throw new Error('TAXONOMY.yaml 必须是 YAML 对象')
  if (raw.standard !== 'knowledge-library-v0.2') {
    throw new Error('TAXONOMY.yaml standard 必须为 knowledge-library-v0.2')
  }
  if (!Array.isArray(raw.categories)) {
    throw new Error('TAXONOMY.yaml categories 必须是数组')
  }

  const categories = new Map<string, KnowledgeCategory>()
  const roots: string[] = []

  const visit = (value: unknown, expectedParentId: string | undefined, path: string): string => {
    if (!isRecord(value)) throw new Error(`${path} 必须是对象`)
    if (!nonEmpty(value.id) || !CATEGORY_ID_RE.test(value.id)) {
      throw new Error(`${path}.id 必须是合法 Cxxx[.xxx...] 分类 ID`)
    }
    if (!nonEmpty(value.title)) throw new Error(`${path}.title 不能为空`)
    if (categories.has(value.id)) throw new Error(`Category ID 重复: ${value.id}`)

    const structuralParent = parentIdOf(value.id)
    if (structuralParent !== expectedParentId) {
      throw new Error(
        `${path}.id ${value.id} 的父地址应为 ${expectedParentId ?? '<root>'}`,
      )
    }

    const rawStatus = typeof value.status === 'string'
      ? value.status.toUpperCase()
      : 'ACTIVE'
    if (!VALID_STATUS.has(rawStatus as KnowledgeCategoryStatus)) {
      throw new Error(`${path}.status 必须为 ACTIVE | DEPRECATED`)
    }

    const rawChildren = value.children
    if (rawChildren !== undefined && !Array.isArray(rawChildren)) {
      throw new Error(`${path}.children 必须是数组`)
    }

    const node: KnowledgeCategory = {
      id: value.id,
      title: value.title.trim(),
      children: [],
      aliases: parseStringArray(value.aliases, `${path}.aliases`),
      status: rawStatus as KnowledgeCategoryStatus,
      ...(expectedParentId ? { parentId: expectedParentId } : {}),
      ...(nonEmpty(value.summary) ? { summary: value.summary.trim() } : {}),
    }
    categories.set(node.id, node)

    const childIds = (rawChildren ?? []).map((child, index) =>
      visit(child, node.id, `${path}.children[${index}]`),
    )
    categories.set(node.id, { ...node, children: childIds })
    return node.id
  }

  for (const [index, value] of raw.categories.entries()) {
    roots.push(visit(value, undefined, `categories[${index}]`))
  }

  return {
    standard: 'knowledge-library-v0.2',
    roots,
    categories: Object.fromEntries(categories.entries()),
  }
}

export function listCategoryDescendants(
  taxonomy: KnowledgeTaxonomy,
  categoryId: string,
  includeSelf = true,
): readonly string[] {
  const root: KnowledgeCategory | undefined = taxonomy.categories[categoryId]
  if (!root) return []

  const result: string[] = []
  const visit = (id: string): void => {
    result.push(id)
    const category: KnowledgeCategory | undefined = taxonomy.categories[id]
    for (const childId of category?.children ?? []) visit(childId)
  }
  visit(categoryId)
  return includeSelf ? result : result.slice(1)
}

export function categoryPathTitles(
  taxonomy: KnowledgeTaxonomy,
  categoryId: string,
): readonly string[] {
  const titles: string[] = []
  let current: KnowledgeCategory | undefined = taxonomy.categories[categoryId]
  while (current) {
    titles.push(current.title, ...current.aliases)
    current = current.parentId ? taxonomy.categories[current.parentId] : undefined
  }
  return titles
}
