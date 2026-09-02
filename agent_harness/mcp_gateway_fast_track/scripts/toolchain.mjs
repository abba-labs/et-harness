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
const readJson = path => JSON.parse(readFileSync(path, 'utf8'))

export const packageManifestPath = resolve(packageRoot, 'package.json')
export const packageLockPath = resolve(packageRoot, 'package-lock.json')

export const pinnedDependencies = () => {
  const manifest = readJson(packageManifestPath)
  return Object.freeze({
    ...(manifest.dependencies ?? {}),
    ...(manifest.devDependencies ?? {}),
  })
}

export const computeToolchainDescriptor = (options = {}) => {
  const packageJsonBytes = options.packageJsonBytes ?? readFileSync(packageManifestPath)
  const packageLockBytes = options.packageLockBytes ?? readFileSync(packageLockPath)
  const nodeVersion = options.nodeVersion ?? EXPECTED_NODE_VERSION
  const platform = options.platform ?? process.platform
  const arch = options.arch ?? process.arch
  const packageJsonSha256 = hashBuffer(packageJsonBytes)
  const packageLockSha256 = hashBuffer(packageLockBytes)
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
    dependencies: pinnedDependencies(),
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
  return Object.freeze({
    descriptor: expectedDescriptor,
    manifest,
    toolchainRoot,
    dependencyVersions,
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
