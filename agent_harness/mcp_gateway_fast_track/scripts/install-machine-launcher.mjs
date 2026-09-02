import { createHash, randomUUID } from 'node:crypto'
import { execFileSync, spawnSync } from 'node:child_process'
import {
  existsSync,
  mkdirSync,
  readFileSync,
  renameSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import { resolve } from 'node:path'

import { EXPECTED_NODE_VERSION, layout, packageRoot } from './environment-layout.mjs'

const MANIFEST_SCHEMA = 'et-harness.machine-launcher.v0.1'
const LAUNCHER_VERSION = '0.1.0'
const repositoryRoot = resolve(packageRoot, '..', '..')
const launcherSource = resolve(packageRoot, 'scripts', 'machine-launcher.mjs')
const commandSource = resolve(packageRoot, 'scripts', 'et-harness.cmd')
const canonicalBytes = path => Buffer.from(
  readFileSync(path, 'utf8').replace(/\r\n?/g, '\n'),
  'utf8',
)
const hash = bytes => createHash('sha256').update(bytes).digest('hex')
const git = args => execFileSync(
  'git.exe',
  args,
  { cwd: repositoryRoot, encoding: 'utf8', windowsHide: true },
).trim()

if (process.version !== EXPECTED_NODE_VERSION) {
  throw new Error(`Machine Launcher installation requires ${EXPECTED_NODE_VERSION}`)
}
if (git(['status', '--short', '--', 'agent_harness/mcp_gateway_fast_track'])) {
  throw new Error('Machine Launcher installation requires a clean committed MCP Gateway source')
}

const productSha = git(['rev-parse', 'HEAD'])
const launcherBytes = canonicalBytes(launcherSource)
const commandBytes = canonicalBytes(commandSource)
const launcherSha256 = hash(launcherBytes)
const commandSha256 = hash(commandBytes)
const binRoot = resolve(layout.environmentRoot, 'bin')
const installedLauncher = resolve(binRoot, 'machine-launcher.mjs')
const installedCommand = resolve(binRoot, 'et-harness.cmd')
const installedManifest = resolve(binRoot, 'machine-launcher.json')

if (existsSync(installedLauncher) && existsSync(installedCommand) && existsSync(installedManifest)) {
  const current = JSON.parse(readFileSync(installedManifest, 'utf8'))
  if (current.schema === MANIFEST_SCHEMA
      && current.launcherVersion === LAUNCHER_VERSION
      && current.installedFromProductSha === productSha
      && current.environmentRoot === layout.environmentRoot
      && current.expectedNodeVersion === EXPECTED_NODE_VERSION
      && current.launcherSha256 === launcherSha256
      && current.commandSha256 === commandSha256
      && hash(readFileSync(installedLauncher)) === launcherSha256
      && hash(readFileSync(installedCommand)) === commandSha256) {
    process.stdout.write(`${JSON.stringify({
      status: 'REUSED_UNCHANGED',
      launcherVersion: LAUNCHER_VERSION,
      installedFromProductSha: productSha,
      launcherSha256,
      environmentRoot: layout.environmentRoot,
      command: installedCommand,
    })}\n`)
    process.exit(0)
  }
}

const staging = resolve(layout.environmentRoot, `bin.staging.${process.pid}.${randomUUID()}`)
rmSync(staging, { recursive: true, force: true })
mkdirSync(staging, { recursive: true })
const manifest = {
  schema: MANIFEST_SCHEMA,
  launcherVersion: LAUNCHER_VERSION,
  installedFromProductSha: productSha,
  environmentRoot: layout.environmentRoot,
  expectedNodeVersion: EXPECTED_NODE_VERSION,
  launcherSha256,
  commandSha256,
  installedAt: new Date().toISOString(),
}
writeFileSync(resolve(staging, 'machine-launcher.mjs'), launcherBytes)
writeFileSync(resolve(staging, 'et-harness.cmd'), commandBytes)
writeFileSync(
  resolve(staging, 'machine-launcher.json'),
  `${JSON.stringify(manifest, null, 2)}\n`,
  'utf8',
)
const syntax = spawnSync(
  layout.nodeExecutable,
  ['--check', resolve(staging, 'machine-launcher.mjs')],
  { encoding: 'utf8', windowsHide: true },
)
if (syntax.status !== 0) {
  rmSync(staging, { recursive: true, force: true })
  throw new Error(`Machine Launcher syntax verification failed: ${syntax.stderr}`)
}

mkdirSync(binRoot, { recursive: true })
for (const name of ['machine-launcher.mjs', 'et-harness.cmd', 'machine-launcher.json']) {
  const target = resolve(binRoot, name)
  const temporary = `${target}.${process.pid}.${randomUUID()}.tmp`
  renameSync(resolve(staging, name), temporary)
  renameSync(temporary, target)
}
rmSync(staging, { recursive: true, force: true })

const status = spawnSync(
  layout.nodeExecutable,
  [installedLauncher, 'status'],
  { encoding: 'utf8', windowsHide: true },
)
if (status.status !== 0) {
  throw new Error(`Installed Machine Launcher verification failed: ${status.stderr}`)
}
process.stdout.write(`${JSON.stringify({
  status: 'INSTALLED',
  ...manifest,
  command: installedCommand,
  mechanicalStatus: JSON.parse(status.stdout),
})}\n`)
