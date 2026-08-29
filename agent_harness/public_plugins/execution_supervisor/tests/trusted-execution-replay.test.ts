import { afterEach, describe, expect, it } from 'vitest'
import {
  EXECUTION_EVENT_SCHEMA,
  TASK_SUPERVISION_CONTRACT_SCHEMA,
  type AgentClaimV01,
  type ExecutionEventEnvelopeV01,
  type ExecutionEventKind,
  type JsonRecord,
  type TaskSupervisionContractV01,
} from '../src/contracts.js'
import { createFileExecutionEventStore, openFileExecutionEventStore } from '../src/event-store.js'
import {
  EXTERNAL_AGENT_EVENT_BUNDLE_SCHEMA,
  EXTERNAL_AGENT_REQUEST_MANIFEST_SCHEMA,
  EXTERNAL_AGENT_RESPONSE_MANIFEST_SCHEMA,
  ingestExternalAgentEventBundle,
  type ExternalAgentEventBundleV01,
  type ExternalAgentRequestManifestV01,
  type ExternalAgentResponseManifestV01,
} from '../src/external-agent-bridge.js'
import { hashCanonicalJson, sha256Hex } from '../src/hash.js'
import { createExecutionObligationLedger } from '../src/obligation-ledger.js'
import {
  SYNTHETIC_LIMITS,
  createSyntheticTempDirectory,
  removeSyntheticTempDirectory,
} from './fixtures/synthetic-fixtures.js'

const HASH_A = 'a'.repeat(64)
const HASH_B = 'b'.repeat(64)
const OUTPUT_HASH = 'c'.repeat(64)
const directories: string[] = []

afterEach(async () => {
  await Promise.all(directories.splice(0).map(removeSyntheticTempDirectory))
})

const contract = (): TaskSupervisionContractV01 => ({
  schema: TASK_SUPERVISION_CONTRACT_SCHEMA,
  projectId: 'project-trusted-replay',
  taskId: 'task-trusted-replay',
  agentId: 'agent-trusted-replay',
  contextHash: HASH_A,
  routeHash: HASH_B,
  projectRevision: 'revision-trusted-replay-001',
  supervisionLevel: 'AUDIT',
  obligations: [{
    id: 'OBL-VALIDATION-REPLAY',
    kind: 'VALIDATION',
    severity: 'MUST',
    sourceRefs: ['contract://trusted-replay/validation'],
    target: {
      validationId: 'validation-trusted-replay',
      targetIdentity: 'target-validation',
    },
    satisfaction: { requiredResultStatus: 'PASS' },
  }, {
    id: 'OBL-OUTPUT-REPLAY',
    kind: 'OUTPUT',
    severity: 'MUST',
    sourceRefs: ['contract://trusted-replay/output'],
    target: {
      outputContractId: 'target-output',
      resourceId: 'resource-output',
      contentHash: OUTPUT_HASH,
    },
    satisfaction: {
      requiredStructuralStatus: 'PASS',
      requiredResultStatus: 'PASS',
    },
  }, {
    id: 'OBL-CLAIMS-REPLAY',
    kind: 'CLAIM_EVIDENCE',
    severity: 'MUST',
    sourceRefs: ['contract://trusted-replay/claims'],
    target: {
      claimKinds: ['VALIDATION', 'OUTPUT'],
      targetIdentities: ['target-validation', 'target-output', 'target-unsupported'],
    },
    satisfaction: { requireEvidenceForPassClaims: true },
  }],
  evidencePolicies: [{
    id: 'EVP-VALIDATION-REPLAY',
    obligationIds: ['OBL-VALIDATION-REPLAY'],
    acceptedProviderIds: ['provider-validator'],
    acceptedProviderKinds: ['VALIDATOR'],
    acceptedResultStatuses: ['PASS'],
    requireExactContextHash: true,
    requireExactProjectRevision: true,
    requireExactTargetIdentity: true,
    maxAgeSeconds: 3_600,
  }, {
    id: 'EVP-OUTPUT-REPLAY',
    obligationIds: ['OBL-OUTPUT-REPLAY'],
    acceptedProviderIds: ['provider-output'],
    acceptedProviderKinds: ['TOOL_GATEWAY'],
    acceptedResultStatuses: ['PASS'],
    requireExactContextHash: true,
    requireExactProjectRevision: true,
    requireExactTargetIdentity: true,
    maxAgeSeconds: 3_600,
  }, {
    id: 'EVP-CLAIMS-REPLAY',
    obligationIds: ['OBL-CLAIMS-REPLAY'],
    acceptedProviderIds: ['provider-validator', 'provider-output'],
    acceptedProviderKinds: ['VALIDATOR', 'TOOL_GATEWAY'],
    acceptedResultStatuses: ['PASS'],
    requireExactContextHash: true,
    requireExactProjectRevision: true,
    requireExactTargetIdentity: true,
    maxAgeSeconds: 3_600,
  }],
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
})

