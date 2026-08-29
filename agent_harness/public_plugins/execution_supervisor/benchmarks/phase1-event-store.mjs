import { mkdir, mkdtemp, rm, stat, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import {
  EXECUTION_EVENT_SCHEMA,
  TASK_SUPERVISION_CONTRACT_SCHEMA,
  createFileExecutionEventStore,
  hashCanonicalJson,
  percentile,
} from '../dist/index.js'

const eventCount = 1_000
const replayLimit = 128
const hashA = 'a'.repeat(64)
const hashB = 'b'.repeat(64)

const contract = {
  schema: TASK_SUPERVISION_CONTRACT_SCHEMA,
  projectId: 'project-synthetic',
  taskId: 'task-synthetic',
  agentId: 'agent-synthetic',
  contextHash: hashA,
  routeHash: hashB,
  projectRevision: 'revision-synthetic-001',
  supervisionLevel: 'AUDIT',
  obligations: [{
    id: 'OBL-SYNTHETIC-001',
    kind: 'REQUIRED_RESOURCE',
    severity: 'MUST',
    sourceRefs: [],
    target: { resourceId: 'resource-synthetic' },
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
}

const binding = {
  requestId: 'request-synthetic',
  runtimeId: 'runtime-synthetic',
  turnId: 'turn-synthetic',
  contract,
}

const eventFor = sequence => {
  const payload = {
    operation: 'synthetic-observation',
    ordinal: sequence,
    summary: `bounded event ${sequence}`,
  }
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
    timestamp: new Date(Date.UTC(2026, 7, 29, 0, 0, sequence)).toISOString(),
    kind: 'TOOL_RESULT',
    payloadHash: hashCanonicalJson(payload),
    payload,
  }
}

const outputIndex = process.argv.indexOf('--output')
const outputPath = outputIndex >= 0 ? process.argv[outputIndex + 1] : undefined
if (outputIndex >= 0 && !outputPath) throw new Error('--output requires a path')

const defaultTempRoot = resolve(import.meta.dirname, '../../../../.tmp/phase1-event-store-benchmark')
const tempRoot = resolve(process.env.PHASE1_TMP_ROOT ?? defaultTempRoot)
await mkdir(tempRoot, { recursive: true })
const runDirectory = await mkdtemp(resolve(tempRoot, 'run-'))
const directory = resolve(runDirectory, 'store')

let store
try {
  const events = Array.from({ length: eventCount }, (_, index) => eventFor(index + 1))
  const heapBefore = process.memoryUsage().heapUsed
  const appendDurationsMicros = []
  const totalStart = process.hrtime.bigint()
  store = await createFileExecutionEventStore({
    directory,
    binding,
    limits: {
      maxEvents: eventCount,
      maxStoreBytes: 32 * 1024 * 1024,
      maxReplayEvents: replayLimit,
    },
  })

  for (const event of events) {
    const start = process.hrtime.bigint()
    const acceptance = await store.append(event)
    appendDurationsMicros.push(Number(process.hrtime.bigint() - start) / 1_000)
    if (acceptance.status !== 'ACCEPTED') {
      throw new Error(`Unexpected append status ${acceptance.status} at ${event.sequence}`)
    }
  }
  const totalWallMillis = Number(process.hrtime.bigint() - totalStart) / 1_000_000

  const replayStart = process.hrtime.bigint()
  const replayed = []
  let after
  let hasMore = true
  let finalCursor = store.cursor
  while (hasMore) {
    const page = await store.replay(after
      ? { after, limit: replayLimit }
      : { limit: replayLimit })
    replayed.push(...page.events)
    after = page.cursor
    finalCursor = page.cursor
    hasMore = page.hasMore
  }
  const replayWallMillis = Number(process.hrtime.bigint() - replayStart) / 1_000_000

  if (replayed.length !== eventCount) throw new Error('Replay count mismatch')
  replayed.forEach((event, index) => {
    if (event.sequence !== index + 1 || event.payloadHash !== events[index].payloadHash) {
      throw new Error(`Replay mismatch at index ${index}`)
    }
  })
  if (finalCursor.sequence !== eventCount || finalCursor.stateHash !== store.cursor.stateHash) {
    throw new Error('Replay final cursor mismatch')
  }

  const manifestBytes = (await stat(resolve(directory, 'manifest.json'))).size
  const eventsBytes = (await stat(resolve(directory, 'events.jsonl'))).size
  const report = {
    schema: 'agent-harness.execution-supervisor-phase1-measurement.v0.1',
    capturedAt: new Date().toISOString(),
    environment: {
      nodeVersion: process.version,
      platform: process.platform,
      architecture: process.arch,
    },
    eventCount,
    replayPageLimit: replayLimit,
    thresholdsFrozen: false,
    measurements: {
      appendP50Micros: percentile(appendDurationsMicros, 0.50),
      appendP95Micros: percentile(appendDurationsMicros, 0.95),
      replayWallMillis,
      total1000EventWallMillis: totalWallMillis,
      persistedBytesPerEvent: (manifestBytes + eventsBytes) / eventCount,
      memoryDeltaBytes: Math.max(0, process.memoryUsage().heapUsed - heapBefore),
    },
    correctness: {
      exactCount: true,
      exactOrder: true,
      exactPayloadHashes: true,
      exactFinalCursor: true,
    },
  }
  for (const [name, value] of Object.entries(report.measurements)) {
    if (!Number.isFinite(value) || value < 0) {
      throw new Error(`Measurement ${name} is not finite and non-negative`)
    }
  }
  const serialized = `${JSON.stringify(report, null, 2)}\n`
  if (outputPath) {
    await mkdir(dirname(resolve(outputPath)), { recursive: true })
    await writeFile(resolve(outputPath), serialized, 'utf8')
  }
  process.stdout.write(serialized)
} finally {
  if (store) await store.close().catch(() => undefined)
  await rm(runDirectory, { recursive: true, force: true })
}
