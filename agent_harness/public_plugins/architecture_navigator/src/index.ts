import type { Context } from '@deepseek-ai/cordis'
import '@agent-harness/governance-core'
import '@agent-harness/project-manager'
import type { GovernanceManifest } from '@agent-harness/governance-core'
import ArchitectureNavigatorService from './service.js'

export * from './contracts.js'
export * from './architecture-parser.js'
export * from './navigator-engine.js'
export * from './service.js'

export const name = 'agent-harness-architecture-navigator'
export const inject = ['governanceCatalog', 'projectManager']

export const governanceManifest: GovernanceManifest = {
  manifestVersion: '0.1',
  pluginId: 'public.architecture-navigator',
  pluginVersion: '0.1.0',
  displayName: 'Public Architecture Navigator',
  scope: { kind: 'global' },
  trust: 'trusted',
  permissions: ['project.read', 'architecture.read'],
  provides: [{ capability: 'architecture.navigate' }],
}

interface DisposableFiber {
  dispose(): Promise<void> | void
}

export function apply(ctx: Context): void {
  ctx.effect(() => {
    const decision = ctx.governanceCatalog.admit(governanceManifest)
    if (decision.status !== 'admitted') {
      throw new Error(`Architecture Navigator 治理准入失败: ${decision.reasons.join('; ')}`)
    }

    let disposeProvider: (() => void) | undefined
    let serviceFiber: DisposableFiber | undefined

    try {
      disposeProvider = ctx.governanceCatalog.registerProvider({
        providerId: 'public.architecture-navigator.default',
        pluginId: governanceManifest.pluginId,
        capability: 'architecture.navigate',
        priority: 1000,
        metadata: {
          service: 'architectureNavigator',
          standard: 'architecture-v0.1',
          role: 'project-architecture-router',
        },
      })

      serviceFiber = ctx.plugin(ArchitectureNavigatorService) as DisposableFiber
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
