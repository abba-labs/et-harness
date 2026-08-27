import type {
  GovernanceActionPreflightInput,
  GovernanceActionPreflightResult,
  GovernanceWorkObservationResult,
} from './contracts.js'

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

export interface GovernedToolInvocation extends GovernanceActionPreflightInput {
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

export interface GovernedToolDefinition<T = unknown> {
  readonly name: string
  readonly execute: GovernedRawToolExecutor<T>
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
}

const errorText = (error: unknown): string => {
  const raw = error instanceof Error ? error.message : String(error)
  return raw.replace(/\s+/g, ' ').trim().slice(0, 1200) || 'Tool execution failed'
}

const keyOf = (name: string): string => name.trim().toLowerCase()
const compactName = (name: string): string => name.toLowerCase().replace(/[^a-z0-9]/g, '')
const unique = (values: readonly string[]): string[] =>
  [...new Set(values.map(value => value.trim()).filter(Boolean))]

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
      if (isForbiddenAgentFacingToolName(name)) {
        throw new Error(`Agent-facing tool is a reserved Governance mutation capability: ${name}`)
      }
      const key = keyOf(name)
      if (this.tools.has(key)) throw new Error(`Duplicate Governed Tool registration: ${name}`)
      this.tools.set(key, {
        name,
        execute: definition.execute as GovernedRawToolExecutor<unknown>,
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

    const preflight = this.runtime.preflightAction({
      runtimeId: invocation.runtimeId,
      turnId: invocation.turnId,
      name: tool.name,
      ...(invocation.arguments !== undefined ? { arguments: invocation.arguments } : {}),
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
      const eventRef = raw.eventRef ?? invocation.eventRef
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
        ...(invocation.eventRef ? { eventRef: invocation.eventRef } : {}),
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
