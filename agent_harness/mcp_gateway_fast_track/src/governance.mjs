import { createHash, randomUUID } from 'node:crypto'
import { mkdir, readFile, realpath, rename, writeFile } from 'node:fs/promises'
import { isAbsolute, relative, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

const MAX_INTENT_CHARS = 8_000
const MAX_PATH_CHARS = 1_024
const MAX_ERROR_CHARS = 500

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

const loadDeployment = async (configPath) => {
  const parsed = JSON.parse(await readFile(configPath, 'utf8'))
  if (!Array.isArray(parsed.projectBindings) || parsed.projectBindings.length === 0) {
    throw new Error('Runtime deployment has no project bindings')
  }
  return parsed
}

export const createBridgeRuntimeAccess = ({ bridgeClientPath, deploymentConfigPath }) => {
  let loaded
  let bridge
  const deployment = async () => (loaded ??= await loadDeployment(deploymentConfigPath))
  const module = async () => {
    if (bridge) return bridge
    const namespace = await import(pathToFileURL(bridgeClientPath).href)
    if (typeof namespace.createCodexLocalBridgeModule !== 'function') {
      throw new Error('Existing Runtime bridge factory is unavailable')
    }
    bridge = namespace.createCodexLocalBridgeModule(deploymentConfigPath)
    return bridge
  }

  const resolveProject = async (workspacePath) => {
    const canonical = await realpath(workspacePath)
    const bindings = []
    for (const binding of (await deployment()).projectBindings) {
      const roots = binding.allowedWorkspaceRoots ?? [binding.projectRoot]
      const canonicalRoots = []
      for (const root of roots) {
        canonicalRoots.push(await realpath(root))
      }
      bindings.push({ ...binding, allowedWorkspaceRoots: canonicalRoots })
    }
    return selectProjectBinding(canonical, bindings)
  }

  const portFor = async (workspacePath) => {
    const current = await module()
    return current.createGovernanceHostRuntimePort({ cwd: workspacePath })
  }

  return Object.freeze({
    resolveProject,
    async openTurn(input) {
      return (await portFor(input.workspacePath)).openTurn(input)
    },
    async getStatus(snapshot) {
      return (await portFor(snapshot.workspacePath)).getStatus(snapshot.runtimeId)
    },
  })
}

const statusSummary = (snapshot, runtimeStatus) => {
  const ledger = runtimeStatus?.supervision?.ledger
  const decision = runtimeStatus?.decision
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
      const taskId = requireString('taskId', input.taskId, 160)
      const snapshot = await snapshotStore.get(taskId)
      if (!snapshot) throw new GatewayGovernanceError('TASK_NOT_FOUND', 'No Gateway task snapshot matches taskId')
      const runtimeStatus = await runtimeAccess.getStatus(snapshot)
      runtimeConnected = true
      return statusSummary(snapshot, runtimeStatus)
    },
  })
}

export const governanceToolError = (error) => ({
  status: 'ERROR',
  code: error instanceof GatewayGovernanceError ? error.code : 'RUNTIME_UNAVAILABLE',
  message: boundedError(error),
})
