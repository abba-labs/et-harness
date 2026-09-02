import { createHash } from 'node:crypto'
import { mkdir, readFile, realpath, stat } from 'node:fs/promises'
import { isAbsolute, relative, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
import { Context } from '@deepseek-ai/cordis'
import GovernanceCatalogService from '@agent-harness/governance-core'
import { ProjectManagerService, loadProjectManifestFile } from '@agent-harness/project-manager'
import { ArchitectureNavigatorService } from '@agent-harness/architecture-navigator'
import { RuleManagerService } from '@agent-harness/rule-manager'
import { EvidenceStateManagerService } from '@agent-harness/evidence-state-manager'
import { KnowledgeManagerService, KnowledgeValidationPolicyService } from '@agent-harness/knowledge-manager'
import { GateManagerService } from '@agent-harness/gate-manager'
import { ContextBuilderService, ContextManagementService } from '@agent-harness/context-builder'
import { ExperienceMemoryManagerService } from '@agent-harness/experience-memory-manager'
import { AgentGovernanceKernelService } from '@agent-harness/agent-governance-kernel'
import { AgentGovernanceClosureAdaptersService } from '@agent-harness/agent-governance-closure-adapters'
import { AutoGovernanceEngineService } from '@agent-harness/auto-governance-engine'
import {
  ScopeSafeGovernanceRuntimeService,
  compileGovernanceProjectSupervisionContractV01,
  createGovernanceHostRuntimePortV01,
  type GovernanceHostRuntimePortV01,
  type GovernanceOpenTurnResult,
} from '@agent-harness/governance-runtime'
import {
  HOST_CAPABILITY_CONTRACT_SCHEMA,
  createFileExecutionEventStore,
  openFileExecutionEventStore,
  type ExecutionEventStoreBindingV01,
  type ExecutionEventStoreV01,
  type HostCapabilityContractV01,
} from '@agent-harness/execution-supervisor'
import { buildProjectBootstrap } from './project-bootstrap.js'

interface DisposableFiber { dispose(): Promise<void> | void }

interface ProjectBinding {
  projectId: string
  projectRoot: string
  projectManifestPath: string
  projectPluginEntryPath: string
  projectPluginReadinessService: string
  allowedWorkspaceRoots: string[]
}

interface RuntimeDeploymentConfig {
  schema: 'et-harness.pure-mcp-runtime-deployment.v1'
  environmentRoot: string
  stateRoot: string
  eventStoreRoot: string
  projectBindings: ProjectBinding[]
}

interface TrustedValidationSpanInput {
  cwd: string
  runtimeId: string
  turnId: string
  requestEventId: string
  requestManifest: Record<string, unknown>
  validationEventId: string
  validationReceipt: Record<string, unknown>
  responseEventId: string
  responseManifest: Record<string, unknown>
}

interface SupervisedTurnSnapshotInput {
  cwd: string
  runtimeId: string
  turnId: string
  taskId: string
  projectId: string
  projectRevision?: string
}

interface AbortSupervisedTurnInput extends SupervisedTurnSnapshotInput {
  reason: string
}

const tick = (): Promise<void> => new Promise(resolveTick => setTimeout(resolveTick, 0))
const storeToken = (runtimeId: string, turnId: string): string =>
  createHash('sha256').update(`${runtimeId}\0${turnId}`).digest('hex')
const MAX_STORE_MANIFEST_BYTES = 2 * 1024 * 1024
const MAX_ABORT_REASON_CHARS = 1_200

const PURE_MCP_AUDIT_CAPABILITIES: HostCapabilityContractV01 = Object.freeze({
  schema: HOST_CAPABILITY_CONTRACT_SCHEMA,
  hostId: 'pure-mcp-local',
  adapterId: 'agent-harness.pure-mcp-gateway.v0.1',
  capabilities: Object.freeze({
    supportsPreflight: true,
    supportsToolInterception: false,
    supportsStableToolEventId: false,
    supportsResourceHash: false,
    supportsMessageRef: false,
    supportsCrossProcessResume: false,
  }),
})

const inside = (candidate: string, root: string): boolean => {
  const relation = relative(root, candidate)
  return relation === '' || (!relation.startsWith('..') && !isAbsolute(relation))
}

const loadDeployment = async (path: string): Promise<RuntimeDeploymentConfig> => {
  const parsed = JSON.parse(await readFile(path, 'utf8')) as Partial<RuntimeDeploymentConfig>
  if (parsed.schema !== 'et-harness.pure-mcp-runtime-deployment.v1') {
    throw new Error('Pure MCP Runtime deployment schema is invalid')
  }
  for (const field of ['environmentRoot', 'stateRoot', 'eventStoreRoot'] as const) {
    if (typeof parsed[field] !== 'string' || !isAbsolute(parsed[field])) {
      throw new Error(`${field} must be an absolute path`)
    }
  }
  if (!Array.isArray(parsed.projectBindings) || parsed.projectBindings.length === 0) {
    throw new Error('Pure MCP Runtime deployment has no project bindings')
  }
  for (const binding of parsed.projectBindings) {
    if (!binding || typeof binding.projectId !== 'string' || !binding.projectId) {
      throw new Error('Pure MCP Runtime project binding has no projectId')
    }
    for (const field of ['projectRoot', 'projectManifestPath', 'projectPluginEntryPath'] as const) {
      if (typeof binding[field] !== 'string' || !isAbsolute(binding[field])) {
        throw new Error(`Project binding ${field} must be an absolute path`)
      }
    }
    if (typeof binding.projectPluginReadinessService !== 'string'
        || !binding.projectPluginReadinessService) {
      throw new Error('Project binding projectPluginReadinessService is required')
    }
    if (!Array.isArray(binding.allowedWorkspaceRoots) || binding.allowedWorkspaceRoots.length === 0
        || binding.allowedWorkspaceRoots.some(root => typeof root !== 'string' || !isAbsolute(root))) {
      throw new Error('Project binding allowedWorkspaceRoots must contain absolute paths')
    }
  }
  return parsed as RuntimeDeploymentConfig
}

const selectProjectBinding = async (
  config: RuntimeDeploymentConfig,
  workspacePath: string,
): Promise<{ workspacePath: string, projectId: string, binding: ProjectBinding }> => {
  const canonicalWorkspace = await realpath(workspacePath)
  const matches: Array<{ binding: ProjectBinding, root: string }> = []
  for (const binding of config.projectBindings) {
    for (const root of binding.allowedWorkspaceRoots) {
      const canonicalRoot = await realpath(root)
      if (inside(canonicalWorkspace, canonicalRoot)) matches.push({ binding, root: canonicalRoot })
    }
  }
  if (matches.length === 0) throw new Error('Workspace is outside the configured project roots')
  matches.sort((left, right) => right.root.length - left.root.length)
  const strongest = matches.filter(match => match.root.length === matches[0].root.length)
  if (new Set(strongest.map(match => match.binding.projectId)).size !== 1) {
    throw new Error('Workspace matches multiple equally specific project bindings')
  }
  return {
    workspacePath: canonicalWorkspace,
    projectId: strongest[0].binding.projectId,
    binding: strongest[0].binding,
  }
}

class PureMcpRuntimeOwner {
  private readonly context = new Context()
  private readonly fibers: DisposableFiber[] = []
  private readonly stores = new Map<string, ExecutionEventStoreV01>()
  private readonly opened = new Map<string, GovernanceOpenTurnResult>()
  private readonly recoveryJobs = new Map<string, Promise<void>>()
  private runtime?: ScopeSafeGovernanceRuntimeService
  private port?: GovernanceHostRuntimePortV01

  constructor(private readonly config: RuntimeDeploymentConfig) {}

  async start(): Promise<void> {
    process.env.AGENT_HARNESS_STATE_ROOT = this.config.stateRoot
    process.env.AGENT_HARNESS_METRICS_ROOT = resolve(this.config.environmentRoot, 'state', 'metrics')
    await mkdir(this.config.eventStoreRoot, { recursive: true })
    await this.composeRuntime()
  }

  runtimePort(): GovernanceHostRuntimePortV01 {
    if (!this.port) throw new Error('Pure MCP Runtime owner is not ready')
    return this.port
  }

  async projectBootstrap(workspacePath: string) {
    const selected = await selectProjectBinding(this.config, workspacePath)
    const projectManager = this.context.get('projectManager')
    const architectureNavigator = this.context.get('architectureNavigator')
    if (!projectManager || !architectureNavigator) {
      throw new Error('Project Architecture bootstrap services are not ready')
    }
    const project = projectManager.getProjectContext(selected.projectId)
    if (!project) throw new Error(`Project disappeared during Architecture bootstrap: ${selected.projectId}`)

    // Project understanding is a bounded read-only bootstrap. Refresh only the
    // Architecture index so a stale Agent context cannot silently survive a
    // project-map change. No task, Ledger, Event Store or Closure state is opened.
    architectureNavigator.refreshProject(project.projectId)
    return buildProjectBootstrap(project, architectureNavigator)
  }

  async ingestTrustedValidationSpan(input: TrustedValidationSpanInput) {
    if (!this.runtime) throw new Error('Pure MCP Runtime owner is not ready')
    await selectProjectBinding(this.config, input.cwd)

    // Queue all three events synchronously on the Runtime ingest tail so no
    // unrelated Host event can interleave inside the persisted trusted span.
    const request = this.runtime.ingestExecutionEvent({
      runtimeId: input.runtimeId,
      turnId: input.turnId,
      eventId: input.requestEventId,
      kind: 'USER_MESSAGE',
      payload: { requestManifest: input.requestManifest },
    })
    const validation = this.runtime.ingestExecutionEvent({
      runtimeId: input.runtimeId,
      turnId: input.turnId,
      eventId: input.validationEventId,
      kind: 'VALIDATION_RESULT',
      payload: { receipt: input.validationReceipt },
    })
    const response = this.runtime.ingestExecutionEvent({
      runtimeId: input.runtimeId,
      turnId: input.turnId,
      eventId: input.responseEventId,
      kind: 'ASSISTANT_MESSAGE',
      payload: { responseManifest: input.responseManifest },
    })
    const [requestResult, validationResult, responseResult] = await Promise.all([
      request,
      validation,
      response,
    ])
    for (const [label, result] of [
      ['request', requestResult],
      ['validation', validationResult],
      ['response', responseResult],
    ] as const) {
      if (result.acceptance.status === 'REJECTED') {
        throw new Error(`Trusted validation ${label} event was rejected: ${result.acceptance.reasons.join('; ')}`)
      }
    }
    return {
      request: requestResult,
      validation: validationResult,
      response: responseResult,
    }
  }

  async ensureSupervisedTurn(input: SupervisedTurnSnapshotInput): Promise<void> {
    if (!this.runtime) throw new Error('Pure MCP Runtime owner is not ready')
    const selected = await selectProjectBinding(this.config, input.cwd)
    if (selected.projectId !== input.projectId) {
      throw new Error('Persisted Gateway task projectId does not match the configured workspace')
    }
    const key = `${input.runtimeId}::${input.turnId}`
    if (this.stores.has(key)) return
    const existing = this.recoveryJobs.get(key)
    if (existing) return existing

    const recovery = this.recoverSupervisedTurn(input, selected.projectId, key)
    this.recoveryJobs.set(key, recovery)
    try {
      await recovery
    } finally {
      this.recoveryJobs.delete(key)
    }
  }

  async abortSupervisedTurn(input: AbortSupervisedTurnInput) {
    if (!this.runtime) throw new Error('Pure MCP Runtime owner is not ready')
    const selected = await selectProjectBinding(this.config, input.cwd)
    if (selected.projectId !== input.projectId) {
      throw new Error('Abort projectId does not match the configured workspace')
    }
    const reason = input.reason.trim().slice(0, MAX_ABORT_REASON_CHARS)
    if (!reason) throw new Error('Abort reason cannot be empty')
    const kernel = this.context.get('agentGovernanceKernel')
    const contextManager = this.context.get('contextManager')
    if (!kernel || !contextManager) throw new Error('Runtime lifecycle compensation services are not ready')

    let journalStatus = 'ABSENT'
    const existingJournal = kernel.getTurn(input.taskId, input.turnId)
    if (existingJournal) {
      if (existingJournal.status === 'OPEN') {
        journalStatus = kernel.abortTurn(input.taskId, input.turnId, { reason }).status
      } else if (existingJournal.status === 'ABORTED') {
        journalStatus = existingJournal.status
      } else {
        throw new Error(`Turn ${input.turnId} cannot be compensated from ${existingJournal.status}`)
      }
    }

    let contextStatus = 'ABSENT'
    let contextStateVersion: number | undefined
    try {
      const existingContext = contextManager.getTask(input.projectId, input.taskId)
      const compensated = existingContext.session.status === 'ABORTED'
        ? existingContext
        : contextManager.abortTask(
          input.projectId,
          input.taskId,
          input.turnId,
          reason,
          existingJournal ? [`governance-journal://task/${input.taskId}/turn/${input.turnId}`] : [],
        )
      contextStatus = compensated.session.status
      contextStateVersion = compensated.stateVersion
    } catch (error) {
      if (!(error instanceof Error) || !error.message.includes('Context task 不存在')) throw error
    }

    const key = `${input.runtimeId}::${input.turnId}`
    const store = this.stores.get(key)
    if (store) await store.close()
    this.stores.delete(key)
    this.opened.delete(key)
    this.runtime.releaseAbortedRuntimeSession(input.runtimeId, input.turnId)
    return {
      status: 'ABORTED' as const,
      runtimeId: input.runtimeId,
      taskId: input.taskId,
      turnId: input.turnId,
      journalStatus,
      contextStatus,
      ...(contextStateVersion === undefined ? {} : { contextStateVersion }),
    }
  }

  async stop(): Promise<void> {
    await Promise.allSettled(this.recoveryJobs.values())
    this.recoveryJobs.clear()
    for (const store of this.stores.values()) await store.close()
    this.stores.clear()
    this.opened.clear()
    for (const fiber of this.fibers.reverse()) await fiber.dispose()
    this.fibers.length = 0
  }

  private async composeRuntime(): Promise<void> {
    this.fibers.push(this.context.plugin(GovernanceCatalogService) as DisposableFiber)
    await tick()
    const addServices = async (deps: readonly string[], services: readonly unknown[]): Promise<void> => {
      const fiber = this.context.inject([...deps], scoped => {
        for (const service of services) scoped.plugin(service as never, undefined as never)
      }) as DisposableFiber
      this.fibers.push(fiber)
      await tick()
    }
    await addServices(['governanceCatalog'], [ProjectManagerService, AgentGovernanceKernelService])
    await addServices(['governanceCatalog', 'projectManager'], [
      ArchitectureNavigatorService,
      RuleManagerService,
      EvidenceStateManagerService,
      KnowledgeManagerService,
      KnowledgeValidationPolicyService,
    ])
    await addServices(['governanceCatalog', 'projectManager', 'evidenceStateManager'], [GateManagerService])
    await addServices([
      'governanceCatalog', 'projectManager', 'architectureNavigator', 'ruleManager',
      'knowledgeManager', 'knowledgeValidationPolicy', 'gateManager', 'evidenceStateManager',
    ], [ContextBuilderService, ContextManagementService])
    await addServices([
      'governanceCatalog', 'projectManager', 'knowledgeManager',
      'knowledgeValidationPolicy', 'evidenceStateManager',
    ], [ExperienceMemoryManagerService])
    await addServices([
      'governanceCatalog', 'agentGovernanceKernel', 'contextManager', 'knowledgeManager',
      'experienceMemoryManager', 'evidenceStateManager', 'gateManager',
    ], [AgentGovernanceClosureAdaptersService])
    await addServices([
      'governanceCatalog', 'projectManager', 'architectureNavigator', 'ruleManager',
      'knowledgeManager', 'gateManager', 'evidenceStateManager', 'contextBuilder', 'contextManager',
    ], [AutoGovernanceEngineService])
    await addServices([
      'governanceCatalog', 'agentGovernanceKernel', 'agentGovernanceClosureAdapters',
      'autoGovernanceEngine', 'knowledgeManager', 'knowledgeValidationPolicy',
    ], [ScopeSafeGovernanceRuntimeService])

    for (let attempt = 0; attempt < 40 && !this.context.get('governanceRuntime'); attempt += 1) {
      await tick()
    }
    const runtime = this.context.get('governanceRuntime')
    const projectManager = this.context.get('projectManager')
    if (!runtime || !projectManager) throw new Error('Governance Runtime composition did not become ready')

    for (const binding of this.config.projectBindings) {
      const manifest = loadProjectManifestFile(binding.projectManifestPath)
      if (manifest.project.id !== binding.projectId) {
        throw new Error(`Configured projectId does not match manifest: ${binding.projectId}`)
      }
      this.fibers.push({ dispose: projectManager.registerProject(manifest, binding.projectRoot) })
      const details = await stat(binding.projectPluginEntryPath)
      if (!details.isFile() || details.size > 16 * 1024 * 1024) {
        throw new Error(`Project Plugin entry is not a bounded file: ${binding.projectPluginEntryPath}`)
      }
      const namespace = await import(pathToFileURL(binding.projectPluginEntryPath).href) as Record<string, unknown>
      const plugin = namespace.default ?? namespace
      if ((typeof plugin !== 'function' && (typeof plugin !== 'object' || plugin === null))
          || (typeof plugin === 'object'
            && typeof (plugin as Record<string, unknown>).apply !== 'function')) {
        throw new Error(`Project Plugin entry does not export a Cordis plugin: ${binding.projectPluginEntryPath}`)
      }
      this.fibers.push(this.context.plugin(plugin as never, undefined as never) as DisposableFiber)
      for (let attempt = 0;
        attempt < 40 && !this.context.get(binding.projectPluginReadinessService);
        attempt += 1) {
        await tick()
      }
      if (!this.context.get(binding.projectPluginReadinessService)) {
        throw new Error(
          `Project Plugin service did not become ready: ${binding.projectPluginReadinessService}`,
        )
      }
    }

    this.runtime = runtime as ScopeSafeGovernanceRuntimeService
    this.port = createGovernanceHostRuntimePortV01(runtime, {
      openSupervisedTurn: input => this.openSupervisedTurn(input),
    })
  }

  private async openSupervisedTurn(
    input: Parameters<GovernanceHostRuntimePortV01['openTurn']>[0],
  ): Promise<GovernanceOpenTurnResult> {
    if (!this.runtime) throw new Error('Pure MCP Runtime owner is not ready')
    if (!input.workspacePath) throw new Error('Runtime Turn workspace is required')
    const selected = await selectProjectBinding(this.config, input.workspacePath)
    if (input.projectId && input.projectId !== selected.projectId) {
      throw new Error('Runtime Turn projectId does not match the configured workspace')
    }
    const key = `${input.runtimeId}::${input.turnId}`
    const existing = this.opened.get(key)
    if (existing) return existing

    const opened = await this.runtime.openTurn({ ...input, projectId: selected.projectId })
    const contract = compileGovernanceProjectSupervisionContractV01({
      projectId: opened.projectId,
      taskId: opened.taskId,
      agentId: opened.actorId,
      context: opened.context,
      supervisionLevel: 'AUDIT',
    })
    const directory = resolve(this.config.eventStoreRoot, storeToken(input.runtimeId, input.turnId))
    let store: ExecutionEventStoreV01 | undefined
    try {
      store = await createFileExecutionEventStore({
        directory,
        binding: {
          requestId: `pure-mcp-request:${storeToken(input.runtimeId, input.turnId).slice(0, 32)}`,
          runtimeId: input.runtimeId,
          turnId: input.turnId,
          contract,
        },
        limits: {
          maxEvents: 10_000,
          maxStoreBytes: 64 * 1024 * 1024,
          maxReplayEvents: 250,
        },
      })
      await this.runtime.bindSupervisedTurn({
        runtimeId: input.runtimeId,
        eventStore: store,
        hostCapabilities: PURE_MCP_AUDIT_CAPABILITIES,
      })
      const taskInput = await this.runtime.ingestExecutionEvent({
        runtimeId: input.runtimeId,
        turnId: input.turnId,
        eventId: `mcp-task-input-${createHash('sha256').update(input.taskText).digest('hex').slice(0, 32)}`,
        kind: 'USER_MESSAGE',
        payload: { text: input.taskText },
      })
      if (taskInput.acceptance.status === 'REJECTED') {
        throw new Error(`Durable task input was rejected: ${taskInput.acceptance.reasons.join('; ')}`)
      }
      this.stores.set(key, store)
      this.opened.set(key, opened)
      return opened
    } catch (error) {
      if (store) await store.close()
      throw error
    }
  }

  private async recoverSupervisedTurn(
    input: SupervisedTurnSnapshotInput,
    selectedProjectId: string,
    key: string,
  ): Promise<void> {
    if (!this.runtime) throw new Error('Pure MCP Runtime owner is not ready')
    const directory = resolve(this.config.eventStoreRoot, storeToken(input.runtimeId, input.turnId))
    const manifestPath = resolve(directory, 'manifest.json')
    const details = await stat(manifestPath)
    if (!details.isFile() || details.size > MAX_STORE_MANIFEST_BYTES) {
      throw new Error('Execution Event Store manifest is not a bounded file')
    }
    const manifest = JSON.parse(await readFile(manifestPath, 'utf8')) as {
      binding?: ExecutionEventStoreBindingV01
    }
    const binding = manifest.binding
    if (!binding || binding.runtimeId !== input.runtimeId || binding.turnId !== input.turnId) {
      throw new Error('Execution Event Store identity does not match the persisted Gateway task')
    }
    if (binding.contract.projectId !== selectedProjectId
        || binding.contract.projectId !== input.projectId
        || binding.contract.taskId !== input.taskId
        || binding.contract.agentId !== input.runtimeId
        || binding.contract.projectRevision !== input.projectRevision) {
      throw new Error('Execution Event Store contract does not match the persisted Gateway task')
    }

    const store = await openFileExecutionEventStore({ directory, binding })
    try {
      await this.runtime.rehydrateSupervisedTurn({
        runtimeId: input.runtimeId,
        eventStore: store,
        hostCapabilities: PURE_MCP_AUDIT_CAPABILITIES,
      })
      this.stores.set(key, store)
    } catch (error) {
      await store.close()
      throw error
    }
  }
}

export const createPureMcpRuntimeModule = (deploymentConfigPath: string) => {
  let configPromise: Promise<RuntimeDeploymentConfig> | undefined
  let ownerPromise: Promise<PureMcpRuntimeOwner> | undefined
  const config = () => configPromise ??= loadDeployment(deploymentConfigPath)
  const owner = () => ownerPromise ??= (async () => {
    const value = new PureMcpRuntimeOwner(await config())
    await value.start()
    return value
  })()

  return Object.freeze({
    async resolveProject(workspacePath: string) {
      const selected = await selectProjectBinding(await config(), workspacePath)
      return { workspacePath: selected.workspacePath, projectId: selected.projectId }
    },
    async projectBootstrap(workspacePath: string) {
      const selected = await selectProjectBinding(await config(), workspacePath)
      return (await owner()).projectBootstrap(selected.workspacePath)
    },
    async createGovernanceHostRuntimePort(input: { cwd: string }) {
      await selectProjectBinding(await config(), input.cwd)
      return (await owner()).runtimePort()
    },
    async ingestTrustedValidationSpan(input: TrustedValidationSpanInput) {
      await selectProjectBinding(await config(), input.cwd)
      return (await owner()).ingestTrustedValidationSpan(input)
    },
    async ensureSupervisedTurn(input: SupervisedTurnSnapshotInput) {
      await selectProjectBinding(await config(), input.cwd)
      return (await owner()).ensureSupervisedTurn(input)
    },
    async abortTurn(input: AbortSupervisedTurnInput) {
      await selectProjectBinding(await config(), input.cwd)
      return (await owner()).abortSupervisedTurn(input)
    },
    async close() {
      if (ownerPromise) await (await ownerPromise).stop()
    },
  })
}
