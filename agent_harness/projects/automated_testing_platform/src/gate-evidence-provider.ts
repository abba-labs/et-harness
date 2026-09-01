import { createHash } from 'node:crypto'
import { exec } from 'node:child_process'
import type {
  EvidenceResultStatus,
  ValidationReceiptV01,
} from '@agent-harness/execution-supervisor'
import type { AtpCompiledTaskContext } from './context-contributor.js'

export const ATP_GATE_EVIDENCE_INVOCATION_SCHEMA =
  'agent-harness.project-gate-evidence-invocation.v0.1' as const
export const ATP_GATE_EVIDENCE_RESULT_SCHEMA =
  'agent-harness.project-gate-evidence-result.v0.1' as const
export const ATP_GATE_COMMAND_TIMEOUT_MS = 5 * 60 * 1_000
export const ATP_GATE_GROUP_TIMEOUT_MS = 30 * 60 * 1_000

export const ATP_CONTEXT_GATE_CAPABILITY = 'governance.context.compile'
export const ATP_SCOPE_GATE_CAPABILITY = 'governance.scope.check'
export const ATP_SOFTWARE_GATE_CAPABILITY = 'validation.software.execute'

export const ATP_CONTEXT_GATE_PROVIDER_ID =
  'project.automated-testing-platform.gate.context'
export const ATP_SCOPE_GATE_PROVIDER_ID =
  'project.automated-testing-platform.gate.scope'
export const ATP_SOFTWARE_GATE_PROVIDER_ID =
  'project.automated-testing-platform.gate.software'

export interface AtpValidationSpecification {
  readonly validationId: string
  readonly command: string
  readonly gateId: string
  readonly stepId: string
  readonly capability: string
  readonly providerId: string
}

export interface AtpGateEvidenceInvocationRequestV01 {
  readonly schema: typeof ATP_GATE_EVIDENCE_INVOCATION_SCHEMA
  readonly projectId: string
  readonly taskId: string
  readonly workspacePath: string
  readonly contextHash: string
  readonly providerId: string
  readonly gateId: string
  readonly stepId: string
  readonly capability: string
  readonly command: string
  readonly eventRef?: string
  readonly execution?: {
    readonly exitCode: number
  }
  readonly timestamp?: string
}

export interface AtpGateEvidenceExecutionRequestV01 {
  readonly schema: typeof ATP_GATE_EVIDENCE_INVOCATION_SCHEMA
  readonly projectId: string
  readonly taskId: string
  readonly workspacePath: string
  readonly contextHash: string
  readonly providerId: string
  readonly gateId: string
  readonly stepId: string
  readonly capability: string
}

export interface AtpGateEvidenceExecutionFactV01 {
  readonly validationId: string
  readonly command: string
  readonly commandIdentity: string
  readonly exitCode: number
  readonly outputDigest: string
  readonly outputPreview: string
  readonly startedAt: string
  readonly completedAt: string
}

export interface AtpGateEvidenceExecutionResultV01 {
  readonly schema: typeof ATP_GATE_EVIDENCE_RESULT_SCHEMA
  readonly applicable: true
  readonly gateValidationIds: readonly string[]
  readonly executions: readonly AtpGateEvidenceExecutionFactV01[]
}

export interface AtpCommandExecutionV01 {
  readonly exitCode: number
  readonly stdout: string
  readonly stderr: string
}

export type AtpCommandExecutorV01 = (
  command: string,
  workspacePath: string,
  timeoutMs: number,
) => Promise<AtpCommandExecutionV01>

export interface AtpGateEvidenceBindingV01 {
  readonly providerId: string
  readonly gateId: string
  readonly stepId: string
  readonly capability: string
  readonly validationId: string
  readonly gateValidationIds: readonly string[]
  readonly commandIdentity: string
}

export type AtpGateEvidenceMatchResultV01 =
  | {
      readonly schema: typeof ATP_GATE_EVIDENCE_RESULT_SCHEMA
      readonly applicable: false
      readonly reason: string
    }
  | {
      readonly schema: typeof ATP_GATE_EVIDENCE_RESULT_SCHEMA
      readonly applicable: true
      readonly binding: AtpGateEvidenceBindingV01
    }

