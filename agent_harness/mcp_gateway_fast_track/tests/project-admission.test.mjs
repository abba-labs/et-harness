import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  canonicalTaskText,
  createProjectAdmissionController,
  normalizeTaskIntent,
  projectSelectorMatches,
} from '../src/project-admission.mjs'

const bootstrap = Object.freeze({
  schema: 'et-harness.project-bootstrap.v0.1',
  projectId: 'et-automated-testing-platform',
  displayName: 'ET Automated Testing Platform',
  aliases: ['ATP', '自动化测试平台'],
  fingerprint: 'sha256:architecture-v1',
  architecture: {
    standard: 'architecture-v0.1',
    roots: [{ id: 'A010', title: 'Project Governance Projection', children: [] }],
  },
})

const taskIntent = {
  schema: 'et-harness.task-intent.v0.1',
  taskType: 'IP_ANALYSIS',
  objective: 'Analyze ET6801 ETIMER IP',
  entities: [
    { kind: 'chip', id: 'ET6801' },
    { kind: 'ip', id: 'ETIMER' },
  ],
}

test('Project Admission accepts exact project aliases and refuses guessed names', () => {
  assert.equal(projectSelectorMatches(bootstrap, 'ATP'), true)
  assert.equal(projectSelectorMatches(bootstrap, 'et-automated-testing-platform'), true)
  assert.equal(projectSelectorMatches(bootstrap, 'APT'), false)
})

test('TaskIntent canonicalization puts Agent-understood entities before human prose', () => {
  const text = canonicalTaskText(
    taskIntent,
    'ATP项目：分析 ET6801 ETIMER 这个 IP and SDK contract',
  )
  const after = /(?:^|[^a-z0-9])ip\s*(?:[:=\-]|of)?\s*([a-z][a-z0-9_-]{0,63})/gi
  const candidates = [...text.toLowerCase().matchAll(after)].map(match => match[1])
  assert.equal(candidates[0], 'etimer')
  assert.match(text, /^Task type: IP_ANALYSIS/m)
  assert.match(text, /^Entities: chip=ET6801; ip=ETIMER$/m)
})

test('New project context is forced through Architecture bootstrap before Runtime opens', async () => {
  let openCount = 0
  let bootstrapCount = 0
  const baseGovernance = {
    health: () => ({ runtimeConnected: false }),
    begin: async (input) => {
      openCount += 1
      return { status: 'ACTIVE', taskId: input.requestedTaskId, intent: input.intent }
    },
  }
  const runtimeAccess = {
    projectBootstrap: async () => {
      bootstrapCount += 1
      return bootstrap
    },
  }
  const controller = createProjectAdmissionController({ baseGovernance, runtimeAccess })

  const first = await controller.begin({
    workspacePath: 'D:/projects/atp',
    project: 'ATP',
    intent: '分析 ET6801 ETIMER 这个 IP',
    requestedTaskId: 'task-1',
  })
  assert.equal(first.status, 'PROJECT_CONTEXT_REQUIRED')
  assert.equal(first.projectContextFingerprint, bootstrap.fingerprint)
  assert.equal(first.architectureBootstrap.roots[0].id, 'A010')
  assert.equal(openCount, 0)
  assert.equal(bootstrapCount, 1)

  const second = await controller.begin({
    workspacePath: 'D:/projects/atp',
    project: 'ATP',
    intent: '分析 ET6801 ETIMER 这个 IP',
    requestedTaskId: 'task-1',
    projectContextFingerprint: bootstrap.fingerprint,
  })
  assert.equal(second.status, 'TASK_INTENT_REQUIRED')
  assert.equal(openCount, 0)
  assert.equal(bootstrapCount, 1)

  const third = await controller.begin({
    workspacePath: 'D:/projects/atp',
    project: 'ATP',
    intent: '分析 ET6801 ETIMER 这个 IP',
    requestedTaskId: 'task-1',
    projectContextFingerprint: bootstrap.fingerprint,
    taskIntent,
  })
  assert.equal(third.status, 'ACTIVE')
  assert.equal(third.projectContextFingerprint, bootstrap.fingerprint)
  assert.equal(third.taskIntent.taskType, 'IP_ANALYSIS')
  assert.match(third.intent, /ip=ETIMER/)
  assert.equal(openCount, 1)
  assert.equal(bootstrapCount, 1)
})

test('Stale project context fingerprint refreshes Architecture without opening Runtime', async () => {
  let openCount = 0
  let bootstrapCount = 0
  const controller = createProjectAdmissionController({
    baseGovernance: {
      begin: async () => {
        openCount += 1
        return {}
      },
    },
    runtimeAccess: {
      projectBootstrap: async () => {
        bootstrapCount += 1
        return bootstrap
      },
    },
  })
  const result = await controller.begin({
    workspacePath: 'D:/projects/atp',
    project: 'ATP',
    intent: '分析 ETIMER',
    requestedTaskId: 'task-2',
    projectContextFingerprint: 'sha256:stale',
    taskIntent,
  })
  assert.equal(result.status, 'PROJECT_CONTEXT_REQUIRED')
  assert.equal(openCount, 0)
  assert.equal(bootstrapCount, 1)
})

test('TaskIntent validation remains bounded and project-agnostic', () => {
  const normalized = normalizeTaskIntent(taskIntent)
  assert.deepEqual(normalized.entities, taskIntent.entities)
  assert.throws(() => normalizeTaskIntent({ ...taskIntent, taskType: 'bad type with spaces' }))
})