const binding = () => ({
  requestId: 'request-trusted-replay',
  runtimeId: 'runtime-trusted-replay',
  turnId: 'turn-trusted-replay',
  contract: contract(),
})

const event = (
  sequence: number,
  kind: ExecutionEventKind,
  eventId: string,
  timestamp: string,
  payload: JsonRecord,
): ExecutionEventEnvelopeV01 => ({
  schema: EXECUTION_EVENT_SCHEMA,
  requestId: 'request-trusted-replay',
  runtimeId: 'runtime-trusted-replay',
  projectId: 'project-trusted-replay',
  taskId: 'task-trusted-replay',
  turnId: 'turn-trusted-replay',
  agentId: 'agent-trusted-replay',
  contextHash: HASH_A,
  sequence,
  eventId,
  timestamp,
  kind,
  payloadHash: hashCanonicalJson(payload),
  payload,
})

const bundle = (): ExternalAgentEventBundleV01 => {
  const claims: readonly AgentClaimV01[] = [{
    id: 'claim-validation',
    kind: 'VALIDATION',
    targetIdentity: 'target-validation',
    resultStatus: 'PASS',
    validationId: 'validation-trusted-replay',
    evidenceRefs: ['evidence-event-validation'],
  }, {
    id: 'claim-output',
    kind: 'OUTPUT',
    targetIdentity: 'target-output',
    resultStatus: 'PASS',
    outputContractId: 'target-output',
    evidenceRefs: ['evidence-event-output'],
  }, {
    id: 'claim-unsupported',
    kind: 'VALIDATION',
    targetIdentity: 'target-unsupported',
    resultStatus: 'PASS',
    validationId: 'validation-trusted-replay',
    evidenceRefs: ['evidence-event-validation'],
  }]
  const requestManifest: ExternalAgentRequestManifestV01 = {
    schema: EXTERNAL_AGENT_REQUEST_MANIFEST_SCHEMA,
    requestId: 'request-trusted-replay',
    runtimeId: 'runtime-trusted-replay',
    projectId: 'project-trusted-replay',
    taskId: 'task-trusted-replay',
    turnId: 'turn-trusted-replay',
    agentId: 'agent-trusted-replay',
    contextHash: HASH_A,
    contractHash: hashCanonicalJson(contract()),
    expectedHostId: 'host-declared',
    expectedProviderId: 'provider-model-declared',
    expectedModelId: 'model-declared',
    userMessage: {
      messageId: 'message-user-replay',
      content: 'Produce and validate the bounded output.',
      contentHash: sha256Hex('Produce and validate the bounded output.'),
    },
    issuedAt: '2026-08-29T01:00:00.000Z',
  }
  const userPayload = { requestManifest }
  const user = event(1, 'USER_MESSAGE', 'message-user-replay', requestManifest.issuedAt, userPayload)
  const validationPayload = {
    receipt: {
      providerId: 'provider-validator',
      providerKind: 'VALIDATOR',
      validationId: 'validation-trusted-replay',
      commandOrTestIdentity: 'test:trusted-replay',
      projectRevision: 'revision-trusted-replay-001',
      contextHash: HASH_A,
      targetIdentity: 'target-validation',
      resultStatus: 'PASS',
      artifactRefs: ['artifact://validation-log'],
      evidenceRefs: ['evidence://validation-pass'],
      claimRefs: ['claim-validation', 'claim-unsupported'],
      timestamp: '2026-08-29T01:00:01.000Z',
    },
  }
  const validation = event(2, 'VALIDATION_RESULT', 'evidence-event-validation',
    '2026-08-29T01:00:01.000Z', validationPayload)
  const outputPayload = {
    receipt: {
      providerId: 'provider-output',
      providerKind: 'TOOL_GATEWAY',
      outputContractId: 'target-output',
      resourceId: 'resource-output',
      path: 'artifacts/result.json',
      contentHash: OUTPUT_HASH,
      projectRevision: 'revision-trusted-replay-001',
      contextHash: HASH_A,
      targetIdentity: 'target-output',
      structuralValidationStatus: 'PASS',
      ruleValidationRefs: ['rule://output-structure'],
      evidenceRefs: ['evidence://output-pass'],
      claimRefs: ['claim-output'],
      timestamp: '2026-08-29T01:00:02.000Z',
    },
  }
  const output = event(3, 'OUTPUT_EMITTED', 'evidence-event-output',
    '2026-08-29T01:00:02.000Z', outputPayload)
  const responseManifest: ExternalAgentResponseManifestV01 = {
    schema: EXTERNAL_AGENT_RESPONSE_MANIFEST_SCHEMA,
    requestManifestHash: hashCanonicalJson(requestManifest),
    requestId: 'request-trusted-replay',
    runtimeId: 'runtime-trusted-replay',
    projectId: 'project-trusted-replay',
    taskId: 'task-trusted-replay',
    turnId: 'turn-trusted-replay',
    agentId: 'agent-trusted-replay',
    contextHash: HASH_A,
    responseId: 'response-trusted-replay',
    actualHostId: 'host-declared',
    actualProviderId: 'provider-model-declared',
    actualModelId: 'model-declared',
    actualAgentId: 'agent-trusted-replay',
    assistantMessage: {
      messageId: 'message-assistant-replay',
      content: 'The output and validation report PASS.',
      contentHash: sha256Hex('The output and validation report PASS.'),
    },
    claims,
    receiptRefs: [validation, output].map(item => ({
      eventId: item.eventId,
      payloadHash: item.payloadHash,
    })),
    completedAt: '2026-08-29T01:00:03.000Z',
  }
  const assistantPayload = { responseManifest }
  const assistant = event(4, 'ASSISTANT_MESSAGE', 'message-assistant-replay',
    responseManifest.completedAt, assistantPayload)
  return {
    schema: EXTERNAL_AGENT_EVENT_BUNDLE_SCHEMA,
    bundleId: 'bundle-trusted-replay',
    requestManifestHash: hashCanonicalJson(requestManifest),
    responseManifestHash: hashCanonicalJson(responseManifest),
    events: [user, validation, output, assistant],
  }
}

