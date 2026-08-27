import { randomUUID } from 'node:crypto'
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
import type { ProjectCandidateResult, ProjectContext } from '@agent-harness/project-contract'
import type { ContextReference } from '@agent-harness/context-builder'
import type {
  AutoGovernanceCompletionResult,
  AutoGovernancePendingReview,
  AutoGovernanceReviewDecisionInput,
  AutoGovernanceReviewDecisionResult,
  AutoGovernanceRouteSnapshot,
  AutoGovernanceTaskStatus,
} from './contracts.js'

const PLUGIN_NAME = 'agent-harness-auto-governance-orchestrator'
const MAX_QUERY_CHARS = 4000
const MAX_REVIEW_PACKETS = 32
const MAX_HANDLE_SUMMARY_CHARS = 220

interface HarnessMessageLike {
  readonly content?: readonly unknown[]
  readonly source?: { readonly kind?: string }
}

interface HarnessAgentLike {
  readonly id: string
  readonly session?: { readonly header?: { readonly cwd?: string } }
}

interface HarnessToolExecutionLike {
  readonly name: string
  readonly arguments?: unknown
  readonly agent?: HarnessAgentLike
}

interface HarnessToolResultLike {
  readonly isError?: boolean
  readonly content?: readonly unknown[]
}

interface DynamicEventContext {
  on(name: string, listener: (...args: any[]) => any, options?: { prepend?: boolean; global?: boolean }): () => unknown
  get(name: string): unknown
}

interface DynamicTools {
  register(definition: Readonly<Record<string, unknown>>): () => unknown
}

interface RuntimeTask {
  agentId: string
  projectId: string
  taskId: string
  goal: string
  codeChangeEpoch: number
  codeChangeSeen: boolean
  route: AutoGovernanceRouteSnapshot
  applicableGateIds: string[]
  currentPacketIds: string[]
  lastInjectedStateVersion?: number
  lastInjectionSignature?: string
}

interface PendingReviewRecord extends Omit<AutoGovernancePendingReview, 'decision'> {
  decision: AutoGovernancePendingReview['decision']
  readonly packet: Readonly<Record<string, unknown>>
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

const reviewHandleSummary = (files: readonly string[]): string => {
  const suffix = '; decision=PENDING'
  if (files.length === 0) return `changed code${suffix}`
  const listed = files.slice(0, 2).join(', ')
  const remainder = files.length > 2 ? `, +${files.length - 2} more` : ''
  const body = `${listed}${remainder}`
  const maxBodyChars = MAX_HANDLE_SUMMARY_CHARS - suffix.length
  if (body.length <= maxBodyChars) return `${body}${suffix}`
  const clipped = `${body.slice(0, Math.max(0, maxBodyChars - 3))}...`
  return `${clipped}${suffix}`
}

const candidateIds = (candidates: readonly ProjectCandidateResult[]): string[] =>
  unique(candidates.map(candidate => candidate.id))

const contentText = (content: readonly unknown[] | undefined): string => {
  if (!content) return ''
  return content.map(block => {
    const record = recordOf(block)
    return typeof record?.text === 'string' ? record.text : ''
  }).filter(Boolean).join('\n').trim()
}

const directHumanText = (messages: readonly unknown[]): string =>
  messages.map(message => {
    const record = recordOf(message) as HarnessMessageLike | undefined
    return record?.source?.kind === 'user' ? contentText(record.content) : ''
  }).filter(Boolean).join('\n').trim()

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

export const isMutationInvocation = (name: string, args: unknown): boolean => {
  const normalized = name.toLowerCase()
  if (/(apply[_-]?patch|write[_-]?file|edit[_-]?file|str[_-]?replace|replace[_-]?file|delete[_-]?file|rename[_-]?file|move[_-]?file|create[_-]?file)/.test(normalized)) return true
  if (!/(bash|shell|terminal|pwsh|powershell|cmd|exec|run_code)/.test(normalized)) return false
  const text = jsonText(args).toLowerCase()
  return /(sed\s+-i|perl\s+-pi|git\s+apply|apply_patch|write_text|write_bytes|file_put_contents|\bmv\b|\brm\b|\bcp\b|>>|[^&]>[^&])/.test(text)
}

export const isBuildOrTestInvocation = (name: string, args: unknown): boolean => {
  const normalized = name.toLowerCase()
  if (/^(build|test|compile|ctest|pytest|cargo_test|npm_test)$/.test(normalized)) return true
  if (!/(bash|shell|terminal|pwsh|powershell|cmd|exec|run_code)/.test(normalized)) {
    return /(build|compile|ctest|pytest|test_runner)/.test(normalized)
  }
  const text = jsonText(args).toLowerCase()
  return /(release_gui\.bat|cmake\s+--build|\bctest\b|\bninja\b|\bpytest\b|npm\s+(run\s+build|test)\b|cargo\s+test\b|\bmake(?:\s|$)|meson\s+test\b)/.test(text)
}

export class AutoGovernanceOrchestratorService extends Service {
  private readonly runtimeContext: Context
  private readonly tasks = new Map<string, RuntimeTask>()
  private readonly pendingReviews = new Map<string, PendingReviewRecord>()
  private toolBridgeInstalled = false

