import { createHash } from 'node:crypto'
import { existsSync, readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { resolve } from 'node:path'

import {
  EXPECTED_NODE_VERSION,
  layout,
  packageRoot,
} from './environment-layout.mjs'

export const TOOLCHAIN_SCHEMA = 'et-harness.toolchain.v1'

const hashBuffer = value => createHash('sha256').update(value).digest('hex')
const canonicalPackageBytes = value => Buffer.from(
  (Buffer.isBuffer(value) ? value.toString('utf8') : String(value)).replace(/\r\n?/g, '\n'),
  'utf8',
)
const hashPackageBytes = value => hashBuffer(canonicalPackageBytes(value))
const readJson = path => JSON.parse(readFileSync(path, 'utf8'))
const parsePackageManifest = bytes => {
  const parsed = JSON.parse(Buffer.isBuffer(bytes) ? bytes.toString('utf8') : String(bytes))
  return Object.freeze({
    ...(parsed.dependencies ?? {}),
    ...(parsed.devDependencies ?? {}),
  })
}

export const packageManifestPath = resolve(packageRoot, 'package.json')
export const packageLockPath = resolve(packageRoot, 'package-lock.json')

export const pinnedDependencies = () => parsePackageManifest(readFileSync(packageManifestPath))

export const computeToolchainDescriptor = (options = {}) => {
  const packageJsonBytes = options.packageJsonBytes ?? readFileSync(packageManifestPath)
  const packageLockBytes = options.packageLockBytes ?? readFileSync(packageLockPath)
  const nodeVersion = options.nodeVersion ?? EXPECTED_NODE_VERSION
  const platform = options.platform ?? process.platform
  const arch = options.arch ?? process.arch
  const packageJsonSha256 = hashPackageBytes(packageJsonBytes)
  const packageLockSha256 = hashPackageBytes(packageLockBytes)
  const digest = createHash('sha256')
  digest.update('et-harness-toolchain-v1\0')
  digest.update(`${nodeVersion}\0${platform}\0${arch}\0`)
  digest.update(`${packageJsonSha256}\0${packageLockSha256}\0`)
  const toolchainId = `tc-${digest.digest('hex').slice(0, 24)}`
  return Object.freeze({
    schema: TOOLCHAIN_SCHEMA,
    toolchainId,
    nodeVersion,
    platform,
    arch,
    packageJsonSha256,
    packageLockSha256,
    dependencies: parsePackageManifest(packageJsonBytes),
  })
}

export const toolchainRootFor = descriptor => resolve(layout.toolchainsRoot, descriptor.toolchainId)

export const verifyInstalledDependencies = (toolchainRoot, descriptor) => {
  const versions = {}
  for (const [name, expected] of Object.entries(descriptor.dependencies)) {
    const manifestPath = resolve(toolchainRoot, 'node_modules', ...name.split('/'), 'package.json')
    let installed
    try {
      installed = readJson(manifestPath)
    } catch {
      throw new Error(`Shared Toolchain dependency is unavailable: ${name}`)
    }
    if (installed.version !== expected) {
      throw new Error(
        `Shared Toolchain dependency mismatch for ${name}: expected ${expected}, received ${installed.version}`,
      )
    }
    versions[name] = installed.version
  }
  return Object.freeze(versions)
}

export const verifyLockfileInstallation = toolchainRoot => {
  const lock = readJson(resolve(toolchainRoot, 'package-lock.json'))
  if (lock?.lockfileVersion !== 3 || !lock.packages || typeof lock.packages !== 'object') {
    throw new Error('Shared Toolchain package-lock.json is not a supported npm lockfile v3')
  }
  let verifiedPackageCount = 0
  let skippedOptionalCount = 0
  for (const [packagePath, locked] of Object.entries(lock.packages)) {
    if (!packagePath.startsWith('node_modules/') || !locked || typeof locked !== 'object') continue
    if (locked.link === true) continue
    const expectedVersion = locked.version
    if (typeof expectedVersion !== 'string' || !expectedVersion) continue
    const installedManifest = resolve(toolchainRoot, packagePath, 'package.json')
    if (!existsSync(installedManifest)) {
      if (locked.optional === true) {
        skippedOptionalCount += 1
        continue
      }
      throw new Error(`Shared Toolchain lockfile package is unavailable: ${packagePath}@${expectedVersion}`)
    }
    const installed = readJson(installedManifest)
    if (installed.version !== expectedVersion) {
      throw new Error(
        `Shared Toolchain lockfile mismatch for ${packagePath}: expected ${expectedVersion}, received ${installed.version}`,
      )
    }
    verifiedPackageCount += 1
  }
  return Object.freeze({ verifiedPackageCount, skippedOptionalCount })
}

export const verifyToolchainAt = (toolchainRoot, expectedDescriptor = computeToolchainDescriptor()) => {
  const manifestPath = resolve(toolchainRoot, 'toolchain.json')
  if (!existsSync(manifestPath)) {
    throw new Error(
      `Shared ET Harness Toolchain is not prepared: ${expectedDescriptor.toolchainId}; `
      + 'run scripts\\prepare-toolchain.cmd once for this dependency lock.',
    )
  }
  const manifest = readJson(manifestPath)
  for (const [field, expected] of [
    ['schema', TOOLCHAIN_SCHEMA],
    ['toolchainId', expectedDescriptor.toolchainId],
    ['nodeVersion', expectedDescriptor.nodeVersion],
    ['platform', expectedDescriptor.platform],
    ['arch', expectedDescriptor.arch],
    ['packageJsonSha256', expectedDescriptor.packageJsonSha256],
    ['packageLockSha256', expectedDescriptor.packageLockSha256],
  ]) {
    if (manifest?.[field] !== expected) {
      throw new Error(`Shared Toolchain manifest mismatch at ${field}: expected ${expected}, received ${manifest?.[field]}`)
    }
  }
  if (process.version !== expectedDescriptor.nodeVersion) {
    throw new Error(`ET Harness Toolchain requires ${expectedDescriptor.nodeVersion}; current Node is ${process.version}`)
  }
  if (process.platform !== expectedDescriptor.platform || process.arch !== expectedDescriptor.arch) {
    throw new Error(
      `ET Harness Toolchain platform mismatch: expected ${expectedDescriptor.platform}/${expectedDescriptor.arch}, `
      + `received ${process.platform}/${process.arch}`,
    )
  }
  const dependencyVersions = verifyInstalledDependencies(toolchainRoot, expectedDescriptor)
  const lockfileVerification = verifyLockfileInstallation(toolchainRoot)
  return Object.freeze({
    descriptor: expectedDescriptor,
    manifest,
    toolchainRoot,
    dependencyVersions,
    lockfileVerification,
  })
}

export const resolveCurrentToolchain = () => {
  const descriptor = computeToolchainDescriptor()
  return verifyToolchainAt(toolchainRootFor(descriptor), descriptor)
}

export const createToolchainRequire = toolchainRoot =>
  createRequire(resolve(toolchainRoot, 'package.json'))

export const resolveToolchainPackage = (specifier, toolchain = resolveCurrentToolchain()) =>
  createToolchainRequire(toolchain.toolchainRoot).resolve(specifier)
