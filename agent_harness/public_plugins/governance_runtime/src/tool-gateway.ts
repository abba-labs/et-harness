import type {
  GovernanceActionPreflightInput,
  GovernanceActionPreflightResult,
  GovernanceActionEffect,
  GovernanceWorkObservationResult,
} from './contracts.js'
import type { MutationIntentV01 } from '@agent-harness/execution-supervisor'

export interface GovernanceToolRuntimePort {
  preflightAction(input: GovernanceActionPreflightInput): GovernanceActionPreflightResult
  observeWork(input: {
    readonly kind: 'tool-result'
    readonly runtimeId: string
    readonly turnId: string
    readonly name: string
    readonly arguments?: unknown
    readonly isError?: boolean
    readonly eventRef?: string
    readonly resourceRefs?: readonly string[]
    readonly summary?: string
  }): GovernanceWorkObservationResult
}

export interface GovernedToolInvocation {
  readonly runtimeId: string
  readonly turnId: string
  readonly name: string
  readonly arguments?: unknown
  readonly eventRef?: string
  readonly resourceRefs?: readonly string[]
}

export interface GovernedRawToolResult<T = unknown> {
  readonly value: T
  readonly summary?: string
  readonly resourceRefs?: readonly string[]
  readonly eventRef?: string
  readonly isError?: boolean
}

export type GovernedRawToolExecutor<T = unknown> = (
  invocation: Pick<GovernedToolInvocation, 'name' | 'arguments'>,
) => Promise<GovernedRawToolResult<T>> | GovernedRawToolResult<T>

type GovernedToolPlanningInput = Pick<GovernedToolInvocation, 'name' | 'arguments'>

export type GovernedToolEffectDefinition =
  | { readonly kind: 'READ_ONLY' }
  | {
      readonly kind: 'MUTATION'
      readonly intent: (invocation: GovernedToolPlanningInput) => MutationIntentV01
    }

export interface GovernedToolDefinition<T = unknown> {
  readonly name: string
  readonly execute: GovernedRawToolExecutor<T>
  /** Trusted registration-side effect metadata; never supplied by the Agent invocation. */
  readonly effect?: GovernedToolEffectDefinition
  /** Trusted Host event identity mapper required by supervised ENFORCE. */
  readonly eventIdentity?: (invocation: GovernedToolPlanningInput) => string
}

export type GovernedToolExecutionResult<T = unknown> =
  | {
      readonly status: 'BLOCKED'
      readonly executorCalled: false
      readonly preflight: GovernanceActionPreflightResult
    }
  | {
      readonly status: 'EXECUTED'
      readonly executorCalled: true
      readonly preflight: GovernanceActionPreflightResult
      readonly result: T
      readonly observation: GovernanceWorkObservationResult
    }
  | {
      readonly status: 'ERROR'
      readonly executorCalled: true
      readonly preflight: GovernanceActionPreflightResult
      readonly error: string
      readonly observation: GovernanceWorkObservationResult
    }

interface RegisteredGovernedTool {
  readonly name: string
  readonly execute: GovernedRawToolExecutor<unknown>
  readonly effect?: GovernedToolEffectDefinition
  readonly eventIdentity?: (invocation: GovernedToolPlanningInput) => string
}

const errorText = (error: unknown): string => {
  const raw = error instanceof Error ? error.message : String(error)
  return raw.replace(/\s+/g, ' ').trim().slice(0, 1200) || 'Tool execution failed'
}

const keyOf = (name: string): string => name.trim().toLowerCase()
const compactName = (name: string): string => name.toLowerCase().replace(/[^a-z0-9]/g, '')
const unique = (values: readonly string[]): string[] =>
  [...new Set(values.map(value => value.trim()).filter(Boolean))]

const validateEffectDefinition = (effect: GovernedToolEffectDefinition | undefined): void => {
  if (!effect) return
  const keys = Object.keys(effect).sort()
  if (effect.kind === 'READ_ONLY'
      && keys.length === 1
      && keys[0] === 'kind') return
  if (effect.kind === 'MUTATION'
      && keys.length === 2
      && keys[0] === 'intent'
      && keys[1] === 'kind'
      && typeof effect.intent === 'function') return
  throw new Error('Governed Tool effect definition is malformed or unsupported')
}

const RESERVED_GOVERNANCE_MUTATION_SUFFIXES = [
  'evidencestatemanagerrecordevidence',
  'evidencestatemanagerupdatestate',
  'knowledgemanagerrecordverification',
  'knowledgemanagersubmitknowledgecandidate',
  'knowledgemanagersubmitglobalknowledgecandidate',
  'knowledgevalidationpolicypromote',
] as const

export function isForbiddenAgentFacingToolName(name: string): boolean {
  const compact = compactName(name)
  if (compact === 'recordevidence' || compact === 'evidencerecord') return true
  return RESERVED_GOVERNANCE_MUTATION_SUFFIXES.some(suffix => compact.endsWith(suffix))
}

/**
 * Canonical model-facing tool boundary.
 *
 * Raw executors are registered once inside the Gateway. The model-facing
 * adapter receives only listToolNames()/execute(); it cannot supply a raw
 * callback per invocation or directly register Governance mutation APIs.
 */
