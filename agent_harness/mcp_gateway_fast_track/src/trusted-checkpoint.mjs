import { exec } from 'node:child_process'
import { createHash, randomUUID } from 'node:crypto'
import { readFile, realpath, stat } from 'node:fs/promises'
import { isAbsolute, relative, resolve } from 'node:path'

import { z } from 'zod'

import { GatewayGovernanceError } from './governance.mjs'

const TRUSTED_PROVIDER_ID = 'et-harness'
const TRUSTED_HOST_ID = 'pure-mcp-local'
const TRUSTED_MODEL_ID = 'runtime-checkpoint'
const EXTERNAL_REQUEST_SCHEMA = 'agent-harness.external-agent-request.v0.1'
const EXTERNAL_RESPONSE_SCHEMA = 'agent-harness.external-agent-response.v0.1'
const MAX_TASK_ID_CHARS = 160
const MAX_RESOURCE_REF_CHARS = 2_048
const MAX_REQUIRED_READ_BYTES = 256 * 1024
const MAX_COMMAND_CHARS = 8_000
const MAX_COMMAND_OUTPUT_BYTES = 2 * 1024 * 1024
const MAX_COMMAND_PREVIEW_CHARS = 4_000
const COMMAND_TIMEOUT_MS = 5 * 60 * 1_000

const hash = (value) => createHash('sha256').update(value).digest('hex')
const slash = (value) => value.replaceAll('\\', '/')

const unsupportedCanonicalValue = (value) => {
  const tag = Object.prototype.toString.call(value)
  throw new TypeError(`Value is not canonical JSON: ${tag}`)
}

const canonicalize = (value, active) => {
  if (value === null) return 'null'
  if (typeof value === 'string') return JSON.stringify(value)
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return unsupportedCanonicalValue(value)
    return Object.is(value, -0) ? '0' : JSON.stringify(value)
  }
  if (typeof value !== 'object') return unsupportedCanonicalValue(value)
  if (active.has(value)) throw new TypeError('Value is not canonical JSON: cycle')
  active.add(value)
  try {
    if (Array.isArray(value)) {
      return `[${value.map((item) => canonicalize(item, active)).join(',')}]`
    }
    const prototype = Object.getPrototypeOf(value)
    if (prototype !== Object.prototype && prototype !== null) {
      return unsupportedCanonicalValue(value)
    }
    const keys = Object.keys(value).sort()
    return `{${keys.map((key) => {
      const item = value[key]
      if (item === undefined) return unsupportedCanonicalValue(item)
      return `${JSON.stringify(key)}:${canonicalize(item, active)}`
    }).join(',')}}`
  } finally {
    active.delete(value)
  }
}

const hashCanonical = (value) => hash(canonicalize(value, new Set()))

const requireString = (label, value, maxChars) => {
  if (typeof value !== 'string' || !value.trim()) {
    throw new GatewayGovernanceError('INVALID_ARGUMENT', `${label} is required`)
  }
  const normalized = value.trim()
  if (normalized.length > maxChars) {
    throw new GatewayGovernanceError('INVALID_ARGUMENT', `${label} exceeds ${maxChars} characters`)
  }
  return normalized
}

const inside = (candidate, root) => {
  const relation = relative(root, candidate)
  return relation === '' || (!relation.startsWith('..') && !isAbsolute(relation))
}

const snapshotFileName = (taskId) => `${hash(taskId)}.json`

const loadSnapshot = async (root, taskIdInput) => {
  const taskId = requireString('taskId', taskIdInput, MAX_TASK_ID_CHARS)
  const path = resolve(root, snapshotFileName(taskId))
  let parsed
  try {
    parsed = JSON.parse(await readFile(path, 'utf8'))
  } catch (error) {
    if (error?.code === 'ENOENT') {
      throw new GatewayGovernanceError('TASK_NOT_FOUND', 'No Gateway task snapshot matches taskId')
    }
    throw error
  }
  if (parsed?.taskId !== taskId || typeof parsed?.workspacePath !== 'string') {
    throw new GatewayGovernanceError('TASK_SNAPSHOT_INVALID', 'Gateway task snapshot is invalid')
  }
  return parsed
}

