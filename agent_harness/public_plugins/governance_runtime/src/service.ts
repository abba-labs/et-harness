import { Service, type Context } from '@deepseek-ai/cordis'
import '@agent-harness/agent-governance-kernel'
import '@agent-harness/agent-governance-closure-adapters'
import '@agent-harness/auto-governance-engine'
import '@agent-harness/knowledge-manager'
import type {
  KnowledgeVerificationReflection,
  TurnJournalRecord,
  TurnReflectionProviderInput,
  TurnReflectionRecord,
} from '@agent-harness/agent-governance-kernel'
import type { AutoGovernanceContextEnvelope } from '@agent-harness/auto-governance-engine'
import type { KnowledgeCategory, KnowledgeTaxonomy } from '@agent-harness/knowledge-manager'
import {
  EXECUTION_EVENT_SCHEMA,
  SUPERVISION_LIFECYCLE_BINDING_SCHEMA,
  createExecutionObligationLedger,
  evaluateMutationPreflight,
  hashCanonicalJson,
  negotiateSupervisionLevel,
  sha256Hex,
  supervisionFingerprint,
  validateHostCapabilityContract,
  type CompletionDecisionV01,
  type ExecutionEventEnvelopeV01,
  type ExecutionEventStoreV01,
  type ExecutionLifecycleAuthorityV01,
  type ExecutionObligationLedgerV01,
  type HostCapabilityContractV01,
  type SupervisionLifecycleBindingV01,
  type SupervisionReadinessReceiptV01,
} from '@agent-harness/execution-supervisor'
import { evaluateKnowledgeGovernanceDecision } from './knowledge-governance-decision.js'
import {
  GOVERNANCE_RUNTIME_CONTRACT_VERSION,
  type GovernanceActionPreflightInput,
  type GovernanceActionPreflightResult,
  type GovernanceBindSupervisedTurnInput,
  type GovernanceCloseTurnInput,
  type GovernanceCloseTurnResult,
  type GovernanceGateEvidenceProducerPreflightInput,
  type GovernanceKnowledgeCategoryOption,
  type GovernanceKnowledgeDecision,
  type GovernanceKnowledgePromotion,
  type GovernanceKnowledgeSourceOption,
  type GovernanceKnowledgeVerificationResult,
  type GovernanceHostSupervisionProfile,
  type GovernanceHostExecutionEventInput,
  type GovernanceHostExecutionEventResult,
  type GovernanceOpenTurnInput,
  type GovernanceOpenTurnResult,
  type GovernanceRehydrateSupervisedTurnInput,
  type GovernanceRuntimeReviewDecisionInput,
  type GovernanceRuntimeReviewDecisionResult,
  type GovernanceRuntimeStatus,
  type GovernanceSemanticExecutor,
  type GovernanceSemanticRequest,
  type GovernanceTurnObservation,
  type GovernanceWorkObservation,
  type GovernanceWorkObservationResult,
} from './contracts.js'
import { GovernanceTurnObservationStore } from './turn-observation-store.js'
import {
  enqueueRuntimeExecutionEvent,
  type RuntimeExecutionEventIdentity,
  type RuntimeExecutionIngressState,
} from './runtime-execution-ingress.js'

interface RuntimeSession {
  runtimeId: string
  actorId: string
  projectId: string
  taskId: string
  activeTurnId?: string
  activeTurnTaskTextHash?: string
  semanticExecutor?: GovernanceSemanticExecutor
  contextHash?: string
  supervision?: RuntimeSupervision
}

interface RuntimeSupervision extends RuntimeExecutionIngressState {
  readonly eventStore: ExecutionEventStoreV01
  readonly ledger: ExecutionObligationLedgerV01
  readonly hostProfile?: GovernanceHostSupervisionProfile
  readonly eventsById: Map<string, RuntimeExecutionEventIdentity>
  ingestTail: Promise<void>
}

interface ReflectionJob {
  readonly runtimeId: string
  readonly actorId: string
  readonly projectId: string
  readonly taskId: string
  readonly turnId: string
  readonly executor: GovernanceSemanticExecutor
}

const cleanIdentifier = (label: string, value: string): string => {
  const normalized = value.trim()
  if (!normalized) throw new Error(`${label} cannot be empty`)
  if (!/^[A-Za-z0-9._:-]+$/.test(normalized)) {
    throw new Error(`${label} contains unsupported characters: ${value}`)
  }
  return normalized
}

const taskToken = (value: string): string =>
  value.trim().replace(/[^A-Za-z0-9._:-]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 96) || 'runtime'

const reflectionKey = (taskId: string, turnId: string): string => `${taskId}::${turnId}`

const unique = (values: readonly string[]): string[] =>
  [...new Set(values.map(value => value.trim()).filter(Boolean))]

const recordValue = (value: unknown): Record<string, unknown> | undefined =>
  typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : undefined

const visibleExecutionMessage = (event: ExecutionEventEnvelopeV01): string | undefined => {
  const payload = recordValue(event.payload)
  const manifest = event.kind === 'USER_MESSAGE'
    ? recordValue(payload?.requestManifest)
    : event.kind === 'ASSISTANT_MESSAGE'
      ? recordValue(payload?.responseManifest)
      : undefined
  const message = event.kind === 'USER_MESSAGE'
    ? recordValue(manifest?.userMessage)
    : event.kind === 'ASSISTANT_MESSAGE'
      ? recordValue(manifest?.assistantMessage)
      : undefined
  const content = message?.content ?? payload?.text ?? payload?.content
  return typeof content === 'string' && content.trim() ? content : undefined
}

const reflectionBindingRef = (reflection: TurnReflectionRecord | undefined): string | undefined =>
  reflection?.readinessBinding
    ? `${reflection.readinessBinding.ref}|${reflection.readinessBinding.fingerprint}`
    : undefined

const errorText = (error: unknown): string => {
  const raw = error instanceof Error ? error.message : String(error)
  return raw.replace(/\s+/g, ' ').trim().slice(0, 1200) || 'Unknown post-Closure error'
}

const mergeKnowledgePromotions = (
  promotions: readonly GovernanceKnowledgePromotion[],
): GovernanceKnowledgePromotion[] => {
  const merged = new Map<string, GovernanceKnowledgePromotion>()
  for (const item of promotions) merged.set(`${item.knowledgeUri}:${item.toStatus}`, item)
  return [...merged.values()]
}

export class GovernanceRuntimeService extends Service {
  private readonly runtimeContext: Context
  private readonly sessions = new Map<string, RuntimeSession>()
  private readonly reflectionJobs = new Map<string, ReflectionJob>()
  private readonly closeJobs = new Map<string, Promise<GovernanceCloseTurnResult>>()
  private readonly observations = new GovernanceTurnObservationStore()

  constructor(ctx: Context) {
    super(ctx, 'governanceRuntime')
    this.runtimeContext = ctx

    ctx.effect(() => {
      const disposeReflectionProvider = ctx.agentGovernanceKernel.registerReflectionProvider({
        providerId: 'public.governance-runtime.semantic-executor',
        priority: 20_000,
        reflect: input => this.executeSemanticReflection(input),
      })
      return () => {
        disposeReflectionProvider()
        this.observations.clear()
        this.closeJobs.clear()
        this.reflectionJobs.clear()
        this.sessions.clear()
      }
    })
  }

  setSemanticExecutor(runtimeIdInput: string, executor: GovernanceSemanticExecutor): () => void {
    const runtimeId = cleanIdentifier('runtimeId', runtimeIdInput)
    if (!executor.executorId.trim()) throw new Error('semantic executorId cannot be empty')
    const session = this.sessions.get(runtimeId)
    if (!session) throw new Error(`Governance Runtime session not found: ${runtimeId}`)
    const previous = session.semanticExecutor
    session.semanticExecutor = executor
    return () => {
      if (previous) session.semanticExecutor = previous
      else delete session.semanticExecutor
    }
  }

