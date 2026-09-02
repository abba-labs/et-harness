import assert from 'node:assert/strict'
import { test } from 'node:test'
import { resolve } from 'node:path'

import {
  environmentLayout,
  resolveEnvironmentRoot,
} from '../scripts/environment-layout.mjs'

test('explicit machine environment root is authoritative and independent of checkout location', () => {
  const root = resolve('D:\\shared-et-harness-env')
  assert.equal(
    resolveEnvironmentRoot({ environmentRoot: root, allowLegacyGatewayConfig: false }),
    root,
  )
  const layout = environmentLayout(root)
  assert.equal(layout.environmentRoot, root)
  assert.equal(layout.activeReleasePointer, resolve(root, 'state', 'pure-mcp-fast-track', 'active-release.json'))
  assert.equal(layout.toolchainsRoot, resolve(root, 'toolchains'))
  assert.equal(layout.nodeExecutable, resolve(root, 'runtimes', 'node-v22.23.2-win-x64', 'node.exe'))
})

test('relative environment roots fail closed instead of being interpreted from the checkout', () => {
  assert.throws(
    () => resolveEnvironmentRoot({ environmentRoot: 'relative-env', allowLegacyGatewayConfig: false }),
    /must be an absolute path/,
  )
})