export interface AtpValidationReceiptResultV01 {
  readonly schema: typeof ATP_GATE_EVIDENCE_RESULT_SCHEMA
  readonly applicable: true
  readonly binding: AtpGateEvidenceBindingV01
  readonly receipt: ValidationReceiptV01
}

const sha256 = (value: string): string =>
  createHash('sha256').update(value).digest('hex')

const recordOf = (value: unknown): Record<string, unknown> | undefined =>
  value && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : undefined

const canonicalTimestamp = (value: string | undefined): string => {
  if (!value || new Date(value).toISOString() !== value) {
    throw new Error('ATP Gate Evidence timestamp must be canonical ISO-8601')
  }
  return value
}

const resultStatus = (
  execution: AtpGateEvidenceInvocationRequestV01['execution'],
): EvidenceResultStatus => execution ? (execution.exitCode === 0 ? 'PASS' : 'FAIL') : 'NOT_EXECUTED'

const executeDeclaredCommand: AtpCommandExecutorV01 = (
  command,
  workspacePath,
  timeoutMs,
) => new Promise((resolveExecution, rejectExecution) => {
  exec(command, {
    cwd: workspacePath,
    env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' },
    maxBuffer: 4 * 1024 * 1024,
    timeout: timeoutMs,
    windowsHide: true,
  }, (error, stdout, stderr) => {
    if (!error) {
      resolveExecution({ exitCode: 0, stdout, stderr })
      return
    }
    const code = (error as NodeJS.ErrnoException & { killed?: boolean }).code
    if (typeof code !== 'number' || (error as { killed?: boolean }).killed) {
      rejectExecution(new Error(`ATP Gate command did not produce a process exit code: ${error.message}`))
      return
    }
    resolveExecution({ exitCode: code, stdout, stderr })
  })
})

const outputPreview = (stdout: string, stderr: string): string =>
  [stdout.trim(), stderr.trim()].filter(Boolean).join('\n').slice(0, 4_000)

export const atpValidationSpecifications = (
  compiled: AtpCompiledTaskContext,
): readonly AtpValidationSpecification[] => [
  {
    validationId: 'task-context-current',
    command: 'python tools/governance/compile_task_context.py check --context project-governance/runtime/current_task_context.json',
    gateId: 'G010.010.010',
    stepId: 'compile-context',
    capability: ATP_CONTEXT_GATE_CAPABILITY,
    providerId: ATP_CONTEXT_GATE_PROVIDER_ID,
  },
  {
    validationId: 'task-write-scope',
    command: 'python tools/governance/compile_task_context.py scope-check --context project-governance/runtime/current_task_context.json',
    gateId: 'G010.010.020',
    stepId: 'scope-check',
    capability: ATP_SCOPE_GATE_CAPABILITY,
    providerId: ATP_SCOPE_GATE_PROVIDER_ID,
  },
  ...compiled.validation.map((command, index) => ({
    validationId: `project-validation-${String(index + 1).padStart(2, '0')}`,
    command,
    gateId: 'G010.010.030',
    stepId: 'project-software-validation',
    capability: ATP_SOFTWARE_GATE_CAPABILITY,
    providerId: ATP_SOFTWARE_GATE_PROVIDER_ID,
  })),
]

export const matchAtpGateEvidenceInvocation = (
  compiled: AtpCompiledTaskContext,
  request: AtpGateEvidenceInvocationRequestV01,
): AtpGateEvidenceMatchResultV01 => {
  if (request.schema !== ATP_GATE_EVIDENCE_INVOCATION_SCHEMA) {
    throw new Error(`Unsupported ATP Gate Evidence request schema: ${request.schema}`)
  }
  const command = request.command.trim()
  if (!command) {
    return {
      schema: ATP_GATE_EVIDENCE_RESULT_SCHEMA,
      applicable: false,
      reason: 'The invocation does not contain a canonical command.',
    }
  }
  const specifications = atpValidationSpecifications(compiled)
  const matched = specifications.find(item =>
    item.command === command
      && item.providerId === request.providerId
      && item.gateId === request.gateId
      && item.stepId === request.stepId
      && item.capability === request.capability,
  )
  if (!matched) {
    return {
      schema: ATP_GATE_EVIDENCE_RESULT_SCHEMA,
      applicable: false,
      reason: 'The command does not exactly match this Gate provider and current Task Context.',
    }
  }
  return {
    schema: ATP_GATE_EVIDENCE_RESULT_SCHEMA,
    applicable: true,
    binding: {
      providerId: matched.providerId,
      gateId: matched.gateId,
      stepId: matched.stepId,
      capability: matched.capability,
      validationId: matched.validationId,
      gateValidationIds: specifications
        .filter(item => item.gateId === matched.gateId)
        .map(item => item.validationId),
      commandIdentity: `sha256:${sha256(matched.command)}`,
    },
  }
}