  constructor(ctx: Context) {
    super(ctx, 'autoGovernanceOrchestrator')
    this.runtimeContext = ctx
    this.installHarnessBridge()
    this.ensureToolBridge()
    ctx.effect(() => () => {
      this.tasks.clear()
      this.pendingReviews.clear()
    })
  }

  preparePreStep(
    agent: HarnessAgentLike,
    messages: readonly unknown[],
    turn: number,
    step: number,
  ): Readonly<Record<string, unknown>> | undefined {
    const humanText = directHumanText(messages)
    let runtime = this.tasks.get(String(agent.id))

    if (humanText) {
      const project = this.resolveProject(agent, humanText)
      if (!project) return undefined
      runtime = this.ensureRuntimeTask(agent, project, humanText, turn)
      runtime.goal = humanText
      runtime.route = this.routeTask(runtime, humanText, true, 'analysis')
      this.runtimeContext.contextManager.updateProgressLedger(runtime.projectId, runtime.taskId, {
        lastAction: `Auto bootstrap from human task at turn ${turn}, step ${step}.`,
        lastResult: 'Architecture / Rule / Knowledge / Gate candidates routed automatically.',
        touchedRefs: [
          ...runtime.route.architectureIds,
          ...runtime.route.ruleIds,
          ...runtime.route.knowledgeIds,
          ...runtime.route.gateIds,
        ],
        currentProblem: '',
        blockers: [],
        next: ['Work only inside the routed project scope.', 'Re-run governance automatically after code changes.'],
      })
      this.runtimeContext.contextManager.recordRecent(runtime.projectId, runtime.taskId, {
        kind: 'DECISION',
        summary: 'Auto Governance bootstrap routed current task context.',
        refs: [...runtime.route.architectureIds, ...runtime.route.ruleIds, ...runtime.route.gateIds],
      })
    }

    if (!runtime) return undefined
    const frame = this.runtimeContext.contextManager.buildFrame(runtime.projectId, runtime.taskId)
    const reviewSignature = runtime.currentPacketIds.map(packetId => {
      const packet = this.pendingReviews.get(packetId)
      return `${packetId}:${packet?.decision ?? 'MISSING'}`
    }).join('|')
    const signature = `${frame.stateVersion}:${reviewSignature}`
    if (!humanText && runtime.lastInjectionSignature === signature) return undefined

    runtime.lastInjectedStateVersion = frame.stateVersion
    runtime.lastInjectionSignature = signature
    const text = this.renderAgentContext(runtime, frame.pack.text)
    return {
      id: `auto-governance-${randomUUID()}`,
      role: 'user',
      content: [{ type: 'text', text }],
      source: {
        kind: 'plugin',
        plugin: PLUGIN_NAME,
        form: 'snapshot',
        sections: [{ name: 'auto-governance', text }],
      },
    }
  }

