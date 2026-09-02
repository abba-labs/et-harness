import assert from 'node:assert/strict'
import { test } from 'node:test'
import { join, resolve } from 'node:path'

import {
  createGovernanceController,
  GatewayGovernanceError,
  selectProjectBinding,
} from '../src/governance.mjs'

const projectRoot = resolve('D:\\projects\\atp')
const projectBinding = {
  projectId: 'et-automated-testing-platform',
  projectRoot,
  allowedWorkspaceRoots: [projectRoot],
}

const renderedContext = [
  '[GOVERNANCE CONTEXT]',
  '',
  '# Context Pack',
  'Project: et-automated-testing-platform',
  '',
  '## [inline] contribution:atp:compiled-task-context-core ATP Compiled Task Context Identity',
  'Provenance: provider://atp',
  '',
  JSON.stringify({ fingerprint: 'context-revision-xbar-01' }),
  '',
  '## [inline] contribution:atp:compiled-task-context-navigation ATP Must-Read And Active Rule Owners',
  'Provenance: provider://atp',
  '',
  JSON.stringify({
    must_read: [{ path: 'AGENTS.md', required: true }],
    rule_owners: [{ owner_id: 'public_ip_semantics', source: 'report/design/rules/R100.md' }],
  }),
  '',
  '## [inline] contribution:atp:scope Project Read / Write Scope Contract',
  'Provenance: provider://atp',
  '',
  'read_scope:',
  '- AGENTS.md',
  'write_scope:',
  '  allowed:',
  '  - test_case_doc/xbar/**',
  '  protected:',
  '  - pc/et_test_platform/core/**',
  '',
  '## [inline] contribution:atp:validation Project Validation Obligations',
  'Provenance: provider://atp',
  '',
  '- task-context-current: Check context. | command=python tools/governance/compile_task_context.py check',
  '- task-write-scope: Check scope. | command=python tools/governance/compile_task_context.py scope-check',
  '',
  'Pending Code Gate Reviews: none prepared for the current epoch.',
].join('\n')

const openTurnResult = () => ({
  runtimeId: 'runtime-01',
  turnId: 'turn-01',
  taskId: 'task-01',
  projectId: 'et-automated-testing-platform',
  context: {
    text: renderedContext,
    route: { ruleIds: ['R010'], gateIds: ['G010'] },
    contextContributions: [{
      providerId: 'project.automated-testing-platform.context',
      contributionId: 'atp-xbar-01',
      fingerprint: 'sha256:contribution-01',
      supervision: { projectRevision: 'revision-atp-01' },
    }],
  },
})

const routeDecision = {
  schema: 'auto-governance.route-decision.v0.1',
  phase: 'analysis',
  queryPreview: 'Analyze XBAR.',
  queryHash: `sha256:${'a'.repeat(64)}`,
  seeds: { architecture: [], rule: [], knowledge: [], gate: [] },
  selected: { architectureIds: [], ruleIds: ['R010'], knowledgeIds: [], gateIds: ['G010'] },
  trace: [{ kind: 'rule', id: 'R010', source: 'semantic-search', depth: 0 }],
  omissions: [],
  contextContributionIds: ['atp-xbar-01'],
}

const memoryStore = () => {
  const values = new Map()
  return {
    get: async (taskId) => values.get(taskId),
    put: async (snapshot) => values.set(snapshot.taskId, snapshot),
  }
}

