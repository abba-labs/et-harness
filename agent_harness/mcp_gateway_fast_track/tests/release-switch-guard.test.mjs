import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  assertGatewayStoppedForReleaseSwitch,
  isProcessRunning,
} from '../scripts/gateway-process-state.mjs'

test('current live process is mechanically recognized', () => {
  assert.equal(isProcessRunning(process.pid), true)
  assert.equal(isProcessRunning(-1), false)
})

test('release switch guard rejects a live Gateway PID and accepts no PID', () => {
  assert.throws(
    () => assertGatewayStoppedForReleaseSwitch({ pid: process.pid }),
    /stop the external Gateway before activation or rollback/,
  )
  assert.doesNotThrow(() => assertGatewayStoppedForReleaseSwitch(undefined))
})
