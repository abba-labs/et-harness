import type {
  GenericModelGenerateRequest,
  GenericModelGenerateResponse,
} from '@agent-harness/generic-model-adapter'

export type OpenAICompatibleApiStyle = 'responses' | 'chat_completions'
export type OpenAICompatibleChatJsonMode = 'json_schema' | 'json_object' | 'prompt_only'

export interface OpenAICompatibleWrapperConfig {
  readonly baseUrl: string
  readonly apiKey: string
  readonly model: string
  readonly apiStyle: OpenAICompatibleApiStyle
  readonly chatJsonMode: OpenAICompatibleChatJsonMode
  readonly providerId: string
  readonly timeoutMs: number
  readonly maxResponseBytes: number
  readonly maxOutputTokens?: number
  readonly extraBody: Readonly<Record<string, unknown>>
  readonly extraHeaders: Readonly<Record<string, string>>
}

const CONTRACT_VERSION = '0.1'
const DEFAULT_TIMEOUT_MS = 120_000
const DEFAULT_MAX_RESPONSE_BYTES = 4 * 1024 * 1024
const RESERVED_RESPONSES_KEYS = new Set([
  'model', 'instructions', 'input', 'stream', 'text', 'max_output_tokens',
])
const RESERVED_CHAT_KEYS = new Set([
  'model', 'messages', 'stream', 'response_format', 'max_tokens', 'max_completion_tokens',
])

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

const requiredEnv = (name: string): string => {
  const value = process.env[name]?.trim()
  if (!value) throw new Error(`${name} is required`)
  return value
}

const optionalPositiveNumber = (name: string): number | undefined => {
  const raw = process.env[name]?.trim()
  if (!raw) return undefined
  const value = Number(raw)
  if (!Number.isFinite(value) || value <= 0) throw new Error(`${name} must be a positive number`)
  return value
}

const parseJsonObjectEnv = (name: string): Record<string, unknown> => {
  const raw = process.env[name]?.trim()
  if (!raw) return {}
  let parsed: unknown
  try {
    parsed = JSON.parse(raw)
  } catch (error) {
    throw new Error(`${name} must be valid JSON: ${error instanceof Error ? error.message : String(error)}`)
  }
  if (!isRecord(parsed)) throw new Error(`${name} must be a JSON object`)
  return parsed
}

const parseHeaderEnv = (): Record<string, string> => {
  const raw = parseJsonObjectEnv('OPENAI_COMPAT_EXTRA_HEADERS_JSON')
  const headers: Record<string, string> = {}
  for (const [key, value] of Object.entries(raw)) {
    if (typeof value !== 'string') throw new Error(`OPENAI_COMPAT_EXTRA_HEADERS_JSON.${key} must be a string`)
    const normalized = key.toLowerCase()
    if (normalized === 'authorization' || normalized === 'content-type') {
      throw new Error(`OPENAI_COMPAT_EXTRA_HEADERS_JSON cannot override ${key}`)
    }
    headers[key] = value
  }
  return headers
}

const normalizeBaseUrl = (value: string): string => value.replace(/\/+$/, '')

const ensureNoReservedExtras = (
  extras: Readonly<Record<string, unknown>>,
  reserved: ReadonlySet<string>,
  style: string,
): void => {
  const conflicts = Object.keys(extras).filter(key => reserved.has(key))
  if (conflicts.length > 0) {
    throw new Error(`OPENAI_COMPAT_EXTRA_BODY_JSON cannot override ${style} fields: ${conflicts.join(', ')}`)
  }
}