  async openTurn(input: GovernanceOpenTurnInput): Promise<GovernanceOpenTurnResult> {
    const runtimeId = cleanIdentifier('runtimeId', input.runtimeId)
    const actorId = cleanIdentifier('actorId', input.actorId ?? runtimeId)
    const turnId = cleanIdentifier('turnId', input.turnId)
    const taskText = input.taskText.trim()
    if (!taskText) throw new Error('taskText cannot be empty')
    if (input.hostCapabilities && !input.supervisionEventStore) {
      throw new Error('Host capability facts require a supervised Runtime binding')
    }
    const requestedHostProfile = input.supervisionEventStore
      ? this.resolveHostProfile(
        input.supervisionEventStore.binding.contract.supervisionLevel,
        input.hostCapabilities,
        false,
      )
      : undefined

    const project = this.runtimeContext.autoGovernanceEngine.resolveProject({
      taskText,
      ...(input.projectId?.trim() ? { projectId: input.projectId.trim() } : {}),
      ...(input.workspacePath?.trim() ? { workspacePath: input.workspacePath.trim() } : {}),
    })
    if (!project) throw new Error('Governance Runtime could not resolve a project for this task')

    const taskId = cleanIdentifier(
      'taskId',
      input.taskId ?? `GOV-${taskToken(project.projectId)}-${taskToken(runtimeId)}`,
    )
    let session = this.sessions.get(runtimeId)
    if (session) {
      if (session.actorId !== actorId || session.projectId !== project.projectId || session.taskId !== taskId) {
        throw new Error(`Runtime ${runtimeId} is already bound to ${session.projectId}/${session.taskId}/${session.actorId}`)
      }
      if (session.supervision?.ledger.binding.turnId !== undefined
          && session.supervision.ledger.binding.turnId !== turnId) {
        throw new Error(
          `Runtime ${runtimeId} is supervised only for Turn ${session.supervision.ledger.binding.turnId}`,
        )
      }
      if (session.supervision && input.supervisionEventStore) {
        if (session.supervision.eventStore !== input.supervisionEventStore) {
          throw new Error(`Runtime ${runtimeId} is already bound to another Execution Event Store`)
        }
        this.assertCompatibleHostProfile(
          runtimeId,
          session.supervision.hostProfile,
          requestedHostProfile,
        )
      }
      if (session.activeTurnId) {
        const recoveringTurnId = session.activeTurnId
        const recovered = await this.closeKnownTurn(session, recoveringTurnId, {})
        if (recovered.closure.status !== 'COMPLETE' || session.activeTurnId) {
          throw new Error(`Runtime ${runtimeId} could not recover active Turn ${recoveringTurnId}`)
        }
      }
      await this.recoverUnresolvedTurns(session)
    } else {
      const unresolved = this.runtimeContext.agentGovernanceKernel.getUnresolvedTurns(taskId)
      if (unresolved.length > 0) {
        throw new Error(
          `Persisted unresolved Turn(s) exist for ${taskId}: ${unresolved.map(item => item.turnId).join(', ')}. `
          + 'Host-independent cross-process task rehydration is not implemented in Governance Runtime v0.1.',
        )
      }
      session = {
        runtimeId,
        actorId,
        projectId: project.projectId,
        taskId,
      }
      this.sessions.set(runtimeId, session)
    }

    const context = this.runtimeContext.autoGovernanceEngine.bootstrapTask({
      actorId,
      taskId,
      goal: taskText,
      projectId: project.projectId,
      ...(input.workspacePath?.trim() ? { workspacePath: input.workspacePath.trim() } : {}),
      phase: 'analysis',
    })
    session.contextHash = hashCanonicalJson(context)
    session.activeTurnTaskTextHash = sha256Hex(taskText)

    if (input.supervisionEventStore) {
      if (input.supervisionEventStore.binding.turnId !== turnId) {
        throw new Error(
          `Supervision turnId mismatch: ${input.supervisionEventStore.binding.turnId} != ${turnId}`,
        )
      }
      await this.bindSupervision(
        session,
        input.supervisionEventStore,
        context,
        input.hostCapabilities,
      )
    }
    if (input.semanticExecutor) session.semanticExecutor = input.semanticExecutor

    let journal = this.runtimeContext.agentGovernanceKernel.beginTurn({
      taskId,
      turnId,
      agentId: actorId,
      projectBinding: { kind: 'BOUND', projectId: project.projectId },
      stateVersionBefore: context.stateVersion,
      sessionRef: `governance-runtime://${runtimeId}`,
      ...(input.userMessageRefs ? { userMessageRefs: unique(input.userMessageRefs) } : {}),
    })
    const taskObservation = this.observations.put({
      taskId,
      turnId,
      kind: 'TASK_INPUT',
      text: taskText,
      refs: input.userMessageRefs ?? [],
      sourceName: 'business-task',
    })
    journal = this.runtimeContext.agentGovernanceKernel.appendTurnRefs(taskId, turnId, {
      userMessageRefs: [taskObservation.observationRef],
      resourceTouchRefs: unique([
        ...context.route.architectureIds,
        ...context.route.ruleIds,
        ...context.route.knowledgeIds,
        ...context.route.gateIds,
      ]),
      sessionRef: `governance-runtime://${runtimeId}`,
    })
    session.activeTurnId = turnId
    const knowledgeDecision = evaluateKnowledgeGovernanceDecision({
      stage: 'OPEN',
      context,
      observations: this.observations.list(taskId, turnId),
    })

    return {
      contractVersion: GOVERNANCE_RUNTIME_CONTRACT_VERSION,
      runtimeId,
      actorId,
      projectId: project.projectId,
      taskId,
      turnId,
      context,
      journal,
      taskObservation,
      knowledgeDecision,
    }
  }

  async bindSupervisedTurn(input: GovernanceBindSupervisedTurnInput): Promise<void> {
    const session = this.requireSession(input.runtimeId)
    if (!session.activeTurnId || input.eventStore.binding.turnId !== session.activeTurnId) {
      throw new Error('Execution Event Store does not match the active Runtime Turn')
    }
    const context = this.runtimeContext.autoGovernanceEngine.buildContextEnvelope(session.actorId)
    await this.bindSupervision(session, input.eventStore, context, input.hostCapabilities)
  }

  async rehydrateSupervisedTurn(input: GovernanceRehydrateSupervisedTurnInput): Promise<void> {
    const runtimeId = cleanIdentifier('runtimeId', input.runtimeId)
    const binding = input.eventStore.binding
    const contract = binding.contract
    this.resolveHostProfile(contract.supervisionLevel, input.hostCapabilities, true)
    if (binding.runtimeId !== runtimeId) {
      throw new Error(`Supervision Runtime identity mismatch: ${binding.runtimeId} != ${runtimeId}`)
    }
    let session = this.sessions.get(runtimeId)
    const isCrossProcessRestore = session === undefined
    if (!session) {
      const journal = this.runtimeContext.agentGovernanceKernel.getTurn(contract.taskId, binding.turnId)
      const reflection = this.runtimeContext.agentGovernanceKernel.getReflection(contract.taskId, binding.turnId)
      if (!journal) throw new Error('Cross-process supervised rehydration requires a durable Kernel Turn')
      if (journal.sessionRef !== `governance-runtime://${runtimeId}`) {
        throw new Error('Persisted Kernel Turn sessionRef does not match supervision Runtime identity')
      }
      if (journal.agentId !== contract.agentId
          || journal.projectBinding.kind !== 'BOUND'
          || journal.projectBinding.projectId !== contract.projectId) {
        throw new Error('Persisted Kernel Turn identity does not match supervision contract')
      }
      const taskText = await this.readDurableTaskText(input.eventStore)
      const project = this.runtimeContext.autoGovernanceEngine.resolveProject({
        taskText,
        projectId: contract.projectId,
      })
      if (!project || project.projectId !== contract.projectId) {
        throw new Error(`Supervised project cannot be restored: ${contract.projectId}`)
      }
      this.runtimeContext.autoGovernanceEngine.bootstrapTask({
        actorId: contract.agentId,
        taskId: contract.taskId,
        goal: taskText,
        projectId: contract.projectId,
        phase: 'implementation',
      })
      const context = this.runtimeContext.autoGovernanceEngine.buildContextEnvelope(contract.agentId)
      if (hashCanonicalJson(context.route) !== contract.routeHash) {
        throw new Error('Rehydrated Auto Governance route does not match the durable supervision routeHash')
      }
      session = {
        runtimeId,
        actorId: contract.agentId,
        projectId: contract.projectId,
        taskId: contract.taskId,
        ...(journal.status === 'CLOSED' ? {} : { activeTurnTaskTextHash: sha256Hex(taskText) }),
        contextHash: contract.contextHash,
        ...(journal.status === 'CLOSED' ? {} : { activeTurnId: binding.turnId }),
      }
      this.sessions.set(runtimeId, session)
    }
    await this.bindSupervision(
      session,
      input.eventStore,
      undefined,
      input.hostCapabilities,
      true,
    )
    if (isCrossProcessRestore) this.restoreAutoGovernanceFromDurableExecution(session)
    const decision = session.supervision!.ledger.getCompletionDecision()
    const currentReadiness = session.supervision!.ledger.getReadinessReceipt()
    if (decision.status !== 'COMPLETE') {
      const reflection = this.runtimeContext.agentGovernanceKernel.getReflection(
        contract.taskId,
        binding.turnId,
      )
      if (!reflection && !isCrossProcessRestore) {
        throw new Error('Persisted Reflection is not bound to the latest durable supervision readiness')
      }
      if (reflection && (!currentReadiness
          || reflectionBindingRef(reflection)
            !== `${currentReadiness.receiptRef}|${supervisionFingerprint(currentReadiness.receiptHash)}`)) {
        throw new Error('Persisted Reflection is not bound to the latest durable supervision readiness')
      }
    }
    if (decision.status !== 'COMPLETE') session.activeTurnId = binding.turnId
    if (input.semanticExecutor) session.semanticExecutor = input.semanticExecutor
  }

