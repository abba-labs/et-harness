import {
  EVIDENCE_PROVIDER_KINDS,
  EVIDENCE_RESULT_STATUSES,
  MAX_EXECUTION_EVENT_PAYLOAD_BYTES,
  MAX_IDENTIFIER_CHARS,
  type AgentClaimV01,
  type EvidenceProviderKind,
  type EvidenceResultStatus,
  type ExecutionEventAcceptanceV01,
  type ExecutionEventEnvelopeV01,
  type ExecutionEventStoreBindingV01,
  type ExecutionObligationLedgerV01,
} from './contracts.js'
import {
  canonicalJsonBytes,
  hashCanonicalJson,
  sha256Hex,
} from './hash.js'
import { validateExecutionEventEnvelope } from './validation.js'

export const EXTERNAL_AGENT_REQUEST_MANIFEST_SCHEMA =
  'agent-harness.external-agent-request.v0.1' as const
export const EXTERNAL_AGENT_RESPONSE_MANIFEST_SCHEMA =
  'agent-harness.external-agent-response.v0.1' as const
export const EXTERNAL_AGENT_EVENT_BUNDLE_SCHEMA =
  'agent-harness.external-agent-event-bundle.v0.1' as const

export const MAX_EXTERNAL_AGENT_BUNDLE_EVENTS = 256
export const MAX_EXTERNAL_AGENT_CLAIMS = 256
export const MAX_EXTERNAL_AGENT_RECEIPT_REFS = 256
export const MAX_VISIBLE_MESSAGE_BYTES = 48 * 1024
export const MAX_EXTERNAL_AGENT_BUNDLE_BYTES =
  MAX_EXTERNAL_AGENT_BUNDLE_EVENTS * (MAX_EXECUTION_EVENT_PAYLOAD_BYTES + 4096)

export interface ExternalVisibleMessageV01 {
  readonly messageId: string
  readonly content: string
  readonly contentHash: string
}

export interface ExternalAgentRequestManifestV01 {
  readonly schema: typeof EXTERNAL_AGENT_REQUEST_MANIFEST_SCHEMA
  readonly requestId: string
  readonly runtimeId: string
  readonly projectId: string
  readonly taskId: string
  readonly turnId: string
  readonly agentId: string
  readonly contextHash: string
  readonly contractHash: string
  readonly expectedHostId: string
  readonly expectedProviderId: string
  readonly expectedModelId: string
  readonly userMessage: ExternalVisibleMessageV01
  readonly issuedAt: string
}

export interface ExternalReceiptReferenceV01 {
  readonly eventId: string
  readonly payloadHash: string
}

export interface ExternalAgentResponseManifestV01 {
  readonly schema: typeof EXTERNAL_AGENT_RESPONSE_MANIFEST_SCHEMA
  readonly requestManifestHash: string
  readonly requestId: string
  readonly runtimeId: string
  readonly projectId: string
  readonly taskId: string
  readonly turnId: string
  readonly agentId: string
  readonly contextHash: string
  readonly responseId: string
  readonly actualHostId: string
  readonly actualProviderId: string
  readonly actualModelId: string
  readonly actualAgentId: string
  readonly assistantMessage: ExternalVisibleMessageV01
  readonly claims: readonly AgentClaimV01[]
  readonly receiptRefs: readonly ExternalReceiptReferenceV01[]
  readonly completedAt: string
}

export interface ExternalAgentEventBundleV01 {
  readonly schema: typeof EXTERNAL_AGENT_EVENT_BUNDLE_SCHEMA
  readonly bundleId: string
  readonly requestManifestHash: string
  readonly responseManifestHash: string
  readonly events: readonly ExecutionEventEnvelopeV01[]
}

export interface ExternalAgentBridgeValidationIssueV01 {
  readonly path: string
  readonly code: string
  readonly message: string
}

export type ExternalAgentBridgeValidationResultV01 =
  | {
      readonly valid: true
      readonly value: ExternalAgentEventBundleV01
      readonly requestManifest: ExternalAgentRequestManifestV01
      readonly responseManifest: ExternalAgentResponseManifestV01
      readonly issues: readonly []
    }
  | {
      readonly valid: false
      readonly issues: readonly ExternalAgentBridgeValidationIssueV01[]
    }

export interface ExternalAgentBridgeRuntimeFailureV01 {
  readonly eventId: string
  readonly sequence: number
  readonly message: string
}

export interface ExternalAgentBundleIngestionResultV01 {
  readonly acceptances: readonly ExecutionEventAcceptanceV01[]
  readonly acceptedPrefix: readonly ExecutionEventAcceptanceV01[]
  readonly failure?: ExecutionEventAcceptanceV01 | ExternalAgentBridgeRuntimeFailureV01
}

type MutableRecord = Record<string, unknown>

const SHA256_PATTERN = /^[0-9a-f]{64}$/
const FORBIDDEN_PAYLOAD_KEYS = new Set([
  'chainOfThought',
  'hiddenReasoning',
  'rawToolOutput',
  'reasoning',
])

