import { describe, expect, it } from 'vitest'
import type {
  EvidencePolicyV01,
  TaskSupervisionContractV01,
  ValidationReceiptV01,
} from '../src/contracts.js'
import { TASK_SUPERVISION_CONTRACT_SCHEMA } from '../src/contracts.js'
import { evaluateTrustedEvidence } from '../src/trusted-evaluation.js'

const HASH_A = 'a'.repeat(64)
const TARGET_IDENTITY = 'validation-target'
const PROJECT_REVISION = 'revision-current'
const EVALUATION_AT = '2026-08-29T01:01:00.000Z'

const policy = (
  overrides: Partial<EvidencePolicyV01> = {},
): EvidencePolicyV01 => ({
  id: 'POLICY-VALIDATION',
  obligationIds: ['OBL-VALIDATION'],
  acceptedProviderIds: ['provider-trusted'],
  acceptedProviderKinds: ['VALIDATOR'],
  acceptedResultStatuses: ['PASS'],
  requireExactContextHash: true,
  requireExactProjectRevision: true,
  requireExactTargetIdentity: true,
  maxAgeSeconds: 60,
  ...overrides,
})

const contract = (
  policyOverride: EvidencePolicyV01 = policy(),
  overrides: Partial<TaskSupervisionContractV01> = {},
): TaskSupervisionContractV01 => ({
  schema: TASK_SUPERVISION_CONTRACT_SCHEMA,
  projectId: 'project-synthetic',
  taskId: 'task-synthetic',
  agentId: 'agent-synthetic',
  contextHash: HASH_A,
  routeHash: 'b'.repeat(64),
  projectRevision: PROJECT_REVISION,
  supervisionLevel: 'AUDIT',
  obligations: [{
    id: 'OBL-VALIDATION',
    kind: 'VALIDATION',
    severity: 'MUST',
    sourceRefs: [],
    target: {
      validationId: 'validation-primary',
      targetIdentity: TARGET_IDENTITY,
    },
    satisfaction: { requiredResultStatus: 'PASS' },
  }],
  evidencePolicies: [policyOverride],
  completionPolicy: {
    requireAllMustSatisfied: true,
    requireNoViolations: true,
    requireReflection: false,
    requireKnowledgeDecision: false,
    requireContextUpdate: false,
    requireClosureReceipt: false,
    allowShouldWarnings: true,
    requiredClosureModuleIds: [],
  },
  ...overrides,
})

const receipt = (
  overrides: Partial<ValidationReceiptV01> = {},
): ValidationReceiptV01 => ({
  providerId: 'provider-trusted',
  providerKind: 'VALIDATOR',
  validationId: 'validation-primary',
  commandOrTestIdentity: 'npm-test-validation-primary',
  projectRevision: PROJECT_REVISION,
  contextHash: HASH_A,
  targetIdentity: TARGET_IDENTITY,
  resultStatus: 'PASS',
  artifactRefs: [],
  evidenceRefs: ['evidence://validation-primary'],
  claimRefs: [],
  timestamp: '2026-08-29T01:00:00.000Z',
  ...overrides,
})

const evaluate = (
  activePolicy = policy(),
  activeContract = contract(activePolicy),
  activeReceipt = receipt(),
) => evaluateTrustedEvidence({
  policy: activePolicy,
  contract: activeContract,
  providerId: activeReceipt.providerId,
  providerKind: activeReceipt.providerKind,
  resultStatus: activeReceipt.resultStatus,
  contextHash: activeReceipt.contextHash,
  ...(activeReceipt.projectRevision === undefined
    ? {}
    : { projectRevision: activeReceipt.projectRevision }),
  targetIdentity: activeReceipt.targetIdentity,
  timestamp: activeReceipt.timestamp,
  evaluationAt: EVALUATION_AT,
  requiredResultStatus: 'PASS',
})