  async ingestExecutionEvent(
    input: GovernanceHostExecutionEventInput,
  ): Promise<GovernanceHostExecutionEventResult> {
    const session = this.requireActiveTurn(input.runtimeId, input.turnId)
    this.requireOpenJournal(session, input.turnId)
    const supervision = session.supervision
    if (!supervision) throw new Error('Execution supervision is not bound to the active Runtime Turn')

    const operation = enqueueRuntimeExecutionEvent(supervision, input, {
      schema: EXECUTION_EVENT_SCHEMA,
      hashPayload: hashCanonicalJson,
      now: () => new Date().toISOString(),
      cleanEventId: value => cleanIdentifier('eventId', value),
    })
    return {
      ...await operation,
      supervision: this.supervisionStatus(supervision),
    }
  }

  observeWork(input: GovernanceWorkObservation): GovernanceWorkObservationResult {
    const session = this.requireActiveTurn(input.runtimeId, input.turnId)
    this.requireOpenJournal(session, input.turnId)
    let context: AutoGovernanceContextEnvelope
    let journal: TurnJournalRecord
    let observation: GovernanceTurnObservation

    switch (input.kind) {
      case 'tool-result': {
        observation = this.observations.put({
          taskId: session.taskId,
          turnId: input.turnId,
          kind: 'TOOL_RESULT',
          text: input.summary,
          refs: unique([
            ...(input.eventRef?.trim() ? [input.eventRef.trim()] : []),
            ...(input.resourceRefs ?? []),
          ]),
          sourceName: input.name,
          isError: input.isError,
        })
        context = this.runtimeContext.autoGovernanceEngine.observeToolResult({
          actorId: session.actorId,
          name: input.name,
          ...(input.arguments !== undefined ? { arguments: input.arguments } : {}),
          ...(input.isError !== undefined ? { isError: input.isError } : {}),
        })
        journal = this.runtimeContext.agentGovernanceKernel.appendTurnRefs(session.taskId, input.turnId, {
          toolEventRefs: unique([
            observation.observationRef,
            ...(input.eventRef?.trim() ? [input.eventRef.trim()] : []),
          ]),
          ...(input.resourceRefs ? { resourceTouchRefs: unique(input.resourceRefs) } : {}),
        })
        break
      }
      case 'resource-touch':
        observation = this.observations.put({
          taskId: session.taskId,
          turnId: input.turnId,
          kind: 'RESOURCE_TOUCH',
          text: input.summary,
          refs: input.resourceRefs,
          sourceName: 'resource-touch',
        })
        context = this.runtimeContext.autoGovernanceEngine.buildContextEnvelope(session.actorId)
        journal = this.runtimeContext.agentGovernanceKernel.appendTurnRefs(session.taskId, input.turnId, {
          resourceTouchRefs: unique([...input.resourceRefs, observation.observationRef]),
        })
        break
      case 'assistant-message':
        observation = this.observations.put({
          taskId: session.taskId,
          turnId: input.turnId,
          kind: 'ASSISTANT_MESSAGE',
          text: input.text,
          refs: input.messageRefs,
          sourceName: 'assistant-visible-output',
        })
        context = this.runtimeContext.autoGovernanceEngine.buildContextEnvelope(session.actorId)
        journal = this.runtimeContext.agentGovernanceKernel.appendTurnRefs(session.taskId, input.turnId, {
          assistantMessageRefs: unique([...input.messageRefs, observation.observationRef]),
        })
        break
      case 'user-message':
        observation = this.observations.put({
          taskId: session.taskId,
          turnId: input.turnId,
          kind: 'USER_MESSAGE',
          text: input.text,
          refs: input.messageRefs,
          sourceName: 'user-visible-input',
        })
        context = this.runtimeContext.autoGovernanceEngine.buildContextEnvelope(session.actorId)
        journal = this.runtimeContext.agentGovernanceKernel.appendTurnRefs(session.taskId, input.turnId, {
          userMessageRefs: unique([...input.messageRefs, observation.observationRef]),
        })
        break
    }
    const knowledgeDecision = evaluateKnowledgeGovernanceDecision({
      stage: 'OBSERVE',
      context,
      observations: this.observations.list(session.taskId, input.turnId),
    })
    return { context, journal, observation, knowledgeDecision }
  }

  getTurnObservations(runtimeIdInput: string, turnIdInput: string): readonly GovernanceTurnObservation[] {
    const session = this.requireSession(runtimeIdInput)
    const turnId = cleanIdentifier('turnId', turnIdInput)
    return this.observations.list(session.taskId, turnId)
  }

  preflightAction(input: GovernanceActionPreflightInput): GovernanceActionPreflightResult {
    const session = this.requireActiveTurn(input.runtimeId, input.turnId)
    const profile = session.supervision?.hostProfile
    if (session.supervision && profile?.negotiation.effectiveLevel === 'ENFORCE') {
      if (!input.eventRef?.trim()) {
        return {
          allowed: false,
          reason: 'Supervised ENFORCE actions require a stable Host tool event identity.',
        }
      }
      if (!input.effect) {
        return {
          allowed: false,
          reason: 'Supervised ENFORCE actions require a trusted tool effect declaration.',
        }
      }
      if (input.effect.kind === 'MUTATION') {
        const scope = evaluateMutationPreflight(
          session.supervision.ledger.binding.contract,
          input.effect.intent,
        )
        if (!scope.allowed) {
          return {
            allowed: false,
            ...(scope.reason ? { reason: scope.reason } : {}),
          }
        }
      }
    }
    const reason = this.runtimeContext.autoGovernanceEngine.guardAction({
      actorId: session.actorId,
      name: input.name,
      ...(input.arguments !== undefined ? { arguments: input.arguments } : {}),
    })
    return reason ? { allowed: false, reason } : { allowed: true }
  }

  preflightGateEvidenceProducer(
    input: GovernanceGateEvidenceProducerPreflightInput,
  ): GovernanceActionPreflightResult {
    const session = this.requireActiveTurn(input.runtimeId, input.turnId)
    const profile = session.supervision?.hostProfile
    if (session.supervision
        && profile?.negotiation.effectiveLevel === 'ENFORCE'
        && !input.eventRef?.trim()) {
      return {
        allowed: false,
        reason: 'Supervised ENFORCE Gate producers require a stable Host tool event identity.',
      }
    }
    const reason = this.runtimeContext.autoGovernanceEngine.guardGateEvidenceProducer({
      actorId: session.actorId,
      name: input.name,
      ...(input.arguments !== undefined ? { arguments: input.arguments } : {}),
      gateId: input.gateId,
      stepId: input.stepId,
      capability: input.capability,
    })
    return reason ? { allowed: false, reason } : { allowed: true }
  }

