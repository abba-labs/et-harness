import type { Context } from '@deepseek-ai/cordis'
import '@agent-harness/governance-core'
import '@agent-harness/project-manager'
import type { GovernanceManifest } from '@agent-harness/governance-core'
import EvidenceStateManagerService from './service.js'

export * from './contracts.js'
export * from './evidence-state-engine.js'
export * from './service.js'

export const name = 'agent-harness-evidence-state-manager'
export const inject = ['governanceCatalog', 'projectManager']

export const governanceManifest: GovernanceManifest = {
  manifestVersion: '0.1',
  pluginId: 'public.evidence-state-manager',
  pluginVersion: '0.1.0',
  displayName: 'Public Evidence / State Manager',
  scope: { kind: 'global' },
  trust: 'trusted',
  permissions: ['project.read', 'evidence.write', 'evidence.read', 'state.read', 'state.write'],
  provides: [
    { capability: 'evidence.record' },
    { capability: 'evidence.read' },
    { capability: 'state.read' },
    { capability: 'state.update' },
  ],
}

interface DisposableFiber { dispose(): Promise<void> | void }

export function apply(ctx: Context): void {
  ctx.effect(() => {
    const decision = ctx.governanceCatalog.admit(governanceManifest)
    if (decision.status !== 'admitted') {
      throw new Error(`Evidence / State Manager 治理准入失败: ${decision.reasons.join('; ')}`)
    }

    const disposers: Array<() => void> = []
    let serviceFiber: DisposableFiber | undefined
    try {
      for (const capability of ['evidence.record', 'evidence.read', 'state.read', 'state.update'] as const) {
        disposers.push(ctx.governanceCatalog.registerProvider({
          providerId: `public.evidence-state-manager.${capability}`,
          pluginId: governanceManifest.pluginId,
          capability,
          priority: 1000,
          metadata: { service: 'evidenceStateManager', role: 'runtime-fact-store' },
        }))
      }
      serviceFiber = ctx.plugin(EvidenceStateManagerService) as DisposableFiber
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
