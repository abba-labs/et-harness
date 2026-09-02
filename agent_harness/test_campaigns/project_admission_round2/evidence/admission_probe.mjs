import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import {
  createProjectAdmissionController,
} from '../../../mcp_gateway_fast_track/src/project-admission.mjs'
import {
  buildProjectBootstrap,
} from '../../../mcp_gateway_fast_track/src/project-bootstrap.ts'

const TESTED_SHA = '2bf842597415ef235d52fc213c197e50ac2cb89e'
const EVIDENCE_FILE = 'agent_harness/test_campaigns/project_admission_round2/evidence/raw_test_results.jsonl'
const workspacePath = resolve('.')
const projectManifestPath = resolve(
  'agent_harness/projects/automated_testing_platform/project.yaml',
)
const architecturePath = resolve(
  'agent_harness/projects/automated_testing_platform/architecture/010_project_governance_map.md',
)
const projectManifest = readFileSync(projectManifestPath, 'utf8')
const architectureSource = readFileSync(architecturePath, 'utf8')

assert.match(projectManifest, /id:\s*et-automated-testing-platform/)
assert.match(projectManifest, /name:\s*ET Automated Testing Platform/)
assert.match(projectManifest, /-\s*ATP/)
assert.match(architectureSource, /\[A010\.020\.010\]\s*Analysis And Contract/)

const bootstrapFor = (titleSuffix = '') => buildProjectBootstrap({
  projectId: 'et-automated-testing-platform',
  displayName: 'ET Automated Testing Platform',
  aliases: ['automated-testing-platform', 'automated_testing_platform', 'ATP', '自动化测试平台'],
  resources: { architecture: 'agent_harness/projects/automated_testing_platform/architecture/' },
  resourceStandards: { architecture: 'architecture-v0.1' },
}, {
  listFiles: () => [{
    id: 'A010',
    file: '010_project_governance_map.md',
    title: `Project Governance Projection${titleSuffix}`,
    summary: 'Actual ATP Architecture file used by the admission probe.',
    aliases: ['project-governance'],
  }],
  getNode: (_projectId, nodeId) => nodeId === 'A010'
    ? { node: {
        id: 'A010',
        title: `Project Governance Projection${titleSuffix}`,
        resources: [architecturePath],
        relations: ['A010.020.010'],
      } }
    : undefined,
  listChildren: () => [{
    id: 'A010.020.010',
    title: `Analysis And Contract${titleSuffix}`,
    resources: [architecturePath],
    relations: [],
  }],
})

const bootstrapV1 = bootstrapFor()
const bootstrapV2 = bootstrapFor(' v2')

const taskIntent = (ip, objective = `Analyze ET6801 ${ip} IP`) => ({
  schema: 'et-harness.task-intent.v0.1',
  taskType: 'IP_ANALYSIS',
  objective,
  entities: [
    { kind: 'chip', id: 'ET6801' },
    { kind: 'ip', id: ip },
  ],
  constraints: ['Architecture route A010.020.010'],
})

const instrumentedController = initialBootstrap => {
  const counts = {
    bootstrapReads: 0,
    governanceBegin: 0,
    runtimeTurns: 0,
    ledgerCreations: 0,
    eventStoreCreations: 0,
  }
  let current = initialBootstrap
  let canonicalIntent
  const controller = createProjectAdmissionController({
    baseGovernance: {
      begin: async input => {
        counts.governanceBegin += 1
        counts.runtimeTurns += 1
        counts.ledgerCreations += 1
        counts.eventStoreCreations += 1
        canonicalIntent = input.intent
        return {
          status: 'ACTIVE',
          runtimeId: `instrumented-runtime-${counts.runtimeTurns}`,
          turnId: `instrumented-turn-${counts.runtimeTurns}`,
          taskId: input.requestedTaskId,
          intent: input.intent,
        }
      },
    },
    runtimeAccess: {
      projectBootstrap: async () => {
        counts.bootstrapReads += 1
        return current
      },
    },
  })
  return {
    controller,
    counts,
    canonical: () => canonicalIntent,
    setBootstrap: value => { current = value },
  }
}

const errorDecision = async operation => {
  try {
    await operation()
    return { code: 'NO_ERROR', message: 'operation unexpectedly succeeded' }
  } catch (error) {
    return { code: error?.code ?? error?.name ?? 'ERROR', message: String(error?.message ?? error) }
  }
}

