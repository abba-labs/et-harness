import { resolve } from 'node:path'
import type { Context } from '@deepseek-ai/cordis'
import '@agent-harness/governance-core'
import '@agent-harness/project-manager'
import {
  PROJECT_CONTEXT_CONTRIBUTION_CAPABILITY,
} from '@agent-harness/auto-governance-engine'
import type { GovernanceManifest } from '@agent-harness/governance-core'
import {
  ATP_CONTEXT_CONTRIBUTOR_PLUGIN_ID,
  ATP_CONTEXT_CONTRIBUTOR_PROVIDER_ID,
  ATP_CONTEXT_CONTRIBUTOR_SERVICE,
  ATP_PROJECT_ID,
  AtpContextContributorService,
} from './context-contributor.js'
import {
  AUTOMATED_TESTING_PLATFORM_PROJECT_MANIFEST,
  findAutomatedTestingPlatformRoot,
  validateAutomatedTestingPlatformResources,
} from './root-discovery.js'

export * from './context-contributor.js'
export * from './contracts.js'
export * from './root-discovery.js'

export const name = 'agent-harness-project-automated-testing-platform'
export const inject = ['governanceCatalog', 'projectManager']

export const governanceManifest: GovernanceManifest = {
  manifestVersion: '0.1',
  pluginId: ATP_CONTEXT_CONTRIBUTOR_PLUGIN_ID,
  pluginVersion: '0.1.0',
  displayName: 'Automated Testing Platform Project Plugin',
  scope: { kind: 'project', id: ATP_PROJECT_ID },
  trust: 'trusted',
  permissions: [
    'project.read',
    'project.register',
    'project.assets.read',
    'context.contribute',
    'process.execute',
  ],
  provides: [{ capability: PROJECT_CONTEXT_CONTRIBUTION_CAPABILITY }],
}

interface DisposableFiber {
  dispose(): Promise<void> | void
}

export function apply(ctx: Context): void {
  ctx.effect(() => {
    const rootPath = findAutomatedTestingPlatformRoot()
    const resourceValidation =
      validateAutomatedTestingPlatformResources(rootPath)

    if (!resourceValidation.valid) {
      throw new Error(
        `Automated Testing Platform Project Plugin 资源校验失败，缺少: ${resourceValidation.missing.join(', ')}`,
      )
    }

    const decision = ctx.governanceCatalog.admit(governanceManifest)
    if (decision.status !== 'admitted') {
      throw new Error(
        `Automated Testing Platform Project Plugin 治理准入失败: ${decision.reasons.join('; ')}`,
      )
    }

    let disposeProject: (() => void) | undefined
    let disposeProvider: (() => void) | undefined
    let serviceFiber: DisposableFiber | undefined

    try {
      serviceFiber = ctx.plugin(AtpContextContributorService) as DisposableFiber
      disposeProvider = ctx.governanceCatalog.registerProvider({
        providerId: ATP_CONTEXT_CONTRIBUTOR_PROVIDER_ID,
        pluginId: governanceManifest.pluginId,
        capability: PROJECT_CONTEXT_CONTRIBUTION_CAPABILITY,
        priority: 1000,
        metadata: {
          projectId: ATP_PROJECT_ID,
          service: ATP_CONTEXT_CONTRIBUTOR_SERVICE,
          method: 'contributeContext',
          contractVersion: '0.1',
          compiler: 'tools/governance/compile_task_context.py',
        },
      })

      const manifestPath = resolve(
        rootPath,
        AUTOMATED_TESTING_PLATFORM_PROJECT_MANIFEST,
      )
      disposeProject = ctx.projectManager.registerProjectFromManifestFile(
        manifestPath,
        rootPath,
      )
    } catch (error) {
      disposeProject?.()
      disposeProvider?.()
      if (serviceFiber) void serviceFiber.dispose()
      ctx.governanceCatalog.removePlugin(governanceManifest.pluginId)
      throw error
    }

    return () => {
      disposeProject?.()
      disposeProvider?.()
      if (serviceFiber) void serviceFiber.dispose()
      ctx.governanceCatalog.removePlugin(governanceManifest.pluginId)
    }
  })
}
