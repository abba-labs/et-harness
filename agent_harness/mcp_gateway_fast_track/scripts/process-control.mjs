import { spawn, spawnSync } from 'node:child_process'
import {
  closeSync,
  existsSync,
  mkdirSync,
  openSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs'
import { resolve } from 'node:path'
import { connect } from 'node:net'
import { pathToFileURL } from 'node:url'

import { assertExternalGatewayLauncher } from './launcher-policy.mjs'
import {
  ET_HARNESS_ENV_ROOT_VAR,
  layout,
  packageRoot,
} from './environment-layout.mjs'
import { verifyRuntimeReleasePointer } from '../src/runtime-release.mjs'

const isRunning = pid => {
  try {
    process.kill(pid, 0)
    return true
  } catch {
    return false
  }
}

const waitForGateway = async (timeoutMs = 10_000) => {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    const connected = await new Promise(resolveConnection => {
      const socket = connect({ host: '127.0.0.1', port: 8765 })
      socket.once('connect', () => {
        socket.destroy()
        resolveConnection(true)
      })
      socket.once('error', () => resolveConnection(false))
    })
    if (connected) return
    await new Promise(resolveDelay => setTimeout(resolveDelay, 100))
  }
  throw new Error('Gateway did not become reachable within 10 seconds')
}

const gatewayLaunch = async () => {
  const release = await verifyRuntimeReleasePointer(layout.activeReleasePointer)
  if (release.gatewayArtifactPath) {
    return {
      release,
      gatewayEntry: release.gatewayArtifactPath,
      cwd: release.releaseRoot,
      args: [release.gatewayArtifactPath],
      bundled: true,
      dependencyMode: 'release-bundled',
    }
  }

  const legacyPackageRoot = resolve(
    release.manifest.repositoryRoot,
    'agent_harness',
    'mcp_gateway_fast_track',
  )
  const gatewayEntry = resolve(legacyPackageRoot, 'src', 'gateway.mjs')
  if (!existsSync(gatewayEntry)) {
    throw new Error(`Legacy active Runtime Gateway source is unavailable: ${gatewayEntry}`)
  }
  const legacyDependenciesReady = [
    resolve(legacyPackageRoot, 'node_modules', '@modelcontextprotocol', 'sdk', 'package.json'),
    resolve(legacyPackageRoot, 'node_modules', 'zod', 'package.json'),
  ].every(existsSync)
  return {
    release,
    gatewayEntry,
    cwd: legacyPackageRoot,
    args: legacyDependenciesReady
      ? [gatewayEntry]
      : [
          '--import',
          pathToFileURL(resolve(packageRoot, 'scripts', 'register-toolchain-loader.mjs')).href,
          gatewayEntry,
        ],
    bundled: false,
    dependencyMode: legacyDependenciesReady ? 'legacy-checkout' : 'shared-toolchain',
  }
}

const start = async () => {
  const launcherProcesses = assertExternalGatewayLauncher()
  mkdirSync(layout.stateRoot, { recursive: true })
  mkdirSync(layout.gatewayTempRoot, { recursive: true })
  mkdirSync(layout.npmCache, { recursive: true })
  mkdirSync(layout.pythonCache, { recursive: true })
  const existing = readExistingPid()
  if (existing?.pid && isRunning(existing.pid)) {
    throw new Error(`Gateway is already running with PID ${existing.pid}`)
  }

  const launch = await gatewayLaunch()
  const stdout = openSync(layout.gatewayStdoutLog, 'a')
  const stderr = openSync(layout.gatewayStderrLog, 'a')
  const child = spawn(process.execPath, launch.args, {
    cwd: launch.cwd,
    detached: true,
    windowsHide: true,
    stdio: ['ignore', stdout, stderr],
    env: {
      ...process.env,
      [ET_HARNESS_ENV_ROOT_VAR]: layout.environmentRoot,
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
  writeFileSync(
    layout.gatewayPidFile,
    `${JSON.stringify({
      pid: child.pid,
      gatewayEntry: launch.gatewayEntry,
      releaseManifestPath: launch.release.manifestPath,
      releaseSchema: launch.release.manifest.schema,
      bundledGateway: launch.bundled,
      dependencyMode: launch.dependencyMode,
      startedAt: new Date().toISOString(),
      launcher: launcherProcesses.map(({ processId, name }) => ({ processId, name })),
    })}\n`,
    'utf8',
  )

  try {
    await waitForGateway()
  } catch (error) {
    if (isRunning(child.pid)) process.kill(child.pid)
    rmSync(layout.gatewayPidFile, { force: true })
    throw error
  }

  process.stdout.write(`${JSON.stringify({
    status: 'STARTED',
    pid: child.pid,
    releaseManifestPath: launch.release.manifestPath,
    bundledGateway: launch.bundled,
    dependencyMode: launch.dependencyMode,
  })}\n`)
}

function readExistingPid() {
  try {
    return JSON.parse(readFileSync(layout.gatewayPidFile, 'utf8'))
  } catch {
    return undefined
  }
}

const readCommandLine = pid => {
  const command = `(Get-CimInstance Win32_Process -Filter \"ProcessId = ${pid}\").CommandLine`
  const result = spawnSync('powershell.exe', ['-NoProfile', '-Command', command], {
    encoding: 'utf8',
    windowsHide: true,
  })
  if (result.status !== 0) throw new Error('Unable to verify the Gateway process command line')
  return result.stdout.trim()
}

const stop = () => {
  const record = readExistingPid()
  if (!record?.pid) {
    process.stdout.write(`${JSON.stringify({ status: 'NOT_RUNNING' })}\n`)
    return
  }
  if (!isRunning(record.pid)) {
    rmSync(layout.gatewayPidFile, { force: true })
    process.stdout.write(`${JSON.stringify({ status: 'STALE_PID_REMOVED' })}\n`)
    return
  }

  const commandLine = readCommandLine(record.pid).toLowerCase()
  if (!record.gatewayEntry || !commandLine.includes(record.gatewayEntry.toLowerCase())) {
    throw new Error(`PID ${record.pid} is not the recorded ET Harness Gateway process`)
  }
  process.kill(record.pid)
  rmSync(layout.gatewayPidFile, { force: true })
  process.stdout.write(`${JSON.stringify({
    status: 'STOPPED',
    pid: record.pid,
    releaseManifestPath: record.releaseManifestPath,
  })}\n`)
}

const action = process.argv[2]
if (action === 'start') await start()
else if (action === 'stop') stop()
else throw new Error('Expected process-control.mjs start|stop')
