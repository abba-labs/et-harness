import { createHash, randomUUID } from 'node:crypto'
import { mkdirSync, renameSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import type {
  GovernanceRuntimeService,
  GovernanceTurnObservation,
} from '@agent-harness/governance-runtime'
import type { AgentGovernanceKernelService } from '@agent-harness/agent-governance-kernel'
import type {
  GenericModelClient,
  GenericModelGenerateRequest,
  GenericModelGenerateResponse,
} from '@agent-harness/generic-model-adapter'

export interface AuditedModelCall {
  readonly sequence: number
  readonly purpose: 'WORK' | 'GOVERNANCE_REFLECTION'
  readonly requestId: string
  readonly status: 'OK' | 'FAILED'
  readonly providerId?: string
  readonly modelId?: string
  readonly durationMs: number
  readonly error?: string
}

export class AuditedModelClient implements GenericModelClient {
  readonly clientId: string
  readonly calls: AuditedModelCall[] = []

  constructor(
    private readonly inner: GenericModelClient,
    private readonly redactError: (error: unknown) => string = error =>
      error instanceof Error ? error.message : String(error),
  ) {
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
        error: this.redactError(error),
      })
      throw error
    }
  }
}

const sha256 = (value: string): string =>
  createHash('sha256').update(value).digest('hex')

const observationAudit = (item: GovernanceTurnObservation) => ({
  observationId: item.observationId,
  observationRef: item.observationRef,
  kind: item.kind,
  charCount: item.text.length,
  textSha256: sha256(item.text),
  refs: [...item.refs],
  truncated: item.truncated,
  ...(item.sourceName ? { sourceName: item.sourceName } : {}),
  ...(item.isError !== undefined ? { isError: item.isError } : {}),
})

export interface RealProviderAuditInput {
  readonly lane: 'synthetic' | 'et-tool'
  readonly runId: string
  readonly runtimeId: string
  readonly turnId: string
  readonly taskText: string
  readonly provider: {
    readonly baseOrigin: string
    readonly apiStyle: string
    readonly configuredModel: string
    readonly configuredProviderId: string
  }
  readonly modelClient: AuditedModelClient
  readonly runtime: GovernanceRuntimeService
  readonly kernel: AgentGovernanceKernelService
  readonly visibleOutput?: string
  readonly error?: unknown
}

export interface RealProviderAuditResult {
  readonly pass: boolean
  readonly blockingReasons: readonly string[]
  readonly receipt: Readonly<Record<string, unknown>>
}

