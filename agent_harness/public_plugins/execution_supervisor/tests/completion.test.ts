import { describe, expect, it } from 'vitest'
import {
  type AgentClaimV01,
  type ExecutionEventKind,
  type JsonRecord,
  createExecutionObligationLedger,
  createFileExecutionEventStore,
  hashCanonicalJson,
  sha256Hex,
  type EvidenceResultStatus,
  type ExecutionObligationLedgerV01,
  type TaskSupervisionContractV01,
} from '../src/index.js'
import {
  EXTERNAL_AGENT_EVENT_BUNDLE_SCHEMA,
  EXTERNAL_AGENT_REQUEST_MANIFEST_SCHEMA,
  EXTERNAL_AGENT_RESPONSE_MANIFEST_SCHEMA,
  ingestExternalAgentEventBundle,
  type ExternalAgentEventBundleV01,
  type ExternalAgentRequestManifestV01,
  type ExternalAgentResponseManifestV01,
} from '../src/external-agent-bridge.js'
import {
  HASH_A,
  SYNTHETIC_LIMITS,
  createSyntheticTempDirectory,
  removeSyntheticTempDirectory,
  syntheticBinding,
  syntheticContract,
  syntheticEvent,
} from './fixtures/synthetic-fixtures.js'

const validationContract = (): TaskSupervisionContractV01 => syntheticContract({
  obligations: [{
    id: 'OBL-VALIDATE-001',
    kind: 'VALIDATION',
    severity: 'MUST',
    sourceRefs: [],
    target: {
      validationId: 'validation-primary',
      targetIdentity: 'target-primary',
    },
    satisfaction: { requiredResultStatus: 'PASS' },
  }],
  evidencePolicies: [{
    id: 'EVP-VALIDATE-001',
    obligationIds: ['OBL-VALIDATE-001'],
    acceptedProviderIds: ['validator-primary'],
    acceptedProviderKinds: ['VALIDATOR'],
    acceptedResultStatuses: ['PASS', 'FAIL', 'NOT_EXECUTED'],
    requireExactContextHash: true,
    requireExactProjectRevision: true,
    requireExactTargetIdentity: true,
    maxAgeSeconds: 3_600,
  }],
})

const withLedger = async (
  contract: TaskSupervisionContractV01,
  run: (ledger: ExecutionObligationLedgerV01) => Promise<void>,
): Promise<void> => {
  const directory = await createSyntheticTempDirectory('phase34-completion-')
  const store = await createFileExecutionEventStore({
    directory,
    binding: syntheticBinding({ contract }),
    limits: SYNTHETIC_LIMITS,
  })
  try {
    const ledger = await createExecutionObligationLedger({ eventStore: store })
    await run(ledger)
  } finally {
    await store.close()
    await removeSyntheticTempDirectory(directory)
  }
}

const validationPayload = (resultStatus: EvidenceResultStatus) => ({
  receipt: {
    providerId: 'validator-primary',
    providerKind: 'VALIDATOR',
    validationId: 'validation-primary',
    commandOrTestIdentity: 'test:primary',
    projectRevision: 'revision-synthetic-001',
    contextHash: HASH_A,
    targetIdentity: 'target-primary',
    resultStatus,
    artifactRefs: [],
    evidenceRefs: [`evidence://${resultStatus.toLowerCase()}`],
    claimRefs: [],
    timestamp: '2026-08-29T00:00:01.000Z',
  },
})

