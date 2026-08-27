import type { GovernanceKnowledgeDecision, GovernanceOpenTurnResult } from '@agent-harness/governance-runtime'

export const GENERIC_MODEL_ADAPTER_CONTRACT_VERSION = '0.1' as const

export type GenericModelPurpose = 'WORK' | 'GOVERNANCE_REFLECTION'
export type GenericModelResponseKind = 'TEXT' | 'JSON'

export interface GenericModelGenerateRequest {
  readonly contractVersion: typeof GENERIC_MODEL_ADAPTER_CONTRACT_VERSION
  readonly requestId: string
  readonly purpose: GenericModelPurpose
  readonly systemText: string
  readonly userText: string
  readonly response: {
    readonly kind: GenericModelResponseKind
    readonly jsonSchema?: Readonly<Record<string, unknown>>
  }
}

export interface GenericModelGenerateResponse {
  readonly contractVersion: typeof GENERIC_MODEL_ADAPTER_CONTRACT_VERSION
  readonly requestId: string
  readonly outputText?: string
  readonly outputJson?: unknown
  readonly providerId?: string
  readonly modelId?: string
}

/**
 * Provider-neutral model transport. Provider/API/CLI details live behind this
 * interface and never enter Public Governance Runtime.
 */
export interface GenericModelClient {
  readonly clientId: string
  generate(request: GenericModelGenerateRequest): Promise<GenericModelGenerateResponse>
}

export interface GovernedModelWorkRequest {
  readonly runtimeId: string
  readonly taskId: string
  readonly turnId: string
  /** Original business task, unchanged. */
  readonly taskText: string
  /** Automatically built Governance Context Envelope. */
  readonly context: GovernanceOpenTurnResult['context']
  readonly knowledgeDecision: GovernanceKnowledgeDecision
}

export interface GovernedModelWorkResult {
  readonly executorId: string
  readonly visibleOutput: string
  readonly providerId?: string
  readonly modelId?: string
}

export interface GovernedModelWorkExecutor {
  readonly executorId: string
  execute(request: GovernedModelWorkRequest): Promise<GovernedModelWorkResult>
}
