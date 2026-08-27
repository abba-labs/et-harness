import { resolve } from 'node:path'
import type {
  ProjectContext,
  ProjectManifestV01,
  ProjectResourceKind,
  ProjectResourceStandardId,
} from './contracts.js'
import { assertProjectManifest } from './manifest-validator.js'

const RESOURCE_KINDS: readonly ProjectResourceKind[] = [
  'architecture',
  'rules',
  'knowledge',
  'gates',
]

export function createProjectContext(
  manifestInput: unknown,
  projectRoot: string,
): ProjectContext {
  assertProjectManifest(manifestInput)
  const manifest: ProjectManifestV01 = manifestInput

  const resources = Object.fromEntries(
    RESOURCE_KINDS.map(kind => [kind, `project://${manifest.project.id}/${kind}`]),
  ) as Readonly<Record<ProjectResourceKind, string>>

  const resourceStandards = Object.fromEntries(
    RESOURCE_KINDS.map(kind => [kind, manifest.resources[kind].standard]),
  ) as Readonly<Record<ProjectResourceKind, ProjectResourceStandardId>>

  const base = {
    contractVersion: manifest.contract_version,
    projectId: manifest.project.id,
    displayName: manifest.project.name,
    aliases: manifest.project.aliases ?? [],
    projectRoot: resolve(projectRoot),
    resources,
    resourceStandards,
    adapters: manifest.adapters ?? {},
  }

  return {
    ...base,
    ...(manifest.project.type ? { projectType: manifest.project.type } : {}),
    ...(manifest.metadata ? { metadata: manifest.metadata } : {}),
  }
}

export function resolveProjectResourcePath(
  manifest: ProjectManifestV01,
  projectRoot: string,
  kind: ProjectResourceKind,
): string {
  return resolve(projectRoot, manifest.resources[kind].path)
}
