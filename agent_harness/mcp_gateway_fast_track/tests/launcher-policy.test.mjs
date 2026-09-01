import assert from 'node:assert/strict'
import { test } from 'node:test'

import { findForbiddenLauncher } from '../scripts/launcher-policy.mjs'

test('launcher policy accepts an independent Explorer or terminal ancestry', () => {
  assert.equal(
    findForbiddenLauncher([
      { name: 'node.exe', commandLine: 'node scripts/process-control.mjs start' },
      { name: 'cmd.exe', commandLine: 'cmd.exe /c start-et-harness-gateway.cmd' },
      { name: 'explorer.exe', commandLine: 'C:\\Windows\\explorer.exe' },
    ]),
    undefined,
  )
})

test('launcher policy rejects Codex Desktop and Codex-owned integrations', () => {
  for (const processInfo of [
    { name: 'codex.exe', commandLine: 'codex.exe app-server' },
    { name: 'ChatGPT.exe', commandLine: 'OpenAI Codex Desktop' },
    { name: 'node.exe', commandLine: 'C:\\Users\\admin\\.codex\\plugins\\gateway.mjs' },
    { name: 'node.exe', commandLine: 'C:\\integration\\hooks\\start.mjs' },
    { name: 'node.exe', commandLine: 'C:\\integration\\marketplace\\start.mjs' },
  ]) {
    assert.equal(findForbiddenLauncher([processInfo]), processInfo)
  }
})
