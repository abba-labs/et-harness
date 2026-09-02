import { randomUUID } from 'node:crypto'
import { spawnSync } from 'node:child_process'
import {
  copyFileSync,
  cpSync,
  existsSync,
  mkdirSync,
  readFileSync,
  renameSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import { resolve } from 'node:path'

import {
  EXPECTED_NODE_VERSION,
  layout,
  packageRoot,
} from './environment-layout.mjs'
import {
  TOOLCHAIN_SCHEMA,
  computeToolchainDescriptor,
  packageLockPath,
  packageManifestPath,
  toolchainRootFor,
  verifyInstalledDependencies,
  verifyLockfileInstallation,
  verifyToolchainAt,
} from './toolchain.mjs'
import { verifyRuntimeReleasePointer } from '../src/runtime-release.mjs'

if (process.version !== EXPECTED_NODE_VERSION) {
  throw new Error(`Shared Toolchain preparation requires ${EXPECTED_NODE_VERSION}; current Node is ${process.version}`)
}

const descriptor = computeToolchainDescriptor()
const toolchainRoot = toolchainRootFor(descriptor)
const seedOnly = process.argv.includes('--seed-only')

try {
  const verified = verifyToolchainAt(toolchainRoot, descriptor)
  process.stdout.write(`${JSON.stringify({
    status: 'REUSED',
    toolchainId: descriptor.toolchainId,
    toolchainRoot: verified.toolchainRoot,
    preparationSource: verified.manifest.preparationSource ?? 'existing',
    verifiedPackageCount: verified.lockfileVerification.verifiedPackageCount,
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

mkdirSync(layout.toolchainTempRoot, { recursive: true })
mkdirSync(layout.npmCache, { recursive: true })
mkdirSync(layout.toolchainsRoot, { recursive: true })
const staging = resolve(layout.toolchainTempRoot, `${descriptor.toolchainId}.${process.pid}.${randomUUID()}`)
rmSync(staging, { recursive: true, force: true })
mkdirSync(staging, { recursive: true })
copyFileSync(packageManifestPath, resolve(staging, 'package.json'))
copyFileSync(packageLockPath, resolve(staging, 'package-lock.json'))

let preparationSource = await seedFromVerifiedEnvironment(staging)
if (!preparationSource && seedOnly) {
  rmSync(staging, { recursive: true, force: true })
  throw new Error(
    `Seed-only Toolchain preparation could not find one fully verified package-lock-compatible seed for ${descriptor.toolchainId}; `
    + 'npm ci was not attempted.',
  )
}
if (!preparationSource) {
  if (!existsSync(layout.npmCli)) {
    rmSync(staging, { recursive: true, force: true })
    throw new Error(`Pinned npm CLI is unavailable: ${layout.npmCli}`)
  }
  const npm = spawnSync(
    process.execPath,
    [
      layout.npmCli,
      'ci',
      '--ignore-scripts',
      '--no-audit',
      '--no-fund',
      '--prefer-offline',
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
  preparationSource = 'npm-ci'
}

const dependencyVersions = verifyInstalledDependencies(staging, descriptor)
const lockfileVerification = verifyLockfileInstallation(staging)
const manifest = {
  schema: TOOLCHAIN_SCHEMA,
  toolchainId: descriptor.toolchainId,
  nodeVersion: descriptor.nodeVersion,
  platform: descriptor.platform,
  arch: descriptor.arch,
  packageJsonSha256: descriptor.packageJsonSha256,
  packageLockSha256: descriptor.packageLockSha256,
  dependencies: dependencyVersions,
  verifiedPackageCount: lockfileVerification.verifiedPackageCount,
  skippedOptionalCount: lockfileVerification.skippedOptionalCount,
  preparationSource,
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
  verifiedPackageCount: verified.lockfileVerification.verifiedPackageCount,
  skippedOptionalCount: verified.lockfileVerification.skippedOptionalCount,
  preparationSource: verified.manifest.preparationSource,
})}\n`)

async function seedFromVerifiedEnvironment(stagingRoot) {
  const candidates = []
  const explicitSeed = process.env.ET_HARNESS_TOOLCHAIN_SEED?.trim()
  if (explicitSeed) candidates.push(resolve(explicitSeed))

  try {
    const active = await verifyRuntimeReleasePointer(layout.activeReleasePointer)
    if (typeof active.manifest.repositoryRoot === 'string') {
      candidates.push(resolve(
        active.manifest.repositoryRoot,
        'agent_harness',
        'mcp_gateway_fast_track',
      ))
    }
  } catch {
    // A shared Toolchain can still be prepared on a machine with no active Runtime.
  }
  candidates.push(packageRoot)

  const uniqueCandidates = [...new Set(candidates.map(value => value.toLowerCase()))]
  for (const normalized of uniqueCandidates) {
    const seedRoot = candidates.find(value => value.toLowerCase() === normalized)
    if (!seedRoot || !compatibleSeed(seedRoot)) continue
    const seedModules = resolve(seedRoot, 'node_modules')
    if (!existsSync(seedModules)) continue
    rmSync(resolve(stagingRoot, 'node_modules'), { recursive: true, force: true })
    try {
      cpSync(seedModules, resolve(stagingRoot, 'node_modules'), {
        recursive: true,
        errorOnExist: true,
        force: false,
      })
      verifyInstalledDependencies(stagingRoot, descriptor)
      verifyLockfileInstallation(stagingRoot)
      return `verified-seed:${seedRoot}`
    } catch {
      rmSync(resolve(stagingRoot, 'node_modules'), { recursive: true, force: true })
    }
  }
  return undefined
}

function compatibleSeed(seedRoot) {
  try {
    const packageJson = readFileSync(resolve(seedRoot, 'package.json'))
    const packageLock = readFileSync(resolve(seedRoot, 'package-lock.json'))
    const seedDescriptor = computeToolchainDescriptor({
      packageJsonBytes: packageJson,
      packageLockBytes: packageLock,
    })
    return seedDescriptor.packageJsonSha256 === descriptor.packageJsonSha256
      && seedDescriptor.packageLockSha256 === descriptor.packageLockSha256
      && Boolean(verifyInstalledDependencies(seedRoot, descriptor))
      && Boolean(verifyLockfileInstallation(seedRoot))
  } catch {
    return false
  }
}