const candidateRegex = /(?:^|[^a-z0-9])ip\s*(?:[:=\-]|of)?\s*([a-z][a-z0-9_-]{0,63})/gi
const firstIpCandidate = text => [...text.toLowerCase().matchAll(candidateRegex)][0]?.[1]

const results = []
const record = result => {
  results.push({ testedSha: TESTED_SHA, evidenceFile: EVIDENCE_FILE, ...result })
}

{
  const probe = instrumentedController(bootstrapV1)
  const actual = await probe.controller.begin({
    workspacePath,
    project: 'ET Automated Testing Platform',
    intent: '项目：ET Automated Testing Platform，帮我分析SRPWM这个ip。',
    requestedTaskId: 'pa2-a01',
  })
  assert.equal(actual.status, 'PROJECT_CONTEXT_REQUIRED')
  assert.equal(actual.architectureBootstrap.roots[0].children[0].id, 'A010.020.010')
  assert.equal(probe.counts.runtimeTurns, 0)
  assert.equal(probe.counts.ledgerCreations, 0)
  assert.equal(probe.counts.eventStoreCreations, 0)
  record({
    testId: 'PA2-A01',
    inputStimulus: 'Exact project; SRPWM human intent; fingerprint absent',
    expectedTrigger: ['Project Admission', 'Project Bootstrap'],
    actualTriggeredModule: ['Project Admission', 'instrumented current Project Bootstrap'],
    actualDecision: actual.status,
    architectureBootstrap: actual.architectureBootstrap.roots[0].children[0],
    runtimeTurnCreated: probe.counts.runtimeTurns,
    ledgerChanges: probe.counts.ledgerCreations,
    eventStoreChanges: probe.counts.eventStoreCreations,
    result: 'PASS',
    firstFailingBoundary: null,
    defectAttribution: null,
  })
}

{
  const probe = instrumentedController(bootstrapV1)
  const actual = await errorDecision(() => probe.controller.begin({
    workspacePath,
    intent: '分析 SRPWM',
    requestedTaskId: 'pa2-a02',
  }))
  assert.equal(actual.code, 'INVALID_ARGUMENT')
  assert.equal(probe.counts.bootstrapReads, 0)
  assert.equal(probe.counts.runtimeTurns, 0)
  record({
    testId: 'PA2-A02',
    inputStimulus: 'Human project declaration missing',
    expectedTrigger: ['Project Admission input validation'],
    actualTriggeredModule: ['Project Admission input validation'],
    actualDecision: actual,
    runtimeTurnCreated: 0,
    ledgerChanges: 0,
    eventStoreChanges: 0,
    result: 'PASS',
    firstFailingBoundary: null,
    defectAttribution: null,
  })
}

{
  const probe = instrumentedController(bootstrapV1)
  const actual = await errorDecision(() => probe.controller.begin({
    workspacePath,
    project: 'APT',
    intent: '分析 SRPWM',
    requestedTaskId: 'pa2-a03',
  }))
  assert.equal(actual.code, 'PROJECT_DECLARATION_MISMATCH')
  assert.equal(probe.counts.runtimeTurns, 0)
  record({
    testId: 'PA2-A03',
    inputStimulus: 'Wrong/guessed project APT',
    expectedTrigger: ['Project Admission', 'Project selector'],
    actualTriggeredModule: ['Project Admission', 'instrumented current Project Bootstrap', 'Project selector'],
    actualDecision: actual,
    runtimeTurnCreated: 0,
    ledgerChanges: 0,
    eventStoreChanges: 0,
    result: 'PASS',
    firstFailingBoundary: null,
    defectAttribution: null,
  })
}

{
  const probe = instrumentedController(bootstrapV1)
  const actual = await probe.controller.begin({
    workspacePath,
    project: 'ATP',
    intent: '分析 ET6801 ETIMER',
    requestedTaskId: 'pa2-a04',
    projectContextFingerprint: 'sha256:unknown',
    taskIntent: taskIntent('ETIMER'),
  })
  assert.equal(actual.status, 'PROJECT_CONTEXT_REQUIRED')
  assert.equal(probe.counts.runtimeTurns, 0)
  record({
    testId: 'PA2-A04',
    inputStimulus: 'Unknown fingerprint plus valid TaskIntent',
    expectedTrigger: ['Project Admission', 'current Project Bootstrap'],
    actualTriggeredModule: ['Project Admission', 'instrumented current Project Bootstrap'],
    actualDecision: actual.status,
    returnedFingerprint: actual.projectContextFingerprint,
    runtimeTurnCreated: 0,
    ledgerChanges: 0,
    eventStoreChanges: 0,
    result: 'PASS',
    firstFailingBoundary: null,
    defectAttribution: null,
  })
}

