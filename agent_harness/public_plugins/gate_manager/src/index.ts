import type { Context } from '@deepseek-ai/cordis'
import '@agent-harness/governance-core'
import '@agent-harness/project-manager'
import '@agent-harness/evidence-state-manager'
import type { GovernanceManifest } from '@agent-harness/governance-core'
import GateManagerService from './service.js'

export * from './contracts.js'
export * from './gate-parser.js'
export * from './gate-manager-engine.js'
export * from './service.js'

export const name = 'agent-harness-gate-manager'
export const inject = ['governanceCatalog', 'projectManager', 'evidenceStateManager']

export const governanceManifest: GovernanceManifest = {
  manifestVersion: '0.1',
  pluginId: 'public.gate-manager',
  pluginVersion: '0.1.0',
  displayName: 'Public Gate Manager',
  scope: { kind: 'global' },
  trust: 'trusted',
  permissions: ['project.read', 'gate.read', 'evidence.read'],
  provides: [{ capability: 'gate.navigate' }],
}

interface DisposableFiber {
  dispose(): Promise<void> | void
}

export function apply(ctx: Context): void {
  ctx.effect(() => {
    const decision = ctx.governanceCatalog.admit(governanceManifest)
    if (decision.status !== 'admitted') {
      throw new Error(`Gate Manager 治理准入失败: ${decision.reasons.join('; ')}`)
    }

    let disposeProvider: (() => void) | undefined
    let serviceFiber: DisposableFiber | undefined

    try {
      disposeProvider = ctx.governanceCatalog.registerProvider({
        providerId: 'public.gate-manager.default',
        pluginId: governanceManifest.pluginId,
        capability: 'gate.navigate',
        priority: 1000,
        metadata: {
          service: 'gateManager',
          standard: 'gate-v0.1',
          role: 'project-gate-router-and-evidence-checker',
        },
      })
      serviceFiber = ctx.plugin(GateManagerService) as DisposableFiber
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