  async closeTurn(input: GovernanceCloseTurnInput): Promise<GovernanceCloseTurnResult> {
    const session = this.requireSession(input.runtimeId)
    if (session.supervision && session.supervision.ledger.binding.turnId !== input.turnId) {
      throw new Error('Supervision Event Store cannot authorize a different Turn')
    }
    if (session.activeTurnId !== input.turnId) {
      const journal = this.runtimeContext.agentGovernanceKernel.getTurn(session.taskId, input.turnId)
      if (!journal || journal.status === 'CLOSED') {
        throw new Error(`Turn ${input.turnId} is not active for runtime ${session.runtimeId}`)
      }
    }
    if (input.semanticExecutor) session.semanticExecutor = input.semanticExecutor
    if (input.assistantMessageRefs) {
      this.runtimeContext.agentGovernanceKernel.appendTurnRefs(session.taskId, input.turnId, {
        assistantMessageRefs: unique(input.assistantMessageRefs),
      })
    }
    const key = reflectionKey(session.taskId, input.turnId)
    const existingJob = this.closeJobs.get(key)
    if (existingJob) return existingJob
    const job = this.closeKnownTurn(session, input.turnId, {
      ...(input.publicCandidateRefs ? { publicCandidateRefs: input.publicCandidateRefs } : {}),
      ...(input.projectCandidateRefs ? { projectCandidateRefs: input.projectCandidateRefs } : {}),
    })
    this.closeJobs.set(key, job)
    try {
      return await job
    } finally {
      if (this.closeJobs.get(key) === job) this.closeJobs.delete(key)
    }
  }

  recordReviewDecision(input: GovernanceRuntimeReviewDecisionInput): GovernanceRuntimeReviewDecisionResult {
    this.requireSession(input.runtimeId)
    return this.runtimeContext.autoGovernanceEngine.recordReviewDecision({
      packetId: input.packetId,
      result: input.result,
      summary: input.summary,
      reviewerId: input.reviewerId,
      ...(input.findings ? { findings: input.findings } : {}),
    })
  }

  completeTask(runtimeIdInput: string) {
    const session = this.requireSession(runtimeIdInput)
    if (session.activeTurnId) {
      return {
        projectId: session.projectId,
        taskId: session.taskId,
        status: 'BLOCKED' as const,
        reason: `Turn ${session.activeTurnId} is still active.`,
      }
    }
    const unresolved = this.runtimeContext.agentGovernanceKernel.getUnresolvedTurns(session.taskId)
    if (unresolved.length > 0) {
      return {
        projectId: session.projectId,
        taskId: session.taskId,
        status: 'BLOCKED' as const,
        reason: `Unresolved governance Turns remain: ${unresolved.map(item => item.turnId).join(', ')}`,
      }
    }
    if (session.supervision) {
      return this.completeSupervisedTask(session)
    }
    return this.runtimeContext.autoGovernanceEngine.completeTask(session.actorId)
  }

  private async completeSupervisedTask(session: RuntimeSession) {
    const supervision = session.supervision!
    await supervision.ledger.synchronize()
    const decision = supervision.ledger.getCompletionDecision()
    const finalization = supervision.eventStore.finalization
    if (decision.status !== 'COMPLETE'
        || !decision.closureRef
        || finalization?.finalizationRef !== decision.closureRef) {
      return {
        projectId: session.projectId,
        taskId: session.taskId,
        status: 'BLOCKED' as const,
        reason: 'Execution Supervisor has not admitted the exact durable lifecycle Closure.',
      }
    }
    return this.runtimeContext.autoGovernanceEngine.completeTask(session.actorId)
  }

  pauseTask(runtimeIdInput: string): void {
    const session = this.requireSession(runtimeIdInput)
    if (session.activeTurnId) throw new Error(`Cannot pause runtime with active Turn ${session.activeTurnId}`)
    this.runtimeContext.autoGovernanceEngine.pauseTask(session.actorId)
  }

  /** Last synchronized snapshot only. This synchronous view is not completion authority. */
  getStatus(runtimeIdInput: string): GovernanceRuntimeStatus | undefined {
    const runtimeId = runtimeIdInput.trim()
    const session = this.sessions.get(runtimeId)
    if (!session) return undefined
    const autoGovernance = this.runtimeContext.autoGovernanceEngine.getTaskStatus(session.actorId)
    if (!autoGovernance) return undefined
    const unresolvedTurnIds = this.runtimeContext.agentGovernanceKernel
      .getUnresolvedTurns(session.taskId)
      .map(item => item.turnId)
    return {
      runtimeId,
      actorId: session.actorId,
      projectId: session.projectId,
      taskId: session.taskId,
      ...(session.activeTurnId ? { activeTurnId: session.activeTurnId } : {}),
      autoGovernance,
      unresolvedTurnIds,
      ...(session.supervision ? { supervision: this.supervisionStatus(session.supervision) } : {}),
    }
  }

  private async recoverUnresolvedTurns(session: RuntimeSession): Promise<void> {
    const unresolved = this.runtimeContext.agentGovernanceKernel.getUnresolvedTurns(session.taskId)
    if (unresolved.length === 0) return
    for (const turn of unresolved) {
      await this.closeKnownTurn(session, turn.turnId, {})
    }
  }

  private async closeKnownTurn(
    session: RuntimeSession,
    turnId: string,
    candidateRefs: {
      readonly publicCandidateRefs?: readonly string[]
      readonly projectCandidateRefs?: readonly string[]
    },
  ): Promise<GovernanceCloseTurnResult> {
    let readiness: SupervisionReadinessReceiptV01 | undefined
    if (session.supervision) {
      if (session.activeTurnId !== turnId
          || session.supervision.ledger.binding.turnId !== turnId) {
        throw new Error('Supervised Closure identity does not match the active Runtime Turn')
      }
      const preparedReadiness = await session.supervision.ledger.prepareReadiness()
      const decision = session.supervision.ledger.getCompletionDecision()
      if (decision.status === 'COMPLETE') {
        readiness = undefined
      } else {
        readiness = preparedReadiness
        if (!readiness || decision.status !== 'READY_TO_CLOSE') {
          throw new Error(`Execution Supervisor blocks Turn Closure: ${decision.status}`)
        }
        if (readiness.turnId !== turnId) {
          throw new Error('Supervision readiness cannot authorize a different Turn')
        }
      }
    }
    const existingReflection = this.runtimeContext.agentGovernanceKernel.getReflection(session.taskId, turnId)
    const executor = session.semanticExecutor
    const key = reflectionKey(session.taskId, turnId)
    if (!existingReflection && !executor) {
      throw new Error(`SemanticExecutor is required to close Turn ${turnId}`)
    }
    if (executor) {
      this.reflectionJobs.set(key, {
        runtimeId: session.runtimeId,
        actorId: session.actorId,
        projectId: session.projectId,
        taskId: session.taskId,
        turnId,
        executor,
      })
    }

    try {
      if (session.supervision && readiness && !existingReflection) {
        const durableTaskText = await this.readDurableTaskText(session.supervision.eventStore)
        if (sha256Hex(durableTaskText) !== session.activeTurnTaskTextHash) {
          throw new Error('Durable USER_MESSAGE task input does not match the Runtime task input')
        }
        await this.projectTrustedExecutionObservations(
          session,
          turnId,
          session.supervision.eventStore,
          readiness,
        )
      }
      const reflection = existingReflection ?? await this.runtimeContext.agentGovernanceKernel.reflectTurn(
        session.taskId,
        turnId,
        {
          taskContextRef: `context://project/${session.projectId}/${session.taskId}`,
          ...(candidateRefs.publicCandidateRefs
            ? { publicCandidateRefs: unique(candidateRefs.publicCandidateRefs) }
            : {}),
          ...(candidateRefs.projectCandidateRefs
            ? { projectCandidateRefs: unique(candidateRefs.projectCandidateRefs) }
            : {}),
          ...(readiness ? {
            readinessBinding: {
              ref: readiness.receiptRef,
              fingerprint: supervisionFingerprint(readiness.receiptHash),
            },
          } : {}),
        },
      )
      const decisionContext = this.runtimeContext.autoGovernanceEngine.buildContextEnvelope(session.actorId)
      const knowledgeDecision = evaluateKnowledgeGovernanceDecision({
        stage: 'CLOSE',
        context: decisionContext,
        observations: this.observations.list(session.taskId, turnId),
        reflection: reflection.result,
      })
      if (knowledgeDecision.captureMode === 'REQUIRED' && reflection.result.knowledge.candidates.length === 0) {
        throw new Error(`Knowledge Governance requires capture for Turn ${turnId}, but Reflection emitted NONE`)
      }
      const closure = await this.runtimeContext.agentGovernanceKernel.closeTurn(session.taskId, turnId)
      let supervisionDecision: CompletionDecisionV01 | undefined
      let knowledgeVerifications: GovernanceKnowledgeVerificationResult[] = []
      let knowledgeVerificationWarnings: string[] = []
      let knowledgePromotions: GovernanceKnowledgePromotion[] = []
      let knowledgePromotionWarnings: string[] = []
      if (closure.status === 'COMPLETE') {
        if (session.supervision) {
          const currentReadiness = readiness ?? session.supervision.ledger.getReadinessReceipt()
          if (!currentReadiness) {
            const existingDecision = session.supervision.ledger.getCompletionDecision()
            if (existingDecision.status !== 'COMPLETE') {
              throw new Error('Execution Supervisor readiness is unavailable for Kernel Closure')
            }
            supervisionDecision = existingDecision
          } else {
            const binding = this.buildLifecycleBinding(session, currentReadiness, reflection, closure)
            supervisionDecision = await session.supervision.ledger.attachLifecycleClosure(binding)
          }
          if (supervisionDecision.status !== 'COMPLETE') {
            throw new Error(`Execution Supervisor rejected Kernel Closure: ${supervisionDecision.status}`)
          }
        }
        if (session.activeTurnId === turnId) {
          delete session.activeTurnId
          delete session.activeTurnTaskTextHash
        }
        try {
          const verificationFeedback = this.applyKnowledgeVerificationReflections(
            session.projectId,
            decisionContext.route.knowledgeIds,
            reflection.result,
            closure.attemptId,
          )
          knowledgeVerifications = [...verificationFeedback.results]
          knowledgeVerificationWarnings = [...verificationFeedback.warnings]
          knowledgePromotions = [...verificationFeedback.promotions]
          const postClosure = this.autoValidateKnowledgeCandidates(session.projectId, closure)
          knowledgePromotions = mergeKnowledgePromotions([
            ...knowledgePromotions,
            ...postClosure.promotions,
          ])
          knowledgePromotionWarnings = [...postClosure.warnings]
        } catch (error) {
          knowledgePromotionWarnings = [
            `Knowledge post-Closure validation failed without reopening Turn ${turnId}: ${errorText(error)}`,
          ]
        }
      }
      const context = this.runtimeContext.autoGovernanceEngine.buildContextEnvelope(session.actorId)
      return {
        contractVersion: GOVERNANCE_RUNTIME_CONTRACT_VERSION,
        runtimeId: session.runtimeId,
        taskId: session.taskId,
        turnId,
        reflection,
        closure,
        context,
        knowledgeDecision,
        knowledgeVerifications,
        knowledgeVerificationWarnings,
        knowledgePromotions,
        knowledgePromotionWarnings,
        ...(session.supervision ? { supervision: this.supervisionStatus(session.supervision) } : {}),
      }
    } finally {
      this.reflectionJobs.delete(key)
    }
  }

