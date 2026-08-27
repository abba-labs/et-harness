import { describe, expect, it } from 'vitest'
import {
  GOVERNANCE_RUNTIME_CONTRACT_VERSION,
  type GovernanceSemanticExecutor,
  type GovernanceSemanticRequest,
} from '../src/contracts.js'

describe('Governance Runtime public contracts', () => {
  it('keeps the semantic executor model/host neutral', async () => {
    const executor: GovernanceSemanticExecutor = {
      executorId: 'mock',
      reflect(request: GovernanceSemanticRequest) {
        return {
          contractVersion: '0.1',
          taskId: request.taskId,
          turnId: request.turnId,
        }
      },
    }
    expect(GOVERNANCE_RUNTIME_CONTRACT_VERSION).toBe('0.1')
    expect(executor.executorId).toBe('mock')
  })
})