const ingestTrustedSpan = async (
  ledger: ExecutionObligationLedgerV01,
  contract: TaskSupervisionContractV01,
  middle: readonly { kind: ExecutionEventKind; payload: JsonRecord }[],
  claims: readonly AgentClaimV01[] = [],
): Promise<number> => {
  const userContent = 'Evaluate the bounded completion fixture.'
  const assistantContent = 'The bounded completion fixture was evaluated.'
  const requestManifest: ExternalAgentRequestManifestV01 = {
    schema: EXTERNAL_AGENT_REQUEST_MANIFEST_SCHEMA,
    requestId: 'request-synthetic',
    runtimeId: 'runtime-synthetic',
    projectId: 'project-synthetic',
    taskId: 'task-synthetic',
    turnId: 'turn-synthetic',
    agentId: 'agent-synthetic',
    contextHash: HASH_A,
    contractHash: hashCanonicalJson(contract),
    expectedHostId: 'host-completion',
    expectedProviderId: 'provider-model-completion',
    expectedModelId: 'model-completion',
    userMessage: {
      messageId: 'message-user-completion',
      content: userContent,
      contentHash: sha256Hex(userContent),
    },
    issuedAt: '2026-08-29T00:00:00.000Z',
  }
  const userEvent = syntheticEvent(1, {
    kind: 'USER_MESSAGE',
    eventId: requestManifest.userMessage.messageId,
    timestamp: requestManifest.issuedAt,
    payload: { requestManifest },
  })
  const middleEvents = middle.map((item, index) => syntheticEvent(index + 2, {
    kind: item.kind,
    eventId: `completion-receipt-${index + 1}`,
    timestamp: new Date(Date.UTC(2026, 7, 29, 0, 0, index + 1)).toISOString(),
    payload: item.payload,
  }))
  const responseManifest: ExternalAgentResponseManifestV01 = {
    schema: EXTERNAL_AGENT_RESPONSE_MANIFEST_SCHEMA,
    requestManifestHash: hashCanonicalJson(requestManifest),
    requestId: 'request-synthetic',
    runtimeId: 'runtime-synthetic',
    projectId: 'project-synthetic',
    taskId: 'task-synthetic',
    turnId: 'turn-synthetic',
    agentId: 'agent-synthetic',
    contextHash: HASH_A,
    responseId: 'response-completion',
    actualHostId: 'host-completion',
    actualProviderId: 'provider-model-completion',
    actualModelId: 'model-completion',
    actualAgentId: 'agent-synthetic',
    assistantMessage: {
      messageId: 'message-assistant-completion',
      content: assistantContent,
      contentHash: sha256Hex(assistantContent),
    },
    claims,
    receiptRefs: middleEvents.map(item => ({
      eventId: item.eventId,
      payloadHash: item.payloadHash,
    })),
    completedAt: new Date(Date.UTC(2026, 7, 29, 0, 0, middleEvents.length + 1)).toISOString(),
  }
  const assistantEvent = syntheticEvent(middleEvents.length + 2, {
    kind: 'ASSISTANT_MESSAGE',
    eventId: responseManifest.assistantMessage.messageId,
    timestamp: responseManifest.completedAt,
    payload: { responseManifest },
  })
  const bundle: ExternalAgentEventBundleV01 = {
    schema: EXTERNAL_AGENT_EVENT_BUNDLE_SCHEMA,
    bundleId: 'bundle-completion',
    requestManifestHash: hashCanonicalJson(requestManifest),
    responseManifestHash: hashCanonicalJson(responseManifest),
    events: [userEvent, ...middleEvents, assistantEvent],
  }
  const result = await ingestExternalAgentEventBundle(ledger, bundle)
  expect(result.failure).toBeUndefined()
  return bundle.events.length + 1
}

