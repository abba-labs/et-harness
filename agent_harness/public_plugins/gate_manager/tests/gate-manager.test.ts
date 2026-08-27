import { mkdtempSync, unlinkSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { tmpdir } from 'node:os'
import { describe, expect, it } from 'vitest'
import { parseGateFile } from '../src/gate-parser.js'
import { GateManagerEngine } from '../src/gate-manager-engine.js'

const validGates = `standard: gate-v0.1
file_id: G010
title: Interface Gates
nodes:
  - id: G010.010
    title: Visual Validation
    children:
      - id: G010.010.010
        title: UI Build
        gate:
          level: MUST
          when: 修改 UI 页面、主题或布局相关代码
          steps:
            - id: build
              tool: build.execute
              args:
                target: ui
            - id: unit
              tool: test.execute
          pass:
            mode: all_steps_pass
          refs: [R010.010.010.010]
      - id: G010.010.020
        title: Visual Review
        gate:
          level: MAY
          when: 修改视觉风格且需要人工视觉确认
          steps:
            - id: review
              tool: review.visual
          pass:
            mode: approved
`

const writeIndex = (root: string, files: string): void => {
  writeFileSync(
    join(root, '00_INDEX.md'),
    `---\ninterface: project-resource-index-v0.1\nresource: gates\nstandard: gate-v0.1\nfiles:${files}\n---\n`,
  )
}

describe('Gate Tree parser', () => {
  it('解析 Branch、Gate Leaf 和 Execution 字段', () => {
    const result = parseGateFile('G010', '010_interface.yaml', validGates)
    expect(result.nodes.map(node => node.id)).toContain('G010.010.010')
    const gate = result.nodes.find(node => node.id === 'G010.010.010')
    expect(gate?.isGate).toBe(true)
    expect(gate?.location).toBe('010_interface.yaml#G010.010.010')
    expect(gate?.gate?.level).toBe('MUST')
    expect(gate?.gate?.steps.map(step => step.tool)).toEqual(['build.execute', 'test.execute'])
    expect(gate?.gate?.refs).toEqual(['R010.010.010.010'])
  })

  it('Branch 和 gate 同时存在时拒绝', () => {
    const invalid = `standard: gate-v0.1\nfile_id: G010\ntitle: X\nnodes:\n  - id: G010.010\n    title: X\n    children: []\n    gate:\n      level: MUST\n      when: x\n      steps: [{id: x, tool: test.execute}]\n      pass: ok\n`
    expect(() => parseGateFile('G010', '010_bad.yaml', invalid)).toThrow('不能同时定义')
  })

  it('非法 Tool Capability 时拒绝', () => {
    const invalid = `standard: gate-v0.1\nfile_id: G010\ntitle: X\nnodes:\n  - id: G010.010\n    title: Gate\n    gate:\n      level: MUST\n      when: x\n      steps:\n        - id: x\n          tool: BAD TOOL\n      pass: ok\n`
    expect(() => parseGateFile('G010', '010_bad.yaml', invalid)).toThrow('合法 Tool Capability')
  })

  it('缺少 pass 时拒绝', () => {
    const invalid = `standard: gate-v0.1\nfile_id: G010\ntitle: X\nnodes:\n  - id: G010.010\n    title: Gate\n    gate:\n      level: MUST\n      when: x\n      steps:\n        - id: x\n          tool: test.execute\n`
    expect(() => parseGateFile('G010', '010_bad.yaml', invalid)).toThrow('gate.pass')
  })
})

describe('Gate Manager cached routing', () => {
  it('建立 Gate Cache 并自然语言命中 MUST Gate', () => {
    const root = mkdtempSync(join(tmpdir(), 'gate-router-'))
    writeIndex(root, `\n  - id: G010\n    file: 010_interface.yaml\n    title: Interface Gates\n    summary: UI visual build and review gates\n    aliases: [ui, visual, build, theme, layout]`)
    writeFileSync(join(root, '010_interface.yaml'), validGates)

    const engine = new GateManagerEngine()
    const snapshot = engine.refreshProject('example', root, 'project://example/gates')
    expect(snapshot.gateCount).toBe(2)

    const result = engine.search({ projectId: 'example', query: 'ui theme build' })
    expect(result.some(item => item.id === 'G010.010.010')).toBe(true)
    const hit = result.find(item => item.id === 'G010.010.010')
    expect(hit?.metadata?.level).toBe('MUST')
    expect(hit?.provenance.location).toBe('010_interface.yaml#G010.010.010')
  })

  it('稳定 G ID 精确寻址并生成 Execution Plan', () => {
    const root = mkdtempSync(join(tmpdir(), 'gate-router-'))
    writeIndex(root, `\n  - id: G010\n    file: 010_interface.yaml\n    title: Interface Gates\n    summary: UI gates\n    aliases: [ui]`)
    writeFileSync(join(root, '010_interface.yaml'), validGates)

    const engine = new GateManagerEngine()
    engine.refreshProject('example', root, 'project://example/gates')
    const exact = engine.search({ projectId: 'example', query: 'G010.010.010' })
    expect(exact).toHaveLength(1)
    expect(exact[0]?.relevance).toBe(1)

    const plan = engine.getExecutionPlan('example', 'G010.010.010')
    expect(plan?.level).toBe('MUST')
    expect(plan?.steps.map(step => step.id)).toEqual(['build', 'unit'])
    expect(plan?.steps[0]?.tool).toBe('build.execute')
  })

  it('刷新后查询使用 Cache', () => {
    const root = mkdtempSync(join(tmpdir(), 'gate-router-'))
    writeIndex(root, `\n  - id: G010\n    file: 010_interface.yaml\n    title: Interface Gates\n    summary: UI gates\n    aliases: [ui]`)
    const filePath = join(root, '010_interface.yaml')
    writeFileSync(filePath, validGates)
    const engine = new GateManagerEngine()
    engine.refreshProject('example', root, 'project://example/gates')
    unlinkSync(filePath)
    expect(engine.getExecutionPlan('example', 'G010.010.010')?.gateId).toBe('G010.010.010')
  })

  it('刷新失败清除旧 Cache', () => {
    const root = mkdtempSync(join(tmpdir(), 'gate-router-'))
    writeIndex(root, `\n  - id: G010\n    file: 010_interface.yaml\n    title: Interface Gates\n    summary: UI gates\n    aliases: [ui]`)
    const filePath = join(root, '010_interface.yaml')
    writeFileSync(filePath, validGates)
    const engine = new GateManagerEngine()
    engine.refreshProject('example', root, 'project://example/gates')
    writeFileSync(filePath, 'standard: gate-v0.1\nfile_id: G010\ntitle: X\nnodes: nope\n')
    expect(() => engine.refreshProject('example', root, 'project://example/gates')).toThrow('nodes 必须是数组')
    expect(engine.getIndex('example')).toBeUndefined()
  })

  it('存在未索引 Gate 文件时拒绝', () => {
    const root = mkdtempSync(join(tmpdir(), 'gate-router-'))
    writeIndex(root, `\n  - id: G010\n    file: 010_interface.yaml\n    title: Interface Gates\n    summary: UI gates\n    aliases: [ui]`)
    writeFileSync(join(root, '010_interface.yaml'), validGates)
    writeFileSync(join(root, '020_orphan.yaml'), 'standard: gate-v0.1\nfile_id: G020\ntitle: O\nnodes: []\n')
    const engine = new GateManagerEngine()
    expect(() => engine.refreshProject('example', root, 'project://example/gates')).toThrow(
      '正式可路由文件未进入 00_INDEX',
    )
  })

  it('空标准接口可以 READY', () => {
    const root = mkdtempSync(join(tmpdir(), 'gate-router-'))
    writeIndex(root, ' []')
    const engine = new GateManagerEngine()
    const snapshot = engine.refreshProject('empty', root, 'project://empty/gates')
    expect(snapshot.state).toBe('ready')
    expect(snapshot.gateCount).toBe(0)
  })
})
