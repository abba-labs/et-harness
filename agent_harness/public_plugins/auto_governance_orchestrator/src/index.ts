import type { Context } from '@deepseek-ai/cordis'
import type { GovernanceManifest } from '@agent-harness/governance-core'
import AutoGovernanceOrchestratorService from './service.js'

export * from './contracts.js'
export * from './service.js'

export const name = 'agent-harness-auto-governance-orchestrator'
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
  pluginId: 'public.auto-governance-orchestrator',
  pluginVersion: '0.1.0',
  displayName: 'Public Auto Governance Orchestrator',
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
  ],
  provides: [{
    capability: 'governance.auto',
    contract: {
      id: 'governance.auto',
      version: '0.1',
      summary: 'Automatically bootstraps Context, routes project governance resources, prepares Code Gate reviews and blocks build/test until required Gate evidence is satisfied.',
      criticality: 'important',
    },
  }],
}

interface DisposableFiber { dispose(): Promise<void> | void }

export function apply(ctx: Context): void {
  ctx.effect(() => {
    const decision = ctx.governanceCatalog.admit(governanceManifest)
    if (decision.status !== 'admitted') {
      throw new Error(`Auto Governance Orchestrator 治理准入失败: ${decision.reasons.join('; ')}`)
    }

    let disposeProvider: (() => void) | undefined
    let serviceFiber: DisposableFiber | undefined
    try {
      disposeProvider = ctx.governanceCatalog.registerProvider({
        providerId: 'public.auto-governance-orchestrator.default',
        pluginId: governanceManifest.pluginId,
        capability: 'governance.auto',
        priority: 1000,
        metadata: {
          service: 'autoGovernanceOrchestrator',
          role: 'public-event-driven-governance-controller',
          harnessEvents: [
            'agent/pre-step',
            'tools/pre-execute',
            'tools/result',
            'agent/disposed',
          ],
          hardBuildTestGuard: true,
          semanticReview: 'project-provider',
        },
      })
      serviceFiber = ctx.plugin(AutoGovernanceOrchestratorService) as DisposableFiber
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
