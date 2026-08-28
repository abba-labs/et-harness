import { createHash } from 'node:crypto'
import {
  EXECUTION_EVENT_SCHEMA,
  EXECUTION_SUPERVISOR_CONTRACT_VERSION,
  TASK_SUPERVISION_CONTRACT_SCHEMA,
  type ExecutionEventV01,
  type TaskSupervisionContractV01,
} from '../src/contracts.js'
import {
  computeExecutionEventHash,
  computeTaskSupervisionContractHash,
} from '../src/canonical-json.js'

const sha256Text = (value: string): string =>
  createHash('sha256').update(value).digest('hex')

export const FIXED_TIME = '2026-08-28T00:00:00.000Z'

export const contractFixture = (): TaskSupervisionContractV01 => {
  const rawTask = 'Analyze the selected subsystem and produce governed artifacts.'
  return {
    schema: TASK_SUPERVISION_CONTRACT_SCHEMA,
    contractVersion: EXECUTION_SUPERVISOR_CONTRACT_VERSION,
    contractId: 'CONTRACT-001',
    mode: 'ENFORCE',
    identity: {
      runtimeId: 'RUNTIME-001',
      taskId: 'TASK-001',
      turnId: 'TURN-001',
      agentId: 'AGENT-001',
      projectId: 'PROJECT-001',
    },
    rawTask,
    rawTaskHash: sha256Text(rawTask),
    contextHash: 'a'.repeat(64),
    routeHash: 'b'.repeat(64),
    taskContextHash: 'c'.repeat(64),
    scope: {
      readAllowed: ['src/**', 'docs/**'],
      writeAllowed: ['docs/output/**'],
      writeProtected: ['src/**'],
      externalSourceAllowed: ['source://project/PROJECT-001/**'],
    },
    obligations: [
      {
        obligationId: 'OBL-RESOURCE-001',
        kind: 'RESOURCE_ACCESS',
        level: 'MUST',
        title: 'Read the governed source set',
        rationale: 'The result must be grounded in project-owned sources.',
        risk: 'HIGH',
        evaluator: {
          kind: 'EVENT_MATCH',
          eventKinds: ['RESOURCE_READ'],
          minimumCount: 1,
        },
        provenanceRefs: ['rule://R001'],
        dependsOn: [],
      },
      {
        obligationId: 'OBL-REFLECTION-001',
        kind: 'REFLECTION',
        level: 'MUST',
        title: 'Complete unified Reflection',
        rationale: 'The Framework must force one bounded semantic reflection.',
        risk: 'HIGH',
        evaluator: {
          kind: 'LIFECYCLE_STATE',
          requiredState: 'REFLECTION_COMPLETE',
        },
        provenanceRefs: ['rule://R002'],
        dependsOn: ['OBL-RESOURCE-001'],
      },
      {
        obligationId: 'OBL-KNOWLEDGE-001',
        kind: 'KNOWLEDGE_CLASSIFICATION',
        level: 'MUST',
        title: 'Classify durable knowledge',
        rationale: 'Knowledge must explicitly choose NONE, PROJECT, PUBLIC or BOTH.',
        risk: 'MEDIUM',
        evaluator: {
          kind: 'LIFECYCLE_STATE',
          requiredState: 'KNOWLEDGE_DECISION_COMPLETE',
        },
        provenanceRefs: ['rule://R003'],
        dependsOn: ['OBL-REFLECTION-001'],
      },
      {
        obligationId: 'OBL-CONTEXT-001',
        kind: 'CONTEXT_RECONCILIATION',
        level: 'MUST',
        title: 'Reconcile task context',
        rationale: 'Confirmed facts, open issues and working set must be persisted.',
        risk: 'MEDIUM',
        evaluator: {
          kind: 'LIFECYCLE_STATE',
          requiredState: 'CONTEXT_RECONCILED',
        },
        provenanceRefs: ['rule://R004'],
        dependsOn: ['OBL-REFLECTION-001'],
      },
      {
        obligationId: 'OBL-CLOSURE-001',
        kind: 'CLOSURE',
        level: 'MUST',
        title: 'Complete mandatory Closure',
        rationale: 'The Turn cannot close until all mandatory modules emit receipts.',
        risk: 'CRITICAL',
        evaluator: {
          kind: 'LIFECYCLE_STATE',
          requiredState: 'TURN_CLOSED',
        },
        provenanceRefs: ['rule://R005'],
        dependsOn: [
          'OBL-REFLECTION-001',
          'OBL-KNOWLEDGE-001',
          'OBL-CONTEXT-001',
        ],
      },
    ],
    claimPolicies: [{
      claimPattern: 'validation:*',
      allowedStates: ['PASS', 'FAIL', 'NOT_EXECUTED', 'NOT_VERIFIED'],
      evidenceRequiredFor: ['PASS'],
      trustedEvidenceProducerIds: ['validator://PROJECT-001/default'],
    }],
    completionPolicy: {
      requireAllMustObligations: true,
      blockOnOpenErrorOrFatalViolation: true,
      reflectionRequired: true,
      knowledgeDecisionRequired: true,
      contextReconciliationRequired: true,
      closureRequired: true,
    },
    provenanceRefs: ['context://PROJECT-001/TASK-001'],
    createdAt: FIXED_TIME,
  }
}

export const eventFixture = (
  sequence = 1,
  previousEventHash?: string,
): ExecutionEventV01 => {
  const contract = contractFixture()
  const base: ExecutionEventV01 = {
    schema: EXECUTION_EVENT_SCHEMA,
    contractVersion: EXECUTION_SUPERVISOR_CONTRACT_VERSION,
    eventId: `EVENT-${String(sequence).padStart(3, '0')}`,
    sequence,
    occurredAt: FIXED_TIME,
    identity: contract.identity,
    kind: sequence === 1 ? 'TASK_HANDOFF' : 'RESOURCE_READ',
    source: {
      hostAdapterId: 'HOST-ADAPTER-001',
      hostSessionId: 'HOST-SESSION-001',
      transportId: 'TRANSPORT-001',
    },
    correlation: {
      requestId: 'REQUEST-001',
      idempotencyKey: `IDEMPOTENCY-${String(sequence).padStart(3, '0')}`,
    },
    payload: {
      summary: sequence === 1
        ? 'The governed task was handed to the external Agent.'
        : 'The Agent read one authorized project resource.',
      outcome: 'SUCCEEDED',
      refs: sequence === 1 ? ['request://REQUEST-001'] : ['source://project/PROJECT-001/source-1'],
      ...(sequence === 1 ? {} : {
        resource: {
          kind: 'FILE' as const,
          action: 'READ' as const,
          locator: 'src/module.ts',
          stableId: 'blob-001',
          revision: 'revision-001',
          contentHash: 'd'.repeat(64),
        },
      }),
    },
    integrity: {
      contractHash: computeTaskSupervisionContractHash(contract),
      ...(previousEventHash ? { previousEventHash } : {}),
      eventHash: '',
    },
  }
  return {
    ...base,
    integrity: {
      ...base.integrity,
      eventHash: computeExecutionEventHash(base),
    },
  }
}
