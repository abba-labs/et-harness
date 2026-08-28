import type { Context } from '@deepseek-ai/cordis'
import type { GovernanceManifest } from '@agent-harness/governance-core'
import AutoGovernanceEngineService from './service.js'

export * from './contracts.js'
export * from './context-contribution.js'
export * from './route-resolver.js'
export * from './service.js'

export const name = 'agent-harness-auto-governance-engine'
export const inject = [
  'governanceCatalog',
  'projectManager',
  'architectureNavigator',
  'ruleManager',
  'knowledgeManager',
  'gateManager',
  'evidenceStateManager',
  'contextBuilder',
  'contextManager',
]

export const governanceManifest: GovernanceManifest = {
  manifestVersion: '0.1',
  pluginId: 'public.auto-governance-engine',
  pluginVersion: '0.1.0',
  displayName: 'Public Auto Governance Engine',
  scope: { kind: 'global' },
  trust: 'trusted',
  permissions: [
    'project.read',
    'architecture.read',
    'rule.read',
    'knowledge.read',
    'gate.read',
    'evidence.read',
    'context.build',
    'context.manage',
    'context.contribute',
  ],
  provides: [{
    capability: 'governance.auto-engine',
    contract: {
      id: 'governance.auto-engine',
      version: '0.1',
      summary: 'Host-independent automatic governance engine for project resolution, Context routing, Gate review preparation and completion guards.',
      criticality: 'important',
    },
  }],
}

interface DisposableFiber { dispose(): Promise<void> | void }

export function apply(ctx: Context): void {
  ctx.effect(() => {
    const decision = ctx.governanceCatalog.admit(governanceManifest)
    if (decision.status !== 'admitted') {
      throw new Error(`Auto Governance Engine admission failed: ${decision.reasons.join('; ')}`)
    }

    let disposeProvider: (() => void) | undefined
    let serviceFiber: DisposableFiber | undefined
    try {
      disposeProvider = ctx.governanceCatalog.registerProvider({
        providerId: 'public.auto-governance-engine.default',
        pluginId: governanceManifest.pluginId,
        capability: 'governance.auto-engine',
        priority: 1000,
        metadata: {
          service: 'autoGovernanceEngine',
          role: 'host-independent-governance-engine',
          harnessEvents: [],
          modelSpecific: false,
          toolSystemSpecific: false,
        },
      })
      serviceFiber = ctx.plugin(AutoGovernanceEngineService) as DisposableFiber
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
