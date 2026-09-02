import { randomUUID } from 'node:crypto'
import { GatewayGovernanceError } from './governance.mjs'

const TASK_INTENT_SCHEMA = 'et-harness.task-intent.v0.1'
const IDENTIFIER_RE = /^[A-Za-z0-9._:-]{1,96}$/
const MAX_PROJECT_CHARS = 160
const MAX_OBJECTIVE_CHARS = 1600
const MAX_ENTITIES = 24
const MAX_CONSTRAINTS = 24
const MAX_CONSTRAINT_CHARS = 800
const MAX_INTENT_CHARS = 8000
const MAX_FINGERPRINT_CHARS = 128

const clean = (value) => String(value ?? '').trim()
const normalizeProjectName = (value) => clean(value).toLowerCase().replace(/\s+/g, ' ')

const requiredText = (label, value, maxChars) => {
  const normalized = clean(value)
  if (!normalized) throw new GatewayGovernanceError('INVALID_ARGUMENT', `${label} is required`)
  if (normalized.length > maxChars) {
    throw new GatewayGovernanceError('INVALID_ARGUMENT', `${label} exceeds ${maxChars} characters`)
  }
  return normalized
}

const requiredIdentifier = (label, value) => {
  const normalized = requiredText(label, value, 96)
  if (!IDENTIFIER_RE.test(normalized)) {
    throw new GatewayGovernanceError('INVALID_ARGUMENT', `${label} must be a bounded identifier`)
  }
  return normalized
}

export const TASK_INTENT_SCHEMA_ID = TASK_INTENT_SCHEMA

export const projectSelectorMatches = (project, selector) => {
  const needle = normalizeProjectName(selector)
  if (!needle || !project || typeof project !== 'object') return false
  const values = [
    project.projectId,
    project.displayName,
    ...(Array.isArray(project.aliases) ? project.aliases : []),
  ]
  return values.some((value) => normalizeProjectName(value) === needle)
}

export const normalizeTaskIntent = (input) => {
  if (!input || typeof input !== 'object' || Array.isArray(input)) {
    throw new GatewayGovernanceError('INVALID_ARGUMENT', 'taskIntent must be an object')
  }
  if (input.schema !== TASK_INTENT_SCHEMA) {
    throw new GatewayGovernanceError(
      'INVALID_ARGUMENT',
      `taskIntent.schema must be ${TASK_INTENT_SCHEMA}`,
    )
  }
  const taskType = requiredIdentifier('taskIntent.taskType', input.taskType).toUpperCase()
  const objective = requiredText('taskIntent.objective', input.objective, MAX_OBJECTIVE_CHARS)
  if (!Array.isArray(input.entities) || input.entities.length > MAX_ENTITIES) {
    throw new GatewayGovernanceError(
      'INVALID_ARGUMENT',
      `taskIntent.entities must contain 0-${MAX_ENTITIES} items`,
    )
  }
  const entities = input.entities.map((entry, index) => {
    if (!entry || typeof entry !== 'object' || Array.isArray(entry)) {
      throw new GatewayGovernanceError(
        'INVALID_ARGUMENT',
        `taskIntent.entities[${index}] must be an object`,
      )
    }
    return Object.freeze({
      kind: requiredIdentifier(`taskIntent.entities[${index}].kind`, entry.kind).toLowerCase(),
      id: requiredIdentifier(`taskIntent.entities[${index}].id`, entry.id),
    })
  })
  const constraints = input.constraints === undefined
    ? []
    : (() => {
        if (!Array.isArray(input.constraints) || input.constraints.length > MAX_CONSTRAINTS) {
          throw new GatewayGovernanceError(
            'INVALID_ARGUMENT',
            `taskIntent.constraints must contain 0-${MAX_CONSTRAINTS} items`,
          )
        }
        return input.constraints.map((value, index) =>
          requiredText(`taskIntent.constraints[${index}]`, value, MAX_CONSTRAINT_CHARS))
      })()
  return Object.freeze({
    schema: TASK_INTENT_SCHEMA,
    taskType,
    objective,
    entities: Object.freeze(entities),
    constraints: Object.freeze(constraints),
  })
}

