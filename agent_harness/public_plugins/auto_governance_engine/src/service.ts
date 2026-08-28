import { resolve, sep } from 'node:path'
import { Service, type Context } from '@deepseek-ai/cordis'
import '@agent-harness/governance-core'
import '@agent-harness/project-manager'
import '@agent-harness/architecture-navigator'
import '@agent-harness/rule-manager'
import '@agent-harness/knowledge-manager'
import '@agent-harness/gate-manager'
import '@agent-harness/evidence-state-manager'
import '@agent-harness/context-builder'
import type { ProjectContext } from '@agent-harness/project-contract'
import type { ContextPriority, ContextReference } from '@agent-harness/context-builder'
import type {
  AutoGovernanceActionCheck,
  AutoGovernanceBootstrapInput,
  AutoGovernanceCompletionResult,
  AutoGovernanceContextEnvelope,
  AutoGovernancePendingReview,
  AutoGovernanceReviewDecisionInput,
  AutoGovernanceReviewDecisionResult,
  AutoGovernanceRouteSnapshot,
  AutoGovernanceTaskStatus,
  AutoGovernanceToolObservation,
} from './contracts.js'
import {
  resolveGovernanceRouteGraph,
  type GovernanceRouteResourceKind,
} from './route-resolver.js'

const MAX_QUERY_CHARS = 4000
const MAX_REVIEW_PACKETS = 32
const MAX_TASK_LEDGER_REFS = 64

interface RuntimeTask {
  actorId: string
  projectId: string
  taskId: string
  goal: string
  codeChangeEpoch: number
  codeChangeSeen: boolean
  route: AutoGovernanceRouteSnapshot
  applicableGateIds: string[]
  currentPacketIds: string[]
  lastContextStateVersion?: number
}

interface PendingReviewRecord extends Omit<AutoGovernancePendingReview, 'decision'> {
  decision: AutoGovernancePendingReview['decision']
  readonly packet: Readonly<Record<string, unknown>>
}

interface DynamicServiceContext {
  get(name: string): unknown
}

const emptyRoute = (): AutoGovernanceRouteSnapshot => ({
  architectureIds: [],
  ruleIds: [],
  knowledgeIds: [],
  gateIds: [],
})

const recordOf = (value: unknown): Record<string, any> | undefined =>
  typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as Record<string, any>
    : undefined

const unique = (values: readonly string[]): string[] =>
  [...new Set(values.map(value => value.trim()).filter(Boolean))]

const normalizedPath = (value: string): string => {
  const full = resolve(value)
  return process.platform === 'win32' ? full.toLowerCase() : full
}

const isInside = (cwd: string, root: string): boolean => {
  const child = normalizedPath(cwd)
  const parent = normalizedPath(root)
  return child === parent || child.startsWith(parent.endsWith(sep) ? parent : `${parent}${sep}`)
}

const jsonText = (value: unknown): string => {
  try {
    return JSON.stringify(value) ?? ''
  } catch {
    return String(value)
  }
}

export const compactReviewFileSummary = (files: readonly string[]): string => {
  if (files.length === 0) return 'changed code'
  const visible = files.slice(0, 3).join(', ')
  const suffix = files.length > 3 ? ` (+${files.length - 3} more)` : ''
  const available = Math.max(3, 170 - suffix.length)
  const prefix = visible.length <= available
    ? visible
    : `${visible.slice(0, Math.max(0, available - 3))}...`
  return `${prefix}${suffix}`
}

const requireIdentifier = (label: string, value: string): string => {
  const normalized = value.trim()
  if (!normalized) throw new Error(`${label} cannot be empty`)
  if (!/^[A-Za-z0-9._:-]+$/.test(normalized)) {
    throw new Error(`${label} contains unsupported characters: ${value}`)
  }
  return normalized
}

