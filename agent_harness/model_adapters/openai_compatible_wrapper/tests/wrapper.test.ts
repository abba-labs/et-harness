import { describe, expect, it } from 'vitest'
import {
  buildProviderRequest,
  extractProviderText,
  validateGenericRequest,
  type OpenAICompatibleWrapperConfig,
} from '../src/index.js'

const request = validateGenericRequest({
  contractVersion: '0.1',
  requestId: 'reflection:test',
  purpose: 'GOVERNANCE_REFLECTION',
  systemText: 'Return JSON.',
  userText: 'Reflect.',
  response: {
    kind: 'JSON',
    jsonSchema: {
      type: 'object',
      required: ['ok'],
      properties: { ok: { type: 'boolean' } },
      additionalProperties: false,
    },
  },
})

const config = (overrides: Partial<OpenAICompatibleWrapperConfig> = {}): OpenAICompatibleWrapperConfig => ({
  baseUrl: 'https://example.invalid/v1',
  apiKey: 'secret',
  model: 'model-x',
  apiStyle: 'responses',
  chatJsonMode: 'json_object',
  providerId: 'test',
  timeoutMs: 1000,
  maxResponseBytes: 1024 * 1024,
  extraBody: {},
  extraHeaders: {},
  ...overrides,
})

describe('OpenAI-compatible model wrapper', () => {
  it('maps structured JSON to Responses text.format json_schema', () => {
    const result = buildProviderRequest(request, config())
    expect(result.url).toBe('https://example.invalid/v1/responses')
    expect(result.body).toMatchObject({
      model: 'model-x',
      text: { format: { type: 'json_schema', strict: true } },
    })
  })

  it('maps broad-compatible chat JSON to response_format json_object', () => {
    const result = buildProviderRequest(request, config({
      apiStyle: 'chat_completions',
      chatJsonMode: 'json_object',
    }))
    expect(result.url).toBe('https://example.invalid/v1/chat/completions')
    expect(result.body.response_format).toEqual({ type: 'json_object' })
  })

  it('supports chat structured outputs when the provider implements json_schema', () => {
    const result = buildProviderRequest(request, config({
      apiStyle: 'chat_completions',
      chatJsonMode: 'json_schema',
    }))
    expect(result.body.response_format).toMatchObject({
      type: 'json_schema',
      json_schema: { strict: true },
    })
  })

  it('extracts Responses and Chat Completions visible text without reasoning fields', () => {
    expect(extractProviderText({
      output: [{ type: 'message', content: [{ type: 'output_text', text: 'response text' }] }],
      reasoning: { hidden: 'ignore' },
    }, 'responses')).toBe('response text')
    expect(extractProviderText({
      choices: [{ message: { content: 'chat text', reasoning_content: 'ignore' } }],
    }, 'chat_completions')).toBe('chat text')
  })
})
