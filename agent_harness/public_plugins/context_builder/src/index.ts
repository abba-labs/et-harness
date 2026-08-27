import type { Context } from '@deepseek-ai/cordis'
import '@agent-harness/governance-core'
import '@agent-harness/project-manager'
import '@agent-harness/architecture-navigator'
import '@agent-harness/rule-manager'
import '@agent-harness/knowledge-manager'
import '@agent-harness/gate-manager'
import '@agent-harness/evidence-state-manager'
import type { GovernanceManifest } from '@agent-harness/governance-core'
import ContextBuilderService from './service.js'
import ContextManagementService from './context-management-service.js'

export * from './contracts.js'
export * from './context-builder-engine.js'
export * from './context-lint.js'
export * from './service.js'
export * from './context-management-service.js'

export const name = 'agent-harness-context-builder'
export const inject = [
  'governanceCatalog',
  'projectManager',
  'architectureNavigator',
  'ruleManager',
  'knowledgeManager',
  'knowledgeValidationPolicy',
  'gateManager',
  'evidenceStateManager',
]

export const governanceManifest: GovernanceManifest = {
  manifestVersion: '0.1',
  pluginId: 'public.context-builder',
  pluginVersion: '0.2.0',
  displayName: 'Public Context Manager / Builder',
  scope: { kind: 'global' },
  trust: 'trusted',
  permissions: ['project.read', 'context.build', 'context.manage', 'state.read', 'state.update'],
  provides: [
    { capability: 'context.build' },
    { capability: 'context.manage' },
  ],
}

interface DisposableFiber { dispose(): Promise<void> | void }

export function apply(ctx: Context): void {
  ctx.effect(() => {
    const decision = ctx.governanceCatalog.admit(governanceManifest)
    if (decision.status !== 'admitted') {
      throw new Error(`Context Manager / Builder 治理准入失败: ${decision.reasons.join('; ')}`)
    }
    const disposers: Array<() => void> = []
    let builderFiber: DisposableFiber | undefined
    let managerFiber: DisposableFiber | undefined
    try {
      disposers.push(ctx.governanceCatalog.registerProvider({
        providerId: 'public.context-builder.default',
        pluginId: governanceManifest.pluginId,
        capability: 'context.build',
        priority: 1000,
        metadata: {
          service: 'contextBuilder',
          role: 'current-effective-context-packager',
          version: '0.2',
          recordStandard: 'context-record-v0.1',
          lint: 'context-lint-v0.1',
        },
      }))
      disposers.push(ctx.governanceCatalog.registerProvider({
        providerId: 'public.context-manager.default',
        pluginId: governanceManifest.pluginId,
        capability: 'context.manage',
        priority: 1000,
        metadata: {
          service: 'contextManager',
          role: 'task-context-lifecycle-manager',
          state: 'evidenceStateManager',
          recordStandard: 'context-record-v0.1',
          lint: 'context-lint-v0.1',
        },
      }))
      builderFiber = ctx.plugin(ContextBuilderService) as DisposableFiber
      managerFiber = ctx.plugin(ContextManagementService) as DisposableFiber
    } catch (error) {
      for (const dispose of disposers.reverse()) dispose()
      if (managerFiber) void managerFiber.dispose()
      if (builderFiber) void builderFiber.dispose()
      ctx.governanceCatalog.removePlugin(governanceManifest.pluginId)
      throw error
    }
    return () => {
      for (const dispose of disposers.reverse()) dispose()
      if (managerFiber) void managerFiber.dispose()
      if (builderFiber) void builderFiber.dispose()
      ctx.governanceCatalog.removePlugin(governanceManifest.pluginId)
    }
  })
}