export const isMutationInvocation = (name: string, args: unknown): boolean => {
  const normalized = name.toLowerCase()
  if (/(apply[_-]?patch|write[_-]?file|update[_-]?file|edit[_-]?file|str[_-]?replace|replace[_-]?file|delete[_-]?file|rename[_-]?file|move[_-]?file|create[_-]?file)/.test(normalized)) return true
  if (!/(bash|shell|terminal|pwsh|powershell|cmd|exec|run_code|python(?:3)?|node|deno|bun|javascript|typescript|ruby|php)/.test(normalized)) return false
  const text = jsonText(args).toLowerCase()
  return /(sed\s+-i|perl\s+-pi|git\s+apply|apply_patch|write_text|write_bytes|file_put_contents|writefilesync|appendfilesync|unlinksync|rmsync|renamesync|copyfilesync|\bmv\b|\brm\b|\bcp\b|>>|[^&]>[^&])/.test(text)
}

export const isProductBuildInvocation = (name: string, args: unknown): boolean => {
  const normalized = name.toLowerCase()
  if (/^(build|compile|cmake|ninja|ctest|msbuild|devenv|nmake)$/.test(normalized)) return true
  if (!/(bash|shell|terminal|pwsh|powershell|cmd|exec|run_code)/.test(normalized)) {
    return /(build|compile|cmake|ninja|ctest|msbuild|devenv|nmake)/.test(normalized)
  }
  const text = jsonText(args).toLowerCase()
  return /(release_gui\.bat|\bcmake\b[^\n\r]{0,400}(?:--build|--install|--preset|\s-[sb](?:\s|$))|\bctest\b|\bninja\b|\bmake(?:\s|$)|\bnmake\b|\bmsbuild\b|\bdevenv\b|\bmeson\s+(?:compile|install)\b)/.test(text)
}

export const isBuildOrTestInvocation = (name: string, args: unknown): boolean => {
  if (isProductBuildInvocation(name, args)) return true
  const normalized = name.toLowerCase()
  if (/^(test|pytest|cargo_test|npm_test)$/.test(normalized)) return true
  if (!/(bash|shell|terminal|pwsh|powershell|cmd|exec|run_code)/.test(normalized)) {
    return /(pytest|test_runner)/.test(normalized)
  }
  const text = jsonText(args).toLowerCase()
  return /(\bpytest\b|npm\s+(run\s+build|test)\b|cargo\s+test\b|meson\s+test\b)/.test(text)
}

export class AutoGovernanceEngineService extends Service {
  private readonly runtimeContext: Context
  private readonly tasks = new Map<string, RuntimeTask>()
  private readonly pendingReviews = new Map<string, PendingReviewRecord>()

  constructor(ctx: Context) {
    super(ctx, 'autoGovernanceEngine')
    this.runtimeContext = ctx
    ctx.effect(() => () => {
      this.tasks.clear()
      this.pendingReviews.clear()
    })
  }

  resolveProject(input: {
    readonly taskText: string
    readonly projectId?: string
    readonly workspacePath?: string
  }): ProjectContext | undefined {
    if (input.projectId?.trim()) {
      return this.runtimeContext.projectManager.getProjectContext(input.projectId.trim())
    }
    const projects = [...this.runtimeContext.projectManager.listProjects()]
    if (input.workspacePath?.trim()) {
      const matched = projects
        .filter(project => isInside(input.workspacePath!, project.projectRoot))
        .sort((left, right) => right.projectRoot.length - left.projectRoot.length)[0]
      if (matched) return matched
    }
    if (projects.length === 1) return projects[0]
    const candidate = this.runtimeContext.projectManager.resolveProject(input.taskText, 3)[0]
    return candidate
      ? this.runtimeContext.projectManager.getProjectContext(candidate.projectId)
      : undefined
  }

