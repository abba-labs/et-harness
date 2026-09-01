import { spawn, spawnSync } from 'node:child_process'
import { closeSync, mkdirSync, openSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { connect } from 'node:net'

const scriptDirectory = dirname(fileURLToPath(import.meta.url))
const packageRoot = resolve(scriptDirectory, '..')
const repositoryRoot = resolve(packageRoot, '..', '..')
const environmentRoot = resolve(repositoryRoot, '..', '..')
const stateDirectory = resolve(environmentRoot, 'state', 'pure-mcp-fast-track')
const pidFile = resolve(stateDirectory, 'gateway.pid.json')
const stdoutLog = resolve(stateDirectory, 'gateway.stdout.log')
const stderrLog = resolve(stateDirectory, 'gateway.stderr.log')
const gatewayEntry = resolve(packageRoot, 'src', 'gateway.mjs')

const isRunning = (pid) => {
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
    const connected = await new Promise((resolveConnection) => {
      const socket = connect({ host: '127.0.0.1', port: 8765 })
      socket.once('connect', () => {
        socket.destroy()
        resolveConnection(true)
      })
      socket.once('error', () => resolveConnection(false))
    })
    if (connected) return
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 100))
  }
  throw new Error('Gateway did not become reachable within 10 seconds')
}

const start = async () => {
  mkdirSync(stateDirectory, { recursive: true })
  if (readExistingPid()?.pid && isRunning(readExistingPid().pid)) {
    throw new Error(`Gateway is already running with PID ${readExistingPid().pid}`)
  }

  const stdout = openSync(stdoutLog, 'a')
  const stderr = openSync(stderrLog, 'a')
  const child = spawn(process.execPath, [gatewayEntry], {
    cwd: packageRoot,
    detached: true,
    windowsHide: true,
    stdio: ['ignore', stdout, stderr],
  })
  child.unref()
  closeSync(stdout)
  closeSync(stderr)
  writeFileSync(
    pidFile,
    `${JSON.stringify({ pid: child.pid, gatewayEntry, startedAt: new Date().toISOString() })}\n`,
    'utf8',
  )

  try {
    await waitForGateway()
  } catch (error) {
    if (isRunning(child.pid)) process.kill(child.pid)
    rmSync(pidFile, { force: true })
    throw error
  }

  process.stdout.write(`${JSON.stringify({ status: 'STARTED', pid: child.pid })}\n`)
}

function readExistingPid() {
  try {
    return JSON.parse(readFileSync(pidFile, 'utf8'))
  } catch {
    return undefined
  }
}

const readCommandLine = (pid) => {
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
    rmSync(pidFile, { force: true })
    process.stdout.write(`${JSON.stringify({ status: 'STALE_PID_REMOVED' })}\n`)
    return
  }

  const commandLine = readCommandLine(record.pid).toLowerCase()
  if (!commandLine.includes(gatewayEntry.toLowerCase())) {
    throw new Error(`PID ${record.pid} is not the recorded ET Harness Gateway process`)
  }
  process.kill(record.pid)
  rmSync(pidFile, { force: true })
  process.stdout.write(`${JSON.stringify({ status: 'STOPPED', pid: record.pid })}\n`)
}

const action = process.argv[2]
if (action === 'start') await start()
else if (action === 'stop') stop()
else throw new Error('Expected process-control.mjs start|stop')