export function buildRealProviderAudit(input: RealProviderAuditInput): RealProviderAuditResult {
  const expectedProjectId = input.lane === 'et-tool' ? 'et-tool' : 'synthetic-level2c'
  const status = input.runtime.getStatus(input.runtimeId)
  const taskId = status?.taskId
  const journal = taskId ? input.kernel.getTurn(taskId, input.turnId) : undefined
  const reflection = taskId ? input.kernel.getReflection(taskId, input.turnId) : undefined
  const closure = taskId ? input.kernel.getClosureReceipt(taskId, input.turnId) : undefined
  const observations = taskId
    ? input.runtime.getTurnObservations(input.runtimeId, input.turnId)
    : []
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
  const receipts = closure?.moduleReceipts ?? []
  const receiptById = new Map(receipts.map(item => [item.moduleId, item]))
  const blockingReasons: string[] = []

  if (input.modelClient.calls.length !== 2) {
    blockingReasons.push(`expected exactly 2 model calls, got ${input.modelClient.calls.length}`)
  } else {
    if (input.modelClient.calls[0]?.purpose !== 'WORK') blockingReasons.push('first model call was not WORK')
    if (input.modelClient.calls[1]?.purpose !== 'GOVERNANCE_REFLECTION') {
      blockingReasons.push('second model call was not GOVERNANCE_REFLECTION')
    }
    if (input.modelClient.calls.some(call => call.status !== 'OK')) blockingReasons.push('one or more model calls failed')
  }

  if (!input.visibleOutput?.trim()) blockingReasons.push('model visible output is empty')
  if (status?.projectId !== expectedProjectId) {
    blockingReasons.push(`runtime project is ${status?.projectId ?? 'missing'}, expected ${expectedProjectId}`)
  }
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
  if (!taskObservation) {
    blockingReasons.push('TASK_INPUT observation is missing')
  } else if (taskObservation.text !== input.taskText) {
    blockingReasons.push('TASK_INPUT observation does not exactly match the original business task')
  }
  if (!assistantObservation) {
    blockingReasons.push('ASSISTANT_MESSAGE observation is missing')
  } else if (input.visibleOutput !== undefined && assistantObservation.text !== input.visibleOutput) {
    blockingReasons.push('ASSISTANT_MESSAGE observation does not exactly match visible model output')
  }

  const knowledgeScope = reflection?.result.knowledge.scopeDecision
  if (!knowledgeScope || !['NONE', 'PROJECT', 'PUBLIC', 'BOTH'].includes(knowledgeScope)) {
    blockingReasons.push('Knowledge scope classification is missing or invalid')
  }
  if (closure?.status !== 'COMPLETE') blockingReasons.push(`Closure status is ${closure?.status ?? 'missing'}`)
  for (const moduleId of mandatoryIds) {
    const receipt = receiptById.get(moduleId)
    if (!receipt) {
      blockingReasons.push(`mandatory Closure receipt missing: ${moduleId}`)
      continue
    }
    if (receipt.status !== 'APPLIED' && receipt.status !== 'NO_CHANGE') {
      blockingReasons.push(`mandatory Closure ${moduleId} is ${receipt.status}`)
    }
  }
  if (journal?.projectBinding.kind !== 'BOUND' || journal.projectBinding.projectId !== expectedProjectId) {
    const actual = journal?.projectBinding.kind === 'BOUND'
      ? journal.projectBinding.projectId
      : journal?.projectBinding.kind ?? 'missing'
    blockingReasons.push(`Journal project binding is ${actual}, expected BOUND:${expectedProjectId}`)
  }
  if (journal?.status !== 'CLOSED') blockingReasons.push(`Journal status is ${journal?.status ?? 'missing'}`)
  if (input.error) blockingReasons.push(`pilot error: ${input.error instanceof Error ? input.error.message : String(input.error)}`)

  const pass = blockingReasons.length === 0
  const receipt: Readonly<Record<string, unknown>> = {
    auditVersion: '0.1',
    runId: input.runId,
    lane: input.lane,
    createdAt: new Date().toISOString(),
    provider: input.provider,
    task: {
      charCount: input.taskText.length,
      sha256: sha256(input.taskText),
    },
    modelCalls: input.modelClient.calls,
    visibleOutput: input.visibleOutput
      ? { charCount: input.visibleOutput.length, sha256: sha256(input.visibleOutput) }
      : null,
    route: route ?? null,
    observations: observations.map(observationAudit),
    reflection: reflection ? {
      reflectionRef: journal?.reflectionRef ?? null,
      scopes: {
        knowledge: reflection.result.knowledge.scopeDecision,
        experience: reflection.result.experience.scopeDecision,
        architecture: reflection.result.architecture.scopeDecision,
        rules: reflection.result.rules.scopeDecision,
        evidence: reflection.result.evidence.scopeDecision,
      },
      candidateCounts: {
        knowledge: reflection.result.knowledge.candidates.length,
        experience: reflection.result.experience.candidates.length,
        architecture: reflection.result.architecture.candidates.length,
        rules: reflection.result.rules.candidates.length,
        evidence: reflection.result.evidence.candidates.length,
      },
    } : null,
    closure: closure ? {
      status: closure.status,
      receiptRef: journal?.closureReceiptRef ?? null,
      moduleReceipts: closure.moduleReceipts.map(item => ({
        moduleId: item.moduleId,
        status: item.status,
        writeCount: item.writes.length,
        candidateRefCount: item.candidateRefs.length,
        evidenceRefCount: item.evidenceRefs.length,
        ...(item.reason ? { reason: item.reason } : {}),
      })),
      blockingReasons: [...closure.blockingReasons],
    } : null,
    journal: journal ? {
      taskId: journal.taskId,
      turnId: journal.turnId,
      projectBinding: journal.projectBinding,
      status: journal.status,
      closureAttemptCount: journal.closureAttemptCount,
    } : null,
    pass,
    blockingReasons,
  }
  return { pass, blockingReasons, receipt }
}

export function writeRealProviderAudit(
  root: string,
  runId: string,
  receipt: Readonly<Record<string, unknown>>,
): { readonly file: string; readonly latest: string } {
  mkdirSync(root, { recursive: true })
  const file = join(root, `${runId}.json`)
  const latest = join(root, 'latest.json')
  const text = `${JSON.stringify(receipt, null, 2)}\n`
  for (const target of [file, latest]) {
    mkdirSync(dirname(target), { recursive: true })
    const temp = `${target}.${process.pid}.${randomUUID()}.tmp`
    writeFileSync(temp, text, 'utf8')
    renameSync(temp, target)
  }
  return { file, latest }
}
