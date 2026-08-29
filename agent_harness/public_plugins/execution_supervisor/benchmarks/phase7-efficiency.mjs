#!/usr/bin/env node

import { execFileSync } from 'node:child_process'
import { mkdir, mkdtemp, readFile, rm, stat, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import {
  EXECUTION_EVENT_SCHEMA,
  TASK_SUPERVISION_CONTRACT_SCHEMA,
  createExecutionObligationLedger,
  createFileExecutionEventStore,
  hashCanonicalJson,
  openFileExecutionEventStore,
  percentile,
} from '../dist/index.js'

const EVENT_COUNT = Number.parseInt(process.env.PHASE7_EVENT_COUNT ?? '1000', 10)
const REPLAY_LIMIT = 127
const HASH_A = 'a'.repeat(64)
const HASH_B = 'b'.repeat(64)
const HASH_C = 'c'.repeat(64)

const argumentValue = name => {
  const index = process.argv.indexOf(name)
  return index >= 0 ? process.argv[index + 1] : undefined
}

const finiteNonNegative = (name, value) => {
  if (!Number.isFinite(value) || value < 0) throw new Error(`${name} must be finite and non-negative`)
  return value
}

const round = value => Number(value.toFixed(3))

const sourceRevision = (() => {
  const explicitRevision = process.env.PHASE7_SOURCE_REVISION?.trim()
  if (explicitRevision) return explicitRevision
  try {
    return execFileSync('git', ['rev-parse', 'HEAD'], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim()
  } catch {
    return 'unknown-revision'
  }
})()

const tempRootInput = process.env.PHASE7_TMP_ROOT?.trim()
if (!tempRootInput) throw new Error('PHASE7_TMP_ROOT is required; benchmark state must use an explicit temporary root')
const tempRoot = resolve(tempRootInput)
await mkdir(tempRoot, { recursive: true })
const runRoot = await mkdtemp(resolve(tempRoot, 'execution-supervisor-'))
const storeDirectory = resolve(runRoot, 'store')

const contract = {
  schema: TASK_SUPERVISION_CONTRACT_SCHEMA,
  projectId: 'project-phase7-benchmark',
  taskId: 'task-phase7-benchmark',
  agentId: 'agent-phase7-benchmark',
  contextHash: HASH_A,
  routeHash: HASH_B,
  projectRevision: sourceRevision,
  supervisionLevel: 'AUDIT',
  obligations: [{
    id: 'OBL-READ-PHASE7',
    kind: 'REQUIRED_RESOURCE',
    severity: 'MUST',
    sourceRefs: [],
    target: { resourceId: 'resource-phase7', contentHash: HASH_C },
    satisfaction: {
      acceptedProviderIds: ['provider-phase7'],
      acceptedDispositions: ['FOUND'],
      requireContentHash: true,
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
}

const binding = {
  requestId: 'request-phase7-benchmark',
  runtimeId: 'runtime-phase7-benchmark',
  turnId: 'turn-phase7-benchmark',
  contract,
}

const eventFor = sequence => {
  const receipt = {
    provider: 'provider-phase7',
    resourceId: 'resource-phase7',
    contentHash: HASH_C,
    disposition: 'FOUND',
    purpose: 'Measure the bounded ordinary-read hot path.',
    claimRefs: [`claim-${sequence.toString().padStart(4, '0')}`],
  }
  const payload = { receipt }
  return {
    schema: EXECUTION_EVENT_SCHEMA,
    requestId: binding.requestId,
    runtimeId: binding.runtimeId,
    projectId: contract.projectId,
    taskId: contract.taskId,
    turnId: binding.turnId,
    agentId: contract.agentId,
    contextHash: contract.contextHash,
    sequence,
    eventId: `event-${sequence.toString().padStart(6, '0')}`,
    timestamp: new Date(Date.UTC(2026, 7, 30, 0, 0, sequence)).toISOString(),
    kind: 'RESOURCE_READ',
    payloadHash: hashCanonicalJson(payload),
    payload,
  }
}

let store
let reopened
try {
  store = await createFileExecutionEventStore({
    directory: storeDirectory,
    binding,
    limits: {
      maxEvents: EVENT_COUNT,
      maxStoreBytes: 32 * 1024 * 1024,
      maxReplayEvents: REPLAY_LIMIT,
    },
  })
  const appendMicros = []
  const ledger = await createExecutionObligationLedger({ eventStore: store })
  const ledgerMicros = []
  for (let sequence = 1; sequence <= EVENT_COUNT; sequence += 1) {
    const event = eventFor(sequence)
    const appendStarted = process.hrtime.bigint()
    const acceptance = await store.append(event)
    appendMicros.push(Number(process.hrtime.bigint() - appendStarted) / 1_000)
    if (acceptance.status !== 'ACCEPTED') throw new Error(`event ${sequence} was ${acceptance.status}`)
    const ledgerStarted = process.hrtime.bigint()
    await ledger.synchronize()
    ledgerMicros.push(Number(process.hrtime.bigint() - ledgerStarted) / 1_000)
  }
  const status = ledger.getStatus()
  const projection = status.obligations[0]
  if (projection?.accessCount !== EVENT_COUNT || projection.eventRefs.length !== 1) {
    throw new Error('Repeated-read projection did not compact deterministically')
  }
  await store.close()
  store = undefined

  const replayStarted = process.hrtime.bigint()
  reopened = await openFileExecutionEventStore({ directory: storeDirectory, binding })
  const replayedLedger = await createExecutionObligationLedger({ eventStore: reopened })
  const replayMillis = Number(process.hrtime.bigint() - replayStarted) / 1_000_000
  const replayStatus = replayedLedger.getStatus()
  const exactReplay = JSON.stringify(replayStatus) === JSON.stringify(status)
  if (!exactReplay) throw new Error('Replayed compact projection differs from uninterrupted execution')

  const eventsBytes = (await stat(resolve(storeDirectory, 'events.jsonl'))).size
  const manifestBytes = (await stat(resolve(storeDirectory, 'manifest.json'))).size
  const projectionBytes = Buffer.byteLength(JSON.stringify(projection), 'utf8')
  const contextDelta = {
    cursor: status.cursor,
    obligations: status.obligations,
    pendingObligationIds: status.pendingObligationIds,
    violatedObligationIds: status.violatedObligationIds,
  }
  const contextDeltaBytes = Buffer.byteLength(JSON.stringify(contextDelta), 'utf8')
  const measurements = {
    eventIngestP50Micros: round(percentile(appendMicros, 0.50)),
    eventIngestP95Micros: round(percentile(appendMicros, 0.95)),
    ledgerTransitionP50Micros: round(percentile(ledgerMicros, 0.50)),
    ledgerTransitionP95Micros: round(percentile(ledgerMicros, 0.95)),
    replayMillis: round(replayMillis),
    persistedEventBytes: eventsBytes,
    persistedBytesPerEvent: round((eventsBytes + manifestBytes) / EVENT_COUNT),
    ledgerProjectionBytes: projectionBytes,
    contextDeltaBytes,
  }
  for (const [name, value] of Object.entries(measurements)) finiteNonNegative(name, value)

  const invariants = {
    eventCount: EVENT_COUNT,
    compactedAccessCount: projection.accessCount,
    representativeEventRefCount: projection.eventRefs.length,
    retainedEvidenceRefCount: projection.evidenceRefs.length,
    evidenceRefsTruncated: projection.evidenceRefsTruncated === true,
    exactReplay,
  }
  const runtimePathCounters = {
    measuredBy: 'governance_runtime/tests/supervised-lifecycle.integration.test.ts',
    benchmarkMeasured: false,
    rerouteCount: 0,
    semanticCallCount: 0,
    reflectionCount: 0,
  }

  const sloPath = argumentValue('--slo')
  let slo
  let sloRegressionMessage
  if (sloPath) {
    const profile = JSON.parse(await readFile(resolve(sloPath), 'utf8'))
    if (profile.schema !== 'agent-harness.execution-supervisor-phase7-slo.v0.1') {
      throw new Error('Unsupported Phase 7 SLO profile schema')
    }
    const environmentMatches = process.version.startsWith(profile.environment.nodeVersionPrefix)
      && process.platform === profile.environment.platform
      && process.arch === profile.environment.architecture
    if (!environmentMatches) {
      throw new Error(`SLO environment mismatch: ${process.version}/${process.platform}/${process.arch}`)
    }
    const scenarioMatches = EVENT_COUNT === profile.scenario.eventCount
      && REPLAY_LIMIT === profile.scenario.replayPageLimit
    if (!scenarioMatches) {
      throw new Error(`SLO scenario mismatch: ${EVENT_COUNT} events/${REPLAY_LIMIT} replay limit`)
    }
    const checks = {
      eventIngestP95Micros: measurements.eventIngestP95Micros <= profile.limits.maxEventIngestP95Micros,
      ledgerTransitionP95Micros: measurements.ledgerTransitionP95Micros <= profile.limits.maxLedgerTransitionP95Micros,
      replayMillis: measurements.replayMillis <= profile.limits.maxReplayMillis,
      persistedBytesPerEvent: measurements.persistedBytesPerEvent <= profile.limits.maxPersistedBytesPerEvent,
      ledgerProjectionBytes: measurements.ledgerProjectionBytes <= profile.limits.maxLedgerProjectionBytes,
      contextDeltaBytes: measurements.contextDeltaBytes <= profile.limits.maxContextDeltaBytes,
      exactReplay: invariants.exactReplay,
    }
    slo = {
      profileId: profile.profileId,
      passed: Object.values(checks).every(Boolean),
      checks,
    }
    if (!slo.passed) {
      sloRegressionMessage = `Phase 7 SLO regression: ${JSON.stringify(checks)}`
    }
  }

  const report = {
    schema: 'agent-harness.execution-supervisor-phase7-efficiency-report.v0.1',
    capturedAt: new Date().toISOString(),
    sourceRevision,
    environment: { nodeVersion: process.version, platform: process.platform, architecture: process.arch },
    scenario: { eventCount: EVENT_COUNT, replayPageLimit: REPLAY_LIMIT },
    measurements,
    invariants,
    runtimePathCounters,
    ...(slo ? { slo } : {}),
    notes: [
      'Canonical Event Store receipts remain exact; only the Ledger status projection is compacted.',
      'contextDeltaBytes measures the bounded Supervisor delta supplied to lifecycle/Context integration, not a full project Context frame.',
      'Runtime hot-path counters are not measured by this Store/Ledger latency benchmark; the referenced real Runtime integration test enforces that boundary.',
    ],
  }
  const serialized = `${JSON.stringify(report, null, 2)}\n`
  const outputPath = argumentValue('--output')
  if (outputPath) {
    const resolved = resolve(outputPath)
    await mkdir(dirname(resolved), { recursive: true })
    await writeFile(resolved, serialized, 'utf8')
  }
  process.stdout.write(serialized)
  if (sloRegressionMessage) throw new Error(sloRegressionMessage)
} finally {
  if (store) await store.close().catch(() => undefined)
  if (reopened) await reopened.close().catch(() => undefined)
  await rm(runRoot, { recursive: true, force: true })
}
