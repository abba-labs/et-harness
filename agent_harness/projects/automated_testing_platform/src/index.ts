import type { Context } from '@deepseek-ai/cordis'
import '@agent-harness/governance-core'
import {
  PROJECT_CONTEXT_CONTRIBUTION_CAPABILITY,
} from '@agent-harness/auto-governance-engine'
import type { GovernanceManifest } from '@agent-harness/governance-core'
import {
  ATP_CONTEXT_CONTRIBUTOR_PLUGIN_ID,
  ATP_CONTEXT_CONTRIBUTOR_PROVIDER_ID,
  ATP_CONTEXT_CONTRIBUTOR_SERVICE,
  ATP_PROJECT_ID,
} from './context-contributor.js'
import AtpCheckpointContextContributorService from './checkpoint-context-contributor.js'
import {
  ATP_CONTEXT_GATE_CAPABILITY,
  ATP_CONTEXT_GATE_PROVIDER_ID,
  ATP_SCOPE_GATE_CAPABILITY,
  ATP_SCOPE_GATE_PROVIDER_ID,
  ATP_SOFTWARE_GATE_CAPABILITY,
  ATP_SOFTWARE_GATE_PROVIDER_ID,
} from './gate-evidence-provider.js'
export * from './context-contributor.js'
export * from './checkpoint-context-contributor.js'
export * from './contracts.js'
export * from './gate-evidence-provider.js'
export * from './root-discovery.js'

export const name = 'agent-harness-project-automated-testing-platform'
export const inject = ['governanceCatalog']

export const governanceManifest: GovernanceManifest = {
  manifestVersion: '0.1',
  pluginId: ATP_CONTEXT_CONTRIBUTOR_PLUGIN_ID,
  pluginVersion: '0.1.0',
  displayName: 'Automated Testing Platform Project Plugin',
  scope: { kind: 'project', id: ATP_PROJECT_ID },
  trust: 'trusted',
  permissions: [
    'project.read',
    'project.assets.read',
    'context.contribute',
    'process.execute',
  ],
  provides: [
    { capability: PROJECT_CONTEXT_CONTRIBUTION_CAPABILITY },
    ...[
      ATP_CONTEXT_GATE_CAPABILITY,
      ATP_SCOPE_GATE_CAPABILITY,
      ATP_SOFTWARE_GATE_CAPABILITY,
    ].map(capability => ({
      capability,
      contract: {
        id: capability,
        version: '0.1',
        summary: 'Project-owned deterministic Gate evidence production for one compiled ATP validation step.',
        criticality: 'important' as const,
        inputSchema: 'agent-harness.project-gate-evidence-invocation.v0.1',
        outputSchema: 'agent-harness.project-gate-evidence-result.v0.1',
      },
    })),
  ],
}

interface DisposableFiber {
  dispose(): Promise<void> | void
}

export function apply(ctx: Context): void {
  ctx.effect(() => {
    const decision = ctx.governanceCatalog.admit(governanceManifest)
    if (decision.status !== 'admitted') {
      throw new Error(
        `Automated Testing Platform Project Plugin 治理准入失败: ${decision.reasons.join('; ')}`,
      )
    }

    const disposeProviders: Array<() => void> = []
    let serviceFiber: DisposableFiber | undefined

    try {
      serviceFiber = ctx.plugin(AtpCheckpointContextContributorService) as DisposableFiber
      disposeProviders.push(ctx.governanceCatalog.registerProvider({
        providerId: ATP_CONTEXT_CONTRIBUTOR_PROVIDER_ID,
        pluginId: governanceManifest.pluginId,
        capability: PROJECT_CONTEXT_CONTRIBUTION_CAPABILITY,
        priority: 1000,
        metadata: {
          projectId: ATP_PROJECT_ID,
          service: ATP_CONTEXT_CONTRIBUTOR_SERVICE,
          method: 'contributeContext',
          contractVersion: '0.1',
          compiler: 'tools/governance/compile_task_context.py',
        },
      }))
      for (const provider of [
        {
          providerId: ATP_CONTEXT_GATE_PROVIDER_ID,
          capability: ATP_CONTEXT_GATE_CAPABILITY,
          gateId: 'G010.010.010',
          stepId: 'compile-context',
        },
        {
          providerId: ATP_SCOPE_GATE_PROVIDER_ID,
          capability: ATP_SCOPE_GATE_CAPABILITY,
          gateId: 'G010.010.020',
          stepId: 'scope-check',
        },
        {
          providerId: ATP_SOFTWARE_GATE_PROVIDER_ID,
          capability: ATP_SOFTWARE_GATE_CAPABILITY,
          gateId: 'G010.010.030',
          stepId: 'project-software-validation',
        },
      ]) {
        disposeProviders.push(ctx.governanceCatalog.registerProvider({
          providerId: provider.providerId,
          pluginId: governanceManifest.pluginId,
          capability: provider.capability,
          priority: 1000,
          metadata: {
            projectId: ATP_PROJECT_ID,
            service: ATP_CONTEXT_CONTRIBUTOR_SERVICE,
            preflightMethod: 'matchGateEvidenceInvocation',
            resultMethod: 'buildValidationReceipt',
            executionMethod: 'executeGateEvidence',
            gateId: provider.gateId,
            stepId: provider.stepId,
            contractVersion: '0.1',
          },
        }))
      }

    } catch (error) {
      for (const disposeProvider of disposeProviders.reverse()) disposeProvider()
      if (serviceFiber) void serviceFiber.dispose()
      ctx.governanceCatalog.removePlugin(governanceManifest.pluginId)
      throw error
    }

    return () => {
      for (const disposeProvider of disposeProviders.reverse()) disposeProvider()
      if (serviceFiber) void serviceFiber.dispose()
      ctx.governanceCatalog.removePlugin(governanceManifest.pluginId)
    }
  })
}
