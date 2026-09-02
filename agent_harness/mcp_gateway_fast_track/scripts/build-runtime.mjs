import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import {
  mkdirSync,
  readFileSync,
  readdirSync,
  renameSync,
  rmSync,
  statSync,
  writeFileSync,
} from 'node:fs'
import { relative, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

import {
  atpProjectPluginEntry,
  computeRuntimeDeploymentFingerprint,
  computeRuntimeSourceSignature,
  packageRoot,
  repositoryRoot,
  resolveBundleSpecifier,
  runtimeOwnerEntry,
} from './runtime-bundle-inputs.mjs'
import { EXPECTED_NODE_VERSION, layout } from './environment-layout.mjs'
import { resolveCurrentToolchain } from './toolchain.mjs'
import { verifyRuntimeReleaseManifest } from '../src/runtime-release.mjs'

if (process.version !== EXPECTED_NODE_VERSION) {
  throw new Error(`Candidate Runtime build requires ${EXPECTED_NODE_VERSION}; current Node is ${process.version}`)
}

const toolchain = resolveCurrentToolchain()
const rolldownEntry = resolveBundleSpecifier('rolldown')
if (!rolldownEntry) throw new Error('Shared Toolchain cannot resolve rolldown')
const { rolldown } = await import(pathToFileURL(rolldownEntry).href)

const hashFile = path => createHash('sha256').update(readFileSync(path)).digest('hex')
const writeJson = (path, value) => writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`, 'utf8')

const filesBelow = directory => {
  const files = []
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const path = resolve(directory, entry.name)
    if (entry.isDirectory()) files.push(...filesBelow(path))
    else if (entry.isFile()) files.push(path)
  }
  return files
}

const sourceRevision = () => execFileSync(
  'git.exe',
  ['rev-parse', 'HEAD'],
  { cwd: repositoryRoot, encoding: 'utf8', windowsHide: true },
).trim()

const sourceDirty = () => Boolean(execFileSync(
  'git.exe',
  ['status', '--short', '--',
    'agent_harness/mcp_gateway_fast_track',
    'agent_harness/governance_core',
    'agent_harness/project_contract',
    'agent_harness/public_plugins',
    'agent_harness/projects/automated_testing_platform'],
  { cwd: repositoryRoot, encoding: 'utf8', windowsHide: true },
).trim())

const aliasPlugin = {
  name: 'et-harness-shared-toolchain-aliases',
  resolveId(source) {
    return resolveBundleSpecifier(source)
  },
}

const sourceSignature = computeRuntimeSourceSignature()
const deploymentFingerprint = computeRuntimeDeploymentFingerprint()
const releaseId = createHash('sha256')
  .update(`et-harness-release-v2\0${deploymentFingerprint}\0${toolchain.descriptor.toolchainId}`)
  .digest('hex')
  .slice(0, 20)
const releaseRoot = resolve(layout.releasesRoot, releaseId)
const manifestPath = resolve(releaseRoot, 'release.json')

if (statSafe(releaseRoot)?.isDirectory()) {
  const verified = await verifyRuntimeReleaseManifest(manifestPath, {
    expectedSourceSignature: sourceSignature,
    expectedRepositoryRoot: repositoryRoot,
    expectedToolchainId: toolchain.descriptor.toolchainId,
  })
  process.stdout.write(`${JSON.stringify({
    status: 'REUSED_CANDIDATE',
    releaseId,
    releaseRoot: verified.releaseRoot,
    releaseManifestPath: verified.manifestPath,
    sourceSignature,
    toolchainId: toolchain.descriptor.toolchainId,
    activeReleaseChanged: false,
  })}\n`)
  process.exit(0)
}

mkdirSync(layout.releasesRoot, { recursive: true })
mkdirSync(layout.runtimeBuildTempRoot, { recursive: true })
const staging = resolve(layout.runtimeBuildTempRoot, `${releaseId}.${process.pid}`)
rmSync(staging, { recursive: true, force: true })
mkdirSync(staging, { recursive: true })

const runtimeBundle = await rolldown({
  input: {
    runtime: runtimeOwnerEntry,
    'atp-project-plugin': atpProjectPluginEntry,
  },
  platform: 'node',
  plugins: [aliasPlugin],
})
await runtimeBundle.write({
  dir: staging,
  format: 'es',
  entryFileNames: '[name].mjs',
  chunkFileNames: 'chunks/[name]-[hash].mjs',
})
await runtimeBundle.close()

const gatewayBundleRoot = resolve(staging, 'src')
mkdirSync(gatewayBundleRoot, { recursive: true })
const gatewayBundle = await rolldown({
  input: { gateway: resolve(packageRoot, 'src', 'gateway-release-entry.mjs') },
  platform: 'node',
  plugins: [aliasPlugin],
})
await gatewayBundle.write({
  dir: gatewayBundleRoot,
  format: 'es',
  entryFileNames: '[name].mjs',
  chunkFileNames: 'chunks/[name]-[hash].mjs',
})
await gatewayBundle.close()
writeFileSync(resolve(staging, 'gateway.mjs'), "import './src/gateway.mjs'\n", 'utf8')

const releaseLocalRuntimePointer = resolve(releaseRoot, 'runtime-pointer.json')
writeJson(resolve(staging, 'runtime-pointer.json'), {
  schema: 'et-harness.pure-mcp-active-release.v1',
  releaseManifestPath: resolve(releaseRoot, 'release.json'),
  activatedAt: null,
})
const sourceGatewayConfig = JSON.parse(readFileSync(resolve(packageRoot, 'config', 'gateway.local.json'), 'utf8'))
const gatewayConfig = {
  ...sourceGatewayConfig,
  runtimeReleasePointerPath: releaseLocalRuntimePointer,
  taskSnapshotRoot: layout.taskSnapshotRoot,
}
mkdirSync(resolve(staging, 'config'), { recursive: true })
writeJson(resolve(staging, 'config', 'gateway.local.json'), gatewayConfig)

const deployment = {
  schema: 'et-harness.pure-mcp-runtime-deployment.v1',
  environmentRoot: layout.environmentRoot,
  stateRoot: layout.runtimeStateRoot,
  eventStoreRoot: layout.eventStoreRoot,
  projectBindings: [{
    projectId: 'et-automated-testing-platform',
    projectRoot: repositoryRoot,
    projectManifestPath: resolve(
      repositoryRoot,
      'agent_harness',
      'projects',
      'automated_testing_platform',
      'project.yaml',
    ),
    allowedWorkspaceRoots: [repositoryRoot],
    projectPluginEntryPath: resolve(releaseRoot, 'atp-project-plugin.mjs'),
    projectPluginReadinessService: 'atpContextContributor',
  }],
}
writeJson(resolve(staging, 'deployment.json'), deployment)

const artifacts = Object.fromEntries(
  filesBelow(staging)
    .map(path => [relative(staging, path).replaceAll('\\', '/'), hashFile(path)])
    .sort(([left], [right]) => left.localeCompare(right)),
)
const manifest = {
  schema: 'et-harness.pure-mcp-runtime-release.v2',
  sourceSignature,
  sourceRevision: sourceRevision(),
  sourceDirty: sourceDirty(),
  repositoryRoot,
  deploymentFingerprint,
  nodeVersion: process.version,
  toolchainId: toolchain.descriptor.toolchainId,
  packageLockSha256: toolchain.descriptor.packageLockSha256,
  dependencyVersions: toolchain.dependencyVersions,
  createdAt: new Date().toISOString(),
  artifacts,
}
writeJson(resolve(staging, 'release.json'), manifest)

if (readdirSync(staging).length === 0) throw new Error('Candidate Runtime bundle produced no artifacts')
renameSync(staging, releaseRoot)
const verified = await verifyRuntimeReleaseManifest(manifestPath, {
  expectedSourceSignature: sourceSignature,
  expectedRepositoryRoot: repositoryRoot,
  expectedToolchainId: toolchain.descriptor.toolchainId,
})
process.stdout.write(`${JSON.stringify({
  status: 'BUILT_CANDIDATE',
  releaseId,
  releaseRoot: verified.releaseRoot,
  releaseManifestPath: verified.manifestPath,
  sourceSignature,
  toolchainId: toolchain.descriptor.toolchainId,
  activeReleaseChanged: false,
})}\n`)

function statSafe(path) {
  try {
    return statSync(path)
  } catch {
    return undefined
  }
}
