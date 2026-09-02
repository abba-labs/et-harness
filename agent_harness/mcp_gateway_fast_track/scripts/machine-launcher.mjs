import { createHash, randomUUID } from 'node:crypto'
import { spawn, spawnSync } from 'node:child_process'
import {
  closeSync,
  existsSync,
  mkdirSync,
  openSync,
  readFileSync,
  realpathSync,
  renameSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import { connect } from 'node:net'
import { basename, dirname, isAbsolute, relative, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

export const LAUNCHER_VERSION = '0.1.0'
export const EXPECTED_NODE_VERSION = 'v22.23.2'
const POINTER_SCHEMA = 'et-harness.pure-mcp-active-release.v1'
const RELEASE_SCHEMAS = new Set([
  'et-harness.pure-mcp-runtime-release.v1',
  'et-harness.pure-mcp-runtime-release.v2',
])
const V2_RELEASE_SCHEMA = 'et-harness.pure-mcp-runtime-release.v2'
const MANIFEST_SCHEMA = 'et-harness.machine-launcher.v0.1'
const EXPECTED_TOOLS = [
  'harness_health',
  'harness_begin',
  'harness_status',
  'harness_observe',
  'harness_preflight',
  'harness_complete',
  'harness_read_required',
  'harness_checkpoint',
]
const FORBIDDEN_PROCESS_NAMES = new Set(['chatgpt.exe', 'codex.exe'])
const FORBIDDEN_COMMAND_FRAGMENTS = ['\\.codex\\plugins\\', '\\hooks\\', '\\marketplace\\']

const readJson = path => JSON.parse(readFileSync(path, 'utf8'))
const hashFile = path => createHash('sha256').update(readFileSync(path)).digest('hex')
const samePath = (left, right) => resolve(left).toLowerCase() === resolve(right).toLowerCase()
const inside = (candidate, root) => {
  const relation = relative(root, candidate)
  return relation === '' || (!relation.startsWith('..') && !isAbsolute(relation))
}
const delay = milliseconds => new Promise(resolveDelay => setTimeout(resolveDelay, milliseconds))

export const environmentRootFromLauncher = launcherPath => resolve(dirname(launcherPath), '..')

export const machineLayout = launcherPath => {
  const environmentRoot = environmentRootFromLauncher(launcherPath)
  const stateRoot = resolve(environmentRoot, 'state', 'pure-mcp-fast-track')
  return Object.freeze({
    environmentRoot,
    binRoot: resolve(environmentRoot, 'bin'),
    nodeExecutable: resolve(environmentRoot, 'runtimes', 'node-v22.23.2-win-x64', 'node.exe'),
    stateRoot,
    activeReleasePointer: resolve(stateRoot, 'active-release.json'),
    previousReleasePointer: resolve(stateRoot, 'previous-release.json'),
    gatewayPidFile: resolve(stateRoot, 'gateway.pid.json'),
    gatewayStdoutLog: resolve(stateRoot, 'gateway.stdout.log'),
    gatewayStderrLog: resolve(stateRoot, 'gateway.stderr.log'),
    runtimeStateRoot: resolve(stateRoot, 'runtime-state'),
    eventStoreRoot: resolve(stateRoot, 'runtime-state', 'execution-events'),
    taskSnapshotRoot: resolve(stateRoot, 'gateway-task-snapshots'),
    gatewayTempRoot: resolve(environmentRoot, 'temp', 'pure-mcp-gateway'),
    npmCache: resolve(environmentRoot, 'cache', 'npm'),
    pythonCache: resolve(environmentRoot, 'cache', 'python'),
    launcherManifest: resolve(environmentRoot, 'bin', 'machine-launcher.json'),
  })
}

export const verifyLauncherInstallation = (layout, launcherPath) => {
  const manifest = readJson(layout.launcherManifest)
  if (manifest?.schema !== MANIFEST_SCHEMA
      || manifest.launcherVersion !== LAUNCHER_VERSION
      || manifest.environmentRoot !== layout.environmentRoot
      || manifest.expectedNodeVersion !== EXPECTED_NODE_VERSION
      || manifest.launcherSha256 !== hashFile(launcherPath)) {
    throw new Error('Installed Machine Launcher failed manifest verification')
  }
  if (process.version !== EXPECTED_NODE_VERSION || !samePath(process.execPath, layout.nodeExecutable)) {
    throw new Error(
      `Machine Launcher requires ${layout.nodeExecutable} (${EXPECTED_NODE_VERSION}); `
      + `received ${process.execPath} (${process.version})`,
    )
  }
  return manifest
}

export const verifyRuntimeReleaseManifest = (layout, manifestPathInput, { requireV2 = false } = {}) => {
  if (!isAbsolute(manifestPathInput)) throw new Error('Runtime release manifest path must be absolute')
  const canonicalEnvironment = realpathSync(layout.environmentRoot)
  const manifestPath = realpathSync(manifestPathInput)
  if (!inside(manifestPath, canonicalEnvironment)) {
    throw new Error('Runtime release manifest escapes the machine Environment Root')
  }
  const manifest = readJson(manifestPath)
  if (!RELEASE_SCHEMAS.has(manifest?.schema) || (requireV2 && manifest.schema !== V2_RELEASE_SCHEMA)) {
    throw new Error(requireV2
      ? 'Normal Machine Launcher start requires a v2 release-bundled Runtime'
      : 'Runtime release manifest schema is invalid')
  }
  if (manifest.nodeVersion !== EXPECTED_NODE_VERSION || manifest.nodeVersion !== process.version) {
    throw new Error(`Runtime release requires ${manifest.nodeVersion}; Machine Node is ${process.version}`)
  }
  const releaseRoot = resolve(manifestPath, '..')
  for (const [name, expectedHash] of Object.entries(manifest.artifacts ?? {})) {
    const artifactPath = resolve(releaseRoot, name)
    if (!inside(artifactPath, releaseRoot)
        || typeof expectedHash !== 'string'
        || hashFile(artifactPath) !== expectedHash) {
      throw new Error(`Runtime release artifact failed integrity verification: ${name}`)
    }
  }
  const required = ['runtime.mjs', 'atp-project-plugin.mjs', 'deployment.json']
  if (manifest.schema === V2_RELEASE_SCHEMA) {
    required.push('gateway.mjs', 'runtime-pointer.json', 'config/gateway.local.json')
  }
  for (const name of required) {
    if (typeof manifest.artifacts?.[name] !== 'string') {
      throw new Error(`Runtime release is missing required artifact: ${name}`)
    }
  }
  let gatewayEntry
  if (manifest.schema === V2_RELEASE_SCHEMA) {
    const runtimePointerPath = resolve(releaseRoot, 'runtime-pointer.json')
    const localPointer = readJson(runtimePointerPath)
    if (localPointer?.schema !== POINTER_SCHEMA
        || typeof localPointer.releaseManifestPath !== 'string'
        || !isAbsolute(localPointer.releaseManifestPath)
        || !samePath(localPointer.releaseManifestPath, manifestPath)) {
      throw new Error('Bundled Gateway Runtime pointer does not bind to its own release manifest')
    }
    const gatewayConfig = readJson(resolve(releaseRoot, 'config', 'gateway.local.json'))
    if (typeof gatewayConfig.runtimeReleasePointerPath !== 'string'
        || !isAbsolute(gatewayConfig.runtimeReleasePointerPath)
        || !samePath(gatewayConfig.runtimeReleasePointerPath, runtimePointerPath)) {
      throw new Error('Bundled Gateway configuration does not use its release-local Runtime pointer')
    }
    gatewayEntry = resolve(releaseRoot, 'gateway.mjs')
  }
  return Object.freeze({
    manifest,
    manifestPath,
    releaseRoot,
    releaseId: basename(releaseRoot),
    gatewayEntry,
  })
}

export const verifyRuntimeReleasePointer = (layout, pointerPath, options) => {
  const pointer = readJson(pointerPath)
  if (pointer?.schema !== POINTER_SCHEMA
      || typeof pointer.releaseManifestPath !== 'string'
      || !isAbsolute(pointer.releaseManifestPath)) {
    throw new Error('Runtime release pointer is invalid')
  }
  return verifyRuntimeReleaseManifest(layout, pointer.releaseManifestPath, options)
}

const isProcessRunning = pid => {
  if (!Number.isInteger(pid) || pid <= 0) return false
  try {
    process.kill(pid, 0)
    return true
  } catch {
    return false
  }
}

const readProcess = pid => {
  const command = `
$ErrorActionPreference = 'Stop'
$process = Get-CimInstance Win32_Process -Filter "ProcessId = ${pid}"
if ($null -eq $process) { exit 3 }
[pscustomobject]@{
  processId = [int]$process.ProcessId
  parentProcessId = [int]$process.ParentProcessId
  name = [string]$process.Name
  executablePath = [string]$process.ExecutablePath
  commandLine = [string]$process.CommandLine
} | ConvertTo-Json -Compress
`
  const result = spawnSync('powershell.exe', ['-NoProfile', '-Command', command], {
    encoding: 'utf8',
    windowsHide: true,
  })
  if (result.status !== 0 || !result.stdout.trim()) return undefined
  return JSON.parse(result.stdout)
}

const readAncestorProcesses = (processId = process.pid) => {
  const command = `
$ErrorActionPreference = 'Stop'
$currentProcessId = ${processId}
$seen = @{}
$rows = @()
for ($index = 0; $index -lt 16 -and $currentProcessId -gt 0; $index++) {
  if ($seen.ContainsKey($currentProcessId)) { break }
  $seen[$currentProcessId] = $true
  $current = Get-CimInstance Win32_Process -Filter "ProcessId = $currentProcessId"
  if ($null -eq $current) { break }
  $rows += [pscustomobject]@{
    processId = [int]$current.ProcessId
    parentProcessId = [int]$current.ParentProcessId
    name = [string]$current.Name
    commandLine = [string]$current.CommandLine
  }
  $currentProcessId = [int]$current.ParentProcessId
}
ConvertTo-Json -InputObject @($rows) -Compress
`
  const result = spawnSync('powershell.exe', ['-NoProfile', '-Command', command], {
    encoding: 'utf8',
    windowsHide: true,
  })
  if (result.status !== 0 || !result.stdout.trim()) {
    throw new Error('Unable to verify the Machine Launcher ancestry')
  }
  const parsed = JSON.parse(result.stdout)
  return Array.isArray(parsed) ? parsed : [parsed]
}

export const findForbiddenLauncher = processes => processes.find(processInfo => {
  const name = String(processInfo.name ?? '').toLowerCase()
  const commandLine = String(processInfo.commandLine ?? '').toLowerCase()
  return FORBIDDEN_PROCESS_NAMES.has(name)
    || FORBIDDEN_COMMAND_FRAGMENTS.some(fragment => commandLine.includes(fragment))
})

const assertExternalLauncher = () => {
  const processes = readAncestorProcesses()
  const forbidden = findForbiddenLauncher(processes)
  if (forbidden) {
    throw new Error(
      `Machine Gateway startup rejected: ${forbidden.name} is in the launcher ancestry; `
      + 'start it from Windows Explorer or an independent terminal outside Codex Desktop',
    )
  }
  return processes
}

const readPidRecord = layout => {
  if (!existsSync(layout.gatewayPidFile)) return undefined
  try {
    return readJson(layout.gatewayPidFile)
  } catch {
    throw new Error(`Gateway PID record is invalid: ${layout.gatewayPidFile}`)
  }
}

const atomicWriteJson = (path, value) => {
  const temporary = `${path}.${process.pid}.${randomUUID()}.tmp`
  writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, 'utf8')
  renameSync(temporary, path)
}

const portIsOpen = async (timeoutMs = 500) => new Promise(resolvePort => {
  const socket = connect({ host: '127.0.0.1', port: 8765 })
  const finish = value => {
    socket.destroy()
    resolvePort(value)
  }
  socket.setTimeout(timeoutMs, () => finish(false))
  socket.once('connect', () => finish(true))
  socket.once('error', () => finish(false))
})

const waitForHttpHealth = async (pid, timeoutMs = 10_000) => {
  const deadline = Date.now() + timeoutMs
  let lastError
  while (Date.now() < deadline) {
    if (!isProcessRunning(pid)) throw new Error(`Gateway PID ${pid} exited before readiness`)
    try {
      const response = await fetch('http://127.0.0.1:8765/health', {
        signal: AbortSignal.timeout(1_000),
      })
      if (response.ok) {
        const health = await response.json()
        if (health.status === 'UP' && health.processId === pid) return health
      }
    } catch (error) {
      lastError = error
    }
    await delay(100)
  }
  throw new Error(`Gateway HTTP readiness failed: ${lastError?.message ?? 'timeout'}`)
}

const stopRecordedGateway = async (layout, record) => {
  if (!record?.pid) return Object.freeze({ status: 'NOT_RUNNING' })
  if (!isProcessRunning(record.pid)) {
    if (await portIsOpen()) {
      throw new Error('Gateway PID is stale but port 8765 is owned by another process')
    }
    rmSync(layout.gatewayPidFile, { force: true })
    return Object.freeze({ status: 'STALE_PID_REMOVED', pid: record.pid })
  }
  if (!record.bundledGateway || record.dependencyMode !== 'release-bundled') {
    throw new Error('Machine Launcher refuses to stop a non-bundled or legacy Gateway record')
  }
  const release = verifyRuntimeReleaseManifest(layout, record.releaseManifestPath, { requireV2: true })
  if (!samePath(record.gatewayEntry, release.gatewayEntry)) {
    throw new Error('Gateway PID record does not match its release-bundled entry')
  }
  const processInfo = readProcess(record.pid)
  if (!processInfo
      || !samePath(processInfo.executablePath, layout.nodeExecutable)
      || !processInfo.commandLine.toLowerCase().includes(release.gatewayEntry.toLowerCase())) {
    throw new Error(`PID ${record.pid} is not the recorded release-bundled ET Harness Gateway`)
  }
  process.kill(record.pid, 'SIGTERM')
  const deadline = Date.now() + 10_000
  while (Date.now() < deadline && isProcessRunning(record.pid)) await delay(100)
  if (isProcessRunning(record.pid)) throw new Error(`Gateway PID ${record.pid} did not exit within 10 seconds`)
  while (Date.now() < deadline && await portIsOpen()) await delay(100)
  if (await portIsOpen()) throw new Error('Gateway port 8765 remained open after stop')
  rmSync(layout.gatewayPidFile, { force: true })
  return Object.freeze({
    status: 'STOPPED',
    pid: record.pid,
    releaseManifestPath: release.manifestPath,
    portClosed: true,
  })
}

const startGateway = async layout => {
  const launcher = assertExternalLauncher()
  const release = verifyRuntimeReleasePointer(
    layout,
    layout.activeReleasePointer,
    { requireV2: true },
  )
  const existing = readPidRecord(layout)
  if (existing?.pid && isProcessRunning(existing.pid)) {
    throw new Error(`Gateway is already running with PID ${existing.pid}`)
  }
  if (existing?.pid) rmSync(layout.gatewayPidFile, { force: true })
  if (await portIsOpen()) throw new Error('Port 8765 is already in use without a live Gateway PID record')

  for (const directory of [layout.stateRoot, layout.gatewayTempRoot, layout.npmCache, layout.pythonCache]) {
    mkdirSync(directory, { recursive: true })
  }
  const stdout = openSync(layout.gatewayStdoutLog, 'a')
  const stderr = openSync(layout.gatewayStderrLog, 'a')
  const child = spawn(layout.nodeExecutable, [release.gatewayEntry], {
    cwd: release.releaseRoot,
    detached: true,
    windowsHide: true,
    stdio: ['ignore', stdout, stderr],
    env: {
      ...process.env,
      ET_HARNESS_ENV_ROOT: layout.environmentRoot,
      TEMP: layout.gatewayTempRoot,
      TMP: layout.gatewayTempRoot,
      npm_config_cache: layout.npmCache,
      PYTHONDONTWRITEBYTECODE: '1',
      PYTHONPYCACHEPREFIX: layout.pythonCache,
    },
  })
  child.unref()
  closeSync(stdout)
  closeSync(stderr)
  const record = {
    pid: child.pid,
    gatewayEntry: release.gatewayEntry,
    releaseManifestPath: release.manifestPath,
    releaseSchema: release.manifest.schema,
    bundledGateway: true,
    dependencyMode: 'release-bundled',
    startedAt: new Date().toISOString(),
    launcher: launcher.map(({ processId, name }) => ({ processId, name })),
  }
  atomicWriteJson(layout.gatewayPidFile, record)
  try {
    const health = await waitForHttpHealth(child.pid)
    return Object.freeze({
      status: 'STARTED',
      pid: child.pid,
      releaseId: release.releaseId,
      releaseManifestPath: release.manifestPath,
      gatewayEntry: release.gatewayEntry,
      bundledGateway: true,
      dependencyMode: 'release-bundled',
      health,
    })
  } catch (error) {
    if (isProcessRunning(child.pid)) process.kill(child.pid, 'SIGTERM')
    const cleanupDeadline = Date.now() + 5_000
    while (Date.now() < cleanupDeadline && isProcessRunning(child.pid)) await delay(100)
    if (isProcessRunning(child.pid)) {
      throw new Error(
        `Gateway startup failed and PID ${child.pid} did not exit; PID record was preserved`,
        { cause: error },
      )
    }
    rmSync(layout.gatewayPidFile, { force: true })
    throw error
  }
}

const statusReport = layout => {
  let activeRelease
  let activeReleaseIntegrity = 'PASS'
  let activeReleaseError
  try {
    activeRelease = verifyRuntimeReleasePointer(layout, layout.activeReleasePointer)
  } catch (error) {
    activeReleaseIntegrity = 'FAIL'
    activeReleaseError = error instanceof Error ? error.message : String(error)
  }
  let previousReleaseId
  try {
    previousReleaseId = verifyRuntimeReleasePointer(layout, layout.previousReleasePointer).releaseId
  } catch {
    previousReleaseId = undefined
  }
  const record = readPidRecord(layout)
  const running = Boolean(record?.pid && isProcessRunning(record.pid))
  return Object.freeze({
    status: activeReleaseIntegrity === 'PASS' ? 'MACHINE_ENVIRONMENT_READY' : 'MACHINE_ENVIRONMENT_INVALID',
    launcherVersion: LAUNCHER_VERSION,
    environmentRoot: layout.environmentRoot,
    nodeVersion: process.version,
    nodePath: process.execPath,
    activeReleaseId: activeRelease?.releaseId,
    activeReleaseSchema: activeRelease?.manifest.schema,
    previousReleaseId,
    pid: record?.pid,
    processRunning: running,
    gatewayEntry: record?.gatewayEntry,
    bundledGateway: record?.bundledGateway ?? false,
    dependencyMode: record?.dependencyMode,
    activeReleaseIntegrity,
    ...(activeReleaseError ? { activeReleaseError } : {}),
  })
}

const mcpPost = async ({ body, sessionId, expectBody = true }) => {
  const response = await fetch('http://127.0.0.1:8765/mcp', {
    method: 'POST',
    headers: {
      accept: 'application/json, text/event-stream',
      'content-type': 'application/json',
      'mcp-protocol-version': '2025-03-26',
      ...(sessionId ? { 'mcp-session-id': sessionId } : {}),
    },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(3_000),
  })
  if (!response.ok) throw new Error(`MCP ${body.method} returned HTTP ${response.status}`)
  const nextSessionId = response.headers.get('mcp-session-id') ?? sessionId
  if (!expectBody) return { sessionId: nextSessionId }
  const payload = await response.json()
  if (payload.error) throw new Error(`MCP ${body.method} failed: ${payload.error.message}`)
  return { sessionId: nextSessionId, payload }
}

const verifyMcpHealth = async () => {
  const initialized = await mcpPost({
    body: {
      jsonrpc: '2.0',
      id: 1,
      method: 'initialize',
      params: {
        protocolVersion: '2025-03-26',
        capabilities: {},
        clientInfo: { name: 'et-harness-machine-launcher', version: LAUNCHER_VERSION },
      },
    },
  })
  if (!initialized.sessionId) throw new Error('MCP initialize returned no session id')
  await mcpPost({
    sessionId: initialized.sessionId,
    expectBody: false,
    body: { jsonrpc: '2.0', method: 'notifications/initialized' },
  })
  const listed = await mcpPost({
    sessionId: initialized.sessionId,
    body: { jsonrpc: '2.0', id: 2, method: 'tools/list', params: {} },
  })
  const tools = listed.payload.result?.tools?.map(tool => tool.name) ?? []
  if (tools.length !== EXPECTED_TOOLS.length
      || EXPECTED_TOOLS.some((name, index) => tools[index] !== name)) {
    throw new Error(`MCP public tool contract mismatch: ${tools.join(', ')}`)
  }
  try {
    await fetch('http://127.0.0.1:8765/mcp', {
      method: 'DELETE',
      headers: {
        'mcp-session-id': initialized.sessionId,
        'mcp-protocol-version': '2025-03-26',
      },
      signal: AbortSignal.timeout(2_000),
    })
  } catch {
    // Session cleanup is best-effort after the required initialize/list proof.
  }
  return Object.freeze({
    serverInfo: initialized.payload.result?.serverInfo,
    protocolVersion: initialized.payload.result?.protocolVersion,
    tools,
    toolCount: tools.length,
  })
}

const healthReport = async layout => {
  const status = statusReport(layout)
  if (status.activeReleaseIntegrity !== 'PASS') throw new Error(status.activeReleaseError)
  if (!status.processRunning || !status.pid) throw new Error('Gateway PID is not running')
  const record = readPidRecord(layout)
  const release = verifyRuntimeReleaseManifest(layout, record.releaseManifestPath, { requireV2: true })
  const processInfo = readProcess(record.pid)
  if (!record.bundledGateway
      || record.dependencyMode !== 'release-bundled'
      || !processInfo
      || !samePath(processInfo.executablePath, layout.nodeExecutable)
      || !processInfo.commandLine.toLowerCase().includes(release.gatewayEntry.toLowerCase())) {
    throw new Error('Running Gateway does not match the release-bundled machine record')
  }
  if (!await portIsOpen()) throw new Error('Gateway port 8765 is not reachable')
  const httpResponse = await fetch('http://127.0.0.1:8765/health', {
    signal: AbortSignal.timeout(2_000),
  })
  if (!httpResponse.ok) throw new Error(`Gateway health returned HTTP ${httpResponse.status}`)
  const http = await httpResponse.json()
  if (http.status !== 'UP' || http.processId !== record.pid) {
    throw new Error('Gateway HTTP health does not match the recorded PID')
  }
  const mcp = await verifyMcpHealth()
  return Object.freeze({ status: 'HEALTHY', machine: status, http, mcp })
}

export const runMachineLauncher = async ({ action, launcherPath }) => {
  const layout = machineLayout(launcherPath)
  verifyLauncherInstallation(layout, launcherPath)
  if (action === 'start') return startGateway(layout)
  if (action === 'stop') return stopRecordedGateway(layout, readPidRecord(layout))
  if (action === 'status') return statusReport(layout)
  if (action === 'health') return healthReport(layout)
  throw new Error('Usage: et-harness.cmd start|stop|status|health')
}

const launcherPath = fileURLToPath(import.meta.url)
const invokedAsMain = process.argv[1]
  && pathToFileURL(resolve(process.argv[1])).href === import.meta.url

if (invokedAsMain) {
  const result = await runMachineLauncher({ action: process.argv[2], launcherPath })
  process.stdout.write(`${JSON.stringify(result)}\n`)
}