{
  const probe = instrumentedController(bootstrapV1)
  const first = await probe.controller.begin({
    workspacePath,
    project: 'ATP',
    intent: '分析 ET6801 ETIMER',
    requestedTaskId: 'pa2-a05',
  })
  probe.setBootstrap(bootstrapV2)
  const stale = await probe.controller.begin({
    workspacePath,
    project: 'ATP',
    intent: '分析 ET6801 ETIMER',
    requestedTaskId: 'pa2-a05',
    projectContextFingerprint: first.projectContextFingerprint,
    taskIntent: taskIntent('ETIMER'),
  })
  assert.equal(stale.status, 'PROJECT_CONTEXT_REQUIRED')
  assert.equal(stale.projectContextFingerprint, bootstrapV2.fingerprint)
  assert.equal(stale.architectureBootstrap.roots[0].title, 'Project Governance Projection v2')
  assert.equal(probe.counts.bootstrapReads, 2)
  assert.equal(probe.counts.runtimeTurns, 0)
  record({
    testId: 'PA2-A05',
    inputStimulus: 'Same controller: bootstrap v1, Architecture changes to v2, submit old v1 fingerprint',
    expectedTrigger: ['Project Admission', 'fresh Project Bootstrap v2'],
    actualTriggeredModule: ['Project Admission', 'instrumented current Project Bootstrap v2'],
    actualDecision: stale.status,
    oldFingerprint: first.projectContextFingerprint,
    returnedCurrentFingerprint: stale.projectContextFingerprint,
    bootstrapReads: probe.counts.bootstrapReads,
    runtimeTurnCreated: 0,
    ledgerChanges: 0,
    eventStoreChanges: 0,
    result: 'PASS',
    firstFailingBoundary: null,
    defectAttribution: null,
  })

  const fresh = await probe.controller.begin({
    workspacePath,
    project: 'ATP',
    intent: '分析 ET6801 ETIMER',
    requestedTaskId: 'pa2-a05',
    projectContextFingerprint: bootstrapV2.fingerprint,
    taskIntent: taskIntent('ETIMER'),
  })
  assert.equal(fresh.status, 'ACTIVE')
  assert.equal(probe.counts.bootstrapReads, 3)
  assert.equal(probe.counts.runtimeTurns, 1)
  record({
    testId: 'PA2-A08',
    inputStimulus: 'Current v2 fingerprint plus valid ETIMER TaskIntent',
    expectedTrigger: ['Project Admission', 'fresh Project Bootstrap v2', 'TaskIntent canonicalization', 'original Governance begin'],
    actualTriggeredModule: ['Project Admission', 'instrumented current Project Bootstrap v2', 'TaskIntent canonicalization', 'instrumented downstream Governance boundary'],
    actualDecision: fresh.status,
    canonicalIntent: probe.canonical(),
    bootstrapReads: probe.counts.bootstrapReads,
    runtimeTurnCreated: 1,
    ledgerChanges: 1,
    eventStoreChanges: 1,
    stateCountQualification: 'Instrumented downstream boundary counts only; not real Runtime/Ledger/Event Store evidence.',
    result: 'PASS',
    firstFailingBoundary: null,
    defectAttribution: null,
  })
}

{
  const probe = instrumentedController(bootstrapV1)
  const actual = await probe.controller.begin({
    workspacePath,
    project: 'ATP',
    intent: '分析 SRPWM',
    requestedTaskId: 'pa2-a06',
    projectContextFingerprint: bootstrapV1.fingerprint,
  })
  assert.equal(actual.status, 'TASK_INTENT_REQUIRED')
  assert.equal(probe.counts.runtimeTurns, 0)
  record({
    testId: 'PA2-A06',
    inputStimulus: 'Current fingerprint; TaskIntent absent',
    expectedTrigger: ['Project Admission', 'current Project Bootstrap'],
    actualTriggeredModule: ['Project Admission', 'instrumented current Project Bootstrap'],
    actualDecision: actual.status,
    runtimeTurnCreated: 0,
    ledgerChanges: 0,
    eventStoreChanges: 0,
    result: 'PASS',
    firstFailingBoundary: null,
    defectAttribution: null,
  })
}

