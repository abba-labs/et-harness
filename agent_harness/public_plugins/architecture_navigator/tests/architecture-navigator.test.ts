import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { tmpdir } from 'node:os'
import { describe, expect, it } from 'vitest'
import { parseArchitectureFile } from '../src/architecture-parser.js'
import { ArchitectureNavigatorEngine } from '../src/navigator-engine.js'

const validArchitecture = `# [A010] Interface Layer
Role: 项目界面与交互入口
Resources: source/apps/ui/

## [A010.010] Visual System
Role: UI visual style, theme and layout

### [A010.010.010] Theme
Role: theme tokens and appearance
Resources: source/apps/ui/theme/

### [A010.010.020] Layout
Role: page layout and spacing
Resources: source/apps/ui/layout/

## [A010.020] Interaction
Role: user interaction and feedback
`

const writeIndex = (root: string, files: string): void => {
  writeFileSync(
    join(root, '00_INDEX.md'),
    `---\ninterface: project-resource-index-v0.1\nresource: architecture\nstandard: architecture-v0.1\nfiles:${files}\n---\n`,
  )
}

describe('Architecture Tree parser', () => {
  it('解析稳定编号树与直接节点内容', () => {
    const result = parseArchitectureFile('A010', '010_interface.md', validArchitecture)
    expect(result.nodes.map(node => node.id)).toEqual([
      'A010',
      'A010.010',
      'A010.010.010',
      'A010.010.020',
      'A010.020',
    ])
    expect(result.nodes.find(node => node.id === 'A010.010')?.children).toEqual([
      'A010.010.010',
      'A010.010.020',
    ])
    expect(result.nodes.find(node => node.id === 'A010.010.010')?.resources).toEqual([
      'source/apps/ui/theme/',
    ])
  })

  it('标题层级与 Node 深度不一致时拒绝', () => {
    expect(() => parseArchitectureFile(
      'A010',
      '010_bad.md',
      '# [A010] Root\n### [A010.010] Wrong Depth\n',
    )).toThrow('标题层级')
  })

  it('父 Node 缺失时拒绝', () => {
    expect(() => parseArchitectureFile(
      'A010',
      '010_bad.md',
      '# [A010] Root\n### [A010.010.010] Orphan\n',
    )).toThrow('父 Node 不存在')
  })
})

