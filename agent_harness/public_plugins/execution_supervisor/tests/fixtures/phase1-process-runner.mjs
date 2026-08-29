import { spawnSync } from 'node:child_process'
import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'

const repositoryRoot = resolve(import.meta.dirname, '../../../../..')
const tempRoot = resolve(
  process.env.PHASE1_PROCESS_TMP_ROOT
    ?? resolve(repositoryRoot, '.tmp/phase1-cross-process'),
)
const logRoot = resolve(
  process.env.PHASE1_PROCESS_LOG_ROOT
    ?? resolve(repositoryRoot, '.phase1-process-logs'),
)
const worker = resolve(import.meta.dirname, 'phase1-process-worker.mjs')

await mkdir(tempRoot, { recursive: true })
const runDirectory = await mkdtemp(resolve(tempRoot, 'run-'))
const storeDirectory = resolve(runDirectory, 'store')
const transcripts = []

const runWorker = (mode, cursor) => {
  const args = [worker, mode, storeDirectory]
  if (cursor !== undefined) args.push(JSON.stringify(cursor))
  const result = spawnSync(process.execPath, args, {
    encoding: 'utf8',
    windowsHide: true,
  })
  const transcript = {
    mode,
    status: result.status,
    signal: result.signal,
    stdout: result.stdout,
    stderr: result.stderr,
    error: result.error?.stack ?? result.error?.message,
  }
  transcripts.push(transcript)
  if (result.status !== 0) {
    throw new Error(`Independent ${mode} process failed: ${JSON.stringify(transcript)}`)
  }
  return JSON.parse(result.stdout)
}

try {
  const created = runWorker('create')
  const continued = runWorker('continue', created.cursor)
  const replayed = runWorker('replay', created.cursor)
  if (
    created.cursor?.sequence !== 2
    || !/^[0-9a-f]{64}$/.test(created.cursor?.stateHash ?? '')
    || JSON.stringify(continued.beforeCursor) !== JSON.stringify(created.cursor)
    || continued.cursor?.sequence !== 3
  ) {
    throw new Error('Independent process handoff cursors were not 2 then 3')
  }
  if (
    replayed.eventCount !== 3
    || JSON.stringify(replayed.afterCursor) !== JSON.stringify(created.cursor)
    || JSON.stringify(replayed.sequences) !== JSON.stringify([3])
    || JSON.stringify(replayed.cursor) !== JSON.stringify(continued.cursor)
    || replayed.runtimeId !== 'runtime-synthetic'
    || replayed.turnId !== 'turn-synthetic'
  ) {
    throw new Error(`Independent replay reconstruction mismatch: ${JSON.stringify(replayed)}`)
  }
  await rm(runDirectory, { recursive: true, force: true })
  process.stdout.write('PHASE1_CROSS_PROCESS_PASS\n')
} catch (error) {
  await mkdir(logRoot, { recursive: true })
  const logPath = resolve(logRoot, `phase1-cross-process-${Date.now()}.json`)
  await writeFile(logPath, `${JSON.stringify({
    capturedAt: new Date().toISOString(),
    node: process.version,
    platform: process.platform,
    architecture: process.arch,
    runDirectory,
    error: error instanceof Error ? error.stack : String(error),
    transcripts,
  }, null, 2)}\n`, 'utf8')
  process.stderr.write(`PHASE1_CROSS_PROCESS_FAIL log=${logPath}\n`)
  process.exitCode = 1
}
