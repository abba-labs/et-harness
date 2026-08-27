import type { Context } from '@deepseek-ai/cordis'
import '@agent-harness/governance-core'
import type { GovernanceManifest } from '@agent-harness/governance-core'
import ProjectManagerService from './service.js'

export * from './manifest-loader.js'
export * from './project-registry-engine.js'
export * from './service.js'

export const name = 'agent-harness-project-manager'
export const inject = ['governanceCatalog']

export const governanceManifest: GovernanceManifest = {
  manifestVersion: '0.1',
  pluginId: 'public.project-manager',
  pluginVersion: '0.1.0',
  displayName: 'Public Project Manager',
  scope: { kind: 'global' },
  trust: 'trusted',
  permissions: ['project.read', 'project.register'],
  provides: [{ capability: 'governance.project' }],
}

interface DisposableFiber {
  dispose(): Promise<void> | void
}

export function apply(ctx: Context): void {
  ctx.effect(() => {
    const decision = ctx.governanceCatalog.admit(governanceManifest)
    if (decision.status !== 'admitted') {
      throw new Error(`Project Manager 治理准入失败: ${decision.reasons.join('; ')}`)
    }

    let disposeProvider: (() => void) | undefined
    let serviceFiber: DisposableFiber | undefined

    try {
      disposeProvider = ctx.governanceCatalog.registerProvider({
        providerId: 'public.project-manager.default',
        pluginId: governanceManifest.pluginId,
        capability: 'governance.project',
        priority: 1000,
        metadata: {
          service: 'projectManager',
          contractVersion: '0.1',
          role: 'public-project-router',
        },
      })

      serviceFiber = ctx.plugin(ProjectManagerService) as DisposableFiber
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
