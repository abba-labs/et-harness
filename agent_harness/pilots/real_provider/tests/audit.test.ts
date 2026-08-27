import { describe, expect, it } from 'vitest'
import type {
  GenericModelGenerateRequest,
  GenericModelGenerateResponse,
  GenericModelClient,
} from '@agent-harness/generic-model-adapter'
import { AuditedModelClient } from '../src/audit.js'

const request: GenericModelGenerateRequest = {
  contractVersion: '0.1',
  requestId: 'test-request',
  purpose: 'WORK',
  systemText: 'system',
  userText: 'user',
  response: { kind: 'TEXT' },
}

describe('Level 2C model-call audit', () => {
  it('stores a redacted failure while rethrowing the provider error', async () => {
    const secret = 'super-secret-api-key'
    const inner: GenericModelClient = {
      clientId: 'failing-model',
      async generate(): Promise<GenericModelGenerateResponse> {
        throw new Error(`provider rejected key ${secret}`)
      },
    }
    const audited = new AuditedModelClient(inner, error =>
      (error instanceof Error ? error.message : String(error)).replaceAll(secret, '[REDACTED]'),
    )

    await expect(audited.generate(request)).rejects.toThrow(secret)
    expect(audited.calls).toHaveLength(1)
    expect(audited.calls[0]?.status).toBe('FAILED')
    expect(audited.calls[0]?.error).toContain('[REDACTED]')
    expect(audited.calls[0]?.error).not.toContain(secret)
  })
})
