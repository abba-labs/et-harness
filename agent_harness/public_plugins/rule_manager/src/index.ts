import type { Context } from '@deepseek-ai/cordis'
import '@agent-harness/governance-core'
import '@agent-harness/project-manager'
import type { GovernanceManifest } from '@agent-harness/governance-core'
import RuleManagerService from './service.js'

export * from './contracts.js'
export * from './rule-parser.js'
export * from './rule-manager-engine.js'
export * from './service.js'

export const name = 'agent-harness-rule-manager'
export const inject = ['governanceCatalog', 'projectManager']

export const governanceManifest: GovernanceManifest = {
  manifestVersion: '0.1',
  pluginId: 'public.rule-manager',
  pluginVersion: '0.1.0',
  displayName: 'Public Rule Manager',
  scope: { kind: 'global' },
  trust: 'trusted',
  permissions: ['project.read', 'rule.read'],
  provides: [{ capability: 'rule.navigate' }],
}

interface DisposableFiber {
  dispose(): Promise<void> | void
}

export function apply(ctx: Context): void {
  ctx.effect(() => {
    const decision = ctx.governanceCatalog.admit(governanceManifest)
    if (decision.status !== 'admitted') {
      throw new Error(`Rule Manager 治理准入失败: ${decision.reasons.join('; ')}`)
    }

    let disposeProvider: (() => void) | undefined
    let serviceFiber: DisposableFiber | undefined

    try {
      disposeProvider = ctx.governanceCatalog.registerProvider({
        providerId: 'public.rule-manager.default',
        pluginId: governanceManifest.pluginId,
        capability: 'rule.navigate',
        priority: 1000,
        metadata: {
          service: 'ruleManager',
          standard: 'rule-v0.1',
          role: 'project-rule-router',
        },
      })

      serviceFiber = ctx.plugin(RuleManagerService) as DisposableFiber
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