describe('Phase 4 deterministic Evidence Policy evaluation', () => {
  it('accepts current PASS only when both declared provider ID and kind match', () => {
    expect(evaluate()).toEqual({
      accepted: true,
      satisfying: true,
      trustedFailure: false,
      reasons: [],
    })

    expect(evaluate(policy(), contract(), receipt({ providerKind: 'CI' })))
      .toMatchObject({
        accepted: false,
        satisfying: false,
        reasons: ['PROVIDER_KIND_NOT_ACCEPTED'],
      })
    expect(evaluate(policy(), contract(), receipt({ providerId: 'provider-other' })))
      .toMatchObject({
        accepted: false,
        satisfying: false,
        reasons: ['PROVIDER_ID_NOT_ACCEPTED'],
      })
  })

  it('requires exact Context, project revision and obligation target identity', () => {
    expect(evaluate(policy(), contract(), receipt({ contextHash: 'b'.repeat(64) })))
      .toMatchObject({ accepted: false, reasons: ['CONTEXT_HASH_MISMATCH'] })
    expect(evaluate(policy(), contract(), receipt({ projectRevision: 'revision-old' })))
      .toMatchObject({ accepted: false, reasons: ['PROJECT_REVISION_MISMATCH'] })
    expect(evaluate(policy(), contract(), receipt({ targetIdentity: 'target-other' })))
      .toMatchObject({ accepted: false, reasons: ['TARGET_IDENTITY_MISMATCH'] })

    const withoutRevision = contract(policy(), { projectRevision: undefined })
    expect(evaluate(policy(), withoutRevision, receipt({ projectRevision: undefined })))
      .toMatchObject({ accepted: false, reasons: ['PROJECT_REVISION_UNAVAILABLE'] })
  })

  it('uses the explicit evaluation time and accepts the exact max-age boundary', () => {
    expect(evaluate()).toMatchObject({ accepted: true, satisfying: true })

    expect(evaluate(
      policy(),
      contract(),
      receipt({ timestamp: '2026-08-29T00:59:59.999Z' }),
    )).toMatchObject({ accepted: false, reasons: ['EVIDENCE_STALE'] })

    expect(evaluate(
      policy(),
      contract(),
      receipt({ timestamp: '2026-08-29T01:01:00.001Z' }),
    )).toMatchObject({ accepted: false, reasons: ['EVIDENCE_FROM_FUTURE'] })
  })

  it('fails closed for invalid receipt or evaluation timestamps', () => {
    expect(evaluate(policy(), contract(), receipt({ timestamp: 'not-a-timestamp' })))
      .toMatchObject({ accepted: false, reasons: ['INVALID_RECEIPT_TIMESTAMP'] })

    const activePolicy = policy()
    const activeContract = contract(activePolicy)
    const activeReceipt = receipt()
    expect(evaluateTrustedEvidence({
      policy: activePolicy,
      contract: activeContract,
      providerId: activeReceipt.providerId,
      providerKind: activeReceipt.providerKind,
      resultStatus: activeReceipt.resultStatus,
      contextHash: activeReceipt.contextHash,
      projectRevision: activeReceipt.projectRevision,
      targetIdentity: activeReceipt.targetIdentity,
      timestamp: activeReceipt.timestamp,
      evaluationAt: 'invalid',
      requiredResultStatus: 'PASS',
    })).toMatchObject({
      accepted: false,
      satisfying: false,
      reasons: ['INVALID_EVALUATION_TIMESTAMP'],
    })
  })

  it.each(['NOT_EXECUTED', 'NOT_VERIFIED', 'HISTORICAL'] as const)(
    'keeps accepted %s Evidence honest but never satisfying for required PASS',
    resultStatus => {
      const activePolicy = policy({
        acceptedResultStatuses: [resultStatus],
      })
      expect(evaluate(
        activePolicy,
        contract(activePolicy),
        receipt({ resultStatus }),
      )).toEqual({
        accepted: true,
        satisfying: false,
        trustedFailure: false,
        reasons: ['REQUIRED_RESULT_STATUS_MISMATCH'],
      })
    },
  )

  it('identifies an accepted FAIL as trusted failure without satisfying PASS', () => {
    const activePolicy = policy({ acceptedResultStatuses: ['FAIL'] })
    expect(evaluate(
      activePolicy,
      contract(activePolicy),
      receipt({ resultStatus: 'FAIL' }),
    )).toEqual({
      accepted: true,
      satisfying: false,
      trustedFailure: true,
      reasons: ['REQUIRED_RESULT_STATUS_MISMATCH'],
    })
  })
})