const recordOf = (value: unknown): MutableRecord | undefined => {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return undefined
  const prototype = Object.getPrototypeOf(value)
  return prototype === Object.prototype || prototype === null
    ? value as MutableRecord
    : undefined
}

const issue = (
  issues: ExternalAgentBridgeValidationIssueV01[],
  path: string,
  code: string,
  message: string,
): void => {
  issues.push({ path, code, message })
}

const exactKeys = (
  record: MutableRecord,
  expected: readonly string[],
  path: string,
  issues: ExternalAgentBridgeValidationIssueV01[],
): void => {
  const allowed = new Set(expected)
  for (const key of Object.keys(record)) {
    if (!allowed.has(key)) issue(issues, `${path}.${key}`, 'UNKNOWN_FIELD', `Unknown field ${key}`)
  }
  for (const key of expected) {
    if (!(key in record)) issue(issues, `${path}.${key}`, 'REQUIRED_FIELD', `Missing field ${key}`)
  }
}

const requiredString = (
  record: MutableRecord,
  key: string,
  path: string,
  issues: ExternalAgentBridgeValidationIssueV01[],
  options: { readonly hash?: boolean; readonly content?: boolean } = {},
): string | undefined => {
  const value = record[key]
  if (typeof value !== 'string' || (!options.content && value.length === 0)) {
    issue(issues, `${path}.${key}`, 'INVALID_STRING', `${key} must be a string${options.content ? '' : ' and non-empty'}`)
    return undefined
  }
  if (!options.content && value.length > MAX_IDENTIFIER_CHARS) {
    issue(issues, `${path}.${key}`, 'STRING_TOO_LONG', `${key} exceeds ${MAX_IDENTIFIER_CHARS} characters`)
  }
  if (options.hash && !SHA256_PATTERN.test(value)) {
    issue(issues, `${path}.${key}`, 'INVALID_HASH', `${key} must be a lowercase SHA-256 digest`)
  }
  return value
}

const requiredTimestamp = (
  record: MutableRecord,
  key: string,
  path: string,
  issues: ExternalAgentBridgeValidationIssueV01[],
): string | undefined => {
  const value = requiredString(record, key, path, issues)
  if (value !== undefined) {
    const parsed = Date.parse(value)
    if (!Number.isFinite(parsed) || new Date(parsed).toISOString() !== value) {
      issue(issues, `${path}.${key}`, 'INVALID_TIMESTAMP', `${key} must be a canonical ISO timestamp`)
    }
  }
  return value
}

const stringArray = (
  value: unknown,
  path: string,
  issues: ExternalAgentBridgeValidationIssueV01[],
): readonly string[] | undefined => {
  if (!Array.isArray(value)) {
    issue(issues, path, 'INVALID_ARRAY', 'Expected an array')
    return undefined
  }
  const result: string[] = []
  value.forEach((item, index) => {
    if (typeof item !== 'string' || item.length === 0 || item.length > MAX_IDENTIFIER_CHARS) {
      issue(issues, `${path}[${index}]`, 'INVALID_STRING', 'Expected a bounded non-empty string')
    } else {
      result.push(item)
    }
  })
  if (new Set(result).size !== result.length) issue(issues, path, 'DUPLICATE_ITEM', 'Array items must be unique')
  return result
}

const visibleMessage = (
  value: unknown,
  path: string,
  issues: ExternalAgentBridgeValidationIssueV01[],
): ExternalVisibleMessageV01 | undefined => {
  const record = recordOf(value)
  if (!record) {
    issue(issues, path, 'INVALID_MESSAGE', 'Visible message must be an object')
    return undefined
  }
  exactKeys(record, ['messageId', 'content', 'contentHash'], path, issues)
  const messageId = requiredString(record, 'messageId', path, issues)
  const content = requiredString(record, 'content', path, issues, { content: true })
  const contentHash = requiredString(record, 'contentHash', path, issues, { hash: true })
  if (content !== undefined) {
    if (Buffer.byteLength(content, 'utf8') > MAX_VISIBLE_MESSAGE_BYTES) {
      issue(issues, `${path}.content`, 'MESSAGE_BUDGET_EXCEEDED', `Visible message exceeds ${MAX_VISIBLE_MESSAGE_BYTES} bytes`)
    }
    if (contentHash !== undefined && sha256Hex(content) !== contentHash) {
      issue(issues, `${path}.contentHash`, 'CONTENT_HASH_MISMATCH', 'contentHash does not bind the exact visible content')
    }
  }
  return messageId && content !== undefined && contentHash
    ? record as unknown as ExternalVisibleMessageV01
    : undefined
}

