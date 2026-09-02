import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { test } from 'node:test'

import { createTrustedCheckpointController } from '../src/trusted-checkpoint.mjs'

const snapshotName = (taskId) => `${createHash('sha256').update(taskId).digest('hex')}.json`

const supervisedStatus = (taskId, obligationState) => ({
  supervision: {
    decision: {
      status: obligationState === 'VIOLATED' ? 'FAILED' : 'READY_TO_CLOSE',
    },
    ledger: {
      binding: {
        requestId: 'request-validation-replay',
        contract: {
          projectId: 'project-1',
          taskId,
          agentId: 'agent-1',
          contextHash: `sha256:${'a'.repeat(64)}`,
          obligations: [{
            id: 'OBL-VALIDATE',
            kind: 'VALIDATION',
            target: {
              validationId: 'validate-current-output',
              targetIdentity: 'output://current',
            },
          }],
          evidencePolicies: [{
            obligationIds: ['OBL-VALIDATE'],
            acceptedProviderIds: ['et-harness'],
            acceptedProviderKinds: ['VALIDATOR'],
          }],
        },
      },
      pendingObligationIds: [],
      satisfiedObligationIds: obligationState === 'SATISFIED' ? ['OBL-VALIDATE'] : [],
      violatedObligationIds: obligationState === 'VIOLATED' ? ['OBL-VALIDATE'] : [],
    },
  },
})

test('explicit checkpoints rerun frozen validation after prior PASS and prior FAIL', async () => {
  const root = await mkdtemp(join(tmpdir(), 'et-harness-checkpoint-'))
  try {
    const taskId = 'TASK-VALIDATION-REPLAY'
    const snapshot = {
      taskId,
      runtimeId: 'runtime-validation-replay',
      turnId: 'turn-validation-replay',
      workspacePath: root,
      projectId: 'project-1',
      context: {
        validation: [{
          id: 'validate-current-output',
          command: `node -e "require('node:fs').appendFileSync('validation-runs.txt','x')"`,
        }],
      },
    }
    await writeFile(join(root, snapshotName(taskId)), `${JSON.stringify(snapshot)}\n`, 'utf8')

    let state = 'SATISFIED'
    const accepted = (eventRef) => ({
      eventRef,
      acceptance: { status: 'ACCEPTED' },
    })
    const runtimeAccess = {
      getStatus: async () => supervisedStatus(taskId, state),
      ingest: async (_snapshot, input) => accepted(`event://${input.eventId}`),
      ingestTrustedValidationSpan: async (_snapshot, input) => ({
        request: accepted(`event://${input.requestEventId}`),
        validation: accepted(`event://${input.validationEventId}`),
        response: accepted(`event://${input.responseEventId}`),
      }),
    }
    const controller = createTrustedCheckpointController({
      runtimeAccess,
      taskSnapshotRoot: root,
    })

    const afterSatisfied = await controller.checkpoint({ taskId })
    assert.equal(afterSatisfied.status, 'CHECKPOINTED')
    assert.equal(afterSatisfied.validations.length, 1)
    assert.equal(afterSatisfied.validations[0].obligationId, 'OBL-VALIDATE')

    state = 'VIOLATED'
    const afterViolated = await controller.checkpoint({ taskId })
    assert.equal(afterViolated.status, 'CHECKPOINTED')
    assert.equal(afterViolated.validations.length, 1)
    assert.equal(await readFile(join(root, 'validation-runs.txt'), 'utf8'), 'xx')
  } finally {
    await rm(root, { recursive: true, force: true })
  }
})