  bootstrapTask(input: AutoGovernanceBootstrapInput): AutoGovernanceContextEnvelope {
    const actorId = requireIdentifier('actorId', input.actorId)
    const taskId = requireIdentifier('taskId', input.taskId)
    const goal = input.goal.trim()
    if (!goal) throw new Error('goal cannot be empty')
    const project = this.resolveProject({
      taskText: goal,
      ...(input.projectId?.trim() ? { projectId: input.projectId.trim() } : {}),
      ...(input.workspacePath?.trim() ? { workspacePath: input.workspacePath.trim() } : {}),
    })
    if (!project) throw new Error('Auto Governance could not resolve a project for the task')

    const runtime = this.ensureRuntimeTask(actorId, project, taskId, goal)
    runtime.goal = goal
    const phase = input.phase ?? 'analysis'
    runtime.route = this.routeTask(runtime, goal, true, phase)
    this.runtimeContext.contextManager.updateProgressLedger(runtime.projectId, runtime.taskId, {
      lastAction: 'Auto Governance bootstrapped the task.',
      lastResult: 'Architecture / Rule / Knowledge / Gate candidates routed automatically.',
      touchedRefs: [
        ...runtime.route.architectureIds,
        ...runtime.route.ruleIds,
        ...runtime.route.knowledgeIds,
        ...runtime.route.gateIds,
      ],
      currentProblem: '',
      blockers: [],
      next: ['Work inside the routed project scope.', 'Re-run governance after material code changes.'],
    })
    this.runtimeContext.contextManager.recordRecent(runtime.projectId, runtime.taskId, {
      kind: 'DECISION',
      summary: 'Auto Governance bootstrap routed current task context.',
      refs: [...runtime.route.architectureIds, ...runtime.route.ruleIds, ...runtime.route.gateIds],
    })
    return this.buildContextEnvelope(actorId)
  }

  buildContextEnvelope(actorIdInput: string): AutoGovernanceContextEnvelope {
    const actorId = requireIdentifier('actorId', actorIdInput)
    const runtime = this.requireRuntime(actorId)
    const frame = this.runtimeContext.contextManager.buildFrame(runtime.projectId, runtime.taskId)
    runtime.lastContextStateVersion = frame.stateVersion
    const pendingReviews = runtime.currentPacketIds
      .map(packetId => this.pendingReviews.get(packetId))
      .filter((item): item is PendingReviewRecord => item !== undefined && item.epoch === runtime.codeChangeEpoch)
    return {
      actorId,
      projectId: runtime.projectId,
      taskId: runtime.taskId,
      goal: runtime.goal,
      stateVersion: frame.stateVersion,
      route: runtime.route,
      applicableGateIds: [...runtime.applicableGateIds],
      pendingReviews,
      text: this.renderGovernanceContext(runtime, frame.pack.text, pendingReviews),
    }
  }

  observeToolResult(input: AutoGovernanceToolObservation): AutoGovernanceContextEnvelope {
    const runtime = this.requireRuntime(input.actorId)
    const mutation = isMutationInvocation(input.name, input.arguments)

    if (!mutation) {
      if (input.isError) {
        this.runtimeContext.contextManager.updateProgressLedger(runtime.projectId, runtime.taskId, {
          lastAction: `Tool ${input.name} failed.`,
          lastResult: 'Tool failure observed automatically.',
          currentProblem: `Tool ${input.name} failed; inspect the failure before continuing.`,
          blockers: [`tool:${input.name}`],
          next: ['Inspect the tool failure and recover before completion.'],
        })
        this.runtimeContext.contextManager.recordRecent(runtime.projectId, runtime.taskId, {
          kind: 'ERROR',
          summary: `Tool ${input.name} failed.`,
        })
      }
      return this.buildContextEnvelope(runtime.actorId)
    }

    // A mutating tool may fail after a partial write. Both success and failure
    // create a fresh review epoch so prior PASS Evidence cannot authorize a build.
    runtime.codeChangeSeen = true
    runtime.codeChangeEpoch += 1
    const query = [
      runtime.goal,
      'code change scope architecture rule logic lifecycle regression contract compatibility',
      input.name,
      jsonText(input.arguments).slice(0, 1200),
    ].join(' ').slice(0, MAX_QUERY_CHARS)
    runtime.route = this.routeTask(runtime, query, true, 'implementation')
    runtime.applicableGateIds = runtime.route.gateIds.filter(gateId =>
      this.runtimeContext.gateManager.getExecutionPlan(runtime.projectId, gateId) !== undefined,
    )
    runtime.currentPacketIds = this.prepareReviewPackets(runtime)

    const reviewBlockers = runtime.currentPacketIds.length > 0
      ? [`${runtime.currentPacketIds.length} current review packet(s) require explicit PASS/BLOCK decisions.`]
      : ['Code change detected but no executable review packet was prepared; Gate evidence must be resolved before build/test.']
    const blockers = input.isError ? [`tool:${input.name}`, ...reviewBlockers] : reviewBlockers
    this.runtimeContext.contextManager.updateProgressLedger(runtime.projectId, runtime.taskId, {
      lastAction: input.isError
        ? `Tool ${input.name} failed after a potentially mutating action.`
        : `Detected code-changing action result: ${input.name}.`,
      lastResult: input.isError
        ? `Governance conservatively refreshed code-change epoch ${runtime.codeChangeEpoch}.`
        : `Governance refresh epoch ${runtime.codeChangeEpoch} completed.`,
      touchedRefs: [...runtime.route.architectureIds, ...runtime.route.ruleIds, ...runtime.applicableGateIds],
      currentProblem: input.isError
        ? `Tool ${input.name} failed and may have partially changed code; current Code Gate review is required.`
        : 'Code change is pending Code Gate review.',
      blockers,
      next: input.isError
        ? ['Inspect the partial failure.', 'Review every current packet.', 'Do not build/test until current Gates have PASS evidence.']
        : ['Review every current packet.', 'Do not build/test until current Gates have PASS evidence.'],
    })
    this.runtimeContext.contextManager.recordRecent(runtime.projectId, runtime.taskId, {
      kind: input.isError ? 'ERROR' : 'ACTION',
      summary: input.isError
        ? `Tool ${input.name} failed after a possible code change; Gates and review packets refreshed.`
        : `Code change detected after ${input.name}; Gates and review packets refreshed.`,
      refs: runtime.applicableGateIds,
    })
    return this.buildContextEnvelope(runtime.actorId)
  }

