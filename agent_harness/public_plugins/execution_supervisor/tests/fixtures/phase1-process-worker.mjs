import {
  EXECUTION_EVENT_SCHEMA,
  TASK_SUPERVISION_CONTRACT_SCHEMA,
  createFileExecutionEventStore,
  hashCanonicalJson,
  openFileExecutionEventStore,
} from '../../dist/index.js'

const [mode, directory, suppliedCursorJson] = process.argv.slice(2)
if (!mode || !directory) throw new Error('Usage: phase1-process-worker.mjs <mode> <directory>')

const suppliedCursor = suppliedCursorJson === undefined
  ? undefined
  : JSON.parse(suppliedCursorJson)

const sameCursor = (left, right) =>
  left?.sequence === right?.sequence && left?.stateHash === right?.stateHash

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
const limits = {
  maxEvents: 16,
  maxStoreBytes: 1024 * 1024,
  maxReplayEvents: 8,
}

const eventFor = sequence => {
  const payload = {
    operation: 'cross-process-observation',
    ordinal: sequence,
    summary: `bounded process event ${sequence}`,
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
    eventId: `process-event-${sequence.toString().padStart(3, '0')}`,
    timestamp: new Date(Date.UTC(2026, 7, 29, 1, 0, sequence)).toISOString(),
    kind: 'TOOL_RESULT',
    payloadHash: hashCanonicalJson(payload),
    payload,
  }
}

let store
try {
  if (mode === 'create') {
    store = await createFileExecutionEventStore({ directory, binding, limits })
    for (const sequence of [1, 2]) {
      const result = await store.append(eventFor(sequence))
      if (result.status !== 'ACCEPTED') throw new Error(`Create process rejected ${sequence}`)
    }
    if (store.eventCount !== 2 || store.cursor.sequence !== 2) {
      throw new Error('Create process cursor mismatch')
    }
    process.stdout.write(JSON.stringify({ mode, cursor: store.cursor }))
  } else if (mode === 'continue') {
    store = await openFileExecutionEventStore({ directory, binding })
    if (store.eventCount !== 2 || store.cursor.sequence !== 2) {
      throw new Error('Continue process did not reconstruct sequence 2')
    }
    if (!sameCursor(store.cursor, suppliedCursor)) {
      throw new Error(`Continue process cursor did not exactly match process A: ${JSON.stringify({
        expected: suppliedCursor,
        actual: store.cursor,
      })}`)
    }
    const beforeCursor = store.cursor
    const result = await store.append(eventFor(3))
    if (result.status !== 'ACCEPTED' || store.cursor.sequence !== 3) {
      throw new Error('Continue process did not append sequence 3')
    }
    process.stdout.write(JSON.stringify({ mode, beforeCursor, cursor: store.cursor }))
  } else if (mode === 'replay') {
    store = await openFileExecutionEventStore({ directory, binding })
    if (suppliedCursor === undefined) throw new Error('Replay process requires process A cursor')
    const page = await store.replay({ after: suppliedCursor, limit: 8 })
    const expected = [3]
    const sequences = page.events.map(event => event.sequence)
    if (JSON.stringify(sequences) !== JSON.stringify(expected)) {
      throw new Error(`Replay process order mismatch: ${JSON.stringify(sequences)}`)
    }
    page.events.forEach((event, index) => {
      if (event.payloadHash !== eventFor(event.sequence).payloadHash) {
        throw new Error(`Replay process payload hash mismatch at ${event.sequence}`)
      }
    })
    if (page.hasMore || page.cursor.sequence !== 3 || page.cursor.stateHash !== store.cursor.stateHash) {
      throw new Error('Replay process final cursor mismatch')
    }
    process.stdout.write(JSON.stringify({
      mode,
      afterCursor: suppliedCursor,
      sequences,
      eventCount: store.eventCount,
      cursor: store.cursor,
      runtimeId: store.binding.runtimeId,
      turnId: store.binding.turnId,
    }))
  } else {
    throw new Error(`Unknown mode ${mode}`)
  }
} finally {
  if (store) await store.close()
}
