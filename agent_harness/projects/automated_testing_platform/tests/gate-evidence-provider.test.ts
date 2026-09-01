import { describe, expect, it } from 'vitest'
import type { AtpCompiledTaskContext } from '../src/context-contributor.js'
import {
  ATP_GATE_EVIDENCE_INVOCATION_SCHEMA,
  ATP_GATE_GROUP_TIMEOUT_MS,
  ATP_SCOPE_GATE_CAPABILITY,
  ATP_SCOPE_GATE_PROVIDER_ID,
  ATP_SOFTWARE_GATE_CAPABILITY,
  ATP_SOFTWARE_GATE_PROVIDER_ID,
  atpValidationSpecifications,
  buildAtpValidationReceipt,
  executeAtpGateEvidence,
  matchAtpGateEvidenceInvocation,
  type AtpGateEvidenceInvocationRequestV01,
} from '../src/gate-evidence-provider.js'

const compiled = (): AtpCompiledTaskContext => ({
  schema: 'et.task-context.v1',
  fingerprint: '1'.repeat(64),
  integrity_fingerprint: '2'.repeat(64),
  task: {
    id: 'ATP-GATE-TEST',
    intent: 'Analyze ET6003 dma IP',
    modules: ['ip-package'],
    changes: ['analysis'],
    lanes: [],
    chip: 'et6003',
    ip: 'dma',
  },
  repository: { head: 'fixture-head' },
  source_inputs: [],
  architecture: [],
  must_read: [],
  rule_owners: [],
  write_scope: { allowed: ['test_case_doc/dma/**'], protected: [] },
  validation: [
    'python tools/quality/check_public_ip_contracts.py',
    'python tools/quality/validate_case_plans.py test_case_doc/dma/dma.md',
  ],
})

const request = (
  overrides: Partial<AtpGateEvidenceInvocationRequestV01> = {},
): AtpGateEvidenceInvocationRequestV01 => ({
  schema: ATP_GATE_EVIDENCE_INVOCATION_SCHEMA,
  projectId: 'et-automated-testing-platform',
  taskId: 'ATP-GATE-TEST',
  workspacePath: 'D:\\ATP',
  contextHash: 'a'.repeat(64),
  providerId: ATP_SOFTWARE_GATE_PROVIDER_ID,
  gateId: 'G010.010.030',
  stepId: 'project-software-validation',
  capability: ATP_SOFTWARE_GATE_CAPABILITY,
  command: 'python tools/quality/check_public_ip_contracts.py',
  ...overrides,
})