describe('Phase 3+4 pre-Closure completion evaluation', () => {
  it('keeps honest NOT_EXECUTED pending and blocks a task-end request', async () => {
    await withLedger(validationContract(), async ledger => {
      expect(ledger.getCompletionDecision().status).toBe('IN_PROGRESS')
      const nextSequence = await ingestTrustedSpan(
        ledger,
        validationContract(),
        [{ kind: 'VALIDATION_RESULT', payload: validationPayload('NOT_EXECUTED') }],
      )
      await ledger.ingest(syntheticEvent(nextSequence, {
        kind: 'TASK_END_REQUEST',
        payload: { requestedBy: 'agent-synthetic' },
      }))

      expect(ledger.getStatus().pendingObligationIds).toEqual(['OBL-VALIDATE-001'])
      expect(ledger.getCompletionDecision()).toMatchObject({
        status: 'BLOCKED',
        pendingObligationIds: ['OBL-VALIDATE-001'],
        violatedObligationIds: [],
      })
    })
  })

  it('re-evaluates stale Evidence at task end and re-blocks its dependent', async () => {
    const base = validationContract()
    const contract = syntheticContract({
      obligations: [base.obligations[0]!, {
        id: 'OBL-SCOPE-DEPENDENT',
        kind: 'WRITE_SCOPE',
        severity: 'MUST',
        sourceRefs: [],
        target: {
          allowedResourceIds: ['resource-allowed'],
          allowedPathPrefixes: [],
        },
        satisfaction: { requireInScope: true },
        dependencies: ['OBL-VALIDATE-001'],
      }],
      evidencePolicies: [{
        ...base.evidencePolicies[0]!,
        maxAgeSeconds: 1,
      }],
    })
    await withLedger(contract, async ledger => {
      const nextSequence = await ingestTrustedSpan(
        ledger,
        contract,
        [{ kind: 'VALIDATION_RESULT', payload: validationPayload('PASS') }],
      )
      expect(ledger.getStatus().satisfiedObligationIds).toContain('OBL-VALIDATE-001')
      expect(ledger.getStatus().pendingObligationIds).toContain('OBL-SCOPE-DEPENDENT')

      await ledger.ingest(syntheticEvent(nextSequence, {
        timestamp: '2026-08-29T00:00:03.000Z',
        kind: 'TASK_END_REQUEST',
        payload: { requestedBy: 'agent-synthetic' },
      }))

      expect(ledger.getStatus().pendingObligationIds).toContain('OBL-VALIDATE-001')
      expect(ledger.getStatus().blockedObligationIds).toContain('OBL-SCOPE-DEPENDENT')
      expect(ledger.getCompletionDecision().status).toBe('BLOCKED')
    })
  })

  it('keeps REQUIRED_RESOURCE pending when a separate disposition is satisfied', async () => {
    const contract = syntheticContract({
      obligations: [{
        id: 'OBL-READ-001',
        kind: 'REQUIRED_RESOURCE',
        severity: 'MUST',
        sourceRefs: [],
        target: { resourceId: 'resource-missing' },
        satisfaction: {
          acceptedProviderIds: ['repository-provider'],
          acceptedDispositions: ['FOUND'],
        },
      }, {
        id: 'OBL-DISPOSITION-001',
        kind: 'SOURCE_DISPOSITION',
        severity: 'MUST',
        sourceRefs: [],
        target: { resourceId: 'resource-missing' },
        satisfaction: {
          acceptedProviderIds: ['repository-provider'],
          acceptedDispositions: ['UNAVAILABLE'],
        },
      }],
    })
    await withLedger(contract, async ledger => {
      await ledger.ingest(syntheticEvent(1, {
        kind: 'RESOURCE_READ',
        payload: {
          receipt: {
            provider: 'repository-provider',
            resourceId: 'resource-missing',
            disposition: 'UNAVAILABLE',
            purpose: 'Record the unavailable required source.',
            claimRefs: [],
            error: 'not available',
          },
        },
      }))
      await ledger.ingest(syntheticEvent(2, {
        kind: 'TASK_END_REQUEST',
        payload: { requestedBy: 'agent-synthetic' },
      }))

      expect(ledger.getStatus().satisfiedObligationIds).toEqual(['OBL-DISPOSITION-001'])
      expect(ledger.getStatus().pendingObligationIds).toEqual(['OBL-READ-001'])
      expect(ledger.getCompletionDecision().status).toBe('BLOCKED')
    })
  })

  it.each([
    ['PASS', 'READY_TO_CLOSE'],
    ['FAIL', 'FAILED'],
  ] as const)('maps trusted %s Evidence to %s without producing COMPLETE', async (
    resultStatus,
    expectedStatus,
  ) => {
    await withLedger(validationContract(), async ledger => {
      const currentContract = validationContract()
      const nextSequence = await ingestTrustedSpan(
        ledger,
        currentContract,
        [{ kind: 'VALIDATION_RESULT', payload: validationPayload(resultStatus) }],
      )
      await ledger.ingest(syntheticEvent(nextSequence, {
        kind: 'TASK_END_REQUEST',
        payload: { requestedBy: 'agent-synthetic' },
      }))

      const decision = ledger.getCompletionDecision()
      expect(decision.status).toBe(expectedStatus)
      expect(decision.status).not.toBe('COMPLETE')
      expect(decision.closureRef).toBeUndefined()
    })
  })

  it('reports close-path obligations as deferred without waiting for Closure first', async () => {
    const contract = syntheticContract({
      obligations: [{
        id: 'OBL-SCOPE-001',
        kind: 'WRITE_SCOPE',
        severity: 'MUST',
        sourceRefs: [],
        target: {
          allowedResourceIds: ['resource-allowed'],
          allowedPathPrefixes: [],
        },
        satisfaction: { requireInScope: true },
      }, {
        id: 'OBL-CLOSURE-001',
        kind: 'CLOSURE',
        severity: 'MUST',
        sourceRefs: [],
        target: { required: true },
        satisfaction: { closureStatus: 'COMPLETE' },
      }],
    })
    await withLedger(contract, async ledger => {
      await ledger.ingest(syntheticEvent(1, {
        kind: 'TASK_END_REQUEST',
        payload: { requestedBy: 'agent-synthetic' },
      }))

      expect(ledger.getCompletionDecision()).toMatchObject({
        status: 'READY_TO_CLOSE',
        blockerRefs: ['deferred-obligation://OBL-CLOSURE-001'],
      })
      expect(ledger.getStatus().pendingObligationIds).toContain('OBL-CLOSURE-001')
    })
  })

  it('blocks a structured PASS claim that has no matching prior Evidence', async () => {
    const contract = syntheticContract({
      obligations: [{
        id: 'OBL-CLAIM-001',
        kind: 'CLAIM_EVIDENCE',
        severity: 'MUST',
        sourceRefs: [],
        target: {
          claimKinds: ['VALIDATION'],
          targetIdentities: ['target-primary'],
        },
        satisfaction: { requireEvidenceForPassClaims: true },
      }],
      evidencePolicies: [{
        id: 'EVP-CLAIM-001',
        obligationIds: ['OBL-CLAIM-001'],
        acceptedProviderIds: ['validator-primary'],
        acceptedProviderKinds: ['VALIDATOR'],
        acceptedResultStatuses: ['PASS'],
        requireExactContextHash: true,
        requireExactProjectRevision: true,
        requireExactTargetIdentity: true,
        maxAgeSeconds: 3_600,
      }],
    })
    await withLedger(contract, async ledger => {
      const claims: readonly AgentClaimV01[] = [{
        id: 'claim-pass-001',
        kind: 'VALIDATION',
        targetIdentity: 'target-primary',
        resultStatus: 'PASS',
        validationId: 'validation-primary',
        evidenceRefs: [],
      }]
      const nextSequence = await ingestTrustedSpan(ledger, contract, [], claims)
      await ledger.ingest(syntheticEvent(nextSequence, {
        kind: 'TASK_END_REQUEST',
        payload: { requestedBy: 'agent-synthetic' },
      }))

      expect(ledger.getStatus().violations).toEqual([
        expect.objectContaining({
          code: 'UNSUPPORTED_PASS_CLAIM',
          claimId: 'claim-pass-001',
          obligationId: 'OBL-CLAIM-001',
        }),
      ])
      expect(ledger.getCompletionDecision().status).toBe('BLOCKED')
    })
  })
})
