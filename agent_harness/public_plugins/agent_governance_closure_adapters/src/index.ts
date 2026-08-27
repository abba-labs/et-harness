import type { Context } from '@deepseek-ai/cordis'
import type { GovernanceManifest } from '@agent-harness/governance-core'
import '@agent-harness/agent-governance-kernel'
import '@agent-harness/context-builder'
import '@agent-harness/knowledge-manager'
import '@agent-harness/experience-memory-manager'
import '@agent-harness/evidence-state-manager'
import '@agent-harness/gate-manager'
import AgentGovernanceClosureAdaptersService from './service.js'

export * from './change-candidate-store.js'
export * from './modules.js'
export * from './remaining-modules.js'
export * from './service.js'

export const name = 'agent-harness-agent-governance-closure-adapters'
export const inject = [
  'governanceCatalog',
  'agentGovernanceKernel',
  'contextManager',
  'knowledgeManager',
  'experienceMemoryManager',
  'evidenceStateManager',
  'gateManager',
]

export const governanceManifest: GovernanceManifest = {
  manifestVersion: '0.1',
  pluginId: 'public.agent-governance-closure-adapters',
  pluginVersion: '0.1.0',
  displayName: 'Public Agent Governance Closure Adapters',
  scope: { kind: 'global' },
  trust: 'builtin',
  permissions: [
    'runtime.lifecycle',
    'runtime.reflection',
    'context.manage',
    'knowledge.read',
    'knowledge.write',
    'experience.manage',
    'evidence.read',
    'evidence.write',
    'state.read',
    'state.write',
    'gate.read',
  ],
  provides: [],
}

interface DisposableFiber { dispose(): Promise<void> | void }

export function apply(ctx: Context): void {
  ctx.effect(() => {
    const decision = ctx.governanceCatalog.admit(governanceManifest)
    if (decision.status !== 'admitted') {
      throw new Error(`Closure Adapters admission failed: ${decision.reasons.join('; ')}`)
    }

    let serviceFiber: DisposableFiber | undefined
    try {
      serviceFiber = ctx.plugin(AgentGovernanceClosureAdaptersService) as DisposableFiber
    } catch (error) {
      if (serviceFiber) void serviceFiber.dispose()
      ctx.governanceCatalog.removePlugin(governanceManifest.pluginId)
      throw error
    }

    return () => {
      if (serviceFiber) void serviceFiber.dispose()
      ctx.governanceCatalog.removePlugin(governanceManifest.pluginId)
    }
  })
}
