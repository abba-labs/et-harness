import type {
  GovernanceSemanticExecutor,
  GovernanceSemanticRequest,
} from '@agent-harness/governance-runtime'
import {
  GENERIC_MODEL_ADAPTER_CONTRACT_VERSION,
  type GenericModelClient,
  type GenericModelGenerateResponse,
  type GovernedModelWorkExecutor,
  type GovernedModelWorkRequest,
  type GovernedModelWorkResult,
} from './contracts.js'
import {
  TURN_REFLECTION_JSON_SCHEMA,
  renderGovernanceReflectionPrompt,
  renderGovernedWorkPrompt,
} from './prompt.js'

const ensureResponse = (
  response: GenericModelGenerateResponse,
  requestId: string,
): GenericModelGenerateResponse => {
  if (!response || typeof response !== 'object' || Array.isArray(response)) {
    throw new Error('Generic model response must be an object')
  }
  if (response.contractVersion !== GENERIC_MODEL_ADAPTER_CONTRACT_VERSION) {
    throw new Error(
      `Generic model response contract mismatch: ${String(response.contractVersion)}`,
    )
  }
  if (typeof response.requestId !== 'string' || response.requestId !== requestId) {
    throw new Error(`Generic model response requestId mismatch: expected ${requestId}, got ${String(response.requestId)}`)
  }
  if (response.outputText !== undefined && typeof response.outputText !== 'string') {
    throw new Error('Generic model response outputText must be a string when present')
  }
  if (response.providerId !== undefined && typeof response.providerId !== 'string') {
    throw new Error('Generic model response providerId must be a string when present')
  }
  if (response.modelId !== undefined && typeof response.modelId !== 'string') {
    throw new Error('Generic model response modelId must be a string when present')
  }
  return response
}

const parseStrictJsonText = (value: string): unknown => {
  const trimmed = value.trim()
  if (!trimmed) throw new Error('Generic model returned empty JSON output')

  let jsonText = trimmed
  const fenced = /^```(?:json)?\s*([\s\S]*?)\s*```$/i.exec(trimmed)
  if (fenced) jsonText = fenced[1]?.trim() ?? ''

  try {
    return JSON.parse(jsonText)
  } catch (error) {
    throw new Error(
      `Generic model did not return one valid JSON object: ${error instanceof Error ? error.message : String(error)}`,
    )
  }
}

const reflectionOutput = (response: GenericModelGenerateResponse): unknown => {
  if (response.outputJson !== undefined) return response.outputJson
  if (typeof response.outputText === 'string') return parseStrictJsonText(response.outputText)
  throw new Error('Generic model Reflection response is missing outputJson/outputText')
}

export const createGovernanceSemanticExecutor = (
  client: GenericModelClient,
): GovernanceSemanticExecutor => ({
  executorId: `${client.clientId}:governance-reflection`,
  async reflect(request: GovernanceSemanticRequest): Promise<unknown> {
    const requestId = `governance-reflection:${request.runtimeId}:${request.turnId}`
    const prompt = renderGovernanceReflectionPrompt(request)
    const response = ensureResponse(await client.generate({
      contractVersion: GENERIC_MODEL_ADAPTER_CONTRACT_VERSION,
      requestId,
      purpose: 'GOVERNANCE_REFLECTION',
      systemText: prompt.systemText,
      userText: prompt.userText,
      response: {
        kind: 'JSON',
        jsonSchema: TURN_REFLECTION_JSON_SCHEMA,
      },
    }), requestId)
    return reflectionOutput(response)
  },
})

export const createGovernedModelWorkExecutor = (
  client: GenericModelClient,
): GovernedModelWorkExecutor => ({
  executorId: `${client.clientId}:governed-work`,
  async execute(request: GovernedModelWorkRequest): Promise<GovernedModelWorkResult> {
    const requestId = `governed-work:${request.runtimeId}:${request.turnId}`
    const prompt = renderGovernedWorkPrompt(request)
    const response = ensureResponse(await client.generate({
      contractVersion: GENERIC_MODEL_ADAPTER_CONTRACT_VERSION,
      requestId,
      purpose: 'WORK',
      systemText: prompt.systemText,
      userText: prompt.userText,
      response: { kind: 'TEXT' },
    }), requestId)
    const visibleOutput = response.outputText?.trim()
    if (!visibleOutput) {
      throw new Error('Generic model work response must provide non-empty outputText')
    }
    return {
      executorId: `${client.clientId}:governed-work`,
      visibleOutput,
      ...(response.providerId ? { providerId: response.providerId } : {}),
      ...(response.modelId ? { modelId: response.modelId } : {}),
    }
  },
})