const requireSupervision = (runtimeStatus) => {
  const supervision = runtimeStatus?.supervision
  const ledger = supervision?.ledger
  const contract = ledger?.binding?.contract
  if (!ledger || !contract || !supervision?.decision) {
    throw new GatewayGovernanceError(
      'SUPERVISION_UNAVAILABLE',
      'Runtime has no bound Execution Supervisor for this task',
    )
  }
  return { supervision, ledger, contract }
}

const boundedStatus = (snapshot, runtimeStatus) => {
  const { supervision, ledger } = requireSupervision(runtimeStatus)
  return {
    taskId: snapshot.taskId,
    runtimeId: snapshot.runtimeId,
    turnId: snapshot.turnId,
    runtimeDecision: supervision.decision.status,
    pendingObligationIds: ledger.pendingObligationIds ?? [],
    satisfiedObligationIds: ledger.satisfiedObligationIds ?? [],
    violatedObligationIds: ledger.violatedObligationIds ?? [],
  }
}

const mustReadEntries = (snapshot) =>
  Array.isArray(snapshot?.context?.mustRead)
    ? snapshot.context.mustRead.map((item) =>
        typeof item === 'string' ? { path: item, required: true } : item,
      )
    : []

const requiredResource = (snapshot, contract, resourceRefInput) => {
  const resourceRef = slash(requireString('resourceRef', resourceRefInput, MAX_RESOURCE_REF_CHARS))
  const mustRead = mustReadEntries(snapshot).find((item) =>
    item && item.required === true && typeof item.path === 'string' && slash(item.path) === resourceRef,
  )
  if (!mustRead) {
    throw new GatewayGovernanceError(
      'RESOURCE_NOT_REQUIRED',
      'resourceRef is not a required mustRead item in the frozen Task Context',
    )
  }
  const obligation = contract.obligations?.find((item) =>
    item?.kind === 'REQUIRED_RESOURCE'
      && slash(String(item?.target?.resourceId ?? '')) === resourceRef,
  )
  if (!obligation) {
    throw new GatewayGovernanceError(
      'RESOURCE_NOT_GOVERNED',
      'resourceRef has no REQUIRED_RESOURCE obligation in the frozen supervision contract',
    )
  }
  const providers = Array.isArray(obligation?.satisfaction?.acceptedProviderIds)
    ? obligation.satisfaction.acceptedProviderIds
    : []
  if (!providers.includes(TRUSTED_PROVIDER_ID)) {
    throw new GatewayGovernanceError(
      'TRUSTED_PROVIDER_NOT_ACCEPTED',
      'The Task Contract does not accept the built-in ET Harness provider for this resource',
    )
  }
  return { resourceRef, obligation }
}

const localResourcePath = async (snapshot, resourceRef) => {
  if (/^[a-z][a-z0-9+.-]*:\/\//i.test(resourceRef)) {
    throw new GatewayGovernanceError(
      'RESOURCE_KIND_UNSUPPORTED',
      'harness_read_required only reads frozen filesystem resources; URI resources require their declared provider',
    )
  }
  const workspace = await realpath(snapshot.workspacePath)
  const candidate = isAbsolute(resourceRef)
    ? resolve(resourceRef)
    : resolve(workspace, resourceRef)
  const canonical = await realpath(candidate)
  if (!isAbsolute(resourceRef) && !inside(canonical, workspace)) {
    throw new GatewayGovernanceError('RESOURCE_PATH_ESCAPE', 'Required resource escapes the governed workspace')
  }
  return canonical
}

const ingestTrustedEvent = async (runtimeAccess, snapshot, input) => {
  const result = await runtimeAccess.ingest(snapshot, {
    runtimeId: snapshot.runtimeId,
    turnId: snapshot.turnId,
    ...input,
  })
  if (result?.acceptance?.status === 'REJECTED') {
    throw new GatewayGovernanceError(
      'EXECUTION_EVENT_REJECTED',
      `Runtime rejected trusted execution event ${input.eventId}`,
    )
  }
  return result
}

