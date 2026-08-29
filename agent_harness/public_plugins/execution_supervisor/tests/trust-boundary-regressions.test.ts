import { afterEach, describe, expect, it } from 'vitest'
import {
  type AgentClaimV01,
  type ExecutionEventKind,
  type JsonRecord,
  type TaskSupervisionContractV01,
  createExecutionObligationLedger,
  createFileExecutionEventStore,
  hashCanonicalJson,
  sha256Hex,
  validateObligationLedgerContribution,
} from '../src/index.js'
import {
  EXTERNAL_AGENT_EVENT_BUNDLE_SCHEMA,
  EXTERNAL_AGENT_REQUEST_MANIFEST_SCHEMA,
  EXTERNAL_AGENT_RESPONSE_MANIFEST_SCHEMA,
  ingestExternalAgentEventBundle,
  validateExternalAgentEventBundle,
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

const directories: string[] = []

afterEach(async () => {
  await Promise.all(directories.splice(0).map(removeSyntheticTempDirectory))
})

const validationObligation = {
  id: 'OBL-VALIDATION-BOUNDARY',
  kind: 'VALIDATION',
  severity: 'MUST',
  sourceRefs: [],
  target: {
    validationId: 'validation-boundary',
    targetIdentity: 'target-boundary',
  },
  satisfaction: { requiredResultStatus: 'PASS' },
} as const

const validationPolicy = (acceptedResultStatuses: readonly ('PASS' | 'FAIL')[] = ['PASS']) => ({
  id: 'EVP-VALIDATION-BOUNDARY',
  obligationIds: ['OBL-VALIDATION-BOUNDARY'],
  acceptedProviderIds: ['validator-boundary'],
  acceptedProviderKinds: ['VALIDATOR'] as const,
  acceptedResultStatuses,
  requireExactContextHash: true,
  requireExactProjectRevision: true,
  requireExactTargetIdentity: true,
  maxAgeSeconds: 3_600,
})

const validationContract = (
  acceptedResultStatuses: readonly ('PASS' | 'FAIL')[] = ['PASS'],
): TaskSupervisionContractV01 => syntheticContract({
  obligations: [validationObligation],
  evidencePolicies: [validationPolicy(acceptedResultStatuses)],
})

const validationPayload = (
  resultStatus: 'PASS' | 'FAIL',
  claimRefs: readonly string[] = [],
  validationId = 'validation-boundary',
) => ({
  receipt: {
    providerId: 'validator-boundary',
    providerKind: 'VALIDATOR',
    validationId,
    commandOrTestIdentity: 'test:trust-boundary',
    projectRevision: 'revision-synthetic-001',
    contextHash: HASH_A,
    targetIdentity: 'target-boundary',
    resultStatus,
    artifactRefs: [],
    evidenceRefs: [`evidence://validation-${resultStatus.toLowerCase()}`],
    claimRefs,
    timestamp: '2026-08-29T00:00:01.000Z',
  },
})

const createLedger = async (contract: TaskSupervisionContractV01) => {
  const directory = await createSyntheticTempDirectory('phase34-trust-boundary-')
  directories.push(directory)
  const eventStore = await createFileExecutionEventStore({
    directory,
    binding: syntheticBinding({ contract }),
    limits: SYNTHETIC_LIMITS,
  })
  const ledger = await createExecutionObligationLedger({ eventStore })
  return { eventStore, ledger }
}

interface MiddleEventInput {
  readonly kind: ExecutionEventKind
  readonly eventId: string
  readonly payload: JsonRecord
}

const bridgeBundle = (
  contract: TaskSupervisionContractV01,
  middleInputs: readonly MiddleEventInput[],
  claims: readonly AgentClaimV01[],
): ExternalAgentEventBundleV01 => {
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
    expectedHostId: 'host-boundary',
    expectedProviderId: 'provider-model-boundary',
    expectedModelId: 'model-boundary',
    userMessage: {
      messageId: 'message-user-boundary',
      content: 'Evaluate the bounded trust-boundary fixture.',
      contentHash: sha256Hex('Evaluate the bounded trust-boundary fixture.'),
    },
    issuedAt: '2026-08-29T00:00:00.000Z',
  }
  const userEvent = syntheticEvent(1, {
    kind: 'USER_MESSAGE',
    eventId: requestManifest.userMessage.messageId,
    timestamp: requestManifest.issuedAt,
    payload: { requestManifest },
  })
  const middleEvents = middleInputs.map((input, index) => syntheticEvent(index + 2, {
    kind: input.kind,
    eventId: input.eventId,
    timestamp: new Date(Date.UTC(2026, 7, 29, 0, 0, index + 1)).toISOString(),
    payload: input.payload,
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
    responseId: 'response-boundary',
    actualHostId: 'host-boundary',
    actualProviderId: 'provider-model-boundary',
    actualModelId: 'model-boundary',
    actualAgentId: 'agent-synthetic',
    assistantMessage: {
      messageId: 'message-assistant-boundary',
      content: 'The bounded trust-boundary fixture was evaluated.',
      contentHash: sha256Hex('The bounded trust-boundary fixture was evaluated.'),
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
  return {
    schema: EXTERNAL_AGENT_EVENT_BUNDLE_SCHEMA,
    bundleId: 'bundle-boundary',
    requestManifestHash: hashCanonicalJson(requestManifest),
    responseManifestHash: hashCanonicalJson(responseManifest),
    events: [userEvent, ...middleEvents, assistantEvent],
  }
}

const claimContract = (): TaskSupervisionContractV01 => syntheticContract({
  obligations: [{
    id: 'OBL-CLAIM-BOUNDARY',
    kind: 'CLAIM_EVIDENCE',
    severity: 'MUST',
    sourceRefs: [],
    target: {
      claimKinds: ['VALIDATION', 'OUTPUT'],
      targetIdentities: ['target-boundary'],
    },
    satisfaction: { requireEvidenceForPassClaims: true },
  }],
  evidencePolicies: [{
    id: 'EVP-CLAIM-BOUNDARY',
    obligationIds: ['OBL-CLAIM-BOUNDARY'],
    acceptedProviderIds: ['validator-boundary', 'output-boundary'],
    acceptedProviderKinds: ['VALIDATOR', 'TOOL_GATEWAY'],
    acceptedResultStatuses: ['PASS'],
    requireExactContextHash: true,
    requireExactProjectRevision: true,
    requireExactTargetIdentity: true,
    maxAgeSeconds: 3_600,
  }],
})

describe('Phase 3+4 trusted ingress and completion regressions', () => {
  it('does not mistake an ordinary USER_MESSAGE for an external Bridge span', async () => {
    const contract = syntheticContract({
      obligations: [{
        id: 'OBL-ORDINARY-READ',
        kind: 'REQUIRED_RESOURCE',
        severity: 'MUST',
        sourceRefs: [],
        target: { resourceId: 'resource-ordinary' },
        satisfaction: {
          acceptedProviderIds: ['repository-boundary'],
          acceptedDispositions: ['FOUND'],
        },
      }],
    })
    const { eventStore, ledger } = await createLedger(contract)
    await ledger.ingest(syntheticEvent(1, {
      kind: 'USER_MESSAGE',
      payload: { message: 'ordinary runtime message' },
    }))
    await ledger.ingest(syntheticEvent(2, {
      kind: 'RESOURCE_READ',
      payload: {
        receipt: {
          provider: 'repository-boundary',
          resourceId: 'resource-ordinary',
          disposition: 'FOUND',
          purpose: 'Read after an ordinary user message.',
          claimRefs: [],
        },
      },
    }))

    expect(ledger.getStatus().satisfiedObligationIds).toEqual(['OBL-ORDINARY-READ'])
    await eventStore.close()
  })

  it('requires OUTPUT contract, resource identity and content hash in the contribution', () => {
    const invalid = syntheticContract({
      obligations: [{
        id: 'OBL-OUTPUT-INCOMPLETE',
        kind: 'OUTPUT',
        severity: 'MUST',
        sourceRefs: [],
        target: { outputContractId: 'output-boundary' },
        satisfaction: {
          requiredStructuralStatus: 'PASS',
          requiredResultStatus: 'PASS',
        },
      }],
      evidencePolicies: [{
        ...validationPolicy(['PASS']),
        id: 'EVP-OUTPUT-INCOMPLETE',
        obligationIds: ['OBL-OUTPUT-INCOMPLETE'],
      }],
    })

    const validation = validateObligationLedgerContribution(invalid)
    expect(validation.valid).toBe(false)
    if (!validation.valid) {
      expect(validation.issues.filter(item => item.code === 'LEDGER_INVALID_OUTPUT_IDENTITY'))
        .toHaveLength(2)
    }
  })

  it('does not satisfy an Evidence obligation from a direct Ledger event absent persisted request/response manifests', async () => {
    const { eventStore, ledger } = await createLedger(validationContract())

    await ledger.ingest(syntheticEvent(1, {
      kind: 'VALIDATION_RESULT',
      payload: validationPayload('PASS'),
    }))

    expect(ledger.getStatus()).toMatchObject({
      pendingObligationIds: ['OBL-VALIDATION-BOUNDARY'],
      satisfiedObligationIds: [],
    })
    await eventStore.close()
  })

  it('admits a provider-kind-only Evidence policy without inventing a provider ID allowlist', async () => {
    const contract = validationContract(['PASS'])
    const kindOnlyContract = {
      ...contract,
      evidencePolicies: [{
        ...contract.evidencePolicies[0]!,
        acceptedProviderIds: [],
      }],
    }
    const { eventStore, ledger } = await createLedger(kindOnlyContract)
    const input = bridgeBundle(kindOnlyContract, [{
      kind: 'VALIDATION_RESULT',
      eventId: 'evidence-event-kind-only',
      payload: validationPayload('PASS'),
    }], [])

    expect(validateExternalAgentEventBundle(input, ledger)).toMatchObject({ valid: true })
    await ingestExternalAgentEventBundle(ledger, input)
    expect(ledger.getStatus().satisfiedObligationIds).toEqual([
      'OBL-VALIDATION-BOUNDARY',
    ])
    await eventStore.close()
  })

  it('replaces a prior READY decision when a later accepted event changes obligation state', async () => {
    const contract = syntheticContract({
      obligations: [validationObligation],
      evidencePolicies: [{
        ...validationPolicy(['PASS']),
        maxAgeSeconds: 1,
      }],
    })
    const { eventStore, ledger } = await createLedger(contract)
    const input = bridgeBundle(contract, [{
      kind: 'VALIDATION_RESULT',
      eventId: 'evidence-event-ready-then-stale',
      payload: validationPayload('PASS'),
    }], [])
    await ingestExternalAgentEventBundle(ledger, input)
    await ledger.ingest(syntheticEvent(4, {
      kind: 'TASK_END_REQUEST',
      timestamp: '2026-08-29T00:00:02.000Z',
      payload: { requestedBy: 'agent-synthetic' },
    }))
    expect(ledger.getCompletionDecision().status).toBe('READY_TO_CLOSE')

    await ledger.ingest(syntheticEvent(5, {
      kind: 'TASK_END_REQUEST',
      timestamp: '2026-08-29T00:00:03.001Z',
      payload: { requestedBy: 'agent-synthetic' },
    }))

    expect(ledger.getStatus().pendingObligationIds).toEqual(['OBL-VALIDATION-BOUNDARY'])
    expect(ledger.getCompletionDecision()).toMatchObject({
      status: 'BLOCKED',
      pendingObligationIds: ['OBL-VALIDATION-BOUNDARY'],
    })
    await eventStore.close()
  })

  it.each([
    [{
      id: 'claim-shape-output',
      kind: 'OUTPUT',
      targetIdentity: 'target-boundary',
      resultStatus: 'PASS',
      validationId: 'validation-boundary',
      evidenceRefs: [],
    }, 'validationId'],
    [{
      id: 'claim-shape-validation',
      kind: 'VALIDATION',
      targetIdentity: 'target-boundary',
      resultStatus: 'PASS',
      outputContractId: 'output-boundary',
      evidenceRefs: [],
    }, 'outputContractId'],
  ] as const)('rejects a claim whose kind does not permit its identity field (%s)', async (
    invalidClaim,
    invalidField,
  ) => {
    const contract = claimContract()
    const { eventStore, ledger } = await createLedger(contract)
    const input = bridgeBundle(contract, [], [invalidClaim as unknown as AgentClaimV01])

    const validation = validateExternalAgentEventBundle(input, ledger)
    expect(validation.valid).toBe(false)
    if (!validation.valid) {
      expect(validation.issues).toEqual(expect.arrayContaining([
        expect.objectContaining({
          code: 'CLAIM_FIELD_MISMATCH',
          path: expect.stringContaining(invalidField),
        }),
      ]))
    }
    expect(eventStore.cursor.sequence).toBe(0)
    await eventStore.close()
  })

  it.each([
    ['VALIDATION', 'validation-other', undefined],
    ['OUTPUT', undefined, 'output-other'],
  ] as const)('requires exact %s claim identity to match its referenced receipt', async (
    kind,
    validationId,
    outputContractId,
  ) => {
    const contract = claimContract()
    const claimId = `claim-${kind.toLowerCase()}-identity-mismatch`
    const claim: AgentClaimV01 = {
      id: claimId,
      kind,
      targetIdentity: 'target-boundary',
      resultStatus: 'PASS',
      ...(validationId === undefined ? {} : { validationId }),
      ...(outputContractId === undefined ? {} : { outputContractId }),
      evidenceRefs: [`evidence-event-${kind.toLowerCase()}`],
    }
    const middle = kind === 'VALIDATION'
      ? [{
          kind: 'VALIDATION_RESULT' as const,
          eventId: 'evidence-event-validation',
          payload: validationPayload('PASS', [claimId]),
        }]
      : [{
          kind: 'OUTPUT_EMITTED' as const,
          eventId: 'evidence-event-output',
          payload: {
            receipt: {
              providerId: 'output-boundary',
              providerKind: 'TOOL_GATEWAY',
              outputContractId: 'output-boundary',
              resourceId: 'resource-output-boundary',
              contentHash: 'd'.repeat(64),
              projectRevision: 'revision-synthetic-001',
              contextHash: HASH_A,
              targetIdentity: 'target-boundary',
              structuralValidationStatus: 'PASS',
              ruleValidationRefs: [],
              evidenceRefs: ['evidence://output-pass'],
              claimRefs: [claimId],
              timestamp: '2026-08-29T00:00:01.000Z',
            },
          },
        }]
    const { eventStore, ledger } = await createLedger(contract)
    const input = bridgeBundle(contract, middle, [claim])

    expect(validateExternalAgentEventBundle(input, ledger)).toMatchObject({ valid: true })
    await ingestExternalAgentEventBundle(ledger, input)

    expect(ledger.getStatus()).toMatchObject({
      violatedObligationIds: ['OBL-CLAIM-BOUNDARY'],
      violations: [expect.objectContaining({
        code: 'UNSUPPORTED_PASS_CLAIM',
        claimId,
      })],
    })
    await eventStore.close()
  })

  it('revalidates structured PASS claim Evidence freshness at task end', async () => {
    const base = claimContract()
    const contract = {
      ...base,
      evidencePolicies: [{ ...base.evidencePolicies[0]!, maxAgeSeconds: 1 }],
    }
    const claimId = 'claim-stale-at-close'
    const claim: AgentClaimV01 = {
      id: claimId,
      kind: 'VALIDATION',
      targetIdentity: 'target-boundary',
      resultStatus: 'PASS',
      validationId: 'validation-boundary',
      evidenceRefs: ['evidence-event-validation'],
    }
    const { eventStore, ledger } = await createLedger(contract)
    await ingestExternalAgentEventBundle(ledger, bridgeBundle(contract, [{
      kind: 'VALIDATION_RESULT',
      eventId: 'evidence-event-validation',
      payload: validationPayload('PASS', [claimId]),
    }], [claim]))
    expect(ledger.getStatus().violations).toEqual([])

    await ledger.ingest(syntheticEvent(4, {
      kind: 'TASK_END_REQUEST',
      timestamp: '2026-08-29T00:00:03.001Z',
      payload: { requestedBy: 'agent-synthetic' },
    }))

    expect(ledger.getStatus()).toMatchObject({
      pendingObligationIds: ['OBL-CLAIM-BOUNDARY'],
      violations: [],
    })
    expect(ledger.getCompletionDecision().status).toBe('BLOCKED')
    await eventStore.close()
  })

  it('treats trusted FAIL as VIOLATED and FAILED even when the policy acceptance list contains only PASS', async () => {
    const contract = validationContract(['PASS'])
    const { eventStore, ledger } = await createLedger(contract)
    const input = bridgeBundle(contract, [{
      kind: 'VALIDATION_RESULT',
      eventId: 'evidence-event-fail',
      payload: validationPayload('FAIL'),
    }], [])

    expect(validateExternalAgentEventBundle(input, ledger)).toMatchObject({ valid: true })
    await ingestExternalAgentEventBundle(ledger, input)
    await ledger.ingest(syntheticEvent(4, {
      kind: 'TASK_END_REQUEST',
      payload: { requestedBy: 'agent-synthetic' },
    }))

    expect(ledger.getStatus()).toMatchObject({
      violatedObligationIds: ['OBL-VALIDATION-BOUNDARY'],
      violations: [expect.objectContaining({
        code: 'TRUSTED_VALIDATION_FAILED',
        eventId: 'evidence-event-fail',
      })],
    })
    expect(ledger.getCompletionDecision().status).toBe('FAILED')
    await eventStore.close()
  })

  it('keeps intrinsic Evidence behind its dependency mask and restores it when the prerequisite is satisfied', async () => {
    const contract = syntheticContract({
      obligations: [{
        ...validationObligation,
        dependencies: ['OBL-READ-PREREQUISITE'],
      }, {
        id: 'OBL-READ-PREREQUISITE',
        kind: 'REQUIRED_RESOURCE',
        severity: 'MUST',
        sourceRefs: [],
        target: { resourceId: 'resource-prerequisite' },
        satisfaction: {
          acceptedProviderIds: ['repository-boundary'],
          acceptedDispositions: ['FOUND'],
        },
      }],
      evidencePolicies: [validationPolicy(['PASS'])],
    })
    const { eventStore, ledger } = await createLedger(contract)
    await ingestExternalAgentEventBundle(ledger, bridgeBundle(contract, [{
      kind: 'VALIDATION_RESULT',
      eventId: 'evidence-event-dependent-first',
      payload: validationPayload('PASS'),
    }], []))

    expect(ledger.getStatus()).toMatchObject({
      blockedObligationIds: ['OBL-VALIDATION-BOUNDARY'],
      pendingObligationIds: ['OBL-READ-PREREQUISITE'],
    })

    await ledger.ingest(syntheticEvent(4, {
      kind: 'RESOURCE_READ',
      payload: {
        receipt: {
          provider: 'repository-boundary',
          resourceId: 'resource-prerequisite',
          disposition: 'FOUND',
          purpose: 'Satisfy the prerequisite after dependent Evidence arrived.',
          claimRefs: [],
        },
      },
    }))

    expect(ledger.getStatus()).toMatchObject({
      satisfiedObligationIds: [
        'OBL-VALIDATION-BOUNDARY',
        'OBL-READ-PREREQUISITE',
      ],
      blockedObligationIds: [],
    })
    await eventStore.close()
  })

  it('records task-end intrinsic WRITE_SCOPE satisfaction while its dependency is blocked', async () => {
    const contract = syntheticContract({
      obligations: [{
        id: 'OBL-SCOPE-DEPENDENT',
        kind: 'WRITE_SCOPE',
        severity: 'MUST',
        sourceRefs: [],
        target: {
          allowedResourceIds: ['resource-allowed'],
          allowedPathPrefixes: [],
        },
        satisfaction: { requireInScope: true },
        dependencies: ['OBL-READ-BEFORE-CLOSE'],
      }, {
        id: 'OBL-READ-BEFORE-CLOSE',
        kind: 'REQUIRED_RESOURCE',
        severity: 'MUST',
        sourceRefs: [],
        target: { resourceId: 'resource-before-close' },
        satisfaction: {
          acceptedProviderIds: ['repository-boundary'],
          acceptedDispositions: ['FOUND'],
        },
      }],
    })
    const { eventStore, ledger } = await createLedger(contract)
    await ledger.ingest(syntheticEvent(1, {
      kind: 'TASK_END_REQUEST',
      payload: { requestedBy: 'agent-synthetic' },
    }))
    expect(ledger.getStatus().blockedObligationIds).toEqual(['OBL-SCOPE-DEPENDENT'])

    await ledger.ingest(syntheticEvent(2, {
      kind: 'RESOURCE_READ',
      payload: {
        receipt: {
          provider: 'repository-boundary',
          resourceId: 'resource-before-close',
          disposition: 'FOUND',
          purpose: 'Resolve the close-path prerequisite.',
          claimRefs: [],
        },
      },
    }))

    expect(ledger.getStatus().satisfiedObligationIds).toEqual([
      'OBL-SCOPE-DEPENDENT',
      'OBL-READ-BEFORE-CLOSE',
    ])
    expect(ledger.getCompletionDecision().status).toBe('READY_TO_CLOSE')
    await eventStore.close()
  })

  it('satisfies SOURCE_DISPOSITION from its matching accepted event kind', async () => {
    const contract = syntheticContract({
      obligations: [{
        id: 'OBL-SOURCE-DISPOSITION-BOUNDARY',
        kind: 'SOURCE_DISPOSITION',
        severity: 'MUST',
        sourceRefs: [],
        target: { resourceId: 'resource-unavailable' },
        satisfaction: {
          acceptedProviderIds: ['repository-boundary'],
          acceptedDispositions: ['UNAVAILABLE'],
        },
      }],
      evidencePolicies: [],
    })
    const { eventStore, ledger } = await createLedger(contract)
    const input = bridgeBundle(contract, [{
      kind: 'SOURCE_DISPOSITION',
      eventId: 'source-disposition-event',
      payload: {
        receipt: {
          provider: 'repository-boundary',
          resourceId: 'resource-unavailable',
          disposition: 'UNAVAILABLE',
          purpose: 'Record the bounded unavailable source.',
          claimRefs: [],
          error: 'not available',
        },
      },
    }], [])

    expect(validateExternalAgentEventBundle(input, ledger)).toMatchObject({ valid: true })
    await ingestExternalAgentEventBundle(ledger, input)

    expect(ledger.getStatus()).toMatchObject({
      satisfiedObligationIds: ['OBL-SOURCE-DISPOSITION-BOUNDARY'],
      pendingObligationIds: [],
    })
    await eventStore.close()
  })
})
