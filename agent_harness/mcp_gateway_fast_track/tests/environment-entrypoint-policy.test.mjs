import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'
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
