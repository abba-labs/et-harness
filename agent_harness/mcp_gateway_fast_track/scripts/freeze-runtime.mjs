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
import { dirname, relative, resolve } from 'node:path'

import {
  atpProjectPluginEntry,
  computeRuntimeSourceSignature,
  environmentRoot,
  localPackageAliases,
  packageRoot,
  repositoryRoot,
  runtimeOwnerEntry,
} from './runtime-bundle-inputs.mjs'
import { verifyActiveRuntimeRelease } from '../src/runtime-release.mjs'

const EXPECTED_NODE = 'v22.23.2'
const pointerPath = resolve(environmentRoot, 'state', 'pure-mcp-fast-track', 'active-release.json')
const releasesRoot = resolve(environmentRoot, 'state', 'pure-mcp-fast-track', 'releases')
const runtimeStateRoot = resolve(environmentRoot, 'state', 'pure-mcp-fast-track', 'runtime-state')
const eventStoreRoot = resolve(runtimeStateRoot, 'execution-events')
const temporaryRoot = resolve(environmentRoot, 'temp', 'pure-mcp-runtime-freeze')

const hashFile = path => createHash('sha256').update(readFileSync(path)).digest('hex')
const writeJson = (path, value) => writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`, 'utf8')

const verifyPinnedDependencies = () => {
  const packageManifest = JSON.parse(readFileSync(resolve(packageRoot, 'package.json'), 'utf8'))
  const pinned = { ...packageManifest.dependencies, ...packageManifest.devDependencies }
  const versions = {}
  for (const [name, expected] of Object.entries(pinned)) {
    const installedPath = resolve(packageRoot, 'node_modules', ...name.split('/'), 'package.json')
    let installed
    try {
      installed = JSON.parse(readFileSync(installedPath, 'utf8'))
    } catch {
      throw new Error(`Pinned dependency is unavailable: ${name}; run scripts\\prepare-environment.cmd once`)
    }
    if (installed.version !== expected) {
      throw new Error(
        `Pinned dependency mismatch for ${name}: expected ${expected}, received ${installed.version}; run scripts\\prepare-environment.cmd`,
      )
    }
    versions[name] = installed.version
  }
  return versions
}

const filesBelow = (directory) => {
  const files = []
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const path = resolve(directory, entry.name)
    if (entry.isDirectory()) files.push(...filesBelow(path))
    else if (entry.isFile()) files.push(path)
  }
  return files
}

const atomicWriteJson = (path, value) => {
  mkdirSync(dirname(path), { recursive: true })
  const temporary = `${path}.${process.pid}.tmp`
  writeJson(temporary, value)
  renameSync(temporary, path)
}

const sourceRevision = () => execFileSync(
  'git.exe',
  ['rev-parse', 'HEAD'],
  { cwd: repositoryRoot, encoding: 'utf8', windowsHide: true },
).trim()

const sourceDirty = () => Boolean(execFileSync(
  'git.exe',
  ['status', '--short', '--', 'agent_harness/mcp_gateway_fast_track', 'agent_harness/governance_core',
    'agent_harness/project_contract', 'agent_harness/public_plugins',
    'agent_harness/projects/automated_testing_platform'],
  { cwd: repositoryRoot, encoding: 'utf8', windowsHide: true },
).trim())

if (process.version !== EXPECTED_NODE) {
  throw new Error(`Pure MCP Runtime freeze requires ${EXPECTED_NODE}; current Node is ${process.version}`)
}
const dependencyVersions = verifyPinnedDependencies()

if (process.argv.includes('--verify-only')) {
  const release = await verifyActiveRuntimeRelease(pointerPath)
  process.stdout.write(`${JSON.stringify({ status: 'VERIFIED', sourceSignature: release.manifest.sourceSignature })}\n`)
  process.exit(0)
}

const sourceSignature = computeRuntimeSourceSignature()
const force = process.argv.includes('--force')
if (!force) {
  try {
    const current = await verifyActiveRuntimeRelease(pointerPath)
    process.stdout.write(`${JSON.stringify({ status: 'REUSED', sourceSignature: current.manifest.sourceSignature })}\n`)
    process.exit(0)
  } catch {
    // A missing or stale pointer is repaired by creating one deterministic release below.
  }
}

let rolldown
try {
  ;({ rolldown } = await import('rolldown'))
} catch {
  throw new Error('Pinned build dependencies are unavailable; run scripts\\prepare-environment.cmd once')
}

const revision = sourceRevision()
const releaseId = createHash('sha256')
  .update(`${repositoryRoot.toLowerCase()}\0${sourceSignature}\0${force ? revision : 'content'}`)
  .digest('hex')
  .slice(0, 20)
const releaseRoot = resolve(releasesRoot, releaseId)
const staging = resolve(temporaryRoot, `${releaseId}.${process.pid}`)
rmSync(staging, { recursive: true, force: true })
mkdirSync(staging, { recursive: true })

const aliasPlugin = {
  name: 'et-harness-local-package-aliases',
  resolveId(source) {
    return localPackageAliases[source]
  },
}

const bundle = await rolldown({
  input: {
    runtime: runtimeOwnerEntry,
    'atp-project-plugin': atpProjectPluginEntry,
  },
  platform: 'node',
  plugins: [aliasPlugin],
})
await bundle.write({
  dir: staging,
  format: 'es',
  entryFileNames: '[name].mjs',
  chunkFileNames: 'chunks/[name]-[hash].mjs',
})
await bundle.close()

const deployment = {
  schema: 'et-harness.pure-mcp-runtime-deployment.v1',
  environmentRoot,
  stateRoot: runtimeStateRoot,
  eventStoreRoot,
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
  schema: 'et-harness.pure-mcp-runtime-release.v1',
  sourceSignature,
  sourceRevision: revision,
  sourceDirty: sourceDirty(),
  repositoryRoot,
  nodeVersion: process.version,
  packageLockSha256: hashFile(resolve(packageRoot, 'package-lock.json')),
  dependencyVersions,
  createdAt: new Date().toISOString(),
  artifacts,
}
writeJson(resolve(staging, 'release.json'), manifest)

mkdirSync(releasesRoot, { recursive: true })
if (statSync(staging).isDirectory()) {
  if (readdirSync(staging).length === 0) throw new Error('Runtime bundle produced no artifacts')
}
if (readdirSync(releasesRoot).includes(releaseId)) rmSync(staging, { recursive: true, force: true })
else renameSync(staging, releaseRoot)

atomicWriteJson(pointerPath, {
  schema: 'et-harness.pure-mcp-active-release.v1',
  releaseManifestPath: resolve(releaseRoot, 'release.json'),
  activatedAt: new Date().toISOString(),
})
const verified = await verifyActiveRuntimeRelease(pointerPath)
process.stdout.write(`${JSON.stringify({
  status: 'FROZEN',
  sourceSignature: verified.manifest.sourceSignature,
  sourceRevision: verified.manifest.sourceRevision,
  releaseRoot: verified.releaseRoot,
})}\n`)