describe('Architecture Navigator cached routing', () => {
  it('按 Index → File → Node 建索引并返回候选', () => {
    const root = mkdtempSync(join(tmpdir(), 'architecture-router-'))
    mkdirSync(root, { recursive: true })
    writeIndex(root, `\n  - id: A010\n    file: 010_interface.md\n    title: Interface Layer\n    summary: UI and interaction architecture\n    aliases: [ui, interface, style, theme, layout]`)
    writeFileSync(join(root, '010_interface.md'), validArchitecture)

    const engine = new ArchitectureNavigatorEngine()
    const snapshot = engine.refreshProject(
      'example',
      root,
      'project://example/architecture',
    )

    expect(snapshot.state).toBe('ready')
    expect(snapshot.nodeCount).toBe(5)

    const candidates = engine.search({
      projectId: 'example',
      query: 'ui theme style',
      limit: 4,
    })

    expect(candidates.some(item => item.id === 'A010.010.010')).toBe(true)
    expect(candidates[0]?.provenance.resource).toBe('project://example/architecture')
  })

  it('支持通过稳定 Node ID 精确寻址', () => {
    const root = mkdtempSync(join(tmpdir(), 'architecture-router-'))
    writeIndex(root, `\n  - id: A010\n    file: 010_interface.md\n    title: Interface Layer\n    summary: UI architecture\n    aliases: [ui]`)
    writeFileSync(join(root, '010_interface.md'), validArchitecture)

    const engine = new ArchitectureNavigatorEngine()
    engine.refreshProject('example', root, 'project://example/architecture')

    expect(engine.search({ projectId: 'example', query: 'A010.010.020' })[0]?.id).toBe(
      'A010.010.020',
    )
    expect(engine.getNode('example', 'A010.010.020')?.node.title).toBe('Layout')
  })

  it('索引建好后高频查询只使用内存缓存', () => {
    const root = mkdtempSync(join(tmpdir(), 'architecture-router-'))
    writeIndex(root, `\n  - id: A010\n    file: 010_interface.md\n    title: Interface Layer\n    summary: UI architecture\n    aliases: [ui, theme]`)
    writeFileSync(join(root, '010_interface.md'), validArchitecture)

    const engine = new ArchitectureNavigatorEngine()
    engine.refreshProject('example', root, 'project://example/architecture')
    rmSync(root, { recursive: true, force: true })

    expect(engine.search({ projectId: 'example', query: 'theme' }).length).toBeGreaterThan(0)
    expect(engine.getNode('example', 'A010.010.010')?.node.title).toBe('Theme')
  })

  it('存在未索引正式文件时拒绝接入', () => {
    const root = mkdtempSync(join(tmpdir(), 'architecture-router-'))
    writeIndex(root, `\n  - id: A010\n    file: 010_interface.md\n    title: Interface Layer\n    summary: UI architecture\n    aliases: [ui]`)
    writeFileSync(join(root, '010_interface.md'), validArchitecture)
    writeFileSync(join(root, '020_orphan.md'), '# [A020] Orphan\nRole: orphan\n')

    const engine = new ArchitectureNavigatorEngine()
    expect(() => engine.refreshProject(
      'example',
      root,
      'project://example/architecture',
    )).toThrow('正式可路由文件未进入 00_INDEX')
  })

  it('允许 Relation 跨 Architecture 文件指向已存在节点', () => {
    const root = mkdtempSync(join(tmpdir(), 'architecture-router-'))
    writeIndex(root, `\n  - id: A010\n    file: 010_product.md\n    title: Product\n    summary: product architecture\n    aliases: [product]\n  - id: A020\n    file: 020_runtime.md\n    title: Runtime\n    summary: runtime architecture\n    aliases: [runtime]`)
    writeFileSync(
      join(root, '010_product.md'),
      '# [A010] Product\nRole: product\nRelations: A020.010\n',
    )
    writeFileSync(
      join(root, '020_runtime.md'),
      '# [A020] Runtime\nRole: runtime\n\n## [A020.010] Execution\nRole: execution\nRelations: A010\n',
    )

    const engine = new ArchitectureNavigatorEngine()
    const snapshot = engine.refreshProject('example', root, 'project://example/architecture')

    expect(snapshot.state).toBe('ready')
    expect(engine.getNode('example', 'A010')?.node.relations).toEqual(['A020.010'])
  })

  it('Architecture Relation 指向不存在节点时拒绝接入', () => {
    const root = mkdtempSync(join(tmpdir(), 'architecture-router-'))
    writeIndex(root, `\n  - id: A010\n    file: 010_product.md\n    title: Product\n    summary: product architecture\n    aliases: [product]`)
    writeFileSync(
      join(root, '010_product.md'),
      '# [A010] Product\nRole: product\nRelations: A999.010\n',
    )

    const engine = new ArchitectureNavigatorEngine()
    expect(() => engine.refreshProject(
      'example',
      root,
      'project://example/architecture',
    )).toThrow('Relation 目标不存在 A010 -> A999.010')
  })

  it('非 Architecture 资源 ID 不做 Architecture 关系完整性误判', () => {
    const root = mkdtempSync(join(tmpdir(), 'architecture-router-'))
    writeIndex(root, `\n  - id: A010\n    file: 010_product.md\n    title: Product\n    summary: product architecture\n    aliases: [product]`)
    writeFileSync(
      join(root, '010_product.md'),
      '# [A010] Product\nRole: product\nRelations: R010, K020, G030\n',
    )

    const engine = new ArchitectureNavigatorEngine()
    expect(engine.refreshProject('example', root, 'project://example/architecture').state).toBe('ready')
  })

  it('空标准接口可以 READY，且查询返回空候选', () => {
    const root = mkdtempSync(join(tmpdir(), 'architecture-router-'))
    writeIndex(root, ' []')

    const engine = new ArchitectureNavigatorEngine()
    const snapshot = engine.refreshProject(
      'empty-project',
      root,
      'project://empty-project/architecture',
    )

    expect(snapshot.state).toBe('ready')
    expect(snapshot.nodeCount).toBe(0)
    expect(engine.search({ projectId: 'empty-project', query: 'anything' })).toEqual([])
  })
})
