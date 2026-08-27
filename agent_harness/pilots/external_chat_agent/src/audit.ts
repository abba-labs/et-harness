import { createHash, randomUUID } from 'node:crypto'
import { dirname, join } from 'node:path'
import { mkdirSync, renameSync, writeFileSync } from 'node:fs'
import type {
  GenericModelClient,
  GenericModelGenerateRequest,
  GenericModelGenerateResponse,
} from '@agent-harness/generic-model-adapter'
import type { GovernanceRuntimeService } from '@agent-harness/governance-runtime'
import type { AgentGovernanceKernelService } from '@agent-harness/agent-governance-kernel'

export interface AuditedExternalAgentCall {
  readonly sequence: number
  readonly purpose: 'WORK' | 'GOVERNANCE_REFLECTION'
  readonly requestId: string
  readonly status: 'OK' | 'FAILED'
  readonly providerId?: string
  readonly modelId?: string
  readonly durationMs: number
  readonly error?: string
}

export class AuditedExternalAgentClient implements GenericModelClient {
  readonly clientId: string
  readonly calls: AuditedExternalAgentCall[] = []

  constructor(private readonly inner: GenericModelClient) {
    this.clientId = inner.clientId
  }

  async generate(request: GenericModelGenerateRequest): Promise<GenericModelGenerateResponse> {
    const started = Date.now()
    try {
      const response = await this.inner.generate(request)
      this.calls.push({
        sequence: this.calls.length + 1,
        purpose: request.purpose,
        requestId: request.requestId,
        status: 'OK',
        ...(response.providerId ? { providerId: response.providerId } : {}),
        ...(response.modelId ? { modelId: response.modelId } : {}),
        durationMs: Date.now() - started,
      })
      return response
    } catch (error) {
      this.calls.push({
        sequence: this.calls.length + 1,
        purpose: request.purpose,
        requestId: request.requestId,
        status: 'FAILED',
        durationMs: Date.now() - started,
        error: error instanceof Error ? error.message : String(error),
      })
      throw error
    }
  }
}

const sha256 = (value: string): string => createHash('sha256').update(value).digest('hex')

export interface ExternalChatAuditInput {
  readonly runId: string
  readonly runtimeId: string
  readonly turnId: string
  readonly taskText: string
  readonly visibleOutput?: string
  readonly modelClient: AuditedExternalAgentClient
  readonly runtime: GovernanceRuntimeService
  readonly kernel: AgentGovernanceKernelService
  readonly error?: unknown
}