  guardAction(input: AutoGovernanceActionCheck): string | undefined {
    const runtime = this.tasks.get(input.actorId)
    if (!runtime) return undefined

    if (isProductBuildInvocation(input.name, input.arguments)) {
      const ruleGuard = this.runtimeContext.ruleManager.guardAction(runtime.projectId, {
        actionKind: 'PRODUCT_BUILD',
        actionText: jsonText(input.arguments),
      })
      if (!ruleGuard.allowed) {
        return `Rule ${ruleGuard.ruleId ?? 'ACTION_GUARD'} blocked product build: ${ruleGuard.reason ?? 'project action guard rejected the action'}`
      }
    }

    if (!isBuildOrTestInvocation(input.name, input.arguments)) return undefined
    if (!runtime.codeChangeSeen) return undefined

    const currentReviews = runtime.currentPacketIds
      .map(packetId => this.pendingReviews.get(packetId))
      .filter((item): item is PendingReviewRecord => item !== undefined && item.epoch === runtime.codeChangeEpoch)
    if (currentReviews.length === 0) {
      return 'Auto Governance blocked build/test: code changed but no current review packet was prepared.'
    }
    const unresolved = currentReviews.filter(item => item.decision !== 'PASS')
    if (unresolved.length > 0) {
      return `Auto Governance blocked build/test: ${unresolved.length} current review packet(s) are not PASS.`
    }
    if (runtime.applicableGateIds.length === 0) {
      return 'Auto Governance blocked build/test: code changed but no executable Gate set was resolved.'
    }
    const gateStatus = this.runtimeContext.gateManager.checkGateSetEvidence(
      runtime.projectId,
      runtime.taskId,
      runtime.applicableGateIds,
    )
    if (!gateStatus.canComplete) {
      return `Auto Governance blocked build/test: missing PASS Evidence for ${gateStatus.blockingGateIds.join(', ')}.`
    }
    return undefined
  }