export function configFromEnv(): OpenAICompatibleWrapperConfig {
  const apiStyleRaw = requiredEnv('OPENAI_COMPAT_API_STYLE')
  if (apiStyleRaw !== 'responses' && apiStyleRaw !== 'chat_completions') {
    throw new Error('OPENAI_COMPAT_API_STYLE must be responses or chat_completions')
  }
  const chatJsonModeRaw = process.env.OPENAI_COMPAT_CHAT_JSON_MODE?.trim() || 'json_object'
  if (!['json_schema', 'json_object', 'prompt_only'].includes(chatJsonModeRaw)) {
    throw new Error('OPENAI_COMPAT_CHAT_JSON_MODE must be json_schema, json_object, or prompt_only')
  }
  const timeoutMs = optionalPositiveNumber('OPENAI_COMPAT_TIMEOUT_MS') ?? DEFAULT_TIMEOUT_MS
  const maxResponseBytes = optionalPositiveNumber('OPENAI_COMPAT_MAX_RESPONSE_BYTES') ?? DEFAULT_MAX_RESPONSE_BYTES
  const maxOutputTokens = optionalPositiveNumber('OPENAI_COMPAT_MAX_OUTPUT_TOKENS')
  const extraBody = parseJsonObjectEnv('OPENAI_COMPAT_EXTRA_BODY_JSON')
  ensureNoReservedExtras(
    extraBody,
    apiStyleRaw === 'responses' ? RESERVED_RESPONSES_KEYS : RESERVED_CHAT_KEYS,
    apiStyleRaw,
  )
  return {
    baseUrl: normalizeBaseUrl(requiredEnv('OPENAI_COMPAT_BASE_URL')),
    apiKey: requiredEnv('OPENAI_COMPAT_API_KEY'),
    model: requiredEnv('OPENAI_COMPAT_MODEL'),
    apiStyle: apiStyleRaw,
    chatJsonMode: chatJsonModeRaw as OpenAICompatibleChatJsonMode,
    providerId: process.env.OPENAI_COMPAT_PROVIDER_ID?.trim() || 'openai-compatible',
    timeoutMs,
    maxResponseBytes,
    ...(maxOutputTokens !== undefined ? { maxOutputTokens } : {}),
    extraBody,
    extraHeaders: parseHeaderEnv(),
  }
}

export function validateGenericRequest(value: unknown): GenericModelGenerateRequest {
  if (!isRecord(value)) throw new Error('Generic model request must be an object')
  if (value.contractVersion !== CONTRACT_VERSION) throw new Error(`Unsupported Generic model contractVersion: ${String(value.contractVersion)}`)
  if (typeof value.requestId !== 'string' || !value.requestId.trim()) throw new Error('requestId must be non-empty')
  if (value.purpose !== 'WORK' && value.purpose !== 'GOVERNANCE_REFLECTION') throw new Error('purpose must be WORK or GOVERNANCE_REFLECTION')
  if (typeof value.systemText !== 'string') throw new Error('systemText must be a string')
  if (typeof value.userText !== 'string') throw new Error('userText must be a string')
  if (!isRecord(value.response)) throw new Error('response must be an object')
  if (value.response.kind !== 'TEXT' && value.response.kind !== 'JSON') throw new Error('response.kind must be TEXT or JSON')
  if (value.response.jsonSchema !== undefined && !isRecord(value.response.jsonSchema)) {
    throw new Error('response.jsonSchema must be an object when supplied')
  }
  return value as unknown as GenericModelGenerateRequest
}

const jsonSystemText = (request: GenericModelGenerateRequest): string =>
  request.response.kind === 'JSON'
    ? `${request.systemText}\n\nReturn the final answer as one valid JSON object only.`
    : request.systemText

const structuredName = (requestId: string): string => {
  const safe = requestId.replace(/[^A-Za-z0-9_-]+/g, '_').slice(0, 56)
  return safe || 'governance_output'
}

export function buildProviderRequest(
  request: GenericModelGenerateRequest,
  config: OpenAICompatibleWrapperConfig,
): { readonly url: string; readonly body: Record<string, unknown> } {
  const systemText = jsonSystemText(request)
  if (config.apiStyle === 'responses') {
    const body: Record<string, unknown> = {
      model: config.model,
      instructions: systemText,
      input: request.userText,
      stream: false,
      ...config.extraBody,
    }
    if (config.maxOutputTokens !== undefined) body.max_output_tokens = config.maxOutputTokens
    if (request.response.kind === 'JSON') {
      if (!request.response.jsonSchema) throw new Error('Responses JSON mode requires response.jsonSchema')
      body.text = {
        format: {
          type: 'json_schema',
          name: structuredName(request.requestId),
          schema: request.response.jsonSchema,
          strict: true,
        },
      }
    }
    return { url: `${config.baseUrl}/responses`, body }
  }

  const body: Record<string, unknown> = {
    model: config.model,
    messages: [
      { role: 'system', content: systemText },
      { role: 'user', content: request.userText },
    ],
    stream: false,
    ...config.extraBody,
  }
  if (config.maxOutputTokens !== undefined) body.max_tokens = config.maxOutputTokens
  if (request.response.kind === 'JSON') {
    if (config.chatJsonMode === 'json_schema') {
      if (!request.response.jsonSchema) throw new Error('chat_completions json_schema mode requires response.jsonSchema')
      body.response_format = {
        type: 'json_schema',
        json_schema: {
          name: structuredName(request.requestId),
          schema: request.response.jsonSchema,
          strict: true,
        },
      }
    } else if (config.chatJsonMode === 'json_object') {
      body.response_format = { type: 'json_object' }
    }
  }
  return { url: `${config.baseUrl}/chat/completions`, body }
}