const fakeRuntime = (overrides = {}) => {
  const calls = { openTurn: 0, getStatus: 0, observeWork: 0, preflightAction: 0, closeTurn: 0 }
  return {
    calls,
    resolveProject: async (workspacePath) => ({
      workspacePath: resolve(workspacePath),
      projectId: 'et-automated-testing-platform',
    }),
    openTurn: async () => {
      calls.openTurn += 1
      return overrides.openTurn ? overrides.openTurn() : openTurnResult()
    },
    getStatus: async () => {
      calls.getStatus += 1
      return {
        autoGovernance: { routeDecision },
        supervision: {
          decision: { status: 'READY_TO_CLOSE' },
          ledger: {
            pendingObligationIds: ['OBL-ATP-READ-001'],
            satisfiedObligationIds: [],
            violatedObligationIds: [],
          },
        },
      }
    },
    observeWork: async (_snapshot, input) => {
      calls.observeWork += 1
      return {
        observation: { observationId: 'observation-01', kind: input.kind.toUpperCase() },
        journal: { status: 'OPEN' },
        knowledgeDecision: { captureMode: 'OPTIONAL', consultMode: 'NONE' },
      }
    },
    preflightAction: async (_snapshot, input) => {
      calls.preflightAction += 1
      return input.effect.kind === 'MUTATION' && input.effect.intent.resourceId === 'resource-protected'
        ? { allowed: false, reason: 'protected resource' }
        : { allowed: true }
    },
    closeTurn: async (_snapshot, input) => {
      calls.closeTurn += 1
      return {
        runtimeId: input.runtimeId,
        taskId: 'task-01',
        turnId: input.turnId,
        reflection: { providerId: 'host-proposal', createdAt: '2026-09-01T00:00:00.000Z' },
        closure: { status: 'COMPLETE', attemptId: 'closure-01' },
        knowledgeDecision: { captureMode: 'OPTIONAL', consultMode: 'NONE' },
        knowledgeVerifications: [],
        knowledgeVerificationWarnings: [],
        knowledgePromotions: [],
        knowledgePromotionWarnings: [],
        supervision: {
          decision: { status: 'COMPLETE' },
          ledger: {
            pendingObligationIds: [],
            satisfiedObligationIds: ['OBL-BASELINE-REFLECTION'],
            violatedObligationIds: [],
          },
        },
      }
    },
  }
}

test('T1 resolves the ATP project root', () => {
  assert.equal(selectProjectBinding(projectRoot, [projectBinding]).projectId, projectBinding.projectId)
})

test('T2 resolves an ATP subdirectory to the same project', () => {
  assert.equal(
    selectProjectBinding(join(projectRoot, 'test_case_doc', 'xbar'), [projectBinding]).projectId,
    projectBinding.projectId,
  )
})

test('T3 fails closed when no configured project matches', () => {
  assert.throws(
    () => selectProjectBinding(resolve('D:\\projects\\other'), [projectBinding]),
    (error) => error instanceof GatewayGovernanceError && error.code === 'PROJECT_NOT_FOUND',
  )
})

test('T4 fails closed when the strongest project match is ambiguous', () => {
  assert.throws(
    () => selectProjectBinding(projectRoot, [
      projectBinding,
      { ...projectBinding, projectId: 'second-project' },
    ]),
    (error) => error instanceof GatewayGovernanceError && error.code === 'PROJECT_AMBIGUOUS',
  )
})

test('T5-T7 begin returns XBAR context, revisions, scope, owners, and validation', async () => {
  const runtime = fakeRuntime()
  const controller = createGovernanceController({
    runtimeAccess: runtime,
    snapshotStore: memoryStore(),
    projects: [projectBinding.projectId],
  })
  const result = await controller.begin({
    workspacePath: projectRoot,
    intent: 'Analyze ET6801 XBAR without modifying files.',
    requestedTaskId: 'xbar-task-01',
  })
  assert.equal(result.projectId, projectBinding.projectId)
  assert.equal(result.projectRevision, 'revision-atp-01')
  assert.equal(result.contextRevision, 'context-revision-xbar-01')
  assert.deepEqual(result.context.mustRead, [{ path: 'AGENTS.md', required: true }])
  assert.equal(result.context.ruleOwners[0].owner_id, 'public_ip_semantics')
  assert.deepEqual(result.context.writeScope.allowed, ['test_case_doc/xbar/**'])
  assert.deepEqual(result.context.writeScope.protected, ['pc/et_test_platform/core/**'])
  assert.equal(result.context.validation.length, 2)
  assert.equal(result.context.contributionReceipts[0].providerId, 'project.automated-testing-platform.context')
  assert.equal(runtime.calls.openTurn, 1)
})