const ingestTrustedValidationSpan = async (
  runtimeAccess,
  snapshot,
  ledger,
  contract,
  checkpointId,
  ordinal,
  receipt,
) => {
  if (typeof runtimeAccess.ingestTrustedValidationSpan !== 'function') {
    throw new GatewayGovernanceError(
      'TRUSTED_VALIDATION_INGRESS_UNAVAILABLE',
      'Frozen Runtime does not expose the internal trusted validation span ingress',
    )
  }
  const requestId = ledger?.binding?.requestId
  if (typeof requestId !== 'string' || !requestId) {
    throw new GatewayGovernanceError(
      'SUPERVISION_BINDING_INVALID',
      'Execution Supervisor binding has no requestId',
    )
  }

  const token = `${checkpointId}-${ordinal}`
  const requestEventId = `mcp-checkpoint-span-request-${token}`
  const validationEventId = `mcp-checkpoint-validation-${token}`
  const responseEventId = `mcp-checkpoint-span-response-${token}`
  const emptyContentHash = hash('')
  const requestManifest = {
    schema: EXTERNAL_REQUEST_SCHEMA,
    requestId,
    runtimeId: snapshot.runtimeId,
    projectId: contract.projectId,
    taskId: contract.taskId,
    turnId: snapshot.turnId,
    agentId: contract.agentId,
    contextHash: contract.contextHash,
    contractHash: hashCanonical(contract),
    expectedHostId: TRUSTED_HOST_ID,
    expectedProviderId: TRUSTED_PROVIDER_ID,
    expectedModelId: TRUSTED_MODEL_ID,
    userMessage: {
      messageId: requestEventId,
      content: '',
      contentHash: emptyContentHash,
    },
    issuedAt: receipt.timestamp,
  }
  const validationPayload = { receipt }
  const requestManifestHash = hashCanonical(requestManifest)
  const responseManifest = {
    schema: EXTERNAL_RESPONSE_SCHEMA,
    requestManifestHash,
    requestId,
    runtimeId: snapshot.runtimeId,
    projectId: contract.projectId,
    taskId: contract.taskId,
    turnId: snapshot.turnId,
    agentId: contract.agentId,
    contextHash: contract.contextHash,
    responseId: `mcp-checkpoint-response-${token}`,
    actualHostId: TRUSTED_HOST_ID,
    actualProviderId: TRUSTED_PROVIDER_ID,
    actualModelId: TRUSTED_MODEL_ID,
    actualAgentId: contract.agentId,
    assistantMessage: {
      messageId: responseEventId,
      content: '',
      contentHash: emptyContentHash,
    },
    claims: [],
    receiptRefs: [{
      eventId: validationEventId,
      payloadHash: hashCanonical(validationPayload),
    }],
    completedAt: receipt.timestamp,
  }

  const span = await runtimeAccess.ingestTrustedValidationSpan(snapshot, {
    runtimeId: snapshot.runtimeId,
    turnId: snapshot.turnId,
    requestEventId,
    requestManifest,
    validationEventId,
    validationReceipt: receipt,
    responseEventId,
    responseManifest,
  })
  for (const [label, result] of [
    ['request', span?.request],
    ['validation', span?.validation],
    ['response', span?.response],
  ]) {
    if (!result || result.acceptance?.status === 'REJECTED') {
      throw new GatewayGovernanceError(
        'EXECUTION_EVENT_REJECTED',
        `Runtime did not accept trusted validation ${label} event`,
      )
    }
  }
  return span
}

const executeCommand = (command, workspacePath) => {
  if (typeof command !== 'string' || !command.trim() || command.length > MAX_COMMAND_CHARS) {
    throw new GatewayGovernanceError('VALIDATION_CONTRACT_INVALID', 'Validation command is missing or over budget')
  }
  return new Promise((resolveExecution, rejectExecution) => {
    const startedAt = new Date().toISOString()
    exec(command, {
      cwd: workspacePath,
      env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' },
      maxBuffer: MAX_COMMAND_OUTPUT_BYTES,
      timeout: COMMAND_TIMEOUT_MS,
      windowsHide: true,
    }, (error, stdout, stderr) => {
      const completedAt = new Date().toISOString()
      if (!error) {
        resolveExecution({ exitCode: 0, stdout, stderr, startedAt, completedAt })
        return
      }
      const code = error.code
      if (typeof code === 'number' && !error.killed) {
        resolveExecution({ exitCode: code, stdout, stderr, startedAt, completedAt })
        return
      }
      rejectExecution(new GatewayGovernanceError(
        'VALIDATION_EXECUTION_FAILED',
        `Validation process did not produce a normal exit code: ${error.message}`,
      ))
    })
  })
}

