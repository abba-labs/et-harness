import {
  copyFileSync,
  cpSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  rmSync,
} from 'node:fs'
import { join, resolve } from 'node:path'
import { tmpdir } from 'node:os'

export interface EtToolProjectSnapshot {
  readonly root: string
  dispose(): void
}

const REQUIRED_PROJECT_RESOURCES = [
  'architecture',
  'rules',
  'knowledge',
  'gates',
] as const

export function createEtToolProjectSnapshot(sourceRootInput: string): EtToolProjectSnapshot {
  const sourceRoot = resolve(sourceRootInput)
  const projectResources = join(sourceRoot, 'agent_harness', 'projects', 'et_tool')
  const sourceManifest = join(projectResources, 'project.yaml')
  const sourceCmake = join(sourceRoot, 'source', 'CMakeLists.txt')
  const sourceApps = join(sourceRoot, 'source', 'apps')
  if (!existsSync(sourceManifest)) throw new Error(`ET-TOOL project manifest missing: ${sourceManifest}`)
  if (!existsSync(sourceCmake)) throw new Error(`ET-TOOL root marker missing: ${sourceCmake}`)
  if (!existsSync(sourceApps)) throw new Error(`ET-TOOL root marker missing: ${sourceApps}`)
  for (const resource of REQUIRED_PROJECT_RESOURCES) {
    const path = join(projectResources, resource)
    if (!existsSync(path)) throw new Error(`ET-TOOL project resource missing: ${path}`)
  }

  const root = mkdtempSync(join(tmpdir(), 'agent-harness-et-tool-level2c-'))
  const targetProjectResources = join(root, 'agent_harness', 'projects', 'et_tool')
  const targetSource = join(root, 'source')
  mkdirSync(targetProjectResources, { recursive: true })
  mkdirSync(join(targetSource, 'apps'), { recursive: true })
  copyFileSync(sourceCmake, join(targetSource, 'CMakeLists.txt'))
  copyFileSync(sourceManifest, join(targetProjectResources, 'project.yaml'))
  for (const resource of REQUIRED_PROJECT_RESOURCES) {
    cpSync(join(projectResources, resource), join(targetProjectResources, resource), { recursive: true })
  }

  return {
    root,
    dispose: () => rmSync(root, { recursive: true, force: true }),
  }
}
