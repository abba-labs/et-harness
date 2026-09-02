import { existsSync, readFileSync } from 'node:fs'

import { layout } from './environment-layout.mjs'

export const isProcessRunning = pid => {
  if (!Number.isInteger(pid) || pid <= 0) return false
  try {
    process.kill(pid, 0)
    return true
  } catch {
    return false
  }
}

export const readGatewayPidRecord = () => {
  if (!existsSync(layout.gatewayPidFile)) return undefined
  try {
    return JSON.parse(readFileSync(layout.gatewayPidFile, 'utf8'))
  } catch {
    throw new Error(`Gateway PID record is invalid: ${layout.gatewayPidFile}`)
  }
}

export const assertGatewayStoppedForReleaseSwitch = (record = readGatewayPidRecord()) => {
  if (record?.pid && isProcessRunning(record.pid)) {
    throw new Error(
      `ET Harness Gateway PID ${record.pid} is still running; stop the external Gateway before activation or rollback`,
    )
  }
}
