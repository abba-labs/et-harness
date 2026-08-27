import type { Context } from '@deepseek-ai/cordis'
import '@agent-harness/governance-core'
import type { GovernanceManifest } from '@agent-harness/governance-core'

export const name = 'agent-harness-governance-demo-plugin'
export const inject = ['governanceCatalog']

const manifest: GovernanceManifest = {
  manifestVersion: '0.1',
  pluginId: 'example.rule-provider',
  pluginVersion: '0.1.0',
  displayName: '示例规则 Provider',
  scope: { kind: 'global' },
  trust: 'reviewed',
  permissions: ['project.read'],
  provides: [{ capability: 'rule.resolve' }],
}

export function apply(ctx: Context): void {
  ctx.effect(() => {
    const decision = ctx.governanceCatalog.admit(manifest)
    if (decision.status !== 'admitted') {
      throw new Error(`治理准入失败: ${decision.reasons.join('; ')}`)
    }

    const disposeProvider = ctx.governanceCatalog.registerProvider({
      providerId: 'example.rule-provider.default',
      pluginId: manifest.pluginId,
      capability: 'rule.resolve',
      priority: 10,
    })

    return () => {
      disposeProvider()
      ctx.governanceCatalog.removePlugin(manifest.pluginId)
    }
  })
}
