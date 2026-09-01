import { describe, expect, it } from 'vitest'
import type { GovernanceProviderRegistration } from '@agent-harness/governance-core'
import type { ProjectContext } from '@agent-harness/project-contract'
import { MANDATORY_LIFECYCLE_CLOSURE_MODULE_IDS } from '@agent-harness/execution-supervisor'
import {
  PROJECT_CONTEXT_CONTRIBUTION_CAPABILITY,
  PROJECT_CONTEXT_CONTRIBUTION_REQUEST_SCHEMA,
  PROJECT_CONTEXT_CONTRIBUTION_SCHEMA,
  PROJECT_SUPERVISION_CONTRIBUTION_SCHEMA,
  mergeContributionInlineItems,
  mergeContributionReferences,
  replaceContributionInlineItems,
  resolveDeclaredProjectContextContributions,
  type ProjectContextContributionRequestV01,
} from '../src/context-contribution.js'

const PROJECT_ID = 'synthetic-project'

const request: ProjectContextContributionRequestV01 = {
  schema: PROJECT_CONTEXT_CONTRIBUTION_REQUEST_SCHEMA,
  projectId: PROJECT_ID,
  taskId: 'TASK-1',
  rawTask: 'Inspect one synthetic component.',
  phase: 'analysis',
  workspacePath: '/workspace/synthetic-project',
  initialRoute: {
    architectureIds: ['A010'],
    ruleIds: ['R010'],
    knowledgeIds: [],
    gateIds: [],
  },
}

const project = (
  adapters: ProjectContext['adapters'],
): ProjectContext => ({
  contractVersion: '0.1',
  projectId: PROJECT_ID,
  displayName: 'Synthetic Project',
  aliases: [],
  projectRoot: '/workspace/synthetic-project',
  resources: {
    architecture: `project://${PROJECT_ID}/architecture`,
    rules: `project://${PROJECT_ID}/rules`,
    knowledge: `project://${PROJECT_ID}/knowledge`,
    gates: `project://${PROJECT_ID}/gates`,
  },
  resourceStandards: {
    architecture: 'architecture-v0.1',
    rules: 'rule-v0.1',
    knowledge: 'knowledge-v0.1',
    gates: 'gate-v0.1',
  },
  adapters,
})

const provider: GovernanceProviderRegistration = {
  providerId: 'synthetic.context-provider',
  pluginId: 'synthetic.plugin',
  capability: PROJECT_CONTEXT_CONTRIBUTION_CAPABILITY,
  priority: 100,
  metadata: {
    projectId: PROJECT_ID,
    service: 'syntheticContextProvider',
    method: 'contributeContext',
  },
}

const adapterProject = () => project({
  context: {
    provider: provider.providerId,
    capability: PROJECT_CONTEXT_CONTRIBUTION_CAPABILITY,
  },
})

const validService = {
  contributeContext: () => ({
    applicable: true,
    contribution: {
      schema: PROJECT_CONTEXT_CONTRIBUTION_SCHEMA,
      projectId: PROJECT_ID,
      taskId: 'TASK-1',
      contributionId: 'synthetic-analysis',
      provenance: 'provider://synthetic.context-provider/TASK-1',
      references: [
        { kind: 'knowledge', id: 'K001', priority: 'high' },
        { kind: 'gate', id: 'G010', priority: 'required' },
      ],
      inlineItems: [{
        id: 'task-parameters',
        title: 'Resolved Task Parameters',
        content: 'module=synthetic\nchange=analysis',
        priority: 'required',
        provenance: 'provider://synthetic.context-provider/TASK-1/parameters',
      }],
      readScope: ['src/**', 'source://external/specification'],
      writeScope: {
        allowed: ['docs/component/**'],
        protected: ['src/core/**'],
      },
      validation: [{
        id: 'validate-contract',
        summary: 'Validate the generated component contract.',
        command: 'python tools/validate_contract.py',
      }],
      outputContract: {
        id: 'analysis-output',
        title: 'Analysis Output Contract',
        content: 'Required sections:\n- Stable Contract\n- Evidence\n- Unknowns',
      },
      supervision: {
        schema: PROJECT_SUPERVISION_CONTRIBUTION_SCHEMA,
        obligations: [{
          id: 'OBL-SYNTHETIC-READ',
          kind: 'REQUIRED_RESOURCE',
          severity: 'MUST',
          sourceRefs: ['R010'],
          target: { resourceId: 'project://synthetic/required' },
          satisfaction: { acceptedProviderIds: ['host.filesystem'], acceptedDispositions: ['FOUND'] },
        }],
        evidencePolicies: [],
        completionPolicy: {
          requireAllMustSatisfied: true,
          requireNoViolations: true,
          requireReflection: true,
          requireKnowledgeDecision: true,
          requireContextUpdate: true,
          requireClosureReceipt: true,
          allowShouldWarnings: true,
          requiredClosureModuleIds: [...MANDATORY_LIFECYCLE_CLOSURE_MODULE_IDS],
        },
      },
    },
  }),
}

