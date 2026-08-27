import { resolve } from 'node:path'
import type { Context } from '@deepseek-ai/cordis'
import '@agent-harness/project-manager'
import {
  ET_TOOL_PROJECT_MANIFEST,
  findEtToolProjectRoot,
  validateEtToolProjectResources,
} from './root-discovery.js'

export * from './contracts.js'
export * from './root-discovery.js'

export const name = 'agent-harness-project-et-tool'
export const inject = ['projectManager']

export function apply(ctx: Context): void {
  ctx.effect(() => {
    const rootPath = findEtToolProjectRoot()
    const resourceValidation = validateEtToolProjectResources(rootPath)
    if (!resourceValidation.valid) {
      throw new Error(
        `ET-TOOL Project Plugin Shell 资源校验失败，缺少: ${resourceValidation.missing.join(', ')}`,
      )
    }

    const manifestPath = resolve(rootPath, ET_TOOL_PROJECT_MANIFEST)
    return ctx.projectManager.registerProjectFromManifestFile(manifestPath, rootPath)
  })
}
