#!/usr/bin/env node

import { execFileSync } from 'node:child_process'
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import {
  EXECUTION_EVENT_SCHEMA,
  TASK_SUPERVISION_CONTRACT_SCHEMA,
  createPhase0PerformanceBaseline,
  hashCanonicalJson,
  summarizeDurationsMicros,
  validateExecutionEventEnvelope,
  validatePerformanceBaselineReport,
  validateTaskSupervisionContract,
} from '../dist/index.js'

const HASH_A = 'a'.repeat(64)
const HASH_B = 'b'.repeat(64)
const WARMUP = Number.parseInt(process.env.EXECUTION_SUPERVISOR_BENCHMARK_WARMUP ?? '2000', 10)
const SAMPLES = Number.parseInt(process.env.EXECUTION_SUPERVISOR_BENCHMARK_SAMPLES ?? '10000', 10)

const argumentValue = name => {
  const index = process.argv.indexOf(name)
  return index >= 0 ? process.argv[index + 1] : undefined
}

const sourceRevision = process.env.GITHUB_SHA?.trim() || (() => {
  try {
    return execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
  } catch {
    return 'unknown-revision'
  }
})()

const contract = {
  schema: TASK_SUPERVISION_CONTRACT_SCHEMA,
  projectId: 'project-baseline',
  taskId: 'task-baseline',
  agentId: 'agent-baseline',
  contextHash: HASH_A,
  routeHash: HASH_B,
  projectRevision: sourceRevision,
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
      id: 'OBL-REFLECT-001',
      kind: 'REFLECTION',
      severity: 'MUST',
      sourceRefs: [],
      target: { required: true },
      satisfaction: { reflectionStatus: 'COMPLETE' },
      dependencies: ['OBL-OUTPUT-001'],
    },
    {
      id: 'OBL-CLOSE-001',
      kind: 'CLOSURE',
      severity: 'MUST',
      sourceRefs: [],
      target: { required: true },
      satisfaction: { closureStatus: 'COMPLETE' },
      dependencies: ['OBL-REFLECT-001'],
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
}

const payload = {
  provider: 'repository-provider',
  resourceId: 'resource-primary',
  disposition: 'FOUND',
  contentHash: HASH_A,
  purpose: 'Resolve a required resource obligation.',
  claimRefs: ['claim://primary'],
}
const event = {
  schema: EXECUTION_EVENT_SCHEMA,
  requestId: 'request-baseline',
  runtimeId: 'runtime-baseline',
  projectId: 'project-baseline',
  taskId: 'task-baseline',
  turnId: 'turn-baseline',
  agentId: 'agent-baseline',
  contextHash: HASH_A,
  sequence: 1,
  eventId: 'event-baseline',
  timestamp: new Date().toISOString(),
  kind: 'RESOURCE_READ',
  payloadHash: hashCanonicalJson(payload),
  payload,
}

const benchmark = (action, warmup, samples) => {
  for (let index = 0; index < warmup; index += 1) action()
  const durations = []
  for (let index = 0; index < samples; index += 1) {
    const start = process.hrtime.bigint()
    action()
    durations.push(Number(process.hrtime.bigint() - start) / 1000)
  }
  return durations
}

const contractDurations = benchmark(() => {
  const result = validateTaskSupervisionContract(contract)
  if (!result.valid) throw new Error(JSON.stringify(result.issues))
}, WARMUP, SAMPLES)
const eventDurations = benchmark(() => {
  const result = validateExecutionEventEnvelope(event)
  if (!result.valid) throw new Error(JSON.stringify(result.issues))
}, WARMUP, SAMPLES)

const report = createPhase0PerformanceBaseline({
  baselineId: `phase0-${sourceRevision.slice(0, 12) || 'unknown'}`,
  capturedAt: new Date().toISOString(),
  sourceRevision,
  nodeVersion: process.version,
  platform: process.platform,
  architecture: process.arch,
  samples: [
    summarizeDurationsMicros({
      scenario: 'task-contract-validation',
      warmupIterations: WARMUP,
      inputBytes: Buffer.byteLength(JSON.stringify(contract), 'utf8'),
      durationsMicros: contractDurations,
    }),
    summarizeDurationsMicros({
      scenario: 'execution-event-validation',
      warmupIterations: WARMUP,
      inputBytes: Buffer.byteLength(JSON.stringify(event), 'utf8'),
      durationsMicros: eventDurations,
    }),
  ],
  notes: [
    'Phase 0 records measurements only; numeric SLOs remain unfrozen.',
    'The measured hot path is deterministic contract validation and performs no semantic call, route refresh or Context mutation.',
  ],
})
const validated = validatePerformanceBaselineReport(report)
if (!validated.valid) throw new Error(JSON.stringify(validated.issues, null, 2))

const output = argumentValue('--output')
if (output) {
  const path = resolve(output)
  mkdirSync(dirname(path), { recursive: true })
  writeFileSync(path, `${JSON.stringify(report, null, 2)}\n`, 'utf8')
}
process.stdout.write(`${JSON.stringify(report, null, 2)}\n`)
