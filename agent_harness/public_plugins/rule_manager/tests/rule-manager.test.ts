import {
  mkdirSync,
  mkdtempSync,
  unlinkSync,
  writeFileSync,
} from 'node:fs'
import { join } from 'node:path'
import { tmpdir } from 'node:os'
import { describe, expect, it } from 'vitest'
import { parseRuleFile } from '../src/rule-parser.js'
import { RuleManagerEngine } from '../src/rule-manager-engine.js'

const validRules = `# [R010] Interface Rules

## [R010.010] Visual Style

### [R010.010.010] Theme

#### [R010.010.010.010] Theme Token
Level: MUST
When: 修改 UI 主题、颜色或视觉样式
Rule: 必须使用项目统一主题变量。
Refs: [A010.010.010, G010.010]

#### [R010.010.010.020] Theme Literal
Level: MUST_NOT
When: 新增或修改 UI 颜色值
Rule: 禁止在业务组件中新增未登记的独立颜色常量。

### [R010.010.020] Typography

#### [R010.010.020.010] Typography Level
Level: MUST
When: 修改页面文字层级
Rule: 必须复用项目既有字体层级定义。

## [R010.020] Interaction

### [R010.020.010] Feedback

#### [R010.020.010.010] Error Feedback
Level: MAY
When: 新增非关键交互反馈
Rule: 可以复用项目已有轻提示组件。
`

const writeIndex = (root: string, files: string): void => {
  writeFileSync(
    join(root, '00_INDEX.md'),
    `---\ninterface: project-resource-index-v0.1\nresource: rules\nstandard: rule-v0.1\nfiles:${files}\n---\n`,
  )
}

describe('Rule Tree parser', () => {
  it('解析 Branch 与 Rule Leaf', () => {
    const result = parseRuleFile('R010', '010_interface.md', validRules)
    expect(result.nodes.length).toBe(10)

    const leaf = result.nodes.find(node => node.id === 'R010.010.010.010')
    expect(leaf?.isLeaf).toBe(true)
    expect(leaf?.level).toBe('MUST')
    expect(leaf?.when).toContain('UI')
    expect(leaf?.rule).toContain('统一主题变量')
    expect(leaf?.refs).toEqual(['A010.010.010', 'G010.010'])

    const branch = result.nodes.find(node => node.id === 'R010.010.010')
    expect(branch?.isLeaf).toBe(false)
    expect(branch?.children).toEqual([
      'R010.010.010.010',
      'R010.010.010.020',
    ])
  })

  it('Leaf 缺少 Level 时拒绝', () => {
    const invalid = `# [R010] Root\n## [R010.010] Branch\n### [R010.010.010] Leaf\nWhen: 任意\nRule: 必须执行。\n`
    expect(() => parseRuleFile('R010', '010_bad.md', invalid)).toThrow('缺少合法 Level')
  })

  it('标题层级与编号树深度不一致时拒绝', () => {
    expect(() => parseRuleFile(
      'R010',
      '010_bad.md',
      '# [R010] Root\n### [R010.010] Wrong Depth\n',
    )).toThrow('标题层级')
  })

  it('模糊措辞产生 Warning，不伪装成结构错误', () => {
    const text = `# [R010] Root\n## [R010.010] Leaf\nLevel: MAY\nWhen: 一般来说修改配置时\nRule: 尽量复用已有实现。\n`
    const result = parseRuleFile('R010', '010_warning.md', text)
    expect(result.warnings.some(item => item.includes('模糊表达'))).toBe(true)
  })
})