const textParts = (value: unknown): string[] => {
  if (typeof value === 'string') return value.trim() ? [value] : []
  if (!Array.isArray(value)) return []
  return value.flatMap(item => {
    if (!isRecord(item)) return []
    if (typeof item.text === 'string' && item.text.trim()) return [item.text]
    if (typeof item.content === 'string' && item.content.trim()) return [item.content]
    return []
  })
}

export function extractProviderText(payload: unknown, style: OpenAICompatibleApiStyle): string {
  if (!isRecord(payload)) throw new Error('Provider response must be a JSON object')
  if (style === 'responses') {
    if (typeof payload.output_text === 'string' && payload.output_text.trim()) return payload.output_text.trim()
    const output = Array.isArray(payload.output) ? payload.output : []
    const pieces: string[] = []
    for (const item of output) {
      if (!isRecord(item)) continue
      if (item.type !== undefined && item.type !== 'message') continue
      pieces.push(...textParts(item.content))
    }
    const joined = pieces.join('\n').trim()
    if (joined) return joined
    throw new Error('Responses API payload contains no text output')
  }

  const choices = Array.isArray(payload.choices) ? payload.choices : []
  const first = choices[0]
  if (!isRecord(first) || !isRecord(first.message)) {
    throw new Error('Chat Completions payload is missing choices[0].message')
  }
  const joined = textParts(first.message.content).join('\n').trim()
  if (!joined) throw new Error('Chat Completions payload contains no message content')
  return joined
}

const readJsonResponse = async (response: Response, maxBytes: number): Promise<unknown> => {
  const lengthHeader = response.headers.get('content-length')
  if (lengthHeader) {
    const declared = Number(lengthHeader)
    if (Number.isFinite(declared) && declared > maxBytes) {
      throw new Error(`Provider response exceeds ${maxBytes} bytes`)
    }
  }
  const bytes = new Uint8Array(await response.arrayBuffer())
  if (bytes.byteLength > maxBytes) throw new Error(`Provider response exceeds ${maxBytes} bytes`)
  const text = new TextDecoder().decode(bytes)
  let parsed: unknown
  try {
    parsed = JSON.parse(text)
  } catch (error) {
    throw new Error(`Provider response is not JSON: ${error instanceof Error ? error.message : String(error)}`)
  }
  if (!response.ok) {
    const message = isRecord(parsed) && isRecord(parsed.error) && typeof parsed.error.message === 'string'
      ? parsed.error.message
      : text.slice(0, 2000)
    throw new Error(`Provider HTTP ${response.status}: ${message}`)
  }
  return parsed
}

export async function generateViaOpenAICompatible(
  request: GenericModelGenerateRequest,
  config: OpenAICompatibleWrapperConfig,
): Promise<GenericModelGenerateResponse> {
  const providerRequest = buildProviderRequest(request, config)
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), config.timeoutMs)
  timer.unref?.()
  try {
    const response = await fetch(providerRequest.url, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        authorization: `Bearer ${config.apiKey}`,
        ...config.extraHeaders,
      },
      body: JSON.stringify(providerRequest.body),
      signal: controller.signal,
    })
    const payload = await readJsonResponse(response, config.maxResponseBytes)
    const outputText = extractProviderText(payload, config.apiStyle)
    return {
      contractVersion: CONTRACT_VERSION,
      requestId: request.requestId,
      outputText,
      providerId: config.providerId,
      modelId: config.model,
    }
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error(`Provider request timed out after ${config.timeoutMs} ms`)
    }
    throw error
  } finally {
    clearTimeout(timer)
  }
}
