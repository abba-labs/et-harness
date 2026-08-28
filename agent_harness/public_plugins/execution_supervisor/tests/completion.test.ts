import { describe, expect, it } from 'vitest'
import {
  addViolation,
  createObligationLedger,
  evaluateCompletion,
  updateObligationLedgerEntry,
  type EvidenceAuthority,
  type EvidenceOutcome,
  type ObligationLedger,
  type TaskSupervisionContract,
} from '../src/index.js'
import { contractFixture, evidence } from './fixtures.js'

const satisfy = (
  ledger: ObligationLedger,
  contract: TaskSupervisionContract,
  obligationId: string,
  authority: EvidenceAuthority,
  outcome: EvidenceOutcome,
  sequence: number,
): ObligationLedger => updateObligationLedgerEntry(ledger, contract, {
  obligationId,
  status: 'SATISFIED',
  sequence,
  eventRef: `event://fixture/${sequence}`,
  evidence: [evidence(obligationId, authority, outcome, sequence)],
})

describe('Execution Supervisor deterministic completion evaluation', () => {
  it('advances only through execution, Reflection and Closure stages', () => {
    const contract = contractFixture()
    let ledger = createObligationLedger(contract)
    expect(evaluateCompletion(contract, ledger).status).toBe('IN_PROGRESS')

    ledger = satisfy(ledger, contract, 'OBL-READ', 'EXTERNAL_SOURCE', 'FOUND', 1)
    ledger = satisfy(ledger, contract, 'OBL-OUTPUT', 'HOST', 'PRESENT', 2)
    ledger = satisfy(
      ledger,
      contract,
      'OBL-VALIDATE',
      'PROJECT_VALIDATOR',
      'PASS',
      3,
    )
    expect(evaluateCompletion(contract, ledger).status).toBe(
      'READY_FOR_REFLECTION',
    )

    ledger = satisfy(ledger, contract, 'OBL-REFLECT', 'FRAMEWORK', 'RECORDED', 4)
    ledger = satisfy(ledger, contract, 'OBL-CLASSIFY', 'FRAMEWORK', 'RECORDED', 5)
    expect(evaluateCompletion(contract, ledger).status).toBe(
      'READY_FOR_CLOSURE',
    )

    ledger = satisfy(ledger, contract, 'OBL-CONTEXT', 'FRAMEWORK', 'RECORDED', 6)
    ledger = satisfy(ledger, contract, 'OBL-KNOWLEDGE', 'FRAMEWORK', 'RECORDED', 7)
    ledger = satisfy(ledger, contract, 'OBL-TURN', 'FRAMEWORK', 'RECORDED', 8)
    const complete = evaluateCompletion(contract, ledger)
    expect(complete.status).toBe('COMPLETE')
    expect(complete.pendingMustObligationIds).toEqual([])
    expect(complete.blockingViolationIds).toEqual([])
    expect(complete.evaluationHash).toMatch(/^[0-9a-f]{64}$/)
  })

  it('does not accept an Agent declaration as Project Validator PASS Evidence', () => {
    const contract = contractFixture()
    let ledger = createObligationLedger(contract)
    ledger = updateObligationLedgerEntry(ledger, contract, {
      obligationId: 'OBL-VALIDATE',
      status: 'SATISFIED',
      sequence: 1,
      evidence: [evidence(
        'OBL-VALIDATE',
        'AGENT_DECLARATION',
        'PASS',
        1,
      )],
    })
    const result = evaluateCompletion(contract, ledger)
    expect(result.status).toBe('IN_PROGRESS')
    expect(result.missingEvidenceObligationIds).toContain('OBL-VALIDATE')
  })

  it('blocks completion while one blocking violation remains open', () => {
    const contract = contractFixture()
    let ledger = createObligationLedger(contract)
    ledger = addViolation(ledger, {
      violationId: 'VIOLATION-001',
      code: 'OUT_OF_SCOPE_WRITE',
      severity: 'BLOCKING',
      status: 'OPEN',
      firstSequence: 1,
      lastSequence: 1,
      summary: 'A synthetic write escaped the generated scope.',
      relatedRefs: ['file://outside/scope'],
    })
    const blocked = evaluateCompletion(contract, ledger)
    expect(blocked.status).toBe('BLOCKED')
    expect(blocked.blockingViolationIds).toEqual(['VIOLATION-001'])

    ledger = addViolation(ledger, {
      violationId: 'VIOLATION-001',
      code: 'OUT_OF_SCOPE_WRITE',
      severity: 'BLOCKING',
      status: 'RESOLVED',
      firstSequence: 1,
      lastSequence: 2,
      summary: 'The out-of-scope change was reverted.',
      relatedRefs: ['file://outside/scope'],
    })
    expect(evaluateCompletion(contract, ledger).status).toBe('IN_PROGRESS')
  })

  it('rejects stale updates and unauthorized NOT_APPLICABLE transitions', () => {
    const contract = contractFixture()
    let ledger = createObligationLedger(contract)
    ledger = satisfy(ledger, contract, 'OBL-OUTPUT', 'HOST', 'PRESENT', 3)
    expect(() => updateObligationLedgerEntry(ledger, contract, {
      obligationId: 'OBL-OUTPUT',
      status: 'PENDING',
      sequence: 2,
    })).toThrow(/Stale obligation update/)
    expect(() => updateObligationLedgerEntry(ledger, contract, {
      obligationId: 'OBL-OUTPUT',
      status: 'NOT_APPLICABLE',
      sequence: 4,
    })).toThrow(/does not allow NOT_APPLICABLE/)
  })
})