  private restoreAutoGovernanceFromDurableExecution(session: RuntimeSession): void {
    if (!session.activeTurnId || !session.supervision) return
    const resourceWriteCount = [...session.supervision.eventsById.values()]
      .filter(event => event.kind === 'RESOURCE_WRITE').length
    if (resourceWriteCount === 0) return
    // A durable write proves code may have changed, but in-memory Review decisions
    // are not durable Evidence. Recreate a fresh fail-closed review epoch instead
    // of silently trusting pre-restart packet state.
    this.runtimeContext.autoGovernanceEngine.observeToolResult({
      actorId: session.actorId,
      name: 'write_file_durable_rehydration',
      arguments: {
        source: 'trusted-execution-event-store',
        resourceWriteCount,
      },
    })
  }

  private async bindSupervision(
    session: RuntimeSession,
    eventStore: ExecutionEventStoreV01,
    context?: AutoGovernanceContextEnvelope,
    hostCapabilities?: HostCapabilityContractV01,
    finalizedRecovery = false,
  ): Promise<void> {
    const binding = eventStore.binding
    const contract = binding.contract
    for (const [label, actual, expected] of [
      ['runtimeId', binding.runtimeId, session.runtimeId],
      ['projectId', contract.projectId, session.projectId],
      ['taskId', contract.taskId, session.taskId],
      ['agentId', contract.agentId, session.actorId],
    ] as const) {
      if (actual !== expected) throw new Error(`Supervision ${label} mismatch: ${actual} != ${expected}`)
    }
    if (session.contextHash !== contract.contextHash) {
      throw new Error('Runtime session Context does not match supervision contextHash')
    }
    if (session.activeTurnId && binding.turnId !== session.activeTurnId) {
      throw new Error(`Supervision turnId mismatch: ${binding.turnId} != ${session.activeTurnId}`)
    }
    const hostProfile = this.resolveHostProfile(
      contract.supervisionLevel,
      hostCapabilities,
      finalizedRecovery,
    )
    if (session.supervision && session.supervision.eventStore !== eventStore) {
      throw new Error(`Runtime ${session.runtimeId} is already bound to another Execution Event Store`)
    }
    if (session.supervision) {
      this.assertCompatibleHostProfile(
        session.runtimeId,
        session.supervision.hostProfile,
        hostProfile,
      )
      return
    }
    if (context) {
      if (hashCanonicalJson(context.route) !== contract.routeHash) {
        throw new Error('Auto Governance route does not match supervision routeHash')
      }
      if (session.contextHash !== contract.contextHash) {
        throw new Error('Auto Governance Context does not match supervision contextHash')
      }
    } else if (!finalizedRecovery) {
      throw new Error('Live Auto Governance Context is required to bind a supervised Turn')
    }
    const authority: ExecutionLifecycleAuthorityV01 = {
      verifyLifecycleClosure: lifecycle => this.verifyKernelLifecycleBinding(lifecycle),
    }
    const ledger = await createExecutionObligationLedger({ eventStore, lifecycleAuthority: authority })
    const eventsById = await this.indexExecutionEvents(eventStore)
    session.supervision = {
      eventStore,
      ledger,
      ...(hostProfile ? { hostProfile } : {}),
      eventsById,
      ingestTail: Promise.resolve(),
    }
  }

  private async indexExecutionEvents(
    eventStore: ExecutionEventStoreV01,
  ): Promise<Map<string, RuntimeExecutionEventIdentity>> {
    const eventsById = new Map<string, RuntimeExecutionEventIdentity>()
    let after: ExecutionEventStoreV01['cursor'] | undefined
    do {
      const page = await eventStore.replay({
        ...(after ? { after } : {}),
        limit: Math.max(1, eventStore.limits.maxReplayEvents),
      })
      for (const event of page.events) eventsById.set(event.eventId, {
        sequence: event.sequence,
        timestamp: event.timestamp,
        kind: event.kind,
        payloadHash: event.payloadHash,
      })
      if (!page.hasMore) break
      after = page.cursor
    } while (true)
    if (eventsById.size !== eventStore.eventCount) {
      throw new Error('Execution Event Store contains duplicate event identities')
    }
    return eventsById
  }

  private resolveHostProfile(
    requestedLevel: 'AUDIT' | 'ENFORCE',
    value: HostCapabilityContractV01 | undefined,
    finalizedRecovery: boolean,
  ): GovernanceHostSupervisionProfile | undefined {
    if (!value) {
      if (requestedLevel === 'ENFORCE') {
        throw new Error('Supervised ENFORCE requires an explicit Host capability contract')
      }
      return undefined
    }
    const validation = validateHostCapabilityContract(value)
    if (!validation.valid) {
      throw new Error(`Invalid Host capability contract: ${validation.issues
        .map(issue => `${issue.path} ${issue.message}`)
        .join('; ')}`)
    }
    const capabilities: HostCapabilityContractV01 = {
      schema: validation.value.schema,
      hostId: validation.value.hostId,
      adapterId: validation.value.adapterId,
      capabilities: { ...validation.value.capabilities },
    }
    const negotiation = negotiateSupervisionLevel(requestedLevel, capabilities)
    if (finalizedRecovery
        && negotiation.effectiveLevel === 'ENFORCE'
        && !capabilities.capabilities.supportsCrossProcessResume) {
      throw new Error('ENFORCE Host profile does not support cross-process resume')
    }
    return {
      capabilities,
      negotiation: {
        requestedLevel: negotiation.requestedLevel,
        effectiveLevel: negotiation.effectiveLevel,
        reasons: [...negotiation.reasons],
      },
      claimsMechanicalInterception: negotiation.effectiveLevel === 'ENFORCE',
    }
  }

