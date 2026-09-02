import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import {
  copyFileSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, resolve } from 'node:path'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

const testRoot = dirname(fileURLToPath(import.meta.url))
const packageRoot = resolve(testRoot, '..')
const scriptsRoot = resolve(packageRoot, 'scripts')
const srcRoot = resolve(packageRoot, 'src')
const read = path => readFileSync(path, 'utf8')

const filesBelow = (directory, suffix) => {
  const result = []
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const path = resolve(directory, entry.name)
    if (entry.isDirectory()) result.push(...filesBelow(path, suffix))
    else if (entry.isFile() && entry.name.endsWith(suffix)) result.push(path)
  }
  return result
}

const resolverEntries = [
  'activate-runtime.cmd',
  'build-runtime.cmd',
  'freeze-runtime.cmd',
  'prepare-toolchain.cmd',
  'rollback-runtime.cmd',
  'smoke.cmd',
  'start-gateway.cmd',
  'stop-gateway.cmd',
  'verify-candidate-runtime.cmd',
  'verify-environment.cmd',
]

test('command entries resolve the machine Node through one shared owner', () => {
  for (const name of resolverEntries) {
    const content = read(resolve(scriptsRoot, name))
    assert.match(content, /call "%~dp0resolve-node\.cmd"/i, `${name} must use resolve-node.cmd`)
    assert.doesNotMatch(
      content,
      /\.\.\\\.\.\\\.\.\\.*runtimes\\node-v22\.23\.2/i,
      `${name} must not infer the machine runtime by walking out of the checkout`,
    )
  }

  assert.match(read(resolve(scriptsRoot, 'prepare-environment.cmd')), /prepare-toolchain\.cmd/i)
  const refresh = read(resolve(scriptsRoot, 'refresh-gateway.cmd'))
  assert.match(refresh, /freeze-runtime\.cmd/i)
  assert.match(refresh, /stop-gateway\.cmd/i)
  assert.match(refresh, /start-gateway\.cmd/i)
  assert.match(read(resolve(packageRoot, 'start-et-harness-gateway.cmd')), /scripts\\start-gateway\.cmd/i)
})

test('legacy Node resolver avoids cmd-sensitive PowerShell pipeline escaping', () => {
  const resolver = read(resolve(scriptsRoot, 'resolve-node.cmd'))
  assert.match(resolver, /ConvertFrom-Json -InputObject/i)
  assert.doesNotMatch(resolver, /\^\|/)
  assert.doesNotMatch(resolver, /\|\s*ConvertFrom-Json/i)
})

test('legacy Node resolver executes through real cmd.exe', { skip: process.platform !== 'win32' }, () => {
  const root = mkdtempSync(resolve(tmpdir(), 'et-harness-resolver-'))
  try {
    const fixtureScripts = resolve(root, 'scripts')
    const fixtureConfig = resolve(root, 'config')
    const machineRoot = resolve(root, 'machine-env')
    const nodeExecutable = resolve(machineRoot, 'runtimes', 'node-v22.23.2-win-x64', 'node.exe')
    const activePointer = resolve(machineRoot, 'state', 'pure-mcp-fast-track', 'active-release.json')
    mkdirSync(fixtureScripts, { recursive: true })
    mkdirSync(fixtureConfig, { recursive: true })
    mkdirSync(dirname(nodeExecutable), { recursive: true })
    mkdirSync(dirname(activePointer), { recursive: true })
    copyFileSync(resolve(scriptsRoot, 'resolve-node.cmd'), resolve(fixtureScripts, 'resolve-node.cmd'))
    writeFileSync(nodeExecutable, '', 'utf8')
    writeFileSync(
      resolve(fixtureConfig, 'gateway.local.json'),
      `${JSON.stringify({ runtimeReleasePointerPath: activePointer }, null, 2)}\n`,
      'utf8',
    )

    const env = { ...process.env }
    delete env.ET_HARNESS_NODE
    delete env.ET_HARNESS_ENV_ROOT
    const command = `call "${resolve(fixtureScripts, 'resolve-node.cmd')}" && echo NODE_EXE=%NODE_EXE%`
    const result = spawnSync('cmd.exe', ['/d', '/c', command], {
      encoding: 'utf8',
      env,
      windowsHide: true,
    })
    assert.equal(
      result.status,
      0,
      [result.stderr, result.stdout].filter(value => value?.trim()).join('\n'),
    )
    assert.match(result.stdout, new RegExp(`NODE_EXE=${escapeRegExp(nodeExecutable)}`, 'i'))
  } finally {
    rmSync(root, { recursive: true, force: true })
  }
})

test('direct MCP smoke loads npm dependencies from the shared Toolchain', () => {
  const smoke = read(resolve(scriptsRoot, 'smoke.cmd'))
  assert.match(smoke, /--import "%~dp0register-toolchain-loader\.mjs"/i)
  assert.match(smoke, /smoke\.mjs/i)
})

test('all Gateway and infrastructure mjs contain no checkout-local environment owner', () => {
  const mjsFiles = [
    ...filesBelow(scriptsRoot, '.mjs'),
    ...filesBelow(srcRoot, '.mjs'),
  ]
  for (const file of mjsFiles) {
    const content = read(file)
    assert.doesNotMatch(
      content,
      /environmentRoot\s*=\s*resolve\(repositoryRoot\s*,\s*['"]\.\.['"]\s*,\s*['"]\.\.['"]\s*\)/,
      `${file} must not derive the machine environment from repositoryRoot`,
    )
    assert.doesNotMatch(
      content,
      /resolve\(packageRoot\s*,\s*['"]node_modules['"]\)/,
      `${file} must not own checkout-local npm dependencies`,
    )
    assert.doesNotMatch(
      content,
      /requireFromPackage\.resolve\(['"]@deepseek-ai\/cordis['"]\)/,
      `${file} must resolve Cordis from the shared Toolchain, not the checkout`,
    )
  }
})

test('release switching is explicit and guarded from a live Gateway', () => {
  const activate = read(resolve(scriptsRoot, 'activate-runtime.mjs'))
  const rollback = read(resolve(scriptsRoot, 'rollback-runtime.mjs'))
  assert.match(activate, /assertGatewayStoppedForReleaseSwitch\(\)/)
  assert.match(rollback, /assertGatewayStoppedForReleaseSwitch\(\)/)
  assert.doesNotMatch(read(resolve(scriptsRoot, 'build-runtime.mjs')), /atomicWriteJson\(layout\.activeReleasePointer/)
  assert.doesNotMatch(read(resolve(scriptsRoot, 'verify-candidate-runtime.mjs')), /atomicWriteJson\(layout\.activeReleasePointer/)
})

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