  recordReviewDecision(input: AutoGovernanceReviewDecisionInput): AutoGovernanceReviewDecisionResult {
    const review = this.pendingReviews.get(input.packetId)
    if (!review) throw new Error(`Auto Governance review packet not found: ${input.packetId}`)
    const service = this.dynamicContext().get(review.serviceName)
    const method = recordOf(service)?.[review.decisionMethod]
    if (typeof method !== 'function') {
      throw new Error(`Review provider decision method unavailable: ${review.serviceName}.${review.decisionMethod}`)
    }
    const raw = method.call(service, {
      packetId: input.packetId,
      result: input.result,
      summary: input.summary,
      reviewer: 'agent',
      reviewerId: input.reviewerId,
      ...(input.findings ? { findings: input.findings } : {}),
    })
    const result = recordOf(raw)
    review.decision = input.result

    const runtime = [...this.tasks.values()].find(item => item.taskId === review.taskId)
    const allCurrentReviewsPass = runtime
      ? runtime.currentPacketIds.length > 0 && runtime.currentPacketIds.every(packetId => {
          const current = this.pendingReviews.get(packetId)
          return current?.epoch === runtime.codeChangeEpoch && current.decision === 'PASS'
        })
      : false
    const gateSetSatisfied = runtime && runtime.applicableGateIds.length > 0
      ? this.runtimeContext.gateManager.checkGateSetEvidence(
          runtime.projectId,
          runtime.taskId,
          runtime.applicableGateIds,
        ).canComplete
      : false

    if (runtime) {
      if (input.result === 'BLOCK') {
        this.runtimeContext.contextManager.updateProgressLedger(runtime.projectId, runtime.taskId, {
          lastAction: `Review packet ${input.packetId} returned BLOCK.`,
          lastResult: input.summary,
          currentProblem: input.summary,
          blockers: [input.packetId],
          next: ['Fix the blocking finding, then refresh governance after the next code change.'],
          ...(typeof result?.evidenceId === 'string' ? { evidenceRefs: [result.evidenceId] } : {}),
        })
      } else if (allCurrentReviewsPass && gateSetSatisfied) {
        this.runtimeContext.contextManager.updateProgressLedger(runtime.projectId, runtime.taskId, {
          lastAction: `Review packet ${input.packetId} returned PASS.`,
          lastResult: 'All current Code Gate reviews and Gate Evidence are satisfied.',
          currentProblem: '',
          blockers: [],
          next: ['Formal build/test may proceed through the project release pipeline.'],
          ...(typeof result?.evidenceId === 'string' ? { evidenceRefs: [result.evidenceId] } : {}),
        })
      }
    }

    return {
      packetId: input.packetId,
      projectId: review.projectId,
      taskId: review.taskId,
      gateId: review.gateId,
      result: input.result,
      ...(typeof result?.evidenceId === 'string' ? { evidenceId: result.evidenceId } : {}),
      allCurrentReviewsPass,
      gateSetSatisfied,
    }
  }

  completeTask(actorIdInput: string): AutoGovernanceCompletionResult {
    const actorId = requireIdentifier('actorId', actorIdInput)
    const runtime = this.tasks.get(actorId)
    if (!runtime) return { projectId: '', taskId: '', status: 'BLOCKED', reason: 'No active Auto Governance task.' }
    const reason = this.completionBlockReason(runtime)
    if (reason) return { projectId: runtime.projectId, taskId: runtime.taskId, status: 'BLOCKED', reason }
    this.runtimeContext.contextManager.updateProgressLedger(runtime.projectId, runtime.taskId, {
      lastAction: 'Auto Governance completion check.',
      lastResult: 'Task completion admitted.',
      currentProblem: '',
      blockers: [],
      next: [],
    })
    this.runtimeContext.contextManager.complete(runtime.projectId, runtime.taskId)
    return { projectId: runtime.projectId, taskId: runtime.taskId, status: 'COMPLETED' }
  }

  pauseTask(actorIdInput: string): void {
    const runtime = this.tasks.get(requireIdentifier('actorId', actorIdInput))
    if (!runtime) return
    const snapshot = this.runtimeContext.contextManager.getTask(runtime.projectId, runtime.taskId)
    if (snapshot.session.status === 'COMPLETED' || snapshot.session.status === 'PAUSED') return
    this.runtimeContext.contextManager.updateProgressLedger(runtime.projectId, runtime.taskId, {
      lastAction: 'Governance runtime paused the task.',
      lastResult: 'Context preserved for resume.',
      next: ['Resume this task when its runtime actor returns.'],
    })
    this.runtimeContext.contextManager.createHandoff(runtime.projectId, runtime.taskId)
    this.runtimeContext.contextManager.pause(runtime.projectId, runtime.taskId)
  }

