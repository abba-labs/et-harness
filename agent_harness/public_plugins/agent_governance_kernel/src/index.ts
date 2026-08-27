import type { Context } from '@deepseek-ai/cordis'
import type { GovernanceManifest } from '@agent-harness/governance-core'
import AgentGovernanceKernelService from './service.js'

export * from './contracts.js'
export * from './closure-coordinator.js'
export * from './closure-module-registry.js'
export * from './lifecycle.js'
export * from './reflection.js'
export * from './service.js'
export * from './turn-closure-store.js'

export const name = 'agent-harness-agent-governance-kernel'
export const inject = ['governanceCatalog']

export const governanceManifest: GovernanceManifest = {
  manifestVersion: '0.1',
  pluginId: 'public.agent-governance-kernel',
  pluginVersion: '0.1.0',
  displayName: 'Public Agent Governance Kernel',
  scope: { kind: 'global' },
  trust: 'builtin',
  permissions: ['runtime.lifecycle', 'runtime.journal', 'runtime.reflection', 'runtime.closure'],
  provides: [
    { capability: 'governance.lifecycle' },
    { capability: 'governance.turn-journal' },
    { capability: 'governance.turn-reflection' },
    { capability: 'governance.turn-closure' },
  ],
}

interface DisposableFiber { dispose(): Promise<void> | void }

export function apply(ctx: Context): void {
  ctx.effect(() => {
    const decision = ctx.governanceCatalog.admit(governanceManifest)
    if (decision.status !== 'admitted') {
      throw new Error(`Public Agent Governance Kernel admission failed: ${decision.reasons.join('; ')}`)
    }

    const disposers: Array<() => void> = []
    let serviceFiber: DisposableFiber | undefined
    try {
      for (const capability of [
        'governance.lifecycle',
        'governance.turn-journal',
        'governance.turn-reflection',
        'governance.turn-closure',
      ]) {
        disposers.push(ctx.governanceCatalog.registerProvider({
          providerId: `public.agent-governance-kernel.${capability}`,
          pluginId: governanceManifest.pluginId,
          capability,
          priority: 10_000,
          metadata: {
            service: 'agentGovernanceKernel',
            mandatory: true,
            projectIndependent: true,
            step: 'phase4a-kernel-v0.1-step3',
          },
        }))
      }
      serviceFiber = ctx.plugin(AgentGovernanceKernelService) as DisposableFiber
    } catch (error) {
      for (const dispose of disposers.reverse()) dispose()
      if (serviceFiber) void serviceFiber.dispose()
      ctx.governanceCatalog.removePlugin(governanceManifest.pluginId)
      throw error
    }

    return () => {
      for (const dispose of disposers.reverse()) dispose()
      if (serviceFiber) void serviceFiber.dispose()
      ctx.governanceCatalog.removePlugin(governanceManifest.pluginId)
    }
  })
}
