import { afterEach, describe, expect, it } from 'vitest'
import {
  EXECUTION_EVENT_SCHEMA,
  TASK_SUPERVISION_CONTRACT_SCHEMA,
  type ExecutionEventEnvelopeV01,
  type ExecutionEventKind,
  type JsonRecord,
  type TaskSupervisionContractV01,
} from '../src/contracts.js'
import { createFileExecutionEventStore } from '../src/event-store.js'
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
import { hashCanonicalJson, sha256Hex } from '../src/hash.js'
import { createExecutionObligationLedger } from '../src/obligation-ledger.js'
import {
  createSyntheticTempDirectory,
  removeSyntheticTempDirectory,
} from './fixtures/synthetic-fixtures.js'

const HASH_A = 'a'.repeat(64)
const HASH_B = 'b'.repeat(64)
const directories: string[] = []

afterEach(async () => {
  await Promise.all(directories.splice(0).map(removeSyntheticTempDirectory))
})

const contract = (): TaskSupervisionContractV01 => ({
  schema: TASK_SUPERVISION_CONTRACT_SCHEMA,
  projectId: 'project-bridge',
  taskId: 'task-bridge',
  agentId: 'agent-bridge',
  contextHash: HASH_A,
  routeHash: HASH_B,
  projectRevision: 'revision-bridge-001',
  supervisionLevel: 'AUDIT',
  obligations: [{
    id: 'OBL-READ-BRIDGE',
    kind: 'REQUIRED_RESOURCE',
    severity: 'MUST',
    sourceRefs: ['contract://bridge/read'],
    target: { resourceId: 'resource-bridge' },
    satisfaction: {
      acceptedProviderIds: ['provider-resource'],
      acceptedDispositions: ['FOUND'],
    },
  }],
  evidencePolicies: [],
  completionPolicy: {
    requireAllMustSatisfied: true,
    requireNoViolations: true,
    requireReflection: true,
    requireKnowledgeDecision: true,
    requireContextUpdate: true,
    requireClosureReceipt: true,
    allowShouldWarnings: true,
    requiredClosureModuleIds: [],
  },
})

const binding = () => ({
  requestId: 'request-bridge',
  runtimeId: 'runtime-bridge',
  turnId: 'turn-bridge',
  contract: contract(),
})

const createLedger = async (maxEvents = 20) => {
  const directory = await createSyntheticTempDirectory('external-agent-bridge-')
  directories.push(directory)
  const eventStore = await createFileExecutionEventStore({
    directory,
    binding: binding(),
    limits: {
      maxEvents,
      maxStoreBytes: 4 * 1024 * 1024,
      maxReplayEvents: Math.min(maxEvents, 20),
    },
  })
  const ledger = await createExecutionObligationLedger({ eventStore })
  return { eventStore, ledger }
}

const event = (
  sequence: number,
  kind: ExecutionEventKind,
  eventId: string,
  timestamp: string,
  payload: JsonRecord,
): ExecutionEventEnvelopeV01 => ({
  schema: EXECUTION_EVENT_SCHEMA,
  requestId: 'request-bridge',
  runtimeId: 'runtime-bridge',
  projectId: 'project-bridge',
  taskId: 'task-bridge',
  turnId: 'turn-bridge',
  agentId: 'agent-bridge',
  contextHash: HASH_A,
  sequence,
  eventId,
  timestamp,
  kind,
  payloadHash: hashCanonicalJson(payload),
  payload,
})

interface BundleOptions {
  readonly actualProviderId?: string
  readonly actualModelId?: string
  readonly receiptRefHash?: string
  readonly corruptAssistantPayloadHash?: boolean
}

