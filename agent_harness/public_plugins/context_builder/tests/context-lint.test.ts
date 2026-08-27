import { describe, expect, it } from 'vitest'
import {
  lintHandle,
  lintProgressLedger,
  lintRecentEvent,
  lintTaskLedger,
} from '../src/context-lint.js'

const stamp = '2026-08-22T10:00:00.000Z'

const baseTaskLedger = () => ({
  goal: '修复 FPGA Flash Backend timeout',
  phase: 'analysis' as const,
  scopeRefs: ['A010.010'],
  constraintRefs: ['R010.010'],
  confirmed: [{ text: 'Flash Backend 属于 A010.010。', refs: ['A010.010'] }],
  assumptions: [{ text: 'ready bit 可能未置位。', refs: [] }],
  openIssues: [{ text: '需要确认 ready bit 状态。', refs: [] }],
  plan: ['读取 ready bit 状态'],
  updatedAt: stamp,
})

describe('Context Lint v0.1', () => {
  it('合法 Task Ledger 通过', () => {
    const result = lintTaskLedger(baseTaskLedger())
    expect(result.valid).toBe(true)
    expect(result.errors).toHaveLength(0)
  })

  it('Confirmed 没有 Ref 时拒绝', () => {
    const ledger = baseTaskLedger()
    const result = lintTaskLedger({
      ...ledger,
      confirmed: [{ text: 'Flash Backend 属于当前模块。', refs: [] }],
    })
    expect(result.valid).toBe(false)
    expect(result.errors.some(item => item.code === 'CONFIRMED_WITHOUT_REF')).toBe(true)
  })

  it('Confirmed 含明显不确定判断时拒绝', () => {
    const ledger = baseTaskLedger()
    const result = lintTaskLedger({
      ...ledger,
      confirmed: [{ text: 'timeout 可能由 ready bit 引起。', refs: ['A010.010'] }],
    })
    expect(result.valid).toBe(false)
    expect(result.errors.some(item => item.code === 'CONFIRMED_UNCERTAIN')).toBe(true)
  })

  it('同一内容不能同时是 Confirmed 和 Assumption', () => {
    const ledger = baseTaskLedger()
    const result = lintTaskLedger({
      ...ledger,
      confirmed: [{ text: 'ready bit 未置位。', refs: ['evidence://project/demo/EV-1'] }],
      assumptions: [{ text: 'ready bit 未置位。', refs: [] }],
    })
    expect(result.errors.some(item => item.code === 'FACT_ASSUMPTION_COLLISION')).toBe(true)
  })

  it('多行和超长 Progress 内容拒绝', () => {
    const result = lintProgressLedger({
      lastAction: '修改 reset\n然后重新测试',
      lastResult: 'FAIL',
      touchedRefs: ['file://source/backend.ts'],
      blockers: [],
      next: ['X'.repeat(221)],
      evidenceRefs: [],
      updatedAt: stamp,
    })
    expect(result.errors.some(item => item.code === 'MULTILINE_TEXT')).toBe(true)
    expect(result.errors.some(item => item.code === 'TEXT_TOO_LONG')).toBe(true)
  })

  it('Recent Tail 和 Handle 只允许短文本', () => {
    const recent = lintRecentEvent({ kind: 'ACTION', summary: 'A'.repeat(301) })
    const handle = lintHandle({
      kind: 'file',
      reference: 'file://source/backend.ts',
      summary: 'line1\nline2',
    })
    expect(recent.valid).toBe(false)
    expect(handle.valid).toBe(false)
  })

  it('未知引用格式只警告，不阻断 Agent', () => {
    const ledger = baseTaskLedger()
    const result = lintTaskLedger({ ...ledger, scopeRefs: ['custom-reference'] })
    expect(result.valid).toBe(true)
    expect(result.warnings.some(item => item.code === 'NON_STANDARD_REFERENCE')).toBe(true)
  })
})
