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
  assert.match(resolver, /resolve-environment-root\.ps1/i)
  assert.doesNotMatch(resolver, /-Command/i)
})

test('real cmd fixture launches a batch probe before resolver assertions', { skip: process.platform !== 'win32' }, () => {
  const root = mkdtempSync(resolve(tmpdir(), 'et-harness-cmd-fixture-'))
  try {
    writeFileSync(resolve(root, 'fixture-probe.cmd'), '@echo off\r\necho CMD_FIXTURE_OK\r\n', 'utf8')
    const result = spawnSync('cmd.exe', ['/d', '/c', 'fixture-probe.cmd'], cmdOptions(root))
    assertCmdPass(result)
    assert.match(result.stdout, /CMD_FIXTURE_OK/)
  } finally {
    rmSync(root, { recursive: true, force: true })
  }
})

test('real cmd resolver honors explicit ET_HARNESS_NODE', { skip: process.platform !== 'win32' }, () => {
  withResolverFixture({ writeConfig: false }, fixture => {
    const explicitNode = resolve(fixture.root, 'explicit node', 'node.exe')
    mkdirSync(dirname(explicitNode), { recursive: true })
    writeFileSync(explicitNode, '', 'utf8')
    const result = runResolver(fixture, { ET_HARNESS_NODE: explicitNode })
    assertCmdPass(result)
    assertResolvedNode(result, explicitNode)
  })
})

test('real cmd resolver honors explicit ET_HARNESS_ENV_ROOT', { skip: process.platform !== 'win32' }, () => {
  withResolverFixture({ writeConfig: false, machineName: 'explicit environment' }, fixture => {
    const result = runResolver(fixture, { ET_HARNESS_ENV_ROOT: fixture.machineRoot })
    assertCmdPass(result)
    assertResolvedNode(result, fixture.nodeExecutable)
  })
})

test('real cmd resolver uses the legacy absolute pointer fallback', { skip: process.platform !== 'win32' }, () => {
  withResolverFixture({}, fixture => {
    const result = runResolver(fixture)
    assertCmdPass(result)
    assertResolvedNode(result, fixture.nodeExecutable)
    assert.match(result.stdout, new RegExp(`ENV_ROOT=${escapeRegExp(fixture.machineRoot)}`, 'i'))
  })
})

test('real cmd resolver supports checkout paths containing spaces', { skip: process.platform !== 'win32' }, () => {
  withResolverFixture({ checkoutPrefix: 'et harness checkout with spaces ' }, fixture => {
    const result = runResolver(fixture)
    assertCmdPass(result)
    assertResolvedNode(result, fixture.nodeExecutable)
  })
})

test('real cmd resolver supports environment paths containing spaces', { skip: process.platform !== 'win32' }, () => {
  withResolverFixture({ machineName: 'machine environment with spaces' }, fixture => {
    const result = runResolver(fixture)
    assertCmdPass(result)
    assertResolvedNode(result, fixture.nodeExecutable)
  })
})

test('real cmd resolver gives different worktrees the same machine Node', { skip: process.platform !== 'win32' }, () => {
  const sharedRoot = mkdtempSync(resolve(tmpdir(), 'et-harness-shared-machine-'))
  const machineRoot = resolve(sharedRoot, 'machine environment')
  const first = createResolverFixture({ checkoutPrefix: 'worktree-one-', machineRoot })
  const second = createResolverFixture({ checkoutPrefix: 'worktree-two-', machineRoot })
  try {
    const firstResult = runResolver(first)
    const secondResult = runResolver(second)
    assertCmdPass(firstResult)
    assertCmdPass(secondResult)
    assertResolvedNode(firstResult, first.nodeExecutable)
    assertResolvedNode(secondResult, first.nodeExecutable)
  } finally {
    rmSync(first.root, { recursive: true, force: true })
    rmSync(second.root, { recursive: true, force: true })
    rmSync(sharedRoot, { recursive: true, force: true })
  }
})