const bundle = (options: BundleOptions = {}): ExternalAgentEventBundleV01 => {
  const issuedAt = '2026-08-29T01:00:00.000Z'
  const receiptAt = '2026-08-29T01:00:01.000Z'
  const completedAt = '2026-08-29T01:00:02.000Z'
  const requestManifest: ExternalAgentRequestManifestV01 = {
    schema: EXTERNAL_AGENT_REQUEST_MANIFEST_SCHEMA,
    requestId: 'request-bridge',
    runtimeId: 'runtime-bridge',
    projectId: 'project-bridge',
    taskId: 'task-bridge',
    turnId: 'turn-bridge',
    agentId: 'agent-bridge',
    contextHash: HASH_A,
    contractHash: hashCanonicalJson(contract()),
    expectedHostId: 'host-codex',
    expectedProviderId: 'provider-model',
    expectedModelId: 'model-synthetic',
    userMessage: {
      messageId: 'message-user-001',
      content: 'Read the required resource and report the bounded result.',
      contentHash: sha256Hex('Read the required resource and report the bounded result.'),
    },
    issuedAt,
  }
  const requestPayload = { requestManifest }
  const userEvent = event(1, 'USER_MESSAGE', 'message-user-001', issuedAt, requestPayload)
  const receiptPayload = {
    receipt: {
      provider: 'provider-resource',
      resourceId: 'resource-bridge',
      disposition: 'FOUND',
      purpose: 'Read the resource required by the frozen contract.',
      claimRefs: [],
    },
  }
  const receiptEvent = event(2, 'RESOURCE_READ', 'receipt-resource-001', receiptAt, receiptPayload)
  const responseManifest: ExternalAgentResponseManifestV01 = {
    schema: EXTERNAL_AGENT_RESPONSE_MANIFEST_SCHEMA,
    requestManifestHash: hashCanonicalJson(requestManifest),
    requestId: 'request-bridge',
    runtimeId: 'runtime-bridge',
    projectId: 'project-bridge',
    taskId: 'task-bridge',
    turnId: 'turn-bridge',
    agentId: 'agent-bridge',
    contextHash: HASH_A,
    responseId: 'response-bridge-001',
    actualHostId: 'host-codex',
    actualProviderId: options.actualProviderId ?? 'provider-model',
    actualModelId: options.actualModelId ?? 'model-synthetic',
    actualAgentId: 'agent-bridge',
    assistantMessage: {
      messageId: 'message-assistant-001',
      content: 'The required resource was read.',
      contentHash: sha256Hex('The required resource was read.'),
    },
    claims: [],
    receiptRefs: [{
      eventId: receiptEvent.eventId,
      payloadHash: options.receiptRefHash ?? receiptEvent.payloadHash,
    }],
    completedAt,
  }
  const responsePayload = { responseManifest }
  const assistant = event(
    3,
    'ASSISTANT_MESSAGE',
    'message-assistant-001',
    completedAt,
    responsePayload,
  )
  const assistantEvent = options.corruptAssistantPayloadHash
    ? { ...assistant, payloadHash: 'f'.repeat(64) }
    : assistant
  return {
    schema: EXTERNAL_AGENT_EVENT_BUNDLE_SCHEMA,
    bundleId: 'bundle-bridge-001',
    requestManifestHash: hashCanonicalJson(requestManifest),
    responseManifestHash: hashCanonicalJson(responseManifest),
    events: [userEvent, receiptEvent, assistantEvent],
  }
}

