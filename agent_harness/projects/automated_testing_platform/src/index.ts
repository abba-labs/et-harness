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
  AtpContextContributorService,
} from './context-contributor.js'
export * from './context-contributor.js'
export * from './contracts.js'
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
  provides: [{ capability: PROJECT_CONTEXT_CONTRIBUTION_CAPABILITY }],
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

    let disposeProvider: (() => void) | undefined
    let serviceFiber: DisposableFiber | undefined

    try {
      serviceFiber = ctx.plugin(AtpContextContributorService) as DisposableFiber
      disposeProvider = ctx.governanceCatalog.registerProvider({
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
      })

    } catch (error) {
      disposeProvider?.()
      if (serviceFiber) void serviceFiber.dispose()
      ctx.governanceCatalog.removePlugin(governanceManifest.pluginId)
      throw error
    }

    return () => {
      disposeProvider?.()
      if (serviceFiber) void serviceFiber.dispose()
      ctx.governanceCatalog.removePlugin(governanceManifest.pluginId)
    }
  })
}
