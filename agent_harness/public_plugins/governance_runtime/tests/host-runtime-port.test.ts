import { describe, expect, it, vi } from 'vitest'
import { createGovernanceHostRuntimePortV01 } from '../src/host-runtime-port.js'

describe('GovernanceHostRuntimePortV01', () => {
  it('keeps supervision binding in trusted Runtime composition and exposes least authority', async () => {
    const openSupervisedTurn = vi.fn(async input => ({ ...input, projectId: 'project-1' }))
    const runtime = {
      ingestExecutionEvent: vi.fn(async () => ({ eventRef: 'execution-event://1' })),
      preflightAction: vi.fn(() => ({ allowed: true })),
      preflightGateEvidenceProducer: vi.fn(() => ({ allowed: true })),
      observeWork: vi.fn(() => ({ observation: {} })),
      closeTurn: vi.fn(async () => ({ turnId: 'turn-1' })),
      pauseTask: vi.fn(),
      getStatus: vi.fn(() => undefined),
      completeTask: vi.fn(),
      bindSupervisedTurn: vi.fn(),
    }
    const port = createGovernanceHostRuntimePortV01(runtime as never, { openSupervisedTurn })

    await port.openTurn({ runtimeId: 'runtime-1', turnId: 'turn-1', taskText: 'task' })

    expect(openSupervisedTurn).toHaveBeenCalledOnce()
    expect(Object.keys(port).sort()).toEqual([
      'closeTurn', 'getStatus', 'ingestExecutionEvent', 'observeWork', 'openTurn',
      'pauseTask', 'preflightAction', 'version',
    ])
    expect('completeTask' in port).toBe(false)
    expect('bindSupervisedTurn' in port).toBe(false)
    expect('preflightGateEvidenceProducer' in port).toBe(false)
    expect('eventStore' in port).toBe(false)
    expect('ledger' in port).toBe(false)
    expect(Object.isFrozen(port)).toBe(true)
  })

  it('supports awaitable proxy implementations without breaking synchronous Runtime methods', async () => {
    const synchronousRuntime = {
      ingestExecutionEvent: vi.fn(async () => ({ eventRef: 'execution-event://1' })),
      preflightAction: vi.fn(() => ({ allowed: true })),
      observeWork: vi.fn(() => ({ observation: { observationId: 'observation-1' } })),
      closeTurn: vi.fn(async () => ({ turnId: 'turn-1' })),
      pauseTask: vi.fn(),
      getStatus: vi.fn(() => undefined),
    }
    const syncPort = createGovernanceHostRuntimePortV01(synchronousRuntime as never, {
      openSupervisedTurn: vi.fn(async input => input as never),
    })
    expect(syncPort.preflightAction({
      runtimeId: 'runtime-1', turnId: 'turn-1', name: 'read',
    })).toEqual({ allowed: true })
    expect(await syncPort.getStatus('runtime-1')).toBeUndefined()

    const asynchronousRuntime = {
      ...synchronousRuntime,
      preflightAction: vi.fn(async () => ({ allowed: false, reason: 'proxy-blocked' })),
      observeWork: vi.fn(async () => ({ observation: { observationId: 'proxy-observation' } })),
      pauseTask: vi.fn(async () => undefined),
      getStatus: vi.fn(async () => undefined),
    }
    const asyncPort = createGovernanceHostRuntimePortV01(asynchronousRuntime as never, {
      openSupervisedTurn: vi.fn(async input => input as never),
    })
    await expect(asyncPort.preflightAction({
      runtimeId: 'runtime-1', turnId: 'turn-1', name: 'write',
    })).resolves.toEqual({ allowed: false, reason: 'proxy-blocked' })
    await expect(asyncPort.pauseTask('runtime-1')).resolves.toBeUndefined()
  })

  it('turns a serializable Reflection proposal into one Runtime-side executor', async () => {
    const proposal = { contractVersion: '0.1', taskId: 'task-1', turnId: 'turn-1' }
    const closeTurn = vi.fn(async input => {
      expect(input).not.toHaveProperty('semanticReflection')
      expect(input.semanticExecutor).toBeDefined()
      expect(() => input.semanticExecutor.reflect({
        runtimeId: 'runtime-other', turnId: 'turn-1',
      })).toThrow('does not match the Runtime/Turn binding')
      expect(input.semanticExecutor.reflect({
        runtimeId: 'runtime-1', turnId: 'turn-1',
      })).toBe(proposal)
      expect(() => input.semanticExecutor.reflect({
        runtimeId: 'runtime-1', turnId: 'turn-1',
      })).toThrow('already consumed')
      return { turnId: 'turn-1' }
    })
    const runtime = {
      ingestExecutionEvent: vi.fn(async () => ({ eventRef: 'execution-event://1' })),
      preflightAction: vi.fn(() => ({ allowed: true })),
      observeWork: vi.fn(() => ({ observation: {} })),
      closeTurn,
      pauseTask: vi.fn(),
      getStatus: vi.fn(() => undefined),
    }
    const port = createGovernanceHostRuntimePortV01(runtime as never, {
      openSupervisedTurn: vi.fn(async input => input as never),
    })

    await port.closeTurn({
      runtimeId: 'runtime-1',
      turnId: 'turn-1',
      assistantMessageRefs: ['message://assistant/1'],
      semanticReflection: proposal,
    })

    expect(closeTurn).toHaveBeenCalledOnce()
  })

  it('never forwards a caller-supplied SemanticExecutor across the Host Port', async () => {
    const closeTurn = vi.fn(async input => {
      expect(input).not.toHaveProperty('semanticExecutor')
      return { turnId: 'turn-1' }
    })
    const runtime = {
      ingestExecutionEvent: vi.fn(async () => ({ eventRef: 'execution-event://1' })),
      preflightAction: vi.fn(() => ({ allowed: true })),
      observeWork: vi.fn(() => ({ observation: {} })),
      closeTurn,
      pauseTask: vi.fn(),
      getStatus: vi.fn(() => undefined),
    }
    const port = createGovernanceHostRuntimePortV01(runtime as never, {
      openSupervisedTurn: vi.fn(async input => input as never),
    })

    await port.closeTurn({
      runtimeId: 'runtime-1',
      turnId: 'turn-1',
      semanticExecutor: { executorId: 'untrusted', reflect: () => ({}) },
    } as never)

    expect(closeTurn).toHaveBeenCalledOnce()
  })
})
