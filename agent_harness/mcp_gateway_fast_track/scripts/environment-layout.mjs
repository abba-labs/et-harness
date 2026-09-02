import { existsSync, readFileSync } from 'node:fs'
import { dirname, isAbsolute, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

export const ET_HARNESS_ENV_ROOT_VAR = 'ET_HARNESS_ENV_ROOT'
export const EXPECTED_NODE_VERSION = 'v22.23.2'

const scriptDirectory = dirname(fileURLToPath(import.meta.url))
export const packageRoot = resolve(scriptDirectory, '..')
export const repositoryRoot = resolve(packageRoot, '..', '..')
const legacyGatewayConfigPath = resolve(packageRoot, 'config', 'gateway.local.json')

const cleanAbsolutePath = (label, value) => {
  const normalized = String(value ?? '').trim()
  if (!normalized || !isAbsolute(normalized)) {
    throw new Error(`${label} must be an absolute path`)
  }
  return resolve(normalized)
}

const legacyEnvironmentRoot = () => {
  try {
    const config = JSON.parse(readFileSync(legacyGatewayConfigPath, 'utf8'))
    const pointer = config?.runtimeReleasePointerPath
    if (typeof pointer !== 'string' || !isAbsolute(pointer)) return undefined
    const stateRoot = resolve(pointer, '..', '..')
    const root = resolve(stateRoot, '..')
    return existsSync(root) ? root : undefined
  } catch {
    return undefined
  }
}

export const resolveEnvironmentRoot = (options = {}) => {
  const explicit = options.environmentRoot ?? process.env[ET_HARNESS_ENV_ROOT_VAR]
  if (explicit?.trim()) return cleanAbsolutePath(ET_HARNESS_ENV_ROOT_VAR, explicit)

  if (options.allowLegacyGatewayConfig !== false) {
    const legacy = legacyEnvironmentRoot()
    if (legacy) return legacy
  }

  throw new Error(
    `${ET_HARNESS_ENV_ROOT_VAR} is not configured. `
    + 'Set it once to the machine-level ET Harness environment root; source checkout paths must not own runtime state or dependencies.',
  )
}

export const environmentLayout = (environmentRootInput = resolveEnvironmentRoot()) => {
  const environmentRoot = cleanAbsolutePath('ET Harness environment root', environmentRootInput)
  const stateRoot = resolve(environmentRoot, 'state', 'pure-mcp-fast-track')
  const nodeRuntimeRoot = resolve(environmentRoot, 'runtimes', 'node-v22.23.2-win-x64')
  return Object.freeze({
    environmentRoot,
    nodeRuntimeRoot,
    nodeExecutable: resolve(nodeRuntimeRoot, 'node.exe'),
    npmCli: resolve(nodeRuntimeRoot, 'node_modules', 'npm', 'bin', 'npm-cli.js'),
    toolchainsRoot: resolve(environmentRoot, 'toolchains'),
    releasesRoot: resolve(stateRoot, 'releases'),
    stateRoot,
    runtimeStateRoot: resolve(stateRoot, 'runtime-state'),
    eventStoreRoot: resolve(stateRoot, 'runtime-state', 'execution-events'),
    taskSnapshotRoot: resolve(stateRoot, 'gateway-task-snapshots'),
    activeReleasePointer: resolve(stateRoot, 'active-release.json'),
    previousReleasePointer: resolve(stateRoot, 'previous-release.json'),
    gatewayPidFile: resolve(stateRoot, 'gateway.pid.json'),
    gatewayStdoutLog: resolve(stateRoot, 'gateway.stdout.log'),
    gatewayStderrLog: resolve(stateRoot, 'gateway.stderr.log'),
    tempRoot: resolve(environmentRoot, 'temp'),
    runtimeBuildTempRoot: resolve(environmentRoot, 'temp', 'pure-mcp-runtime-build'),
    toolchainTempRoot: resolve(environmentRoot, 'temp', 'toolchains'),
    gatewayTempRoot: resolve(environmentRoot, 'temp', 'pure-mcp-gateway'),
    cacheRoot: resolve(environmentRoot, 'cache'),
    npmCache: resolve(environmentRoot, 'cache', 'npm'),
    pythonCache: resolve(environmentRoot, 'cache', 'python'),
  })
}

export const environmentRoot = resolveEnvironmentRoot()
export const layout = environmentLayout(environmentRoot)
