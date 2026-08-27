import { describe, expect, it, vi } from 'vitest'
import {
  createGovernedToolGateway,
  isForbiddenAgentFacingToolName,
  type GovernanceToolRuntimePort,
} from '../src/tool-gateway.js'
import type { GovernanceWorkObservationResult } from '../src/contracts.js'

const observationResult = {} as GovernanceWorkObservationResult

describe('Governed Tool Gateway', () => {
  it('BLOCK 时不调用 raw executor', async () => {
    const runtime: GovernanceToolRuntimePort = {
      preflightAction: vi.fn(() => ({ allowed: false, reason: 'blocked' })),
      observeWork: vi.fn(() => observationResult),
    }
    let called = false
    const gateway = createGovernedToolGateway(runtime, [{
      name: 'shell',
      execute: () => {
        called = true
        return { value: 'unsafe' }
      },
    }])

    const result = await gateway.execute({
      runtimeId: 'runtime-1',
      turnId: 'turn-1',
      name: 'shell',
      arguments: { command: 'cmake -S . -B build' },
    })

    expect(result.status).toBe('BLOCKED')
    expect(called).toBe(false)
    expect(runtime.observeWork).not.toHaveBeenCalled()
  })

  it('ALLOW 后执行并自动 Observation', async () => {
    const runtime: GovernanceToolRuntimePort = {
      preflightAction: vi.fn(() => ({ allowed: true })),
      observeWork: vi.fn(() => observationResult),
    }
    const gateway = createGovernedToolGateway(runtime, [{
      name: 'read_file',
      execute: () => ({
        value: 'content',
        summary: 'read completed',
        resourceRefs: ['resource://file/a'],
      }),
    }])

    const result = await gateway.execute<string>({
      runtimeId: 'runtime-1',
      turnId: 'turn-1',
      name: 'read_file',
      arguments: { path: 'a' },
    })

    expect(result.status).toBe('EXECUTED')
    expect(result.status === 'EXECUTED' ? result.result : undefined).toBe('content')
    expect(runtime.observeWork).toHaveBeenCalledWith(expect.objectContaining({
      kind: 'tool-result',
      name: 'read_file',
      resourceRefs: ['resource://file/a'],
    }))
  })

  it('executor exception 自动形成 error Observation', async () => {
    const runtime: GovernanceToolRuntimePort = {
      preflightAction: vi.fn(() => ({ allowed: true })),
      observeWork: vi.fn(() => observationResult),
    }
    const gateway = createGovernedToolGateway(runtime, [{
      name: 'hardware_probe',
      execute: () => { throw new Error('probe failed') },
    }])

    const result = await gateway.execute({
      runtimeId: 'runtime-1',
      turnId: 'turn-1',
      name: 'hardware_probe',
    })

    expect(result.status).toBe('ERROR')
    expect(runtime.observeWork).toHaveBeenCalledWith(expect.objectContaining({
      name: 'hardware_probe',
      isError: true,
      summary: 'probe failed',
    }))
  })

  it('拒绝把 Evidence Manager 写接口注册为 Agent-facing tool', () => {
    expect(isForbiddenAgentFacingToolName('record_evidence')).toBe(true)
    expect(isForbiddenAgentFacingToolName('ctx.evidenceStateManager.recordEvidence')).toBe(true)
    expect(() => createGovernedToolGateway({
      preflightAction: () => ({ allowed: true }),
      observeWork: () => observationResult,
    }, [{
      name: 'evidenceStateManager.recordEvidence',
      execute: () => ({ value: 'forbidden' }),
    }])).toThrow('reserved Governance mutation capability')
  })

  it('未注册工具在 raw execution 前 fail-closed', async () => {
    const runtime: GovernanceToolRuntimePort = {
      preflightAction: vi.fn(() => ({ allowed: true })),
      observeWork: vi.fn(() => observationResult),
    }
    const gateway = createGovernedToolGateway(runtime, [])
    const result = await gateway.execute({
      runtimeId: 'runtime-1',
      turnId: 'turn-1',
      name: 'raw_shell',
    })
    expect(result.status).toBe('BLOCKED')
    expect(runtime.preflightAction).not.toHaveBeenCalled()
    expect(runtime.observeWork).not.toHaveBeenCalled()
  })
})
