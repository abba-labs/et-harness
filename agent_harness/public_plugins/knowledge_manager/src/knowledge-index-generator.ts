import type {
  KnowledgeProjectIndex,
  KnowledgeTaxonomy,
} from './contracts.js'

const escapeYaml = (value: string): string => JSON.stringify(value)

const categoryDirectCount = (
  categoryCounts: Readonly<Record<string, number>>,
  categoryId: string,
): number => categoryCounts[categoryId] ?? 0

const categorySubtreeCount = (
  taxonomy: KnowledgeTaxonomy,
  categoryCounts: Readonly<Record<string, number>>,
  categoryId: string,
): number => {
  const category = taxonomy.categories[categoryId]
  if (!category) return 0
  return categoryDirectCount(categoryCounts, categoryId)
    + category.children.reduce(
      (total, childId) => total + categorySubtreeCount(taxonomy, categoryCounts, childId),
      0,
    )
}

const renderCategoryTree = (
  taxonomy: KnowledgeTaxonomy,
  categoryCounts: Readonly<Record<string, number>>,
): string[] => {
  const lines: string[] = []
  const visit = (id: string, depth: number): void => {
    const category = taxonomy.categories[id]
    if (!category) return
    const indent = '  '.repeat(depth)
    const total = categorySubtreeCount(taxonomy, categoryCounts, id)
    const direct = categoryDirectCount(categoryCounts, category.id)
    lines.push(`${indent}- [${id}] ${category.title} — ${total} 条（直接 ${direct}）`)
    for (const childId of category.children) visit(childId, depth + 1)
  }
  for (const rootId of taxonomy.roots) visit(rootId, 0)
  return lines
}

export function renderGeneratedKnowledgeIndex(snapshot: KnowledgeProjectIndex): string {
  if (snapshot.libraryMode !== 'library-v0.2' || !snapshot.taxonomy || !snapshot.sourceFingerprint) {
    throw new Error('只有 knowledge-library-v0.2 可以生成 00_INDEX.md')
  }

  const files = snapshot.files.map(file => [
    `  - id: ${file.id}`,
    `    file: ${escapeYaml(file.file)}`,
    `    title: ${escapeYaml(file.title)}`,
    `    summary: ${escapeYaml(file.summary)}`,
    `    aliases: [${file.aliases.map(escapeYaml).join(', ')}]`,
  ].join('\n')).join('\n')

  const categoryLines = renderCategoryTree(
    snapshot.taxonomy,
    snapshot.categoryCounts ?? {},
  )

  const fileRows = snapshot.files.map(file =>
    `| ${file.id} | \`${file.file}\` | ${file.title} | ${file.nodes.length} |`,
  )

  return `---
interface: project-resource-index-v0.1
resource: knowledge
standard: knowledge-v0.1
generated: true
generator: knowledge-manager-v0.2
source_fingerprint: ${escapeYaml(snapshot.sourceFingerprint)}
files:
${files || '  []'}
---

# Project Knowledge Index

> AUTO GENERATED — DO NOT EDIT.  
> Source of Truth: \`TAXONOMY.yaml\` + \`NNN_*.md\`  
> Rebuild: \`knowledge reindex <knowledge-root>\`

## Library Summary

- Knowledge: ${snapshot.knowledgeCount}
- Categories: ${Object.keys(snapshot.taxonomy.categories).length}
- CANDIDATE: ${snapshot.statusCounts.CANDIDATE}
- VALIDATED: ${snapshot.statusCounts.VALIDATED}
- FULL_VALIDATED: ${snapshot.statusCounts.FULL_VALIDATED}
- DEPRECATED: ${snapshot.statusCounts.DEPRECATED}
- Source fingerprint: \`${snapshot.sourceFingerprint}\`

## Classification Tree

${categoryLines.length > 0 ? categoryLines.join('\n') : '_No categories._'}

## Knowledge Files

| File ID | File | Title | Nodes |
|---|---|---|---:|
${fileRows.length > 0 ? fileRows.join('\n') : '| - | - | - | 0 |'}
`
}