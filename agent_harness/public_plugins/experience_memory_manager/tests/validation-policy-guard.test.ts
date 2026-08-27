import { describe, expect, it } from 'vitest'
import { ExperienceMemoryManagerService } from '../src/service.js'

describe('Experience / Memory validation-policy guard', () => {
  it('knowledge-library-v0.2 禁止旧 promoteToKnowledge 绕过 Validation Policy', () => {
    const service = Object.create(ExperienceMemoryManagerService.prototype) as any
    service.runtimeContext = {
      knowledgeManager: {
        getIndex: () => ({ libraryMode: 'library-v0.2' }),
      },
    }
    service.requireCandidateState = () => ({
      record: { version: 1 },
      candidate: {
        candidateId: 'EXP-test',
        projectId: 'example',
        taskId: 'TASK-1',
        title: 'Experience',
        fact: 'Reusable fact',
        evidenceRefs: ['EV-1'],
        status: 'CANDIDATE',
        createdAt: '2026-08-21T00:00:00.000Z',
      },
    })

    expect(() => service.promoteToKnowledge('example', {
      candidateId: 'EXP-test',
      fileId: 'K010',
      parentNodeId: 'K010.010',
      nodeId: 'K010.010.010',
      title: 'Experience',
    })).toThrow('禁止 Experience Manager 直接写入 VALIDATED Knowledge')
  })
})
