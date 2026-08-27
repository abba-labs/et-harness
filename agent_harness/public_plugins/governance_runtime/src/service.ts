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
import { evaluateKnowledgeGovernanceDecision } from './knowledge-governance-decision.js'
import {
  GOVERNANCE_RUNTIME_CONTRACT_VERSION,
  type GovernanceActionPreflightInput,
  type GovernanceActionPreflightResult,
  type GovernanceCloseTurnInput,
  type GovernanceCloseTurnResult,
  type GovernanceKnowledgeCategoryOption,
  type GovernanceKnowledgeDecision,
  type GovernanceKnowledgePromotion,
  type GovernanceKnowledgeSourceOption,
  type GovernanceKnowledgeVerificationResult,
  type GovernanceOpenTurnInput,
  type GovernanceOpenTurnResult,
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

interface RuntimeSession {
  runtimeId: string
  actorId: string
  projectId: string
  taskId: string
  activeTurnId?: string
  semanticExecutor?: GovernanceSemanticExecutor
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
      if (input.semanticExecutor) session.semanticExecutor = input.semanticExecutor
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
        ...(input.semanticExecutor ? { semanticExecutor: input.semanticExecutor } : {}),
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
    const reason = this.runtimeContext.autoGovernanceEngine.guardAction({
      actorId: session.actorId,
      name: input.name,
      ...(input.arguments !== undefined ? { arguments: input.arguments } : {}),
    })
    return reason ? { allowed: false, reason } : { allowed: true }
  }

  async closeTurn(input: GovernanceCloseTurnInput): Promise<GovernanceCloseTurnResult> {
    const session = this.requireSession(input.runtimeId)
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
    return this.closeKnownTurn(session, input.turnId, {
      ...(input.publicCandidateRefs ? { publicCandidateRefs: input.publicCandidateRefs } : {}),
      ...(input.projectCandidateRefs ? { projectCandidateRefs: input.projectCandidateRefs } : {}),
    })
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
    return this.runtimeContext.autoGovernanceEngine.completeTask(session.actorId)
  }

  pauseTask(runtimeIdInput: string): void {
    const session = this.requireSession(runtimeIdInput)
    if (session.activeTurnId) throw new Error(`Cannot pause runtime with active Turn ${session.activeTurnId}`)
    this.runtimeContext.autoGovernanceEngine.pauseTask(session.actorId)
  }

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
      let knowledgeVerifications: GovernanceKnowledgeVerificationResult[] = []
      let knowledgeVerificationWarnings: string[] = []
      let knowledgePromotions: GovernanceKnowledgePromotion[] = []
      let knowledgePromotionWarnings: string[] = []
      if (closure.status === 'COMPLETE') {
        if (session.activeTurnId === turnId) delete session.activeTurnId
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
      }
    } finally {
      this.reflectionJobs.delete(key)
    }
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