const validateClaims = (
  value: unknown,
  path: string,
  issues: ExternalAgentBridgeValidationIssueV01[],
): readonly AgentClaimV01[] | undefined => {
  if (!Array.isArray(value) || value.length > MAX_EXTERNAL_AGENT_CLAIMS) {
    issue(issues, path, 'INVALID_CLAIMS', `claims must be an array of at most ${MAX_EXTERNAL_AGENT_CLAIMS} items`)
    return undefined
  }
  const claims: AgentClaimV01[] = []
  const ids = new Set<string>()
  value.forEach((item, index) => {
    const itemPath = `${path}[${index}]`
    const record = recordOf(item)
    if (!record) {
      issue(issues, itemPath, 'INVALID_CLAIM', 'Claim must be an object')
      return
    }
    const expected = ['id', 'kind', 'targetIdentity', 'resultStatus', 'evidenceRefs']
    if ('validationId' in record) expected.push('validationId')
    if ('outputContractId' in record) expected.push('outputContractId')
    exactKeys(record, expected, itemPath, issues)
    const id = requiredString(record, 'id', itemPath, issues)
    requiredString(record, 'targetIdentity', itemPath, issues)
    if (!['OUTPUT', 'VALIDATION', 'RULE_COMPLIANCE'].includes(String(record.kind))) {
      issue(issues, `${itemPath}.kind`, 'INVALID_CLAIM_KIND', `Unsupported claim kind ${String(record.kind)}`)
    }
    if (!EVIDENCE_RESULT_STATUSES.includes(record.resultStatus as EvidenceResultStatus)) {
      issue(issues, `${itemPath}.resultStatus`, 'INVALID_RESULT_STATUS', `Unsupported result status ${String(record.resultStatus)}`)
    }
    stringArray(record.evidenceRefs, `${itemPath}.evidenceRefs`, issues)
    if (record.kind === 'OUTPUT') {
      requiredString(record, 'outputContractId', itemPath, issues)
      if ('validationId' in record) issue(issues, `${itemPath}.validationId`, 'CLAIM_FIELD_MISMATCH', 'OUTPUT claim cannot declare validationId')
    } else if (record.kind === 'VALIDATION' || record.kind === 'RULE_COMPLIANCE') {
      requiredString(record, 'validationId', itemPath, issues)
      if ('outputContractId' in record) issue(issues, `${itemPath}.outputContractId`, 'CLAIM_FIELD_MISMATCH', `${String(record.kind)} claim cannot declare outputContractId`)
    }
    if (id && ids.has(id)) issue(issues, `${itemPath}.id`, 'DUPLICATE_CLAIM_ID', `Duplicate claim id ${id}`)
    if (id) ids.add(id)
    claims.push(record as unknown as AgentClaimV01)
  })
  return claims
}

const requestManifest = (
  value: unknown,
  path: string,
  issues: ExternalAgentBridgeValidationIssueV01[],
): ExternalAgentRequestManifestV01 | undefined => {
  const record = recordOf(value)
  if (!record) {
    issue(issues, path, 'INVALID_REQUEST_MANIFEST', 'Request manifest must be an object')
    return undefined
  }
  exactKeys(record, [
    'schema', 'requestId', 'runtimeId', 'projectId', 'taskId', 'turnId', 'agentId',
    'contextHash', 'contractHash', 'expectedHostId', 'expectedProviderId',
    'expectedModelId', 'userMessage', 'issuedAt',
  ], path, issues)
  if (record.schema !== EXTERNAL_AGENT_REQUEST_MANIFEST_SCHEMA) {
    issue(issues, `${path}.schema`, 'INVALID_SCHEMA', `schema must be ${EXTERNAL_AGENT_REQUEST_MANIFEST_SCHEMA}`)
  }
  for (const key of [
    'requestId', 'runtimeId', 'projectId', 'taskId', 'turnId', 'agentId',
    'expectedHostId', 'expectedProviderId', 'expectedModelId',
  ]) requiredString(record, key, path, issues)
  requiredString(record, 'contextHash', path, issues, { hash: true })
  requiredString(record, 'contractHash', path, issues, { hash: true })
  const userMessage = visibleMessage(record.userMessage, `${path}.userMessage`, issues)
  requiredTimestamp(record, 'issuedAt', path, issues)
  if (!userMessage) return undefined
  return { ...record, userMessage } as unknown as ExternalAgentRequestManifestV01
}

const receiptReferences = (
  value: unknown,
  path: string,
  issues: ExternalAgentBridgeValidationIssueV01[],
): readonly ExternalReceiptReferenceV01[] | undefined => {
  if (!Array.isArray(value) || value.length > MAX_EXTERNAL_AGENT_RECEIPT_REFS) {
    issue(issues, path, 'INVALID_RECEIPT_REFS', `receiptRefs must be an array of at most ${MAX_EXTERNAL_AGENT_RECEIPT_REFS} items`)
    return undefined
  }
  const refs: ExternalReceiptReferenceV01[] = []
  const ids = new Set<string>()
  value.forEach((item, index) => {
    const itemPath = `${path}[${index}]`
    const record = recordOf(item)
    if (!record) {
      issue(issues, itemPath, 'INVALID_RECEIPT_REF', 'Receipt reference must be an object')
      return
    }
    exactKeys(record, ['eventId', 'payloadHash'], itemPath, issues)
    const eventId = requiredString(record, 'eventId', itemPath, issues)
    requiredString(record, 'payloadHash', itemPath, issues, { hash: true })
    if (eventId && ids.has(eventId)) issue(issues, `${itemPath}.eventId`, 'DUPLICATE_RECEIPT_REF', `Duplicate receipt event ${eventId}`)
    if (eventId) ids.add(eventId)
    refs.push(record as unknown as ExternalReceiptReferenceV01)
  })
  return refs
}

