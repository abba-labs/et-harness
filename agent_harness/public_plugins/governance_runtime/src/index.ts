import type { Context } from '@deepseek-ai/cordis'
import type { GovernanceManifest } from '@agent-harness/governance-core'
import '@agent-harness/agent-governance-kernel'
import '@agent-harness/agent-governance-closure-adapters'
import '@agent-harness/auto-governance-engine'
import '@agent-harness/knowledge-manager'
import GovernanceRuntimeService from './service.js'

export * from './contracts.js'
export * from './turn-observation-store.js'
export * from './knowledge-governance-decision.js'
export * from './tool-gateway.js'
export * from './host-runtime-port.js'
export * from './baseline-supervision-compiler.js'
export * from './service.js'

export const name = 'agent-harness-governance-runtime'
export const inject = [
  'governanceCatalog',
  'agentGovernanceKernel',
  'agentGovernanceClosureAdapters',
  'autoGovernanceEngine',
  'knowledgeManager',
  'knowledgeValidationPolicy',
]

export const governanceManifest: GovernanceManifest = {
  manifestVersion: '0.1',
  pluginId: 'public.governance-runtime',
  pluginVersion: '0.1.0',
  displayName: 'Public Governance Runtime',
  scope: { kind: 'global' },
  trust: 'builtin',
  permissions: [
    'runtime.lifecycle',
    'runtime.journal',
    'runtime.reflection',
    'runtime.closure',
    'project.read',
    'context.build',
    'context.manage',
    'knowledge.read',
    'knowledge.write',
  ],
  provides: [{
    capability: 'governance.runtime',
    contract: {
      id: 'governance.runtime',
      version: '0.1',
      summary: 'Host/model-independent runtime that owns governed Turn lifecycle, automatic Context routing, semantic reflection and mandatory closure.',
      criticality: 'core',
    },
  }],
}

interface DisposableFiber { dispose(): Promise<void> | void }

export function apply(ctx: Context): void {
  ctx.effect(() => {
    const decision = ctx.governanceCatalog.admit(governanceManifest)
    if (decision.status !== 'admitted') {
      throw new Error(`Governance Runtime admission failed: ${decision.reasons.join('; ')}`)
    }
    const missing = ctx.agentGovernanceKernel.getMissingMandatoryClosureModules()
    if (missing.length > 0) {
      throw new Error(`Governance Runtime requires all fixed Closure Modules: missing ${missing.join(', ')}`)
    }

    let disposeProvider: (() => void) | undefined
    let serviceFiber: DisposableFiber | undefined
    try {
      disposeProvider = ctx.governanceCatalog.registerProvider({
        providerId: 'public.governance-runtime.default',
        pluginId: governanceManifest.pluginId,
        capability: 'governance.runtime',
        priority: 20_000,
        metadata: {
          service: 'governanceRuntime',
          role: 'host-model-independent-governance-runtime',
          hostSpecific: false,
          modelSpecific: false,
          toolSystemSpecific: false,
          ownsTurnLifecycle: true,
          ownsReflectionTrigger: true,
          ownsClosureTrigger: true,
        },
      })
      serviceFiber = ctx.plugin(GovernanceRuntimeService) as DisposableFiber
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
