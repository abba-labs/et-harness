import { posix } from 'node:path'
import {
  AGENT_CLAIM_KINDS,
  EVIDENCE_PROVIDER_KINDS,
  EVIDENCE_RESULT_STATUSES,
  MANDATORY_LIFECYCLE_CLOSURE_MODULE_IDS,
  OBLIGATION_LEDGER_STATUS_SCHEMA,
  SUPERVISION_LIFECYCLE_BINDING_SCHEMA,
  type AgentClaimV01,
  type ClaimEvidenceSatisfactionV01,
  type ClaimEvidenceTargetV01,
  type CompletionDecisionV01,
  type CreateExecutionObligationLedgerInputV01,
  type ContractValidationIssue,
  type ContractValidationResult,
  type ExecutionEventAcceptanceV01,
  type ExecutionEventEnvelopeV01,
  type ExecutionEventStoreBindingV01,
  type ExecutionEventStoreV01,
  type ExecutionLifecycleAuthorityV01,
  type ExecutionObligationLedgerV01,
  type ExecutionReplayCursorV01,
  type ExecutionStoreFinalizationV01,
  type EvidencePolicyV01,
  type JsonRecord,
  type MutationIntentV01,
  type MutationPreflightDecisionV01,
  type MutationReceiptV01,
  type OutputReceiptV01,
  type OutputSatisfactionV01,
  type OutputTargetV01,
  type ObligationDefinitionV01,
  type ObligationLedgerStatusV01,
  type ObligationState,
  type ObligationStateRecordV01,
  type ObligationViolationRecordV01,
  type RequiredResourceSatisfactionV01,
  type RequiredResourceTargetV01,
  type ResourceReceiptV01,
  type SourceDispositionSatisfactionV01,
  type SourceDispositionTargetV01,
  type SourceDisposition,
  type SupervisionLifecycleBindingV01,
  type SupervisionReadinessReceiptV01,
  type TaskSupervisionContractV01,
  type ValidationReceiptV01,
  type ValidationSatisfactionV01,
  type ValidationTargetV01,
  type WriteScopeTargetV01,
} from './contracts.js'
import { canonicalJson, hashCanonicalJson, sha256Hex } from './hash.js'
import {
  assertLifecycleBindingShape,
  createLifecycleFinalization,
  createSupervisionReadinessReceipt,
  lifecycleClosureRef,
  supervisionFingerprint,
} from './lifecycle-closure.js'
import { evaluateTrustedEvidence } from './trusted-evaluation.js'
import { validateTaskSupervisionContract } from './validation.js'
import {
  EXTERNAL_AGENT_REQUEST_MANIFEST_SCHEMA,
  EXTERNAL_AGENT_RESPONSE_MANIFEST_SCHEMA,
  MAX_EXTERNAL_AGENT_BUNDLE_BYTES,
  MAX_EXTERNAL_AGENT_BUNDLE_EVENTS,
  validatePersistedExternalAgentSpan,
} from './external-agent-bridge.js'

const LEDGER_GENESIS_TIMESTAMP = '1970-01-01T00:00:00.000Z'
const SHA256_PATTERN = /^[0-9a-f]{64}$/
const MAX_LEDGER_STATE_EVIDENCE_REFS = 64
type LedgerProjectionMode = 'COMPACT' | 'LEGACY_READINESS'

interface MutableObligationStateRecord {
  obligationId: string
  state: ObligationState
  updatedAt: string
  accessCount?: number
  evidenceRefsTruncated?: boolean
  eventRefs: string[]
  evidenceRefs: string[]
  blockerRefs: string[]
  violationRefs: string[]
  reason?: string
}

interface ValidationEvidenceCandidate {
  readonly event: ExecutionEventEnvelopeV01
  readonly receipt: ValidationReceiptV01
}

interface OutputEvidenceCandidate {
  readonly event: ExecutionEventEnvelopeV01
  readonly receipt: OutputReceiptV01
}

interface AgentClaimCandidate {
  readonly event: ExecutionEventEnvelopeV01
  readonly claim: AgentClaimV01
}

interface DurableExternalSpanAdmission {
  readonly events: readonly ExecutionEventEnvelopeV01[]
  readonly claims: readonly AgentClaimV01[]
}

const recordOf = (value: unknown): JsonRecord | undefined =>
  typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as JsonRecord
    : undefined

const stringArray = (value: unknown): readonly string[] | undefined =>
  Array.isArray(value) && value.every(item => typeof item === 'string')
    ? value
    : undefined

const canonicalClone = <T>(value: T): T =>
  JSON.parse(canonicalJson(value)) as T

const deepFreeze = <T>(value: T): T => {
  if (typeof value !== 'object' || value === null || Object.isFrozen(value)) {
    return value
  }
  Object.freeze(value)
  for (const child of Object.values(value as Record<string, unknown>)) {
    deepFreeze(child)
  }
  return value
}

const immutableSnapshot = <T>(value: T): T =>
  deepFreeze(canonicalClone(value))

const exactRecordKeys = (record: JsonRecord, keys: readonly string[]): boolean => {
  const actual = Object.keys(record).sort()
  const expected = [...keys].sort()
  return canonicalJson(actual) === canonicalJson(expected)
}

const uniqueAppend = (values: string[], value: string): void => {
  if (!values.includes(value)) values.push(value)
}

const boundedUniqueAppend = (
  values: string[],
  value: string,
  maxItems: number,
): boolean => {
  if (values.includes(value)) return false
  const truncated = values.length >= maxItems
  if (truncated) values.splice(0, values.length - maxItems + 1)
  values.push(value)
  return truncated
}

const replaceWithLatest = (values: string[], value: string): void => {
  if (values.length === 1 && values[0] === value) return
  values.splice(0, values.length, value)
}

const validationIdentityKey = (validationId: string, targetIdentity: string): string =>
  `${validationId}\u0000${targetIdentity}`

const outputIdentityKey = (outputContractId: string): string => outputContractId

const exactKeys = (
  record: JsonRecord,
  keys: readonly string[],
  path: string,
  issues: ContractValidationIssue[],
): void => {
  const allowed = new Set(keys)
  for (const key of Object.keys(record)) {
    if (!allowed.has(key)) {
      issues.push({
        path: `${path}.${key}`,
        code: 'LEDGER_UNKNOWN_FIELD',
        message: `Unknown structured obligation field ${key}`,
      })
    }
  }
}

const nonEmptyUniqueStrings = (
  value: unknown,
  path: string,
  issues: ContractValidationIssue[],
  allowEmpty = false,
): readonly string[] | undefined => {
  if (!Array.isArray(value)
      || value.some(item => typeof item !== 'string' || item.length === 0)
      || (!allowEmpty && value.length === 0)) {
    issues.push({
      path,
      code: 'LEDGER_INVALID_STRING_ARRAY',
      message: `${path} must be ${allowEmpty ? 'an' : 'a non-empty'} array of non-empty strings`,
    })
    return undefined
  }
  if (new Set(value).size !== value.length) {
    issues.push({
      path,
      code: 'LEDGER_DUPLICATE_ITEM',
      message: `${path} must not contain duplicate values`,
    })
  }
  return value
}