const responseManifest = (
  value: unknown,
  path: string,
  issues: ExternalAgentBridgeValidationIssueV01[],
): ExternalAgentResponseManifestV01 | undefined => {
  const record = recordOf(value)
  if (!record) {
    issue(issues, path, 'INVALID_RESPONSE_MANIFEST', 'Response manifest must be an object')
    return undefined
  }
  exactKeys(record, [
    'schema', 'requestManifestHash', 'requestId', 'runtimeId', 'projectId', 'taskId',
    'turnId', 'agentId', 'contextHash', 'responseId', 'actualHostId',
    'actualProviderId', 'actualModelId', 'actualAgentId', 'assistantMessage',
    'claims', 'receiptRefs', 'completedAt',
  ], path, issues)
  if (record.schema !== EXTERNAL_AGENT_RESPONSE_MANIFEST_SCHEMA) {
    issue(issues, `${path}.schema`, 'INVALID_SCHEMA', `schema must be ${EXTERNAL_AGENT_RESPONSE_MANIFEST_SCHEMA}`)
  }
  for (const key of [
    'requestId', 'runtimeId', 'projectId', 'taskId', 'turnId', 'agentId', 'responseId',
    'actualHostId', 'actualProviderId', 'actualModelId', 'actualAgentId',
  ]) requiredString(record, key, path, issues)
  requiredString(record, 'requestManifestHash', path, issues, { hash: true })
  requiredString(record, 'contextHash', path, issues, { hash: true })
  const assistantMessage = visibleMessage(record.assistantMessage, `${path}.assistantMessage`, issues)
  const claims = validateClaims(record.claims, `${path}.claims`, issues)
  const refs = receiptReferences(record.receiptRefs, `${path}.receiptRefs`, issues)
  requiredTimestamp(record, 'completedAt', path, issues)
  if (!assistantMessage || !claims || !refs) return undefined
  return {
    ...record,
    assistantMessage,
    claims,
    receiptRefs: refs,
  } as unknown as ExternalAgentResponseManifestV01
}

const forbidHiddenPayload = (
  value: unknown,
  path: string,
  issues: ExternalAgentBridgeValidationIssueV01[],
): void => {
  if (Array.isArray(value)) {
    value.forEach((item, index) => forbidHiddenPayload(item, `${path}[${index}]`, issues))
    return
  }
  const record = recordOf(value)
  if (!record) return
  for (const [key, item] of Object.entries(record)) {
    if (FORBIDDEN_PAYLOAD_KEYS.has(key)) issue(issues, `${path}.${key}`, 'FORBIDDEN_PAYLOAD_FIELD', `Payload field ${key} is forbidden`)
    forbidHiddenPayload(item, `${path}.${key}`, issues)
  }
}

const exactReceipt = (
  event: ExecutionEventEnvelopeV01,
  allowedKeys: readonly string[],
  issues: ExternalAgentBridgeValidationIssueV01[],
): MutableRecord | undefined => {
  const payloadPath = `$.events[${event.sequence - 1}].payload`
  const payload = recordOf(event.payload)
  if (!payload) return undefined
  exactKeys(payload, ['receipt'], payloadPath, issues)
  const receipt = recordOf(payload.receipt)
  if (!receipt) {
    issue(issues, `${payloadPath}.receipt`, 'INVALID_RECEIPT', 'Receipt must be an object')
    return undefined
  }
  exactKeys(receipt, allowedKeys.filter(key => key in receipt), `${payloadPath}.receipt`, issues)
  return receipt
}

const trustedResourceProviderIds = (ledger: ExecutionObligationLedgerV01): ReadonlySet<string> => {
  const ids = new Set<string>()
  for (const obligation of ledger.binding.contract.obligations) {
    const satisfaction = recordOf(obligation.satisfaction)
    if (Array.isArray(satisfaction?.acceptedProviderIds)) {
      satisfaction.acceptedProviderIds.forEach(id => {
        if (typeof id === 'string') ids.add(id)
      })
    }
  }
  return ids
}

const evidenceProviderAccepted = (
  ledger: ExecutionObligationLedgerV01,
  providerId: string,
  providerKind: EvidenceProviderKind,
): boolean => ledger.binding.contract.evidencePolicies.some(policy =>
  (policy.acceptedProviderIds.length === 0
    || policy.acceptedProviderIds.includes(providerId))
  && (policy.acceptedProviderKinds.length === 0
    || policy.acceptedProviderKinds.includes(providerKind)))

