import type { Context } from '@deepseek-ai/cordis'
import '@agent-harness/governance-core'
import '@agent-harness/project-manager'
import '@agent-harness/knowledge-manager'
import '@agent-harness/evidence-state-manager'
import type { GovernanceManifest } from '@agent-harness/governance-core'
import ExperienceMemoryManagerService from './service.js'

export * from './contracts.js'
export * from './knowledge-writer.js'
export * from './service.js'

export const name = 'agent-harness-experience-memory-manager'
export const inject = [
  'governanceCatalog',
  'projectManager',
  'knowledgeManager',
  'knowledgeValidationPolicy',
  'evidenceStateManager',
]

export const governanceManifest: GovernanceManifest = {
  manifestVersion: '0.1',
  pluginId: 'public.experience-memory-manager',
  pluginVersion: '0.2.0',
  displayName: 'Public Experience / Memory Manager',
  scope: { kind: 'global' },
  trust: 'trusted',
  permissions: [
    'project.read',
    'knowledge.read',
    'knowledge.write',
    'evidence.read',
    'state.read',
    'state.write',
  ],
  provides: [
    { capability: 'experience.manage' },
    { capability: 'memory.context' },
  ],
}

interface DisposableFiber { dispose(): Promise<void> | void }

export function apply(ctx: Context): void {
  ctx.effect(() => {
    const decision = ctx.governanceCatalog.admit(governanceManifest)
    if (decision.status !== 'admitted') {
      throw new Error(`Experience / Memory Manager 治理准入失败: ${decision.reasons.join('; ')}`)
    }
    const disposers: Array<() => void> = []
    let serviceFiber: DisposableFiber | undefined
    try {
      for (const capability of ['experience.manage', 'memory.context'] as const) {
        disposers.push(ctx.governanceCatalog.registerProvider({
          providerId: `public.experience-memory-manager.${capability}`,
          pluginId: governanceManifest.pluginId,
          capability,
          priority: 1000,
          metadata: {
            service: 'experienceMemoryManager',
            role: 'project-experience-memory',
            version: '0.2',
            knowledgeLifecycle: 'candidate-verification-validation-promote',
            validationPolicy: 'knowledge-validation-policy-v0.1',
          },
        }))
      }
      serviceFiber = ctx.plugin(ExperienceMemoryManagerService) as DisposableFiber
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
