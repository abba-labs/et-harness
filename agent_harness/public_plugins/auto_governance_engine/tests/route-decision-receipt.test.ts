import { describe, expect, it } from 'vitest'
import AutoGovernanceEngineService from '../src/service.js'

const candidate = (id: string, relevance: number, matchReasons: string[]) => ({
  projectId: 'p1',
  id,
  title: id,
  type: 'node',
  location: `${id}.md`,
  relevance,
  matchReasons,
  provenance: { resource: 'test', location: `${id}.md` },
})

describe('bounded Governance Route Decision Receipt', () => {
  it('preserves seeds, selected route, trace and omissions without changing route output', () => {
    const project = {
      projectId: 'p1',
      displayName: 'Project 1',
      aliases: [],
      projectRoot: '/workspace/p1',
      resources: {},
      resourceStandards: {},
      adapters: {},
    }
    const runtimeContext = {
      projectManager: { getProjectContext: () => project },
      architectureNavigator: {
        searchArchitecture: ({ query }: { query: string }) => query === 'A010'
          ? [candidate('A010', 1, ['exact architecture'])]
          : [candidate('A010', 0.9, ['architecture seed'])],
        getNode: () => ({ node: {} }),
      },
      ruleManager: {
        searchRules: ({ query }: { query: string }) => query === 'R010'
          ? [candidate('R010', 1, ['exact rule'])]
          : [candidate('R010', 0.8, ['rule seed'])],
        getNode: () => ({ node: {} }),
      },
      knowledgeManager: {
        searchKnowledge: () => [candidate('K010', 0.7, ['knowledge seed'])],
        getNode: () => ({ node: {} }),
      },
      gateManager: {
        searchGates: () => [candidate('G010', 0.6, ['gate seed'])],
        getNode: () => ({ node: {} }),
      },
      governanceCatalog: { listProviders: () => [] },
      contextManager: {
        getTask: () => ({
          stateVersion: 1,
          session: { inlineItems: [], taskLedger: { scopeRefs: [], constraintRefs: [] } },
        }),
        replaceInlineItems: () => undefined,
        replaceWorkingSet: () => undefined,
        attach: () => undefined,
        updateTaskLedger: () => undefined,
      },
      get: () => undefined,
    }

    const service = Object.create(AutoGovernanceEngineService.prototype) as any
    service.runtimeContext = runtimeContext
    service.tasks = new Map()
    service.pendingReviews = new Map()
    const runtime = {
      actorId: 'actor-1',
      projectId: 'p1',
      taskId: 'TASK-1',
      goal: 'inspect project routing',
      codeChangeEpoch: 0,
      codeChangeSeen: false,
      route: { architectureIds: [], ruleIds: [], knowledgeIds: [], gateIds: [] },
      contextContributions: [],
      applicableGateIds: [],
      currentPacketIds: [],
    }

    const route = service.routeTask(runtime, runtime.goal, true, 'analysis')
    expect(runtime.routeDecision.schema).toBe('auto-governance.route-decision.v0.1')
    expect(runtime.routeDecision.phase).toBe('analysis')
    expect(runtime.routeDecision.queryPreview).toBe(runtime.goal)
    expect(runtime.routeDecision.queryHash).toMatch(/^sha256:[0-9a-f]{64}$/)
    expect(runtime.routeDecision.seeds.architecture[0]).toMatchObject({
      id: 'A010',
      relevance: 0.9,
      reasons: ['architecture seed'],
    })
    expect(runtime.routeDecision.selected).toEqual(route)
    expect(runtime.routeDecision.trace.some((item: any) => item.id === 'A010')).toBe(true)
    expect(runtime.routeDecision.contextContributionIds).toEqual([])

    service.tasks.set(runtime.actorId, runtime)
    const status = service.getTaskStatus(runtime.actorId)
    expect(status?.route).toEqual(route)
    expect(status?.routeDecision?.selected).toEqual(route)
  })
})
