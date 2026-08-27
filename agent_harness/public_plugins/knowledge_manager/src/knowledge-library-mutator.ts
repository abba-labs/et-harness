import { randomUUID } from 'node:crypto'
import {
  existsSync,
  readFileSync,
  renameSync,
  unlinkSync,
  writeFileSync,
} from 'node:fs'
import { join } from 'node:path'
import { stringify } from 'yaml'
import { KnowledgeManagerEngine } from './knowledge-manager-engine.js'
import { listCategoryDescendants } from './taxonomy-parser.js'
import type {
  KnowledgeCandidateInput,
  KnowledgeCandidateUpdate,
  KnowledgeCategory,
  KnowledgeCategoryCreateInput,
  KnowledgeCategoryMutationResult,
  KnowledgeCategoryUpdateInput,
  KnowledgeMutationResult,
  KnowledgeNode,
  KnowledgeProjectIndex,
  KnowledgeTaxonomy,
} from './contracts.js'

const MANAGED_SHARD_RE = /^(\d{3})_library\.md$/
const SINGLE_LINE = /^[^\r\n]+$/

const normalizeFact = (value: string): string =>
  value.toLowerCase().replace(/[^a-z0-9\u4e00-\u9fff]+/g, '')

const assertLine = (name: string, value: string): string => {
  const trimmed = value.trim()
  if (!trimmed || !SINGLE_LINE.test(trimmed)) throw new Error(`${name} 必须是非空单行文本`)
  return trimmed
}

const normalizeStringList = (name: string, values: readonly string[] | undefined): string[] => {
  if (!values) return []
  return [...new Set(values.map(value => assertLine(name, value)))]
}

const atomicWrite = (file: string, content: string): void => {
  const temp = `${file}.${process.pid}.${randomUUID()}.tmp`
  writeFileSync(temp, content, 'utf-8')
  renameSync(temp, file)
}

interface FileBackup {
  readonly path: string
  readonly existed: boolean
  readonly content?: string
}

const backupFile = (path: string): FileBackup => existsSync(path)
  ? { path, existed: true, content: readFileSync(path, 'utf-8') }
  : { path, existed: false }

const restoreBackup = (backup: FileBackup): void => {
  if (backup.existed) {
    atomicWrite(backup.path, backup.content ?? '')
  } else if (existsSync(backup.path)) {
    unlinkSync(backup.path)
  }
}

const renderList = (values: readonly string[]): string => `[${values.join(', ')}]`

const renderManagedLeaf = (
  id: string,
  input: KnowledgeCandidateInput,
): string => {
  const tags = normalizeStringList('Tags', input.tags)
  const refs = normalizeStringList('Refs', input.refs)
  const lines = [
    `## [${id}] ${assertLine('Title', input.title)}`,
    'Status: CANDIDATE',
    `Category: ${assertLine('Category', input.categoryId)}`,
    `Fact: ${assertLine('Fact', input.fact)}`,
  ]
  if (input.scope?.trim()) lines.push(`Scope: ${assertLine('Scope', input.scope)}`)
  lines.push(`Provenance: ${assertLine('Provenance', input.provenance)}`)
  if (tags.length > 0) lines.push(`Tags: ${renderList(tags)}`)
  if (refs.length > 0) lines.push(`Refs: ${renderList(refs)}`)
  return `${lines.join('\n')}\n`
}

const renderManagedShard = (fileId: string, leafText: string): string =>
  `# [${fileId}] Managed Knowledge Shard ${fileId}\n\n${leafText}`

const fileForNode = (
  engine: KnowledgeManagerEngine,
  projectId: string,
  node: KnowledgeNode,
): string => {
  const route = engine.listFiles(projectId).find(file => file.id === node.fileId)
  if (!route) throw new Error(`Knowledge File 不存在: ${node.fileId}`)
  return route.file
}