{
  const probe = instrumentedController(bootstrapV1)
  const actual = await errorDecision(() => probe.controller.begin({
    workspacePath,
    project: 'ATP',
    intent: '分析 SRPWM',
    requestedTaskId: 'pa2-a07',
    projectContextFingerprint: bootstrapV1.fingerprint,
    taskIntent: { ...taskIntent('SRPWM'), taskType: 'bad type with spaces' },
  }))
  assert.equal(actual.code, 'INVALID_ARGUMENT')
  assert.equal(probe.counts.runtimeTurns, 0)
  record({
    testId: 'PA2-A07',
    inputStimulus: 'Current fingerprint; malformed TaskIntent.taskType',
    expectedTrigger: ['Project Admission', 'TaskIntent structural validation'],
    actualTriggeredModule: ['Project Admission', 'instrumented current Project Bootstrap', 'TaskIntent structural validation'],
    actualDecision: actual,
    runtimeTurnCreated: 0,
    ledgerChanges: 0,
    eventStoreChanges: 0,
    result: 'PASS',
    firstFailingBoundary: null,
    defectAttribution: null,
  })
}

const naturalCases = [
  {
    testId: 'PA2-NL01',
    ip: 'ETIMER',
    human: 'Analyze ET6801 ETIMER IP and SDK contract; compare register behavior and document unknowns.',
  },
  {
    testId: 'PA2-NL02',
    ip: 'XBAR',
    human: '项目：ET Automated Testing Platform，请分析 ET6801 XBAR IP 的寄存器、路由关系和测试边界。',
  },
  {
    testId: 'PA2-NL03',
    ip: 'SRPWM',
    human: '项目：ET Automated Testing Platform，帮我分析SRPWM这个ip。',
  },
  {
    testId: 'PA2-NL04',
    ip: 'SRPWM',
    human: 'For the ET Automated Testing Platform project, please perform a bounded ET6801 SRPWM IP and SDK analysis, reconcile the public IP contract with chip adaptation facts, identify registers, interrupts, clock/reset dependencies, unknowns and validation obligations, but do not modify firmware, framework, environment or dependencies.',
  },
]

for (const entry of naturalCases) {
  const probe = instrumentedController(bootstrapV1)
  const bootstrapStage = await probe.controller.begin({
    workspacePath,
    project: 'ET Automated Testing Platform',
    intent: entry.human,
    requestedTaskId: entry.testId.toLowerCase(),
  })
  assert.equal(bootstrapStage.status, 'PROJECT_CONTEXT_REQUIRED')
  assert.equal(probe.counts.runtimeTurns, 0)
  const actual = await probe.controller.begin({
    workspacePath,
    project: 'ET Automated Testing Platform',
    intent: entry.human,
    requestedTaskId: entry.testId.toLowerCase(),
    projectContextFingerprint: bootstrapStage.projectContextFingerprint,
    taskIntent: taskIntent(entry.ip, `Analyze ET6801 ${entry.ip} IP`),
  })
  const candidate = firstIpCandidate(probe.canonical())
  assert.equal(actual.status, 'ACTIVE')
  assert.equal(candidate, entry.ip.toLowerCase())
  assert.notEqual(candidate, 'and')
  assert.equal(probe.counts.runtimeTurns, 1)
  record({
    testId: entry.testId,
    inputStimulus: entry.human,
    expectedTrigger: ['Project Admission', 'Project Bootstrap', 'Agent TaskIntent', 'canonicalization', 'original Governance begin'],
    actualTriggeredModule: ['Project Admission', 'instrumented current Project Bootstrap', 'TaskIntent canonicalization', 'instrumented downstream Governance boundary'],
    actualDecision: actual.status,
    bootstrapDecisionBeforeTaskIntent: bootstrapStage.status,
    canonicalIntent: probe.canonical(),
    firstIpCandidate: candidate,
    runtimeTurnCreated: 1,
    ledgerChanges: 1,
    eventStoreChanges: 1,
    stateCountQualification: 'Instrumented downstream boundary counts only; not real Runtime/Ledger/Event Store evidence.',
    result: 'PASS',
    firstFailingBoundary: null,
    defectAttribution: null,
  })
}

for (const result of results) {
  process.stdout.write(`${JSON.stringify(result)}\n`)
}