export const validateObligationLedgerContribution = (
  value: unknown,
): ContractValidationResult<TaskSupervisionContractV01> => {
  const base = validateTaskSupervisionContract(value)
  if (!base.valid) return base
  const issues: ContractValidationIssue[] = []
  const writeScopeCount = base.value.obligations
    .filter(obligation => obligation.kind === 'WRITE_SCOPE')
    .length
  if (writeScopeCount > 1) {
    issues.push({
      path: '$.obligations',
      code: 'LEDGER_MULTIPLE_WRITE_SCOPES_UNSUPPORTED',
      message: 'Phase 2 v0.1 accepts at most one WRITE_SCOPE obligation',
    })
  }
  if (!base.value.completionPolicy.requireAllMustSatisfied) {
    issues.push({
      path: '$.completionPolicy.requireAllMustSatisfied',
      code: 'LEDGER_ALL_MUST_REQUIRED',
      message: 'Pre-Closure readiness requires every execution-stage MUST obligation',
    })
  }
  if (!base.value.completionPolicy.requireNoViolations) {
    issues.push({
      path: '$.completionPolicy.requireNoViolations',
      code: 'LEDGER_NO_VIOLATIONS_REQUIRED',
      message: 'Pre-Closure readiness requires no current blocking violation',
    })
  }
  const evidencePolicyCountByObligationId = new Map<string, number>()
  for (const policy of base.value.evidencePolicies) {
    for (const obligationId of policy.obligationIds) {
      evidencePolicyCountByObligationId.set(
        obligationId,
        (evidencePolicyCountByObligationId.get(obligationId) ?? 0) + 1,
      )
    }
    if (policy.requireExactProjectRevision && base.value.projectRevision === undefined) {
      issues.push({
        path: `$.evidencePolicies[${base.value.evidencePolicies.indexOf(policy)}].requireExactProjectRevision`,
        code: 'LEDGER_PROJECT_REVISION_REQUIRED',
        message: 'Exact project revision Evidence requires a projectRevision in the Task contract',
      })
    }
  }
  base.value.obligations.forEach((obligation, index) => {
    const path = `$.obligations[${index}]`
    if (obligation.kind === 'REQUIRED_RESOURCE') {
      const target = recordOf(obligation.target)!
      const satisfaction = recordOf(obligation.satisfaction)!
      exactKeys(target, ['resourceId', 'revision', 'contentHash'], `${path}.target`, issues)
      exactKeys(
        satisfaction,
        ['acceptedProviderIds', 'acceptedDispositions', 'requireContentHash'],
        `${path}.satisfaction`,
        issues,
      )
      if (typeof target.resourceId !== 'string' || target.resourceId.length === 0) {
        issues.push({
          path: `${path}.target.resourceId`,
          code: 'LEDGER_RESOURCE_ID_REQUIRED',
          message: 'REQUIRED_RESOURCE target requires resourceId',
        })
      }
      for (const field of ['revision', 'contentHash'] as const) {
        if (field in target && (typeof target[field] !== 'string' || target[field].length === 0)) {
          issues.push({
            path: `${path}.target.${field}`,
            code: 'LEDGER_INVALID_RESOURCE_IDENTITY',
            message: `${field} must be a non-empty string when declared`,
          })
        }
      }
      nonEmptyUniqueStrings(
        satisfaction.acceptedProviderIds,
        `${path}.satisfaction.acceptedProviderIds`,
        issues,
      )
      const dispositions = nonEmptyUniqueStrings(
        satisfaction.acceptedDispositions,
        `${path}.satisfaction.acceptedDispositions`,
        issues,
      )
      for (const disposition of dispositions ?? []) {
        if (disposition !== 'FOUND') {
          issues.push({
            path: `${path}.satisfaction.acceptedDispositions`,
            code: 'LEDGER_REQUIRED_RESOURCE_REQUIRES_FOUND',
            message: 'REQUIRED_RESOURCE may only be satisfied by FOUND; source disposition is a separate obligation',
          })
        }
      }
      if ('requireContentHash' in satisfaction
          && typeof satisfaction.requireContentHash !== 'boolean') {
        issues.push({
          path: `${path}.satisfaction.requireContentHash`,
          code: 'LEDGER_INVALID_BOOLEAN',
          message: 'requireContentHash must be boolean when declared',
        })
      }
      if (typeof target.contentHash === 'string'
          && !SHA256_PATTERN.test(target.contentHash)) {
        issues.push({
          path: `${path}.target.contentHash`,
          code: 'LEDGER_INVALID_CONTENT_HASH',
          message: 'contentHash must be a lowercase SHA-256 digest',
        })
      }
    } else if (obligation.kind === 'SOURCE_DISPOSITION') {
      const target = recordOf(obligation.target)!
      const satisfaction = recordOf(obligation.satisfaction)!
      exactKeys(target, ['resourceId'], `${path}.target`, issues)
      exactKeys(
        satisfaction,
        ['acceptedProviderIds', 'acceptedDispositions'],
        `${path}.satisfaction`,
        issues,
      )
      if (typeof target.resourceId !== 'string' || target.resourceId.length === 0) {
        issues.push({
          path: `${path}.target.resourceId`,
          code: 'LEDGER_RESOURCE_ID_REQUIRED',
          message: 'SOURCE_DISPOSITION target requires resourceId',
        })
      }
      nonEmptyUniqueStrings(
        satisfaction.acceptedProviderIds,
        `${path}.satisfaction.acceptedProviderIds`,
        issues,
      )
      const dispositions = nonEmptyUniqueStrings(
        satisfaction.acceptedDispositions,
        `${path}.satisfaction.acceptedDispositions`,
        issues,
      )
      if ((dispositions ?? []).some(item => !['NO_MATCH', 'UNAVAILABLE'].includes(item))) {
        issues.push({
          path: `${path}.satisfaction.acceptedDispositions`,
          code: 'LEDGER_INVALID_SOURCE_DISPOSITION',
          message: 'SOURCE_DISPOSITION accepts only NO_MATCH or UNAVAILABLE',
        })
      }
    } else if (obligation.kind === 'WRITE_SCOPE') {
      const target = recordOf(obligation.target)!
      const satisfaction = recordOf(obligation.satisfaction)!
      exactKeys(target, ['allowedResourceIds', 'allowedPathPrefixes'], `${path}.target`, issues)
      exactKeys(satisfaction, ['requireInScope'], `${path}.satisfaction`, issues)
      const resourceIds = nonEmptyUniqueStrings(
        target.allowedResourceIds,
        `${path}.target.allowedResourceIds`,
        issues,
        true,
      )
      const pathPrefixes = target.allowedPathPrefixes === undefined
        ? []
        : nonEmptyUniqueStrings(
          target.allowedPathPrefixes,
          `${path}.target.allowedPathPrefixes`,
          issues,
          true,
        )
      if ((resourceIds?.length ?? 0) === 0 && (pathPrefixes?.length ?? 0) === 0) {
        issues.push({
          path: `${path}.target`,
          code: 'LEDGER_EMPTY_WRITE_SCOPE',
          message: 'WRITE_SCOPE must declare at least one allowed resource or path prefix',
        })
      }
      if (satisfaction.requireInScope !== true) {
        issues.push({
          path: `${path}.satisfaction.requireInScope`,
          code: 'LEDGER_REQUIRE_IN_SCOPE',
          message: 'WRITE_SCOPE satisfaction must require in-scope mutations',
        })
      }
    } else if (obligation.kind === 'OUTPUT') {
      const target = recordOf(obligation.target)!
      const satisfaction = recordOf(obligation.satisfaction)!
      exactKeys(target, ['outputContractId', 'resourceId', 'contentHash'], `${path}.target`, issues)
      exactKeys(
        satisfaction,
        ['requiredStructuralStatus', 'requiredResultStatus'],
        `${path}.satisfaction`,
        issues,
      )
      if (typeof target.outputContractId !== 'string' || target.outputContractId.length === 0) {
        issues.push({
          path: `${path}.target.outputContractId`,
          code: 'LEDGER_OUTPUT_CONTRACT_REQUIRED',
          message: 'OUTPUT target requires outputContractId',
        })
      }
      for (const field of ['resourceId', 'contentHash'] as const) {
        if (typeof target[field] !== 'string' || target[field].length === 0) {
          issues.push({
            path: `${path}.target.${field}`,
            code: 'LEDGER_INVALID_OUTPUT_IDENTITY',
            message: `OUTPUT target requires non-empty ${field}`,
          })
        }
      }
      if (typeof target.contentHash === 'string' && !SHA256_PATTERN.test(target.contentHash)) {
        issues.push({
          path: `${path}.target.contentHash`,
          code: 'LEDGER_INVALID_CONTENT_HASH',
          message: 'OUTPUT contentHash must be a lowercase SHA-256 digest',
        })
      }
      if (satisfaction.requiredStructuralStatus !== 'PASS'
          || satisfaction.requiredResultStatus !== 'PASS') {
        issues.push({
          path: `${path}.satisfaction`,
          code: 'LEDGER_OUTPUT_REQUIRES_PASS',
          message: 'OUTPUT satisfaction requires structural and Evidence PASS',
        })
      }
    } else if (obligation.kind === 'VALIDATION'
        || obligation.kind === 'RULE_COMPLIANCE') {
      const target = recordOf(obligation.target)!
      const satisfaction = recordOf(obligation.satisfaction)!
      exactKeys(target, ['validationId', 'targetIdentity'], `${path}.target`, issues)
      exactKeys(satisfaction, ['requiredResultStatus'], `${path}.satisfaction`, issues)
      for (const field of ['validationId', 'targetIdentity'] as const) {
        if (typeof target[field] !== 'string' || target[field].length === 0) {
          issues.push({
            path: `${path}.target.${field}`,
            code: 'LEDGER_VALIDATION_IDENTITY_REQUIRED',
            message: `${obligation.kind} target requires ${field}`,
          })
        }
      }
      if (satisfaction.requiredResultStatus !== 'PASS') {
        issues.push({
          path: `${path}.satisfaction.requiredResultStatus`,
          code: 'LEDGER_VALIDATION_REQUIRES_PASS',
          message: `${obligation.kind} satisfaction requires PASS`,
        })
      }
    } else if (obligation.kind === 'CLAIM_EVIDENCE') {
      const target = recordOf(obligation.target)!
      const satisfaction = recordOf(obligation.satisfaction)!
      exactKeys(target, ['claimKinds', 'targetIdentities'], `${path}.target`, issues)
      exactKeys(
        satisfaction,
        ['requireEvidenceForPassClaims'],
        `${path}.satisfaction`,
        issues,
      )
      const claimKinds = nonEmptyUniqueStrings(
        target.claimKinds,
        `${path}.target.claimKinds`,
        issues,
      )
      if ((claimKinds ?? []).some(kind => !AGENT_CLAIM_KINDS.includes(kind as never))) {
        issues.push({
          path: `${path}.target.claimKinds`,
          code: 'LEDGER_INVALID_CLAIM_KIND',
          message: 'CLAIM_EVIDENCE contains an unsupported claim kind',
        })
      }
      if (target.targetIdentities !== undefined) {
        nonEmptyUniqueStrings(
          target.targetIdentities,
          `${path}.target.targetIdentities`,
          issues,
          true,
        )
      }
      if (satisfaction.requireEvidenceForPassClaims !== true) {
        issues.push({
          path: `${path}.satisfaction.requireEvidenceForPassClaims`,
          code: 'LEDGER_CLAIM_EVIDENCE_REQUIRED',
          message: 'CLAIM_EVIDENCE must require Evidence for PASS claims',
        })
      }
    }

    if (['OUTPUT', 'VALIDATION', 'CLAIM_EVIDENCE', 'RULE_COMPLIANCE']
      .includes(obligation.kind)) {
      const policyCount = evidencePolicyCountByObligationId.get(obligation.id) ?? 0
      if (policyCount !== 1) {
        issues.push({
          path,
          code: 'LEDGER_EXACTLY_ONE_EVIDENCE_POLICY_REQUIRED',
          message: `${obligation.kind} requires exactly one Evidence Policy; received ${policyCount}`,
        })
      }
    }
  })
  return issues.length === 0
    ? { valid: true, issues: [], value: base.value }
    : { valid: false, issues }
}

const requiredResourceTarget = (
  obligation: ObligationDefinitionV01,
): RequiredResourceTargetV01 | undefined => {
  const target = recordOf(obligation.target)
  if (!target || typeof target.resourceId !== 'string') return undefined
  if ('revision' in target && typeof target.revision !== 'string') return undefined
  if ('contentHash' in target && typeof target.contentHash !== 'string') return undefined
  return target as unknown as RequiredResourceTargetV01
}

const requiredResourceSatisfaction = (
  obligation: ObligationDefinitionV01,
): RequiredResourceSatisfactionV01 | undefined => {
  const satisfaction = recordOf(obligation.satisfaction)
  if (!satisfaction) return undefined
  const acceptedProviderIds = stringArray(satisfaction.acceptedProviderIds)
  const acceptedDispositions = stringArray(satisfaction.acceptedDispositions)
  if (!acceptedProviderIds || acceptedProviderIds.length === 0
      || !acceptedDispositions || acceptedDispositions.length === 0) {
    return undefined
  }
  const dispositions = acceptedDispositions as readonly SourceDisposition[]
  if (dispositions.some(item => !['FOUND', 'NO_MATCH', 'UNAVAILABLE'].includes(item))) {
    return undefined
  }
  if ('requireContentHash' in satisfaction
      && typeof satisfaction.requireContentHash !== 'boolean') {
    return undefined
  }
  return satisfaction as unknown as RequiredResourceSatisfactionV01
}

const resourceReceipt = (event: ExecutionEventEnvelopeV01): ResourceReceiptV01 | undefined => {
  const payload = recordOf(event.payload)
  const receipt = recordOf(payload?.receipt)
  if (!receipt
      || typeof receipt.provider !== 'string'
      || typeof receipt.resourceId !== 'string'
      || typeof receipt.purpose !== 'string'
      || !stringArray(receipt.claimRefs)
      || !['FOUND', 'NO_MATCH', 'UNAVAILABLE'].includes(String(receipt.disposition))) {
    return undefined
  }
  for (const field of [
    'path',
    'revision',
    'modifiedAt',
    'contentHash',
    'error',
  ] as const) {
    if (field in receipt && typeof receipt[field] !== 'string') return undefined
  }
  if (typeof receipt.contentHash === 'string'
      && !SHA256_PATTERN.test(receipt.contentHash)) return undefined
  return receipt as unknown as ResourceReceiptV01
}

