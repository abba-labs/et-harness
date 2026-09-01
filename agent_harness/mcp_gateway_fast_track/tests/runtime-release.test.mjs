import assert from 'node:assert/strict'
import { after, test } from 'node:test'
import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises'
import { join, resolve } from 'node:path'

import {
  computeRuntimeSourceSignature,
  environmentRoot,
  repositoryRoot,
} from '../scripts/runtime-bundle-inputs.mjs'
import { verifyActiveRuntimeRelease } from '../src/runtime-release.mjs'

const parent = resolve(environmentRoot, 'state', 'pure-mcp-fast-track', 'release-verifier-tests')
await mkdir(parent, { recursive: true })
const testRoot = await mkdtemp(join(parent, 'case-'))
after(async () => rm(testRoot, { recursive: true, force: true }))

const writeJson = (path, value) => writeFile(path, `${JSON.stringify(value)}\n`, 'utf8')

test('active Runtime release matches the current source and artifact hashes', async () => {
  const release = await verifyActiveRuntimeRelease(
    resolve(environmentRoot, 'state', 'pure-mcp-fast-track', 'active-release.json'),
  )
  assert.equal(release.manifest.sourceSignature, computeRuntimeSourceSignature())
  assert.equal(release.manifest.repositoryRoot, repositoryRoot)
})

test('stale Runtime source signature fails closed before activation', async () => {
  const directory = resolve(testRoot, 'stale')
  await mkdir(directory, { recursive: true })
  const manifestPath = resolve(directory, 'release.json')
  const pointerPath = resolve(directory, 'pointer.json')
  await writeJson(manifestPath, {
    schema: 'et-harness.pure-mcp-runtime-release.v1',
    sourceSignature: '0'.repeat(64),
    repositoryRoot,
    nodeVersion: process.version,
    artifacts: {},
  })
  await writeJson(pointerPath, {
    schema: 'et-harness.pure-mcp-active-release.v1',
    releaseManifestPath: manifestPath,
  })
  await assert.rejects(
    verifyActiveRuntimeRelease(pointerPath),
    /Runtime release is stale for the current source/,
  )
})

test('damaged Runtime artifacts fail integrity verification', async () => {
  const directory = resolve(testRoot, 'damaged')
  await mkdir(directory, { recursive: true })
  for (const name of ['runtime.mjs', 'atp-project-plugin.mjs', 'deployment.json']) {
    await writeFile(resolve(directory, name), 'damaged', 'utf8')
  }
  const manifestPath = resolve(directory, 'release.json')
  const pointerPath = resolve(directory, 'pointer.json')
  await writeJson(manifestPath, {
    schema: 'et-harness.pure-mcp-runtime-release.v1',
    sourceSignature: computeRuntimeSourceSignature(),
    repositoryRoot,
    nodeVersion: process.version,
    artifacts: {
      'runtime.mjs': '0'.repeat(64),
      'atp-project-plugin.mjs': '0'.repeat(64),
      'deployment.json': '0'.repeat(64),
    },
  })
  await writeJson(pointerPath, {
    schema: 'et-harness.pure-mcp-active-release.v1',
    releaseManifestPath: manifestPath,
  })
  await assert.rejects(
    verifyActiveRuntimeRelease(pointerPath),
    /Runtime release artifact failed integrity verification/,
  )
})
