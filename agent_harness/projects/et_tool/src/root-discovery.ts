import { existsSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import type { EtToolProjectResourceValidation } from './contracts.js'

export const ET_TOOL_PROJECT_MANIFEST = 'agent_harness/projects/et_tool/project.yaml'

export const ET_TOOL_ROOT_MARKERS = [
  'source/CMakeLists.txt',
  ET_TOOL_PROJECT_MANIFEST,
] as const

export const ET_TOOL_PROJECT_SHELL_REQUIRED_PATHS = [
  ET_TOOL_PROJECT_MANIFEST,
  'agent_harness/projects/et_tool/architecture/00_INDEX.md',
  'agent_harness/projects/et_tool/rules/00_INDEX.md',
  'agent_harness/projects/et_tool/knowledge/00_INDEX.md',
  'agent_harness/projects/et_tool/gates/00_INDEX.md',
] as const

export function isEtToolProjectRoot(candidate: string): boolean {
  const root = resolve(candidate)
  return ET_TOOL_ROOT_MARKERS.every(marker => existsSync(resolve(root, marker)))
}

export function findEtToolProjectRoot(startPath?: string): string {
  const explicitRoot = process.env.ET_TOOL_PROJECT_ROOT?.trim()
  let current = resolve(explicitRoot || startPath || process.cwd())

  if (explicitRoot) {
    if (!isEtToolProjectRoot(current)) {
      throw new Error(
        `ET_TOOL_PROJECT_ROOT=${explicitRoot} 不是有效 ET-TOOL 根目录；必须包含 source/CMakeLists.txt 与 Project Contract manifest。`,
      )
    }
    return current
  }

  for (;;) {
    if (isEtToolProjectRoot(current)) return current
    const parent = dirname(current)
    if (parent === current) break
    current = parent
  }

  throw new Error(
    `无法发现 ET-TOOL 根目录。请从仓库内启动，或设置 ET_TOOL_PROJECT_ROOT。`,
  )
}

export function validateEtToolProjectResources(
  rootPath: string,
  relativePaths: readonly string[] = ET_TOOL_PROJECT_SHELL_REQUIRED_PATHS,
): EtToolProjectResourceValidation {
  const checked = relativePaths.map(path => resolve(rootPath, path))
  const missing = checked.filter(path => !existsSync(path))

  return {
    valid: missing.length === 0,
    checked,
    missing,
  }
}
