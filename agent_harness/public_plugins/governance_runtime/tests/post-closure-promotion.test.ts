import { describe, expect, it } from 'vitest'
import GovernanceRuntimeService from '../src/service.js'

describe('Governance Runtime post-Closure Knowledge validation', () => {
  it('promotion policy failure becomes warning instead of throwing', () => {
    const service = Object.create(GovernanceRuntimeService.prototype) as any
    service.runtimeContext = {
      knowledgeManager: {
        resolveKnowledgeReference: () => ({
          knowledgeUri: 'knowledge://project/et-tool/K001.001',
          libraryScope: { kind: 'project', projectId: 'et-tool' },
          result: {
            projectId: 'et-tool',
            node: {
              id: 'K001.001',
              isLeaf: true,
              status: 'CANDIDATE',
              refs: [],
            },
          },
        }),
        listVerifications: () => [],
        recordVerification: () => { throw new Error('should not be called') },
      },
      knowledgeValidationPolicy: {
        evaluate: () => { throw new Error('promotion probe failed') },
        promote: () => { throw new Error('should not be called') },
      },
    }

    const result = service.autoValidateKnowledgeCandidates('et-tool', {
      attemptId: 'closure-attempt-1',
      moduleReceipts: [{
        moduleId: 'knowledge-closure',
        candidateRefs: ['knowledge://project/et-tool/K001.001'],
      }],
    })

    expect(result.promotions).toEqual([])
    expect(result.warnings).toHaveLength(1)
    expect(result.warnings[0]).toContain('promotion probe failed')
  })
})