const mutationReceipt = (event: ExecutionEventEnvelopeV01): MutationReceiptV01 | undefined => {
  const payload = recordOf(event.payload)
  const receipt = recordOf(payload?.receipt)
  if (!receipt
      || typeof receipt.resourceId !== 'string'
      || typeof receipt.action !== 'string'
      || typeof receipt.scopeDecision !== 'string'
      || typeof receipt.executorId !== 'string') {
    return undefined
  }
  if (!['CREATE', 'UPDATE', 'DELETE', 'MOVE', 'COPY'].includes(receipt.action)) {
    return undefined
  }
  if (!['ALLOWED', 'PROTECTED', 'OUTSIDE_SCOPE', 'UNKNOWN']
    .includes(receipt.scopeDecision)) return undefined
  for (const field of ['path', 'beforeHash', 'afterHash'] as const) {
    if (field in receipt && typeof receipt[field] !== 'string') return undefined
  }
  return receipt as unknown as MutationReceiptV01
}

const isCanonicalTimestamp = (value: unknown): value is string => {
  if (typeof value !== 'string') return false
  const milliseconds = Date.parse(value)
  return Number.isFinite(milliseconds)
    && new Date(milliseconds).toISOString() === value
}

const validationReceipt = (
  event: ExecutionEventEnvelopeV01,
): ValidationReceiptV01 | undefined => {
  const payload = recordOf(event.payload)
  const receipt = recordOf(payload?.receipt)
  if (!receipt
      || typeof receipt.providerId !== 'string'
      || !EVIDENCE_PROVIDER_KINDS.includes(receipt.providerKind as never)
      || typeof receipt.validationId !== 'string'
      || typeof receipt.commandOrTestIdentity !== 'string'
      || typeof receipt.contextHash !== 'string'
      || !SHA256_PATTERN.test(receipt.contextHash)
      || typeof receipt.targetIdentity !== 'string'
      || !EVIDENCE_RESULT_STATUSES.includes(receipt.resultStatus as never)
      || !stringArray(receipt.artifactRefs)
      || !stringArray(receipt.evidenceRefs)
      || !stringArray(receipt.claimRefs)
      || !isCanonicalTimestamp(receipt.timestamp)) {
    return undefined
  }
  if ('projectRevision' in receipt
      && typeof receipt.projectRevision !== 'string') return undefined
  return receipt as unknown as ValidationReceiptV01
}

const outputReceipt = (
  event: ExecutionEventEnvelopeV01,
): OutputReceiptV01 | undefined => {
  const payload = recordOf(event.payload)
  const receipt = recordOf(payload?.receipt)
  if (!receipt
      || typeof receipt.providerId !== 'string'
      || !EVIDENCE_PROVIDER_KINDS.includes(receipt.providerKind as never)
      || typeof receipt.outputContractId !== 'string'
      || typeof receipt.resourceId !== 'string'
      || typeof receipt.contentHash !== 'string'
      || !SHA256_PATTERN.test(receipt.contentHash)
      || typeof receipt.contextHash !== 'string'
      || !SHA256_PATTERN.test(receipt.contextHash)
      || typeof receipt.targetIdentity !== 'string'
      || !['PASS', 'FAIL', 'NOT_EXECUTED'].includes(String(receipt.structuralValidationStatus))
      || !stringArray(receipt.ruleValidationRefs)
      || !stringArray(receipt.evidenceRefs)
      || !stringArray(receipt.claimRefs)
      || !isCanonicalTimestamp(receipt.timestamp)) {
    return undefined
  }
  for (const field of ['path', 'projectRevision'] as const) {
    if (field in receipt && typeof receipt[field] !== 'string') return undefined
  }
  return receipt as unknown as OutputReceiptV01
}

const agentClaims = (event: ExecutionEventEnvelopeV01): readonly AgentClaimV01[] => {
  const payload = recordOf(event.payload)
  const manifest = recordOf(payload?.responseManifest)
  if (!Array.isArray(manifest?.claims)) return []
  const claims: AgentClaimV01[] = []
  for (const value of manifest.claims) {
    const claim = recordOf(value)
    if (!claim
        || typeof claim.id !== 'string'
        || !AGENT_CLAIM_KINDS.includes(claim.kind as never)
        || typeof claim.targetIdentity !== 'string'
        || !EVIDENCE_RESULT_STATUSES.includes(claim.resultStatus as never)
        || !stringArray(claim.evidenceRefs)) continue
    if (('validationId' in claim && typeof claim.validationId !== 'string')
        || ('outputContractId' in claim
          && typeof claim.outputContractId !== 'string')) continue
    const keys = ['id', 'kind', 'targetIdentity', 'resultStatus', 'evidenceRefs']
    if (claim.kind === 'OUTPUT') {
      if (typeof claim.outputContractId !== 'string' || 'validationId' in claim) continue
      keys.push('outputContractId')
    } else {
      if (typeof claim.validationId !== 'string' || 'outputContractId' in claim) continue
      keys.push('validationId')
    }
    if (!exactRecordKeys(claim, keys)) continue
    claims.push(claim as unknown as AgentClaimV01)
  }
  return claims
}

const durableExternalSpanAdmission = (
  events: readonly ExecutionEventEnvelopeV01[],
  binding: ExecutionEventStoreBindingV01,
): DurableExternalSpanAdmission | undefined => {
  if (events.length < 2
      || events[0]?.kind !== 'USER_MESSAGE'
      || events.at(-1)?.kind !== 'ASSISTANT_MESSAGE') return undefined
  if (!validatePersistedExternalAgentSpan(events, binding).valid) return undefined
  const first = events[0]!
  const last = events.at(-1)!
  if (!events.every((event, index) => index === 0
    || event.sequence === events[index - 1]!.sequence + 1)) return undefined
  const requestPayload = recordOf(first.payload)
  const responsePayload = recordOf(last.payload)
  if (!requestPayload || !responsePayload
      || !exactRecordKeys(requestPayload, ['requestManifest'])
      || !exactRecordKeys(responsePayload, ['responseManifest'])) return undefined
  const request = recordOf(requestPayload.requestManifest)
  const response = recordOf(responsePayload.responseManifest)
  if (!request || !response
      || request.schema !== EXTERNAL_AGENT_REQUEST_MANIFEST_SCHEMA
      || response.schema !== EXTERNAL_AGENT_RESPONSE_MANIFEST_SCHEMA
      || !exactRecordKeys(request, [
        'schema', 'requestId', 'runtimeId', 'projectId', 'taskId', 'turnId',
        'agentId', 'contextHash', 'contractHash', 'expectedHostId',
        'expectedProviderId', 'expectedModelId', 'userMessage', 'issuedAt',
      ])
      || !exactRecordKeys(response, [
        'schema', 'requestManifestHash', 'requestId', 'runtimeId', 'projectId',
        'taskId', 'turnId', 'agentId', 'contextHash', 'responseId',
        'actualHostId', 'actualProviderId', 'actualModelId', 'actualAgentId',
        'assistantMessage', 'claims', 'receiptRefs', 'completedAt',
      ])) return undefined
  const identity = {
    requestId: binding.requestId,
    runtimeId: binding.runtimeId,
    projectId: binding.contract.projectId,
    taskId: binding.contract.taskId,
    turnId: binding.turnId,
    agentId: binding.contract.agentId,
    contextHash: binding.contract.contextHash,
  }
  for (const [key, expected] of Object.entries(identity)) {
    if (request[key] !== expected || response[key] !== expected) return undefined
  }
  if (request.contractHash !== hashCanonicalJson(binding.contract)
      || response.requestManifestHash !== hashCanonicalJson(request)
      || request.expectedHostId !== response.actualHostId
      || request.expectedProviderId !== response.actualProviderId
      || request.expectedModelId !== response.actualModelId
      || request.agentId !== response.actualAgentId) return undefined
  const issuedAt = Date.parse(String(request.issuedAt))
  const completedAt = Date.parse(String(response.completedAt))
  if (!Number.isFinite(issuedAt) || !Number.isFinite(completedAt)
      || completedAt < issuedAt) return undefined
  const userMessage = recordOf(request.userMessage)
  const assistantMessage = recordOf(response.assistantMessage)
  if (!userMessage || !assistantMessage
      || userMessage.messageId !== first.eventId
      || assistantMessage.messageId !== last.eventId
      || typeof userMessage.content !== 'string'
      || userMessage.contentHash !== sha256Hex(userMessage.content)
      || typeof assistantMessage.content !== 'string'
      || assistantMessage.contentHash !== sha256Hex(assistantMessage.content)
      || !exactRecordKeys(userMessage, ['messageId', 'content', 'contentHash'])
      || !exactRecordKeys(assistantMessage, ['messageId', 'content', 'contentHash'])) {
    return undefined
  }
  const refs = Array.isArray(response.receiptRefs) ? response.receiptRefs : undefined
  if (!refs || refs.length !== events.length - 2) return undefined
  const middle = events.slice(1, -1)
  const allowedMiddleKinds = new Set([
    'RESOURCE_SEARCH', 'RESOURCE_READ', 'SOURCE_DISPOSITION', 'RESOURCE_WRITE',
    'VALIDATION_RESULT', 'OUTPUT_EMITTED',
  ])
  if (middle.some(event => !allowedMiddleKinds.has(event.kind))) return undefined
  const refById = new Map<string, string>()
  for (const value of refs) {
    const ref = recordOf(value)
    if (!ref || typeof ref.eventId !== 'string'
        || typeof ref.payloadHash !== 'string'
        || refById.has(ref.eventId)) return undefined
    refById.set(ref.eventId, ref.payloadHash)
  }
  if (!middle.every(event => refById.get(event.eventId) === event.payloadHash)) {
    return undefined
  }
  const claims = agentClaims(last)
  if (!Array.isArray(response.claims) || claims.length !== response.claims.length) {
    return undefined
  }
  const declaredRefs = new Set(refById.keys())
  if (claims.some(claim => claim.evidenceRefs.some(ref => !declaredRefs.has(ref)))) {
    return undefined
  }
  return { events: middle, claims }
}

