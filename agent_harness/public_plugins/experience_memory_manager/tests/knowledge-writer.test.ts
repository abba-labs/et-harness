import { describe, expect, it } from 'vitest'
import { parseKnowledgeFile } from '@agent-harness/knowledge-manager'
import { insertKnowledgeLeaf } from '../src/knowledge-writer.js'
import type { ExperienceCandidate } from '../src/contracts.js'

const candidate: ExperienceCandidate = {
  projectId: 'p1',
  taskId: 'T1',
  candidateId: 'EXP-1',
  status: 'CANDIDATE',
  title: 'Theme lesson',
  fact: '修改主题后需要重新读取运行时状态。',
  scope: 'ui theme',
  evidenceRefs: ['EV-1'],
  refs: ['R010.010'],
  createdAt: '2026-08-21T00:00:00.000Z',
}

const original = `# [K010] Project Knowledge

## [K010.010] UI

### [K010.010.010] Existing
Status: VALIDATED
Fact: 已有知识。
Provenance: EV-0

## [K010.020] Runtime

### [K010.020.010] Existing Runtime
Status: VALIDATED
Fact: 运行时知识。
Provenance: EV-X
`

describe('Experience Knowledge Writer', () => {
  it('按稳定 K 地址插入 VALIDATED Knowledge Leaf', () => {
    const updated = insertKnowledgeLeaf(
      original,
      'K010.010',
      'K010.010.020',
      'Theme Refresh',
      candidate,
    )
    const parsed = parseKnowledgeFile('K010', '010_project.md', updated)
    const node = parsed.nodes.find(item => item.id === 'K010.010.020')
    expect(node?.status).toBe('VALIDATED')
    expect(node?.fact).toBe(candidate.fact)
    expect(node?.provenance).toBe('EV-1')
    expect(node?.refs).toEqual(['R010.010'])
  })

  it('禁止写入非直接子地址', () => {
    expect(() => insertKnowledgeLeaf(
      original,
      'K010.010',
      'K010.020.020',
      'Wrong',
      candidate,
    )).toThrow('直接子节点')
  })

  it('禁止复用已有 Knowledge ID', () => {
    expect(() => insertKnowledgeLeaf(
      original,
      'K010.010',
      'K010.010.010',
      'Duplicate',
      candidate,
    )).toThrow('已存在')
  })
})
