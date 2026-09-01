import assert from 'node:assert/strict'
import { after, test } from 'node:test'
import { mkdir, mkdtemp, rm } from 'node:fs/promises'
import { join, resolve } from 'node:path'

import {
  environmentRoot,
  repositoryRoot,
} from '../scripts/runtime-bundle-inputs.mjs'
import {
  createFileSnapshotStore,
  createGovernanceController,
} from '../src/governance.mjs'
import { createFrozenRuntimeAccess } from '../src/runtime-release.mjs'

const stateParent = resolve(
  environmentRoot,
  'state',
  'pure-mcp-fast-track',
  'frozen-runtime-wiring-tests',
)
await mkdir(stateParent, { recursive: true })
const stateRoot = await mkdtemp(join(stateParent, 'case-'))
after(async () => rm(stateRoot, { recursive: true, force: true }))

test('real frozen Runtime keeps explicit WRITE_SCOPE preflight truthful under AUDIT', async () => {
  const runtimeAccess = createFrozenRuntimeAccess({
    releasePointerPath: resolve(
      environmentRoot,
      'state',
      'pure-mcp-fast-track',
      'active-release.json',
    ),
  })
  const controller = createGovernanceController({
    runtimeAccess,
    snapshotStore: createFileSnapshotStore(resolve(stateRoot, 'snapshots')),
    projects: ['et-automated-testing-platform'],
  })

  try {
    const begun = await controller.begin({
      workspacePath: repositoryRoot,
      intent: '分析6801芯片etimer这个IP，复核现有两份文档是否仍符合当前项目规则；不要修改PC、Firmware或Harness框架代码。',
      requestedTaskId: 'round3-p0-frozen-runtime-wiring-regression',
    })
    const status = await runtimeAccess.getStatus(begun)
    const allowed = await controller.preflight({
      taskId: begun.taskId,
      name: 'filesystem.create',
      effect: {
        kind: 'MUTATION',
        intent: {
          resourceId: 'test_case_doc/etimer/round3_p0_probe.md',
          path: 'test_case_doc/etimer/round3_p0_probe.md',
          action: 'CREATE',
        },
      },
    })
    const protectedPath = resolve(
      repositoryRoot,
      'pc',
      'et_test_platform',
      'core',
      'forbidden_round3_p0.py',
    )
    const forbidden = await controller.preflight({
      taskId: begun.taskId,
      name: 'filesystem.create',
      effect: {
        kind: 'MUTATION',
        intent: {
          resourceId: 'pc/et_test_platform/core/forbidden_round3_p0.py',
          path: 'pc/et_test_platform/core/forbidden_round3_p0.py',
          action: 'CREATE',
        },
      },
    })

    assert.equal(status.supervision.hostProfile.negotiation.effectiveLevel, 'AUDIT')
    assert.equal(status.supervision.hostProfile.negotiation.claimsMechanicalInterception, false)
    assert.deepEqual(allowed, { status: 'ALLOWED', allowed: true })
    assert.equal(forbidden.status, 'BLOCKED')
    assert.equal(forbidden.allowed, false)
    assert.match(forbidden.reason, /outside the governed WRITE_SCOPE/i)
    await assert.rejects(
      async () => (await import('node:fs/promises')).access(protectedPath),
      { code: 'ENOENT' },
    )
  } finally {
    await runtimeAccess.close()
  }
})
