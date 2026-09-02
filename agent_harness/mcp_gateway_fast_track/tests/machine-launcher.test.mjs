import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import {
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, resolve } from 'node:path'
import { test } from 'node:test'

import {
  environmentRootFromLauncher,
  findForbiddenLauncher,
  verifyRuntimeReleaseManifest,
  verifyRuntimeReleasePointer,
} from '../scripts/machine-launcher.mjs'

const POINTER_SCHEMA = 'et-harness.pure-mcp-active-release.v1'
const hash = path => createHash('sha256').update(readFileSync(path)).digest('hex')

test('Machine Launcher owns Environment Root from its installed physical path', () => {
  assert.equal(
    environmentRootFromLauncher('D:\\machine env\\bin\\machine-launcher.mjs'),
    'D:\\machine env',
  )
})

test('Machine Launcher accepts only a self-bound v2 active release', () => {
  withReleaseFixture(fixture => {
    const release = verifyRuntimeReleasePointer(
      fixture.layout,
      fixture.activePointer,
      { requireV2: true },
    )
    assert.equal(release.releaseId, fixture.releaseId)
    assert.equal(release.gatewayEntry, resolve(fixture.releaseRoot, 'gateway.mjs'))
  })
})

test('Machine Launcher rejects a tampered active artifact', () => {
  withReleaseFixture(fixture => {
    writeFileSync(resolve(fixture.releaseRoot, 'gateway.mjs'), 'tampered\n', 'utf8')
    assert.throws(
      () => verifyRuntimeReleasePointer(fixture.layout, fixture.activePointer, { requireV2: true }),
      /artifact failed integrity verification/,
    )
  })
})

test('Machine Launcher rejects a release pointer outside Environment Root', () => {
  withReleaseFixture(fixture => {
    const escapedRoot = mkdtempSync(resolve(tmpdir(), 'et-harness-escaped-release-'))
    try {
      const escapedManifest = resolve(escapedRoot, 'release.json')
      writeFileSync(escapedManifest, JSON.stringify({
        schema: 'et-harness.pure-mcp-runtime-release.v2',
        nodeVersion: process.version,
        artifacts: {},
      }), 'utf8')
      writeFileSync(fixture.activePointer, JSON.stringify({
        schema: POINTER_SCHEMA,
        releaseManifestPath: escapedManifest,
      }), 'utf8')
      assert.throws(
        () => verifyRuntimeReleasePointer(fixture.layout, fixture.activePointer, { requireV2: true }),
        /escapes the machine Environment Root/,
      )
    } finally {
      rmSync(escapedRoot, { recursive: true, force: true })
    }
  })
})

test('Machine Launcher rejects non-v2 normal start candidates', () => {
  withReleaseFixture(fixture => {
    const manifest = JSON.parse(readFileSync(fixture.manifestPath, 'utf8'))
    manifest.schema = 'et-harness.pure-mcp-runtime-release.v1'
    writeFileSync(fixture.manifestPath, JSON.stringify(manifest), 'utf8')
    assert.throws(
      () => verifyRuntimeReleaseManifest(fixture.layout, fixture.manifestPath, { requireV2: true }),
      /requires a v2 release-bundled Runtime/,
    )
  })
})

test('Machine Launcher retains the external-launcher ancestry boundary', () => {
  assert.equal(findForbiddenLauncher([
    { name: 'cmd.exe', commandLine: 'cmd.exe /c et-harness.cmd start' },
    { name: 'explorer.exe', commandLine: 'C:\\Windows\\explorer.exe' },
  ]), undefined)
  assert.equal(findForbiddenLauncher([
    { name: 'node.exe', commandLine: 'node machine-launcher.mjs start' },
    { name: 'codex.exe', commandLine: 'Codex.exe' },
  ])?.name, 'codex.exe')
  assert.equal(findForbiddenLauncher([
    { name: 'node.exe', commandLine: 'C:\\Users\\admin\\.codex\\plugins\\launcher.js' },
  ])?.name, 'node.exe')
})

function withReleaseFixture(assertion) {
  const environmentRoot = mkdtempSync(resolve(tmpdir(), 'et-harness-machine-launcher-'))
  const releaseId = 'fixture-v2-release'
  const releaseRoot = resolve(
    environmentRoot,
    'state',
    'pure-mcp-fast-track',
    'releases',
    releaseId,
  )
  const manifestPath = resolve(releaseRoot, 'release.json')
  const activePointer = resolve(
    environmentRoot,
    'state',
    'pure-mcp-fast-track',
    'active-release.json',
  )
  const layout = { environmentRoot }
  const artifacts = {}
  try {
    for (const [name, content] of [
      ['runtime.mjs', 'runtime\n'],
      ['atp-project-plugin.mjs', 'plugin\n'],
      ['deployment.json', '{}\n'],
      ['gateway.mjs', 'gateway\n'],
    ]) {
      const path = resolve(releaseRoot, name)
      mkdirSync(dirname(path), { recursive: true })
      writeFileSync(path, content, 'utf8')
      artifacts[name] = hash(path)
    }
    const runtimePointer = resolve(releaseRoot, 'runtime-pointer.json')
    writeFileSync(runtimePointer, JSON.stringify({
      schema: POINTER_SCHEMA,
      releaseManifestPath: manifestPath,
      activatedAt: null,
    }), 'utf8')
    artifacts['runtime-pointer.json'] = hash(runtimePointer)
    const gatewayConfig = resolve(releaseRoot, 'config', 'gateway.local.json')
    mkdirSync(dirname(gatewayConfig), { recursive: true })
    writeFileSync(gatewayConfig, JSON.stringify({
      runtimeReleasePointerPath: runtimePointer,
    }), 'utf8')
    artifacts['config/gateway.local.json'] = hash(gatewayConfig)
    writeFileSync(manifestPath, JSON.stringify({
      schema: 'et-harness.pure-mcp-runtime-release.v2',
      nodeVersion: process.version,
      artifacts,
    }), 'utf8')
    mkdirSync(dirname(activePointer), { recursive: true })
    writeFileSync(activePointer, JSON.stringify({
      schema: POINTER_SCHEMA,
      releaseManifestPath: manifestPath,
    }), 'utf8')
    assertion({
      environmentRoot,
      releaseId,
      releaseRoot,
      manifestPath,
      activePointer,
      layout,
    })
  } finally {
    rmSync(environmentRoot, { recursive: true, force: true })
  }
}
