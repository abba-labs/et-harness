import type {
  GovernanceCloseTurnResult,
  GovernanceOpenTurnResult,
  GovernanceRuntimeService,
  GovernanceTurnObservation,
} from '@agent-harness/governance-runtime'
import {
  createGovernanceSemanticExecutor,
  createGovernedModelWorkExecutor,
  type GenericModelClient,
  type GovernedModelWorkResult,
} from '@agent-harness/generic-model-adapter'

export interface GenericModelPilotTurnInput {
  readonly runtimeId: string
  readonly turnId: string
  /** Original business task. No governance instructions are added to this value. */
  readonly taskText: string
  readonly projectId?: string
  readonly workspacePath?: string
  readonly actorId?: string
  readonly additionalToolResults?: readonly {
    readonly name: string
    readonly summary: string
    readonly resourceRefs?: readonly string[]
    readonly isError?: boolean
  }[]
}

export interface GenericModelPilotTurnResult {
  readonly open: GovernanceOpenTurnResult
  readonly work: GovernedModelWorkResult
  readonly assistantObservation: GovernanceTurnObservation
  readonly close: GovernanceCloseTurnResult
}

export class GenericModelPilotDriver {
  private readonly semanticExecutor
  private readonly workExecutor

  constructor(
    private readonly runtime: GovernanceRuntimeService,
    private readonly modelClient: GenericModelClient,
  ) {
    this.semanticExecutor = createGovernanceSemanticExecutor(modelClient)
    this.workExecutor = createGovernedModelWorkExecutor(modelClient)
  }

  async runTurn(input: GenericModelPilotTurnInput): Promise<GenericModelPilotTurnResult> {
    const open = await this.runtime.openTurn({
      runtimeId: input.runtimeId,
      turnId: input.turnId,
      taskText: input.taskText,
      ...(input.projectId ? { projectId: input.projectId } : {}),
      ...(input.workspacePath ? { workspacePath: input.workspacePath } : {}),
      ...(input.actorId ? { actorId: input.actorId } : {}),
      semanticExecutor: this.semanticExecutor,
    })

    const work = await this.workExecutor.execute({
      runtimeId: open.runtimeId,
      taskId: open.taskId,
      turnId: open.turnId,
      taskText: input.taskText,
      context: open.context,
      knowledgeDecision: open.knowledgeDecision,
    })
    const messageRef = `model-output://${this.modelClient.clientId}/${open.runtimeId}/${open.turnId}`
    const observed = this.runtime.observeWork({
      kind: 'assistant-message',
      runtimeId: open.runtimeId,
      turnId: open.turnId,
      messageRefs: [messageRef],
      text: work.visibleOutput,
    })
    for (const extra of input.additionalToolResults ?? []) {
      this.runtime.observeWork({
        kind: 'tool-result',
        runtimeId: open.runtimeId,
        turnId: open.turnId,
        name: extra.name,
        summary: extra.summary,
        ...(extra.resourceRefs ? { resourceRefs: extra.resourceRefs } : {}),
        ...(extra.isError !== undefined ? { isError: extra.isError } : {}),
      })
    }
    const close = await this.runtime.closeTurn({
      runtimeId: open.runtimeId,
      turnId: open.turnId,
    })
    return {
      open,
      work,
      assistantObservation: observed.observation,
      close,
    }
  }
}

export default GenericModelPilotDriver