  private assertCompatibleHostProfile(
    runtimeId: string,
    existing: GovernanceHostSupervisionProfile | undefined,
    requested: GovernanceHostSupervisionProfile | undefined,
  ): void {
    if (!requested) return
    if (!existing || hashCanonicalJson(existing) !== hashCanonicalJson(requested)) {
      throw new Error(`Runtime ${runtimeId} is already bound to another Host profile`)
    }
  }

  private async readDurableTaskText(eventStore: ExecutionEventStoreV01): Promise<string> {
    let after: ExecutionEventStoreV01['cursor'] | undefined
    do {
      const page = await eventStore.replay({
        ...(after ? { after } : {}),
        limit: Math.max(1, eventStore.limits.maxReplayEvents),
      })
      for (const event of page.events) {
        if (event.kind !== 'USER_MESSAGE') continue
        const text = visibleExecutionMessage(event)
        if (text?.trim()) return text.trim()
      }
      if (!page.hasMore) break
      after = page.cursor
    } while (true)
    throw new Error('Finalized supervision stream does not contain a durable USER_MESSAGE task input')
  }

  private supervisionStatus(supervision: RuntimeSupervision) {
    const readiness = supervision.ledger.getReadinessReceipt()
    return {
      ...(supervision.hostProfile
        ? { hostProfile: structuredClone(supervision.hostProfile) }
        : {}),
      ledger: supervision.ledger.getStatus(),
      decision: supervision.ledger.getCompletionDecision(),
      ...(readiness ? { readiness } : {}),
    }
  }

  private buildLifecycleBinding(
    session: RuntimeSession,
    readiness: SupervisionReadinessReceiptV01,
    reflection: TurnReflectionRecord,
    closure: import('@agent-harness/agent-governance-kernel').TurnClosureReceipt,
  ): SupervisionLifecycleBindingV01 {
    const journal = this.runtimeContext.agentGovernanceKernel.getTurn(session.taskId, readiness.turnId)
    if (!journal?.closureReceiptRef) throw new Error('Kernel Closure receipt reference is unavailable')
    return {
      schema: SUPERVISION_LIFECYCLE_BINDING_SCHEMA,
      readinessRef: readiness.receiptRef,
      readinessHash: readiness.receiptHash,
      projectId: readiness.projectId,
      taskId: readiness.taskId,
      turnId: readiness.turnId,
      agentId: readiness.agentId,
      contextHash: readiness.contextHash,
      journalRef: closure.journalRef,
      reflection: {
        reflectionRef: closure.reflectionRef,
        inputFingerprint: reflection.inputFingerprint,
        domainDecisions: {
          knowledge: reflection.result.knowledge.scopeDecision,
          experience: reflection.result.experience.scopeDecision,
          architecture: reflection.result.architecture.scopeDecision,
          rules: reflection.result.rules.scopeDecision,
          evidence: reflection.result.evidence.scopeDecision,
        },
      },
      kernelClosureRef: journal.closureReceiptRef,
      kernelClosureInputFingerprint: closure.inputFingerprint,
      kernelClosureCreatedAt: closure.createdAt,
      moduleReceipts: closure.moduleReceipts.map(receipt => ({
        moduleId: receipt.moduleId,
        moduleVersion: receipt.moduleVersion,
        status: receipt.status === 'APPLIED' || receipt.status === 'NO_CHANGE'
          ? receipt.status
          : (() => { throw new Error(`Kernel Closure module is not successful: ${receipt.moduleId}`) })(),
        idempotencyKey: receipt.idempotencyKey,
      })),
    }
  }

  private verifyKernelLifecycleBinding(binding: SupervisionLifecycleBindingV01): void {
    const reflection = this.runtimeContext.agentGovernanceKernel.getReflection(binding.taskId, binding.turnId)
    const closure = this.runtimeContext.agentGovernanceKernel.getClosureReceipt(binding.taskId, binding.turnId)
    const journal = this.runtimeContext.agentGovernanceKernel.getTurn(binding.taskId, binding.turnId)
    if (!reflection || !closure || !journal || closure.status !== 'COMPLETE' || !journal.closureReceiptRef) {
      throw new Error('Kernel does not hold one COMPLETE lifecycle receipt for this binding')
    }
    const expectedReadinessBinding = {
      ref: binding.readinessRef,
      fingerprint: supervisionFingerprint(binding.readinessHash),
    }
    if (reflection.readinessBinding?.ref !== expectedReadinessBinding.ref
        || reflection.readinessBinding?.fingerprint !== expectedReadinessBinding.fingerprint
        || closure.readinessBinding?.ref !== expectedReadinessBinding.ref
        || closure.readinessBinding?.fingerprint !== expectedReadinessBinding.fingerprint) {
      throw new Error('Durable Kernel Reflection/Closure is not bound to the exact supervision readiness')
    }
    const expected = this.buildLifecycleBinding({
      runtimeId: '',
      actorId: binding.agentId,
      projectId: binding.projectId,
      taskId: binding.taskId,
    }, {
      schema: 'agent-harness.supervision-readiness-receipt.v0.1',
      requestId: '', runtimeId: '', projectId: binding.projectId, taskId: binding.taskId,
      turnId: binding.turnId, agentId: binding.agentId, contextHash: binding.contextHash,
      contractHash: '', cursor: { sequence: 0, stateHash: '' }, ledgerStatusHash: '', decisionHash: '',
      taskEndEventId: '', taskEndTimestamp: closure.createdAt,
      receiptHash: binding.readinessHash, receiptRef: binding.readinessRef,
    }, reflection, closure)
    if (hashCanonicalJson(expected) !== hashCanonicalJson(binding)) {
      throw new Error('Lifecycle binding does not exactly match durable Kernel receipts')
    }
  }