  handleToolResult(exec: HarnessToolExecutionLike, result: HarnessToolResultLike): void {
    const agent = exec.agent
    if (!agent) return
    const runtime = this.tasks.get(String(agent.id))
    if (!runtime) return

    if (result.isError) {
      this.runtimeContext.contextManager.updateProgressLedger(runtime.projectId, runtime.taskId, {
        lastAction: `Tool ${exec.name} failed.`,
        lastResult: 'Tool failure observed automatically.',
        currentProblem: `Tool ${exec.name} failed; inspect the failure before continuing.`,
        blockers: [`tool:${exec.name}`],
        next: ['Inspect the tool failure and recover before completion.'],
      })
      this.runtimeContext.contextManager.recordRecent(runtime.projectId, runtime.taskId, {
        kind: 'ERROR',
        summary: `Tool ${exec.name} failed.`,
      })
      return
    }

    if (!isMutationInvocation(exec.name, exec.arguments)) return

    runtime.codeChangeSeen = true
    runtime.codeChangeEpoch += 1
    const query = [
      runtime.goal,
      'code change scope architecture rule logic lifecycle regression contract compatibility',
      exec.name,
      jsonText(exec.arguments).slice(0, 1200),
    ].join(' ').slice(0, MAX_QUERY_CHARS)
    runtime.route = this.routeTask(runtime, query, false, 'implementation')
    runtime.applicableGateIds = runtime.route.gateIds.filter(gateId =>
      this.runtimeContext.gateManager.getExecutionPlan(runtime.projectId, gateId) !== undefined,
    )
    runtime.currentPacketIds = this.prepareReviewPackets(runtime)

    const blockers = runtime.currentPacketIds.length > 0
      ? [`${runtime.currentPacketIds.length} current review packet(s) require explicit Agent PASS/BLOCK decisions.`]
      : ['Code change detected but no executable review packet was prepared; Gate evidence must be resolved before build/test.']
    this.runtimeContext.contextManager.updateProgressLedger(runtime.projectId, runtime.taskId, {
      lastAction: `Detected code-changing tool result: ${exec.name}.`,
      lastResult: `Governance refresh epoch ${runtime.codeChangeEpoch} completed.`,
      touchedRefs: [...runtime.route.architectureIds, ...runtime.route.ruleIds, ...runtime.applicableGateIds],
      currentProblem: 'Code change is pending Code Gate review.',
      blockers,
      next: ['Review every current packet.', 'Do not build/test until current Gates have PASS evidence.'],
    })
    this.runtimeContext.contextManager.recordRecent(runtime.projectId, runtime.taskId, {
      kind: 'ACTION',
      summary: `Code change detected automatically after ${exec.name}; Gates and review packets refreshed.`,
      refs: runtime.applicableGateIds,
    })
  }