const startsDurableExternalSpan = (event: ExecutionEventEnvelopeV01): boolean => {
  if (event.kind !== 'USER_MESSAGE') return false
  const payload = recordOf(event.payload)
  const manifest = recordOf(payload?.requestManifest)
  return payload !== undefined
    && exactRecordKeys(payload, ['requestManifest'])
    && manifest?.schema === EXTERNAL_AGENT_REQUEST_MANIFEST_SCHEMA
}

const readMatches = (
  obligation: ObligationDefinitionV01,
  receipt: ResourceReceiptV01,
): boolean => {
  const target = requiredResourceTarget(obligation)
  const satisfaction = requiredResourceSatisfaction(obligation)
  if (!target || !satisfaction) return false
  if (receipt.resourceId !== target.resourceId) return false
  if (!satisfaction.acceptedProviderIds.includes(receipt.provider)) return false
  if (!satisfaction.acceptedDispositions.includes(receipt.disposition)) return false
  if (target.revision !== undefined && receipt.revision !== target.revision) return false
  if (target.contentHash !== undefined && receipt.contentHash !== target.contentHash) return false
  if (satisfaction.requireContentHash === true && receipt.contentHash === undefined) return false
  return true
}

const sourceDispositionMatches = (
  obligation: ObligationDefinitionV01,
  receipt: ResourceReceiptV01,
): boolean => {
  const target = recordOf(obligation.target) as SourceDispositionTargetV01 | undefined
  const satisfaction = recordOf(obligation.satisfaction) as
    | SourceDispositionSatisfactionV01
    | undefined
  if (!target || !satisfaction) return false
  return receipt.resourceId === target.resourceId
    && satisfaction.acceptedProviderIds.includes(receipt.provider)
    && satisfaction.acceptedDispositions.includes(
      receipt.disposition as 'NO_MATCH' | 'UNAVAILABLE',
    )
}

const normalizedPath = (value: string): string => {
  const normalized = posix.normalize(value.replaceAll('\\', '/'))
  return normalized.length > 1 && normalized.endsWith('/')
    ? normalized.slice(0, -1)
    : normalized
}

const pathWithinPrefix = (path: string, prefix: string): boolean => {
  const candidate = normalizedPath(path)
  const boundary = normalizedPath(prefix)
  return candidate === boundary || candidate.startsWith(`${boundary}/`)
}

const mutationAllowed = (
  obligation: ObligationDefinitionV01,
  mutation: MutationIntentV01,
): boolean => {
  // The v0.1 mutation receipt has only one path/resource identity and cannot
  // prove both endpoints of MOVE or COPY. Fail closed until that contract grows.
  if (mutation.action === 'MOVE' || mutation.action === 'COPY') return false
  const target = recordOf(obligation.target)
  const satisfaction = recordOf(obligation.satisfaction)
  if (!target || satisfaction?.requireInScope !== true) return false
  const allowedResourceIds = stringArray(target.allowedResourceIds)
  const allowedPathPrefixes = target.allowedPathPrefixes === undefined
    ? []
    : stringArray(target.allowedPathPrefixes)
  if (!allowedResourceIds || !allowedPathPrefixes) return false
  if (allowedResourceIds.includes(mutation.resourceId)) return true
  return mutation.path !== undefined
    && allowedPathPrefixes.some(prefix => pathWithinPrefix(mutation.path!, prefix))
}

const writeAllowed = (
  obligation: ObligationDefinitionV01,
  receipt: MutationReceiptV01,
): boolean => mutationAllowed(obligation, receipt)

const validMutationIntent = (intent: MutationIntentV01): boolean => {
  const record = recordOf(intent)
  if (!record) return false
  const keys = Object.keys(record).sort()
  const expected = (intent.path === undefined
    ? ['action', 'resourceId']
    : ['action', 'path', 'resourceId']).sort()
  return keys.length === expected.length
    && keys.every((key, index) => key === expected[index])
    && typeof intent.resourceId === 'string'
    && intent.resourceId.trim().length > 0
    && ['CREATE', 'UPDATE', 'DELETE', 'MOVE', 'COPY'].includes(intent.action)
    && (intent.path === undefined
      || (typeof intent.path === 'string' && intent.path.trim().length > 0))
}

/** Deterministic hot-path scope decision; it never changes Ledger state. */
export const evaluateMutationPreflight = (
  contract: TaskSupervisionContractV01,
  intent: MutationIntentV01,
): MutationPreflightDecisionV01 => {
  if (!validMutationIntent(intent)) {
    return {
      allowed: false,
      reason: 'Mutation intent is malformed or contains undeclared fields.',
    }
  }
  const writeScope = contract.obligations.find(definition => definition.kind === 'WRITE_SCOPE')
  if (!writeScope) return { allowed: true }
  if (mutationAllowed(writeScope, intent)) {
    return { allowed: true, obligationId: writeScope.id }
  }
  return {
    allowed: false,
    obligationId: writeScope.id,
    reason: `Mutation is outside WRITE_SCOPE obligation ${writeScope.id}.`,
  }
}

const violationFor = (
  obligation: ObligationDefinitionV01,
  event: ExecutionEventEnvelopeV01,
  receipt: MutationReceiptV01,
): ObligationViolationRecordV01 => {
  const id = `violation-${hashCanonicalJson({
    code: 'OUT_OF_SCOPE_WRITE',
    eventId: event.eventId,
    obligationId: obligation.id,
  })}`
  return {
    id,
    code: 'OUT_OF_SCOPE_WRITE',
    obligationId: obligation.id,
    severity: obligation.severity,
    eventId: event.eventId,
    sequence: event.sequence,
    observedAt: event.timestamp,
    resourceId: receipt.resourceId,
    ...(receipt.path === undefined ? {} : { path: receipt.path }),
    action: receipt.action,
    executorId: receipt.executorId,
  }
}