const replaceLeafSection = (
  text: string,
  nodeId: string,
  replacement: string,
): string => {
  const lines = text.replaceAll('\r\n', '\n').split('\n')
  const escaped = nodeId.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const heading = new RegExp(`^(#{1,6})\\s+\\[${escaped}\\]\\s+`)
  const start = lines.findIndex(line => heading.test(line))
  if (start < 0) throw new Error(`Knowledge Node 标题不存在: ${nodeId}`)
  let end = start + 1
  while (end < lines.length && !/^#{1,6}\s+/.test(lines[end] ?? '')) end += 1
  const replacementLines = replacement.trimEnd().split('\n')
  return [...lines.slice(0, start), ...replacementLines, '', ...lines.slice(end)]
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trimEnd() + '\n'
}

const replaceLeafField = (
  text: string,
  nodeId: string,
  field: 'Status' | 'Category',
  value: string,
): string => {
  const lines = text.replaceAll('\r\n', '\n').split('\n')
  const escaped = nodeId.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const heading = new RegExp(`^(#{1,6})\\s+\\[${escaped}\\]\\s+`)
  const start = lines.findIndex(line => heading.test(line))
  if (start < 0) throw new Error(`Knowledge Node 标题不存在: ${nodeId}`)
  let end = start + 1
  while (end < lines.length && !/^#{1,6}\s+/.test(lines[end] ?? '')) end += 1
  const fieldRe = new RegExp(`^${field}:\\s*`)
  const fieldIndex = lines.slice(start + 1, end).findIndex(line => fieldRe.test(line))
  if (fieldIndex < 0) throw new Error(`${nodeId} 缺少 ${field}`)
  lines[start + 1 + fieldIndex] = `${field}: ${value}`
  return lines.join('\n')
}

const serializeTaxonomy = (taxonomy: KnowledgeTaxonomy): string => {
  const visit = (id: string): Record<string, unknown> => {
    const node = taxonomy.categories[id]
    if (!node) throw new Error(`Category 不存在: ${id}`)
    return {
      id: node.id,
      title: node.title,
      status: node.status,
      ...(node.aliases.length > 0 ? { aliases: [...node.aliases] } : {}),
      ...(node.summary ? { summary: node.summary } : {}),
      ...(node.children.length > 0 ? { children: node.children.map(visit) } : {}),
    }
  }
  return stringify({
    standard: 'knowledge-library-v0.2',
    categories: taxonomy.roots.map(visit),
  })
}

const allocateSegment = (usedIds: readonly string[], parentId?: string): string => {
  const used = new Set(
    usedIds
      .filter(id => parentId ? id.startsWith(`${parentId}.`) : /^C\d{3}$/.test(id))
      .map(id => Number.parseInt(id.split('.').at(-1) ?? '0', 10)),
  )
  for (let number = 10; number <= 990; number += 10) {
    if (!used.has(number)) return String(number).padStart(3, '0')
  }
  throw new Error(`Category 同级编号空间已满: ${parentId ?? '<root>'}`)
}

export class KnowledgeLibraryMutator {
  constructor(
    private readonly engine: KnowledgeManagerEngine,
    private readonly projectId: string,
    private readonly root: string,
    private readonly reindex: () => KnowledgeProjectIndex,
  ) {}

  submitCandidate(input: KnowledgeCandidateInput): KnowledgeMutationResult {
    const snapshot = this.requireLibrary()
    const taxonomy = snapshot.taxonomy!
    const category = taxonomy.categories[input.categoryId]
    if (!category) throw new Error(`Category 不存在: ${input.categoryId}`)
    if (category.status !== 'ACTIVE') throw new Error(`Category 不是 ACTIVE: ${input.categoryId}`)

    const fact = assertLine('Fact', input.fact)
    const normalized = normalizeFact(fact)
    for (const file of snapshot.files) {
      for (const id of file.nodes) {
        const node = this.engine.getNode(this.projectId, id)?.node
        if (!node?.isLeaf || node.status === 'DEPRECATED' || !node.fact) continue
        if (normalizeFact(node.fact) === normalized) {
          throw new Error(`重复 Knowledge Fact: ${node.id}`)
        }
      }
    }

    const target = this.allocateManagedTarget(snapshot)
    const path = join(this.root, target.file)
    const backup = backupFile(path)
    const leaf = renderManagedLeaf(target.nodeId, input)
    const next = backup.existed
      ? `${backup.content!.trimEnd()}\n\n${leaf}`
      : renderManagedShard(target.fileId, leaf)

    return this.transact([backup], () => atomicWrite(path, next), () => {
      const updated = this.engine.getNode(this.projectId, target.nodeId)?.node
      if (!updated?.isLeaf || updated.status !== 'CANDIDATE') {
        throw new Error(`新增 Knowledge 未形成 CANDIDATE Leaf: ${target.nodeId}`)
      }
      return {
        knowledgeId: target.nodeId,
        file: target.file,
        status: updated.status,
        categoryId: input.categoryId,
        sourceFingerprint: this.engine.getIndex(this.projectId)?.sourceFingerprint,
      }
    })
  }

  updateCandidate(knowledgeId: string, update: KnowledgeCandidateUpdate): KnowledgeMutationResult {
    this.requireLibrary()
    const node = this.requireLeaf(knowledgeId)
    if (node.status !== 'CANDIDATE') throw new Error(`只有 CANDIDATE 可以直接更新: ${knowledgeId}`)
    const file = fileForNode(this.engine, this.projectId, node)
    if (!MANAGED_SHARD_RE.test(file)) throw new Error(`只允许更新 Knowledge Manager 管理的 Candidate: ${knowledgeId}`)

    const merged: KnowledgeCandidateInput = {
      categoryId: node.category!,
      title: update.title ?? node.title,
      fact: update.fact ?? node.fact!,
      provenance: update.provenance ?? node.provenance!,
      ...(update.scope !== undefined ? { scope: update.scope } : node.scope ? { scope: node.scope } : {}),
      tags: update.tags ?? node.tags,
      refs: update.refs ?? node.refs,
    }

    if (update.fact !== undefined) this.assertNoDuplicateFact(merged.fact, knowledgeId)
    const path = join(this.root, file)
    const backup = backupFile(path)
    const replacement = renderManagedLeaf(knowledgeId, merged)
    return this.transact([backup], () => {
      atomicWrite(path, replaceLeafSection(backup.content!, knowledgeId, replacement))
    }, () => {
      const current = this.requireLeaf(knowledgeId)
      return {
        knowledgeId,
        file,
        status: current.status!,
        categoryId: current.category!,
        sourceFingerprint: this.engine.getIndex(this.projectId)?.sourceFingerprint,
      }
    })
  }

  reclassify(knowledgeId: string, categoryId: string): KnowledgeMutationResult {
    const snapshot = this.requireLibrary()
    const category = snapshot.taxonomy!.categories[categoryId]
    if (!category) throw new Error(`Category 不存在: ${categoryId}`)
    if (category.status !== 'ACTIVE') throw new Error(`Category 不是 ACTIVE: ${categoryId}`)
    const node = this.requireLeaf(knowledgeId)
    const file = fileForNode(this.engine, this.projectId, node)
    const path = join(this.root, file)
    const backup = backupFile(path)
    return this.transact([backup], () => {
      atomicWrite(path, replaceLeafField(backup.content!, knowledgeId, 'Category', categoryId))
    }, () => {
      const current = this.requireLeaf(knowledgeId)
      return {
        knowledgeId,
        file,
        status: current.status!,
        categoryId: current.category!,
        sourceFingerprint: this.engine.getIndex(this.projectId)?.sourceFingerprint,
      }
    })
  }

  deprecateKnowledge(knowledgeId: string): KnowledgeMutationResult {
    this.requireLibrary()
    const node = this.requireLeaf(knowledgeId)
    if (node.status === 'DEPRECATED') throw new Error(`Knowledge 已经 DEPRECATED: ${knowledgeId}`)
    const file = fileForNode(this.engine, this.projectId, node)
    const path = join(this.root, file)
    const backup = backupFile(path)
    return this.transact([backup], () => {
      atomicWrite(path, replaceLeafField(backup.content!, knowledgeId, 'Status', 'DEPRECATED'))
    }, () => {
      const current = this.requireLeaf(knowledgeId)
      return {
        knowledgeId,
        file,
        status: current.status!,
        categoryId: current.category!,
        sourceFingerprint: this.engine.getIndex(this.projectId)?.sourceFingerprint,
      }
    })
  }

  addCategory(input: KnowledgeCategoryCreateInput): KnowledgeCategoryMutationResult {
    const snapshot = this.requireLibrary()
    const taxonomy = snapshot.taxonomy!
    if (input.parentId) {
      const parent = taxonomy.categories[input.parentId]
      if (!parent) throw new Error(`Category 父节点不存在: ${input.parentId}`)
      if (parent.status !== 'ACTIVE') throw new Error(`Category 父节点不是 ACTIVE: ${input.parentId}`)
    }
    const segment = allocateSegment(Object.keys(taxonomy.categories), input.parentId)
    const id = input.parentId ? `${input.parentId}.${segment}` : `C${segment}`
    const next = this.cloneTaxonomy(taxonomy)
    const category: KnowledgeCategory = {
      id,
      title: assertLine('Category title', input.title),
      children: [],
      aliases: normalizeStringList('Category alias', input.aliases),
      status: 'ACTIVE',
      ...(input.parentId ? { parentId: input.parentId } : {}),
      ...(input.summary?.trim() ? { summary: assertLine('Category summary', input.summary) } : {}),
    }
    next.categories[id] = category
    if (input.parentId) {
      const parent = next.categories[input.parentId]!
      next.categories[input.parentId] = { ...parent, children: [...parent.children, id] }
    } else {
      next.roots.push(id)
    }
    return this.writeTaxonomy(next, id)
  }

  renameCategory(categoryId: string, update: KnowledgeCategoryUpdateInput): KnowledgeCategoryMutationResult {
    const snapshot = this.requireLibrary()
    const taxonomy = snapshot.taxonomy!
    const current = taxonomy.categories[categoryId]
    if (!current) throw new Error(`Category 不存在: ${categoryId}`)
    const next = this.cloneTaxonomy(taxonomy)
    next.categories[categoryId] = {
      ...current,
      ...(update.title !== undefined ? { title: assertLine('Category title', update.title) } : {}),
      ...(update.aliases !== undefined ? { aliases: normalizeStringList('Category alias', update.aliases) } : {}),
      ...(update.summary !== undefined
        ? update.summary.trim()
          ? { summary: assertLine('Category summary', update.summary) }
          : { summary: undefined }
        : {}),
    }
    return this.writeTaxonomy(next, categoryId)
  }

  deprecateCategory(categoryId: string): KnowledgeCategoryMutationResult {
    const snapshot = this.requireLibrary()
    const taxonomy = snapshot.taxonomy!
    const current = taxonomy.categories[categoryId]
    if (!current) throw new Error(`Category 不存在: ${categoryId}`)
    if (current.status === 'DEPRECATED') throw new Error(`Category 已经 DEPRECATED: ${categoryId}`)

    const subtree = new Set(listCategoryDescendants(taxonomy, categoryId, true))
    const activeChildren = [...subtree]
      .filter(id => id !== categoryId && taxonomy.categories[id]?.status === 'ACTIVE')
    if (activeChildren.length > 0) {
      throw new Error(`Category 子树仍有 ACTIVE 分类: ${activeChildren[0]}`)
    }
    for (const file of snapshot.files) {
      for (const id of file.nodes) {
        const node = this.engine.getNode(this.projectId, id)?.node
        if (node?.isLeaf && node.status !== 'DEPRECATED' && node.category && subtree.has(node.category)) {
          throw new Error(`Category 子树仍有非 DEPRECATED Knowledge: ${node.id}`)
        }
      }
    }

    const next = this.cloneTaxonomy(taxonomy)
    next.categories[categoryId] = { ...current, status: 'DEPRECATED' }
    return this.writeTaxonomy(next, categoryId)
  }

  private allocateManagedTarget(snapshot: KnowledgeProjectIndex): {
    readonly file: string
    readonly fileId: string
    readonly nodeId: string
  } {
    const managed = snapshot.files
      .filter(file => MANAGED_SHARD_RE.test(file.file))
      .sort((a, b) => a.id.localeCompare(b.id))

    for (const file of managed) {
      const direct = file.nodes
        .filter(id => id.split('.').length === 2)
        .map(id => Number.parseInt(id.split('.')[1] ?? '0', 10))
      if (direct.length >= 999) continue
      const used = new Set(direct)
      for (let number = 1; number <= 999; number += 1) {
        if (!used.has(number)) {
          return {
            file: file.file,
            fileId: file.id,
            nodeId: `${file.id}.${String(number).padStart(3, '0')}`,
          }
        }
      }
    }

    const usedFileNumbers = new Set(
      snapshot.files.map(file => Number.parseInt(file.id.slice(1), 10)),
    )
    for (let number = 1; number <= 999; number += 1) {
      if (usedFileNumbers.has(number)) continue
      const segment = String(number).padStart(3, '0')
      return {
        file: `${segment}_library.md`,
        fileId: `K${segment}`,
        nodeId: `K${segment}.001`,
      }
    }
    throw new Error('Knowledge managed shard 编号空间已满')
  }

  private assertNoDuplicateFact(fact: string, exceptId?: string): void {
    const normalized = normalizeFact(assertLine('Fact', fact))
    const snapshot = this.requireLibrary()
    for (const file of snapshot.files) {
      for (const id of file.nodes) {
        if (id === exceptId) continue
        const node = this.engine.getNode(this.projectId, id)?.node
        if (!node?.isLeaf || node.status === 'DEPRECATED' || !node.fact) continue
        if (normalizeFact(node.fact) === normalized) throw new Error(`重复 Knowledge Fact: ${node.id}`)
      }
    }
  }

  private requireLibrary(): KnowledgeProjectIndex {
    const snapshot = this.engine.getIndex(this.projectId)
    if (!snapshot) throw new Error(`Knowledge Library 尚未建立索引: ${this.projectId}`)
    if (snapshot.libraryMode !== 'library-v0.2' || !snapshot.taxonomy) {
      throw new Error('写治理只支持 knowledge-library-v0.2')
    }
    return snapshot
  }

  private requireLeaf(knowledgeId: string): KnowledgeNode {
    const node = this.engine.getNode(this.projectId, knowledgeId)?.node
    if (!node?.isLeaf) throw new Error(`Knowledge Leaf 不存在: ${knowledgeId}`)
    if (!node.category || !node.status || !node.fact || !node.provenance) {
      throw new Error(`Knowledge Leaf 不完整: ${knowledgeId}`)
    }
    return node
  }

  private cloneTaxonomy(taxonomy: KnowledgeTaxonomy): {
    standard: 'knowledge-library-v0.2'
    roots: string[]
    categories: Record<string, KnowledgeCategory>
  } {
    return {
      standard: 'knowledge-library-v0.2',
      roots: [...taxonomy.roots],
      categories: Object.fromEntries(
        Object.entries(taxonomy.categories).map(([id, category]) => [
          id,
          { ...category, children: [...category.children], aliases: [...category.aliases] },
        ]),
      ),
    }
  }

  private writeTaxonomy(
    taxonomy: KnowledgeTaxonomy,
    categoryId: string,
  ): KnowledgeCategoryMutationResult {
    const path = join(this.root, 'TAXONOMY.yaml')
    const backup = backupFile(path)
    return this.transact([backup], () => atomicWrite(path, serializeTaxonomy(taxonomy)), () => {
      const category = this.engine.getTaxonomy(this.projectId)?.categories[categoryId]
      if (!category) throw new Error(`Taxonomy 修改后 Category 不存在: ${categoryId}`)
      return {
        categoryId,
        status: category.status,
        sourceFingerprint: this.engine.getIndex(this.projectId)?.sourceFingerprint,
      }
    })
  }

  private transact<T>(
    backups: readonly FileBackup[],
    mutate: () => void,
    result: () => T,
  ): T {
    mutate()
    try {
      this.reindex()
      return result()
    } catch (error) {
      for (const backup of [...backups].reverse()) restoreBackup(backup)
      try {
        this.reindex()
      } catch {
        // Preserve original error; caller sees the mutation failure.
      }
      throw error
    }
  }
}