const validationSpec = (snapshot, validationId) => {
  const items = Array.isArray(snapshot?.context?.validation) ? snapshot.context.validation : []
  const item = items.find((candidate) => candidate?.id === validationId)
  if (!item || typeof item.command !== 'string') {
    throw new GatewayGovernanceError(
      'VALIDATION_CONTRACT_INVALID',
      `Frozen Task Context has no command for validation ${validationId}`,
    )
  }
  return item
}

const acceptedCheckpointPolicy = (contract, obligationId) => {
  const policy = contract.evidencePolicies?.find((item) =>
    Array.isArray(item?.obligationIds) && item.obligationIds.includes(obligationId),
  )
  if (!policy
      || !policy.acceptedProviderIds?.includes(TRUSTED_PROVIDER_ID)
      || !policy.acceptedProviderKinds?.includes('VALIDATOR')) {
    throw new GatewayGovernanceError(
      'CHECKPOINT_PROVIDER_NOT_ACCEPTED',
      `Task Contract does not authorize ${TRUSTED_PROVIDER_ID} as a validator for ${obligationId}`,
    )
  }
  return policy
}

export const createTrustedCheckpointController = ({
  runtimeAccess,
  taskSnapshotRoot,
}) => {
  return Object.freeze({
    async readRequired(input) {
      const snapshot = await loadSnapshot(taskSnapshotRoot, input?.taskId)
      const runtimeStatus = await runtimeAccess.getStatus(snapshot)
      const { ledger, contract } = requireSupervision(runtimeStatus)
      const { resourceRef, obligation } = requiredResource(snapshot, contract, input?.resourceRef)
      const path = await localResourcePath(snapshot, resourceRef)
      const info = await stat(path)
      if (!info.isFile()) {
        throw new GatewayGovernanceError('RESOURCE_NOT_FILE', 'Required resource is not a regular file')
      }
      if (info.size > MAX_REQUIRED_READ_BYTES) {
        throw new GatewayGovernanceError(
          'RESOURCE_TOO_LARGE',
          `Required resource exceeds ${MAX_REQUIRED_READ_BYTES} bytes; refusing partial trusted read`,
        )
      }
      const bytes = await readFile(path)
      if (bytes.includes(0)) {
        throw new GatewayGovernanceError('RESOURCE_NOT_TEXT', 'Required resource is not bounded text')
      }
      const contentHash = hash(bytes)
      const eventId = `mcp-read-${hash(`${snapshot.taskId}\0${resourceRef}\0${contentHash}`).slice(0, 48)}`
      const event = await ingestTrustedEvent(runtimeAccess, snapshot, {
        eventId,
        kind: 'RESOURCE_READ',
        payload: {
          receipt: {
            provider: TRUSTED_PROVIDER_ID,
            resourceId: resourceRef,
            path: slash(path),
            contentHash,
            disposition: 'FOUND',
            purpose: 'required-task-context-read',
            claimRefs: [],
          },
        },
      })
      return {
        status: 'READ',
        taskId: snapshot.taskId,
        obligationId: obligation.id,
        resourceRef,
        bytes: bytes.length,
        contentHash: `sha256:${contentHash}`,
        eventRef: event.eventRef,
        eventAcceptance: event.acceptance?.status,
        content: bytes.toString('utf8'),
        pendingObligationIds: ledger.pendingObligationIds ?? [],
      }
    },

    async checkpoint(input) {
      const snapshot = await loadSnapshot(taskSnapshotRoot, input?.taskId)
      let runtimeStatus = await runtimeAccess.getStatus(snapshot)
      let { ledger, contract } = requireSupervision(runtimeStatus)
      const pending = new Set(ledger.pendingObligationIds ?? [])
      const pendingRequiredReads = contract.obligations
        .filter((item) => item.kind === 'REQUIRED_RESOURCE' && pending.has(item.id))
        .map((item) => item.id)
      if (pendingRequiredReads.length > 0) {
        return {
          status: 'BLOCKED',
          reason: 'REQUIRED_READS_PENDING',
          pendingRequiredReadIds: pendingRequiredReads,
          ...boundedStatus(snapshot, runtimeStatus),
        }
      }

      const checkpointId = randomUUID()
      const validations = []
      for (const obligation of contract.obligations) {
        if (obligation.kind !== 'VALIDATION' || !pending.has(obligation.id)) continue
        acceptedCheckpointPolicy(contract, obligation.id)
        const validationId = String(obligation?.target?.validationId ?? '')
        const targetIdentity = String(obligation?.target?.targetIdentity ?? '')
        if (!validationId || !targetIdentity) {
          throw new GatewayGovernanceError(
            'VALIDATION_CONTRACT_INVALID',
            `Validation obligation ${obligation.id} has no stable target identity`,
          )
        }
        const spec = validationSpec(snapshot, validationId)
        const execution = await executeCommand(spec.command, snapshot.workspacePath)
        const output = `${execution.stdout}\0${execution.stderr}`
        const outputHash = hash(output)
        const toolEvent = await ingestTrustedEvent(runtimeAccess, snapshot, {
          eventId: `mcp-checkpoint-tool-${checkpointId}-${validations.length + 1}`,
          kind: 'TOOL_RESULT',
          payload: {
            checkpoint: {
              validationId,
              commandHash: `sha256:${hash(spec.command)}`,
              exitCode: execution.exitCode,
              outputHash: `sha256:${outputHash}`,
              outputPreview: [execution.stdout.trim(), execution.stderr.trim()]
                .filter(Boolean)
                .join('\n')
                .slice(0, MAX_COMMAND_PREVIEW_CHARS),
            },
          },
        })
        const receipt = {
          providerId: TRUSTED_PROVIDER_ID,
          providerKind: 'VALIDATOR',
          validationId,
          commandOrTestIdentity: `sha256:${hash(spec.command)}`,
          ...(contract.projectRevision ? { projectRevision: contract.projectRevision } : {}),
          contextHash: contract.contextHash,
          targetIdentity,
          resultStatus: execution.exitCode === 0 ? 'PASS' : 'FAIL',
          artifactRefs: [],
          evidenceRefs: [toolEvent.eventRef],
          claimRefs: [],
          timestamp: execution.completedAt,
        }
        const span = await ingestTrustedValidationSpan(
          runtimeAccess,
          snapshot,
          ledger,
          contract,
          checkpointId,
          validations.length + 1,
          receipt,
        )
        validations.push({
          obligationId: obligation.id,
          validationId,
          exitCode: execution.exitCode,
          resultStatus: receipt.resultStatus,
          toolEventRef: toolEvent.eventRef,
          requestEventRef: span.request.eventRef,
          validationEventRef: span.validation.eventRef,
          responseEventRef: span.response.eventRef,
          outputHash: `sha256:${outputHash}`,
        })
        if (execution.exitCode !== 0) break
      }

      runtimeStatus = await runtimeAccess.getStatus(snapshot)
      ;({ ledger, contract } = requireSupervision(runtimeStatus))
      return {
        status: validations.some((item) => item.resultStatus === 'FAIL') ? 'FAILED' : 'CHECKPOINTED',
        validations,
        ...boundedStatus(snapshot, runtimeStatus),
      }
    },
  })
}

