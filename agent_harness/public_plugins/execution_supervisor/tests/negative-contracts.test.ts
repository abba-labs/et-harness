import { describe, expect, it } from 'vitest'
import {
  EXECUTION_EVENT_SCHEMA,
  HOST_CAPABILITY_CONTRACT_SCHEMA,
  MAX_EXECUTION_EVENT_PAYLOAD_BYTES,
  TASK_SUPERVISION_CONTRACT_SCHEMA,
  hashCanonicalJson,
  negotiateSupervisionLevel,
  validateCompletionDecision,
  validateExecutionEventEnvelope,
  validateHostCapabilityContract,
  validatePerformanceBaselineReport,
  validateTaskSupervisionContract,
  type TaskSupervisionContractV01,
} from '../src/index.js'

const HASH_A = 'a'.repeat(64)
const HASH_B = 'b'.repeat(64)

const baseContract = (): TaskSupervisionContractV01 => ({
  schema: TASK_SUPERVISION_CONTRACT_SCHEMA,
  projectId: 'project-alpha',
  taskId: 'task-001',
  agentId: 'agent-primary',
  contextHash: HASH_A,
  routeHash: HASH_B,
  supervisionLevel: 'AUDIT',
  obligations: [
    {
      id: 'OBL-001',
      kind: 'REQUIRED_RESOURCE',
      severity: 'MUST',
      sourceRefs: [],
      target: { resourceId: 'resource-primary' },
      satisfaction: { disposition: 'FOUND' },
    },
  ],
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

const eventFor = (payload: Record<string, unknown>) => ({
  schema: EXECUTION_EVENT_SCHEMA,
  requestId: 'request-001',
  runtimeId: 'runtime-001',
  projectId: 'project-alpha',
  taskId: 'task-001',
  turnId: 'turn-001',
  agentId: 'agent-primary',
  contextHash: HASH_A,
  sequence: 1,
  eventId: 'event-001',
  timestamp: '2026-08-28T00:00:00.000Z',
  kind: 'TOOL_RESULT',
  payloadHash: hashCanonicalJson(payload),
  payload,
})

describe('Execution Supervisor Phase 0 fail-closed validation', () => {
  it('rejects the wrong schema and unknown top-level fields', () => {
    const contract = { ...baseContract(), schema: 'wrong', extra: true }
    const result = validateTaskSupervisionContract(contract)
    expect(result.valid).toBe(false)
    if (!result.valid) {
      expect(result.issues.map(item => item.code)).toEqual(expect.arrayContaining([
        'INVALID_SCHEMA',
        'UNKNOWN_FIELD',
      ]))
    }
  })

  it('rejects duplicate obligations and dependency cycles', () => {
    const contract = baseContract()
    const template = contract.obligations[0]!
    const result = validateTaskSupervisionContract({
      ...contract,
      obligations: [
        { ...template, id: 'OBL-CYCLE-A', dependencies: ['OBL-CYCLE-B'] },
        { ...template, id: 'OBL-CYCLE-B', dependencies: ['OBL-CYCLE-A'] },
        { ...template, id: 'OBL-DUPLICATE' },
        { ...template, id: 'OBL-DUPLICATE' },
      ],
    })
    expect(result.valid).toBe(false)
    if (!result.valid) {
      expect(result.issues.map(item => item.code)).toEqual(expect.arrayContaining([
        'DUPLICATE_OBLIGATION_ID',
        'DEPENDENCY_CYCLE',
      ]))
    }
  })

  it('rejects an evidence policy without a trusted provider', () => {
    const contract = baseContract()
    const result = validateTaskSupervisionContract({
      ...contract,
      evidencePolicies: [{
        id: 'EVP-001',
        obligationIds: ['OBL-001'],
        acceptedProviderIds: [],
        acceptedProviderKinds: [],
        acceptedResultStatuses: ['PASS'],
        requireExactContextHash: true,
        requireExactProjectRevision: true,
        requireExactTargetIdentity: true,
      }],
    })
    expect(result.valid).toBe(false)
    if (!result.valid) expect(result.issues.some(item => item.code === 'NO_TRUSTED_PROVIDER')).toBe(true)
  })

  it('rejects a tampered payload hash', () => {
    const event = eventFor({ status: 'SUCCESS' })
    const result = validateExecutionEventEnvelope({
      ...event,
      payload: { status: 'ERROR' },
    })
    expect(result.valid).toBe(false)
    if (!result.valid) expect(result.issues.some(item => item.code === 'PAYLOAD_HASH_MISMATCH')).toBe(true)
  })

  it('rejects an unknown event kind and sequence zero', () => {
    const event = eventFor({ status: 'SUCCESS' })
    const result = validateExecutionEventEnvelope({
      ...event,
      kind: 'UNDECLARED_EVENT',
      sequence: 0,
    })
    expect(result.valid).toBe(false)
    if (!result.valid) {
      expect(result.issues.map(item => item.code)).toEqual(expect.arrayContaining([
        'INVALID_ENUM',
        'INVALID_INTEGER',
      ]))
    }
  })

  it('rejects hidden reasoning and oversized payloads', () => {
    const hidden = eventFor({ privateReasoning: 'not allowed' })
    const hiddenResult = validateExecutionEventEnvelope(hidden)
    expect(hiddenResult.valid).toBe(false)
    if (!hiddenResult.valid) {
      expect(hiddenResult.issues.some(item => item.code === 'HIDDEN_REASONING_FORBIDDEN')).toBe(true)
    }

    const largePayload = { summary: 'x'.repeat(MAX_EXECUTION_EVENT_PAYLOAD_BYTES + 1) }
    const largeResult = validateExecutionEventEnvelope(eventFor(largePayload))
    expect(largeResult.valid).toBe(false)
    if (!largeResult.valid) {
      expect(largeResult.issues.some(item => item.code === 'JSON_BUDGET_EXCEEDED')).toBe(true)
    }
  })

  it('truthfully downgrades ENFORCE to AUDIT when interception is unavailable', () => {
    const host = {
      schema: HOST_CAPABILITY_CONTRACT_SCHEMA,
      hostId: 'host-audit-only',
      adapterId: 'adapter-audit-only',
      capabilities: {
        supportsPreflight: false,
        supportsToolInterception: false,
        supportsStableToolEventId: true,
        supportsResourceHash: true,
        supportsMessageRef: true,
        supportsCrossProcessResume: true,
      },
    } as const
    expect(validateHostCapabilityContract(host).valid).toBe(true)
    expect(negotiateSupervisionLevel('ENFORCE', host)).toMatchObject({
      requestedLevel: 'ENFORCE',
      effectiveLevel: 'AUDIT',
    })
  })

  it('rejects COMPLETE without Closure and READY_TO_CLOSE with pending obligations', () => {
    const missingClosure = validateCompletionDecision({
      status: 'COMPLETE',
      pendingObligationIds: [],
      violatedObligationIds: [],
      blockerRefs: [],
      evidenceRefs: [],
    })
    expect(missingClosure.valid).toBe(false)

    const premature = validateCompletionDecision({
      status: 'READY_TO_CLOSE',
      pendingObligationIds: ['OBL-001'],
      violatedObligationIds: [],
      blockerRefs: [],
      evidenceRefs: [],
    })
    expect(premature.valid).toBe(false)
  })

  it('rejects a Phase 0 baseline that pretends numeric SLOs are frozen', () => {
    const result = validatePerformanceBaselineReport({
      schema: 'agent-harness.execution-supervisor-baseline.v0.1',
      baselineId: 'bad-baseline',
      capturedAt: '2026-08-28T00:00:00.000Z',
      sourceRevision: 'revision-001',
      environment: {
        nodeVersion: process.version,
        platform: process.platform,
        architecture: process.arch,
      },
      thresholdsFrozen: true,
      invariants: {
        noSemanticCallOnHotPath: true,
        noFullRerouteForOrdinaryRead: true,
        maxUnifiedReflectionsPerTurn: 1,
        maxEventPayloadBytes: MAX_EXECUTION_EVENT_PAYLOAD_BYTES,
        maxTaskContractBytes: 512 * 1024,
      },
      samples: [{
        scenario: 'contract-validation',
        warmupIterations: 1,
        sampleIterations: 1,
        inputBytes: 1,
        p50Micros: 1,
        p95Micros: 1,
        p99Micros: 1,
        meanMicros: 1,
        maxMicros: 1,
      }],
      notes: [],
    })
    expect(result.valid).toBe(false)
  })
})
