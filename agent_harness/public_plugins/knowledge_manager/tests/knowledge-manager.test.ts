import { mkdtempSync, unlinkSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { tmpdir } from 'node:os'
import { describe, expect, it } from 'vitest'
import { parseKnowledgeFile } from '../src/knowledge-parser.js'
import { KnowledgeManagerEngine } from '../src/knowledge-manager-engine.js'

const validKnowledge = `# [K010] Interface Knowledge

## [K010.010] Visual System

### [K010.010.010] Theme Source
Status: VALIDATED
Fact: UI 主题变量统一定义在主题配置入口，业务组件应通过该入口理解当前视觉变量。
Scope: ui theme visual
Provenance: TASK-100
Refs: [A010.010.010]

### [K010.010.020] Candidate Theme Finding
Status: CANDIDATE
Fact: 某个旧页面可能仍直接保存颜色常量，需要后续验证。
Scope: ui theme legacy
Provenance: TASK-101

## [K010.020] Debugging

### [K010.020.010] Refresh Order
Status: VALIDATED
Fact: 配置刷新后必须重新读取运行时状态才能观察最新值。
Scope: runtime refresh debug
Provenance: TASK-102
`

const writeIndex = (root: string, files: string): void => {
  writeFileSync(
    join(root, '00_INDEX.md'),
    `---\ninterface: project-resource-index-v0.1\nresource: knowledge\nstandard: knowledge-v0.1\nfiles:${files}\n---\n`,
  )
}

describe('Knowledge Tree parser', () => {
  it('解析 Knowledge Leaf 与状态', () => {
    const result = parseKnowledgeFile('K010', '010_interface.md', validKnowledge)
    const validated = result.nodes.find(node => node.id === 'K010.010.010')
    expect(validated?.isLeaf).toBe(true)
    expect(validated?.status).toBe('VALIDATED')
    expect(validated?.fact).toContain('主题变量')
    expect(validated?.provenance).toBe('TASK-100')
  })

  it('缺少 Provenance 时拒绝', () => {
    const invalid = `# [K010] Root\n## [K010.010] Leaf\nStatus: VALIDATED\nFact: 已确认事实。\n`
    expect(() => parseKnowledgeFile('K010', '010_bad.md', invalid)).toThrow('缺少 Provenance')
  })

  it('非法 Status 时拒绝', () => {
    const invalid = `# [K010] Root\n## [K010.010] Leaf\nStatus: ACTIVE\nFact: 已确认事实。\nProvenance: TASK-X\n`
    expect(() => parseKnowledgeFile('K010', '010_bad.md', invalid)).toThrow('缺少合法 Status')
  })
})

describe('Knowledge Manager tiered all-status routing', () => {
  it('默认自然语言查询同时返回可靠知识和探索知识', () => {
    const root = mkdtempSync(join(tmpdir(), 'knowledge-router-'))
    writeIndex(root, `\n  - id: K010\n    file: 010_interface.md\n    title: Interface Knowledge\n    summary: UI theme and runtime knowledge\n    aliases: [ui, theme, visual, runtime, debug]`)
    writeFileSync(join(root, '010_interface.md'), validKnowledge)

    const engine = new KnowledgeManagerEngine()
    const snapshot = engine.refreshProject('example', root, 'project://example/knowledge')
    expect(snapshot.knowledgeCount).toBe(3)
    expect(snapshot.statusCounts.VALIDATED).toBe(2)
    expect(snapshot.statusCounts.CANDIDATE).toBe(1)

    const result = engine.search({ projectId: 'example', query: 'ui theme 主题' })
    expect(result.some(item => item.id === 'K010.010.010')).toBe(true)
    expect(result.some(item => item.id === 'K010.010.020')).toBe(true)
    expect(result.find(item => item.id === 'K010.010.020')?.metadata?.usagePolicy).toBe(
      'HYPOTHESIS_AND_TEST_LEAD_ONLY',
    )
  })

  it('显式 status filter 可以查询 CANDIDATE', () => {
    const root = mkdtempSync(join(tmpdir(), 'knowledge-router-'))
    writeIndex(root, `\n  - id: K010\n    file: 010_interface.md\n    title: Interface Knowledge\n    summary: UI theme knowledge\n    aliases: [ui, theme, legacy]`)
    writeFileSync(join(root, '010_interface.md'), validKnowledge)

    const engine = new KnowledgeManagerEngine()
    engine.refreshProject('example', root, 'project://example/knowledge')
    const result = engine.search({
      projectId: 'example',
      query: 'legacy theme',
      filters: { status: 'CANDIDATE' },
    })
    expect(result.some(item => item.id === 'K010.010.020')).toBe(true)
    expect(result.find(item => item.id === 'K010.010.020')?.warnings?.[0]).toContain('CANDIDATE')
  })

  it('显式非法 status filter 直接拒绝，不静默改变查询条件', () => {
    const root = mkdtempSync(join(tmpdir(), 'knowledge-router-'))
    writeIndex(root, `\n  - id: K010\n    file: 010_interface.md\n    title: Interface Knowledge\n    summary: UI theme knowledge\n    aliases: [ui, theme]`)
    writeFileSync(join(root, '010_interface.md'), validKnowledge)

    const engine = new KnowledgeManagerEngine()
    engine.refreshProject('example', root, 'project://example/knowledge')
    expect(() => engine.search({
      projectId: 'example',
      query: 'theme',
      filters: { status: 'ACTIVE' },
    })).toThrow('非法 Knowledge status filter')
  })

  it('稳定 K ID 可以精确读取非 VALIDATED 节点，并显式标状态', () => {
    const root = mkdtempSync(join(tmpdir(), 'knowledge-router-'))
    writeIndex(root, `\n  - id: K010\n    file: 010_interface.md\n    title: Interface Knowledge\n    summary: UI knowledge\n    aliases: [ui]`)
    writeFileSync(join(root, '010_interface.md'), validKnowledge)

    const engine = new KnowledgeManagerEngine()
    engine.refreshProject('example', root, 'project://example/knowledge')
    const exact = engine.search({ projectId: 'example', query: 'K010.010.020' })
    expect(exact).toHaveLength(1)
    expect(exact[0]?.metadata?.status).toBe('CANDIDATE')
    expect(exact[0]?.warnings?.[0]).toContain('CANDIDATE')
  })

  it('刷新后查询使用 Cache', () => {
    const root = mkdtempSync(join(tmpdir(), 'knowledge-router-'))
    writeIndex(root, `\n  - id: K010\n    file: 010_interface.md\n    title: Interface Knowledge\n    summary: UI knowledge\n    aliases: [ui, theme]`)
    const filePath = join(root, '010_interface.md')
    writeFileSync(filePath, validKnowledge)

    const engine = new KnowledgeManagerEngine()
    engine.refreshProject('example', root, 'project://example/knowledge')
    unlinkSync(filePath)
    expect(engine.search({ projectId: 'example', query: 'K010.010.010' })[0]?.id).toBe(
      'K010.010.010',
    )
  })

  it('刷新失败清除旧 Cache', () => {
    const root = mkdtempSync(join(tmpdir(), 'knowledge-router-'))
    writeIndex(root, `\n  - id: K010\n    file: 010_interface.md\n    title: Interface Knowledge\n    summary: UI knowledge\n    aliases: [ui]`)
    const filePath = join(root, '010_interface.md')
    writeFileSync(filePath, validKnowledge)

    const engine = new KnowledgeManagerEngine()
    engine.refreshProject('example', root, 'project://example/knowledge')
    writeFileSync(filePath, '# [K010] Root\n## [K010.010] Leaf\nStatus: VALIDATED\nFact: X\n')
    expect(() => engine.refreshProject('example', root, 'project://example/knowledge')).toThrow(
      '缺少 Provenance',
    )
    expect(engine.getIndex('example')).toBeUndefined()
  })

  it('空标准接口可以 READY', () => {
    const root = mkdtempSync(join(tmpdir(), 'knowledge-router-'))
    writeIndex(root, ' []')
    const engine = new KnowledgeManagerEngine()
    const snapshot = engine.refreshProject('empty', root, 'project://empty/knowledge')
    expect(snapshot.state).toBe('ready')
    expect(snapshot.knowledgeCount).toBe(0)
  })
})