export const canonicalTaskText = (taskIntentInput, humanIntent) => {
  const taskIntent = normalizeTaskIntent(taskIntentInput)
  const original = requiredText('intent', humanIntent, MAX_INTENT_CHARS)
  const entityLine = taskIntent.entities.length > 0
    ? taskIntent.entities.map((entry) => `${entry.kind}=${entry.id}`).join('; ')
    : 'none'
  const lines = [
    `Task type: ${taskIntent.taskType}`,
    `Entities: ${entityLine}`,
    `Objective: ${taskIntent.objective}`,
  ]
  if (taskIntent.constraints.length > 0) {
    lines.push(`Constraints: ${taskIntent.constraints.join(' | ')}`)
  }
  lines.push(`Original user request: ${original}`)
  return lines.join('\n')
}

export const taskIntentContract = () => Object.freeze({
  schema: TASK_INTENT_SCHEMA,
  fields: Object.freeze({
    taskType: 'semantic task type chosen by the Agent after project understanding',
    objective: 'concise objective grounded in the human request',
    entities: 'project entities as {kind,id}; use concrete project identifiers',
    constraints: 'optional human constraints; never invent governance policy',
  }),
})

const boundedFingerprint = (value) => value === undefined
  ? undefined
  : requiredText('projectContextFingerprint', value, MAX_FINGERPRINT_CHARS)

const stagedResponse = ({ status, taskId, bootstrap }) => Object.freeze({
  status,
  taskId,
  projectId: bootstrap.projectId,
  displayName: bootstrap.displayName,
  projectContextFingerprint: bootstrap.fingerprint,
  ...(status === 'PROJECT_CONTEXT_REQUIRED'
    ? { architectureBootstrap: bootstrap.architecture }
    : {}),
  taskIntentContract: taskIntentContract(),
})

export const createProjectAdmissionController = ({ baseGovernance, runtimeAccess }) => {
  if (!baseGovernance || typeof baseGovernance.begin !== 'function') {
    throw new Error('Project Admission requires the existing Governance controller')
  }
  if (!runtimeAccess || typeof runtimeAccess.projectBootstrap !== 'function') {
    throw new Error('Project Admission requires Runtime projectBootstrap access')
  }

  return Object.freeze({
    ...baseGovernance,
    async begin(input) {
      const workspacePath = requiredText('workspacePath', input.workspacePath, 1024)
      const project = requiredText('project', input.project, MAX_PROJECT_CHARS)
      const intent = requiredText('intent', input.intent, MAX_INTENT_CHARS)
      const taskId = input.requestedTaskId === undefined
        ? `codex-task-${randomUUID()}`
        : requiredText('requestedTaskId', input.requestedTaskId, 160)
      const suppliedFingerprint = boundedFingerprint(input.projectContextFingerprint)

      // Fingerprint freshness is owned by the current Architecture, never by a
      // Gateway-local cache. projectBootstrap() performs the existing bounded,
      // read-only Architecture refresh without opening Runtime/Ledger/Closure state.
      const bootstrap = await runtimeAccess.projectBootstrap(workspacePath)

      if (!projectSelectorMatches(bootstrap, project)) {
        throw new GatewayGovernanceError(
          'PROJECT_DECLARATION_MISMATCH',
          `Declared project ${project} does not match workspace project ${bootstrap.projectId}`,
        )
      }

      if (suppliedFingerprint !== bootstrap.fingerprint) {
        return stagedResponse({ status: 'PROJECT_CONTEXT_REQUIRED', taskId, bootstrap })
      }

      if (input.taskIntent === undefined) {
        return stagedResponse({ status: 'TASK_INTENT_REQUIRED', taskId, bootstrap })
      }

      const taskIntent = normalizeTaskIntent(input.taskIntent)
      const canonicalIntent = canonicalTaskText(taskIntent, intent)
      const opened = await baseGovernance.begin({
        workspacePath,
        intent: canonicalIntent,
        requestedTaskId: taskId,
      })
      return Object.freeze({
        ...opened,
        humanIntent: intent,
        taskIntent,
        projectContextFingerprint: bootstrap.fingerprint,
      })
    },
  })
}
