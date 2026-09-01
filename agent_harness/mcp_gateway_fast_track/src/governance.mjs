import { createHash, randomUUID } from 'node:crypto'
import { mkdir, readFile, rename, writeFile } from 'node:fs/promises'
import { isAbsolute, relative, resolve } from 'node:path'

const MAX_INTENT_CHARS = 8_000
const MAX_PATH_CHARS = 1_024
const MAX_ERROR_CHARS = 500
const MAX_TEXT_CHARS = 8_000
const MAX_REF_CHARS = 2_048
const MAX_REFS = 64

export class GatewayGovernanceError extends Error {
  constructor(code, message) {
    super(message)
    this.name = 'GatewayGovernanceError'
    this.code = code
  }
}

const boundedError = (error) =>
  (error instanceof Error ? error.message : String(error))
    .replace(/\s+/g, ' ')
    .slice(0, MAX_ERROR_CHARS)

const hash = (value) => createHash('sha256').update(value).digest('hex')

const inside = (candidate, root) => {
  const relation = relative(root, candidate)
  return relation === '' || (!relation.startsWith('..') && !isAbsolute(relation))
}

export const selectProjectBinding = (workspacePath, bindings) => {
  const matches = []
  for (const binding of bindings) {
    const roots = binding.allowedWorkspaceRoots ?? [binding.projectRoot]
    for (const root of roots) {
      if (inside(workspacePath, root)) matches.push({ binding, canonicalRoot: root })
    }
  }
  if (matches.length === 0) {
    throw new GatewayGovernanceError('PROJECT_NOT_FOUND', 'No configured ET Harness project matches workspacePath')
  }
  matches.sort((left, right) => right.canonicalRoot.length - left.canonicalRoot.length)
  const longest = matches[0].canonicalRoot.length
  const best = matches.filter((item) => item.canonicalRoot.length === longest)
  const projectIds = [...new Set(best.map((item) => item.binding.projectId))]
  if (projectIds.length !== 1) {
    throw new GatewayGovernanceError('PROJECT_AMBIGUOUS', 'workspacePath matches multiple configured projects')
  }
  return { workspacePath, projectId: projectIds[0] }
}

const requireString = (label, value, maxChars) => {
  if (typeof value !== 'string' || !value.trim()) {
    throw new GatewayGovernanceError('INVALID_ARGUMENT', `${label} is required`)
  }
  const normalized = value.trim()
  if (normalized.length > maxChars) {
    throw new GatewayGovernanceError('INVALID_ARGUMENT', `${label} exceeds ${maxChars} characters`)
  }
  return normalized
}

const optionalString = (label, value, maxChars) => value === undefined
  ? undefined
  : requireString(label, value, maxChars)

const stringArray = (label, value, { required = false } = {}) => {
  if (value === undefined && !required) return undefined
  if (!Array.isArray(value) || (required && value.length === 0) || value.length > MAX_REFS) {
    throw new GatewayGovernanceError(
      'INVALID_ARGUMENT',
      `${label} must contain ${required ? '1-' : '0-'}${MAX_REFS} strings`,
    )
  }
  return value.map((item, index) => requireString(`${label}[${index}]`, item, MAX_REF_CHARS))
}

const requireRecord = (label, value) => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new GatewayGovernanceError('INVALID_ARGUMENT', `${label} must be an object`)
  }
  return value
}

const parseJsonItem = (item, label) => {
  if (!item) throw new GatewayGovernanceError('CONTEXT_INCOMPLETE', `${label} is missing`)
  try {
    return JSON.parse(item.content)
  } catch {
    throw new GatewayGovernanceError('CONTEXT_INCOMPLETE', `${label} is not valid JSON`)
  }
}

export const parseRenderedInlineItems = (text) => {
  const items = []
  const pattern = /^## \[inline\] (\S+) ([^\r\n]+)\r?\nProvenance:[^\r\n]*(?:\r?\nWarnings:[^\r\n]*)?\r?\n\r?\n([\s\S]*?)(?=\r?\n## \[|\r?\nPending Code Gate Reviews:|(?![\s\S]))/gm
  for (const match of text.matchAll(pattern)) {
    items.push({ id: match[1], title: match[2].trim(), content: match[3].trim() })
  }
  return items
}

