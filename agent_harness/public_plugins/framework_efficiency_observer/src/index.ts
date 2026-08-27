import type { Context } from '@deepseek-ai/cordis'
import {
  activateFrameworkMetrics,
  type GovernanceManifest,
} from '@agent-harness/governance-core'
import FrameworkEfficiencyObserverService from './service.js'

export * from './contracts.js'
export * from './analyzer.js'
export * from './session-analyzer.js'
export * from './service.js'

export const name = 'agent-harness-framework-efficiency-observer'
export const inject = ['governanceCatalog']

export const governanceManifest: GovernanceManifest = {
  manifestVersion: '0.1',
  pluginId: 'public.framework-efficiency-observer',
  pluginVersion: '0.1.0',
  displayName: 'Framework Efficiency Observer',
  scope: { kind: 'global' },
  trust: 'trusted',
  permissions: ['metrics.read', 'metrics.write'],
  provides: [{
    capability: 'observability.framework',
    contract: {
      id: 'observability.framework',
      version: '0.1',
      summary: '可拔插旁路采集与离线分析 Framework Efficiency Metrics',
      criticality: 'optional',
    },
  }],
}

interface DisposableFiber { dispose(): Promise<void> | void }

export function apply(ctx: Context): void {
  ctx.effect(() => {
    const decision = ctx.governanceCatalog.admit(governanceManifest)
    if (decision.status !== 'admitted') {
      throw new Error(`Framework Efficiency Observer 治理准入失败: ${decision.reasons.join('; ')}`)
    }

    let disposeProvider: (() => void) | undefined
    let disposeActivation: (() => void) | undefined
    let serviceFiber: DisposableFiber | undefined
    try {
      disposeProvider = ctx.governanceCatalog.registerProvider({
        providerId: 'public.framework-efficiency-observer.default',
        pluginId: governanceManifest.pluginId,
        capability: 'observability.framework',
        priority: 100,
        metadata: {
          service: 'frameworkEfficiencyObserver',
          role: 'optional-sidecar-observer',
          standard: 'framework-metric-v0.1',
          failOpen: true,
          absentFastPath: true,
          sessionAnalysis: 'offline',
        },
      })
      disposeActivation = activateFrameworkMetrics()
      serviceFiber = ctx.plugin(FrameworkEfficiencyObserverService) as DisposableFiber
    } catch (error) {
      disposeActivation?.()
      disposeProvider?.()
      if (serviceFiber) void serviceFiber.dispose()
      ctx.governanceCatalog.removePlugin(governanceManifest.pluginId)
      throw error
    }

    return () => {
      disposeActivation?.()
      disposeProvider?.()
      if (serviceFiber) void serviceFiber.dispose()
      ctx.governanceCatalog.removePlugin(governanceManifest.pluginId)
    }
  })
}
