import { describe, expect, it } from 'vitest'
import {
  EXECUTION_EVENT_SCHEMA,
  TASK_SUPERVISION_CONTRACT_SCHEMA,
  createPhase0PerformanceBaseline,
  hashCanonicalJson,
  summarizeDurationsMicros,
  validateExecutionEventEnvelope,
  validatePerformanceBaselineReport,
  validateTaskSupervisionContract,
  type TaskSupervisionContractV01,
} from '../src/index.js'

const HASH_A = 'a'.repeat(64)
const HASH_B = 'b'.repeat(64)

const contractFixture = (): TaskSupervisionContractV01 => ({
  schema: TASK_SUPERVISION_CONTRACT_SCHEMA,
  projectId: 'project-performance',
  taskId: 'task-performance',
  agentId: 'agent-performance',
  contextHash: HASH_A,
  routeHash: HASH_B,
  supervisionLevel: 'AUDIT',
  obligations: [{
    id: 'OBL-001',
    kind: 'REQUIRED_RESOURCE',
    severity: 'MUST',
    sourceRefs: [],
    target: { resourceId: 'resource-primary' },
    satisfaction: { disposition: 'FOUND' },
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

const eventFixture = () => {
  const payload = {
    provider: 'repository-provider',
    resourceId: 'resource-primary',
    disposition: 'FOUND',
    contentHash: HASH_A,
  }
  return {
    schema: EXECUTION_EVENT_SCHEMA,
    requestId: 'request-performance',
    runtimeId: 'runtime-performance',
    projectId: 'project-performance',
    taskId: 'task-performance',
    turnId: 'turn-performance',
    agentId: 'agent-performance',
    contextHash: HASH_A,
    sequence: 1,
    eventId: 'event-performance',
    timestamp: '2026-08-28T00:00:00.000Z',
    kind: 'RESOURCE_READ',
    payloadHash: hashCanonicalJson(payload),
    payload,
  } as const
}

const measure = (action: () => void, iterations: number): number[] => {
  const values: number[] = []
  for (let index = 0; index < iterations; index += 1) {
    const start = process.hrtime.bigint()
    action()
    values.push(Number(process.hrtime.bigint() - start) / 1000)
  }
  return values
}

describe('Execution Supervisor Phase 0 performance baseline', () => {
  it('captures measurements without freezing numeric SLOs', () => {
    const contract = contractFixture()
    const event = eventFixture()
    for (let index = 0; index < 100; index += 1) {
      validateTaskSupervisionContract(contract)
      validateExecutionEventEnvelope(event)
    }
    const contractDurations = measure(() => {
      const result = validateTaskSupervisionContract(contract)
      if (!result.valid) throw new Error('contract fixture became invalid')
    }, 500)
    const eventDurations = measure(() => {
      const result = validateExecutionEventEnvelope(event)
      if (!result.valid) throw new Error('event fixture became invalid')
    }, 500)

    const report = createPhase0PerformanceBaseline({
      baselineId: 'phase0-test-baseline',
      capturedAt: '2026-08-28T00:00:00.000Z',
      sourceRevision: 'test-revision',
      nodeVersion: process.version,
      platform: process.platform,
      architecture: process.arch,
      samples: [
        summarizeDurationsMicros({
          scenario: 'task-contract-validation',
          warmupIterations: 100,
          inputBytes: Buffer.byteLength(JSON.stringify(contract), 'utf8'),
          durationsMicros: contractDurations,
        }),
        summarizeDurationsMicros({
          scenario: 'execution-event-validation',
          warmupIterations: 100,
          inputBytes: Buffer.byteLength(JSON.stringify(event), 'utf8'),
          durationsMicros: eventDurations,
        }),
      ],
      notes: ['This test verifies report integrity; CI publishes the environment-specific baseline artifact.'],
    })
    const result = validatePerformanceBaselineReport(report)
    expect(result.valid).toBe(true)
    expect(report.thresholdsFrozen).toBe(false)
    expect(report.invariants).toMatchObject({
      noSemanticCallOnHotPath: true,
      noFullRerouteForOrdinaryRead: true,
      maxUnifiedReflectionsPerTurn: 1,
    })
    expect(report.samples).toHaveLength(2)
  })
})
