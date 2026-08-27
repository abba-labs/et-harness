import {
  existsSync,
  mkdtempSync,
  readFileSync,
  writeFileSync,
} from 'node:fs'
import { join } from 'node:path'
import { tmpdir } from 'node:os'
import { describe, expect, it } from 'vitest'
import { KnowledgeManagerEngine } from '../src/knowledge-manager-engine.js'
import { KnowledgeLibraryMutator } from '../src/knowledge-library-mutator.js'

const taxonomy = `standard: knowledge-library-v0.2
categories:
  - id: C010
    title: Knowledge
    aliases: [knowledge]
  - id: C020
    title: Experience
    aliases: [experience]
`

const setup = () => {
  const root = mkdtempSync(join(tmpdir(), 'knowledge-mutation-'))
  writeFileSync(join(root, 'TAXONOMY.yaml'), taxonomy)
  const engine = new KnowledgeManagerEngine()
  const projectId = 'example'
  const handle = 'project://example/knowledge'
  engine.refreshProject(projectId, root, handle)
  const reindex = () => engine.reindexProject(projectId, root, handle)
  const mutator = new KnowledgeLibraryMutator(engine, projectId, root, reindex)
  return { root, engine, projectId, mutator }
}

describe('Knowledge Library v0.2 mutation governance', () => {
  it('新增知识固定为 CANDIDATE，并自动分配 managed K-ID', () => {
    const { root, engine, projectId, mutator } = setup()
    const result = mutator.submitCandidate({
      categoryId: 'C010',
      title: 'DMA Access',
      fact: 'DMA cannot directly access the target TCM window.',
      provenance: 'SRC-001',
      tags: ['dma', 'tcm'],
    })

    expect(result.knowledgeId).toBe('K001.001')
    expect(result.file).toBe('001_library.md')
    expect(result.status).toBe('CANDIDATE')
    expect(engine.getNode(projectId, 'K001.001')?.node.category).toBe('C010')
    expect(readFileSync(join(root, '00_INDEX.md'), 'utf-8')).toContain('AUTO GENERATED')
  })

  it('Knowledge Contribution 不会自动创建不存在的分类', () => {
    const { root, mutator } = setup()
    expect(() => mutator.submitCandidate({
      categoryId: 'C999',
      title: 'Unknown',
      fact: 'This must not be written.',
      provenance: 'SRC-X',
    })).toThrow('Category 不存在')
    expect(existsSync(join(root, '001_library.md'))).toBe(false)
  })

  it('规范化 Fact 完全重复时拒绝，避免同义副本从最简单路径进入', () => {
    const { mutator } = setup()
    mutator.submitCandidate({
      categoryId: 'C010',
      title: 'DMA Access',
      fact: 'DMA cannot access DTCM directly.',
      provenance: 'SRC-001',
    })

    expect(() => mutator.submitCandidate({
      categoryId: 'C020',
      title: 'Duplicate',
      fact: 'DMA cannot access DTCM directly!',
      provenance: 'SRC-002',
    })).toThrow('重复 Knowledge Fact: K001.001')
  })

  it('Candidate 可以更新，但 K-ID 保持稳定', () => {
    const { engine, projectId, mutator } = setup()
    mutator.submitCandidate({
      categoryId: 'C010',
      title: 'Initial',
      fact: 'Initial candidate fact.',
      provenance: 'SRC-001',
    })

    const result = mutator.updateCandidate('K001.001', {
      title: 'Updated',
      fact: 'Updated candidate fact.',
      provenance: 'SRC-002',
    })

    expect(result.knowledgeId).toBe('K001.001')
    expect(engine.getNode(projectId, 'K001.001')?.node.title).toBe('Updated')
    expect(engine.getNode(projectId, 'K001.001')?.node.fact).toBe('Updated candidate fact.')
  })

  it('重分类只修改 C-ID，不改变 K-ID 或文件地址', () => {
    const { engine, projectId, mutator } = setup()
    mutator.submitCandidate({
      categoryId: 'C010',
      title: 'Reclassify',
      fact: 'This item will be reclassified.',
      provenance: 'SRC-001',
    })

    const result = mutator.reclassify('K001.001', 'C020')
    expect(result.knowledgeId).toBe('K001.001')
    expect(result.file).toBe('001_library.md')
    expect(engine.getNode(projectId, 'K001.001')?.node.category).toBe('C020')
  })

  it('分类只能显式新增、改名；ID 保持稳定', () => {
    const { engine, projectId, mutator } = setup()
    const added = mutator.addCategory({ parentId: 'C010', title: 'Chip' })
    expect(added.categoryId).toBe('C010.010')

    const renamed = mutator.renameCategory('C010.010', {
      title: 'Chip Knowledge',
      aliases: ['chip', 'mcu'],
    })
    expect(renamed.categoryId).toBe('C010.010')
    expect(engine.getTaxonomy(projectId)?.categories['C010.010']?.title).toBe('Chip Knowledge')
  })

  it('分类子树仍有有效 Knowledge 时禁止废弃', () => {
    const { mutator } = setup()
    mutator.submitCandidate({
      categoryId: 'C010',
      title: 'Keep Category',
      fact: 'Active knowledge blocks category deprecation.',
      provenance: 'SRC-001',
    })

    expect(() => mutator.deprecateCategory('C010')).toThrow('仍有非 DEPRECATED Knowledge')
    mutator.deprecateKnowledge('K001.001')
    expect(mutator.deprecateCategory('C010').status).toBe('DEPRECATED')
  })

  it('reindex 失败时回滚 canonical 写入，不留下半个知识文件', () => {
    const root = mkdtempSync(join(tmpdir(), 'knowledge-rollback-'))
    writeFileSync(join(root, 'TAXONOMY.yaml'), taxonomy)
    const engine = new KnowledgeManagerEngine()
    const projectId = 'rollback'
    const handle = 'project://rollback/knowledge'
    engine.refreshProject(projectId, root, handle)
    const mutator = new KnowledgeLibraryMutator(
      engine,
      projectId,
      root,
      () => { throw new Error('forced reindex failure') },
    )

    expect(() => mutator.submitCandidate({
      categoryId: 'C010',
      title: 'Rollback',
      fact: 'This write must be rolled back.',
      provenance: 'SRC-X',
    })).toThrow('forced reindex failure')

    expect(existsSync(join(root, '001_library.md'))).toBe(false)
  })
})