describe('optional project context contribution contract', () => {
  it('keeps projects without a declared provider fully unchanged', () => {
    let lookups = 0
    const contributions = resolveDeclaredProjectContextContributions({
      project: project({}),
      request,
      providers: [],
      serviceLookup: () => {
        lookups += 1
        return undefined
      },
    })
    expect(contributions).toEqual([])
    expect(lookups).toBe(0)
  })

  it('accepts a declarative provider and renders generic scope, validation and output items', () => {
    const contributions = resolveDeclaredProjectContextContributions({
      project: adapterProject(),
      request,
      providers: [provider],
      serviceLookup: serviceName =>
        serviceName === 'syntheticContextProvider' ? validService : undefined,
    })

    expect(contributions).toHaveLength(1)
    expect(contributions[0]?.fingerprint).toMatch(/^sha256:[0-9a-f]{64}$/)
    expect(contributions[0]?.supervision?.obligations[0]?.id).toBe('OBL-SYNTHETIC-READ')
    const items = mergeContributionInlineItems(contributions)
    expect(items.some(item => item.content.includes('write_scope:'))).toBe(true)
    expect(items.some(item => item.content.includes('validate-contract'))).toBe(true)
    expect(items.some(item => item.content.includes('Stable Contract'))).toBe(true)
    expect(mergeContributionReferences(contributions)).toEqual([
      { kind: 'knowledge', id: 'K001', priority: 'high' },
      { kind: 'gate', id: 'G010', priority: 'required' },
    ])
  })

  it('replaces only prior contribution items and preserves host-owned Inline Context', () => {
    const contributions = resolveDeclaredProjectContextContributions({
      project: adapterProject(),
      request,
      providers: [provider],
      serviceLookup: () => validService,
    })
    const merged = replaceContributionInlineItems([
      {
        id: 'host-owned',
        title: 'Host Owned',
        content: 'keep me',
        provenance: 'runtime://synthetic/host',
      },
      {
        id: 'contribution:stale:scope',
        title: 'Stale',
        content: 'remove me',
        provenance: 'provider://stale/context',
      },
    ], contributions)
    expect(merged.some(item => item.id === 'host-owned')).toBe(true)
    expect(merged.some(item => item.id === 'contribution:stale:scope')).toBe(false)
    expect(merged.some(item => item.id.includes('synthetic-analysis'))).toBe(true)
  })

  it('allows a declared provider to report that the task is not applicable', () => {
    const contributions = resolveDeclaredProjectContextContributions({
      project: adapterProject(),
      request,
      providers: [provider],
      serviceLookup: () => ({
        contributeContext: () => ({ applicable: false, reason: 'No matching task kind.' }),
      }),
    })
    expect(contributions).toEqual([])
  })

  it('fails closed when a declared provider is missing', () => {
    expect(() => resolveDeclaredProjectContextContributions({
      project: adapterProject(),
      request,
      providers: [],
      serviceLookup: () => undefined,
    })).toThrow(/unavailable provider/)
  })

  it('rejects unsafe project write scopes', () => {
    expect(() => resolveDeclaredProjectContextContributions({
      project: adapterProject(),
      request,
      providers: [provider],
      serviceLookup: () => ({
        contributeContext: () => ({
          applicable: true,
          contribution: {
            schema: PROJECT_CONTEXT_CONTRIBUTION_SCHEMA,
            projectId: PROJECT_ID,
            taskId: 'TASK-1',
            contributionId: 'unsafe',
            provenance: 'provider://synthetic.context-provider/TASK-1',
            writeScope: { allowed: ['../other-project/**'], protected: [] },
          },
        }),
      }),
    })).toThrow(/safe project-relative path/)
  })

  it('rejects cross-platform absolute and URI-like write scopes', () => {
    for (const unsafe of ['C:/other-project/**', 'source://external/write']) {
      expect(() => resolveDeclaredProjectContextContributions({
        project: adapterProject(),
        request,
        providers: [provider],
        serviceLookup: () => ({
          contributeContext: () => ({
            applicable: true,
            contribution: {
              schema: PROJECT_CONTEXT_CONTRIBUTION_SCHEMA,
              projectId: PROJECT_ID,
              taskId: 'TASK-1',
              contributionId: 'unsafe-cross-platform',
              provenance: 'provider://synthetic.context-provider/TASK-1',
              writeScope: { allowed: [unsafe], protected: [] },
            },
          }),
        }),
      })).toThrow(/safe project-relative path/)
    }
  })

  it('rejects unsafe project read scopes while allowing stable source URIs', () => {
    expect(() => resolveDeclaredProjectContextContributions({
      project: adapterProject(),
      request,
      providers: [provider],
      serviceLookup: () => ({
        contributeContext: () => ({
          applicable: true,
          contribution: {
            schema: PROJECT_CONTEXT_CONTRIBUTION_SCHEMA,
            projectId: PROJECT_ID,
            taskId: 'TASK-1',
            contributionId: 'unsafe-read',
            provenance: 'provider://synthetic.context-provider/TASK-1',
            readScope: ['C:/other-project/secrets/**'],
          },
        }),
      }),
    })).toThrow(/absolute Windows path/)

    expect(() => resolveDeclaredProjectContextContributions({
      project: adapterProject(),
      request,
      providers: [provider],
      serviceLookup: () => ({
        contributeContext: () => ({
          applicable: true,
          contribution: {
            schema: PROJECT_CONTEXT_CONTRIBUTION_SCHEMA,
            projectId: PROJECT_ID,
            taskId: 'TASK-1',
            contributionId: 'unsafe-read-parent',
            provenance: 'provider://synthetic.context-provider/TASK-1',
            readScope: ['../other-project/**'],
          },
        }),
      }),
    })).toThrow(/safe project-relative path/)
  })

  it('rejects cross-project providers and asynchronous providers', () => {
    const foreign = {
      ...provider,
      metadata: { ...provider.metadata, projectId: 'other-project' },
    }
    expect(() => resolveDeclaredProjectContextContributions({
      project: adapterProject(),
      request,
      providers: [foreign],
      serviceLookup: () => validService,
    })).toThrow(/another project/)

    expect(() => resolveDeclaredProjectContextContributions({
      project: adapterProject(),
      request,
      providers: [provider],
      serviceLookup: () => ({ contributeContext: async () => ({ applicable: false, reason: 'async' }) }),
    })).toThrow(/must be synchronous/)
  })
})