class ExecutionObligationLedger implements ExecutionObligationLedgerV01 {
  readonly #eventStore: ExecutionEventStoreV01
  readonly #lifecycleAuthority: ExecutionLifecycleAuthorityV01 | undefined
  readonly #projectionMode: LedgerProjectionMode
  readonly #ignoreFinalization: boolean
  readonly #binding: ExecutionEventStoreBindingV01
  readonly #contractHash: string
  readonly #definitions: readonly ObligationDefinitionV01[]
  readonly #definitionsById: ReadonlyMap<string, ObligationDefinitionV01>
  readonly #dependentsById: ReadonlyMap<string, readonly string[]>
  readonly #resourceDefinitionsById = new Map<string, ObligationDefinitionV01[]>()
  readonly #writeScopeDefinitions: ObligationDefinitionV01[] = []
  readonly #evidencePolicyByObligationId: ReadonlyMap<string, EvidencePolicyV01>
  readonly #states: Map<string, MutableObligationStateRecord>
  readonly #violations: ObligationViolationRecordV01[] = []
  readonly #violationIds = new Set<string>()
  readonly #validationCandidates: ValidationEvidenceCandidate[] = []
  readonly #outputCandidates: OutputEvidenceCandidate[] = []
  readonly #validationCandidatesByKey = new Map<string, ValidationEvidenceCandidate[]>()
  readonly #outputCandidatesByKey = new Map<string, OutputEvidenceCandidate[]>()
  readonly #validationDefinitionsByKey = new Map<string, ObligationDefinitionV01[]>()
  readonly #outputDefinitionsByKey = new Map<string, ObligationDefinitionV01[]>()
  readonly #claimCandidates: AgentClaimCandidate[] = []
  readonly #trustedFailureObligationIds = new Set<string>()
  readonly #intrinsicallySatisfiedIds = new Set<string>()
  #openExternalSpan: ExecutionEventEnvelopeV01[] | undefined
  #openExternalSpanBytes = 0
  #cursor: ExecutionReplayCursorV01 | undefined
  #taskEndEvent: ExecutionEventEnvelopeV01 | undefined
  #appliedLifecycleFinalizationHash: string | undefined
  #readinessReceipt: SupervisionReadinessReceiptV01 | undefined
  #readinessCursorStateHash: string | undefined
  #completionDecision: CompletionDecisionV01 = {
    status: 'IN_PROGRESS',
    pendingObligationIds: [],
    violatedObligationIds: [],
    blockerRefs: [],
    evidenceRefs: [],
  }

  constructor(
    eventStore: ExecutionEventStoreV01,
    lifecycleAuthority?: ExecutionLifecycleAuthorityV01,
    projectionMode: LedgerProjectionMode = 'COMPACT',
    ignoreFinalization = false,
  ) {
    this.#eventStore = eventStore
    this.#lifecycleAuthority = lifecycleAuthority
    this.#projectionMode = projectionMode
    this.#ignoreFinalization = ignoreFinalization
    this.#binding = immutableSnapshot(eventStore.binding)
    this.#contractHash = hashCanonicalJson(this.#binding.contract)
    this.#definitions = this.#binding.contract.obligations
    this.#definitionsById = new Map(this.#definitions.map(item => [item.id, item]))
    for (const definition of this.#definitions) {
      if (definition.kind === 'REQUIRED_RESOURCE' || definition.kind === 'SOURCE_DISPOSITION') {
        const target = recordOf(definition.target)
        if (typeof target?.resourceId === 'string') {
          const values = this.#resourceDefinitionsById.get(target.resourceId) ?? []
          values.push(definition)
          this.#resourceDefinitionsById.set(target.resourceId, values)
        }
      } else if (definition.kind === 'WRITE_SCOPE') {
        this.#writeScopeDefinitions.push(definition)
      } else if (definition.kind === 'VALIDATION' || definition.kind === 'RULE_COMPLIANCE') {
        const target = recordOf(definition.target) as unknown as ValidationTargetV01
        const key = validationIdentityKey(target.validationId, target.targetIdentity)
        const values = this.#validationDefinitionsByKey.get(key) ?? []
        values.push(definition)
        this.#validationDefinitionsByKey.set(key, values)
      } else if (definition.kind === 'OUTPUT') {
        const target = recordOf(definition.target) as unknown as OutputTargetV01
        const key = outputIdentityKey(target.outputContractId)
        const values = this.#outputDefinitionsByKey.get(key) ?? []
        values.push(definition)
        this.#outputDefinitionsByKey.set(key, values)
      }
    }
    const policies = new Map<string, EvidencePolicyV01>()
    for (const policy of this.#binding.contract.evidencePolicies) {
      for (const obligationId of policy.obligationIds) policies.set(obligationId, policy)
    }
    this.#evidencePolicyByObligationId = policies
    const dependents = new Map<string, string[]>()
    for (const definition of this.#definitions) {
      for (const dependency of definition.dependencies ?? []) {
        const values = dependents.get(dependency) ?? []
        values.push(definition.id)
        dependents.set(dependency, values)
      }
    }
    this.#dependentsById = dependents
    this.#states = new Map(this.#definitions.map(definition => {
      const blockers = [...(definition.dependencies ?? [])]
      return [definition.id, {
        obligationId: definition.id,
        state: blockers.length === 0 ? 'PENDING' : 'BLOCKED',
        updatedAt: LEDGER_GENESIS_TIMESTAMP,
        ...(this.#projectionMode === 'COMPACT'
          && ['REQUIRED_RESOURCE', 'SOURCE_DISPOSITION'].includes(definition.kind)
          ? { accessCount: 0, evidenceRefsTruncated: false }
          : {}),
        eventRefs: [],
        evidenceRefs: [],
        blockerRefs: blockers,
        violationRefs: [],
      }]
    }))
  }

  get binding(): ExecutionEventStoreBindingV01 {
    return immutableSnapshot(this.#binding)
  }

  get cursor(): ExecutionReplayCursorV01 {
    if (!this.#cursor) throw new Error('Obligation Ledger has not synchronized')
    return immutableSnapshot(this.#cursor)
  }

  async ingest(
    event: ExecutionEventEnvelopeV01,
  ): Promise<ExecutionEventAcceptanceV01> {
    const acceptance = await this.#eventStore.append(event)
    if (acceptance.status === 'ACCEPTED') {
      await this.synchronize()
      if (event.kind === 'TASK_END_REQUEST') await this.#refreshReadinessReceipt()
    }
    return acceptance
  }

  async synchronize(): Promise<void> {
    while (true) {
      const page = await this.#eventStore.replay({
        ...(this.#cursor === undefined ? {} : { after: this.#cursor }),
        limit: this.#eventStore.limits.maxReplayEvents,
      })
      for (const event of page.events) this.#applyEvent(event)
      this.#cursor = page.cursor
      if (!page.hasMore) break
    }
    if (!this.#ignoreFinalization && this.#eventStore.finalization) {
      if (this.#projectionMode === 'COMPACT') await this.#refreshReadinessReceipt()
      await this.#applyDurableLifecycleBinding(this.#eventStore.finalization)
    }
  }

  async prepareReadiness(): Promise<SupervisionReadinessReceiptV01 | undefined> {
    await this.synchronize()
    if (this.#projectionMode === 'COMPACT') await this.#refreshReadinessReceipt()
    return this.getReadinessReceipt()
  }

  getStatus(): ObligationLedgerStatusV01 {
    if (!this.#cursor) throw new Error('Obligation Ledger has not synchronized')
    const obligations: ObligationStateRecordV01[] = this.#definitions.map(definition => {
      const state = this.#states.get(definition.id)!
      return {
        obligationId: state.obligationId,
        state: state.state,
        updatedAt: state.updatedAt,
        ...(state.accessCount === undefined ? {} : { accessCount: state.accessCount }),
        ...(state.evidenceRefsTruncated === undefined
          ? {}
          : { evidenceRefsTruncated: state.evidenceRefsTruncated }),
        eventRefs: [...state.eventRefs],
        evidenceRefs: [...state.evidenceRefs],
        blockerRefs: [...state.blockerRefs],
        violationRefs: [...state.violationRefs],
        ...(state.reason === undefined ? {} : { reason: state.reason }),
      }
    })
    const idsFor = (state: ObligationState): string[] => obligations
      .filter(item => item.state === state)
      .map(item => item.obligationId)
    return immutableSnapshot({
      schema: OBLIGATION_LEDGER_STATUS_SCHEMA,
      binding: this.#binding,
      contractHash: this.#contractHash,
      cursor: this.#cursor,
      obligations,
      violations: this.#violations,
      pendingObligationIds: idsFor('PENDING'),
      blockedObligationIds: idsFor('BLOCKED'),
      satisfiedObligationIds: idsFor('SATISFIED'),
      violatedObligationIds: idsFor('VIOLATED'),
    })
  }
  getCompletionDecision(): CompletionDecisionV01 {
    return immutableSnapshot(this.#completionDecision)
  }

  getReadinessReceipt(): SupervisionReadinessReceiptV01 | undefined {
    if (!this.#cursor || !this.#taskEndEvent || this.#completionDecision.status !== 'READY_TO_CLOSE') {
      return undefined
    }
    if (this.#projectionMode === 'COMPACT') {
      return this.#readinessCursorStateHash === this.#cursor.stateHash
        ? this.#readinessReceipt
        : undefined
    }
    return createSupervisionReadinessReceipt({
      binding: this.#binding,
      cursor: this.#cursor,
      status: this.getStatus(),
      decision: this.#completionDecision,
      taskEndEventId: this.#taskEndEvent.eventId,
      taskEndTimestamp: this.#taskEndEvent.timestamp,
    })
  }

  async #refreshReadinessReceipt(): Promise<void> {
    if (!this.#cursor || !this.#taskEndEvent || this.#completionDecision.status !== 'READY_TO_CLOSE') {
      this.#readinessReceipt = undefined
      this.#readinessCursorStateHash = undefined
      return
    }
    if (this.#readinessCursorStateHash === this.#cursor.stateHash && this.#readinessReceipt) return
    const legacy = new ExecutionObligationLedger(
      this.#eventStore,
      undefined,
      'LEGACY_READINESS',
      true,
    )
    await legacy.synchronize()
    const readiness = legacy.getReadinessReceipt()
    if (!readiness) throw new Error('Legacy readiness projection did not reach READY_TO_CLOSE')
    this.#readinessReceipt = readiness
    this.#readinessCursorStateHash = this.#cursor.stateHash
  }

  async attachLifecycleClosure(
    binding: SupervisionLifecycleBindingV01,
  ): Promise<CompletionDecisionV01> {
    if (!this.#lifecycleAuthority) {
      throw new Error('Framework lifecycle authority is required to attach Closure')
    }
    await this.prepareReadiness()
    const existingFinalization = this.#eventStore.finalization
    if (existingFinalization) {
      if (existingFinalization.finalizationHash !== hashCanonicalJson(binding)
          || existingFinalization.finalizationRef !== lifecycleClosureRef(binding)) {
        throw new Error('Execution Event Store is finalized with a different lifecycle binding')
      }
      if (this.#completionDecision.status !== 'COMPLETE') {
        throw new Error('Durable lifecycle binding did not project COMPLETE')
      }
      return this.getCompletionDecision()
    }
    const readiness = this.#validateLifecycleBinding(binding)
    await this.#lifecycleAuthority.verifyLifecycleClosure(binding)
    const finalization = createLifecycleFinalization(binding, readiness.cursor)
    await this.#eventStore.finalize(finalization)
    this.#applyLifecycleBinding(binding, finalization.finalizationRef)
    return this.getCompletionDecision()
  }

  #validateLifecycleBinding(
    binding: SupervisionLifecycleBindingV01,
  ): SupervisionReadinessReceiptV01 {
    assertLifecycleBindingShape(binding)
    const readiness = this.getReadinessReceipt()
    if (!readiness) throw new Error('Latest durable supervision state is not READY_TO_CLOSE')
    const contract = this.#binding.contract
    const policy = contract.completionPolicy
    if (!policy.requireAllMustSatisfied
        || !policy.requireNoViolations
        || !policy.requireReflection
        || !policy.requireKnowledgeDecision
        || !policy.requireContextUpdate
        || !policy.requireClosureReceipt) {
      throw new Error('Governed lifecycle attachment requires the full mandatory completion policy')
    }
    const requiredModuleIds = [...new Set(policy.requiredClosureModuleIds)]
    const frozenModuleIds = [...MANDATORY_LIFECYCLE_CLOSURE_MODULE_IDS]
    if (requiredModuleIds.length === 0
        || requiredModuleIds.length !== policy.requiredClosureModuleIds.length) {
      throw new Error('Governed lifecycle attachment requires unique mandatory Closure module IDs')
    }
    if (requiredModuleIds.length !== frozenModuleIds.length
        || [...requiredModuleIds].sort().some((id, index) => id !== [...frozenModuleIds].sort()[index])) {
      throw new Error('Governed lifecycle completion policy must require all eight frozen Closure modules')
    }
    const actualModuleIds = binding.moduleReceipts.map(item => item.moduleId)
    if (actualModuleIds.length !== requiredModuleIds.length
        || [...actualModuleIds].sort().some((id, index) => id !== [...requiredModuleIds].sort()[index])) {
      throw new Error('Lifecycle binding does not contain exactly the required Closure modules')
    }
    const requiredLifecycleKinds = [
      'REFLECTION',
      'KNOWLEDGE_DECISION',
      'CONTEXT_UPDATE',
      'CLOSURE',
    ] as const
    for (const kind of requiredLifecycleKinds) {
      if (!this.#definitions.some(item => item.kind === kind && item.severity === 'MUST')) {
        throw new Error(`Governed lifecycle contract is missing MUST ${kind} obligation`)
      }
    }
    for (const [label, actual, expected] of [
      ['projectId', binding.projectId, contract.projectId],
      ['taskId', binding.taskId, contract.taskId],
      ['turnId', binding.turnId, this.#binding.turnId],
      ['agentId', binding.agentId, contract.agentId],
      ['contextHash', binding.contextHash, contract.contextHash],
      ['readinessRef', binding.readinessRef, readiness.receiptRef],
      ['readinessHash', binding.readinessHash, readiness.receiptHash],
    ] as const) {
      if (actual !== expected) throw new Error(`${label} does not match the exact readiness binding`)
    }
    if (Date.parse(binding.kernelClosureCreatedAt) < Date.parse(readiness.taskEndTimestamp)) {
      throw new Error('Kernel Closure predates the persisted TASK_END request')
    }
    this.#preflightLifecycleProjection()
    return readiness
  }

  async #applyDurableLifecycleBinding(
    finalization: ExecutionStoreFinalizationV01,
  ): Promise<void> {
    if (!this.#lifecycleAuthority) {
      throw new Error('Framework lifecycle authority is required to replay finalized Closure')
    }
    if (finalization.payload.schema !== SUPERVISION_LIFECYCLE_BINDING_SCHEMA) {
      throw new Error('Durable Event Store finalization is not a lifecycle Closure binding')
    }
    const binding = finalization.payload as unknown as SupervisionLifecycleBindingV01
    if (this.#appliedLifecycleFinalizationHash === finalization.finalizationHash) {
      if (finalization.finalizationRef !== lifecycleClosureRef(binding)
          || finalization.finalizationHash !== hashCanonicalJson(binding)) {
        throw new Error('Durable lifecycle finalization content address is invalid')
      }
      await this.#lifecycleAuthority.verifyLifecycleClosure(binding)
      return
    }
    const readiness = this.#validateLifecycleBinding(binding)
    if (finalization.cursor.sequence !== readiness.cursor.sequence
        || finalization.cursor.stateHash !== readiness.cursor.stateHash) {
      throw new Error('Durable lifecycle finalization cursor does not match readiness')
    }
    if (finalization.finalizationRef !== lifecycleClosureRef(binding)
        || finalization.finalizationHash !== hashCanonicalJson(binding)) {
      throw new Error('Durable lifecycle finalization content address is invalid')
    }
    await this.#lifecycleAuthority.verifyLifecycleClosure(binding)
    this.#applyLifecycleBinding(binding, finalization.finalizationRef)
    this.#appliedLifecycleFinalizationHash = finalization.finalizationHash
  }

  #preflightLifecycleProjection(): void {
    const lifecycleKinds = new Set([
      'REFLECTION',
      'KNOWLEDGE_DECISION',
      'CONTEXT_UPDATE',
      'CLOSURE',
    ])
    const projected = new Map<string, ObligationState>(
      [...this.#states].map(([id, state]) => [id, state.state]),
    )
    for (let pass = 0; pass < this.#definitions.length; pass += 1) {
      let changed = false
      for (const definition of this.#definitions) {
        if (!lifecycleKinds.has(definition.kind)) continue
        const dependenciesSatisfied = (definition.dependencies ?? []).every(id =>
          ['SATISFIED', 'NOT_APPLICABLE', 'WAIVED'].includes(projected.get(id) ?? 'PENDING'))
        const next: ObligationState = dependenciesSatisfied ? 'SATISFIED' : 'BLOCKED'
        if (projected.get(definition.id) !== next) {
          projected.set(definition.id, next)
          changed = true
        }
      }
      if (!changed) break
    }
    const unresolved = this.#definitions.filter(definition =>
      lifecycleKinds.has(definition.kind)
      && definition.severity === 'MUST'
      && projected.get(definition.id) !== 'SATISFIED')
    if (unresolved.length > 0) {
      throw new Error(`Lifecycle obligations cannot close with unresolved dependencies: ${unresolved.map(item => item.id).join(', ')}`)
    }
  }

  #applyLifecycleBinding(
    binding: SupervisionLifecycleBindingV01,
    closureRef: string,
  ): void {
    const lifecycleKinds = new Set([
      'REFLECTION',
      'KNOWLEDGE_DECISION',
      'CONTEXT_UPDATE',
      'CLOSURE',
    ])
    for (const definition of this.#definitions) {
      if (!lifecycleKinds.has(definition.kind)) continue
      const state = this.#states.get(definition.id)!
      this.#intrinsicallySatisfiedIds.add(definition.id)
      state.updatedAt = binding.kernelClosureCreatedAt
      state.reason = 'Satisfied by exact Framework Reflection and Kernel Closure binding'
      uniqueAppend(state.evidenceRefs, binding.reflection.reflectionRef)
      uniqueAppend(state.evidenceRefs, binding.kernelClosureRef)
      uniqueAppend(state.evidenceRefs, closureRef)
    }
    for (let pass = 0; pass < this.#definitions.length; pass += 1) {
      let changed = false
      for (const definition of this.#definitions) {
        if (!lifecycleKinds.has(definition.kind)) continue
        const state = this.#states.get(definition.id)!
        const blockers = (definition.dependencies ?? []).filter(id => {
          const dependency = this.#states.get(id)?.state
          return !dependency || !['SATISFIED', 'NOT_APPLICABLE', 'WAIVED'].includes(dependency)
        })
        state.blockerRefs = blockers
        const next = blockers.length === 0 ? 'SATISFIED' : 'BLOCKED'
        if (state.state !== next) {
          state.state = next
          changed = true
        }
      }
      if (!changed) break
    }
    const unresolved = this.#definitions.filter(definition =>
      lifecycleKinds.has(definition.kind)
      && definition.severity === 'MUST'
      && this.#states.get(definition.id)!.state !== 'SATISFIED')
    if (unresolved.length > 0) {
      throw new Error(`Lifecycle obligations remain unresolved: ${unresolved.map(item => item.id).join(', ')}`)
    }
    this.#completionDecision = immutableSnapshot({
      status: 'COMPLETE',
      pendingObligationIds: [],
      violatedObligationIds: [],
      blockerRefs: [],
      evidenceRefs: [
        ...this.#completionDecision.evidenceRefs,
        binding.reflection.reflectionRef,
        binding.kernelClosureRef,
      ].filter((value, index, values) => values.indexOf(value) === index),
      closureRef,
    })
    this.#appliedLifecycleFinalizationHash = hashCanonicalJson(binding)
  }

  #applyEvent(event: ExecutionEventEnvelopeV01): void {
    if (startsDurableExternalSpan(event) && this.#openExternalSpan === undefined) {
      this.#openExternalSpan = [event]
      this.#openExternalSpanBytes = Buffer.byteLength(canonicalJson(event), 'utf8')
      if (this.#taskEndEvent !== undefined) {
        this.#completionDecision = this.#evaluateCompletionDecision()
      }
      return
    }
    if (this.#openExternalSpan !== undefined) {
      this.#openExternalSpan.push(event)
      this.#openExternalSpanBytes += Buffer.byteLength(canonicalJson(event), 'utf8')
      if (this.#openExternalSpan.length > MAX_EXTERNAL_AGENT_BUNDLE_EVENTS
          || this.#openExternalSpanBytes > MAX_EXTERNAL_AGENT_BUNDLE_BYTES) {
        throw new Error('Persisted external Agent span exceeds the frozen Bridge budget')
      }
      if (event.kind !== 'ASSISTANT_MESSAGE') {
        if (this.#taskEndEvent !== undefined) {
          this.#completionDecision = this.#evaluateCompletionDecision()
        }
        return
      }
      const span = this.#openExternalSpan
      this.#openExternalSpan = undefined
      this.#openExternalSpanBytes = 0
      const admission = durableExternalSpanAdmission(span, this.#binding)
      if (admission) {
        for (const admitted of admission.events) {
          if (['RESOURCE_READ', 'SOURCE_DISPOSITION'].includes(admitted.kind)) {
            const receipt = resourceReceipt(admitted)
            if (receipt) this.#applyResourceRead(admitted, receipt)
          } else if (admitted.kind === 'RESOURCE_WRITE') {
            const receipt = mutationReceipt(admitted)
            if (receipt) this.#applyResourceWrite(admitted, receipt)
          } else if (admitted.kind === 'VALIDATION_RESULT') {
            const receipt = validationReceipt(admitted)
            if (receipt) this.#applyValidationResult(admitted, receipt)
          } else if (admitted.kind === 'OUTPUT_EMITTED') {
            const receipt = outputReceipt(admitted)
            if (receipt) this.#applyOutput(admitted, receipt)
          }
        }
        this.#applyClaims(event, admission.claims)
      }
    } else if (event.kind === 'RESOURCE_READ') {
      const receipt = resourceReceipt(event)
      if (receipt) this.#applyResourceRead(event, receipt)
    } else if (event.kind === 'RESOURCE_WRITE') {
      const receipt = mutationReceipt(event)
      if (receipt) this.#applyResourceWrite(event, receipt)
    } else if (event.kind === 'TASK_END_REQUEST') {
      this.#applyTaskEndRequest(event)
    }
    if (this.#taskEndEvent !== undefined
        && event.kind !== 'TASK_END_REQUEST'
        && event.sequence > this.#taskEndEvent.sequence) {
      this.#completionDecision = this.#evaluateCompletionDecision()
    }
  }

  #applyResourceRead(
    event: ExecutionEventEnvelopeV01,
    receipt: ResourceReceiptV01,
  ): void {
    for (const definition of this.#resourceDefinitionsById.get(receipt.resourceId) ?? []) {
      const state = this.#states.get(definition.id)!
      const matches = definition.kind === 'REQUIRED_RESOURCE'
        ? readMatches(definition, receipt)
        : sourceDispositionMatches(definition, receipt)
      if (state.state === 'VIOLATED' || !matches) continue
      this.#intrinsicallySatisfiedIds.add(definition.id)
      state.state = state.blockerRefs.length === 0 ? 'SATISFIED' : 'BLOCKED'
      state.updatedAt = event.timestamp
      if (this.#projectionMode === 'LEGACY_READINESS') {
        uniqueAppend(state.eventRefs, event.eventId)
        for (const reference of receipt.claimRefs) uniqueAppend(state.evidenceRefs, reference)
      } else {
        state.accessCount = (state.accessCount ?? 0) + 1
        replaceWithLatest(state.eventRefs, event.eventId)
        for (const reference of receipt.claimRefs) {
          if (boundedUniqueAppend(state.evidenceRefs, reference, MAX_LEDGER_STATE_EVIDENCE_REFS)) {
            state.evidenceRefsTruncated = true
          }
        }
      }
      state.reason = definition.kind === 'REQUIRED_RESOURCE'
        ? 'Matching accepted resource receipt'
        : 'Matching accepted source disposition receipt'
      this.#updateDependencyDescendants(definition.id, event)
    }
  }

  #applyResourceWrite(
    event: ExecutionEventEnvelopeV01,
    receipt: MutationReceiptV01,
  ): void {
    for (const definition of this.#writeScopeDefinitions) {
      if (writeAllowed(definition, receipt)) continue
      const violation = violationFor(definition, event, receipt)
      if (this.#violationIds.has(violation.id)) continue
      this.#violationIds.add(violation.id)
      this.#violations.push(violation)
      const state = this.#states.get(definition.id)!
      state.state = 'VIOLATED'
      this.#intrinsicallySatisfiedIds.delete(definition.id)
      state.updatedAt = event.timestamp
      uniqueAppend(state.eventRefs, event.eventId)
      uniqueAppend(state.violationRefs, violation.id)
      state.reason = 'Observed write is outside the contributed scope'
      this.#updateDependencyDescendants(definition.id, event)
    }
  }

  #applyValidationResult(
    event: ExecutionEventEnvelopeV01,
    receipt: ValidationReceiptV01,
  ): void {
    const candidate = { event, receipt }
    this.#validationCandidates.push(candidate)
    const key = validationIdentityKey(receipt.validationId, receipt.targetIdentity)
    const candidates = this.#validationCandidatesByKey.get(key) ?? []
    candidates.push(candidate)
    this.#validationCandidatesByKey.set(key, candidates)
    for (const definition of this.#validationDefinitionsByKey.get(key) ?? []) {
      this.#recomputeEvidenceDefinition(definition, event.timestamp, event)
    }
  }

  #applyOutput(
    event: ExecutionEventEnvelopeV01,
    receipt: OutputReceiptV01,
  ): void {
    const candidate = { event, receipt }
    this.#outputCandidates.push(candidate)
    const key = outputIdentityKey(receipt.outputContractId)
    const candidates = this.#outputCandidatesByKey.get(key) ?? []
    candidates.push(candidate)
    this.#outputCandidatesByKey.set(key, candidates)
    for (const definition of this.#outputDefinitionsByKey.get(key) ?? []) {
      this.#recomputeEvidenceDefinition(definition, event.timestamp, event)
    }
  }

  #recomputeEvidenceDefinition(
    definition: ObligationDefinitionV01,
    evaluationAt: string,
    cause: ExecutionEventEnvelopeV01,
  ): void {
    const policy = this.#evidencePolicyByObligationId.get(definition.id)
    if (!policy) return
    const candidates: Array<{
      readonly event: ExecutionEventEnvelopeV01
      readonly providerId: string
      readonly providerKind: ValidationReceiptV01['providerKind']
      readonly resultStatus: ValidationReceiptV01['resultStatus']
      readonly contextHash: string
      readonly projectRevision?: string
      readonly targetIdentity: string
      readonly timestamp: string
      readonly evidenceRefs: readonly string[]
    }> = []

    if (definition.kind === 'VALIDATION' || definition.kind === 'RULE_COMPLIANCE') {
      const target = recordOf(definition.target) as ValidationTargetV01 | undefined
      const satisfaction = recordOf(definition.satisfaction) as
        | ValidationSatisfactionV01
        | undefined
      if (!target || satisfaction?.requiredResultStatus !== 'PASS') return
      const key = validationIdentityKey(target.validationId, target.targetIdentity)
      for (const candidate of this.#validationCandidatesByKey.get(key) ?? []) {
        if (candidate.receipt.validationId !== target.validationId
            || candidate.receipt.targetIdentity !== target.targetIdentity) continue
        candidates.push({
          event: candidate.event,
          providerId: candidate.receipt.providerId,
          providerKind: candidate.receipt.providerKind,
          resultStatus: candidate.receipt.resultStatus,
          contextHash: candidate.receipt.contextHash,
          ...(candidate.receipt.projectRevision === undefined
            ? {}
            : { projectRevision: candidate.receipt.projectRevision }),
          targetIdentity: candidate.receipt.targetIdentity,
          timestamp: candidate.receipt.timestamp,
          evidenceRefs: candidate.receipt.evidenceRefs,
        })
      }
    } else if (definition.kind === 'OUTPUT') {
      const target = recordOf(definition.target) as OutputTargetV01 | undefined
      const satisfaction = recordOf(definition.satisfaction) as
        | OutputSatisfactionV01
        | undefined
      if (!target
          || satisfaction?.requiredStructuralStatus !== 'PASS'
          || satisfaction.requiredResultStatus !== 'PASS') return
      for (const candidate of this.#outputCandidatesByKey.get(
        outputIdentityKey(target.outputContractId),
      ) ?? []) {
        const receipt = candidate.receipt
        if (receipt.outputContractId !== target.outputContractId
            || (target.resourceId !== undefined && receipt.resourceId !== target.resourceId)
            || (target.contentHash !== undefined && receipt.contentHash !== target.contentHash)) {
          continue
        }
        candidates.push({
          event: candidate.event,
          providerId: receipt.providerId,
          providerKind: receipt.providerKind,
          resultStatus: receipt.structuralValidationStatus,
          contextHash: receipt.contextHash,
          ...(receipt.projectRevision === undefined
            ? {}
            : { projectRevision: receipt.projectRevision }),
          targetIdentity: receipt.targetIdentity,
          timestamp: receipt.timestamp,
          evidenceRefs: receipt.evidenceRefs,
        })
      }
    } else {
      return
    }

    const evaluated = candidates
      .map(candidate => ({
        candidate,
        evaluation: evaluateTrustedEvidence({
          policy,
          contract: this.#binding.contract,
          providerId: candidate.providerId,
          providerKind: candidate.providerKind,
          resultStatus: candidate.resultStatus,
          contextHash: candidate.contextHash,
          ...(candidate.projectRevision === undefined
            ? {}
            : { projectRevision: candidate.projectRevision }),
          targetIdentity: candidate.targetIdentity,
          timestamp: candidate.timestamp,
          evaluationAt,
          requiredResultStatus: 'PASS',
          expectedTargetIdentity: (recordOf(definition.target)?.targetIdentity
            ?? recordOf(definition.target)?.outputContractId) as string,
        }),
      }))
      .filter(item => item.evaluation.satisfying || item.evaluation.trustedFailure)
      .sort((left, right) => right.candidate.event.sequence - left.candidate.event.sequence)

    const current = evaluated[0]
    const state = this.#states.get(definition.id)!
    const dependencyBlockers = (definition.dependencies ?? []).filter(dependency => {
      const dependencyState = this.#states.get(dependency)!.state
      return !['SATISFIED', 'NOT_APPLICABLE', 'WAIVED'].includes(dependencyState)
    })
    state.blockerRefs = dependencyBlockers
    this.#trustedFailureObligationIds.delete(definition.id)
    if (!current) {
      state.state = dependencyBlockers.length === 0 ? 'PENDING' : 'BLOCKED'
      this.#intrinsicallySatisfiedIds.delete(definition.id)
      state.updatedAt = cause.timestamp
      state.reason = 'No current trusted Evidence satisfies the obligation'
      this.#updateDependencyDescendants(definition.id, cause)
      return
    }

    state.updatedAt = cause.timestamp
    uniqueAppend(state.eventRefs, current.candidate.event.eventId)
    for (const reference of current.candidate.evidenceRefs) {
      uniqueAppend(state.evidenceRefs, reference)
    }
    if (current.evaluation.trustedFailure) {
      state.state = 'VIOLATED'
      this.#intrinsicallySatisfiedIds.delete(definition.id)
      state.reason = 'Current trusted Evidence reports FAIL'
      this.#trustedFailureObligationIds.add(definition.id)
      const violation = this.#evidenceViolation(
        'TRUSTED_VALIDATION_FAILED',
        definition,
        current.candidate.event,
        {
          providerId: current.candidate.providerId,
          targetIdentity: current.candidate.targetIdentity,
          evidenceRef: current.candidate.evidenceRefs[0]
            ?? current.candidate.event.eventId,
        },
      )
      this.#recordViolation(violation)
    } else {
      this.#intrinsicallySatisfiedIds.add(definition.id)
      state.state = dependencyBlockers.length === 0 ? 'SATISFIED' : 'BLOCKED'
      state.reason = dependencyBlockers.length === 0
        ? 'Matching current trusted Evidence satisfies the obligation'
        : 'Matching current trusted Evidence is masked by unresolved dependencies'
    }
    this.#updateDependencyDescendants(definition.id, cause)
  }

  #applyClaims(
    event: ExecutionEventEnvelopeV01,
    claims: readonly AgentClaimV01[],
  ): void {
    for (const claim of claims) {
      this.#claimCandidates.push({ event, claim })
      if (claim.resultStatus !== 'PASS') continue
      for (const definition of this.#definitions) {
        if (definition.kind !== 'CLAIM_EVIDENCE'
            || !this.#claimInScope(definition, claim)) continue
        const state = this.#states.get(definition.id)!
        if (this.#claimHasPriorEvidence(definition, claim, event)) {
          uniqueAppend(state.eventRefs, event.eventId)
          for (const reference of claim.evidenceRefs) {
            uniqueAppend(state.evidenceRefs, reference)
          }
          continue
        }
        const violation = this.#evidenceViolation(
          'UNSUPPORTED_PASS_CLAIM',
          definition,
          event,
          {
            claimId: claim.id,
            targetIdentity: claim.targetIdentity,
          },
        )
        this.#recordViolation(violation)
        state.state = 'VIOLATED'
        this.#intrinsicallySatisfiedIds.delete(definition.id)
        state.updatedAt = event.timestamp
        uniqueAppend(state.eventRefs, event.eventId)
        uniqueAppend(state.violationRefs, violation.id)
        state.reason = 'Structured PASS claim has no matching prior trusted Evidence'
        this.#updateDependencyDescendants(definition.id, event)
      }
    }
  }

  #claimInScope(
    definition: ObligationDefinitionV01,
    claim: AgentClaimV01,
  ): boolean {
    const target = recordOf(definition.target) as ClaimEvidenceTargetV01 | undefined
    const satisfaction = recordOf(definition.satisfaction) as
      | ClaimEvidenceSatisfactionV01
      | undefined
    if (!target || satisfaction?.requireEvidenceForPassClaims !== true) return false
    if (!target.claimKinds.includes(claim.kind)) return false
    return target.targetIdentities === undefined
      || target.targetIdentities.includes(claim.targetIdentity)
  }

  #claimHasPriorEvidence(
    definition: ObligationDefinitionV01,
    claim: AgentClaimV01,
    claimEvent: ExecutionEventEnvelopeV01,
    evaluationAt = claimEvent.timestamp,
  ): boolean {
    const policy = this.#evidencePolicyByObligationId.get(definition.id)
    if (!policy) return false
    const validationCandidates = claim.kind === 'OUTPUT'
      ? []
      : this.#validationCandidatesByKey.get(validationIdentityKey(
        claim.validationId!,
        claim.targetIdentity,
      )) ?? []
    const validationMatches = claim.kind !== 'OUTPUT'
      && validationCandidates.some(candidate => {
      if (candidate.event.sequence >= claimEvent.sequence
          || !claim.evidenceRefs.includes(candidate.event.eventId)
          || !candidate.receipt.claimRefs.includes(claim.id)
          || candidate.receipt.targetIdentity !== claim.targetIdentity
          || candidate.receipt.validationId !== claim.validationId) return false
      return evaluateTrustedEvidence({
        policy,
        contract: this.#binding.contract,
        providerId: candidate.receipt.providerId,
        providerKind: candidate.receipt.providerKind,
        resultStatus: candidate.receipt.resultStatus,
        contextHash: candidate.receipt.contextHash,
        ...(candidate.receipt.projectRevision === undefined
          ? {}
          : { projectRevision: candidate.receipt.projectRevision }),
        targetIdentity: candidate.receipt.targetIdentity,
        timestamp: candidate.receipt.timestamp,
        evaluationAt,
        requiredResultStatus: 'PASS',
        expectedTargetIdentity: claim.targetIdentity,
      }).satisfying
    })
    if (validationMatches) return true
    if (claim.kind !== 'OUTPUT' || typeof claim.outputContractId !== 'string') {
      return false
    }
    return (this.#outputCandidatesByKey.get(
      outputIdentityKey(claim.outputContractId),
    ) ?? []).some(candidate => {
      const receipt = candidate.receipt
      if (candidate.event.sequence >= claimEvent.sequence
          || !claim.evidenceRefs.includes(candidate.event.eventId)
          || !receipt.claimRefs.includes(claim.id)
          || receipt.targetIdentity !== claim.targetIdentity
          || receipt.outputContractId !== claim.outputContractId) return false
      return evaluateTrustedEvidence({
        policy,
        contract: this.#binding.contract,
        providerId: receipt.providerId,
        providerKind: receipt.providerKind,
        resultStatus: receipt.structuralValidationStatus,
        contextHash: receipt.contextHash,
        ...(receipt.projectRevision === undefined
          ? {}
          : { projectRevision: receipt.projectRevision }),
        targetIdentity: receipt.targetIdentity,
        timestamp: receipt.timestamp,
        evaluationAt,
        requiredResultStatus: 'PASS',
        expectedTargetIdentity: claim.targetIdentity,
      }).satisfying
    })
  }

  #applyTaskEndRequest(event: ExecutionEventEnvelopeV01): void {
    this.#taskEndEvent = event
    for (const definition of this.#definitions) {
      if (['OUTPUT', 'VALIDATION', 'RULE_COMPLIANCE'].includes(definition.kind)) {
        this.#recomputeEvidenceDefinition(definition, event.timestamp, event)
      }
    }
    this.#recomputeDependencyStates(event)
    for (const definition of this.#definitions) {
      const state = this.#states.get(definition.id)!
      if (state.state === 'VIOLATED') continue
      if (definition.kind === 'WRITE_SCOPE') {
        this.#intrinsicallySatisfiedIds.add(definition.id)
        state.state = state.blockerRefs.length === 0 ? 'SATISFIED' : 'BLOCKED'
        state.updatedAt = event.timestamp
        uniqueAppend(state.eventRefs, event.eventId)
        state.reason = state.blockerRefs.length === 0
          ? 'All accepted mutations observed before task end were in scope'
          : 'In-scope mutation history is masked by unresolved dependencies'
      } else if (definition.kind === 'CLAIM_EVIDENCE') {
        const passClaims = this.#claimCandidates.filter(candidate =>
          candidate.claim.resultStatus === 'PASS'
          && this.#claimInScope(definition, candidate.claim))
        const allCurrent = passClaims.every(candidate => this.#claimHasPriorEvidence(
          definition,
          candidate.claim,
          candidate.event,
          event.timestamp,
        ))
        if (allCurrent) this.#intrinsicallySatisfiedIds.add(definition.id)
        else this.#intrinsicallySatisfiedIds.delete(definition.id)
        state.state = state.blockerRefs.length > 0
          ? 'BLOCKED'
          : allCurrent ? 'SATISFIED' : 'PENDING'
        state.updatedAt = event.timestamp
        uniqueAppend(state.eventRefs, event.eventId)
        state.reason = state.blockerRefs.length > 0
          ? 'Claim Evidence status is masked by unresolved dependencies'
          : allCurrent
          ? 'Every structured PASS claim in scope has prior trusted Evidence'
          : 'A structured PASS claim no longer has current trusted Evidence'
      }
    }
    this.#recomputeDependencyStates(event)
    this.#completionDecision = this.#evaluateCompletionDecision()
  }

  #evaluateCompletionDecision(): CompletionDecisionV01 {
    if (!this.#taskEndEvent) return this.#completionDecision
    const executionKinds = new Set([
      'REQUIRED_RESOURCE',
      'SOURCE_DISPOSITION',
      'OUTPUT',
      'WRITE_SCOPE',
      'VALIDATION',
      'CLAIM_EVIDENCE',
      'RULE_COMPLIANCE',
    ])
    const policy = this.#binding.contract.completionPolicy
    const required = this.#definitions.filter(definition =>
      executionKinds.has(definition.kind)
      && (definition.severity === 'MUST' || !policy.allowShouldWarnings))
    const pending = required.filter(definition =>
      ['PENDING', 'BLOCKED'].includes(this.#states.get(definition.id)!.state))
      .map(definition => definition.id)
    const violated = required.filter(definition =>
      this.#states.get(definition.id)!.state === 'VIOLATED')
      .map(definition => definition.id)
    const deferred = this.#definitions.filter(definition =>
      !executionKinds.has(definition.kind)
      && (definition.severity === 'MUST' || !policy.allowShouldWarnings))
      .map(definition => `deferred-obligation://${definition.id}`)
    const blockerRefs = [
      ...deferred,
      ...required.flatMap(definition => this.#states.get(definition.id)!.blockerRefs),
    ].filter((value, index, values) => values.indexOf(value) === index)
    const evidenceRefs = required
      .flatMap(definition => this.#states.get(definition.id)!.evidenceRefs)
      .filter((value, index, values) => values.indexOf(value) === index)
    const trustedFailure = violated.some(id =>
      this.#trustedFailureObligationIds.has(id))
    const status = trustedFailure
      ? 'FAILED'
      : pending.length > 0 || violated.length > 0 || this.#openExternalSpan !== undefined
        ? 'BLOCKED'
        : 'READY_TO_CLOSE'
    return immutableSnapshot({
      status,
      pendingObligationIds: pending,
      violatedObligationIds: violated,
      blockerRefs: this.#openExternalSpan === undefined
        ? blockerRefs
        : [...blockerRefs, 'external-agent-span://incomplete'],
      evidenceRefs,
    })
  }

  #evidenceViolation(
    code: 'UNSUPPORTED_PASS_CLAIM' | 'TRUSTED_VALIDATION_FAILED',
    definition: ObligationDefinitionV01,
    event: ExecutionEventEnvelopeV01,
    details: {
      readonly claimId?: string
      readonly targetIdentity?: string
      readonly providerId?: string
      readonly evidenceRef?: string
    },
  ): ObligationViolationRecordV01 {
    return {
      id: `violation-${hashCanonicalJson({
        code,
        eventId: event.eventId,
        obligationId: definition.id,
      })}`,
      code,
      obligationId: definition.id,
      severity: definition.severity,
      eventId: event.eventId,
      sequence: event.sequence,
      observedAt: event.timestamp,
      ...details,
    }
  }

  #recordViolation(violation: ObligationViolationRecordV01): void {
    if (this.#violationIds.has(violation.id)) return
    this.#violationIds.add(violation.id)
    this.#violations.push(violation)
  }

  #recomputeDependencyStates(event: ExecutionEventEnvelopeV01): void {
    for (let pass = 0; pass < this.#definitions.length; pass += 1) {
      let changed = false
      for (const definition of this.#definitions) {
        const state = this.#states.get(definition.id)!
        if (state.state === 'VIOLATED') continue
        const blockers = (definition.dependencies ?? []).filter(dependency => {
          const dependencyState = this.#states.get(dependency)!.state
          return !['SATISFIED', 'NOT_APPLICABLE', 'WAIVED'].includes(dependencyState)
        })
        if (blockers.length > 0 && state.state !== 'BLOCKED') {
          state.state = 'BLOCKED'
          state.updatedAt = event.timestamp
          state.reason = 'One or more declared dependencies are unresolved'
          changed = true
        } else if (blockers.length === 0 && state.state === 'BLOCKED') {
          state.state = this.#intrinsicallySatisfiedIds.has(definition.id)
            ? 'SATISFIED'
            : 'PENDING'
          state.updatedAt = event.timestamp
          state.reason = 'All declared dependencies are satisfied'
          changed = true
        }
        state.blockerRefs = blockers
      }
      if (!changed) return
    }
  }

  #updateDependencyDescendants(
    changedId: string,
    event: ExecutionEventEnvelopeV01,
  ): void {
    const queue = [...(this.#dependentsById.get(changedId) ?? [])]
    const visited = new Set<string>()
    while (queue.length > 0) {
      const obligationId = queue.shift()!
      if (visited.has(obligationId)) continue
      visited.add(obligationId)
      const definition = this.#definitionsById.get(obligationId)!
      const state = this.#states.get(obligationId)!
      const blockers = (definition.dependencies ?? []).filter(dependency => {
        const dependencyState = this.#states.get(dependency)!.state
        return !['SATISFIED', 'NOT_APPLICABLE', 'WAIVED'].includes(dependencyState)
      })
      if (this.#projectionMode === 'LEGACY_READINESS') {
        state.blockerRefs = blockers
        state.updatedAt = event.timestamp
        uniqueAppend(state.eventRefs, event.eventId)
        if (state.state !== 'VIOLATED' && blockers.length > 0) {
          state.state = 'BLOCKED'
          state.reason = 'One or more declared dependencies are unresolved'
        } else if (state.state === 'BLOCKED') {
          state.state = this.#intrinsicallySatisfiedIds.has(definition.id)
            ? 'SATISFIED'
            : 'PENDING'
          state.reason = 'All declared dependencies are satisfied'
        }
        queue.push(...(this.#dependentsById.get(obligationId) ?? []))
        continue
      }
      let nextState = state.state
      let nextReason = state.reason
      if (state.state !== 'VIOLATED' && blockers.length > 0) {
        nextState = 'BLOCKED'
        nextReason = 'One or more declared dependencies are unresolved'
      } else if (state.state === 'BLOCKED') {
        nextState = this.#intrinsicallySatisfiedIds.has(definition.id)
          ? 'SATISFIED'
          : 'PENDING'
        nextReason = 'All declared dependencies are satisfied'
      }
      const changed = nextState !== state.state
        || nextReason !== state.reason
        || canonicalJson(blockers) !== canonicalJson(state.blockerRefs)
      if (changed) {
        state.state = nextState
        if (nextReason === undefined) delete state.reason
        else state.reason = nextReason
        state.blockerRefs = blockers
        state.updatedAt = event.timestamp
        replaceWithLatest(state.eventRefs, event.eventId)
        queue.push(...(this.#dependentsById.get(obligationId) ?? []))
      }
    }
  }
}

export const createExecutionObligationLedger = async (
  input: CreateExecutionObligationLedgerInputV01,
): Promise<ExecutionObligationLedgerV01> => {
  const contribution = validateObligationLedgerContribution(
    input.eventStore.binding.contract,
  )
  if (!contribution.valid) {
    throw new TypeError(contribution.issues
      .map(item => `${item.path} ${item.code}: ${item.message}`)
      .join('\n'))
  }
  const ledger = new ExecutionObligationLedger(
    input.eventStore,
    input.lifecycleAuthority,
  )
  await ledger.synchronize()
  if (!input.eventStore.finalization
      && ledger.getCompletionDecision().status === 'READY_TO_CLOSE') {
    await ledger.prepareReadiness()
  }
  return ledger
}