const parseScope = (content) => {
  const result = { read: [], allowed: [], protected: [] }
  let section
  let subsection
  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim()
    if (line === 'read_scope:') {
      section = 'read'
      subsection = undefined
      continue
    }
    if (line === 'write_scope:') {
      section = 'write'
      subsection = undefined
      continue
    }
    if (section === 'write' && (line === 'allowed:' || line === 'protected:')) {
      subsection = line.slice(0, -1)
      continue
    }
    const item = line.match(/^-\s+(.+)$/)?.[1]?.trim()
    if (!item) continue
    if (section === 'read') result.read.push(item)
    if (section === 'write' && subsection === 'allowed') result.allowed.push(item)
    if (section === 'write' && subsection === 'protected') result.protected.push(item)
  }
  return result
}

const parseValidation = (content) => {
  const validations = []
  for (const line of content.split(/\r?\n/)) {
    const match = line.match(/^-\s+([^:]+):\s*(.*?)\s*\|\s*command=(.+)$/)
    if (!match) continue
    validations.push({ id: match[1].trim(), summary: match[2].trim(), command: match[3].trim() })
  }
  return validations
}

const itemEnding = (items, suffix) => items.find((item) => item.id.endsWith(`:${suffix}`))

export const projectContextFromOpenTurn = (opened) => {
  const context = opened?.context
  if (!context || typeof context.text !== 'string') {
    throw new GatewayGovernanceError('CONTEXT_INCOMPLETE', 'Runtime returned no rendered Context')
  }
  const contributions = Array.isArray(context.contextContributions)
    ? context.contextContributions
    : []
  if (contributions.length === 0) {
    throw new GatewayGovernanceError(
      'CONTEXT_CONTRIBUTOR_UNAVAILABLE',
      'Runtime returned no Project Context contribution',
    )
  }

  const items = parseRenderedInlineItems(context.text)
  const core = parseJsonItem(itemEnding(items, 'compiled-task-context-core'), 'compiled Task Context identity')
  const navigation = parseJsonItem(
    itemEnding(items, 'compiled-task-context-navigation'),
    'compiled Task Context navigation',
  )
  const scopeItem = itemEnding(items, 'scope')
  const validationItem = itemEnding(items, 'validation')
  if (!scopeItem || !validationItem) {
    throw new GatewayGovernanceError('CONTEXT_INCOMPLETE', 'Runtime Context has no scope or validation contract')
  }
  const scope = parseScope(scopeItem.content)
  const validation = parseValidation(validationItem.content)
  const mustRead = Array.isArray(navigation.must_read) ? navigation.must_read : []
  const ruleOwners = Array.isArray(navigation.rule_owners) ? navigation.rule_owners : []
  if (mustRead.length === 0 || ruleOwners.length === 0 || scope.allowed.length === 0 || validation.length === 0) {
    throw new GatewayGovernanceError(
      'CONTEXT_INCOMPLETE',
      'Runtime Context is missing required navigation, scope, or validation data',
    )
  }

  const projectRevision = contributions
    .map((item) => item?.supervision?.projectRevision)
    .find((value) => typeof value === 'string' && value)
  const contextRevision = typeof core.fingerprint === 'string' ? core.fingerprint : contributions[0]?.fingerprint
  if (!projectRevision || !contextRevision) {
    throw new GatewayGovernanceError('CONTEXT_INCOMPLETE', 'Runtime Context has no project or context revision')
  }

  return Object.freeze({
    projectId: opened.projectId,
    projectRevision,
    contextRevision,
    mustRead,
    ruleOwners,
    readScope: scope.read,
    writeScope: { allowed: scope.allowed, protected: scope.protected },
    validation,
    route: context.route,
    contributionReceipts: contributions.map((item) => ({
      providerId: item.providerId,
      contributionId: item.contributionId,
      fingerprint: item.fingerprint,
    })),
    warnings: Array.isArray(context.warnings) ? context.warnings : [],
  })
}

