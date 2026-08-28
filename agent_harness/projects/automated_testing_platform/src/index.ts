import { resolve } from 'node:path'
import type { Context } from '@deepseek-ai/cordis'
import '@agent-harness/project-manager'
import {
  AUTOMATED_TESTING_PLATFORM_PROJECT_MANIFEST,
  findAutomatedTestingPlatformRoot,
  validateAutomatedTestingPlatformResources,
} from './root-discovery.js'

export * from './contracts.js'
export * from './root-discovery.js'

export const name = 'agent-harness-project-automated-testing-platform'
export const inject = ['projectManager']

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

    const manifestPath = resolve(
      rootPath,
      AUTOMATED_TESTING_PLATFORM_PROJECT_MANIFEST,
    )
    return ctx.projectManager.registerProjectFromManifestFile(
      manifestPath,
      rootPath,
    )
  })
}