  getTaskStatus(actorIdInput: string): AutoGovernanceTaskStatus | undefined {
    const runtime = this.tasks.get(actorIdInput)
    if (!runtime) return undefined
    return {
      actorId: runtime.actorId,
      projectId: runtime.projectId,
      taskId: runtime.taskId,
      goal: runtime.goal,
      codeChangeEpoch: runtime.codeChangeEpoch,
      codeChangeSeen: runtime.codeChangeSeen,
      route: runtime.route,
      applicableGateIds: [...runtime.applicableGateIds],
      pendingReviews: runtime.currentPacketIds
        .map(packetId => this.pendingReviews.get(packetId))
        .filter((item): item is PendingReviewRecord => item !== undefined),
      ...(runtime.lastContextStateVersion !== undefined
        ? { lastContextStateVersion: runtime.lastContextStateVersion }
        : {}),
    }
  }

  private ensureRuntimeTask(
    actorId: string,
    project: ProjectContext,
    taskId: string,
    goal: string,
  ): RuntimeTask {
    const existing = this.tasks.get(actorId)
    if (existing) {
      if (existing.projectId !== project.projectId || existing.taskId !== taskId) {
        throw new Error(`Actor ${actorId} already owns another governed task: ${existing.projectId}/${existing.taskId}`)
      }
      const snapshot = this.runtimeContext.contextManager.getTask(existing.projectId, existing.taskId)
      if (snapshot.session.status === 'PAUSED') this.runtimeContext.contextManager.resume(existing.projectId, existing.taskId)
      if (snapshot.session.status === 'COMPLETED') {
        throw new Error(`Governed task is already completed: ${existing.projectId}/${existing.taskId}`)
      }
      return existing
    }

    try {
      const current = this.runtimeContext.contextManager.getTask(project.projectId, taskId)
      if (current.session.status === 'PAUSED') this.runtimeContext.contextManager.resume(project.projectId, taskId)
      if (current.session.status === 'COMPLETED') {
        throw new Error(`Governed task is already completed: ${project.projectId}/${taskId}`)
      }
    } catch (error) {
      if (error instanceof Error && error.message.startsWith('Governed task is already completed:')) throw error
      this.runtimeContext.contextManager.beginTask({ projectId: project.projectId, taskId, goal })
    }

    const runtime: RuntimeTask = {
      actorId,
      projectId: project.projectId,
      taskId,
      goal,
      codeChangeEpoch: 0,
      codeChangeSeen: false,
      route: emptyRoute(),
      applicableGateIds: [],
      currentPacketIds: [],
    }
    this.tasks.set(actorId, runtime)
    return runtime
  }