describe('Rule Manager cached routing', () => {
  it('按 Index → File → Rule Tree 建索引并返回 Leaf Candidate', () => {
    const root = mkdtempSync(join(tmpdir(), 'rule-router-'))
    writeIndex(root, `\n  - id: R010\n    file: 010_interface.md\n    title: Interface Rules\n    summary: UI style and interaction constraints\n    aliases: [ui, interface, style, theme, typography]`)
    writeFileSync(join(root, '010_interface.md'), validRules)

    const engine = new RuleManagerEngine()
    const snapshot = engine.refreshProject('example', root, 'project://example/rules')

    expect(snapshot.state).toBe('ready')
    expect(snapshot.ruleCount).toBe(4)

    const candidates = engine.search({
      projectId: 'example',
      query: 'ui theme 主题',
      limit: 4,
    })

    expect(candidates.some(item => item.id === 'R010.010.010.010')).toBe(true)
    expect(candidates.find(item => item.id === 'R010.010.010.010')?.metadata?.isLeaf).toBe(true)
    expect(candidates[0]?.provenance.resource).toBe('project://example/rules')
  })

  it('稳定 Rule ID 直接精确寻址', () => {
    const root = mkdtempSync(join(tmpdir(), 'rule-router-'))
    writeIndex(root, `\n  - id: R010\n    file: 010_interface.md\n    title: Interface Rules\n    summary: UI rules\n    aliases: [ui]`)
    writeFileSync(join(root, '010_interface.md'), validRules)

    const engine = new RuleManagerEngine()
    engine.refreshProject('example', root, 'project://example/rules')

    const exact = engine.search({
      projectId: 'example',
      query: 'R010.010.010.020',
    })
    expect(exact).toHaveLength(1)
    expect(exact[0]?.id).toBe('R010.010.010.020')
    expect(exact[0]?.relevance).toBe(1)
  })

  it('宽泛分支查询依赖 Index route hints，并可返回 Branch 供 Agent 继续缩小', () => {
    const root = mkdtempSync(join(tmpdir(), 'rule-router-'))
    writeIndex(root, `\n  - id: R010\n    file: 010_interface.md\n    title: Interface Rules\n    summary: UI visual style rules\n    aliases: [ui, interface, visual, style]`)
    writeFileSync(join(root, '010_interface.md'), validRules)

    const engine = new RuleManagerEngine()
    engine.refreshProject('example', root, 'project://example/rules')

    const result = engine.search({ projectId: 'example', query: 'Visual Style' })
    expect(result.some(item => item.id === 'R010.010' && item.type === 'rule-branch')).toBe(true)
  })

  it('刷新完成后查询使用 Cache，不依赖重新读取源文件', () => {
    const root = mkdtempSync(join(tmpdir(), 'rule-router-'))
    writeIndex(root, `\n  - id: R010\n    file: 010_interface.md\n    title: Interface Rules\n    summary: UI rules\n    aliases: [ui, theme]`)
    const filePath = join(root, '010_interface.md')
    writeFileSync(filePath, validRules)

    const engine = new RuleManagerEngine()
    engine.refreshProject('example', root, 'project://example/rules')
    unlinkSync(filePath)

    expect(engine.search({ projectId: 'example', query: 'R010.010.010.010' })[0]?.id).toBe(
      'R010.010.010.010',
    )
  })

  it('刷新失败后清除旧 READY Cache', () => {
    const root = mkdtempSync(join(tmpdir(), 'rule-router-'))
    writeIndex(root, `\n  - id: R010\n    file: 010_interface.md\n    title: Interface Rules\n    summary: UI rules\n    aliases: [ui]`)
    const filePath = join(root, '010_interface.md')
    writeFileSync(filePath, validRules)

    const engine = new RuleManagerEngine()
    engine.refreshProject('example', root, 'project://example/rules')
    writeFileSync(filePath, '# [R010] Root\n### [R010.010] Wrong Depth\n')

    expect(() => engine.refreshProject('example', root, 'project://example/rules')).toThrow('标题层级')
    expect(engine.getIndex('example')).toBeUndefined()
  })

  it('存在未进入 Index 的规则文件时拒绝接入', () => {
    const root = mkdtempSync(join(tmpdir(), 'rule-router-'))
    writeIndex(root, `\n  - id: R010\n    file: 010_interface.md\n    title: Interface Rules\n    summary: UI rules\n    aliases: [ui]`)
    writeFileSync(join(root, '010_interface.md'), validRules)
    writeFileSync(
      join(root, '020_orphan.md'),
      '# [R020] Root\n## [R020.010] Leaf\nLevel: MUST\nWhen: 任意\nRule: 必须执行。\n',
    )

    const engine = new RuleManagerEngine()
    expect(() => engine.refreshProject('example', root, 'project://example/rules')).toThrow(
      '正式可路由文件未进入 00_INDEX',
    )
  })

  it('空标准接口可以 READY', () => {
    const root = mkdtempSync(join(tmpdir(), 'rule-router-'))
    writeIndex(root, ' []')

    const engine = new RuleManagerEngine()
    const snapshot = engine.refreshProject('empty', root, 'project://empty/rules')
    expect(snapshot.state).toBe('ready')
    expect(snapshot.ruleCount).toBe(0)
    expect(engine.search({ projectId: 'empty', query: 'anything' })).toEqual([])
  })
})