describe('Phase 3 external Agent data-only Bridge', () => {
  it('prevalidates the whole bundle, ingests only through the Ledger, and durably preserves both manifests', async () => {
    const { eventStore, ledger } = await createLedger()
    const input = bundle()

    const validation = validateExternalAgentEventBundle(input, ledger)
    expect(validation).toMatchObject({ valid: true, issues: [] })

    const result = await ingestExternalAgentEventBundle(ledger, input)
    expect(result.failure).toBeUndefined()
    expect(result.acceptances.map(item => item.status)).toEqual([
      'ACCEPTED', 'ACCEPTED', 'ACCEPTED',
    ])
    expect(result.acceptedPrefix).toHaveLength(3)
    expect(ledger.getStatus()).toMatchObject({
      cursor: { sequence: 3 },
      satisfiedObligationIds: ['OBL-READ-BRIDGE'],
    })

    const replay = await eventStore.replay({ limit: 10 })
    expect(replay.events[0]?.payload).toEqual(input.events[0]?.payload)
    expect(replay.events[2]?.payload).toEqual(input.events[2]?.payload)
    await eventStore.close()
  })

  it.each([
    [{ actualProviderId: 'provider-wrong' }, 'PROVIDER_IDENTITY_MISMATCH'],
    [{ actualModelId: 'model-wrong' }, 'MODEL_IDENTITY_MISMATCH'],
    [{ receiptRefHash: 'f'.repeat(64) }, 'RECEIPT_HASH_MISMATCH'],
  ] as const)('rejects identity or receipt binding mismatch before the first append', async (options, code) => {
    const { eventStore, ledger } = await createLedger()
    const validation = validateExternalAgentEventBundle(bundle(options), ledger)

    expect(validation.valid).toBe(false)
    if (!validation.valid) expect(validation.issues.map(item => item.code)).toContain(code)
    await expect(ingestExternalAgentEventBundle(ledger, bundle(options))).rejects.toThrow(code)
    expect(eventStore.cursor.sequence).toBe(0)
    await eventStore.close()
  })

  it('does not append an earlier valid event when a later event envelope is invalid', async () => {
    const { eventStore, ledger } = await createLedger()
    const input = bundle({ corruptAssistantPayloadHash: true })

    const validation = validateExternalAgentEventBundle(input, ledger)
    expect(validation.valid).toBe(false)
    if (!validation.valid) {
      expect(validation.issues.map(item => item.code)).toContain('EVENT_PAYLOAD_HASH_MISMATCH')
    }
    await expect(ingestExternalAgentEventBundle(ledger, input)).rejects.toThrow('EVENT_PAYLOAD_HASH_MISMATCH')
    expect(eventStore.cursor.sequence).toBe(0)
    await eventStore.close()
  })

  it('rejects a visible messageId that is not the persisted message eventId', async () => {
    const { eventStore, ledger } = await createLedger()
    const input = bundle()
    const mismatched = {
      ...input,
      events: [{ ...input.events[0]!, eventId: 'message-user-mismatch' }, ...input.events.slice(1)],
    }

    const validation = validateExternalAgentEventBundle(mismatched, ledger)
    expect(validation.valid).toBe(false)
    if (!validation.valid) {
      expect(validation.issues.map(item => item.code)).toContain('USER_MESSAGE_ID_MISMATCH')
    }
    expect(eventStore.cursor.sequence).toBe(0)
    await eventStore.close()
  })

  it('returns typed validation issues for malformed visible messages without appending', async () => {
    const { eventStore, ledger } = await createLedger()
    const input = bundle() as unknown as { events: Array<Record<string, unknown>> }
    const first = input.events[0]!
    const payload = first.payload as { requestManifest: Record<string, unknown> }
    payload.requestManifest.userMessage = null
    first.payloadHash = hashCanonicalJson(payload)

    expect(() => validateExternalAgentEventBundle(input, ledger)).not.toThrow()
    const validation = validateExternalAgentEventBundle(input, ledger)
    expect(validation.valid).toBe(false)
    if (!validation.valid) {
      expect(validation.issues.map(item => item.code)).toContain('INVALID_MESSAGE')
    }
    expect(eventStore.cursor.sequence).toBe(0)
    await eventStore.close()
  })

  it('relies on Phase 1 idempotency for a complete retry without duplicating Ledger effects', async () => {
    const { eventStore, ledger } = await createLedger()
    const input = bundle()

    await ingestExternalAgentEventBundle(ledger, input)
    const retried = await ingestExternalAgentEventBundle(ledger, input)

    expect(retried.failure).toBeUndefined()
    expect(retried.acceptances.map(item => item.status)).toEqual([
      'DUPLICATE', 'DUPLICATE', 'DUPLICATE',
    ])
    expect(eventStore.eventCount).toBe(3)
    expect(ledger.getStatus().obligations[0]?.eventRefs).toEqual(['receipt-resource-001'])
    await eventStore.close()
  })

  it('reports the exact accepted prefix when the durable store rejects a later append', async () => {
    const { eventStore, ledger } = await createLedger(2)

    const result = await ingestExternalAgentEventBundle(ledger, bundle())

    expect(result.acceptances.map(item => item.status)).toEqual([
      'ACCEPTED', 'ACCEPTED', 'REJECTED',
    ])
    expect(result.acceptedPrefix.map(item => item.eventId)).toEqual([
      'message-user-001', 'receipt-resource-001',
    ])
    expect(result.failure).toMatchObject({
      eventId: 'message-assistant-001',
      sequence: 3,
      status: 'REJECTED',
    })
    expect(eventStore.cursor.sequence).toBe(2)
    expect(ledger.getStatus().pendingObligationIds).toEqual(['OBL-READ-BRIDGE'])
    expect(ledger.getStatus().satisfiedObligationIds).toEqual([])
    await eventStore.close()
  })
})
