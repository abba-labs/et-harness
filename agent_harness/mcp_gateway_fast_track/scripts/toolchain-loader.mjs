import { pathToFileURL } from 'node:url'

import { createToolchainRequire, resolveCurrentToolchain } from './toolchain.mjs'

const toolchain = resolveCurrentToolchain()
const requireFromToolchain = createToolchainRequire(toolchain.toolchainRoot)
const directPackages = Object.keys(toolchain.descriptor.dependencies)

const ownedPackage = specifier => directPackages.find(name =>
  specifier === name || specifier.startsWith(`${name}/`),
)

export async function resolve(specifier, context, nextResolve) {
  if (!ownedPackage(specifier)) return nextResolve(specifier, context)
  return {
    url: pathToFileURL(requireFromToolchain.resolve(specifier)).href,
    shortCircuit: true,
  }
}