  guardToolExecution(exec: HarnessToolExecutionLike): string | undefined {
    if (!exec.agent || !isBuildOrTestInvocation(exec.name, exec.arguments)) return undefined
    const runtime = this.tasks.get(String(exec.agent.id))
    if (!runtime || !runtime.codeChangeSeen) return undefined

    const currentReviews = runtime.currentPacketIds
      .map(packetId => this.pendingReviews.get(packetId))
      .filter((item): item is PendingReviewRecord => item !== undefined && item.epoch === runtime.codeChangeEpoch)
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
          next: ['Fix the blocking finding, then let Auto Governance detect the new code change and refresh reviews.'],
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

  completeTaskForAgent(agent: HarnessAgentLike): AutoGovernanceCompletionResult {
    const runtime = this.tasks.get(String(agent.id))
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

  getTaskStatus(agentId: string): AutoGovernanceTaskStatus | undefined {
    const runtime = this.tasks.get(agentId)
    if (!runtime) return undefined
    return {
      agentId: runtime.agentId,
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
      ...(runtime.lastInjectedStateVersion !== undefined
        ? { lastInjectedStateVersion: runtime.lastInjectedStateVersion }
        : {}),
    }
  }

  pauseForAgent(agent: HarnessAgentLike): void {
    const runtime = this.tasks.get(String(agent.id))
    if (!runtime) return
    try {
      const snapshot = this.runtimeContext.contextManager.getTask(runtime.projectId, runtime.taskId)
      if (snapshot.session.status === 'COMPLETED') return
      this.runtimeContext.contextManager.updateProgressLedger(runtime.projectId, runtime.taskId, {
        lastAction: 'Harness agent disposed.',
        lastResult: 'Context preserved for automatic resume.',
        next: ['Resume this task when the same Agent/session returns.'],
      })
      this.runtimeContext.contextManager.createHandoff(runtime.projectId, runtime.taskId)
      this.runtimeContext.contextManager.pause(runtime.projectId, runtime.taskId)
    } catch {
      // Teardown must never make agent disposal fail.
    }
  }

  private installHarnessBridge(): void {
    const events = this.dynamicContext()
    events.on('agent/pre-step', async (payload: any, next: () => Promise<any>) => {
      const downstream = await next()
      if (downstream?.kind !== 'enter' || payload?.signal?.aborted) return downstream
      const message = this.preparePreStep(payload.agent, downstream.messages ?? [], payload.turn ?? 0, payload.step ?? 0)
      return message
        ? { kind: 'enter', messages: [message, ...(downstream.messages ?? [])] }
        : downstream
    }, { prepend: true })

    events.on('tools/result', (exec: HarnessToolExecutionLike, result: HarnessToolResultLike) => {
      this.handleToolResult(exec, result)
    })

    events.on('tools/pre-execute', async (exec: HarnessToolExecutionLike, next: () => Promise<any>) => {
      const reason = this.guardToolExecution(exec)
      return reason ? { kind: 'deny', reason } : next()
    }, { prepend: true })

    events.on('agent/disposed', (payload: { agent?: HarnessAgentLike }) => {
      if (payload?.agent) this.pauseForAgent(payload.agent)
    })

    events.on('agent/created', () => this.ensureToolBridge())
  }

  private ensureToolBridge(): void {
    if (this.toolBridgeInstalled) return
    const tools = this.dynamicContext().get('tools') as DynamicTools | undefined
    if (!tools?.register) return
    try {
      tools.register({
        name: 'governance_review_decision',
        description: 'Submit PASS or BLOCK for one Auto Governance review packet after inspecting the actual change. Use this instead of asking the human to manually advance Code Gates.',
        parameters: {
          type: 'object',
          additionalProperties: false,
          required: ['packetId', 'result', 'summary'],
          properties: {
            packetId: { type: 'string' },
            result: { type: 'string', enum: ['PASS', 'BLOCK'] },
            summary: { type: 'string' },
          },
        },
        output: {
          schema: { type: 'object', additionalProperties: true },
          render: (_args: unknown, value: any) => [{
            type: 'text',
            text: `Governance review ${value.packetId}: ${value.result}; gateSetSatisfied=${String(value.gateSetSatisfied)}`,
          }],
        },
        execute: async (args: any, exec: any) => this.recordReviewDecision({
          packetId: String(args.packetId),
          result: args.result === 'BLOCK' ? 'BLOCK' : 'PASS',
          summary: String(args.summary),
          reviewerId: String(exec?.agent?.id ?? 'agent'),
        }),
      })
      tools.register({
        name: 'governance_complete_task',
        description: 'Ask Auto Governance to complete the current task. It refuses completion when current Code Gates are unresolved.',
        parameters: { type: 'object', additionalProperties: false, properties: {} },
        output: {
          schema: { type: 'object', additionalProperties: true },
          render: (_args: unknown, value: any) => [{
            type: 'text',
            text: value.status === 'COMPLETED'
              ? 'Governance task completed.'
              : `Governance completion blocked: ${value.reason}`,
          }],
        },
        execute: async (_args: any, exec: any) => {
          if (!exec?.agent) return { projectId: '', taskId: '', status: 'BLOCKED', reason: 'Tool call has no Agent.' }
          return this.completeTaskForAgent(exec.agent)
        },
      })
      this.toolBridgeInstalled = true
    } catch {
      // Tool integration is optional. Core event orchestration remains active without it.
    }
  }

  private ensureRuntimeTask(
    agent: HarnessAgentLike,
    project: ProjectContext,
    goal: string,
    turn: number,
  ): RuntimeTask {
    const agentId = String(agent.id)
    const existing = this.tasks.get(agentId)
    if (existing && existing.projectId === project.projectId) {
      try {
        const snapshot = this.runtimeContext.contextManager.getTask(existing.projectId, existing.taskId)
        if (snapshot.session.status === 'PAUSED') this.runtimeContext.contextManager.resume(existing.projectId, existing.taskId)
        if (snapshot.session.status !== 'COMPLETED') return existing
      } catch {
        // Fall through and recreate the deterministic task.
      }
    }

    let taskId = `AUTO-${project.projectId}-${agentId}`
    try {
      const snapshot = this.runtimeContext.contextManager.getTask(project.projectId, taskId)
      if (snapshot.session.status === 'COMPLETED') taskId = `${taskId}-T${turn}`
    } catch {
      // Task does not exist yet.
    }
    try {
      const current = this.runtimeContext.contextManager.getTask(project.projectId, taskId)
      if (current.session.status === 'PAUSED') this.runtimeContext.contextManager.resume(project.projectId, taskId)
    } catch {
      this.runtimeContext.contextManager.beginTask({ projectId: project.projectId, taskId, goal })
    }

    const runtime: RuntimeTask = {
      agentId,
      projectId: project.projectId,
      taskId,
      goal,
      codeChangeEpoch: 0,
      codeChangeSeen: false,
      route: emptyRoute(),
      applicableGateIds: [],
      currentPacketIds: [],
    }
    this.tasks.set(agentId, runtime)
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
    const architecture = this.runtimeContext.architectureNavigator.searchArchitecture({ ...request, limit: 6 })
    const rules = this.runtimeContext.ruleManager.searchRules({ ...request, limit: 10 })
    const knowledge = this.runtimeContext.knowledgeManager.searchKnowledge({ ...request, limit: 8 })
    const gates = this.runtimeContext.gateManager.searchGates({ ...request, limit: phase === 'implementation' ? 64 : 8 })
    const route: AutoGovernanceRouteSnapshot = {
      architectureIds: candidateIds(architecture),
      ruleIds: candidateIds(rules),
      knowledgeIds: candidateIds(knowledge),
      gateIds: candidateIds(gates),
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
      scopeRefs: unique([...current.scopeRefs, ...route.architectureIds]),
      constraintRefs: unique([...current.constraintRefs, ...route.ruleIds, ...route.gateIds]),
      plan: [
        'Use automatically routed Architecture / Rules / Knowledge before editing.',
        'Keep the change minimal and inside the resolved project scope.',
        'After code changes, satisfy current Code Gates before build/test.',
        'Record PASS/BLOCK through the review decision interface; do not ask the human to manually advance governance.',
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
        summary: reviewHandleSummary(review.changeFiles),
      }
    })
    if (handles.length > 0) this.runtimeContext.contextManager.addHandles(runtime.projectId, runtime.taskId, handles)
    return unique(packetIds)
  }

  private attachPacketContext(runtime: RuntimeTask, packet: Record<string, any>): void {
    const refs: ContextReference[] = []
    const append = (kind: ContextReference['kind'], value: unknown, priority: ContextReference['priority']) => {
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

  private renderAgentContext(runtime: RuntimeTask, frameText: string): string {
    const reviews = runtime.currentPacketIds
      .map(packetId => this.pendingReviews.get(packetId))
      .filter((item): item is PendingReviewRecord => item !== undefined && item.epoch === runtime.codeChangeEpoch)
    const reviewText = reviews.length === 0
      ? 'Pending Code Gate Reviews: none prepared for the current epoch.'
      : [
          'Pending Code Gate Reviews:',
          ...reviews.map(item =>
            `- ${item.packetId} | ${item.gateId} | ${item.capability} | ${item.decision} | files=${item.changeFiles.join(', ') || 'see packet'}`,
          ),
          'Agent action: inspect the actual change and submit each decision through governance_review_decision. Do not ask the human to trigger governance manually.',
        ].join('\n')
    return [
      '[AUTO GOVERNANCE CONTEXT — automatically injected]',
      'MUST / MUST_NOT Rules and MUST Gates in this frame are binding.',
      'Architecture / Rule / Knowledge / Gate routing is automatic; refine only when evidence shows a route is wrong.',
      'After a detected code change, build/test is blocked until the CURRENT review epoch is PASS and Gate Evidence is satisfied.',
      frameText,
      reviewText,
    ].join('\n\n')
  }

  private completionBlockReason(runtime: RuntimeTask): string | undefined {
    if (!runtime.codeChangeSeen) return undefined
    const unresolved = runtime.currentPacketIds
      .map(packetId => this.pendingReviews.get(packetId))
      .filter(item => item?.epoch === runtime.codeChangeEpoch && item.decision !== 'PASS')
    if (unresolved.length > 0) return `${unresolved.length} current review packet(s) are unresolved.`
    if (runtime.applicableGateIds.length === 0) return 'No executable Gate set resolved after code change.'
    const status = this.runtimeContext.gateManager.checkGateSetEvidence(runtime.projectId, runtime.taskId, runtime.applicableGateIds)
    return status.canComplete ? undefined : `Missing PASS Evidence: ${status.blockingGateIds.join(', ')}`
  }

  private resolveProject(agent: HarnessAgentLike, promptText: string): ProjectContext | undefined {
    const projects = [...this.runtimeContext.projectManager.listProjects()]
    const cwd = agent.session?.header?.cwd
    if (cwd) {
      const matched = projects
        .filter(project => isInside(cwd, project.projectRoot))
        .sort((a, b) => b.projectRoot.length - a.projectRoot.length)[0]
      if (matched) return matched
    }
    if (projects.length === 1) return projects[0]
    const candidate = this.runtimeContext.projectManager.resolveProject(promptText, 3)[0]
    return candidate ? this.runtimeContext.projectManager.getProjectContext(candidate.projectId) : undefined
  }

  private dynamicContext(): DynamicEventContext {
    return this.runtimeContext as unknown as DynamicEventContext
  }
}

declare module '@deepseek-ai/cordis' {
  interface Context {
    autoGovernanceOrchestrator: AutoGovernanceOrchestratorService
  }
}

export default AutoGovernanceOrchestratorService