export const registerTrustedCheckpointTools = ({
  server,
  governance,
  toolResult,
  governanceToolError,
}) => {
  server.registerTool(
    'harness_read_required',
    {
      title: 'Read one governed required resource',
      description:
        'Read one exact required mustRead filesystem resource through the trusted ET Harness boundary and record a Runtime-owned RESOURCE_READ event. It is not a general filesystem tool.',
      inputSchema: {
        taskId: z.string().min(1).max(MAX_TASK_ID_CHARS),
        resourceRef: z.string().min(1).max(MAX_RESOURCE_REF_CHARS),
      },
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: false,
      },
    },
    async (input) => {
      try {
        return toolResult(await governance.readRequired(input))
      } catch (error) {
        return toolResult(governanceToolError(error), true)
      }
    },
  )

  server.registerTool(
    'harness_checkpoint',
    {
      title: 'Run trusted governed checkpoint',
      description:
        'Run only frozen Task Context validation commands authorized by the Task Contract, emit trusted validation events, and return bounded Supervisor status. The caller cannot supply commands, PASS states, receipts, or obligation outcomes.',
      inputSchema: {
        taskId: z.string().min(1).max(MAX_TASK_ID_CHARS),
      },
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: false,
        openWorldHint: false,
      },
    },
    async (input) => {
      try {
        return toolResult(await governance.checkpoint(input))
      } catch (error) {
        return toolResult(governanceToolError(error), true)
      }
    },
  )
}
