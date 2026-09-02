import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { after, test } from 'node:test'
import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises'
import { join, resolve } from 'node:path'

import { layout, repositoryRoot } from '../scripts/environment-layout.mjs'
import { computeRuntimeSourceSignature } from '../scripts/runtime-bundle-inputs.mjs'
import {
  verifyActiveRuntimeRelease,
  verifyRuntimeReleaseManifest,
} from '../src/runtime-release.mjs'

const parent = resolve(layout.tempRoot, 'release-verifier-tests')
await mkdir(parent, { recursive: true })
const testRoot = await mkdtemp(join(parent, 'case-'))
after(async () => rm(testRoot, { recursive: true, force: true }))

const writeJson = (path, value) => writeFile(path, `${JSON.stringify(value)}\n`, 'utf8')
const sha256 = value => createHash('sha256').update(value).digest('hex')

const writeValidV1 = async (directory, overrides = {}) => {
  await mkdir(directory, { recursive: true })
  const artifacts = {}
  for (const [name, content] of [
    ['runtime.mjs', 'runtime'],
    ['atp-project-plugin.mjs', 'plugin'],
    ['deployment.json', '{}\n'],
  ]) {
    await writeFile(resolve(directory, name), content, 'utf8')
    artifacts[name] = sha256(content)
  }
  const manifestPath = resolve(directory, 'release.json')
  await writeJson(manifestPath, {
    schema: 'et-harness.pure-mcp-runtime-release.v1',
    sourceSignature: computeRuntimeSourceSignature(),
    repositoryRoot,
    nodeVersion: process.version,
    artifacts,
    ...overrides,
  })
  return manifestPath
}

const writeV2 = async (directory, options = {}) => {
  await mkdir(resolve(directory, 'config'), { recursive: true })
  const manifestPath = resolve(directory, 'release.json')
  const runtimePointerPath = resolve(directory, 'runtime-pointer.json')
  const pointerTarget = options.pointerTarget ?? manifestPath
  const gatewayPointer = options.gatewayPointer ?? runtimePointerPath
  const contents = new Map([
    ['runtime.mjs', 'runtime-v2'],
    ['atp-project-plugin.mjs', 'plugin-v2'],
    ['deployment.json', '{}\n'],
    ['gateway.mjs', "import './src/gateway.mjs'\n"],
    ['runtime-pointer.json', `${JSON.stringify({
      schema: 'et-harness.pure-mcp-active-release.v1',
      releaseManifestPath: pointerTarget,
    })}\n`],
    ['config/gateway.local.json', `${JSON.stringify({
      runtimeReleasePointerPath: gatewayPointer,
    })}\n`],
  ])
  const artifacts = {}
  for (const [name, content] of contents) {
    await writeFile(resolve(directory, name), content, 'utf8')
    artifacts[name] = sha256(content)
  }
  await writeJson(manifestPath, {
    schema: 'et-harness.pure-mcp-runtime-release.v2',
    sourceSignature: computeRuntimeSourceSignature(),
    repositoryRoot,
    nodeVersion: process.version,
    toolchainId: 'tc-fixture',
    artifacts,
  })
  return manifestPath
}

const pointerFor = async (directory, manifestPath) => {
  const pointerPath = resolve(directory, 'pointer.json')
  await writeJson(pointerPath, {
    schema: 'et-harness.pure-mcp-active-release.v1',
    releaseManifestPath: manifestPath,
  })
  return pointerPath
}

test('an active pointer verifies release integrity without requiring current-checkout identity', async () => {
  const directory = resolve(testRoot, 'active-independent')
  const manifestPath = await writeValidV1(directory, {
    sourceSignature: '1'.repeat(64),
    repositoryRoot: resolve(repositoryRoot, '..', 'different-worktree'),
  })
  const pointerPath = await pointerFor(directory, manifestPath)
  const release = await verifyActiveRuntimeRelease(pointerPath)
  assert.equal(release.manifest.sourceSignature, '1'.repeat(64))
})

test('candidate identity checks are explicit and reject a stale source signature', async () => {
  const manifestPath = await writeValidV1(resolve(testRoot, 'stale'), {
    sourceSignature: '0'.repeat(64),
  })
  await assert.rejects(
    verifyRuntimeReleaseManifest(manifestPath, {
      expectedSourceSignature: computeRuntimeSourceSignature(),
      expectedRepositoryRoot: repositoryRoot,
    }),
    /Runtime release source signature mismatch/,
  )
})

test('valid legacy release can be verified independently of checkout-local dependencies', async () => {
  const manifestPath = await writeValidV1(resolve(testRoot, 'valid'))
  const release = await verifyRuntimeReleaseManifest(manifestPath, {
    expectedSourceSignature: computeRuntimeSourceSignature(),
    expectedRepositoryRoot: repositoryRoot,
  })
  assert.equal(release.manifestPath, manifestPath)
})

test('v2 bundled Gateway is mechanically bound to its own immutable Runtime release', async () => {
  const directory = resolve(testRoot, 'v2-self-bound')
  const manifestPath = await writeV2(directory)
  const release = await verifyRuntimeReleaseManifest(manifestPath)
  assert.equal(release.runtimePointerPath, resolve(directory, 'runtime-pointer.json'))
  assert.equal(release.gatewayConfigPath, resolve(directory, 'config', 'gateway.local.json'))
})

test('v2 rejects a release-local Runtime pointer that targets another release', async () => {
  const directory = resolve(testRoot, 'v2-wrong-runtime')
  const manifestPath = await writeV2(directory, {
    pointerTarget: resolve(testRoot, 'other-release', 'release.json'),
  })
  await assert.rejects(
    verifyRuntimeReleaseManifest(manifestPath),
    /Bundled Gateway Runtime pointer does not bind to its own release manifest/,
  )
})

test('v2 rejects Gateway configuration that bypasses its release-local Runtime pointer', async () => {
  const directory = resolve(testRoot, 'v2-wrong-gateway-config')
  const manifestPath = await writeV2(directory, {
    gatewayPointer: layout.activeReleasePointer,
  })
  await assert.rejects(
    verifyRuntimeReleaseManifest(manifestPath),
    /Bundled Gateway configuration does not use its release-local Runtime pointer/,
  )
})

test('damaged Runtime artifacts fail integrity verification', async () => {
  const directory = resolve(testRoot, 'damaged')
  const manifestPath = await writeValidV1(directory)
  await writeFile(resolve(directory, 'runtime.mjs'), 'tampered', 'utf8')
  await assert.rejects(
    verifyRuntimeReleaseManifest(manifestPath),
    /Runtime release artifact failed integrity verification: runtime.mjs/,
  )
})
