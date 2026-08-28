import { describe, expect, it } from 'vitest'
import {
  EXECUTION_RECEIPT_SCHEMA,
  EXECUTION_SUPERVISOR_CONTRACT_VERSION,
} from '../src/contracts.js'
import {
  createInitialObligationLedger,
  createSupervisionViolation,
} from '../src/phase0-runtime.js'
import {
  validateExecutionReceipt,
  validateSupervisionViolation,
} from '../src/receipt-validation.js'
import { contractFixture, eventFixture, FIXED_TIME } from './fixtures.js'

describe('Execution Supervisor receipts', () => {
  it('accepts one deterministic accepted-event Receipt', () => {
    const contract = contractFixture()
    const ledger = createInitialObligationLedger(contract, FIXED_TIME)
    const event = eventFixture()
    const receipt = {
      schema: EXECUTION_RECEIPT_SCHEMA,
      contractVersion: EXECUTION_SUPERVISOR_CONTRACT_VERSION,
      receiptId: 'RECEIPT-001',
      identity: contract.identity,
      eventId: event.eventId,
      sequence: event.sequence,
      eventHash: event.integrity.eventHash,
      disposition: 'ACCEPTED',
      ledgerVersionBefore: ledger.ledgerVersion,
      ledgerVersionAfter: ledger.ledgerVersion + 1,
      changedObligationIds: [],
      violationIds: [],
      receivedAt: FIXED_TIME,
    }
    expect(validateExecutionReceipt(receipt)).toEqual({ valid: true, errors: [] })
  })

  it('rejects a duplicate Receipt that mutates the Ledger', () => {
    const contract = contractFixture()
    const event = eventFixture()
    const result = validateExecutionReceipt({
      schema: EXECUTION_RECEIPT_SCHEMA,
      contractVersion: EXECUTION_SUPERVISOR_CONTRACT_VERSION,
      receiptId: 'RECEIPT-002',
      identity: contract.identity,
      eventId: event.eventId,
      sequence: event.sequence,
      eventHash: event.integrity.eventHash,
      disposition: 'DUPLICATE',
      ledgerVersionBefore: 2,
      ledgerVersionAfter: 3,
      changedObligationIds: [],
      violationIds: [],
      receivedAt: FIXED_TIME,
    })
    expect(result.valid).toBe(false)
    expect(result.errors.join('\n')).toContain('cannot advance')
  })

  it('keeps warnings non-blocking and errors blocking by default', () => {
    const identity = contractFixture().identity
    const warning = createSupervisionViolation({
      violationId: 'V-WARNING-001',
      identity,
      kind: 'HOST_ADAPTER_PROTOCOL_ERROR',
      severity: 'WARNING',
      detectedAt: FIXED_TIME,
      details: 'One optional metadata field was omitted.',
    })
    const error = createSupervisionViolation({
      violationId: 'V-ERROR-001',
      identity,
      kind: 'UNSUPPORTED_PASS_CLAIM',
      severity: 'ERROR',
      detectedAt: FIXED_TIME,
      details: 'PASS was asserted without trusted Evidence.',
    })
    expect(warning.blocking).toBe(false)
    expect(error.blocking).toBe(true)
    expect(validateSupervisionViolation(warning)).toEqual({ valid: true, errors: [] })
    expect(validateSupervisionViolation(error)).toEqual({ valid: true, errors: [] })
  })
})
