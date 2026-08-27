import type { Context } from '@deepseek-ai/cordis'
import '@agent-harness/governance-core'
import '@agent-harness/project-manager'
import type { GovernanceManifest } from '@agent-harness/governance-core'
import KnowledgeManagerService from './service.js'
import KnowledgeValidationPolicyService from './validation-service.js'

export * from './contracts.js'
export * from './knowledge-address.js'
export * from './source-verification-store.js'
export * from './validation-policy.js'
export * from './knowledge-promotion.js'
export * from './knowledge-parser.js'
export * from './taxonomy-parser.js'
export * from './knowledge-index-generator.js'
export * from './knowledge-manager-engine.js'
export * from './knowledge-library-mutator.js'
export * from './service.js'
export * from './validation-service.js'

export const name = 'agent-harness-knowledge-manager'
export const inject = ['governanceCatalog', 'projectManager']

export const governanceManifest: GovernanceManifest = {
  manifestVersion: '0.1',
  pluginId: 'public.knowledge-manager',
  pluginVersion: '0.2.0',
  displayName: 'Public Knowledge Manager',
  scope: { kind: 'global' },
  trust: 'trusted',
  permissions: [
    'project.read',
    'knowledge.read',
    'knowledge.write',
    'knowledge.index.write',
    'evidence.read',
  ],
  provides: [
    { capability: 'knowledge.navigate' },
    { capability: 'knowledge.library' },
  ],
}

interface DisposableFiber {
  dispose(): Promise<void> | void
}

export function apply(ctx: Context): void {
  ctx.effect(() => {
    const decision = ctx.governanceCatalog.admit(governanceManifest)
    if (decision.status !== 'admitted') {
      throw new Error(`Knowledge Manager 治理准入失败: ${decision.reasons.join('; ')}`)
    }

    const disposers: Array<() => void> = []
    const serviceFibers: DisposableFiber[] = []

    try {
      disposers.push(ctx.governanceCatalog.registerProvider({
        providerId: 'public.knowledge-manager.default',
        pluginId: governanceManifest.pluginId,
        capability: 'knowledge.navigate',
        priority: 1000,
        metadata: {
          service: 'knowledgeManager',
          nodeStandard: 'knowledge-v0.1',
          libraryStandard: 'knowledge-library-v0.2',
          scopes: ['global', 'project'],
          role: 'scoped-knowledge-router',
        },
      }))
      disposers.push(ctx.governanceCatalog.registerProvider({
        providerId: 'public.knowledge-manager.library',
        pluginId: governanceManifest.pluginId,
        capability: 'knowledge.library',
        priority: 1000,
        metadata: {
          service: 'knowledgeManager',
          validationService: 'knowledgeValidationPolicy',
          libraryStandard: 'knowledge-library-v0.2',
          sourceStandard: 'knowledge-source-registry-v0.1',
          verificationStandard: 'knowledge-verification-v0.1',
          validationPolicy: 'knowledge-validation-policy-v0.1',
          scopes: ['global', 'project'],
          globalRootEnv: 'AGENT_HARNESS_GLOBAL_KNOWLEDGE_ROOT',
          role: 'scoped-knowledge-library-manager',
        },
      }))
      serviceFibers.push(ctx.plugin(KnowledgeManagerService) as DisposableFiber)
      serviceFibers.push(ctx.plugin(KnowledgeValidationPolicyService) as DisposableFiber)
    } catch (error) {
      for (const dispose of disposers.reverse()) dispose()
      for (const fiber of serviceFibers.reverse()) void fiber.dispose()
      ctx.governanceCatalog.removePlugin(governanceManifest.pluginId)
      throw error
    }

    return () => {
      for (const dispose of disposers.reverse()) dispose()
      for (const fiber of serviceFibers.reverse()) void fiber.dispose()
      ctx.governanceCatalog.removePlugin(governanceManifest.pluginId)
    }
  })
}