  private async projectTrustedExecutionObservations(
    session: RuntimeSession,
    turnId: string,
    eventStore: ExecutionEventStoreV01,
    readiness: SupervisionReadinessReceiptV01,
  ): Promise<void> {
    if (eventStore.cursor.sequence !== readiness.cursor.sequence
        || eventStore.cursor.stateHash !== readiness.cursor.stateHash) {
      throw new Error('Execution Event Store advanced after readiness was frozen')
    }
    const sourceName = `trusted-execution-event-store:${readiness.cursor.stateHash}`
    const existing = this.observations.list(session.taskId, turnId)
      .find(item => item.sourceName === sourceName)
    if (existing) return
    const projectedKinds = [
      'USER_MESSAGE',
      'ASSISTANT_MESSAGE',
      'TASK_END_REQUEST',
      'VALIDATION_RESULT',
      'OUTPUT_EMITTED',
      'SOURCE_DISPOSITION',
    ] as const
    const projectedKindSet = new Set<ExecutionEventEnvelopeV01['kind']>(projectedKinds)
    interface ProjectionSummary {
      readonly sequence: number
      readonly eventId: string
      readonly kind: ExecutionEventEnvelopeV01['kind']
      readonly payloadHash: string
      readonly trustedPayload?: unknown
    }
    const buckets = new Map<string, ProjectionSummary[]>()
    const compactReceipt = (event: ExecutionEventEnvelopeV01): unknown => {
      const receipt = recordValue(recordValue(event.payload)?.receipt)
      if (!receipt) return undefined
      const keep = event.kind === 'VALIDATION_RESULT'
        ? ['providerId', 'validationId', 'targetIdentity', 'resultStatus', 'timestamp']
        : event.kind === 'OUTPUT_EMITTED'
          ? ['providerId', 'outputContractId', 'resourceId', 'path', 'contentHash', 'structuralValidationStatus', 'timestamp']
          : ['provider', 'resourceId', 'disposition', 'purpose', 'error']
      const result: Record<string, unknown> = {}
      for (const key of keep) {
        const value = receipt[key]
        if (typeof value === 'string') result[key] = value.slice(0, 2_000)
      }
      for (const key of ['artifactRefs', 'evidenceRefs', 'ruleValidationRefs']) {
        const value = receipt[key]
        if (Array.isArray(value)) result[key] = value.filter(item => typeof item === 'string').slice(0, 8)
      }
      return result
    }
    const summarize = (event: ExecutionEventEnvelopeV01): ProjectionSummary => {
      let trustedPayload: unknown
      if (event.kind === 'USER_MESSAGE' || event.kind === 'ASSISTANT_MESSAGE') {
        const content = visibleExecutionMessage(event)
        if (content !== undefined) trustedPayload = { content: content.slice(0, 2_000) }
      } else if (event.kind === 'TASK_END_REQUEST') {
        const requestedBy = recordValue(event.payload)?.requestedBy
        if (typeof requestedBy === 'string') trustedPayload = { requestedBy }
      } else if (['VALIDATION_RESULT', 'OUTPUT_EMITTED', 'SOURCE_DISPOSITION'].includes(event.kind)) {
        trustedPayload = { receipt: compactReceipt(event) }
      }
      return {
        sequence: event.sequence,
        eventId: event.eventId,
        kind: event.kind,
        payloadHash: event.payloadHash,
        ...(trustedPayload === undefined ? {} : { trustedPayload }),
      }
    }
    const retain = (bucket: ProjectionSummary[], summary: ProjectionSummary, limit: number): void => {
      if (bucket.length < limit) bucket.push(summary)
      else bucket[bucket.length - 1] = summary
    }
    const kindCounts = new Map<string, number>()
    let eventCount = 0
    let after: ExecutionEventStoreV01['cursor'] | undefined
    do {
      const page = await eventStore.replay({
        ...(after ? { after } : {}),
        limit: Math.max(1, eventStore.limits.maxReplayEvents),
      })
      for (const event of page.events) {
        eventCount += 1
        kindCounts.set(event.kind, (kindCounts.get(event.kind) ?? 0) + 1)
        const bucketKey = projectedKindSet.has(event.kind) ? event.kind : 'OTHER'
        const bucket = buckets.get(bucketKey) ?? []
        retain(bucket, summarize(event), bucketKey === 'OTHER' ? 6 : 4)
        buckets.set(bucketKey, bucket)
      }
      if (!page.hasMore) break
      after = page.cursor
    } while (true)
    if (eventStore.cursor.sequence !== readiness.cursor.sequence
        || eventStore.cursor.stateHash !== readiness.cursor.stateHash
        || eventCount !== eventStore.eventCount) {
      throw new Error('Execution Event Store changed while trusted observations were projected')
    }
    const sampledEvents = [
      ...projectedKinds.flatMap(kind => buckets.get(kind) ?? []),
      ...(buckets.get('OTHER') ?? []),
    ]
    const observation = this.observations.put({
      taskId: session.taskId,
      turnId,
      kind: 'RESOURCE_TOUCH',
      text: JSON.stringify({
        trustedExecutionProjection: 'v0.1',
        cursor: readiness.cursor,
        eventCount,
        kindCounts: Object.fromEntries([...kindCounts].sort(([left], [right]) => left.localeCompare(right))),
        sampledEvents,
      }),
      refs: [
        `execution-store-cursor://sha256:${readiness.cursor.stateHash}`,
        ...sampledEvents.map(event => `execution-event://${event.eventId}`),
      ],
      sourceName,
    })
    this.runtimeContext.agentGovernanceKernel.appendTurnRefs(session.taskId, turnId, {
      toolEventRefs: [observation.observationRef],
    })
  }

  private async executeSemanticReflection(input: TurnReflectionProviderInput): Promise<unknown> {
    const key = reflectionKey(input.journal.taskId, input.journal.turnId)
    const job = this.reflectionJobs.get(key)
    if (!job) throw new Error(`Governance Runtime semantic job not found: ${key}`)
    const request = this.buildSemanticRequest(job, input.journal)
    return job.executor.reflect(request)
  }

  private buildSemanticRequest(job: ReflectionJob, journal: TurnReflectionProviderInput['journal']): GovernanceSemanticRequest {
    const context = this.runtimeContext.autoGovernanceEngine.buildContextEnvelope(job.actorId)
    const projectTaxonomy = this.runtimeContext.knowledgeManager.getTaxonomy(job.projectId)
    const publicMounted = this.runtimeContext.knowledgeManager.isGlobalLibraryMounted()
    const publicTaxonomy = publicMounted
      ? this.runtimeContext.knowledgeManager.getGlobalTaxonomy()
      : undefined
    return {
      contractVersion: GOVERNANCE_RUNTIME_CONTRACT_VERSION,
      runtimeId: job.runtimeId,
      actorId: job.actorId,
      projectId: job.projectId,
      taskId: job.taskId,
      turnId: job.turnId,
      journal,
      context,
      turnObservations: this.observations.list(job.taskId, job.turnId),
      knowledgeValidation: {
        projectSources: this.sourceOptions(this.runtimeContext.knowledgeManager.listProjectSources(job.projectId), 'PROJECT', job.projectId),
        publicSources: publicMounted
          ? this.sourceOptions(this.runtimeContext.knowledgeManager.listGlobalSources(), 'PUBLIC')
          : [],
      },
      knowledgeClassification: {
        projectCategories: this.categoryOptions(projectTaxonomy, 'PROJECT', job.projectId),
        publicLibraryMounted: publicMounted,
        publicCategories: this.categoryOptions(publicTaxonomy, 'PUBLIC'),
      },
      requirements: [
        'Return one valid TurnReflectionResult for this exact taskId and turnId.',
        'Use turnObservations as the authoritative bounded record of visible task/work outputs; never invent or expose hidden chain-of-thought.',
        'Every knowledge / experience / architecture / rules / evidence section must explicitly choose NONE, PROJECT, PUBLIC, or BOTH.',
        'Use NONE when this Turn produced no durable candidate for that domain; never create a candidate only to avoid NONE.',
        'Every emitted candidate must be supported by Context or turnObservations and use PROJECT, PUBLIC, or BOTH.',
        'Every Knowledge candidate must include knowledge-category://project/<categoryId> and/or knowledge-category://public/<categoryId> in relatedRefs for every selected persistence scope.',
        'When a Knowledge candidate is directly supported by an observed registered document/spec/SVD source, include its source:// reference in provenanceRefs or relatedRefs; do not cite a source merely because it exists.',
        'When a Knowledge candidate is directly supported by pre-existing PASS validation evidence, include its evidence:// reference; Runtime, not the model, decides the resulting validation tier.',
        'Routed Knowledge may be FULL_VALIDATED, VALIDATED, CANDIDATE, DEPRECATED, or validation-BLOCKED. Use CANDIDATE only as a hypothesis/test lead and DEPRECATED only as history.',
        'When this Turn produces a real source/evidence result that SUPPORTS or CONTRADICTS a routed/touched Knowledge item, emit knowledgeVerifications with knowledgeRef, relation, basisRefs, and rationale. Do not guess a relation from prose alone.',
        'Do not claim MUST Gate obligations are resolved unless real PASS Evidence exists; never manufacture PASS evidence from prose conclusions.',
        'Architecture and Rule findings are change candidates, not direct edits to canonical Architecture/Rule resources.',
      ],
    }
  }


