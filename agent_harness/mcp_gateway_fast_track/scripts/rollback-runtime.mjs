import { randomUUID } from 'node:crypto'
import { readFileSync, renameSync, writeFileSync } from 'node:fs'

import { layout } from './environment-layout.mjs'
import { verifyRuntimeReleasePointer } from '../src/runtime-release.mjs'

const active = await verifyRuntimeReleasePointer(layout.activeReleasePointer)
const previous = await verifyRuntimeReleasePointer(layout.previousReleasePointer)

atomicWriteJson(layout.activeReleasePointer, {
  schema: 'et-harness.pure-mcp-active-release.v1',
  releaseManifestPath: previous.manifestPath,
  activatedAt: new Date().toISOString(),
})
atomicWriteJson(layout.previousReleasePointer, {
  schema: 'et-harness.pure-mcp-active-release.v1',
  releaseManifestPath: active.manifestPath,
  activatedAt: new Date().toISOString(),
})
const restored = await verifyRuntimeReleasePointer(layout.activeReleasePointer)
process.stdout.write(`${JSON.stringify({
  status: 'ROLLED_BACK',
  releaseManifestPath: restored.manifestPath,
  previousReleaseManifestPath: active.manifestPath,
  gatewayRestarted: false,
})}\n`)

function atomicWriteJson(path, value) {
  const temporary = `${path}.${process.pid}.${randomUUID()}.tmp`
  writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, 'utf8')
  renameSync(temporary, path)
}