const snapshotFileName = (taskId) => `${hash(taskId)}.json`

export const createFileSnapshotStore = (root) => {
  if (!isAbsolute(root)) throw new Error('taskSnapshotRoot must be absolute')
  const resolvedRoot = resolve(root)
  const pathFor = (taskId) => resolve(resolvedRoot, snapshotFileName(taskId))

  return Object.freeze({
    async get(taskId) {
      try {
        const value = JSON.parse(await readFile(pathFor(taskId), 'utf8'))
        return value?.taskId === taskId ? value : undefined
      } catch (error) {
        if (error?.code === 'ENOENT') return undefined
        throw error
      }
    },
    async put(snapshot) {
      await mkdir(resolvedRoot, { recursive: true })
      const destination = pathFor(snapshot.taskId)
      const temporary = `${destination}.${process.pid}.${randomUUID()}.tmp`
      await writeFile(temporary, `${JSON.stringify(snapshot)}\n`, { encoding: 'utf8', flag: 'wx' })
      await rename(temporary, destination)
    },
  })
}

const statusSummary = (snapshot, runtimeStatus) => {
  const ledger = runtimeStatus?.supervision?.ledger
  const decision = runtimeStatus?.supervision?.decision
  return {
    status: 'ACTIVE',
    taskId: snapshot.taskId,
    runtimeId: snapshot.runtimeId,
    turnId: snapshot.turnId,
    projectId: snapshot.projectId,
    projectRevision: snapshot.projectRevision,
    contextRevision: snapshot.contextRevision,
    runtimeDecision: decision?.status ?? 'IN_PROGRESS',
    pendingObligationIds: ledger?.pendingObligationIds ?? [],
    satisfiedObligationIds: ledger?.satisfiedObligationIds ?? [],
    violatedObligationIds: ledger?.violatedObligationIds ?? [],
  }
}

const requireSnapshot = async (snapshotStore, input) => {
  const taskId = requireString('taskId', input.taskId, 160)
  const snapshot = await snapshotStore.get(taskId)
  if (!snapshot) throw new GatewayGovernanceError('TASK_NOT_FOUND', 'No Gateway task snapshot matches taskId')
  return snapshot
}

const workObservation = (snapshot, input) => {
  const kind = requireString('kind', input.kind, 40)
  const common = {
    kind,
    runtimeId: snapshot.runtimeId,
    turnId: snapshot.turnId,
  }
  if (kind === 'tool-result') {
    return {
      ...common,
      name: requireString('name', input.name, 256),
      ...(input.arguments === undefined ? {} : { arguments: input.arguments }),
      ...(input.isError === undefined ? {} : { isError: Boolean(input.isError) }),
      ...(optionalString('eventRef', input.eventRef, MAX_REF_CHARS) === undefined
        ? {}
        : { eventRef: optionalString('eventRef', input.eventRef, MAX_REF_CHARS) }),
      ...(stringArray('resourceRefs', input.resourceRefs) === undefined
        ? {}
        : { resourceRefs: stringArray('resourceRefs', input.resourceRefs) }),
      ...(optionalString('summary', input.summary, MAX_TEXT_CHARS) === undefined
        ? {}
        : { summary: optionalString('summary', input.summary, MAX_TEXT_CHARS) }),
    }
  }
  if (kind === 'resource-touch') {
    return {
      ...common,
      resourceRefs: stringArray('resourceRefs', input.resourceRefs, { required: true }),
      ...(optionalString('summary', input.summary, MAX_TEXT_CHARS) === undefined
        ? {}
        : { summary: optionalString('summary', input.summary, MAX_TEXT_CHARS) }),
    }
  }
  if (kind === 'assistant-message' || kind === 'user-message') {
    return {
      ...common,
      messageRefs: stringArray('messageRefs', input.messageRefs, { required: true }),
      ...(optionalString('text', input.text, MAX_TEXT_CHARS) === undefined
        ? {}
        : { text: optionalString('text', input.text, MAX_TEXT_CHARS) }),
    }
  }
  throw new GatewayGovernanceError('INVALID_ARGUMENT', 'kind is not a supported Runtime observation kind')
}

