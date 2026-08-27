import { describe, expect, it } from 'vitest'
import {
  GLOBAL_KNOWLEDGE_LIBRARY_ID,
  knowledgeLibraryKey,
  parseKnowledgeReference,
  qualifyKnowledgeId,
} from '../src/knowledge-address.js'

describe('Knowledge Library scope address', () => {
  it('Global 与 Project 可以拥有相同 K-ID 但 URI 不冲突', () => {
    const global = qualifyKnowledgeId({ kind: 'global' }, 'K001.001')
    const project = qualifyKnowledgeId({ kind: 'project', projectId: 'et-tool' }, 'K001.001')

    expect(global).toBe('knowledge://global/K001.001')
    expect(project).toBe('knowledge://project/et-tool/K001.001')
    expect(global).not.toBe(project)
  })

  it('解析 Global / Project / 当前项目裸 K-ID', () => {
    expect(parseKnowledgeReference('knowledge://global/K010.020')).toEqual({
      scope: { kind: 'global' },
      knowledgeId: 'K010.020',
    })
    expect(parseKnowledgeReference('knowledge://project/et-tool/K010.020')).toEqual({
      scope: { kind: 'project', projectId: 'et-tool' },
      knowledgeId: 'K010.020',
    })
    expect(parseKnowledgeReference('K010.020', 'et-tool')).toEqual({
      scope: { kind: 'project', projectId: 'et-tool' },
      knowledgeId: 'K010.020',
    })
  })

  it('裸 K-ID 无当前项目时拒绝，避免错误跨库解析', () => {
    expect(() => parseKnowledgeReference('K010.020')).toThrow('currentProjectId')
  })

  it('Global 使用独立内部 Library Key', () => {
    expect(knowledgeLibraryKey({ kind: 'global' })).toBe(GLOBAL_KNOWLEDGE_LIBRARY_ID)
    expect(knowledgeLibraryKey({ kind: 'project', projectId: 'et-tool' })).toBe('et-tool')
  })
})
