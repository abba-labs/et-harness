import { readFileSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import {
  EXECUTION_EVENT_SCHEMA,
  HOST_CAPABILITY_CONTRACT_SCHEMA,
  TASK_SUPERVISION_CONTRACT_SCHEMA,
  createPhase0PerformanceBaseline,
  hashCanonicalJson,
  negotiateSupervisionLevel,
  summarizeDurationsMicros,
  validateCompletionDecision,
  validateExecutionEventEnvelope,
  validateHostCapabilityContract,
  validatePerformanceBaselineReport,
  validateTaskSupervisionContract,
  type HostCapabilityContractV01,
  type TaskSupervisionContractV01,
} from '../src/index.js'

const HASH_A = 'a'.repeat(64)
const HASH_B = 'b'.repeat(64)

const validTaskContract = (): TaskSupervisionContractV01 => ({
  schema: TASK_SUPERVISION_CONTRACT_SCHEMA,
  projectId: 'project-alpha',
  taskId: 'task-analysis-001',
  agentId: 'agent-primary',
  contextHash: HASH_A,
  routeHash: HASH_B,
  projectRevision: 'revision-001',
  supervisionLevel: 'AUDIT',
  obligations: [
    {
      id: 'OBL-READ-001',
      kind: 'REQUIRED_RESOURCE',
      severity: 'MUST',
      sourceRefs: ['rule://R001'],
      target: { resourcePattern: 'source/**' },
      satisfaction: { acceptedDispositions: ['FOUND'] },
    },
    {
      id: 'OBL-OUTPUT-001',
      kind: 'OUTPUT',
      severity: 'MUST',
      sourceRefs: ['rule://R002'],
      target: { contractId: 'output-contract-primary' },
      satisfaction: { structuralStatus: 'PASS' },
      dependencies: ['OBL-READ-001'],
    },
    {
      id: 'OBL-CLOSE-001',
      kind: 'CLOSURE',
      severity: 'MUST',
      sourceRefs: [],
      target: { required: true },
      satisfaction: { closureStatus: 'COMPLETE' },
      dependencies: ['OBL-OUTPUT-001'],
    },
  ],
  evidencePolicies: [
    {
      id: 'EVP-OUTPUT-001',
      obligationIds: ['OBL-OUTPUT-001'],
      acceptedProviderIds: ['validator-primary'],
      acceptedProviderKinds: ['VALIDATOR'],
      acceptedResultStatuses: ['PASS'],
      requireExactContextHash: true,
      requireExactProjectRevision: true,
      requireExactTargetIdentity: true,
      maxAgeSeconds: 3600,
    },
  ],
  completionPolicy: {
    requireAllMustSatisfied: true,
    requireNoViolations: true,
    requireReflection: true,
    requireKnowledgeDecision: true,
    requireContextUpdate: true,
    requireClosureReceipt: true,
    allowShouldWarnings: true,
    requiredClosureModuleIds: ['context-closure', 'knowledge-closure'],
  },
})

const hostCapabilities = (): HostCapabilityContractV01 => ({
  schema: HOST_CAPABILITY_CONTRACT_SCHEMA,
  hostId: 'host-primary',
  adapterId: 'adapter-primary',
  capabilities: {
    supportsPreflight: true,
    supportsToolInterception: true,
    supportsStableToolEventId: true,
    supportsResourceHash: true,
    supportsMessageRef: true,
    supportsCrossProcessResume: true,
  },
})

describe('Execution Supervisor Phase 0 contracts', () => {
  it('accepts one generic task supervision contract', () => {
    const result = validateTaskSupervisionContract(validTaskContract())
    expect(result.valid).toBe(true)
  })

  it('accepts one canonical bounded execution event', () => {
    const payload = {
      provider: 'repository-provider',
      resourceId: 'resource-primary',
      disposition: 'FOUND',
      contentHash: HASH_A,
      purpose: 'Resolve a required resource obligation.',
      claimRefs: ['claim://primary'],
    }
    const result = validateExecutionEventEnvelope({
      schema: EXECUTION_EVENT_SCHEMA,
      requestId: 'request-001',
      runtimeId: 'runtime-001',
      projectId: 'project-alpha',
      taskId: 'task-analysis-001',
      turnId: 'turn-001',
      agentId: 'agent-primary',
      contextHash: HASH_A,
      sequence: 1,
      eventId: 'event-001',
      timestamp: '2026-08-28T00:00:00.000Z',
      kind: 'RESOURCE_READ',
      payloadHash: hashCanonicalJson(payload),
      payload,
    })
    expect(result.valid).toBe(true)
  })

  it('negotiates ENFORCE only when the Host owns the minimum tool boundary', () => {
    const host = hostCapabilities()
    expect(validateHostCapabilityContract(host).valid).toBe(true)
    expect(negotiateSupervisionLevel('ENFORCE', host)).toMatchObject({
      requestedLevel: 'ENFORCE',
      effectiveLevel: 'ENFORCE',
    })
  })

  it('requires Closure identity before COMPLETE', () => {
    expect(validateCompletionDecision({
      status: 'COMPLETE',
      pendingObligationIds: [],
      violatedObligationIds: [],
      blockerRefs: [],
      evidenceRefs: ['evidence://primary'],
      closureRef: 'closure://task-analysis-001/turn-001',
    }).valid).toBe(true)
  })

  it('builds a valid unfrozen Phase 0 performance report', () => {
    const sample = summarizeDurationsMicros({
      scenario: 'contract-validation',
      warmupIterations: 2,
      inputBytes: 100,
      durationsMicros: [1, 2, 3, 4, 5],
    })
    const report = createPhase0PerformanceBaseline({
      baselineId: 'phase0-local',
      capturedAt: '2026-08-28T00:00:00.000Z',
      sourceRevision: 'revision-001',
      nodeVersion: process.version,
      platform: process.platform,
      architecture: process.arch,
      samples: [sample],
      notes: ['Numeric SLOs are intentionally not frozen in Phase 0.'],
    })
    expect(validatePerformanceBaselineReport(report).valid).toBe(true)
  })

  it('keeps public contract source free of project/domain business terms', () => {
    const srcRoot = resolve(import.meta.dirname, '../src')
    const text = readdirSync(srcRoot)
      .filter(name => name.endsWith('.ts'))
      .map(name => readFileSync(resolve(srcRoot, name), 'utf8'))
      .join('\n')
    const forbidden = [
      ['A', 'T', 'P'].join(''),
      ['E', 'T', '6', '8', '0', '1'].join(''),
      ['e', 'T', 'i', 'm', 'e', 'r'].join(''),
      ['M', 'C', 'U'].join(''),
    ]
    for (const term of forbidden) expect(text).not.toContain(term)
  })
})