  private routeTask(
    runtime: RuntimeTask,
    queryText: string,
    replaceWorkingSet: boolean,
    phase: 'analysis' | 'implementation',
  ): AutoGovernanceRouteSnapshot {
    const query = queryText.replace(/\s+/g, ' ').trim().slice(0, MAX_QUERY_CHARS)
    const request = { projectId: runtime.projectId, query, scope: { taskId: runtime.taskId }, limit: 8 }
    const seeds = {
      architecture: this.runtimeContext.architectureNavigator.searchArchitecture({ ...request, limit: 6 }),
      rule: this.runtimeContext.ruleManager.searchRules({ ...request, limit: 10 }),
      knowledge: this.runtimeContext.knowledgeManager.searchKnowledge({ ...request, limit: 8 }),
      gate: this.runtimeContext.gateManager.searchGates({
        ...request,
        limit: phase === 'implementation' ? 24 : 8,
      }),
    }
    const exactLookup = (kind: GovernanceRouteResourceKind, id: string) => {
      if (kind === 'architecture') {
        return this.runtimeContext.architectureNavigator.searchArchitecture({ ...request, query: id, limit: 1 })[0]
      }
      if (kind === 'rule') {
        return this.runtimeContext.ruleManager.searchRules({ ...request, query: id, limit: 1 })[0]
      }
      if (kind === 'knowledge') {
        return this.runtimeContext.knowledgeManager.searchKnowledge({ ...request, query: id, limit: 1 })[0]
      }
      return this.runtimeContext.gateManager.searchGates({ ...request, query: id, limit: 1 })[0]
    }
    const resolution = resolveGovernanceRouteGraph({
      projectId: runtime.projectId,
      seeds,
      maxDepth: 2,
      limits: {
        architecture: 12,
        rule: 24,
        knowledge: 20,
        gate: phase === 'implementation' ? 32 : 16,
      },
      exactLookup,
    })
    const route: AutoGovernanceRouteSnapshot = {
      architectureIds: resolution.candidates.architecture.map(candidate => candidate.id),
      ruleIds: resolution.candidates.rule.map(candidate => candidate.id),
      knowledgeIds: resolution.candidates.knowledge.map(candidate => candidate.id),
      gateIds: resolution.candidates.gate.map(candidate => candidate.id),
    }
    const refs: ContextReference[] = [
      ...route.architectureIds.map(id => ({ kind: 'architecture' as const, id, priority: 'high' as const })),
      ...route.ruleIds.map(id => ({ kind: 'rule' as const, id, priority: 'high' as const })),
      ...route.knowledgeIds.map(id => ({ kind: 'knowledge' as const, id, priority: 'normal' as const })),
      ...route.gateIds.map(id => ({ kind: 'gate' as const, id, priority: 'high' as const })),
    ]
    if (replaceWorkingSet) {
      this.runtimeContext.contextManager.replaceWorkingSet(runtime.projectId, runtime.taskId, refs)
    } else {
      this.runtimeContext.contextManager.attach(runtime.projectId, runtime.taskId, refs)
    }
    const current = this.runtimeContext.contextManager.getTask(runtime.projectId, runtime.taskId).session.taskLedger
    this.runtimeContext.contextManager.updateTaskLedger(runtime.projectId, runtime.taskId, {
      goal: runtime.goal,
      phase,
      scopeRefs: unique([...route.architectureIds, ...current.scopeRefs]).slice(0, MAX_TASK_LEDGER_REFS),
      constraintRefs: unique([...route.ruleIds, ...route.gateIds, ...current.constraintRefs])
        .slice(0, MAX_TASK_LEDGER_REFS),
      plan: [
        'Use automatically routed Architecture / Rules / Knowledge before editing.',
        'Keep the change minimal and inside the resolved project scope.',
        'After code changes, satisfy current Code Gates before build/test.',
        'Record PASS/BLOCK through the runtime review interface; do not ask the human to manually advance governance.',
      ],
    })
    return route
  }

  private prepareReviewPackets(runtime: RuntimeTask): string[] {
    const packetIds: string[] = []
    for (const gateId of runtime.applicableGateIds) {
      const plan = this.runtimeContext.gateManager.getExecutionPlan(runtime.projectId, gateId)
      if (!plan) continue
      for (const step of plan.steps) {
        if (packetIds.length >= MAX_REVIEW_PACKETS) break
        const providers = this.runtimeContext.governanceCatalog.listProviders(step.tool)
        const provider = providers.find(item => item.metadata?.projectId === runtime.projectId) ?? providers[0]
        if (!provider) continue
        const serviceName = typeof provider.metadata?.service === 'string' ? provider.metadata.service : ''
        const prepareMethod = typeof provider.metadata?.prepareMethod === 'string' ? provider.metadata.prepareMethod : ''
        const decisionMethod = typeof provider.metadata?.decisionMethod === 'string' ? provider.metadata.decisionMethod : ''
        if (!serviceName || !prepareMethod || !decisionMethod) continue
        const service = this.dynamicContext().get(serviceName)
        const method = recordOf(service)?.[prepareMethod]
        if (typeof method !== 'function') continue
        try {
          const packetRaw = method.call(service, {
            projectId: runtime.projectId,
            taskId: runtime.taskId,
            gateId,
            capability: step.tool,
            taskIntent: runtime.goal,
            reviewEpoch: runtime.codeChangeEpoch,
            ...(typeof step.args?.focus === 'string' ? { focus: step.args.focus } : {}),
          })
          const packet = recordOf(packetRaw)
          if (!packet) continue
          const packetId = typeof packet.packetId === 'string' ? packet.packetId : ''
          if (!packetId) continue
          const change = recordOf(packet.change)
          const changeFiles = Array.isArray(change?.files)
            ? change.files.filter((item: unknown): item is string => typeof item === 'string')
            : []
          const review: PendingReviewRecord = {
            packetId,
            projectId: runtime.projectId,
            taskId: runtime.taskId,
            gateId,
            capability: step.tool,
            providerId: provider.providerId,
            serviceName,
            decisionMethod,
            ...(typeof packet.focus === 'string' ? { focus: packet.focus } : {}),
            epoch: runtime.codeChangeEpoch,
            decision: 'PENDING',
            changeFiles,
            packet,
          }
          this.pendingReviews.set(packetId, review)
          packetIds.push(packetId)
          this.attachPacketContext(runtime, packet)
        } catch {
          // A project adapter may reject a false-positive mutation trigger or unsupported Gate step.
        }
      }
    }
    const handles = packetIds.map(packetId => {
      const review = this.pendingReviews.get(packetId)!
      return {
        kind: 'other' as const,
        reference: `review://${packetId}`,
        title: `${review.gateId} ${review.capability}`,
        summary: `${compactReviewFileSummary(review.changeFiles)}; decision=PENDING`,
      }
    })
    if (handles.length > 0) this.runtimeContext.contextManager.addHandles(runtime.projectId, runtime.taskId, handles)
    return unique(packetIds)
  }

