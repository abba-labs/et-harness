import { describe, expect, it } from 'vitest'
import {
  EXECUTION_SUPERVISOR_CONTRACT_VERSION,
  PROJECT_SUPERVISION_CONTRIBUTION_SCHEMA,
  PUBLIC_LIFECYCLE_OBLIGATION_IDS,
  buildTaskSupervisionContract,
  validateTaskSupervisionContract,
} from '../src/index.js'
import {
  authorizedSourceRefs,
  buildInputFixture,
  contributionFixture,
} from './contract-builder-fixtures.js'

describe('Execution Supervisor Phase 1 Task Supervision Contract builder', () => {
  it('compiles project obligations plus mandatory public lifecycle obligations', () => {
    const result = buildTaskSupervisionContract(buildInputFixture())
    expect(validateTaskSupervisionContract(result.contract)).toEqual({
      valid: true,
      issues: [],
    })
    expect(result.contract.mode).toBe('AUDIT')
    expect(result.contract.obligations.map(item => item.obligationId)).toEqual(
      expect.arrayContaining([
        'PROJECT.READ.REQUIRED-SPEC',
        'PROJECT.OUTPUT.REQUIRED',
        'PROJECT.VALIDATION.REQUIRED',
        PUBLIC_LIFECYCLE_OBLIGATION_IDS.reflection,
        PUBLIC_LIFECYCLE_OBLIGATION_IDS.knowledgeClassification,
        PUBLIC_LIFECYCLE_OBLIGATION_IDS.contextClosure,
        PUBLIC_LIFECYCLE_OBLIGATION_IDS.knowledgeClosure,
        PUBLIC_LIFECYCLE_OBLIGATION_IDS.turnClosure,
      ]),
    )
    expect(result.receipt.projectObligationCount).toBe(3)
    expect(result.receipt.publicLifecycleObligationCount).toBe(5)
    expect(result.receipt.totalObligationCount).toBe(8)
    expect(result.receipt.contributions).toEqual([
      expect.objectContaining({
        contributionId: 'synthetic-project-obligations',
        provenance: 'provider://synthetic-project/context',
        obligationCount: 3,
      }),
    ])
    expect(result.receipt.hostId).toBe('generic-external-chat-host')
    expect(result.receipt.adapterId).toBe('generic-external-chat-adapter')
    expect(result.receipt.contractHash).toBe(result.contract.contractHash)
    expect(result.receipt.receiptHash).toMatch(/^[0-9a-f]{64}$/)
  })

  it('is deterministic across contribution and authorized-reference ordering', () => {
    const first = buildInputFixture()
    const second = {
      ...first,
      authorizedSourceRefs: [...first.authorizedSourceRefs].reverse(),
      projectContributions: [
        {
          ...first.projectContributions[0]!,
          obligations: [...first.projectContributions[0]!.obligations].reverse(),
        },
      ],
    }
    const left = buildTaskSupervisionContract(first)
    const right = buildTaskSupervisionContract(second)
    expect(right.contract).toEqual(left.contract)
    expect(right.receipt).toEqual(left.receipt)
  })

  it('rejects project and task identity mismatches', () => {
    const input = buildInputFixture()
    expect(() => buildTaskSupervisionContract({
      ...input,
      projectContributions: [{
        ...input.projectContributions[0]!,
        projectId: 'another-project',
      }],
    })).toThrow(/project mismatch/)
    expect(() => buildTaskSupervisionContract({
      ...input,
      projectContributions: [{
        ...input.projectContributions[0]!,
        taskId: 'ANOTHER-TASK',
      }],
    })).toThrow(/task mismatch/)
  })

  it('rejects obligations not grounded in automatically authorized sources', () => {
    const input = buildInputFixture()
    expect(() => buildTaskSupervisionContract({
      ...input,
      projectContributions: [{
        ...input.projectContributions[0]!,
        obligations: [{
          ...input.projectContributions[0]!.obligations[0]!,
          sourceRefs: ['rule:R-MANUALLY-INJECTED'],
        }],
      }],
    })).toThrow(/unauthorized source/)
  })

  it('never silently upgrades an audit-only Host to ENFORCE', () => {
    const input = buildInputFixture()
    expect(() => buildTaskSupervisionContract({
      ...input,
      requestedMode: 'ENFORCE',
    })).toThrow(/pre-execution action guarding/)

    const enforced = buildTaskSupervisionContract({
      ...input,
      requestedMode: 'ENFORCE',
      hostCapabilities: {
        ...input.hostCapabilities,
        preExecutionActionGuard: true,
        mechanicalToolInterception: true,
      },
    })
    expect(enforced.contract.mode).toBe('ENFORCE')
  })

  it('rejects a Host that cannot return any execution event stream', () => {
    const input = buildInputFixture()
    expect(() => buildTaskSupervisionContract({
      ...input,
      hostCapabilities: {
        ...input.hostCapabilities,
        executionEventStream: false,
      },
    })).toThrow(/execution event stream/)
  })

  it('prevents project contributions from overriding public lifecycle control', () => {
    const input = buildInputFixture()
    expect(() => buildTaskSupervisionContract({
      ...input,
      projectContributions: [{
        ...input.projectContributions[0]!,
        obligations: [{
          ...input.projectContributions[0]!.obligations[0]!,
          obligationId: PUBLIC_LIFECYCLE_OBLIGATION_IDS.turnClosure,
        }],
      }],
    })).toThrow(/cannot override public lifecycle obligation/)
  })

  it('adds follow-up reuse only when a project contribution requires it', () => {
    const input = buildInputFixture()
    const ordinary = buildTaskSupervisionContract(input)
    expect(ordinary.contract.completionPolicy.requireFollowUpReuse).toBe(false)
    expect(ordinary.contract.obligations.some(item =>
      item.obligationId === PUBLIC_LIFECYCLE_OBLIGATION_IDS.followUpReuse,
    )).toBe(false)

    const withReuse = buildTaskSupervisionContract({
      ...input,
      projectContributions: [{
        ...input.projectContributions[0]!,
        requireFollowUpReuse: true,
      }],
    })
    expect(withReuse.contract.completionPolicy.requireFollowUpReuse).toBe(true)
    expect(withReuse.contract.obligations.some(item =>
      item.obligationId === PUBLIC_LIFECYCLE_OBLIGATION_IDS.followUpReuse,
    )).toBe(true)
  })

  it('remains project- and Host-neutral', () => {
    const result = buildTaskSupervisionContract(buildInputFixture())
    const serialized = JSON.stringify(result)
    expect(serialized).not.toMatch(/etimer|ET6801|automated-testing-platform/i)
    expect(PROJECT_SUPERVISION_CONTRIBUTION_SCHEMA).toContain('project-supervision')
    expect(EXECUTION_SUPERVISOR_CONTRACT_VERSION).toBe('0.1')
    expect(authorizedSourceRefs.length).toBeGreaterThan(0)
    expect(contributionFixture().projectId).toBe('synthetic-project')
  })
})