export function buildExternalChatAudit(input: ExternalChatAuditInput): {
  readonly pass: boolean
  readonly blockingReasons: readonly string[]
  readonly receipt: Readonly<Record<string, unknown>>
} {
  const expectedProjectId = 'et-tool'
  const status = input.runtime.getStatus(input.runtimeId)
  const taskId = status?.taskId
  const journal = taskId ? input.kernel.getTurn(taskId, input.turnId) : undefined
  const reflection = taskId ? input.kernel.getReflection(taskId, input.turnId) : undefined
  const closure = taskId ? input.kernel.getClosureReceipt(taskId, input.turnId) : undefined
  const observations = taskId ? input.runtime.getTurnObservations(input.runtimeId, input.turnId) : []
  const route = status?.autoGovernance.route
  const mandatoryIds = [
    'context-closure',
    'knowledge-closure',
    'experience-memory-closure',
    'architecture-closure',
    'rules-closure',
    'evidence-state-closure',
    'working-set-closure',
    'obligation-gate-reconcile',
  ]
  const receiptById = new Map((closure?.moduleReceipts ?? []).map(item => [item.moduleId, item]))
  const blockingReasons: string[] = []

  if (input.modelClient.calls.length !== 2) {
    blockingReasons.push(`expected exactly 2 external-Agent calls, got ${input.modelClient.calls.length}`)
  } else {
    if (input.modelClient.calls[0]?.purpose !== 'WORK') blockingReasons.push('first external-Agent call was not WORK')
    if (input.modelClient.calls[1]?.purpose !== 'GOVERNANCE_REFLECTION') {
      blockingReasons.push('second external-Agent call was not GOVERNANCE_REFLECTION')
    }
    if (input.modelClient.calls.some(call => call.status !== 'OK')) blockingReasons.push('one or more external-Agent calls failed')
  }

  if (!input.visibleOutput?.trim()) blockingReasons.push('external Agent visible output is empty')
  if (status?.projectId !== expectedProjectId) blockingReasons.push(`runtime project is ${status?.projectId ?? 'missing'}, expected et-tool`)
  if (!route) {
    blockingReasons.push('automatic governance route is missing')
  } else {
    if (route.architectureIds.length === 0) blockingReasons.push('Architecture routing returned zero candidates')
    if (route.ruleIds.length === 0) blockingReasons.push('Rule routing returned zero candidates')
    if (route.knowledgeIds.length === 0) blockingReasons.push('Knowledge routing returned zero candidates')
    if (route.gateIds.length === 0) blockingReasons.push('Gate routing returned zero candidates')
  }

  const taskObservation = observations.find(item => item.kind === 'TASK_INPUT')
  const assistantObservation = observations.find(item => item.kind === 'ASSISTANT_MESSAGE')
  if (!taskObservation || taskObservation.text !== input.taskText) blockingReasons.push('TASK_INPUT observation is missing or changed')
  if (!assistantObservation || assistantObservation.text !== input.visibleOutput) blockingReasons.push('ASSISTANT_MESSAGE observation is missing or changed')

  const knowledgeScope = reflection?.result.knowledge.scopeDecision
  if (!knowledgeScope || !['NONE', 'PROJECT', 'PUBLIC', 'BOTH'].includes(knowledgeScope)) {
    blockingReasons.push('Knowledge scope classification is missing or invalid')
  }

  if (closure?.status !== 'COMPLETE') blockingReasons.push(`Closure status is ${closure?.status ?? 'missing'}`)
  for (const moduleId of mandatoryIds) {
    const receipt = receiptById.get(moduleId)
    if (!receipt) blockingReasons.push(`mandatory Closure receipt missing: ${moduleId}`)
    else if (receipt.status !== 'APPLIED' && receipt.status !== 'NO_CHANGE') {
      blockingReasons.push(`mandatory Closure ${moduleId} is ${receipt.status}`)
    }
  }

  if (journal?.projectBinding.kind !== 'BOUND' || journal.projectBinding.projectId !== expectedProjectId) {
    blockingReasons.push('Kernel Journal is not BOUND:et-tool')
  }
  if (journal?.status !== 'CLOSED') blockingReasons.push(`Journal status is ${journal?.status ?? 'missing'}`)
  if (input.error) blockingReasons.push(`pilot error: ${input.error instanceof Error ? input.error.message : String(input.error)}`)

  const pass = blockingReasons.length === 0
  return {
    pass,
    blockingReasons,
    receipt: {
      auditVersion: 'external-chat-agent-v0.1',
      runId: input.runId,
      createdAt: new Date().toISOString(),
      task: { charCount: input.taskText.length, sha256: sha256(input.taskText) },
      externalAgentCalls: input.modelClient.calls,
      route: route ?? null,
      observationKinds: observations.map(item => item.kind),
      reflectionScopes: reflection ? {
        knowledge: reflection.result.knowledge.scopeDecision,
        experience: reflection.result.experience.scopeDecision,
        architecture: reflection.result.architecture.scopeDecision,
        rules: reflection.result.rules.scopeDecision,
        evidence: reflection.result.evidence.scopeDecision,
      } : null,
      closure: closure ? {
        status: closure.status,
        moduleReceipts: closure.moduleReceipts.map(item => ({ moduleId: item.moduleId, status: item.status })),
      } : null,
      journal: journal ? { projectBinding: journal.projectBinding, status: journal.status } : null,
      visibleOutput: input.visibleOutput ? { charCount: input.visibleOutput.length, sha256: sha256(input.visibleOutput) } : null,
      pass,
      blockingReasons,
    },
  }
}

export function writeExternalChatAudit(root: string, runId: string, receipt: Readonly<Record<string, unknown>>): {
  readonly file: string
  readonly latest: string
} {
  mkdirSync(root, { recursive: true })
  const text = `${JSON.stringify(receipt, null, 2)}\n`
  const file = join(root, `${runId}.json`)
  const latest = join(root, 'latest.json')
  for (const target of [file, latest]) {
    mkdirSync(dirname(target), { recursive: true })
    const temp = `${target}.${process.pid}.${randomUUID()}.tmp`
    writeFileSync(temp, text, 'utf8')
    renameSync(temp, target)
  }
  return { file, latest }
}