const observationSummary = (result) => ({
  status: 'OBSERVED',
  observationId: result?.observation?.observationId,
  observationKind: result?.observation?.kind,
  journalStatus: result?.journal?.status,
  knowledgeCaptureMode: result?.knowledgeDecision?.captureMode,
  knowledgeConsultationMode: result?.knowledgeDecision?.consultationMode,
})

const actionPreflight = (snapshot, input) => {
  const effect = requireRecord('effect', input.effect)
  if (effect.kind !== 'READ_ONLY' && effect.kind !== 'MUTATION') {
    throw new GatewayGovernanceError('INVALID_ARGUMENT', 'effect.kind must be READ_ONLY or MUTATION')
  }
  let normalizedEffect = { kind: 'READ_ONLY' }
  if (effect.kind === 'MUTATION') {
    const intent = requireRecord('effect.intent', effect.intent)
    normalizedEffect = {
      kind: 'MUTATION',
      intent: {
        resourceId: requireString('effect.intent.resourceId', intent.resourceId, MAX_REF_CHARS),
        ...(optionalString('effect.intent.path', intent.path, MAX_PATH_CHARS) === undefined
          ? {}
          : { path: optionalString('effect.intent.path', intent.path, MAX_PATH_CHARS) }),
        action: requireString('effect.intent.action', intent.action, 40),
      },
    }
  }
  return {
    runtimeId: snapshot.runtimeId,
    turnId: snapshot.turnId,
    name: requireString('name', input.name, 256),
    ...(input.arguments === undefined ? {} : { arguments: input.arguments }),
    ...(optionalString('eventRef', input.eventRef, MAX_REF_CHARS) === undefined
      ? {}
      : { eventRef: optionalString('eventRef', input.eventRef, MAX_REF_CHARS) }),
    effect: normalizedEffect,
  }
}

const closeInput = (snapshot, input) => ({
  runtimeId: snapshot.runtimeId,
  turnId: snapshot.turnId,
  ...(stringArray('assistantMessageRefs', input.assistantMessageRefs) === undefined
    ? {}
    : { assistantMessageRefs: stringArray('assistantMessageRefs', input.assistantMessageRefs) }),
  ...(stringArray('publicCandidateRefs', input.publicCandidateRefs) === undefined
    ? {}
    : { publicCandidateRefs: stringArray('publicCandidateRefs', input.publicCandidateRefs) }),
  ...(stringArray('projectCandidateRefs', input.projectCandidateRefs) === undefined
    ? {}
    : { projectCandidateRefs: stringArray('projectCandidateRefs', input.projectCandidateRefs) }),
  ...(input.semanticReflection === undefined
    ? {}
    : { semanticReflection: requireRecord('semanticReflection', input.semanticReflection) }),
})

const closeSummary = (result) => ({
  status: result?.closure?.status ?? 'UNKNOWN',
  runtimeId: result?.runtimeId,
  taskId: result?.taskId,
  turnId: result?.turnId,
  reflection: {
    providerId: result?.reflection?.providerId,
    createdAt: result?.reflection?.createdAt,
    journalRef: result?.reflection?.journalRef,
  },
  closure: {
    status: result?.closure?.status,
    attemptId: result?.closure?.attemptId,
    receiptRef: result?.closure?.receiptRef,
  },
  knowledge: {
    captureMode: result?.knowledgeDecision?.captureMode,
    consultationMode: result?.knowledgeDecision?.consultationMode,
    verificationCount: result?.knowledgeVerifications?.length ?? 0,
    promotionCount: result?.knowledgePromotions?.length ?? 0,
    verificationWarnings: result?.knowledgeVerificationWarnings ?? [],
    promotionWarnings: result?.knowledgePromotionWarnings ?? [],
  },
  supervision: {
    decision: result?.supervision?.decision?.status,
    pendingObligationIds: result?.supervision?.ledger?.pendingObligationIds ?? [],
    satisfiedObligationIds: result?.supervision?.ledger?.satisfiedObligationIds ?? [],
    violatedObligationIds: result?.supervision?.ledger?.violatedObligationIds ?? [],
  },
})