test('T8 contributor failure fails closed and persists no snapshot', async () => {
  const store = memoryStore()
  const controller = createGovernanceController({
    runtimeAccess: fakeRuntime({
      openTurn: () => ({ ...openTurnResult(), context: { text: renderedContext, contextContributions: [] } }),
    }),
    snapshotStore: store,
  })
  await assert.rejects(
    controller.begin({ workspacePath: projectRoot, intent: 'Analyze XBAR.', requestedTaskId: 'xbar-fail' }),
    (error) => error instanceof GatewayGovernanceError && error.code === 'CONTEXT_CONTRIBUTOR_UNAVAILABLE',
  )
  assert.equal(await store.get('xbar-fail'), undefined)
})

test('T9 status reads the existing Runtime state and exposes bounded route decision receipt', async () => {
  const runtime = fakeRuntime()
  const controller = createGovernanceController({ runtimeAccess: runtime, snapshotStore: memoryStore() })
  await controller.begin({ workspacePath: projectRoot, intent: 'Analyze XBAR.', requestedTaskId: 'xbar-status' })
  const status = await controller.status({ taskId: 'xbar-status' })
  assert.equal(status.runtimeDecision, 'READY_TO_CLOSE')
  assert.deepEqual(status.pendingObligationIds, ['OBL-ATP-READ-001'])
  assert.deepEqual(status.routeDecision, routeDecision)
  assert.equal(runtime.calls.getStatus, 1)
})

test('T10 thin wrappers bind task identity and preserve Runtime authority', async () => {
  const runtime = fakeRuntime()
  const controller = createGovernanceController({ runtimeAccess: runtime, snapshotStore: memoryStore() })
  await controller.begin({ workspacePath: projectRoot, intent: 'Analyze XBAR.', requestedTaskId: 'xbar-closed-loop' })

  const observed = await controller.observe({
    taskId: 'xbar-closed-loop',
    kind: 'resource-touch',
    resourceRefs: ['source://xbar/registers'],
    summary: 'Material XBAR source fact.',
  })
  assert.deepEqual(observed, {
    status: 'OBSERVED',
    observationId: 'observation-01',
    observationKind: 'RESOURCE-TOUCH',
    journalStatus: 'OPEN',
    knowledgeCaptureMode: 'OPTIONAL',
    knowledgeConsultationMode: 'NONE',
  })

  const blocked = await controller.preflight({
    taskId: 'xbar-closed-loop',
    name: 'write_file',
    eventRef: 'host-event-01',
    effect: {
      kind: 'MUTATION',
      intent: { resourceId: 'resource-protected', path: 'pc/core.py', action: 'UPDATE' },
    },
  })
  assert.deepEqual(blocked, { status: 'BLOCKED', allowed: false, reason: 'protected resource' })

  const completed = await controller.complete({
    taskId: 'xbar-closed-loop',
    semanticReflection: { contractVersion: '0.1' },
  })
  assert.equal(completed.status, 'COMPLETE')
  assert.equal(completed.knowledge.consultationMode, 'NONE')
  assert.equal(completed.supervision.decision, 'COMPLETE')
  assert.deepEqual(completed.supervision.satisfiedObligationIds, ['OBL-BASELINE-REFLECTION'])
  assert.deepEqual(runtime.calls, {
    openTurn: 1,
    getStatus: 0,
    observeWork: 1,
    preflightAction: 1,
    closeTurn: 1,
  })
})

test('T11 requestedTaskId is idempotent for equal input and conflicts for changed input', async () => {
  const runtime = fakeRuntime()
  const controller = createGovernanceController({ runtimeAccess: runtime, snapshotStore: memoryStore() })
  const input = { workspacePath: projectRoot, intent: 'Analyze XBAR.', requestedTaskId: 'xbar-idempotent' }
  const first = await controller.begin(input)
  const replay = await controller.begin(input)
  assert.equal(first.idempotentReplay, false)
  assert.equal(replay.idempotentReplay, true)
  assert.equal(first.runtimeId, replay.runtimeId)
  assert.equal(runtime.calls.openTurn, 1)
  await assert.rejects(
    controller.begin({ ...input, intent: 'Different XBAR task.' }),
    (error) => error instanceof GatewayGovernanceError && error.code === 'TASK_ID_CONFLICT',
  )
})