const validateReceiptPayload = (
  event: ExecutionEventEnvelopeV01,
  ledger: ExecutionObligationLedgerV01,
  issues: ExternalAgentBridgeValidationIssueV01[],
): void => {
  const eventPath = `$.events[${event.sequence - 1}]`
  if (['RESOURCE_SEARCH', 'RESOURCE_READ', 'SOURCE_DISPOSITION'].includes(event.kind)) {
    const receipt = exactReceipt(event, [
      'provider', 'resourceId', 'path', 'revision', 'modifiedAt', 'contentHash',
      'disposition', 'purpose', 'claimRefs', 'error',
    ], issues)
    if (!receipt) return
    const provider = requiredString(receipt, 'provider', `${eventPath}.payload.receipt`, issues)
    requiredString(receipt, 'resourceId', `${eventPath}.payload.receipt`, issues)
    requiredString(receipt, 'purpose', `${eventPath}.payload.receipt`, issues)
    stringArray(receipt.claimRefs, `${eventPath}.payload.receipt.claimRefs`, issues)
    if (!['FOUND', 'NO_MATCH', 'UNAVAILABLE'].includes(String(receipt.disposition))) {
      issue(issues, `${eventPath}.payload.receipt.disposition`, 'INVALID_DISPOSITION', 'Unsupported source disposition')
    }
    for (const key of ['path', 'revision', 'modifiedAt', 'error']) {
      if (key in receipt && typeof receipt[key] !== 'string') issue(issues, `${eventPath}.payload.receipt.${key}`, 'INVALID_RECEIPT_FIELD', `${key} must be a string when declared`)
    }
    if ('contentHash' in receipt && (typeof receipt.contentHash !== 'string' || !SHA256_PATTERN.test(receipt.contentHash))) issue(issues, `${eventPath}.payload.receipt.contentHash`, 'INVALID_HASH', 'contentHash must be a lowercase SHA-256 digest')
    if (provider && !trustedResourceProviderIds(ledger).has(provider)) {
      issue(issues, `${eventPath}.payload.receipt.provider`, 'UNTRUSTED_PROVIDER', `Provider ${provider} is not contributed as trusted`)
    }
    return
  }
  if (event.kind === 'RESOURCE_WRITE') {
    const receipt = exactReceipt(event, [
      'resourceId', 'path', 'beforeHash', 'afterHash', 'action', 'scopeDecision', 'executorId',
    ], issues) as MutableRecord | undefined
    if (!receipt) return
    for (const key of ['resourceId', 'action', 'scopeDecision', 'executorId']) {
      requiredString(receipt, key, `${eventPath}.payload.receipt`, issues)
    }
    if (!['CREATE', 'UPDATE', 'DELETE', 'MOVE', 'COPY'].includes(String(receipt.action))) issue(issues, `${eventPath}.payload.receipt.action`, 'INVALID_ACTION', 'Unsupported mutation action')
    if (!['ALLOWED', 'PROTECTED', 'OUTSIDE_SCOPE', 'UNKNOWN'].includes(String(receipt.scopeDecision))) issue(issues, `${eventPath}.payload.receipt.scopeDecision`, 'INVALID_SCOPE_DECISION', 'Unsupported scope decision')
    for (const key of ['path', 'beforeHash', 'afterHash']) {
      if (key in receipt && typeof receipt[key] !== 'string') issue(issues, `${eventPath}.payload.receipt.${key}`, 'INVALID_RECEIPT_FIELD', `${key} must be a string when declared`)
    }
    for (const key of ['beforeHash', 'afterHash']) {
      if (typeof receipt[key] === 'string' && !SHA256_PATTERN.test(receipt[key])) issue(issues, `${eventPath}.payload.receipt.${key}`, 'INVALID_HASH', `${key} must be a lowercase SHA-256 digest`)
    }
    return
  }
  if (event.kind === 'VALIDATION_RESULT') {
    const receipt = exactReceipt(event, [
      'providerId', 'providerKind', 'validationId', 'commandOrTestIdentity',
      'projectRevision', 'contextHash', 'targetIdentity', 'resultStatus',
      'artifactRefs', 'evidenceRefs', 'claimRefs', 'timestamp',
    ], issues) as MutableRecord | undefined
    if (!receipt) return
    const provider = requiredString(receipt, 'providerId', `${eventPath}.payload.receipt`, issues)
    if (provider && EVIDENCE_PROVIDER_KINDS.includes(receipt.providerKind as EvidenceProviderKind)
        && !evidenceProviderAccepted(ledger, provider, receipt.providerKind as EvidenceProviderKind)) issue(issues, `${eventPath}.payload.receipt.providerId`, 'UNTRUSTED_PROVIDER', `Provider ${provider} and kind are not contributed as trusted`)
    if (!EVIDENCE_PROVIDER_KINDS.includes(receipt.providerKind as EvidenceProviderKind)) issue(issues, `${eventPath}.payload.receipt.providerKind`, 'INVALID_PROVIDER_KIND', 'Unsupported provider kind')
    if (!EVIDENCE_RESULT_STATUSES.includes(receipt.resultStatus as EvidenceResultStatus)) issue(issues, `${eventPath}.payload.receipt.resultStatus`, 'INVALID_RESULT_STATUS', 'Unsupported result status')
    for (const key of ['validationId', 'commandOrTestIdentity', 'contextHash', 'targetIdentity']) requiredString(receipt, key, `${eventPath}.payload.receipt`, issues, { hash: key === 'contextHash' })
    for (const key of ['artifactRefs', 'evidenceRefs', 'claimRefs']) stringArray(receipt[key], `${eventPath}.payload.receipt.${key}`, issues)
    requiredTimestamp(receipt, 'timestamp', `${eventPath}.payload.receipt`, issues)
    if ('projectRevision' in receipt && typeof receipt.projectRevision !== 'string') issue(issues, `${eventPath}.payload.receipt.projectRevision`, 'INVALID_RECEIPT_FIELD', 'projectRevision must be a string when declared')
    return
  }
  if (event.kind === 'OUTPUT_EMITTED') {
    const receipt = exactReceipt(event, [
      'providerId', 'providerKind', 'outputContractId', 'resourceId', 'path',
      'contentHash', 'projectRevision', 'contextHash', 'targetIdentity',
      'structuralValidationStatus', 'ruleValidationRefs', 'evidenceRefs',
      'claimRefs', 'timestamp',
    ], issues) as MutableRecord | undefined
    if (!receipt) return
    const provider = requiredString(receipt, 'providerId', `${eventPath}.payload.receipt`, issues)
    if (provider && EVIDENCE_PROVIDER_KINDS.includes(receipt.providerKind as EvidenceProviderKind)
        && !evidenceProviderAccepted(ledger, provider, receipt.providerKind as EvidenceProviderKind)) issue(issues, `${eventPath}.payload.receipt.providerId`, 'UNTRUSTED_PROVIDER', `Provider ${provider} and kind are not contributed as trusted`)
    if (!EVIDENCE_PROVIDER_KINDS.includes(receipt.providerKind as EvidenceProviderKind)) issue(issues, `${eventPath}.payload.receipt.providerKind`, 'INVALID_PROVIDER_KIND', 'Unsupported provider kind')
    for (const key of ['outputContractId', 'resourceId', 'contentHash', 'contextHash', 'targetIdentity']) requiredString(receipt, key, `${eventPath}.payload.receipt`, issues, { hash: key === 'contentHash' || key === 'contextHash' })
    if (!['PASS', 'FAIL', 'NOT_EXECUTED'].includes(String(receipt.structuralValidationStatus))) issue(issues, `${eventPath}.payload.receipt.structuralValidationStatus`, 'INVALID_STRUCTURAL_STATUS', 'Unsupported structural validation status')
    for (const key of ['ruleValidationRefs', 'evidenceRefs', 'claimRefs']) stringArray(receipt[key], `${eventPath}.payload.receipt.${key}`, issues)
    requiredTimestamp(receipt, 'timestamp', `${eventPath}.payload.receipt`, issues)
    for (const key of ['path', 'projectRevision']) {
      if (key in receipt && typeof receipt[key] !== 'string') issue(issues, `${eventPath}.payload.receipt.${key}`, 'INVALID_RECEIPT_FIELD', `${key} must be a string when declared`)
    }
  }
}