export const createGovernanceController = ({ runtimeAccess, snapshotStore, projects = [] }) => {
  let runtimeConnected = false

  return Object.freeze({
    health: () => ({ runtimeConnected, projects: [...projects] }),
    async begin(input) {
      const workspacePath = requireString('workspacePath', input.workspacePath, MAX_PATH_CHARS)
      const intent = requireString('intent', input.intent, MAX_INTENT_CHARS)
      const requestedTaskId = input.requestedTaskId === undefined
        ? undefined
        : requireString('requestedTaskId', input.requestedTaskId, 160)
      const project = await runtimeAccess.resolveProject(workspacePath)
      const taskId = requestedTaskId ?? `codex-task-${randomUUID()}`
      const intentHash = hash(JSON.stringify({
        workspacePath: project.workspacePath,
        projectId: project.projectId,
        intent,
      }))
      const existing = await snapshotStore.get(taskId)
      if (existing) {
        if (existing.intentHash !== intentHash) {
          throw new GatewayGovernanceError(
            'TASK_ID_CONFLICT',
            'requestedTaskId already exists with different workspace or intent',
          )
        }
        return { ...existing, idempotentReplay: true }
      }

      const runtimeId = `codex-runtime-${randomUUID()}`
      const turnId = `codex-turn-${randomUUID()}`
      const opened = await runtimeAccess.openTurn({
        runtimeId,
        turnId,
        taskId,
        projectId: project.projectId,
        workspacePath: project.workspacePath,
        taskText: intent,
      })
      runtimeConnected = true
      const context = projectContextFromOpenTurn(opened)
      const snapshot = {
        schema: 'et-harness.gateway-task-snapshot.v0.1',
        taskId,
        runtimeId,
        turnId,
        workspacePath: project.workspacePath,
        projectId: context.projectId,
        projectRevision: context.projectRevision,
        contextRevision: context.contextRevision,
        intentHash,
        createdAt: new Date().toISOString(),
        context,
      }
      await snapshotStore.put(snapshot)
      return { ...snapshot, idempotentReplay: false }
    },
    async status(input) {
      const snapshot = await requireSnapshot(snapshotStore, input)
      const runtimeStatus = await runtimeAccess.getStatus(snapshot)
      runtimeConnected = true
      return statusSummary(snapshot, runtimeStatus)
    },
    async observe(input) {
      const snapshot = await requireSnapshot(snapshotStore, input)
      const result = await runtimeAccess.observeWork(snapshot, workObservation(snapshot, input))
      runtimeConnected = true
      return observationSummary(result)
    },
    async preflight(input) {
      const snapshot = await requireSnapshot(snapshotStore, input)
      const result = await runtimeAccess.preflightAction(snapshot, actionPreflight(snapshot, input))
      runtimeConnected = true
      return {
        status: result.allowed ? 'ALLOWED' : 'BLOCKED',
        allowed: result.allowed,
        ...(result.reason ? { reason: result.reason.slice(0, MAX_ERROR_CHARS) } : {}),
      }
    },
    async complete(input) {
      const snapshot = await requireSnapshot(snapshotStore, input)
      const result = await runtimeAccess.closeTurn(snapshot, closeInput(snapshot, input))
      runtimeConnected = true
      return closeSummary(result)
    },
  })
}

export const governanceToolError = (error) => ({
  status: 'ERROR',
  code: error instanceof GatewayGovernanceError ? error.code : 'RUNTIME_UNAVAILABLE',
  message: boundedError(error),
})
