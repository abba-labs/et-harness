import assert from 'node:assert/strict'
import { test } from 'node:test'

import { createFreshCompletionGovernance } from '../src/gateway.mjs'
import { GatewayGovernanceError } from '../src/governance.mjs'

const harness = ({ runtimeDecision, checkpointStatus = 'CHECKPOINTED' }) => {
  const calls = { status: 0, checkpoint: 0, complete: 0 }
  const admitted = {
    health: () => ({}),
    begin: async () => ({}),
    status: async () => {
      calls.status += 1
      return { runtimeDecision }
    },
    observe: async () => ({}),
    preflight: async () => ({}),
    complete: async () => {
      calls.complete += 1
      return { status: 'COMPLETE', closure: { attemptId: 'closure-1' } }
    },
  }
  const trusted = {
    readRequired: async () => ({}),
    checkpoint: async () => {
      calls.checkpoint += 1
      return {
        status: checkpointStatus,
        ...(checkpointStatus === 'CHECKPOINTED' ? {} : { reason: 'validator reported FAIL' }),
      }
    },
  }
  return {
    calls,
    governance: createFreshCompletionGovernance(admitted, trusted),
  }
}

test('first completion runs a fresh checkpoint before Runtime closure', async () => {
  const { calls, governance } = harness({ runtimeDecision: 'READY_TO_CLOSE' })
  const result = await governance.complete({ taskId: 'TASK-1' })
  assert.equal(result.status, 'COMPLETE')
  assert.deepEqual(calls, { status: 1, checkpoint: 1, complete: 1 })
})

test('failed fresh validation blocks closure without calling Runtime complete', async () => {
  const { calls, governance } = harness({
    runtimeDecision: 'READY_TO_CLOSE',
    checkpointStatus: 'FAILED',
  })
  await assert.rejects(
    governance.complete({ taskId: 'TASK-1' }),
    (error) => error instanceof GatewayGovernanceError
      && error.code === 'VALIDATION_NOT_CURRENT'
      && /validator reported FAIL/.test(error.message),
  )
  assert.deepEqual(calls, { status: 1, checkpoint: 1, complete: 0 })
})

test('closed completion replay skips validation and returns durable Runtime result', async () => {
  const { calls, governance } = harness({ runtimeDecision: 'COMPLETE' })
  const result = await governance.complete({ taskId: 'TASK-1' })
  assert.equal(result.status, 'COMPLETE')
  assert.deepEqual(calls, { status: 1, checkpoint: 0, complete: 1 })
})
