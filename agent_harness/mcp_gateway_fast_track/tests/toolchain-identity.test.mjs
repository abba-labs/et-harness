import assert from 'node:assert/strict'
import { test } from 'node:test'

import { computeToolchainDescriptor } from '../scripts/toolchain.mjs'

test('toolchain identity depends on pinned content and platform, not checkout path', () => {
  const input = {
    packageJsonBytes: Buffer.from('{"name":"fixture"}'),
    packageLockBytes: Buffer.from('{"lockfileVersion":3}'),
    nodeVersion: 'v22.23.2',
    platform: 'win32',
    arch: 'x64',
  }
  const left = computeToolchainDescriptor(input)
  const right = computeToolchainDescriptor({ ...input })
  assert.equal(left.toolchainId, right.toolchainId)
})

test('toolchain identity changes when dependency lock content changes', () => {
  const common = {
    packageJsonBytes: Buffer.from('{"name":"fixture"}'),
    nodeVersion: 'v22.23.2',
    platform: 'win32',
    arch: 'x64',
  }
  const first = computeToolchainDescriptor({
    ...common,
    packageLockBytes: Buffer.from('{"lockfileVersion":3,"revision":1}'),
  })
  const second = computeToolchainDescriptor({
    ...common,
    packageLockBytes: Buffer.from('{"lockfileVersion":3,"revision":2}'),
  })
  assert.notEqual(first.toolchainId, second.toolchainId)
})
