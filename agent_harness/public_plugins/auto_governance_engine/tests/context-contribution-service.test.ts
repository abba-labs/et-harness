import { describe, expect, it } from 'vitest'
import {
  PROJECT_CONTEXT_CONTRIBUTION_CAPABILITY,
  PROJECT_CONTEXT_CONTRIBUTION_SCHEMA,
} from '../src/context-contribution.js'
import AutoGovernanceEngineService from '../src/service.js'

const PROJECT_ID = 'synthetic-project'
const PROVIDER_ID = 'project.synthetic.context-provider'

const emptyRoute = () => ({
  architectureIds: [] as string[],
  ruleIds: [] as string[],
  knowledgeIds: [] as string[],
  gateIds: [] as string[],
})

describe('Auto Governance project context contribution integration', () => {
  it('re-evaluates the provider per phase and preserves host-owned Inline Context', () => {
    const phases: string[] = []
    let inlineItems = [{
      id: 'host-owned',
      title: 'Host Owned',
      content: 'preserve this runtime item',
      provenance: 'runtime://synthetic/host',
    }]
    let workingSet: unknown[] = []

    const project = {
      projectId: PROJECT_ID,
      displayName: 'Synthetic Project',
      aliases: [],
      projectRoot: '/workspace/synthetic',
      resources: {},
      resourceStandards: {},
      adapters: {
        context: {
          provider: PROVIDER_ID,
          capability: PROJECT_CONTEXT_CONTRIBUTION_CAPABILITY,
        },
      },
    }
    const provider = {
      providerId: PROVIDER_ID,
      pluginId: 'project.synthetic.context-plugin',
      capability: PROJECT_CONTEXT_CONTRIBUTION_CAPABILITY,
      priority: 100,
      metadata: {
        projectId: PROJECT_ID,
        service: 'syntheticContextProvider',
        method: 'contributeContext',
      },
    }
    const providerService = {
      contributeContext: (request: { phase: string; projectId: string; taskId: string }) => {
        phases.push(request.phase)
        return {
          applicable: true,
          contribution: {
            schema: PROJECT_CONTEXT_CONTRIBUTION_SCHEMA,
            projectId: request.projectId,
            taskId: request.taskId,
            contributionId: `phase-${request.phase}`,
            provenance: `provider://${PROVIDER_ID}/${request.taskId}`,
            inlineItems: [{
              id: 'scope-summary',
              title: `Scope ${request.phase}`,
              content: `phase=${request.phase}`,
              provenance: `provider://${PROVIDER_ID}/${request.taskId}`,
            }],
          },
        }
      },
    }

    const contextManager = {
      getTask: () => ({
        stateVersion: 1,
        session: {
          inlineItems,
          taskLedger: {
            scopeRefs: [] as string[],
            constraintRefs: [] as string[],
          },
        },
      }),
      replaceInlineItems: (_projectId: string, _taskId: string, items: typeof inlineItems) => {
        inlineItems = items
      },
      replaceWorkingSet: (_projectId: string, _taskId: string, refs: unknown[]) => {
        workingSet = refs
      },
      attach: () => undefined,
      updateTaskLedger: () => undefined,
    }
    const runtimeContext = {
      projectManager: {
        getProjectContext: () => project,
      },
      architectureNavigator: {
        searchArchitecture: () => [],
        getNode: () => undefined,
      },
      ruleManager: {
        searchRules: () => [],
        getNode: () => undefined,
      },
      knowledgeManager: {
        searchKnowledge: () => [],
        getNode: () => undefined,
      },
      gateManager: {
        searchGates: () => [],
        getNode: () => undefined,
      },
      governanceCatalog: {
        listProviders: (capability: string) =>
          capability === PROJECT_CONTEXT_CONTRIBUTION_CAPABILITY ? [provider] : [],
      },
      contextManager,
      get: (name: string) => name === 'syntheticContextProvider' ? providerService : undefined,
    }

    const service = Object.create(AutoGovernanceEngineService.prototype) as any
    service.runtimeContext = runtimeContext
    const runtime = {
      actorId: 'actor-1',
      projectId: PROJECT_ID,
      taskId: 'TASK-1',
      goal: 'analyze the project',
      codeChangeEpoch: 0,
      codeChangeSeen: false,
      route: emptyRoute(),
      contextContributions: [],
      applicableGateIds: [],
      currentPacketIds: [],
    }

    service.routeTask(runtime, runtime.goal, true, 'analysis')
    expect(phases).toEqual(['analysis'])
    expect(inlineItems.some(item => item.id === 'host-owned')).toBe(true)
    expect(inlineItems.some(item => item.id.includes('phase-analysis'))).toBe(true)
    expect(workingSet).toEqual([])

    service.routeTask(runtime, runtime.goal, true, 'implementation')
    expect(phases).toEqual(['analysis', 'implementation'])
    expect(inlineItems.some(item => item.id === 'host-owned')).toBe(true)
    expect(inlineItems.some(item => item.id.includes('phase-analysis'))).toBe(false)
    expect(inlineItems.some(item => item.id.includes('phase-implementation'))).toBe(true)
  })

  it('keeps projects without a declared contributor backward compatible', () => {
    let providerLookups = 0
    let inlineItems = [{
      id: 'host-owned',
      title: 'Host Owned',
      content: 'unchanged',
      provenance: 'runtime://synthetic/host',
    }]
    const runtimeContext = {
      projectManager: {
        getProjectContext: () => ({
          projectId: PROJECT_ID,
          displayName: 'Static Project',
          aliases: [],
          projectRoot: '/workspace/static',
          resources: {},
          resourceStandards: {},
          adapters: {},
        }),
      },
      architectureNavigator: { searchArchitecture: () => [], getNode: () => undefined },
      ruleManager: { searchRules: () => [], getNode: () => undefined },
      knowledgeManager: { searchKnowledge: () => [], getNode: () => undefined },
      gateManager: { searchGates: () => [], getNode: () => undefined },
      governanceCatalog: {
        listProviders: () => {
          providerLookups += 1
          return []
        },
      },
      contextManager: {
        getTask: () => ({
          stateVersion: 1,
          session: {
            inlineItems,
            taskLedger: { scopeRefs: [] as string[], constraintRefs: [] as string[] },
          },
        }),
        replaceInlineItems: (_projectId: string, _taskId: string, items: typeof inlineItems) => {
          inlineItems = items
        },
        replaceWorkingSet: () => undefined,
        attach: () => undefined,
        updateTaskLedger: () => undefined,
      },
      get: () => undefined,
    }
    const service = Object.create(AutoGovernanceEngineService.prototype) as any
    service.runtimeContext = runtimeContext
    const runtime = {
      actorId: 'actor-static',
      projectId: PROJECT_ID,
      taskId: 'TASK-STATIC',
      goal: 'read the project',
      codeChangeEpoch: 0,
      codeChangeSeen: false,
      route: emptyRoute(),
      contextContributions: [],
      applicableGateIds: [],
      currentPacketIds: [],
    }

    service.routeTask(runtime, runtime.goal, true, 'analysis')
    expect(providerLookups).toBe(0)
    expect(runtime.contextContributions).toEqual([])
    expect(inlineItems).toEqual([{
      id: 'host-owned',
      title: 'Host Owned',
      content: 'unchanged',
      provenance: 'runtime://synthetic/host',
    }])
  })
})