  private applyKnowledgeVerificationReflections(
    projectId: string,
    routedKnowledgeRefs: readonly string[],
    reflection: TurnReflectionRecord['result'],
    closureAttemptId: string,
  ): {
    readonly results: readonly GovernanceKnowledgeVerificationResult[]
    readonly promotions: readonly GovernanceKnowledgePromotion[]
    readonly warnings: readonly string[]
  } {
    const proposals = reflection.knowledgeVerifications ?? []
    if (proposals.length === 0) return { results: [], promotions: [], warnings: [] }
    const manager = this.runtimeContext.knowledgeManager
    const policy = (this.runtimeContext as unknown as {
      knowledgeValidationPolicy?: {
        evaluate(reference: string, currentProjectId?: string): import('@agent-harness/knowledge-manager').KnowledgeValidationEvaluation
        promote(reference: string, currentProjectId?: string): import('@agent-harness/knowledge-manager').KnowledgePromotionResult
      }
    }).knowledgeValidationPolicy
    if (!policy) {
      return {
        results: [],
        promotions: [],
        warnings: ['Knowledge Verification feedback skipped: knowledgeValidationPolicy is unavailable.'],
      }
    }

    const allowedKnowledgeUris = new Set<string>()
    for (const reference of unique([
      ...routedKnowledgeRefs,
      ...reflection.context.touchedRefs,
    ])) {
      try {
        const resolved = manager.resolveKnowledgeReference(reference, projectId)
        if (resolved?.result.node.isLeaf) allowedKnowledgeUris.add(resolved.knowledgeUri)
      } catch {
        // Non-Knowledge touched refs are expected.
      }
    }

    const results: GovernanceKnowledgeVerificationResult[] = []
    const promotions: GovernanceKnowledgePromotion[] = []
    const warnings: string[] = []
    for (const proposal of proposals) {
      try {
        const target = manager.resolveKnowledgeReference(proposal.knowledgeRef, projectId)
        const node = target?.result.node
        if (!target || !node?.isLeaf || !node.status) {
          throw new Error(`Knowledge Verification target not found: ${proposal.knowledgeRef}`)
        }
        if (!allowedKnowledgeUris.has(target.knowledgeUri)) {
          throw new Error(
            `Knowledge Verification target was neither routed nor touched in this Turn: ${target.knowledgeUri}`,
          )
        }
        const basisRefs = unique(proposal.basisRefs)
        const currentFingerprint = policy.evaluate(target.knowledgeUri, projectId).knowledgeFingerprint
        const existing = new Set(
          manager.listVerifications(target.knowledgeUri)
            .filter(item => item.knowledgeFingerprint === currentFingerprint)
            .map(item => `${item.relation}:${item.basisRef}`),
        )
        for (const basisRef of basisRefs) {
          const duplicateKey = `${proposal.relation}:${basisRef}`
          if (existing.has(duplicateKey)) continue
          const record = manager.recordVerification({
            knowledgeUri: target.knowledgeUri,
            basisRef,
            relation: proposal.relation,
            note: `${proposal.rationale} (Closure ${closureAttemptId})`,
          })
          existing.add(`${record.relation}:${record.basisRef}`)
        }

        const evaluation = policy.evaluate(target.knowledgeUri, projectId)
        let resultingStatus = node.status
        if (
          proposal.relation === 'SUPPORT'
          && evaluation.decision === 'READY'
          && evaluation.targetStatus
          && node.status !== 'DEPRECATED'
          && node.status !== 'FULL_VALIDATED'
        ) {
          const promoted = policy.promote(target.knowledgeUri, projectId)
          resultingStatus = promoted.mutation.status
          promotions.push({
            knowledgeUri: target.knowledgeUri,
            fromStatus: node.status,
            toStatus: promoted.mutation.status as 'VALIDATED' | 'FULL_VALIDATED',
            basisRefs,
          })
        }
        results.push({
          knowledgeUri: target.knowledgeUri,
          relation: proposal.relation,
          basisRefs,
          decision: evaluation.decision,
          resultingStatus,
        })
      } catch (error) {
        warnings.push(`${proposal.knowledgeRef}: ${errorText(error)}`)
      }
    }
    return {
      results,
      promotions: mergeKnowledgePromotions(promotions),
      warnings: unique(warnings),
    }
  }

  private autoValidateKnowledgeCandidates(
    projectId: string,
    closure: import('@agent-harness/agent-governance-kernel').TurnClosureReceipt,
  ): {
    readonly promotions: readonly GovernanceKnowledgePromotion[]
    readonly warnings: readonly string[]
  } {
    const receipt = closure.moduleReceipts.find(item => item.moduleId === 'knowledge-closure')
    if (!receipt) return { promotions: [], warnings: [] }
    const manager = this.runtimeContext.knowledgeManager
    const policy = (this.runtimeContext as unknown as {
      knowledgeValidationPolicy?: {
        evaluate(reference: string, currentProjectId?: string): import('@agent-harness/knowledge-manager').KnowledgeValidationEvaluation
        promote(reference: string, currentProjectId?: string): import('@agent-harness/knowledge-manager').KnowledgePromotionResult
      }
    }).knowledgeValidationPolicy
    if (!policy) return { promotions: [], warnings: [] }
    const promotions: GovernanceKnowledgePromotion[] = []
    const warnings: string[] = []

    for (const knowledgeUri of unique(receipt.candidateRefs)) {
      try {
        const target = manager.resolveKnowledgeReference(knowledgeUri, projectId)
        const node = target?.result.node
        if (!target || !node?.isLeaf || !node.status || node.status === 'DEPRECATED' || node.status === 'FULL_VALIDATED') continue
        const basisRefs = unique(node.refs.filter(ref => ref.startsWith('source://') || ref.startsWith('evidence://')))
        const existing = manager.listVerifications(target.knowledgeUri)
        for (const basisRef of basisRefs) {
          if (existing.some(record => record.basisRef === basisRef && record.relation === 'SUPPORT')) continue
          try {
            manager.recordVerification({
              knowledgeUri: target.knowledgeUri,
              basisRef,
              relation: 'SUPPORT',
              note: `Auto-recorded by Governance Runtime closure ${closure.attemptId}`,
            })
          } catch (error) {
            warnings.push(`${target.knowledgeUri}: ignored unverifiable ${basisRef}: ${errorText(error)}`)
          }
        }
        const evaluation = policy.evaluate(target.knowledgeUri, projectId)
        if (evaluation.decision !== 'READY' || !evaluation.targetStatus) continue
        const fromStatus = node.status
        const promoted = policy.promote(target.knowledgeUri, projectId)
        if (promoted.mutation.status !== evaluation.targetStatus) {
          warnings.push(
            `${target.knowledgeUri}: promotion returned ${promoted.mutation.status}, expected ${evaluation.targetStatus}`,
          )
          continue
        }
        promotions.push({
          knowledgeUri: target.knowledgeUri,
          fromStatus,
          toStatus: evaluation.targetStatus,
          basisRefs,
        })
      } catch (error) {
        warnings.push(`${knowledgeUri}: ${errorText(error)}`)
      }
    }
    return { promotions, warnings: unique(warnings) }
  }

  private sourceOptions(
    sources: readonly import('@agent-harness/knowledge-manager').KnowledgeSourceRecord[],
    scope: 'PROJECT' | 'PUBLIC',
    projectId?: string,
  ): GovernanceKnowledgeSourceOption[] {
    return sources
      .filter(source => source.status === 'ACTIVE')
      .map(source => ({
        sourceRef: scope === 'PROJECT'
          ? `source://project/${projectId}/${source.sourceId}`
          : `source://global/${source.sourceId}`,
        kind: source.kind,
        title: source.title,
        location: source.location,
        ...(source.revision ? { revision: source.revision } : {}),
      }))
  }

  private categoryOptions(
    taxonomy: KnowledgeTaxonomy | undefined,
    scope: 'PROJECT' | 'PUBLIC',
    projectId?: string,
  ): GovernanceKnowledgeCategoryOption[] {
    if (!taxonomy) return []
    return Object.values(taxonomy.categories)
      .filter(category => category.status === 'ACTIVE')
      .sort((left, right) => left.id.localeCompare(right.id))
      .map(category => this.categoryOption(category, scope, projectId))
  }

  private categoryOption(
    category: KnowledgeCategory,
    scope: 'PROJECT' | 'PUBLIC',
    projectId?: string,
  ): GovernanceKnowledgeCategoryOption {
    const categoryRef = scope === 'PROJECT'
      ? `knowledge-category://project/${category.id}`
      : `knowledge-category://public/${category.id}`
    return {
      scope,
      categoryId: category.id,
      categoryRef,
      title: category.title,
      ...(category.parentId ? { parentId: category.parentId } : {}),
      ...(category.summary ? { summary: category.summary } : {}),
    }
  }

  private requireSession(runtimeIdInput: string): RuntimeSession {
    const runtimeId = cleanIdentifier('runtimeId', runtimeIdInput)
    const session = this.sessions.get(runtimeId)
    if (!session) throw new Error(`Governance Runtime session not found: ${runtimeId}`)
    return session
  }

  private requireActiveTurn(runtimeIdInput: string, turnIdInput: string): RuntimeSession {
    const session = this.requireSession(runtimeIdInput)
    const turnId = cleanIdentifier('turnId', turnIdInput)
    if (session.activeTurnId !== turnId) {
      throw new Error(`Runtime ${session.runtimeId} active Turn is ${session.activeTurnId ?? 'none'}, not ${turnId}`)
    }
    return session
  }

  private requireOpenJournal(session: RuntimeSession, turnId: string): TurnJournalRecord {
    const journal = this.runtimeContext.agentGovernanceKernel.getTurn(session.taskId, turnId)
    if (!journal) throw new Error(`Turn Journal not found: ${session.taskId}/${turnId}`)
    if (journal.status !== 'OPEN') {
      throw new Error(`Turn ${turnId} is ${journal.status}; governed observations are sealed`)
    }
    return journal
  }
}

declare module '@deepseek-ai/cordis' {
  interface Context {
    governanceRuntime: GovernanceRuntimeService
  }
}

export default GovernanceRuntimeService