export class GovernedToolGateway {
  private readonly tools = new Map<string, RegisteredGovernedTool>()

  constructor(
    private readonly runtime: GovernanceToolRuntimePort,
    definitions: readonly GovernedToolDefinition[],
  ) {
    for (const definition of definitions) {
      const name = definition.name.trim()
      if (!name) throw new Error('Governed Tool name cannot be empty')
      validateEffectDefinition(definition.effect)
      if (isForbiddenAgentFacingToolName(name)) {
        throw new Error(`Agent-facing tool is a reserved Governance mutation capability: ${name}`)
      }
      const key = keyOf(name)
      if (this.tools.has(key)) throw new Error(`Duplicate Governed Tool registration: ${name}`)
      const effect = definition.effect?.kind === 'READ_ONLY'
        ? { kind: 'READ_ONLY' as const }
        : definition.effect?.kind === 'MUTATION'
          ? { kind: 'MUTATION' as const, intent: definition.effect.intent }
          : undefined
      this.tools.set(key, {
        name,
        execute: definition.execute as GovernedRawToolExecutor<unknown>,
        ...(effect ? { effect } : {}),
        ...(definition.eventIdentity ? { eventIdentity: definition.eventIdentity } : {}),
      })
    }
  }

  listToolNames(): readonly string[] {
    return [...this.tools.values()].map(tool => tool.name).sort()
  }

  async execute<T = unknown>(
    invocation: GovernedToolInvocation,
  ): Promise<GovernedToolExecutionResult<T>> {
    const tool = this.tools.get(keyOf(invocation.name))
    if (!tool) {
      return {
        status: 'BLOCKED',
        executorCalled: false,
        preflight: {
          allowed: false,
          reason: `Governed Tool is not registered for the Agent: ${invocation.name}`,
        },
      }
    }

    const planningInput: GovernedToolPlanningInput = {
      name: tool.name,
      ...(invocation.arguments !== undefined ? { arguments: invocation.arguments } : {}),
    }
    let effect: GovernanceActionEffect | undefined
    let trustedEventRef: string | undefined
    try {
      effect = tool.effect?.kind === 'MUTATION'
        ? { kind: 'MUTATION', intent: tool.effect.intent(planningInput) }
        : tool.effect
      trustedEventRef = tool.eventIdentity?.(planningInput)?.trim()
    } catch (error) {
      return {
        status: 'BLOCKED',
        executorCalled: false,
        preflight: {
          allowed: false,
          reason: `Trusted tool preflight planning failed: ${errorText(error)}`,
        },
      }
    }

    const preflight = this.runtime.preflightAction({
      runtimeId: invocation.runtimeId,
      turnId: invocation.turnId,
      name: tool.name,
      ...(invocation.arguments !== undefined ? { arguments: invocation.arguments } : {}),
      ...(trustedEventRef ? { eventRef: trustedEventRef } : {}),
      ...(effect ? { effect } : {}),
    })
    if (!preflight.allowed) {
      return { status: 'BLOCKED', executorCalled: false, preflight }
    }

    try {
      const raw = await tool.execute({
        name: tool.name,
        ...(invocation.arguments !== undefined ? { arguments: invocation.arguments } : {}),
      })
      const resourceRefs = unique([
        ...(invocation.resourceRefs ?? []),
        ...(raw.resourceRefs ?? []),
      ])
      const eventRef = trustedEventRef ?? raw.eventRef ?? invocation.eventRef
      const observation = this.runtime.observeWork({
        kind: 'tool-result',
        runtimeId: invocation.runtimeId,
        turnId: invocation.turnId,
        name: tool.name,
        ...(invocation.arguments !== undefined ? { arguments: invocation.arguments } : {}),
        ...(raw.isError !== undefined ? { isError: raw.isError } : {}),
        ...(eventRef ? { eventRef } : {}),
        ...(resourceRefs.length > 0 ? { resourceRefs } : {}),
        ...(raw.summary ? { summary: raw.summary } : {}),
      })
      return {
        status: 'EXECUTED',
        executorCalled: true,
        preflight,
        result: raw.value as T,
        observation,
      }
    } catch (error) {
      const summary = errorText(error)
      const observation = this.runtime.observeWork({
        kind: 'tool-result',
        runtimeId: invocation.runtimeId,
        turnId: invocation.turnId,
        name: tool.name,
        ...(invocation.arguments !== undefined ? { arguments: invocation.arguments } : {}),
        isError: true,
        ...(trustedEventRef ?? invocation.eventRef
          ? { eventRef: trustedEventRef ?? invocation.eventRef }
          : {}),
        ...(invocation.resourceRefs?.length ? { resourceRefs: invocation.resourceRefs } : {}),
        summary,
      })
      return {
        status: 'ERROR',
        executorCalled: true,
        preflight,
        error: summary,
        observation,
      }
    }
  }
}

export const createGovernedToolGateway = (
  runtime: GovernanceToolRuntimePort,
  definitions: readonly GovernedToolDefinition[],
): GovernedToolGateway => new GovernedToolGateway(runtime, definitions)