  private attachPacketContext(runtime: RuntimeTask, packet: Record<string, any>): void {
    const refs: ContextReference[] = []
    const append = (kind: ContextReference['kind'], value: unknown, priority: ContextPriority) => {
      if (!Array.isArray(value)) return
      for (const candidate of value) {
        const id = recordOf(candidate)?.id
        if (typeof id === 'string' && id.trim()) refs.push({ kind, id, priority })
      }
    }
    append('architecture', packet.architectureCandidates, 'high')
    append('rule', packet.ruleCandidates, 'high')
    append('knowledge', packet.knowledgeCandidates, 'normal')
    if (refs.length > 0) this.runtimeContext.contextManager.attach(runtime.projectId, runtime.taskId, refs)
  }

  private renderGovernanceContext(
    runtime: RuntimeTask,
    frameText: string,
    reviews: readonly PendingReviewRecord[],
  ): string {
    const reviewText = reviews.length === 0
      ? 'Pending Code Gate Reviews: none prepared for the current epoch.'
      : [
          'Pending Code Gate Reviews:',
          ...reviews.map(item =>
            `- ${item.packetId} | ${item.gateId} | ${item.capability} | ${item.decision} | files=${item.changeFiles.join(', ') || 'see packet'}`,
          ),
          'Required action: inspect the actual change and submit each decision through the host/runtime review bridge.',
        ].join('\n')
    return [
      '[GOVERNANCE CONTEXT]',
      'MUST / MUST_NOT Rules and MUST Gates in this context are binding.',
      'Architecture / Rule / Knowledge / Gate routing is automatic; refine only when evidence shows a route is wrong.',
      'After a detected code change, build/test is blocked until the current review epoch is PASS and Gate Evidence is satisfied.',
      frameText,
      reviewText,
    ].join('\n\n')
  }

  private completionBlockReason(runtime: RuntimeTask): string | undefined {
    if (!runtime.codeChangeSeen) return undefined
    const currentReviews = runtime.currentPacketIds
      .map(packetId => this.pendingReviews.get(packetId))
      .filter((item): item is PendingReviewRecord => item !== undefined && item.epoch === runtime.codeChangeEpoch)
    if (currentReviews.length === 0) return 'No current review packet was prepared after code change.'
    const unresolved = currentReviews.filter(item => item.decision !== 'PASS')
    if (unresolved.length > 0) return `${unresolved.length} current review packet(s) are unresolved.`
    if (runtime.applicableGateIds.length === 0) return 'No executable Gate set resolved after code change.'
    const status = this.runtimeContext.gateManager.checkGateSetEvidence(runtime.projectId, runtime.taskId, runtime.applicableGateIds)
    return status.canComplete ? undefined : `Missing PASS Evidence: ${status.blockingGateIds.join(', ')}`
  }

  private requireRuntime(actorIdInput: string): RuntimeTask {
    const actorId = requireIdentifier('actorId', actorIdInput)
    const runtime = this.tasks.get(actorId)
    if (!runtime) throw new Error(`No active Auto Governance task for actor: ${actorId}`)
    return runtime
  }

  private dynamicContext(): DynamicServiceContext {
    return this.runtimeContext as unknown as DynamicServiceContext
  }
}

declare module '@deepseek-ai/cordis' {
  interface Context {
    autoGovernanceEngine: AutoGovernanceEngineService
  }
}

export default AutoGovernanceEngineService