test('real cmd resolver fails closed when config is missing', { skip: process.platform !== 'win32' }, () => {
  withResolverFixture({ writeConfig: false }, fixture => assertCmdFail(runResolver(fixture)))
})

test('real cmd resolver fails closed when pointer is missing', { skip: process.platform !== 'win32' }, () => {
  withResolverFixture({ createPointer: false }, fixture => assertCmdFail(runResolver(fixture)))
})

test('real cmd resolver fails closed when pointer is relative', { skip: process.platform !== 'win32' }, () => {
  withResolverFixture({ pointerValue: 'relative\\active-release.json' }, fixture => {
    assertCmdFail(runResolver(fixture))
  })
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

function createResolverFixture(options = {}) {
  const root = mkdtempSync(resolve(tmpdir(), options.checkoutPrefix ?? 'et-harness-resolver-'))
  const fixtureScripts = resolve(root, 'scripts')
  const fixtureConfig = resolve(root, 'config')
  const machineRoot = options.machineRoot ?? resolve(root, options.machineName ?? 'machine-env')
  const nodeExecutable = resolve(machineRoot, 'runtimes', 'node-v22.23.2-win-x64', 'node.exe')
  const activePointer = resolve(machineRoot, 'state', 'pure-mcp-fast-track', 'active-release.json')
  mkdirSync(fixtureScripts, { recursive: true })
  mkdirSync(fixtureConfig, { recursive: true })
  mkdirSync(dirname(nodeExecutable), { recursive: true })
  writeFileSync(nodeExecutable, '', 'utf8')
  copyFileSync(resolve(scriptsRoot, 'resolve-node.cmd'), resolve(fixtureScripts, 'resolve-node.cmd'))
  copyFileSync(
    resolve(scriptsRoot, 'resolve-environment-root.ps1'),
    resolve(fixtureScripts, 'resolve-environment-root.ps1'),
  )
  writeFileSync(
    resolve(fixtureScripts, 'resolver-probe.cmd'),
    '@echo off\r\ncall "%~dp0resolve-node.cmd"\r\nif errorlevel 1 exit /b %ERRORLEVEL%\r\necho NODE_EXE=%NODE_EXE%\r\necho ENV_ROOT=%ET_HARNESS_ENV_ROOT%\r\n',
    'utf8',
  )
  if (options.createPointer !== false) {
    mkdirSync(dirname(activePointer), { recursive: true })
    writeFileSync(activePointer, '{}\n', 'utf8')
  }
  if (options.writeConfig !== false) {
    writeFileSync(
      resolve(fixtureConfig, 'gateway.local.json'),
      `${JSON.stringify({ runtimeReleasePointerPath: options.pointerValue ?? activePointer }, null, 2)}\n`,
      'utf8',
    )
  }
  return { root, fixtureScripts, machineRoot, nodeExecutable }
}

function withResolverFixture(options, assertion) {
  const fixture = createResolverFixture(options)
  try {
    assertion(fixture)
  } finally {
    rmSync(fixture.root, { recursive: true, force: true })
  }
}

function runResolver(fixture, overrides = {}) {
  const env = { ...process.env }
  delete env.ET_HARNESS_NODE
  delete env.ET_HARNESS_ENV_ROOT
  Object.assign(env, overrides)
  return spawnSync('cmd.exe', ['/d', '/c', 'resolver-probe.cmd'], {
    ...cmdOptions(fixture.fixtureScripts),
    env,
  })
}

function cmdOptions(cwd) {
  return { cwd, encoding: 'utf8', windowsHide: true }
}

function assertCmdPass(result) {
  assert.equal(result.status, 0, commandOutput(result))
}

function assertCmdFail(result) {
  assert.notEqual(result.status, 0, commandOutput(result))
}

function assertResolvedNode(result, expected) {
  assert.match(result.stdout, new RegExp(`NODE_EXE=${escapeRegExp(expected)}`, 'i'))
}

function commandOutput(result) {
  return [result.stderr, result.stdout].filter(value => value?.trim()).join('\n')
}
