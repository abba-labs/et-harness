import { readFileSync } from 'node:fs'
import { isAbsolute, resolve } from 'node:path'

import { layout, repositoryRoot } from './environment-layout.mjs'
import {
  computeRuntimeSourceSignature,
} from './runtime-bundle-inputs.mjs'
import { resolveCurrentToolchain } from './toolchain.mjs'
import { verifyRuntimeReleaseManifest } from '../src/runtime-release.mjs'

const rawManifestPath = process.argv[2]
if (!rawManifestPath) throw new Error('Usage: verify-candidate-runtime.mjs <absolute-release-manifest-path>')
const manifestPath = resolve(rawManifestPath)
if (!isAbsolute(manifestPath)) throw new Error('Candidate release manifest path must be absolute')

const activePointerBefore = readOptional(layout.activeReleasePointer)
const toolchain = resolveCurrentToolchain()
const sourceSignature = computeRuntimeSourceSignature()
const release = await verifyRuntimeReleaseManifest(manifestPath, {
  expectedSourceSignature: sourceSignature,
  expectedRepositoryRoot: repositoryRoot,
  expectedToolchainId: toolchain.descriptor.toolchainId,
})
if (release.manifest.sourceDirty) {
  throw new Error('Candidate Runtime was built from dirty Framework/product sources and cannot be promoted')
}
const deployment = JSON.parse(readFileSync(release.deploymentConfigPath, 'utf8'))
if (deployment?.environmentRoot !== layout.environmentRoot) {
  throw new Error('Candidate deployment environmentRoot does not match the machine-level ET Harness environment')
}
if (!Array.isArray(deployment.projectBindings)
    || deployment.projectBindings.some(binding => binding.projectRoot?.toLowerCase() !== repositoryRoot.toLowerCase())) {
  throw new Error('Candidate deployment project binding does not match the tested source workspace')
}
const activePointerAfter = readOptional(layout.activeReleasePointer)
if (activePointerAfter !== activePointerBefore) {
  throw new Error('Candidate verification mutated the active Runtime pointer')
}
process.stdout.write(`${JSON.stringify({
  status: 'CANDIDATE_VERIFIED',
  releaseManifestPath: release.manifestPath,
  releaseRoot: release.releaseRoot,
  sourceSignature,
  toolchainId: toolchain.descriptor.toolchainId,
  activeReleaseChanged: false,
})}\n`)

function readOptional(path) {
  try {
    return readFileSync(path, 'utf8')
  } catch {
    return undefined
  }
}
