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

test('toolchain identity ignores worktree line-ending conversion', () => {
  const common = {
    nodeVersion: 'v22.23.2',
    platform: 'win32',
    arch: 'x64',
  }
  const lf = computeToolchainDescriptor({
    ...common,
    packageJsonBytes: Buffer.from('{\n  "name": "fixture"\n}\n'),
    packageLockBytes: Buffer.from('{\n  "lockfileVersion": 3\n}\n'),
  })
  const crlf = computeToolchainDescriptor({
    ...common,
    packageJsonBytes: Buffer.from('{\r\n  "name": "fixture"\r\n}\r\n'),
    packageLockBytes: Buffer.from('{\r\n  "lockfileVersion": 3\r\n}\r\n'),
  })
  assert.equal(lf.packageJsonSha256, crlf.packageJsonSha256)
  assert.equal(lf.packageLockSha256, crlf.packageLockSha256)
  assert.equal(lf.toolchainId, crlf.toolchainId)
})
