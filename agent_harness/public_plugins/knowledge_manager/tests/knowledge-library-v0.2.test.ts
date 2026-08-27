import { mkdtempSync, readFileSync, unlinkSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { tmpdir } from 'node:os'
import { describe, expect, it } from 'vitest'
import { KnowledgeManagerEngine } from '../src/knowledge-manager-engine.js'
import { parseKnowledgeTaxonomy } from '../src/taxonomy-parser.js'

const taxonomy = `standard: knowledge-library-v0.2
categories:
  - id: C010
    title: Knowledge
    aliases: [knowledge]
    children:
      - id: C010.010
        title: Chips
        aliases: [chip, mcu]
        children:
          - id: C010.010.010
            title: DMA
            aliases: [dmac]
  - id: C020
    title: Experience
    aliases: [experience]
    children:
      - id: C020.010
        title: Debug
        aliases: [debug]
`

const knowledge = `# [K010] Platform Knowledge

## [K010.010] DMA

### [K010.010.010] DMA DTCM Access
Status: VALIDATED
Category: C010.010.010
Fact: DMA master cannot directly access the current DTCM address space.
Scope: dma dtcm chip
Provenance: SRC-001
Tags: [dma, dtcm]
Refs: [K010.020.010, A020.010]

### [K010.010.020] DMA Candidate
Status: CANDIDATE
Category: C010.010.010
Fact: A legacy DMA path may still assume direct DTCM access.
Scope: dma legacy
Provenance: TASK-002
Tags: [dma, legacy]

## [K010.020] Debug

### [K010.020.010] DMA Debug Method
Status: VALIDATED
Category: C020.010
Fact: Check the DMA bus-visible address map before debugging transfer failures.
Scope: dma debug
Provenance: TASK-003
Tags: [dma, debug]
Refs: [K010.010.010]
`

const createLibrary = (): string => {
  const root = mkdtempSync(join(tmpdir(), 'knowledge-library-v02-'))
  writeFileSync(join(root, 'TAXONOMY.yaml'), taxonomy)
  writeFileSync(join(root, '010_platform.md'), knowledge)
  writeFileSync(join(root, '00_INDEX.md'), '# MANUAL CONTENT MUST BE REPLACED\n')
  return root
}

describe('Knowledge Library v0.2 taxonomy', () => {
  it('解析稳定 C-ID 分类树', () => {
    const parsed = parseKnowledgeTaxonomy(taxonomy)
    expect(parsed.roots).toEqual(['C010', 'C020'])
    expect(parsed.categories['C010.010.010']?.title).toBe('DMA')
    expect(parsed.categories['C010.010']?.children).toEqual(['C010.010.010'])
  })

  it('C-ID 父子地址不一致时拒绝', () => {
    const invalid = `standard: knowledge-library-v0.2\ncategories:\n  - id: C010\n    title: Root\n    children:\n      - id: C020.010\n        title: Wrong\n`
    expect(() => parseKnowledgeTaxonomy(invalid)).toThrow('父地址')
  })
})

describe('Knowledge Library v0.2 generated index and search', () => {
  it('从 TAXONOMY + Knowledge 自动重建 00_INDEX', () => {
    const root = createLibrary()
    const engine = new KnowledgeManagerEngine()
    const snapshot = engine.refreshProject('example', root, 'project://example/knowledge')

    expect(snapshot.libraryMode).toBe('library-v0.2')
    expect(snapshot.knowledgeCount).toBe(3)
    expect(snapshot.taxonomy?.categories['C010.010.010']?.title).toBe('DMA')
    expect(snapshot.categoryCounts?.['C010.010.010']).toBe(2)

    const generated = readFileSync(join(root, '00_INDEX.md'), 'utf-8')
    expect(generated).toContain('AUTO GENERATED — DO NOT EDIT')
    expect(generated).toContain('generator: knowledge-manager-v0.2')
    expect(generated).toContain('[C010.010.010] DMA')
    expect(generated).not.toContain('MANUAL CONTENT MUST BE REPLACED')
  })

  it('自然语言默认返回所有相关状态，并使用分类路径参与检索', () => {
    const root = createLibrary()
    const engine = new KnowledgeManagerEngine()
    engine.refreshProject('example', root, 'project://example/knowledge')

    const result = engine.search({ projectId: 'example', query: 'chip dmac dtcm' })
    expect(result.some(item => item.id === 'K010.010.010')).toBe(true)
    expect(result.some(item => item.id === 'K010.010.020')).toBe(true)
    expect(result.find(item => item.id === 'K010.010.020')?.metadata?.trustTier).toBe('EXPLORATORY')
    expect(result.find(item => item.id === 'K010.010.020')?.warnings?.[0]).toContain('假设')
  })

  it('Category filter 支持包含子分类且不扫描其他分类', () => {
    const root = createLibrary()
    const engine = new KnowledgeManagerEngine()
    engine.refreshProject('example', root, 'project://example/knowledge')

    const chipResult = engine.search({
      projectId: 'example',
      query: 'dma',
      filters: { category: 'C010', includeDescendants: true },
    })
    expect(chipResult.some(item => item.id === 'K010.010.010')).toBe(true)
    expect(chipResult.some(item => item.id === 'K010.020.010')).toBe(false)

    const debugResult = engine.search({
      projectId: 'example',
      query: '',
      filters: { category: 'C020', includeDescendants: true },
    })
    expect(debugResult.map(item => item.id)).toContain('K010.020.010')
  })

  it('Relation Index 同时提供正向与反向关系', () => {
    const root = createLibrary()
    const engine = new KnowledgeManagerEngine()
    engine.refreshProject('example', root, 'project://example/knowledge')

    const related = engine.getRelated('example', 'K010.010.010')
    expect(related.outgoing).toContain('K010.020.010')
    expect(related.incoming).toContain('K010.020.010')
  })

  it('建索引后查询只依赖 Cache，不重新读取 Knowledge Markdown', () => {
    const root = createLibrary()
    const file = join(root, '010_platform.md')
    const engine = new KnowledgeManagerEngine()
    engine.refreshProject('example', root, 'project://example/knowledge')
    unlinkSync(file)

    expect(engine.search({ projectId: 'example', query: 'dtcm dma' })[0]?.id).toBe(
      'K010.010.010',
    )
  })

  it('Leaf 没有 Category 时拒绝进入 library-v0.2 READY', () => {
    const root = mkdtempSync(join(tmpdir(), 'knowledge-library-v02-'))
    writeFileSync(join(root, 'TAXONOMY.yaml'), taxonomy)
    writeFileSync(
      join(root, '010_bad.md'),
      '# [K010] Root\n## [K010.010] Leaf\nStatus: VALIDATED\nFact: X\nProvenance: SRC-X\n',
    )
    const engine = new KnowledgeManagerEngine()
    expect(() => engine.refreshProject('example', root, 'project://example/knowledge')).toThrow(
      '必须提供 Category',
    )
  })

  it('Knowledge 指向不存在 Category 时拒绝', () => {
    const root = mkdtempSync(join(tmpdir(), 'knowledge-library-v02-'))
    writeFileSync(join(root, 'TAXONOMY.yaml'), taxonomy)
    writeFileSync(
      join(root, '010_bad.md'),
      '# [K010] Root\n## [K010.010] Leaf\nStatus: VALIDATED\nCategory: C999\nFact: X\nProvenance: SRC-X\n',
    )
    const engine = new KnowledgeManagerEngine()
    expect(() => engine.refreshProject('example', root, 'project://example/knowledge')).toThrow(
      'Category 不存在',
    )
  })
})
