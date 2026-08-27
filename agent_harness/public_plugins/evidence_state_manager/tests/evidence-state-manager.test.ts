import { mkdtempSync } from 'node:fs'
import { join } from 'node:path'
import { tmpdir } from 'node:os'
import { describe, expect, it } from 'vitest'
import { EvidenceStateEngine } from '../src/evidence-state-engine.js'

describe('Evidence State Engine', () => {
  it('Evidence 追加记录并可按 task / result 查询', () => {
    const root = mkdtempSync(join(tmpdir(), 'evidence-state-'))
    const engine = new EvidenceStateEngine(root)
    const pass = engine.recordEvidence({
      projectId: 'p1',
      taskId: 'TASK-1',
      kind: 'gate',
      result: 'PASS',
      summary: 'build pass',
      source: 'build.execute',
      gateId: 'G010.010',
    })
    engine.recordEvidence({
      projectId: 'p1',
      taskId: 'TASK-1',
      kind: 'gate',
      result: 'FAIL',
      summary: 'old fail',
      source: 'test.execute',
    })

    expect(engine.listEvidence({ projectId: 'p1', taskId: 'TASK-1' })).toHaveLength(2)
    expect(engine.listEvidence({ projectId: 'p1', result: 'PASS' })[0]?.evidenceId).toBe(pass.evidenceId)
    expect(engine.getEvidence('p1', pass.evidenceId)?.summary).toBe('build pass')
  })

  it('State 版本递增并支持 expectedVersion 防止覆盖', () => {
    const root = mkdtempSync(join(tmpdir(), 'evidence-state-'))
    const engine = new EvidenceStateEngine(root)
    const first = engine.updateState({
      projectId: 'p1',
      scope: 'task:T1',
      key: 'status',
      value: 'IMPLEMENTED',
      reason: 'code changed',
      expectedVersion: 0,
    })
    expect(first.version).toBe(1)

    const second = engine.updateState({
      projectId: 'p1',
      scope: 'task:T1',
      key: 'status',
      value: 'VALIDATED',
      reason: 'validated',
      expectedVersion: 1,
    })
    expect(second.version).toBe(2)
    expect(() => engine.updateState({
      projectId: 'p1',
      scope: 'task:T1',
      key: 'status',
      value: 'BAD',
      reason: 'stale writer',
      expectedVersion: 1,
    })).toThrow('version conflict')
  })

  it('State 引用 Evidence 时必须属于同一项目且真实存在', () => {
    const root = mkdtempSync(join(tmpdir(), 'evidence-state-'))
    const engine = new EvidenceStateEngine(root)
    const evidence = engine.recordEvidence({
      projectId: 'p1',
      taskId: 'T1',
      kind: 'test',
      result: 'PASS',
      summary: 'pass',
      source: 'test.execute',
    })

    const state = engine.updateState({
      projectId: 'p1',
      scope: 'task:T1',
      key: 'validation',
      value: 'PASS',
      reason: 'evidence-backed',
      evidenceRefs: [evidence.evidenceId],
    })
    expect(state.evidenceRefs).toEqual([evidence.evidenceId])

    expect(() => engine.updateState({
      projectId: 'p2',
      scope: 'task:T1',
      key: 'validation',
      value: 'PASS',
      reason: 'wrong project',
      evidenceRefs: [evidence.evidenceId],
    })).toThrow('不存在或不属于当前项目')
  })

  it('State 在新 Engine 实例中可恢复', () => {
    const root = mkdtempSync(join(tmpdir(), 'evidence-state-'))
    new EvidenceStateEngine(root).updateState({
      projectId: 'p1',
      scope: 'project',
      key: 'phase',
      value: 'P3',
      reason: 'phase update',
    })
    const recovered = new EvidenceStateEngine(root).readState('p1', 'project', 'phase')
    expect(recovered?.value).toBe('P3')
    expect(recovered?.version).toBe(1)
  })
})