export const validateExternalAgentEventBundle = (
  value: unknown,
  ledger: ExecutionObligationLedgerV01,
): ExternalAgentBridgeValidationResultV01 => {
  const issues: ExternalAgentBridgeValidationIssueV01[] = []
  const bundle = recordOf(value)
  if (!bundle) return { valid: false, issues: [{ path: '$', code: 'INVALID_BUNDLE', message: 'Bundle must be an object' }] }
  exactKeys(bundle, ['schema', 'bundleId', 'requestManifestHash', 'responseManifestHash', 'events'], '$', issues)
  if (bundle.schema !== EXTERNAL_AGENT_EVENT_BUNDLE_SCHEMA) issue(issues, '$.schema', 'INVALID_SCHEMA', `schema must be ${EXTERNAL_AGENT_EVENT_BUNDLE_SCHEMA}`)
  requiredString(bundle, 'bundleId', '$', issues)
  requiredString(bundle, 'requestManifestHash', '$', issues, { hash: true })
  requiredString(bundle, 'responseManifestHash', '$', issues, { hash: true })
  if (!Array.isArray(bundle.events) || bundle.events.length < 2 || bundle.events.length > MAX_EXTERNAL_AGENT_BUNDLE_EVENTS) {
    issue(issues, '$.events', 'INVALID_EVENT_COUNT', `events must contain 2-${MAX_EXTERNAL_AGENT_BUNDLE_EVENTS} items`)
    return { valid: false, issues }
  }
  try {
    if (canonicalJsonBytes(bundle) > MAX_EXTERNAL_AGENT_BUNDLE_BYTES) issue(issues, '$', 'BUNDLE_BUDGET_EXCEEDED', `Bundle exceeds ${MAX_EXTERNAL_AGENT_BUNDLE_BYTES} bytes`)
  } catch (error) {
    issue(issues, '$', 'NON_CANONICAL_BUNDLE', error instanceof Error ? error.message : String(error))
  }

  const events = bundle.events as unknown[]
  const validEvents: ExecutionEventEnvelopeV01[] = []
  events.forEach((event, index) => {
    const result = validateExecutionEventEnvelope(event)
    if (!result.valid) {
      result.issues.forEach(item => issue(issues, `$.events[${index}]${item.path.slice(1)}`, `EVENT_${item.code}`, item.message))
    } else {
      validEvents.push(result.value)
      forbidHiddenPayload(result.value.payload, `$.events[${index}].payload`, issues)
    }
  })
  if (validEvents.length !== events.length) return { valid: false, issues }

  const eventIds = new Set<string>()
  validEvents.forEach((event, index) => {
    if (eventIds.has(event.eventId)) issue(issues, `$.events[${index}].eventId`, 'DUPLICATE_EVENT_ID', `Duplicate event id ${event.eventId}`)
    eventIds.add(event.eventId)
    if (index > 0 && event.sequence !== validEvents[index - 1]!.sequence + 1) issue(issues, `$.events[${index}].sequence`, 'NON_CONTIGUOUS_SEQUENCE', 'Bundle event sequences must be contiguous and ordered')
  })
  const userEvents = validEvents.filter(event => event.kind === 'USER_MESSAGE')
  const assistantEvents = validEvents.filter(event => event.kind === 'ASSISTANT_MESSAGE')
  if (userEvents.length !== 1 || validEvents[0]?.kind !== 'USER_MESSAGE') issue(issues, '$.events', 'REQUEST_EVENT_CARDINALITY', 'Bundle must begin with exactly one USER_MESSAGE event')
  if (assistantEvents.length !== 1 || validEvents.at(-1)?.kind !== 'ASSISTANT_MESSAGE') issue(issues, '$.events', 'RESPONSE_EVENT_CARDINALITY', 'Bundle must end with exactly one ASSISTANT_MESSAGE event')
  const userPayload = recordOf(userEvents[0]?.payload)
  const assistantPayload = recordOf(assistantEvents[0]?.payload)
  if (userPayload) exactKeys(userPayload, ['requestManifest'], '$.events[0].payload', issues)
  if (assistantPayload) exactKeys(assistantPayload, ['responseManifest'], `$.events[${validEvents.length - 1}].payload`, issues)
  const request = requestManifest(userPayload?.requestManifest, '$.events[0].payload.requestManifest', issues)
  const response = responseManifest(assistantPayload?.responseManifest, `$.events[${validEvents.length - 1}].payload.responseManifest`, issues)
  if (!request || !response) return { valid: false, issues }
  if (request.userMessage.messageId !== userEvents[0]!.eventId) issue(issues, '$.events[0].eventId', 'USER_MESSAGE_ID_MISMATCH', 'Request visible messageId must equal the USER_MESSAGE eventId')
  if (response.assistantMessage.messageId !== assistantEvents[0]!.eventId) issue(issues, `$.events[${validEvents.length - 1}].eventId`, 'ASSISTANT_MESSAGE_ID_MISMATCH', 'Response visible messageId must equal the ASSISTANT_MESSAGE eventId')

  const binding = ledger.binding
  const expectedIdentity: Readonly<Record<string, string>> = {
    requestId: binding.requestId,
    runtimeId: binding.runtimeId,
    projectId: binding.contract.projectId,
    taskId: binding.contract.taskId,
    turnId: binding.turnId,
    agentId: binding.contract.agentId,
    contextHash: binding.contract.contextHash,
  }
  for (const [key, expected] of Object.entries(expectedIdentity)) {
    if (request[key as keyof ExternalAgentRequestManifestV01] !== expected) issue(issues, `$.events[0].payload.requestManifest.${key}`, 'LEDGER_BINDING_MISMATCH', `${key} does not match the Ledger binding`)
    if (response[key as keyof ExternalAgentResponseManifestV01] !== expected) issue(issues, `$.events[${validEvents.length - 1}].payload.responseManifest.${key}`, 'LEDGER_BINDING_MISMATCH', `${key} does not match the Ledger binding`)
  }
  const contractHash = hashCanonicalJson(binding.contract)
  if (request.contractHash !== contractHash) issue(issues, '$.events[0].payload.requestManifest.contractHash', 'CONTRACT_HASH_MISMATCH', 'Request contractHash does not bind the Ledger contract')
  const actualRequestHash = hashCanonicalJson(request)
  const actualResponseHash = hashCanonicalJson(response)
  if (bundle.requestManifestHash !== actualRequestHash || response.requestManifestHash !== actualRequestHash) issue(issues, '$.requestManifestHash', 'REQUEST_MANIFEST_HASH_MISMATCH', 'Request manifest hash binding is inconsistent')
  if (bundle.responseManifestHash !== actualResponseHash) issue(issues, '$.responseManifestHash', 'RESPONSE_MANIFEST_HASH_MISMATCH', 'Response manifest hash binding is inconsistent')
  if (request.expectedHostId !== response.actualHostId) issue(issues, '$.events', 'HOST_IDENTITY_MISMATCH', 'Actual Host does not match the requested Host')
  if (request.expectedProviderId !== response.actualProviderId) issue(issues, '$.events', 'PROVIDER_IDENTITY_MISMATCH', 'Actual provider does not match the requested provider')
  if (request.expectedModelId !== response.actualModelId) issue(issues, '$.events', 'MODEL_IDENTITY_MISMATCH', 'Actual model does not match the requested model')
  if (request.agentId !== response.actualAgentId) issue(issues, '$.events', 'AGENT_IDENTITY_MISMATCH', 'Actual Agent does not match the requested Agent')
  if (Date.parse(response.completedAt) < Date.parse(request.issuedAt)) issue(issues, '$.events', 'RESPONSE_PRECEDES_REQUEST', 'Response cannot complete before the request was issued')

  validEvents.forEach(event => {
    for (const [key, expected] of Object.entries(expectedIdentity)) {
      if (event[key as keyof ExecutionEventEnvelopeV01] !== expected) issue(issues, `$.events[${event.sequence - validEvents[0]!.sequence}].${key}`, 'EVENT_BINDING_MISMATCH', `${key} does not match the manifest and Ledger binding`)
    }
  })

  const receiptEvents = validEvents.slice(1, -1)
  const refs = new Map(response.receiptRefs.map(ref => [ref.eventId, ref]))
  for (const event of receiptEvents) {
    const ref = refs.get(event.eventId)
    if (!ref) issue(issues, '$.events', 'MISSING_RECEIPT_REF', `Receipt event ${event.eventId} is not declared by the response`)
    else if (ref.payloadHash !== event.payloadHash) issue(issues, '$.events', 'RECEIPT_HASH_MISMATCH', `Receipt reference ${event.eventId} has the wrong payload hash`)
  }
  for (const ref of response.receiptRefs) {
    if (!receiptEvents.some(event => event.eventId === ref.eventId)) issue(issues, '$.events', 'UNKNOWN_RECEIPT_REF', `Receipt reference ${ref.eventId} is not in the bundle`)
  }
  for (const claim of response.claims) {
    for (const evidenceRef of Array.isArray(claim.evidenceRefs) ? claim.evidenceRefs : []) {
      if (!refs.has(evidenceRef)) issue(issues, '$.events', 'UNBOUND_CLAIM_EVIDENCE', `Claim ${claim.id} references undeclared Evidence ${evidenceRef}`)
    }
  }
  const supportedMiddleKinds = new Set([
    'RESOURCE_SEARCH', 'RESOURCE_READ', 'SOURCE_DISPOSITION', 'RESOURCE_WRITE',
    'VALIDATION_RESULT', 'OUTPUT_EMITTED',
  ])
  for (const event of receiptEvents) {
    if (!supportedMiddleKinds.has(event.kind)) {
      issue(issues, '$.events', 'UNSUPPORTED_BUNDLE_EVENT_KIND', `Event kind ${event.kind} is not allowed inside a v0.1 external Agent bundle`)
      continue
    }
    validateReceiptPayload(event, ledger, issues)
  }

  return issues.length === 0
    ? {
        valid: true,
        value: bundle as unknown as ExternalAgentEventBundleV01,
        requestManifest: request,
        responseManifest: response,
        issues: [],
      }
    : { valid: false, issues }
}

