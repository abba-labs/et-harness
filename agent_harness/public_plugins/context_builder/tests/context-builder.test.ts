import { describe, expect, it } from 'vitest'
import { ContextBuilderEngine } from '../src/context-builder-engine.js'
import ContextManagementService from '../src/context-management-service.js'
import { inject } from '../src/index.js'
import type { ContextResolvedItem } from '../src/contracts.js'

const item = (overrides: Partial<ContextResolvedItem> = {}): ContextResolvedItem => ({
  projectId: 'p1',
  kind: 'architecture',
  id: 'A010',
  title: 'Architecture',
  content: 'short content',
  priority: 'normal',
  required: false,
  provenance: 'project://p1/architecture#A010',
  warnings: [],
  ...overrides,
})

describe('Context Builder Engine', () => {
  it('显式声明 Knowledge Validation Policy 运行时依赖', () => {
    expect(inject).toContain('knowledgeValidationPolicy')
  })

  it('Context Manager 显式声明 sibling Context Builder 依赖', () => {
    expect(ContextManagementService.inject).toContain('contextBuilder')
  })

  it('拒绝跨项目内容', () => {
    const engine = new ContextBuilderEngine()
    expect(() => engine.build(
      { projectId: 'p1', references: [] },
      [item({ projectId: 'p2' })],
    )).toThrow('拒绝跨项目内容')
  })

  it('同一资源去重并保留更高优先级', () => {
    const engine = new ContextBuilderEngine()
    const result = engine.build(
      { projectId: 'p1', references: [] },
      [item({ priority: 'low' }), item({ priority: 'high' })],
    )
    expect(result.items).toHaveLength(1)
    expect(result.items[0]?.priority).toBe('high')
  })

  it('预算不足时省略低优先级项，但保留 required', () => {
    const engine = new ContextBuilderEngine()
    const required = item({
      kind: 'rule',
      id: 'R010.010',
      title: 'Required Rule',
      content: 'X'.repeat(1400),
      priority: 'required',
      required: true,
    })
    const low = item({
      id: 'A020',
      title: 'Low Architecture',
      content: 'Y'.repeat(1400),
      priority: 'low',
    })
    const result = engine.build(
      { projectId: 'p1', references: [], maxChars: 1000 },
      [required, low],
    )
    expect(result.items.some(x => x.id === 'R010.010')).toBe(true)
    expect(result.omitted).toContain('architecture:A020')
    expect(result.overBudget).toBe(true)
  })

  it('在同一 high 预算竞争中优先保留已选出的 prior Context', () => {
    const engine = new ContextBuilderEngine()
    const result = engine.build(
      { projectId: 'p1', references: [], maxChars: 1000 },
      [
        item({
          kind: 'inline',
          id: 'prior-context-TASK-OLD',
          title: 'Prior Context',
          content: 'P'.repeat(650),
          priority: 'high',
        }),
        item({
          id: 'A020',
          title: 'Additional Architecture',
          content: 'A'.repeat(650),
          priority: 'high',
        }),
      ],
    )
    expect(result.items.map(value => value.id)).toContain('prior-context-TASK-OLD')
    expect(result.omitted).toContain('architecture:A020')
  })

  it('不会截断 item 语义内容', () => {
    const engine = new ContextBuilderEngine()
    const content = '完整规则正文'.repeat(50)
    const result = engine.build(
      { projectId: 'p1', references: [], maxChars: 5000 },
      [item({ kind: 'rule', id: 'R010', content, priority: 'required', required: true })],
    )
    expect(result.text).toContain(content)
  })
})
