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

const parent = resolve(layout.stateRoot, 'release-verifier-tests')
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

test('active Runtime release verifies its own integrity without requiring the current checkout source', async () => {
  const release = await verifyActiveRuntimeRelease(layout.activeReleasePointer)
  assert.equal(typeof release.manifest.sourceSignature, 'string')
  assert.equal(typeof release.manifest.repositoryRoot, 'string')
  assert.equal(typeof release.manifest.artifacts?.['runtime.mjs'], 'string')
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

test('damaged Runtime artifacts fail integrity verification', async () => {
  const directory = resolve(testRoot, 'damaged')
  const manifestPath = await writeValidV1(directory)
  await writeFile(resolve(directory, 'runtime.mjs'), 'tampered', 'utf8')
  await assert.rejects(
    verifyRuntimeReleaseManifest(manifestPath),
    /Runtime release artifact failed integrity verification: runtime.mjs/,
  )
})
