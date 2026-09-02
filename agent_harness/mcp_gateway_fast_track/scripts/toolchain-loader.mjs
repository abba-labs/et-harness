import { createToolchainRequire, resolveCurrentToolchain } from './toolchain.mjs'

const toolchain = resolveCurrentToolchain()
const requireFromToolchain = createToolchainRequire(toolchain.toolchainRoot)
const directPackages = Object.keys(toolchain.descriptor.dependencies)

const ownedPackage = specifier => directPackages.find(name =>
  specifier === name || specifier.startsWith(`${name}/`),
)

export async function resolve(specifier, context, nextResolve) {
  if (!ownedPackage(specifier)) return nextResolve(specifier, context)
  const url = new URL(`file:///${requireFromToolchain.resolve(specifier).replaceAll('\\', '/')}`)
  return { url: url.href, shortCircuit: true }
}
