import { describe, expect, it } from 'vitest'
import {
  checkExecutionEventProtocol,
  createInitialObligationLedger,
} from '../src/phase0-runtime.js'
import {
  computeTaskSupervisionContractHash,
} from '../src/canonical-json.js'
import { contractFixture, eventFixture, FIXED_TIME } from './fixtures.js'

describe('Execution Supervisor cross-host protocol', () => {
  it('accepts the first event only when identity, contract and sequence match', () => {
    const contract = contractFixture()
    const ledger = createInitialObligationLedger(contract, FIXED_TIME)
    const event = eventFixture()
    expect(checkExecutionEventProtocol({
      contract,
      ledger,
      event,
      detectedAt: FIXED_TIME,
    })).toEqual([])
  })

  it('fails closed on an Agent/Task identity mismatch', () => {
    const contract = contractFixture()
    const ledger = createInitialObligationLedger(contract, FIXED_TIME)
    const event = eventFixture()
    const violations = checkExecutionEventProtocol({
      contract,
      ledger,
      event: {
        ...event,
        identity: { ...event.identity, agentId: 'OTHER-AGENT' },
      },
      detectedAt: FIXED_TIME,
    })
    expect(violations.map(item => item.kind)).toContain('IDENTITY_MISMATCH')
    expect(violations.every(item => item.blocking)).toBe(true)
  })

  it('fails closed on sequence gaps and contract substitution', () => {
    const contract = contractFixture()
    const ledger = createInitialObligationLedger(contract, FIXED_TIME)
    const event = eventFixture(3)
    const violations = checkExecutionEventProtocol({
      contract,
      ledger,
      event: {
        ...event,
        integrity: {
          ...event.integrity,
          contractHash: 'f'.repeat(64),
        },
      },
      detectedAt: FIXED_TIME,
    })
    expect(violations.map(item => item.kind)).toEqual(expect.arrayContaining([
      'CONTRACT_HASH_MISMATCH',
      'EVENT_SEQUENCE_GAP',
    ]))
  })

  it('requires one continuous event hash chain after the first event', () => {
    const contract = contractFixture()
    const first = eventFixture()
    const ledger = {
      ...createInitialObligationLedger(contract, FIXED_TIME),
      contractHash: computeTaskSupervisionContractHash(contract),
      ledgerVersion: 1,
      lastAcceptedSequence: 1,
      lastEventHash: first.integrity.eventHash,
    }
    const second = eventFixture(2, '0'.repeat(64))
    const violations = checkExecutionEventProtocol({
      contract,
      ledger,
      event: second,
      detectedAt: FIXED_TIME,
    })
    expect(violations.map(item => item.kind)).toContain('EVENT_TAMPERING')
  })
})
