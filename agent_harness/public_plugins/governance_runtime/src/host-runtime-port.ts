import type {
  GovernanceActionPreflightInput,
  GovernanceActionPreflightResult,
  GovernanceCloseTurnInput,
  GovernanceCloseTurnResult,
  GovernanceHostExecutionEventInput,
  GovernanceHostExecutionEventResult,
  GovernanceOpenTurnInput,
  GovernanceOpenTurnResult,
  GovernanceRuntimeStatus,
  GovernanceWorkObservation,
  GovernanceWorkObservationResult,
} from './contracts.js'

export const GOVERNANCE_HOST_RUNTIME_PORT_VERSION = '0.1' as const

export type GovernanceHostAwaitable<T> = T | Promise<T>

/**
 * Host-neutral surface exposed to replaceable adapters. It intentionally omits
 * Event Store, Obligation Ledger, Project internals and completion authority.
 */
export type GovernanceHostOpenTurnInput = Omit<
  GovernanceOpenTurnInput,
  'supervisionEventStore' | 'hostCapabilities'
>

/**
 * Serializable Closure input used across a Host transport boundary.
 *
 * A Host may propose one visible structured Reflection value, but it cannot
 * send a SemanticExecutor function or acquire Reflection/Closure authority.
 * Runtime and Kernel validation remain authoritative.
 */
export type GovernanceHostCloseTurnInput = Omit<
  GovernanceCloseTurnInput,
  'semanticExecutor'
> & {
  readonly semanticReflection?: unknown
}

export interface GovernanceHostRuntimePortV01 {
  readonly version: typeof GOVERNANCE_HOST_RUNTIME_PORT_VERSION
  openTurn(input: GovernanceHostOpenTurnInput): Promise<GovernanceOpenTurnResult>
  ingestExecutionEvent(
    input: GovernanceHostExecutionEventInput,
  ): Promise<GovernanceHostExecutionEventResult>
  preflightAction(
    input: GovernanceActionPreflightInput,
  ): GovernanceHostAwaitable<GovernanceActionPreflightResult>
  observeWork(
    input: GovernanceWorkObservation,
  ): GovernanceHostAwaitable<GovernanceWorkObservationResult>
  closeTurn(input: GovernanceHostCloseTurnInput): Promise<GovernanceCloseTurnResult>
  pauseTask(runtimeId: string): GovernanceHostAwaitable<void>
  getStatus(
    runtimeId: string,
  ): GovernanceHostAwaitable<GovernanceRuntimeStatus | undefined>
}

export interface GovernanceHostSupervisedTurnOpenerV01 {
  /** Must return only after Runtime-owned supervision is bound to the Turn. */
  openSupervisedTurn(input: GovernanceHostOpenTurnInput): Promise<GovernanceOpenTurnResult>
}

interface HostVisibleRuntimeOperations {
  ingestExecutionEvent(
    input: GovernanceHostExecutionEventInput,
  ): Promise<GovernanceHostExecutionEventResult>
  preflightAction(
    input: GovernanceActionPreflightInput,
  ): GovernanceHostAwaitable<GovernanceActionPreflightResult>
  observeWork(
    input: GovernanceWorkObservation,
  ): GovernanceHostAwaitable<GovernanceWorkObservationResult>
  closeTurn(input: GovernanceCloseTurnInput): Promise<GovernanceCloseTurnResult>
  pauseTask(runtimeId: string): GovernanceHostAwaitable<void>
  getStatus(
    runtimeId: string,
  ): GovernanceHostAwaitable<GovernanceRuntimeStatus | undefined>
}

const runtimeCloseInput = (
  input: GovernanceHostCloseTurnInput,
): GovernanceCloseTurnInput => {
  const closeInput: GovernanceCloseTurnInput = {
    runtimeId: input.runtimeId,
    turnId: input.turnId,
    ...(input.assistantMessageRefs === undefined
      ? {}
      : { assistantMessageRefs: input.assistantMessageRefs }),
    ...(input.publicCandidateRefs === undefined
      ? {}
      : { publicCandidateRefs: input.publicCandidateRefs }),
    ...(input.projectCandidateRefs === undefined
      ? {}
      : { projectCandidateRefs: input.projectCandidateRefs }),
  }
  if (input.semanticReflection === undefined) return closeInput

  let consumed = false
  return {
    ...closeInput,
    semanticExecutor: {
      executorId: `governance-host-port:${input.runtimeId}:${input.turnId}`,
      reflect: request => {
        if (request.runtimeId !== input.runtimeId || request.turnId !== input.turnId) {
          throw new Error('Host Reflection proposal does not match the Runtime/Turn binding')
        }
        if (consumed) throw new Error('Host Reflection proposal was already consumed')
        consumed = true
        return input.semanticReflection
      },
    },
  }
}

/**
 * Builds the least-authority adapter view. The trusted opener stays on the
 * Runtime composition side and may own Contract/Store creation and binding;
 * none of those capabilities cross this returned Port.
 */
export const createGovernanceHostRuntimePortV01 = (
  runtime: HostVisibleRuntimeOperations,
  opener: GovernanceHostSupervisedTurnOpenerV01,
): GovernanceHostRuntimePortV01 => {
  const port: GovernanceHostRuntimePortV01 = {
    version: GOVERNANCE_HOST_RUNTIME_PORT_VERSION,
    openTurn: input => opener.openSupervisedTurn(input),
    ingestExecutionEvent: input => runtime.ingestExecutionEvent(input),
    preflightAction: input => runtime.preflightAction(input),
    observeWork: input => runtime.observeWork(input),
    closeTurn: input => runtime.closeTurn(runtimeCloseInput(input)),
    pauseTask: runtimeId => runtime.pauseTask(runtimeId),
    getStatus: runtimeId => runtime.getStatus(runtimeId),
  }
  return Object.freeze(port)
}
