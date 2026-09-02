import { randomUUID } from 'node:crypto'
import { spawnSync } from 'node:child_process'
import {
  copyFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  renameSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import { dirname, resolve } from 'node:path'

import {
  EXPECTED_NODE_VERSION,
  layout,
} from './environment-layout.mjs'
import {
  TOOLCHAIN_SCHEMA,
  computeToolchainDescriptor,
  packageLockPath,
  packageManifestPath,
  toolchainRootFor,
  verifyInstalledDependencies,
  verifyToolchainAt,
} from './toolchain.mjs'

if (process.version !== EXPECTED_NODE_VERSION) {
  throw new Error(`Shared Toolchain preparation requires ${EXPECTED_NODE_VERSION}; current Node is ${process.version}`)
}

const descriptor = computeToolchainDescriptor()
const toolchainRoot = toolchainRootFor(descriptor)

try {
  const verified = verifyToolchainAt(toolchainRoot, descriptor)
  process.stdout.write(`${JSON.stringify({
    status: 'REUSED',
    toolchainId: descriptor.toolchainId,
    toolchainRoot: verified.toolchainRoot,
  })}\n`)
  process.exit(0)
} catch (error) {
  if (existsSync(toolchainRoot)) {
    throw new Error(
      `Shared Toolchain directory exists but failed verification and will not be mutated: ${toolchainRoot}; `
      + `${error instanceof Error ? error.message : String(error)}`,
    )
  }
}

if (!existsSync(layout.npmCli)) {
  throw new Error(`Pinned npm CLI is unavailable: ${layout.npmCli}`)
}
mkdirSync(layout.toolchainTempRoot, { recursive: true })
mkdirSync(layout.npmCache, { recursive: true })
mkdirSync(layout.toolchainsRoot, { recursive: true })
const staging = resolve(layout.toolchainTempRoot, `${descriptor.toolchainId}.${process.pid}.${randomUUID()}`)
rmSync(staging, { recursive: true, force: true })
mkdirSync(staging, { recursive: true })
copyFileSync(packageManifestPath, resolve(staging, 'package.json'))
copyFileSync(packageLockPath, resolve(staging, 'package-lock.json'))

const npm = spawnSync(
  process.execPath,
  [
    layout.npmCli,
    'ci',
    '--ignore-scripts',
    '--no-audit',
    '--no-fund',
  ],
  {
    cwd: staging,
    encoding: 'utf8',
    windowsHide: true,
    env: {
      ...process.env,
      TEMP: layout.toolchainTempRoot,
      TMP: layout.toolchainTempRoot,
      npm_config_cache: layout.npmCache,
    },
  },
)
if (npm.status !== 0) {
  rmSync(staging, { recursive: true, force: true })
  const detail = [npm.stderr, npm.stdout].filter(value => value?.trim()).join('\n').trim()
  throw new Error(`Shared Toolchain npm ci failed with exit ${npm.status}${detail ? `: ${detail}` : ''}`)
}

const dependencyVersions = verifyInstalledDependencies(staging, descriptor)
const manifest = {
  schema: TOOLCHAIN_SCHEMA,
  toolchainId: descriptor.toolchainId,
  nodeVersion: descriptor.nodeVersion,
  platform: descriptor.platform,
  arch: descriptor.arch,
  packageJsonSha256: descriptor.packageJsonSha256,
  packageLockSha256: descriptor.packageLockSha256,
  dependencies: dependencyVersions,
  createdAt: new Date().toISOString(),
}
writeFileSync(resolve(staging, 'toolchain.json'), `${JSON.stringify(manifest, null, 2)}\n`, 'utf8')

try {
  renameSync(staging, toolchainRoot)
} catch (error) {
  if (!existsSync(toolchainRoot)) throw error
  rmSync(staging, { recursive: true, force: true })
}

const verified = verifyToolchainAt(toolchainRoot, descriptor)
process.stdout.write(`${JSON.stringify({
  status: 'PREPARED',
  toolchainId: descriptor.toolchainId,
  toolchainRoot: verified.toolchainRoot,
  dependencyCount: Object.keys(verified.dependencyVersions).length,
})}\n`)