describe('ATP deterministic Gate Evidence Provider', () => {
  it('matches only an exact current Task Context command and returns the whole Gate group', () => {
    const match = matchAtpGateEvidenceInvocation(compiled(), request())
    expect(match).toMatchObject({
      applicable: true,
      binding: {
        providerId: ATP_SOFTWARE_GATE_PROVIDER_ID,
        gateId: 'G010.010.030',
        validationId: 'project-validation-01',
        gateValidationIds: ['project-validation-01', 'project-validation-02'],
      },
    })

    expect(matchAtpGateEvidenceInvocation(compiled(), request({
      command: 'python tools/quality/check_public_ip_contracts.py --skip',
    }))).toMatchObject({ applicable: false })
    expect(matchAtpGateEvidenceInvocation(compiled(), request({
      providerId: ATP_SCOPE_GATE_PROVIDER_ID,
      capability: ATP_SCOPE_GATE_CAPABILITY,
      gateId: 'G010.010.020',
      stepId: 'scope-check',
    }))).toMatchObject({ applicable: false })
  })

  it('creates PASS only from a durable exact command with structured success', () => {
    const result = buildAtpValidationReceipt(compiled(), request({
      eventRef: 'execution-event://tool-result-1',
      execution: { exitCode: 0 },
      timestamp: '2026-09-01T00:00:00.000Z',
    }))
    expect(result.receipt).toMatchObject({
      providerId: ATP_SOFTWARE_GATE_PROVIDER_ID,
      providerKind: 'VALIDATOR',
      validationId: 'project-validation-01',
      targetIdentity: 'validation:project-validation-01',
      resultStatus: 'PASS',
      evidenceRefs: ['execution-event://tool-result-1'],
      projectRevision: 'fixture-head',
    })
    expect(result.receipt.commandOrTestIdentity).toMatch(/^sha256:[a-f0-9]{64}$/)
  })

  it('fails closed for opaque, failed, or agent-invented results', () => {
    expect(buildAtpValidationReceipt(compiled(), request({
      eventRef: 'execution-event://opaque',
      timestamp: '2026-09-01T00:00:00.000Z',
    })).receipt.resultStatus).toBe('NOT_EXECUTED')
    expect(buildAtpValidationReceipt(compiled(), request({
      eventRef: 'execution-event://failed',
      execution: { exitCode: 1 },
      timestamp: '2026-09-01T00:00:00.000Z',
    })).receipt.resultStatus).toBe('FAIL')
    expect(() => buildAtpValidationReceipt(compiled(), request({
      timestamp: '2026-09-01T00:00:00.000Z',
    }))).toThrow(/durable TOOL_RESULT eventRef/)
  })

  it('keeps validation identities and provider ownership deterministic', () => {
    expect(atpValidationSpecifications(compiled()).map(item => [
      item.validationId,
      item.providerId,
      item.gateId,
    ])).toEqual([
      ['task-context-current', 'project.automated-testing-platform.gate.context', 'G010.010.010'],
      ['task-write-scope', 'project.automated-testing-platform.gate.scope', 'G010.010.020'],
      ['project-validation-01', ATP_SOFTWARE_GATE_PROVIDER_ID, 'G010.010.030'],
      ['project-validation-02', ATP_SOFTWARE_GATE_PROVIDER_ID, 'G010.010.030'],
    ])
  })

  it('executes only the declared provider group and returns mechanical exit facts', async () => {
    const calls: string[] = []
    const result = await executeAtpGateEvidence(compiled(), {
      schema: ATP_GATE_EVIDENCE_INVOCATION_SCHEMA,
      projectId: 'et-automated-testing-platform',
      taskId: 'ATP-GATE-TEST',
      workspacePath: 'D:\\ATP',
      contextHash: 'a'.repeat(64),
      providerId: ATP_SOFTWARE_GATE_PROVIDER_ID,
      gateId: 'G010.010.030',
      stepId: 'project-software-validation',
      capability: ATP_SOFTWARE_GATE_CAPABILITY,
    }, async command => {
      calls.push(command)
      return { exitCode: 0, stdout: `passed ${calls.length}`, stderr: '' }
    })
    expect(calls).toEqual(compiled().validation)
    expect(result.gateValidationIds).toEqual(['project-validation-01', 'project-validation-02'])
    expect(result.executions).toHaveLength(2)
    expect(result.executions[0]).toMatchObject({
      validationId: 'project-validation-01',
      exitCode: 0,
      outputPreview: 'passed 1',
    })
    expect(result.executions[0]?.outputDigest).toMatch(/^sha256:[a-f0-9]{64}$/)
  })

  it('stops a provider group after the first non-zero process exit', async () => {
    let calls = 0
    const result = await executeAtpGateEvidence(compiled(), {
      schema: ATP_GATE_EVIDENCE_INVOCATION_SCHEMA,
      projectId: 'et-automated-testing-platform',
      taskId: 'ATP-GATE-TEST',
      workspacePath: 'D:\\ATP',
      contextHash: 'a'.repeat(64),
      providerId: ATP_SOFTWARE_GATE_PROVIDER_ID,
      gateId: 'G010.010.030',
      stepId: 'project-software-validation',
      capability: ATP_SOFTWARE_GATE_CAPABILITY,
    }, async () => {
      calls += 1
      return { exitCode: 2, stdout: '', stderr: 'failed' }
    })
    expect(calls).toBe(1)
    expect(result.executions).toMatchObject([{
      validationId: 'project-validation-01',
      exitCode: 2,
      outputPreview: 'failed',
    }])
  })

  it('bounds the whole provider group and clips each command to the remaining budget', async () => {
    const timeouts: number[] = []
    const clock = [0, ATP_GATE_GROUP_TIMEOUT_MS - 60_000]
    await executeAtpGateEvidence(compiled(), {
      schema: ATP_GATE_EVIDENCE_INVOCATION_SCHEMA,
      projectId: 'et-automated-testing-platform',
      taskId: 'ATP-GATE-TEST',
      workspacePath: 'D:\\ATP',
      contextHash: 'a'.repeat(64),
      providerId: ATP_SCOPE_GATE_PROVIDER_ID,
      gateId: 'G010.010.020',
      stepId: 'scope-check',
      capability: ATP_SCOPE_GATE_CAPABILITY,
    }, async (_command, _workspacePath, timeoutMs) => {
      timeouts.push(timeoutMs)
      return { exitCode: 0, stdout: 'passed', stderr: '' }
    }, () => clock.shift() ?? ATP_GATE_GROUP_TIMEOUT_MS)
    expect(timeouts).toEqual([60_000])
  })

  it('fails closed before starting another command after the group budget expires', async () => {
    let calls = 0
    await expect(executeAtpGateEvidence(compiled(), {
      schema: ATP_GATE_EVIDENCE_INVOCATION_SCHEMA,
      projectId: 'et-automated-testing-platform',
      taskId: 'ATP-GATE-TEST',
      workspacePath: 'D:\\ATP',
      contextHash: 'a'.repeat(64),
      providerId: ATP_SCOPE_GATE_PROVIDER_ID,
      gateId: 'G010.010.020',
      stepId: 'scope-check',
      capability: ATP_SCOPE_GATE_CAPABILITY,
    }, async () => {
      calls += 1
      return { exitCode: 0, stdout: '', stderr: '' }
    }, (() => {
      const clock = [0, ATP_GATE_GROUP_TIMEOUT_MS]
      return () => clock.shift() ?? ATP_GATE_GROUP_TIMEOUT_MS
    })())).rejects.toThrow(/thirty-minute execution budget/)
    expect(calls).toBe(0)
  })
})
