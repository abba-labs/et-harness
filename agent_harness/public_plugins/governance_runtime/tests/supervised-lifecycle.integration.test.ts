import { randomUUID } from 'node:crypto'
import { mkdir, rm, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { Context } from '@deepseek-ai/cordis'
import GovernanceCatalogService from '@agent-harness/governance-core'
import { ProjectManagerService } from '@agent-harness/project-manager'
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
import GovernanceRuntimeService from '../src/service.js'
import {
  EXTERNAL_AGENT_REQUEST_MANIFEST_SCHEMA,
  EXTERNAL_AGENT_RESPONSE_MANIFEST_SCHEMA,
  EXECUTION_EVENT_SCHEMA,
  TASK_SUPERVISION_CONTRACT_SCHEMA,
  createFileExecutionEventStore,
  hashCanonicalJson,
  openFileExecutionEventStore,
  sha256Hex,
  type ExecutionEventStoreV01,
  type ExecutionEventEnvelopeV01,
  type JsonRecord,
  type TaskSupervisionContractV01,
} from '@agent-harness/execution-supervisor'
import { afterEach, describe, expect, it } from 'vitest'

const MODULE_IDS = [
  'context-closure', 'knowledge-closure', 'experience-memory-closure', 'architecture-closure',
  'rules-closure', 'evidence-state-closure', 'working-set-closure', 'obligation-gate-reconcile',
] as const
const tempRoot = resolve(import.meta.dirname, '../../../../../.tmp/phase5-runtime-integration')
const cleanup: string[] = []
const tick = () => new Promise(resolveTick => setTimeout(resolveTick, 0))

afterEach(async () => {
  for (const path of cleanup.splice(0)) {
    if (!resolve(path).startsWith(`${tempRoot}/`) && !resolve(path).startsWith(`${tempRoot}\\`)) {
      throw new Error(`Refusing cleanup outside Phase 5 temp root: ${path}`)
    }
    await rm(path, { recursive: true, force: true })
  }
})

const writeProject = async (root: string): Promise<void> => {
  for (const directory of ['architecture', 'rules', 'knowledge', 'gates']) {
    await mkdir(resolve(root, directory), { recursive: true })
  }
  await writeFile(resolve(root, 'project.marker'), 'synthetic\n')
  await writeFile(resolve(root, 'architecture/00_INDEX.md'), `---
interface: project-resource-index-v0.1
resource: architecture
standard: architecture-v0.1
files:
  - id: A010
    file: 010_runtime.md
    title: Runtime Architecture
    summary: supervised runtime lifecycle
    aliases: [runtime, supervision]
---
`)
  await writeFile(resolve(root, 'architecture/010_runtime.md'), `# [A010] Runtime Architecture
## [A010.010] Supervised Runtime
Role: common supervised runtime
Boundary: lifecycle closure stays in the public runtime
Resources: source/runtime/
`)
  await writeFile(resolve(root, 'rules/00_INDEX.md'), `---
interface: project-resource-index-v0.1
resource: rules
standard: rule-v0.1
files:
  - id: R010
    file: 010_runtime.md
    title: Runtime Rules
    summary: supervised runtime constraints
    aliases: [runtime, supervision]
---
`)
  await writeFile(resolve(root, 'rules/010_runtime.md'), `# [R010] Runtime Rules
## [R010.010] Closure Admission
Level: MUST
When: supervised runtime lifecycle
Rule: Completion requires the common closure path.
Refs: [A010.010]
`)
  await writeFile(resolve(root, 'knowledge/TAXONOMY.yaml'), `standard: knowledge-library-v0.2
categories:
  - id: C010
    title: Runtime
    summary: runtime facts
`)
  await writeFile(resolve(root, 'knowledge/001_runtime.md'), `# [K001] Runtime
## [K001.001] Common Closure
Status: VALIDATED
Category: C010
Fact: The public runtime owns lifecycle admission.
Provenance: PROJECT-BASELINE
Tags: [runtime]
`)
  await writeFile(resolve(root, 'gates/00_INDEX.md'), `---
interface: project-resource-index-v0.1
resource: gates
standard: gate-v0.1
files: []
---
`)
}

const manifest = {
  contract_version: '0.1',
  project: { id: 'project-1', name: 'Phase 5 Synthetic', type: 'test' },
  root: { markers: ['project.marker'] },
  resources: {
    architecture: { path: 'architecture/', standard: 'architecture-v0.1' },
    rules: { path: 'rules/', standard: 'rule-v0.1' },
    knowledge: { path: 'knowledge/', standard: 'knowledge-v0.1' },
    gates: { path: 'gates/', standard: 'gate-v0.1' },
  },
  adapters: {},
}

const startRuntime = async (projectRoot: string) => {
  const ctx = new Context()
  const fibers: Array<{ dispose(): Promise<void> | void }> = []
  fibers.push(ctx.plugin(GovernanceCatalogService) as { dispose(): Promise<void> | void })
  await tick()
  const addServices = async (deps: readonly string[], services: readonly unknown[]) => {
    const fiber = ctx.inject([...deps], scoped => {
      for (const service of services) scoped.plugin(service as never)
    })
    fibers.push(fiber as { dispose(): Promise<void> | void })
    await tick()
  }
  await addServices(['governanceCatalog'], [ProjectManagerService, AgentGovernanceKernelService])
  await addServices(['governanceCatalog', 'projectManager'], [
    ArchitectureNavigatorService, RuleManagerService, EvidenceStateManagerService,
    KnowledgeManagerService, KnowledgeValidationPolicyService,
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
  ], [GovernanceRuntimeService])
  for (let retry = 0; retry < 20 && !ctx.get('governanceRuntime'); retry += 1) await tick()
  const projectManager = ctx.get('projectManager')!
  const disposeProject = projectManager.registerProject(manifest as never, projectRoot)
  const runtime = ctx.get('governanceRuntime')
  const kernel = ctx.get('agentGovernanceKernel')
  if (!runtime || !kernel) {
    const names = [
      'governanceCatalog', 'projectManager', 'architectureNavigator', 'ruleManager',
      'evidenceStateManager', 'knowledgeManager', 'gateManager', 'contextManager',
      'experienceMemoryManager', 'agentGovernanceKernel', 'agentGovernanceClosureAdapters',
      'autoGovernanceEngine', 'governanceRuntime',
    ]
    throw new Error(`Real services missing: ${names.filter(name => !ctx.get(name)).join(', ')}`)
  }
  return {
    ctx,
    runtime,
    kernel,
    async dispose() {
      disposeProject()
      for (const fiber of fibers.reverse()) await fiber.dispose()
    },
  }
}

const contractFor = (context: unknown): TaskSupervisionContractV01 => ({
  schema: TASK_SUPERVISION_CONTRACT_SCHEMA,
  projectId: 'project-1', taskId: 'task-1', agentId: 'agent-1',
  contextHash: hashCanonicalJson(context),
  routeHash: hashCanonicalJson((context as { route: unknown }).route),
  supervisionLevel: 'AUDIT', evidencePolicies: [],
  obligations: [
    { id: 'OBL-REFLECTION', kind: 'REFLECTION', severity: 'MUST', sourceRefs: [], target: {}, satisfaction: {} },
    { id: 'OBL-KNOWLEDGE', kind: 'KNOWLEDGE_DECISION', severity: 'MUST', sourceRefs: [], target: {}, satisfaction: {}, dependencies: ['OBL-REFLECTION'] },
    { id: 'OBL-CONTEXT', kind: 'CONTEXT_UPDATE', severity: 'MUST', sourceRefs: [], target: {}, satisfaction: {}, dependencies: ['OBL-KNOWLEDGE'] },
    { id: 'OBL-CLOSURE', kind: 'CLOSURE', severity: 'MUST', sourceRefs: [], target: {}, satisfaction: {}, dependencies: ['OBL-CONTEXT'] },
  ],
  completionPolicy: {
    requireAllMustSatisfied: true, requireNoViolations: true, requireReflection: true,
    requireKnowledgeDecision: true, requireContextUpdate: true, requireClosureReceipt: true,
    allowShouldWarnings: true, requiredClosureModuleIds: MODULE_IDS,
  },
})

const executionEvent = (
  sequence: number,
  kind: ExecutionEventEnvelopeV01['kind'],
  payload: JsonRecord,
): ExecutionEventEnvelopeV01 => ({
  schema: EXECUTION_EVENT_SCHEMA,
  requestId: 'request-1', runtimeId: 'runtime-1', projectId: 'project-1', taskId: 'task-1',
  turnId: 'turn-1', agentId: 'agent-1', contextHash: '', sequence,
  eventId: `event-${sequence}`, timestamp: `2026-08-29T00:00:0${sequence}.000Z`, kind,
  payloadHash: hashCanonicalJson(payload), payload,
})

const none = () => ({ scopeDecision: 'NONE' as const, rationale: 'No durable change.', candidates: [] })

describe('Governance Runtime real supervised lifecycle', () => {
  it('runs READY through one real Reflection, 8/8 Closure, COMPLETE and clean finalized rehydrate', async () => {
    const caseRoot = resolve(tempRoot, randomUUID())
    cleanup.push(caseRoot)
    const projectRoot = resolve(caseRoot, 'project')
    const stateRoot = resolve(caseRoot, 'state')
    const storeRoot = resolve(caseRoot, 'event-store')
    await mkdir(projectRoot, { recursive: true })
    await writeProject(projectRoot)
    process.env.AGENT_HARNESS_STATE_ROOT = stateRoot

    const first = await startRuntime(projectRoot)
    let semanticCalls = 0
    const taskText = 'Supervised runtime lifecycle integration'
    const opened = await first.runtime.openTurn({
      runtimeId: 'runtime-1', actorId: 'agent-1', taskId: 'task-1', turnId: 'turn-1',
      taskText, projectId: 'project-1', workspacePath: projectRoot,
      semanticExecutor: {
        executorId: 'integration-semantic',
        reflect(request) {
          semanticCalls += 1
          const trustedProjection = request.turnObservations.find(item =>
            item.sourceName?.startsWith('trusted-execution-event-store:'))
          expect(trustedProjection?.text).toContain(taskText)
          expect(trustedProjection?.text).toContain('Lifecycle work is ready for governed closure.')
          return {
            contractVersion: '0.1', taskId: request.taskId, turnId: request.turnId,
            context: { progress: 'closed', decisions: [], confirmed: [], assumptions: [], openIssues: [], next: [], touchedRefs: [] },
            knowledge: none(), experience: none(), architecture: none(), rules: none(), evidence: none(),
            workingSet: { keep: [], add: [], remove: [] },
            obligations: { opened: [], resolved: [], unchanged: [] },
          }
        },
      },
    })
    const contract = contractFor(opened.context)
    const store = await createFileExecutionEventStore({
      directory: storeRoot,
      binding: { requestId: 'request-1', runtimeId: 'runtime-1', turnId: 'turn-1', contract },
      limits: { maxEvents: 100, maxStoreBytes: 2_000_000, maxReplayEvents: 20 },
    })
    let failFinalizationOnce = true
    const failingFinalizationStore: ExecutionEventStoreV01 = {
      get binding() { return store.binding },
      get limits() { return store.limits },
      get cursor() { return store.cursor },
      get eventCount() { return store.eventCount },
      get finalization() { return store.finalization },
      append: event => store.append(event),
      replay: request => store.replay(request),
      finalize: finalization => {
        if (failFinalizationOnce) {
          failFinalizationOnce = false
          throw new Error('synthetic finalization interruption')
        }
        return store.finalize(finalization)
      },
      close: () => store.close(),
    }
    await first.runtime.bindSupervisedTurn({ runtimeId: 'runtime-1', eventStore: failingFinalizationStore })
    const userMessageId = 'message-user-1'
    const assistantMessageId = 'message-assistant-1'
    const requestManifest = {
      schema: EXTERNAL_AGENT_REQUEST_MANIFEST_SCHEMA,
      requestId: 'request-1', runtimeId: 'runtime-1', projectId: 'project-1', taskId: 'task-1',
      turnId: 'turn-1', agentId: 'agent-1', contextHash: contract.contextHash,
      contractHash: hashCanonicalJson(contract), expectedHostId: 'host-1',
      expectedProviderId: 'provider-1', expectedModelId: 'model-1',
      userMessage: { messageId: userMessageId, content: taskText, contentHash: sha256Hex(taskText) },
      issuedAt: '2026-08-29T00:00:01.000Z',
    }
    const responseManifest = {
      schema: EXTERNAL_AGENT_RESPONSE_MANIFEST_SCHEMA,
      requestManifestHash: hashCanonicalJson(requestManifest),
      requestId: 'request-1', runtimeId: 'runtime-1', projectId: 'project-1', taskId: 'task-1',
      turnId: 'turn-1', agentId: 'agent-1', contextHash: contract.contextHash,
      responseId: 'response-1', actualHostId: 'host-1', actualProviderId: 'provider-1',
      actualModelId: 'model-1', actualAgentId: 'agent-1',
      assistantMessage: {
        messageId: assistantMessageId,
        content: 'Lifecycle work is ready for governed closure.',
        contentHash: sha256Hex('Lifecycle work is ready for governed closure.'),
      },
      claims: [], receiptRefs: [], completedAt: '2026-08-29T00:00:02.000Z',
    }
    await store.append({
      ...executionEvent(1, 'USER_MESSAGE', { requestManifest }),
      eventId: userMessageId, contextHash: contract.contextHash,
    })
    await store.append({
      ...executionEvent(2, 'ASSISTANT_MESSAGE', { responseManifest }),
      eventId: assistantMessageId, contextHash: contract.contextHash,
    })
    await store.append({
      ...executionEvent(3, 'TASK_END_REQUEST', { requestedBy: 'agent-1' }),
      contextHash: contract.contextHash,
    })
    expect(semanticCalls).toBe(0)
    expect(first.runtime.completeTask('runtime-1')).toMatchObject({ status: 'BLOCKED' })

    const concurrentCloseA = first.runtime.closeTurn({ runtimeId: 'runtime-1', turnId: 'turn-1' })
    const concurrentCloseB = first.runtime.closeTurn({ runtimeId: 'runtime-1', turnId: 'turn-1' })
    await expect(Promise.all([concurrentCloseA, concurrentCloseB]))
      .rejects.toThrow('synthetic finalization interruption')
    expect(semanticCalls).toBe(1)
    const originalClosure = first.kernel.getClosureReceipt('task-1', 'turn-1')!
    expect(originalClosure.status).toBe('COMPLETE')
    expect(originalClosure.moduleReceipts).toHaveLength(8)
    expect(store.finalization).toBeUndefined()
    await store.close()
    await first.dispose()

    const second = await startRuntime(projectRoot)
    const reopened = await openFileExecutionEventStore({
      directory: storeRoot,
      binding: { requestId: 'request-1', runtimeId: 'runtime-1', turnId: 'turn-1', contract },
    })
    await second.runtime.rehydrateSupervisedTurn({ runtimeId: 'runtime-1', eventStore: reopened })
    expect(second.runtime.getStatus('runtime-1')?.supervision?.decision.status).toBe('READY_TO_CLOSE')
    const recovered = await second.runtime.closeTurn({ runtimeId: 'runtime-1', turnId: 'turn-1' })
    expect(recovered.supervision?.decision.status).toBe('COMPLETE')
    expect(recovered.closure).toEqual(originalClosure)
    expect(second.kernel.getClosureReceipt('task-1', 'turn-1')).toEqual(originalClosure)
    await expect(second.runtime.completeTask('runtime-1')).resolves.toMatchObject({ status: 'COMPLETED' })
    await reopened.close()
    await second.dispose()
  }, 30_000)
})
