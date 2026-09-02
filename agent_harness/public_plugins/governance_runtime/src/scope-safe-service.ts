import type { Context } from '@deepseek-ai/cordis'
import {
  reflectionInputFingerprint,
  validateTurnReflectionResult,
} from '@agent-harness/agent-governance-kernel'
import {
  evaluateMutationPreflight,
  hashCanonicalJson,
} from '@agent-harness/execution-supervisor'
import { evaluateKnowledgeGovernanceDecision } from './knowledge-governance-decision.js'
import type {
  GovernanceActionPreflightInput,
  GovernanceActionPreflightResult,
  GovernanceCloseTurnInput,
  GovernanceCloseTurnResult,
  GovernanceSemanticRequest,
} from './contracts.js'
import GovernanceRuntimeService from './service.js'

/**
 * Keeps deterministic Task Contract scope checks active for every explicit
 * Runtime preflight, even when a Host can only negotiate AUDIT supervision.
 *
 * AUDIT still does not claim that the Host intercepts every native tool call.
 * This only makes an explicit preflight truthful and fail-closed for mutations.
 */
export class ScopeSafeGovernanceRuntimeService extends GovernanceRuntimeService {
  private readonly lifecycleContext: Context

  constructor(ctx: Context) {
    super(ctx)
    this.lifecycleContext = ctx
  }

  override preflightAction(
    input: GovernanceActionPreflightInput,
  ): GovernanceActionPreflightResult {
    // Preserve the canonical Runtime identity/Turn/policy checks first. Under
    // ENFORCE this already performs the scope check and also verifies the Host
    // interception/event-identity contract.
    const base = super.preflightAction(input)
    if (!base.allowed || input.effect?.kind !== 'MUTATION') return base

    // AUDIT cannot claim universal Host interception, but an explicit preflight
    // still has a frozen Task Contract and therefore must answer scope truthfully.
    const contract = this.getStatus(input.runtimeId)?.supervision?.ledger.binding.contract
    if (!contract) return base
    const scope = evaluateMutationPreflight(contract, input.effect.intent)
    if (!scope.allowed) {
      return {
        allowed: false,
        reason: scope.reason ?? 'Mutation is outside the governed WRITE_SCOPE.',
      }
    }
    return base
  }

  override async closeTurn(input: GovernanceCloseTurnInput): Promise<GovernanceCloseTurnResult> {
    const status = this.getStatus(input.runtimeId)
    if (!status || status.activeTurnId === input.turnId) {
      const result = await super.closeTurn(input)
      return result.closure.status === 'COMPLETE'
        ? this.terminalizeCompletedContext(result)
        : result
    }

    const journal = this.lifecycleContext.agentGovernanceKernel.getTurn(status.taskId, input.turnId)
    const reflection = this.lifecycleContext.agentGovernanceKernel.getReflection(status.taskId, input.turnId)
    const closure = this.lifecycleContext.agentGovernanceKernel.getClosureReceipt(status.taskId, input.turnId)
    if (!journal || journal.status !== 'CLOSED' || !reflection || !closure || closure.status !== 'COMPLETE') {
      return super.closeTurn(input)
    }
    if (status.supervision?.decision.status !== 'COMPLETE') {
      throw new Error(`Closed Turn ${input.turnId} has no exact supervised lifecycle finalization`)
    }
    if (input.assistantMessageRefs?.some(ref => !journal.assistantMessageRefs.includes(ref.trim()))) {
      throw new Error(`Turn Closure replay input changed: ${status.taskId}/${input.turnId}`)
    }

    const replayFingerprint = reflectionInputFingerprint({
      journal,
      taskContextRef: `context://project/${status.projectId}/${status.taskId}`,
      publicCandidateRefs: input.publicCandidateRefs ?? [],
      projectCandidateRefs: input.projectCandidateRefs ?? [],
      ...(reflection.readinessBinding ? { readinessBinding: reflection.readinessBinding } : {}),
    })
    if (replayFingerprint !== reflection.inputFingerprint) {
      throw new Error(`Turn Closure replay input changed: ${status.taskId}/${input.turnId}`)
    }

    if (input.semanticExecutor) {
      const expectedExecutorId = `governance-host-port:${input.runtimeId}:${input.turnId}`
      if (input.semanticExecutor.executorId !== expectedExecutorId) {
        throw new Error('Closed Turn replay does not execute a new semantic provider')
      }
      const proposed = await input.semanticExecutor.reflect({
        runtimeId: input.runtimeId,
        turnId: input.turnId,
      } as GovernanceSemanticRequest)
      const normalized = validateTurnReflectionResult(proposed, journal)
      if (hashCanonicalJson(normalized) !== hashCanonicalJson(reflection.result)) {
        throw new Error(`Turn Closure replay Reflection changed: ${status.taskId}/${input.turnId}`)
      }
    }

    if (!journal.closureReceiptRef) {
      throw new Error(`Closed Turn ${input.turnId} has no durable Closure reference`)
    }
    this.lifecycleContext.contextManager.completeFromClosure(
      status.projectId,
      status.taskId,
      input.turnId,
      journal.closureReceiptRef,
    )
    const context = this.lifecycleContext.autoGovernanceEngine.buildContextEnvelope(status.actorId)
    const knowledgeDecision = evaluateKnowledgeGovernanceDecision({
      stage: 'CLOSE',
      context,
      observations: [],
      reflection: reflection.result,
    })
    return {
      contractVersion: '0.1',
      runtimeId: input.runtimeId,
      taskId: status.taskId,
      turnId: input.turnId,
      reflection,
      closure,
      context,
      knowledgeDecision,
      knowledgeVerifications: [],
      knowledgeVerificationWarnings: [],
      knowledgePromotions: [],
      knowledgePromotionWarnings: [],
      supervision: status.supervision,
    }
  }

  private terminalizeCompletedContext(
    result: GovernanceCloseTurnResult,
  ): GovernanceCloseTurnResult {
    const status = this.getStatus(result.runtimeId)
    const journal = this.lifecycleContext.agentGovernanceKernel.getTurn(result.taskId, result.turnId)
    if (!status || !journal?.closureReceiptRef) {
      throw new Error(`Completed Turn ${result.turnId} has no durable lifecycle identity`)
    }
    this.lifecycleContext.contextManager.completeFromClosure(
      status.projectId,
      result.taskId,
      result.turnId,
      journal.closureReceiptRef,
    )
    return {
      ...result,
      context: this.lifecycleContext.autoGovernanceEngine.buildContextEnvelope(status.actorId),
      ...(status.supervision ? { supervision: status.supervision } : {}),
    }
  }
}

export default ScopeSafeGovernanceRuntimeService
