#!/usr/bin/env node
import { resolve } from 'node:path'
import { KnowledgeManagerEngine } from './knowledge-manager-engine.js'
import { KnowledgeLibraryMutator } from './knowledge-library-mutator.js'

const usage = (): never => {
  console.error(`Usage:
  knowledge tree <knowledge-root>
  knowledge search <knowledge-root> <query> [--category C010] [--status VALIDATED] [--limit 8]
  knowledge get <knowledge-root> <K-ID>
  knowledge related <knowledge-root> <K-ID>
  knowledge validate <knowledge-root>
  knowledge reindex <knowledge-root>

  knowledge add <knowledge-root> --category C010 --title <title> --fact <fact> --provenance <source> [--scope <scope>] [--tags a,b] [--refs K...,A...]
  knowledge update-candidate <knowledge-root> <K-ID> [--title <title>] [--fact <fact>] [--provenance <source>] [--scope <scope>] [--tags a,b] [--refs ...]
  knowledge reclassify <knowledge-root> <K-ID> --category C010
  knowledge deprecate <knowledge-root> <K-ID>

  knowledge category-add <knowledge-root> --title <title> [--parent C010] [--aliases a,b] [--summary <summary>]
  knowledge category-rename <knowledge-root> <C-ID> [--title <title>] [--aliases a,b] [--summary <summary>]
  knowledge category-deprecate <knowledge-root> <C-ID>`)
  process.exit(2)
}

const [command, rawRoot, ...rest] = process.argv.slice(2)
if (!command || !rawRoot) usage()
const root = resolve(rawRoot)
const projectId = 'cli-knowledge'
const engine = new KnowledgeManagerEngine()

const load = () => engine.refreshProject(projectId, root, `file://${root}`)
const reindex = () => engine.reindexProject(projectId, root, `file://${root}`)

const flag = (name: string): string | undefined => {
  const index = rest.indexOf(name)
  return index >= 0 ? rest[index + 1] : undefined
}

const requireFlag = (name: string): string => {
  const value = flag(name)
  if (!value) return usage()
  return value
}

const csv = (value: string | undefined): string[] | undefined =>
  value === undefined
    ? undefined
    : value.split(',').map(item => item.trim()).filter(Boolean)

const positional = (): string[] => {
  const result: string[] = []
  for (let index = 0; index < rest.length; index += 1) {
    if (rest[index]?.startsWith('--')) {
      index += 1
      continue
    }
    result.push(rest[index]!)
  }
  return result
}

const mutator = (): KnowledgeLibraryMutator => {
  load()
  return new KnowledgeLibraryMutator(engine, projectId, root, reindex)
}

switch (command) {
  case 'tree': {
    load()
    const taxonomy = engine.getTaxonomy(projectId)
    if (!taxonomy) throw new Error('当前知识库未启用 knowledge-library-v0.2')
    const visit = (id: string, depth: number): void => {
      const category = taxonomy.categories[id]
      if (!category) return
      console.log(`${'  '.repeat(depth)}[${id}] ${category.title} (${category.status})`)
      for (const childId of category.children) visit(childId, depth + 1)
    }
    for (const rootId of taxonomy.roots) visit(rootId, 0)
    break
  }

  case 'search': {
    load()
    const query = positional().join(' ')
    const category = flag('--category')
    const status = flag('--status')
    const limitRaw = flag('--limit')
    const limit = limitRaw ? Number.parseInt(limitRaw, 10) : 8
    const filters: Record<string, unknown> = {}
    if (category) filters.category = category
    if (status) filters.status = status
    const result = engine.search({
      projectId,
      query,
      filters,
      limit: Number.isFinite(limit) ? limit : 8,
    })
    console.log(JSON.stringify(result, null, 2))
    break
  }

  case 'get': {
    load()
    const id = positional()[0]
    if (!id) usage()
    console.log(JSON.stringify(engine.getNode(projectId, id), null, 2))
    break
  }

  case 'related': {
    load()
    const id = positional()[0]
    if (!id) usage()
    console.log(JSON.stringify(engine.getRelated(projectId, id), null, 2))
    break
  }

  case 'validate': {
    const snapshot = load()
    console.log(JSON.stringify({
      valid: true,
      libraryMode: snapshot.libraryMode,
      warnings: snapshot.warnings,
      sourceFingerprint: snapshot.sourceFingerprint,
    }, null, 2))
    break
  }

  case 'reindex': {
    const snapshot = reindex()
    console.log(JSON.stringify({
      reindexed: true,
      libraryMode: snapshot.libraryMode,
      knowledgeCount: snapshot.knowledgeCount,
      sourceFingerprint: snapshot.sourceFingerprint,
      index: resolve(root, '00_INDEX.md'),
    }, null, 2))
    break
  }

  case 'add': {
    const result = mutator().submitCandidate({
      categoryId: requireFlag('--category'),
      title: requireFlag('--title'),
      fact: requireFlag('--fact'),
      provenance: requireFlag('--provenance'),
      ...(flag('--scope') ? { scope: flag('--scope') } : {}),
      ...(csv(flag('--tags')) ? { tags: csv(flag('--tags')) } : {}),
      ...(csv(flag('--refs')) ? { refs: csv(flag('--refs')) } : {}),
    })
    console.log(JSON.stringify(result, null, 2))
    break
  }

  case 'update-candidate': {
    const id = positional()[0]
    if (!id) usage()
    const result = mutator().updateCandidate(id, {
      ...(flag('--title') !== undefined ? { title: flag('--title') } : {}),
      ...(flag('--fact') !== undefined ? { fact: flag('--fact') } : {}),
      ...(flag('--provenance') !== undefined ? { provenance: flag('--provenance') } : {}),
      ...(flag('--scope') !== undefined ? { scope: flag('--scope') } : {}),
      ...(flag('--tags') !== undefined ? { tags: csv(flag('--tags')) ?? [] } : {}),
      ...(flag('--refs') !== undefined ? { refs: csv(flag('--refs')) ?? [] } : {}),
    })
    console.log(JSON.stringify(result, null, 2))
    break
  }

  case 'reclassify': {
    const id = positional()[0]
    if (!id) usage()
    console.log(JSON.stringify(
      mutator().reclassify(id, requireFlag('--category')),
      null,
      2,
    ))
    break
  }

  case 'deprecate': {
    const id = positional()[0]
    if (!id) usage()
    console.log(JSON.stringify(mutator().deprecateKnowledge(id), null, 2))
    break
  }

  case 'category-add': {
    console.log(JSON.stringify(mutator().addCategory({
      title: requireFlag('--title'),
      ...(flag('--parent') ? { parentId: flag('--parent') } : {}),
      ...(csv(flag('--aliases')) ? { aliases: csv(flag('--aliases')) } : {}),
      ...(flag('--summary') ? { summary: flag('--summary') } : {}),
    }), null, 2))
    break
  }

  case 'category-rename': {
    const id = positional()[0]
    if (!id) usage()
    console.log(JSON.stringify(mutator().renameCategory(id, {
      ...(flag('--title') !== undefined ? { title: flag('--title') } : {}),
      ...(flag('--aliases') !== undefined ? { aliases: csv(flag('--aliases')) ?? [] } : {}),
      ...(flag('--summary') !== undefined ? { summary: flag('--summary') } : {}),
    }), null, 2))
    break
  }

  case 'category-deprecate': {
    const id = positional()[0]
    if (!id) usage()
    console.log(JSON.stringify(mutator().deprecateCategory(id), null, 2))
    break
  }

  default:
    usage()
}