export const buildAtpValidationReceipt = (
  compiled: AtpCompiledTaskContext,
  request: AtpGateEvidenceInvocationRequestV01,
): AtpValidationReceiptResultV01 => {
  const match = matchAtpGateEvidenceInvocation(compiled, request)
  if (!match.applicable) throw new Error(match.reason)
  if (!/^[a-f0-9]{64}$/.test(request.contextHash)) {
    throw new Error('ATP Gate Evidence contextHash must be a SHA-256 value')
  }
  if (!request.eventRef?.trim()) {
    throw new Error('ATP Gate Evidence requires the durable TOOL_RESULT eventRef')
  }
  const repository = recordOf(compiled.repository)
  const revision = typeof repository?.head === 'string' && repository.head.trim()
    ? repository.head.trim()
    : undefined
  return {
    schema: ATP_GATE_EVIDENCE_RESULT_SCHEMA,
    applicable: true,
    binding: match.binding,
    receipt: {
      providerId: match.binding.providerId,
      providerKind: 'VALIDATOR',
      validationId: match.binding.validationId,
      commandOrTestIdentity: match.binding.commandIdentity,
      ...(revision ? { projectRevision: revision } : {}),
      contextHash: request.contextHash,
      targetIdentity: `validation:${match.binding.validationId}`,
      resultStatus: resultStatus(request.execution),
      artifactRefs: [],
      evidenceRefs: [request.eventRef],
      claimRefs: [`gate://${match.binding.gateId}/${match.binding.stepId}`],
      timestamp: canonicalTimestamp(request.timestamp),
    },
  }
}

export const executeAtpGateEvidence = async (
  compiled: AtpCompiledTaskContext,
  request: AtpGateEvidenceExecutionRequestV01,
  executor: AtpCommandExecutorV01 = executeDeclaredCommand,
  now: () => number = Date.now,
): Promise<AtpGateEvidenceExecutionResultV01> => {
  if (request.schema !== ATP_GATE_EVIDENCE_INVOCATION_SCHEMA) {
    throw new Error(`Unsupported ATP Gate execution request schema: ${request.schema}`)
  }
  if (!/^[a-f0-9]{64}$/.test(request.contextHash)) {
    throw new Error('ATP Gate execution contextHash must be a SHA-256 value')
  }
  const specifications = atpValidationSpecifications(compiled).filter(item =>
    item.providerId === request.providerId
      && item.gateId === request.gateId
      && item.stepId === request.stepId
      && item.capability === request.capability,
  )
  if (specifications.length === 0) {
    throw new Error('ATP Gate execution does not match a current Task Context provider group')
  }
  const deadline = now() + ATP_GATE_GROUP_TIMEOUT_MS
  const executions: AtpGateEvidenceExecutionFactV01[] = []
  for (const specification of specifications) {
    const remainingMs = deadline - now()
    if (remainingMs <= 0) {
      throw new Error('ATP Gate provider group exceeded its thirty-minute execution budget')
    }
    const startedAt = new Date().toISOString()
    const result = await executor(
      specification.command,
      request.workspacePath,
      Math.min(ATP_GATE_COMMAND_TIMEOUT_MS, remainingMs),
    )
    const completedAt = new Date().toISOString()
    const output = `${result.stdout}\0${result.stderr}`
    executions.push({
      validationId: specification.validationId,
      command: specification.command,
      commandIdentity: `sha256:${sha256(specification.command)}`,
      exitCode: result.exitCode,
      outputDigest: `sha256:${sha256(output)}`,
      outputPreview: outputPreview(result.stdout, result.stderr),
      startedAt,
      completedAt,
    })
    if (result.exitCode !== 0) break
  }
  return {
    schema: ATP_GATE_EVIDENCE_RESULT_SCHEMA,
    applicable: true,
    gateValidationIds: specifications.map(item => item.validationId),
    executions,
  }
}