describe('Phase 3+4 trusted execution replay', () => {
  it('reconstructs Bridge manifests, Evidence, claims, violations and completion without duplicate effects', async () => {
    const directory = await createSyntheticTempDirectory('trusted-execution-replay-')
    directories.push(directory)
    const input = bundle()
    const firstStore = await createFileExecutionEventStore({
      directory,
      binding: binding(),
      limits: SYNTHETIC_LIMITS,
    })
    const firstLedger = await createExecutionObligationLedger({ eventStore: firstStore })

    const ingestion = await ingestExternalAgentEventBundle(firstLedger, input)
    expect(ingestion.acceptances.map(item => item.status)).toEqual([
      'ACCEPTED', 'ACCEPTED', 'ACCEPTED', 'ACCEPTED',
    ])
    await firstLedger.ingest(event(5, 'TASK_END_REQUEST', 'task-end-replay',
      '2026-08-29T01:00:04.000Z', { requestedBy: 'agent-trusted-replay' }))

    const uninterruptedStatus = firstLedger.getStatus()
    const uninterruptedDecision = firstLedger.getCompletionDecision()
    expect(uninterruptedStatus).toMatchObject({
      cursor: { sequence: 5 },
      satisfiedObligationIds: ['OBL-VALIDATION-REPLAY', 'OBL-OUTPUT-REPLAY'],
      violatedObligationIds: ['OBL-CLAIMS-REPLAY'],
    })
    expect(uninterruptedStatus.violations).toEqual([
      expect.objectContaining({
        code: 'UNSUPPORTED_PASS_CLAIM',
        claimId: 'claim-unsupported',
        obligationId: 'OBL-CLAIMS-REPLAY',
      }),
    ])
    expect(uninterruptedDecision).toMatchObject({
      status: 'BLOCKED',
      pendingObligationIds: [],
      violatedObligationIds: ['OBL-CLAIMS-REPLAY'],
    })
    await firstStore.close()

    const reopenedStore = await openFileExecutionEventStore({ directory, binding: binding() })
    const replayedLedger = await createExecutionObligationLedger({ eventStore: reopenedStore })
    await replayedLedger.synchronize()

    expect(replayedLedger.getStatus()).toEqual(uninterruptedStatus)
    expect(replayedLedger.getCompletionDecision()).toEqual(uninterruptedDecision)
    const replay = await reopenedStore.replay({ limit: 10 })
    expect(replay.events[0]?.payload).toEqual(input.events[0]?.payload)
    expect(replay.events[3]?.payload).toEqual(input.events[3]?.payload)

    const violationCount = replayedLedger.getStatus().violations.length
    const evidenceRefs = replayedLedger.getCompletionDecision().evidenceRefs
    await replayedLedger.synchronize()
    await replayedLedger.synchronize()
    expect(replayedLedger.getStatus()).toEqual(uninterruptedStatus)
    expect(replayedLedger.getStatus().violations).toHaveLength(violationCount)
    expect(replayedLedger.getCompletionDecision().evidenceRefs).toEqual(evidenceRefs)
    await reopenedStore.close()
  })
})
