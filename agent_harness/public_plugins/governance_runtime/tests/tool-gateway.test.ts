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

  it('trusted registration effect controls ENFORCE preflight before raw execution', async () => {
    const runtime: GovernanceToolRuntimePort = {
      preflightAction: vi.fn(input => ({
        allowed: input.eventRef === 'host-event-1'
          && input.effect?.kind === 'MUTATION'
          && input.effect.intent.resourceId === 'resource-allowed',
        reason: 'outside scope',
      })),
      observeWork: vi.fn(() => observationResult),
    }
    const executor = vi.fn(() => ({ value: 'unsafe' }))
    const gateway = createGovernedToolGateway(runtime, [{
      name: 'write_file',
      effect: {
        kind: 'MUTATION',
        intent: () => ({ resourceId: 'resource-forbidden', action: 'UPDATE' }),
      },
      eventIdentity: () => 'host-event-1',
      execute: executor,
    }])

    const result = await gateway.execute({
      runtimeId: 'runtime-1',
      turnId: 'turn-1',
      name: 'write_file',
      arguments: { path: 'forbidden' },
      eventRef: 'agent-event',
      effect: { kind: 'READ_ONLY' },
    } as never)

    expect(result).toMatchObject({ status: 'BLOCKED', executorCalled: false })
    expect(runtime.preflightAction).toHaveBeenCalledWith(expect.objectContaining({
      eventRef: 'host-event-1',
      effect: { kind: 'MUTATION', intent: { resourceId: 'resource-forbidden', action: 'UPDATE' } },
    }))
    expect(executor).not.toHaveBeenCalled()
  })

  it('preserves the trusted event identity for success and executor errors', async () => {
    const runtime: GovernanceToolRuntimePort = {
      preflightAction: vi.fn(() => ({ allowed: true })),
      observeWork: vi.fn(() => observationResult),
    }
    const gateway = createGovernedToolGateway(runtime, [
      {
        name: 'read_ok',
        effect: { kind: 'READ_ONLY' },
        eventIdentity: () => 'host-event-ok',
        execute: () => ({ value: 'ok', eventRef: 'raw-event' }),
      },
      {
        name: 'read_error',
        effect: { kind: 'READ_ONLY' },
        eventIdentity: () => 'host-event-error',
        execute: () => { throw new Error('failed') },
      },
    ])

    await gateway.execute({
      runtimeId: 'runtime-1', turnId: 'turn-1', name: 'read_ok', eventRef: 'agent-event',
    })
    await gateway.execute({
      runtimeId: 'runtime-1', turnId: 'turn-1', name: 'read_error', eventRef: 'agent-error',
    })

    expect(runtime.observeWork).toHaveBeenNthCalledWith(1, expect.objectContaining({
      eventRef: 'host-event-ok',
    }))
    expect(runtime.observeWork).toHaveBeenNthCalledWith(2, expect.objectContaining({
      eventRef: 'host-event-error', isError: true,
    }))
  })

  it('rejects malformed effects and snapshots valid registration metadata', async () => {
    expect(() => createGovernedToolGateway({
      preflightAction: () => ({ allowed: true }),
      observeWork: () => observationResult,
    }, [{
      name: 'unknown',
      effect: { kind: 'UNKNOWN' },
      execute: () => ({ value: 'unsafe' }),
    } as never])).toThrow('effect definition')

    const runtime: GovernanceToolRuntimePort = {
      preflightAction: vi.fn(() => ({ allowed: true })),
      observeWork: vi.fn(() => observationResult),
    }
    const mutableEffect: any = { kind: 'READ_ONLY' }
    const gateway = createGovernedToolGateway(runtime, [{
      name: 'stable', effect: mutableEffect, execute: () => ({ value: 'ok' }),
    }])
    mutableEffect.kind = 'UNKNOWN'
    await gateway.execute({ runtimeId: 'runtime-1', turnId: 'turn-1', name: 'stable' })
    expect(runtime.preflightAction).toHaveBeenCalledWith(expect.objectContaining({
      effect: { kind: 'READ_ONLY' },
    }))
  })
})
