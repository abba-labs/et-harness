import { readFileSync } from 'node:fs'
import { parse } from 'yaml'
import type { ProjectManifestV01 } from '@agent-harness/project-contract'
import { assertProjectManifest } from '@agent-harness/project-contract'

export function loadProjectManifestFile(path: string): ProjectManifestV01 {
  const raw = readFileSync(path, 'utf-8')
  const parsed: unknown = parse(raw)
  assertProjectManifest(parsed)
  return parsed
}