/**
 * Re-validates the durable USER_MESSAGE -> receipt events -> ASSISTANT_MESSAGE
 * span during Ledger replay. This is the same whole-span admission used before
 * append, reconstructed only from persisted facts.
 */
export const validatePersistedExternalAgentSpan = (
  events: readonly ExecutionEventEnvelopeV01[],
  binding: ExecutionEventStoreBindingV01,
): ExternalAgentBridgeValidationResultV01 => {
  const request = recordOf(recordOf(events[0]?.payload)?.requestManifest)
  const response = recordOf(recordOf(events.at(-1)?.payload)?.responseManifest)
  if (!request || !response) {
    return {
      valid: false,
      issues: [{
        path: '$.events',
        code: 'MISSING_DURABLE_MANIFEST',
        message: 'Persisted external Agent span must contain both manifests',
      }],
    }
  }
  const replayBundle: ExternalAgentEventBundleV01 = {
    schema: EXTERNAL_AGENT_EVENT_BUNDLE_SCHEMA,
    bundleId: 'durable-replay',
    requestManifestHash: hashCanonicalJson(request),
    responseManifestHash: hashCanonicalJson(response),
    events,
  }
  const ledgerView = { binding } as ExecutionObligationLedgerV01
  return validateExternalAgentEventBundle(replayBundle, ledgerView)
}

export const ingestExternalAgentEventBundle = async (
  ledger: ExecutionObligationLedgerV01,
  value: unknown,
): Promise<ExternalAgentBundleIngestionResultV01> => {
  const validation = validateExternalAgentEventBundle(value, ledger)
  if (!validation.valid) {
    throw new TypeError(validation.issues.map(item => `${item.path} ${item.code}: ${item.message}`).join('\n'))
  }
  const acceptances: ExecutionEventAcceptanceV01[] = []
  const acceptedPrefix: ExecutionEventAcceptanceV01[] = []
  for (const event of validation.value.events) {
    try {
      const acceptance = await ledger.ingest(event)
      acceptances.push(acceptance)
      if (acceptance.status === 'REJECTED') {
        return { acceptances, acceptedPrefix, failure: acceptance }
      }
      acceptedPrefix.push(acceptance)
    } catch (error) {
      return {
        acceptances,
        acceptedPrefix,
        failure: {
          eventId: event.eventId,
          sequence: event.sequence,
          message: error instanceof Error ? error.message : String(error),
        },
      }
    }
  }
  return { acceptances, acceptedPrefix }
}
