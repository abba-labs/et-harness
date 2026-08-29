import { randomUUID } from 'node:crypto'
import { mkdir, readFile, rm } from 'node:fs/promises'
import { resolve } from 'node:path'
import {
  EXECUTION_EVENT_SCHEMA,
  TASK_SUPERVISION_CONTRACT_SCHEMA,
  hashCanonicalJson,
  type ExecutionEventEnvelopeV01,
  type ExecutionEventStoreBindingV01,
  type ExecutionEventStoreLimitsV01,
  type JsonRecord,
  type TaskSupervisionContractV01,
} from '../../src/index.js'

export const HASH_A = 'a'.repeat(64)
export const HASH_B = 'b'.repeat(64)
export const HASH_C = 'c'.repeat(64)

export const syntheticContract = (
  overrides: Partial<TaskSupervisionContractV01> = {},
): TaskSupervisionContractV01 => ({
  schema: TASK_SUPERVISION_CONTRACT_SCHEMA,
  projectId: 'project-synthetic',
  taskId: 'task-synthetic',
  agentId: 'agent-synthetic',
  contextHash: HASH_A,
  routeHash: HASH_B,
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
  ...overrides,
})

export const syntheticBinding = (
  overrides: Partial<ExecutionEventStoreBindingV01> = {},
): ExecutionEventStoreBindingV01 => ({
  requestId: 'request-synthetic',
  runtimeId: 'runtime-synthetic',
  turnId: 'turn-synthetic',
  contract: syntheticContract(),
  ...overrides,
})

export const SYNTHETIC_LIMITS: ExecutionEventStoreLimitsV01 = {
  maxEvents: 2_000,
  maxStoreBytes: 32 * 1024 * 1024,
  maxReplayEvents: 200,
}

type EventOverrides = Partial<ExecutionEventEnvelopeV01> & {
  readonly payload?: JsonRecord
}

export const syntheticEvent = (
  sequence: number,
  overrides: EventOverrides = {},
): ExecutionEventEnvelopeV01 => {
  const payload = overrides.payload ?? {
    operation: 'synthetic-observation',
    ordinal: sequence,
    summary: `bounded event ${sequence}`,
  }
  const event: ExecutionEventEnvelopeV01 = {
    schema: EXECUTION_EVENT_SCHEMA,
    requestId: 'request-synthetic',
    runtimeId: 'runtime-synthetic',
    projectId: 'project-synthetic',
    taskId: 'task-synthetic',
    turnId: 'turn-synthetic',
    agentId: 'agent-synthetic',
    contextHash: HASH_A,
    sequence,
    eventId: `event-${sequence.toString().padStart(6, '0')}`,
    timestamp: new Date(Date.UTC(2026, 7, 29, 0, 0, sequence)).toISOString(),
    kind: 'TOOL_RESULT',
    payloadHash: hashCanonicalJson(payload),
    payload,
    ...overrides,
  }
  if (overrides.payload !== undefined && overrides.payloadHash === undefined) {
    return { ...event, payloadHash: hashCanonicalJson(overrides.payload) }
  }
  return event
}

const TEMP_ROOT = resolve(import.meta.dirname, '../../../../../.tmp/phase1-event-store')

export const createSyntheticTempDirectory = async (
  prefix = 'case-',
): Promise<string> => {
  await mkdir(TEMP_ROOT, { recursive: true })
  return resolve(TEMP_ROOT, `${prefix}${randomUUID()}`)
}

export const removeSyntheticTempDirectory = async (
  directory: string,
): Promise<void> => {
  const resolved = resolve(directory)
  if (!resolved.startsWith(`${TEMP_ROOT}\\`) && !resolved.startsWith(`${TEMP_ROOT}/`)) {
    throw new Error(`Refusing to remove a directory outside the synthetic temp root: ${resolved}`)
  }
  await rm(resolved, { recursive: true, force: true })
}

export const storeSnapshot = async (directory: string): Promise<{
  readonly manifest: Buffer
  readonly events: Buffer
}> => ({
  manifest: await readFile(resolve(directory, 'manifest.json')),
  events: await readFile(resolve(directory, 'events.jsonl')),
})

export const expectSha256 = (value: string): void => {
  if (!/^[0-9a-f]{64}$/.test(value)) {
    throw new Error(`Expected a lowercase SHA-256 digest, received ${value}`)
  }
}
