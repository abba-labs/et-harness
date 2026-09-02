import { randomUUID } from 'node:crypto'
import {
  mkdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import { isAbsolute, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

import { layout, repositoryRoot } from './environment-layout.mjs'
import { computeRuntimeSourceSignature } from './runtime-bundle-inputs.mjs'
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

const verificationRoot = resolve(
  layout.tempRoot,
  'candidate-runtime-verification',
  `${process.pid}-${randomUUID()}`,
)
mkdirSync(verificationRoot, { recursive: true })
const isolatedDeploymentPath = resolve(verificationRoot, 'deployment.json')
const previousStateRoot = process.env.AGENT_HARNESS_STATE_ROOT
const previousMetricsRoot = process.env.AGENT_HARNESS_METRICS_ROOT
let runtimeModule
try {
  const isolatedDeployment = {
    ...deployment,
    environmentRoot: verificationRoot,
    stateRoot: resolve(verificationRoot, 'runtime-state'),
    eventStoreRoot: resolve(verificationRoot, 'execution-events'),
  }
  writeFileSync(
    isolatedDeploymentPath,
    `${JSON.stringify(isolatedDeployment, null, 2)}\n`,
    'utf8',
  )

  const namespace = await import(
    `${pathToFileURL(release.runtimeArtifactPath).href}?candidate-verify=${randomUUID()}`
  )
  if (typeof namespace.createPureMcpRuntimeModule !== 'function') {
    throw new Error('Candidate Runtime artifact does not export createPureMcpRuntimeModule')
  }
  runtimeModule = namespace.createPureMcpRuntimeModule(isolatedDeploymentPath)
  const resolvedProject = await runtimeModule.resolveProject(repositoryRoot)
  if (!resolvedProject?.projectId || resolvedProject.projectId !== deployment.projectBindings[0]?.projectId) {
    throw new Error('Candidate Runtime could not resolve the configured validation project')
  }
  const bootstrap = await runtimeModule.projectBootstrap(repositoryRoot)
  if (bootstrap?.projectId !== resolvedProject.projectId
      || typeof bootstrap.fingerprint !== 'string'
      || !bootstrap.fingerprint.startsWith('sha256:')
      || !Array.isArray(bootstrap.architecture?.roots)
      || bootstrap.architecture.roots.length === 0) {
    throw new Error('Candidate Runtime Architecture Bootstrap smoke returned an invalid result')
  }
} finally {
  try {
    await runtimeModule?.close?.()
  } finally {
    if (previousStateRoot === undefined) delete process.env.AGENT_HARNESS_STATE_ROOT
    else process.env.AGENT_HARNESS_STATE_ROOT = previousStateRoot
    if (previousMetricsRoot === undefined) delete process.env.AGENT_HARNESS_METRICS_ROOT
    else process.env.AGENT_HARNESS_METRICS_ROOT = previousMetricsRoot
    rmSync(verificationRoot, { recursive: true, force: true })
  }
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
  runtimeCompositionSmoke: 'PASS',
  architectureBootstrapSmoke: 'PASS',
  stableStateUsed: false,
  activeReleaseChanged: false,
})}\n`)

function readOptional(path) {
  try {
    return readFileSync(path, 'utf8')
  } catch {
    return undefined
  }
}
