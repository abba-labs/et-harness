import { describe, expect, it } from 'vitest'
import {
  EXECUTION_EVENT_BATCH_SCHEMA,
  validateExecutionEventBatch,
} from '../src/event-batch.js'
import {
  EXECUTION_SUPERVISOR_CONTRACT_VERSION,
} from '../src/contracts.js'
import {
  computeTaskSupervisionContractHash,
} from '../src/canonical-json.js'
import { contractFixture, eventFixture, FIXED_TIME } from './fixtures.js'

describe('Execution Event Batch v0.1', () => {
  it('accepts one bounded contiguous batch', () => {
    const contract = contractFixture()
    const first = eventFixture(1)
    const second = eventFixture(2, first.integrity.eventHash)
    const batch = {
      schema: EXECUTION_EVENT_BATCH_SCHEMA,
      contractVersion: EXECUTION_SUPERVISOR_CONTRACT_VERSION,
      batchId: 'BATCH-001',
      identity: contract.identity,
      contractHash: computeTaskSupervisionContractHash(contract),
      firstSequence: 1,
      lastSequence: 2,
      events: [first, second],
      createdAt: FIXED_TIME,
    }
    expect(validateExecutionEventBatch(batch)).toEqual({ valid: true, errors: [] })
  })

  it('rejects gaps and a broken intra-batch hash chain', () => {
    const contract = contractFixture()
    const first = eventFixture(1)
    const third = eventFixture(3, '0'.repeat(64))
    const result = validateExecutionEventBatch({
      schema: EXECUTION_EVENT_BATCH_SCHEMA,
      contractVersion: EXECUTION_SUPERVISOR_CONTRACT_VERSION,
      batchId: 'BATCH-002',
      identity: contract.identity,
      contractHash: computeTaskSupervisionContractHash(contract),
      firstSequence: 1,
      lastSequence: 3,
      events: [first, third],
      createdAt: FIXED_TIME,
    })
    expect(result.valid).toBe(false)
    expect(result.errors.join('\n')).toMatch(/expected sequence|hash chain|lastSequence/)
  })
})
