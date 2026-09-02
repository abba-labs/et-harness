import { randomUUID } from 'node:crypto'
import {
  existsSync,
  mkdirSync,
  renameSync,
  writeFileSync,
} from 'node:fs'
import { dirname, resolve } from 'node:path'

import { layout, repositoryRoot } from './environment-layout.mjs'
import { assertGatewayStoppedForReleaseSwitch } from './gateway-process-state.mjs'
import { computeRuntimeSourceSignature } from './runtime-bundle-inputs.mjs'
import { resolveCurrentToolchain } from './toolchain.mjs'
import {
  verifyRuntimeReleaseManifest,
  verifyRuntimeReleasePointer,
} from '../src/runtime-release.mjs'

const rawManifestPath = process.argv[2]
if (!rawManifestPath) throw new Error('Usage: activate-runtime.mjs <release-manifest-path>')
const candidateManifestPath = resolve(rawManifestPath)
const toolchain = resolveCurrentToolchain()
const candidate = await verifyRuntimeReleaseManifest(candidateManifestPath, {
  expectedSourceSignature: computeRuntimeSourceSignature(),
  expectedRepositoryRoot: repositoryRoot,
  expectedToolchainId: toolchain.descriptor.toolchainId,
})
if (candidate.manifest.sourceDirty) {
  throw new Error('Dirty-source Candidate Runtime cannot be activated')
}

let current
if (existsSync(layout.activeReleasePointer)) {
  current = await verifyRuntimeReleasePointer(layout.activeReleasePointer)
  if (current.manifestPath === candidate.manifestPath) {
    process.stdout.write(`${JSON.stringify({
      status: 'ALREADY_ACTIVE',
      releaseManifestPath: candidate.manifestPath,
      previousReleaseChanged: false,
    })}\n`)
    process.exit(0)
  }
}

// Release pointer switching is intentionally separated from process lifecycle.
// The Gateway must already be stopped so no v1 lazy Runtime load or v2 process
// can observe a pointer transition mid-process.
assertGatewayStoppedForReleaseSwitch()

mkdirSync(dirname(layout.activeReleasePointer), { recursive: true })
if (current) {
  atomicWriteJson(layout.previousReleasePointer, {
    schema: 'et-harness.pure-mcp-active-release.v1',
    releaseManifestPath: current.manifestPath,
    activatedAt: new Date().toISOString(),
  })
}
atomicWriteJson(layout.activeReleasePointer, {
  schema: 'et-harness.pure-mcp-active-release.v1',
  releaseManifestPath: candidate.manifestPath,
  activatedAt: new Date().toISOString(),
})
const active = await verifyRuntimeReleasePointer(layout.activeReleasePointer, {
  expectedSourceSignature: candidate.manifest.sourceSignature,
  expectedRepositoryRoot: repositoryRoot,
  expectedToolchainId: toolchain.descriptor.toolchainId,
})
process.stdout.write(`${JSON.stringify({
  status: 'ACTIVATED',
  releaseManifestPath: active.manifestPath,
  previousReleaseManifestPath: current?.manifestPath,
  gatewayRestarted: false,
})}\n`)

function atomicWriteJson(path, value) {
  const temporary = `${path}.${process.pid}.${randomUUID()}.tmp`
  writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, 'utf8')
  renameSync(temporary, path)
}
