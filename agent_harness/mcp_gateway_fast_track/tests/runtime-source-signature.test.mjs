import assert from 'node:assert/strict'
import { test } from 'node:test'

import { canonicalRuntimeSourceBytes } from '../scripts/runtime-bundle-inputs.mjs'

test('Runtime source identity ignores worktree line-ending conversion', () => {
  const lf = canonicalRuntimeSourceBytes(Buffer.from('first\nsecond\n'))
  const crlf = canonicalRuntimeSourceBytes(Buffer.from('first\r\nsecond\r\n'))
  assert.deepEqual(lf, crlf)
})
