import { existsSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import type { AutomatedTestingPlatformResourceValidation } from './contracts.js'

export const AUTOMATED_TESTING_PLATFORM_PROJECT_MANIFEST =
  'agent_harness/projects/automated_testing_platform/project.yaml'

export const AUTOMATED_TESTING_PLATFORM_ROOT_MARKERS = [
  'AGENTS.md',
  'pyproject.toml',
  'project-governance/system-map.yaml',
  'report/design/rule_owner_catalog.yaml',
  AUTOMATED_TESTING_PLATFORM_PROJECT_MANIFEST,
] as const

export const AUTOMATED_TESTING_PLATFORM_REQUIRED_PATHS = [
  AUTOMATED_TESTING_PLATFORM_PROJECT_MANIFEST,
  'agent_harness/projects/automated_testing_platform/architecture/00_INDEX.md',
  'agent_harness/projects/automated_testing_platform/rules/00_INDEX.md',
  'agent_harness/projects/automated_testing_platform/knowledge/00_INDEX.md',
  'agent_harness/projects/automated_testing_platform/knowledge/TAXONOMY.yaml',
  'agent_harness/projects/automated_testing_platform/knowledge/SOURCES.yaml',
  'agent_harness/projects/automated_testing_platform/gates/00_INDEX.md',
] as const

export function isAutomatedTestingPlatformRoot(candidate: string): boolean {
  const root = resolve(candidate)
  return AUTOMATED_TESTING_PLATFORM_ROOT_MARKERS.every(marker =>
    existsSync(resolve(root, marker)),
  )
}

export function findAutomatedTestingPlatformRoot(startPath?: string): string {
  const explicitRoot =
    process.env.AUTOMATED_TESTING_PLATFORM_PROJECT_ROOT?.trim()
  let current = resolve(explicitRoot || startPath || process.cwd())

  if (explicitRoot) {
    if (!isAutomatedTestingPlatformRoot(current)) {
      throw new Error(
        `AUTOMATED_TESTING_PLATFORM_PROJECT_ROOT=${explicitRoot} 不是有效 ATP 项目根目录`,
      )
    }
    return current
  }

  for (;;) {
    if (isAutomatedTestingPlatformRoot(current)) return current
    const parent = dirname(current)
    if (parent === current) break
    current = parent
  }

  throw new Error(
    '无法发现 Automated Testing Platform 项目根目录；请从项目内启动，或设置 AUTOMATED_TESTING_PLATFORM_PROJECT_ROOT',
  )
}

export function validateAutomatedTestingPlatformResources(
  rootPath: string,
  relativePaths: readonly string[] =
    AUTOMATED_TESTING_PLATFORM_REQUIRED_PATHS,
): AutomatedTestingPlatformResourceValidation {
  const checked = relativePaths.map(path => resolve(rootPath, path))
  const missing = checked.filter(path => !existsSync(path))
  return {
    valid: missing.length === 0,
    checked,
    missing,
  }
}
