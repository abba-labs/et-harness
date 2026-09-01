import { describe, expect, it, vi } from 'vitest'
import { AutoGovernanceEngineService } from '../src/service.js'

describe('Phase 7 incremental Context envelope reuse', () => {
  it('keeps a broad project route inside the recent-decision reference budget', () => {
    const recordRecent = vi.fn()
    const service = Object.create(AutoGovernanceEngineService.prototype) as any
    service.runtimeContext = {
      contextManager: {
        updateProgressLedger: vi.fn(),
        recordRecent,
      },
      gateManager: {
        getExecutionPlan: vi.fn(() => undefined),
      },
    }
    const runtime = {
      actorId: 'agent-1',
      projectId: 'project-1',
      taskId: 'task-1',
      goal: 'Analyze a project IP.',
      route: { architectureIds: [], ruleIds: [], knowledgeIds: [], gateIds: [] },
    }
    service.resolveProject = vi.fn(() => ({ projectId: 'project-1' }))
    service.ensureRuntimeTask = vi.fn(() => runtime)
    service.routeTask = vi.fn(() => ({
      architectureIds: Array.from({ length: 12 }, (_, index) => `A${index}`),
      ruleIds: Array.from({ length: 22 }, (_, index) => `R${index}`),
      knowledgeIds: Array.from({ length: 9 }, (_, index) => `K${index}`),
      gateIds: Array.from({ length: 4 }, (_, index) => `G${index}`),
    }))
    service.buildContextEnvelope = vi.fn(() => ({ text: 'bounded' }))

    service.bootstrapTask({
      actorId: 'agent-1',
      taskId: 'task-1',
      goal: runtime.goal,
      projectId: 'project-1',
    })

    expect(recordRecent).toHaveBeenCalledOnce()
    expect(recordRecent.mock.calls[0][2].refs).toHaveLength(32)
    expect(recordRecent.mock.calls[0][2].refs[0]).toBe('A0')
    expect(recordRecent.mock.calls[0][2].refs.at(-1)).toBe('R19')
  })

  it('keeps 1000 ordinary reads off reroute/rebuild and refreshes after mutation', () => {
    let stateVersion = 7
    const getTask = vi.fn(() => ({
      stateVersion,
      session: { projectId: 'project-1', taskId: 'task-1' },
    }))
    const buildFrame = vi.fn(() => ({
      stateVersion,
      pack: { text: `bounded frame ${stateVersion}` },
    }))
    const service = Object.create(AutoGovernanceEngineService.prototype) as any
    service.runtimeContext = {
      contextManager: {
        getTask,
        buildFrame,
        updateProgressLedger: vi.fn(() => { stateVersion += 1 }),
        recordRecent: vi.fn(() => { stateVersion += 1 }),
      },
      gateManager: { getExecutionPlan: vi.fn(() => undefined) },
    }
    service.pendingReviews = new Map()
    service.tasks = new Map([['agent-1', {
      actorId: 'agent-1',
      projectId: 'project-1',
      taskId: 'task-1',
      goal: 'Verify incremental Context reuse.',
      codeChangeEpoch: 0,
      codeChangeSeen: false,
      route: { architectureIds: [], ruleIds: [], knowledgeIds: [], gateIds: [] },
      contextContributions: [],
      applicableGateIds: [],
      currentPacketIds: [],
    }]])
    service.renderGovernanceContext = vi.fn((_runtime: unknown, text: string) => text)
    service.routeTask = vi.fn(() => ({
      architectureIds: [], ruleIds: [], knowledgeIds: [], gateIds: [],
    }))
    service.prepareReviewPackets = vi.fn(() => [])

    const results = Array.from({ length: 1_000 }, () => service.observeToolResult({
      actorId: 'agent-1',
      name: 'read_file',
      arguments: { path: 'source/read-only.ts' },
    }))
    expect(new Set(results).size).toBe(1)
    expect(buildFrame).toHaveBeenCalledTimes(1)
    expect(service.routeTask).not.toHaveBeenCalled()

    const refreshed = service.observeToolResult({
      actorId: 'agent-1',
      name: 'write_file',
      arguments: { path: 'source/changed.ts' },
    })
    expect(refreshed).not.toBe(results[0])
    expect(buildFrame).toHaveBeenCalledTimes(2)
    expect(service.routeTask).toHaveBeenCalledTimes(1)
  })
})
