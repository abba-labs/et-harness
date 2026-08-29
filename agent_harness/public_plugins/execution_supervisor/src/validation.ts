import {
  COMPLETION_STATUSES,
  EVIDENCE_PROVIDER_KINDS,
  EVIDENCE_RESULT_STATUSES,
  EXECUTION_EVENT_KINDS,
  EXECUTION_EVENT_SCHEMA,
  HOST_CAPABILITY_CONTRACT_SCHEMA,
  MAX_EVIDENCE_POLICY_COUNT,
  MAX_EXECUTION_EVENT_PAYLOAD_BYTES,
  MAX_IDENTIFIER_CHARS,
  MAX_OBLIGATION_COUNT,
  MAX_REFERENCE_CHARS,
  MAX_TASK_SUPERVISION_CONTRACT_BYTES,
  OBLIGATION_KINDS,
  OBLIGATION_SEVERITIES,
  PERFORMANCE_BASELINE_REPORT_SCHEMA,
  SUPERVISION_LEVELS,
  TASK_SUPERVISION_CONTRACT_SCHEMA,
  type CompletionDecisionV01,
  type CompletionPolicyV01,
  type ContractValidationIssue,
  type ContractValidationResult,
  type ExecutionEventEnvelopeV01,
  type ExecutionEventStoreBindingV01,
  type ExecutionEventStoreLimitsV01,
  type ExecutionReplayCursorV01,
  type HostCapabilityContractV01,
  type HostCapabilityFlagsV01,
  type ObligationDefinitionV01,
  type PerformanceBaselineReportV01,
  type PerformanceBaselineSampleV01,
  type SupervisionLevel,
  type SupervisionNegotiationV01,
  type TaskSupervisionContractV01,
} from './contracts.js'
import { canonicalJsonBytes, hashCanonicalJson } from './hash.js'

const IDENTIFIER_RE = /^[A-Za-z0-9][A-Za-z0-9._:/-]*$/
const SHA256_RE = /^[0-9a-f]{64}$/
const HIDDEN_REASONING_KEY_RE = /^(?:chain[_-]?of[_-]?thought|private[_-]?reasoning|hidden[_-]?reasoning|scratchpad)$/i

const recordOf = (value: unknown): Record<string, unknown> | undefined =>
  typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : undefined

const issue = (
  issues: ContractValidationIssue[],
  path: string,
  code: string,
  message: string,
): void => {
  issues.push({ path, code, message })
}

const exactKeys = (
  record: Record<string, unknown>,
  allowed: readonly string[],
  path: string,
  issues: ContractValidationIssue[],
): void => {
  const allowedSet = new Set(allowed)
  for (const key of Object.keys(record)) {
    if (!allowedSet.has(key)) {
      issue(issues, `${path}.${key}`, 'UNKNOWN_FIELD', `Unsupported field ${key}`)
    }
  }
}

const requireString = (
  record: Record<string, unknown>,
  key: string,
  path: string,
  issues: ContractValidationIssue[],
  options: { identifier?: boolean; hash?: boolean; max?: number } = {},
): string | undefined => {
  const value = record[key]
  if (typeof value !== 'string' || !value.trim()) {
    issue(issues, `${path}.${key}`, 'REQUIRED_STRING', `${key} must be a non-empty string`)
    return undefined
  }
  if (value.length > (options.max ?? MAX_REFERENCE_CHARS)) {
    issue(issues, `${path}.${key}`, 'STRING_TOO_LONG', `${key} exceeds its character budget`)
  }
  if (options.identifier && (value.length > MAX_IDENTIFIER_CHARS || !IDENTIFIER_RE.test(value))) {
    issue(issues, `${path}.${key}`, 'INVALID_IDENTIFIER', `${key} is not a valid stable identifier`)
  }
  if (options.hash && !SHA256_RE.test(value)) {
    issue(issues, `${path}.${key}`, 'INVALID_SHA256', `${key} must be a lowercase SHA-256 hex digest`)
  }
  return value
}

const optionalString = (
  record: Record<string, unknown>,
  key: string,
  path: string,
  issues: ContractValidationIssue[],
  options: { identifier?: boolean; hash?: boolean; max?: number } = {},
): string | undefined => {
  if (!(key in record)) return undefined
  return requireString(record, key, path, issues, options)
}

const requireBoolean = (
  record: Record<string, unknown>,
  key: string,
  path: string,
  issues: ContractValidationIssue[],
): boolean | undefined => {
  const value = record[key]
  if (typeof value !== 'boolean') {
    issue(issues, `${path}.${key}`, 'REQUIRED_BOOLEAN', `${key} must be boolean`)
    return undefined
  }
  return value
}

const requireInteger = (
  record: Record<string, unknown>,
  key: string,
  path: string,
  issues: ContractValidationIssue[],
  minimum: number,
): number | undefined => {
  const value = record[key]
  if (!Number.isSafeInteger(value) || (value as number) < minimum) {
    issue(issues, `${path}.${key}`, 'INVALID_INTEGER', `${key} must be a safe integer >= ${minimum}`)
    return undefined
  }
  return value as number
}

const requireFiniteNumber = (
  record: Record<string, unknown>,
  key: string,
  path: string,
  issues: ContractValidationIssue[],
  minimum = 0,
): number | undefined => {
  const value = record[key]
  if (typeof value !== 'number' || !Number.isFinite(value) || value < minimum) {
    issue(issues, `${path}.${key}`, 'INVALID_NUMBER', `${key} must be a finite number >= ${minimum}`)
    return undefined
  }
  return value
}

const requireTimestamp = (
  record: Record<string, unknown>,
  key: string,
  path: string,
  issues: ContractValidationIssue[],
): string | undefined => {
  const value = requireString(record, key, path, issues, { max: 128 })
  if (value && Number.isNaN(Date.parse(value))) {
    issue(issues, `${path}.${key}`, 'INVALID_TIMESTAMP', `${key} must be an ISO-compatible timestamp`)
  }
  return value
}

const requireEnum = <T extends string>(
  record: Record<string, unknown>,
  key: string,
  values: readonly T[],
  path: string,
  issues: ContractValidationIssue[],
): T | undefined => {
  const value = record[key]
  if (typeof value !== 'string' || !values.includes(value as T)) {
    issue(issues, `${path}.${key}`, 'INVALID_ENUM', `${key} must be one of ${values.join(', ')}`)
    return undefined
  }
  return value as T
}

const stringArray = (
  value: unknown,
  path: string,
  issues: ContractValidationIssue[],
  options: { allowEmpty?: boolean; identifier?: boolean; maxItems?: number } = {},
): string[] | undefined => {
  if (!Array.isArray(value)) {
    issue(issues, path, 'REQUIRED_ARRAY', `${path} must be an array`)
    return undefined
  }
  if (!options.allowEmpty && value.length === 0) {
    issue(issues, path, 'EMPTY_ARRAY', `${path} must not be empty`)
  }
  if (value.length > (options.maxItems ?? MAX_OBLIGATION_COUNT)) {
    issue(issues, path, 'ARRAY_TOO_LARGE', `${path} exceeds its item budget`)
  }
  const result: string[] = []
  const seen = new Set<string>()
  value.forEach((item, index) => {
    const itemPath = `${path}[${index}]`
    if (typeof item !== 'string' || !item.trim()) {
      issue(issues, itemPath, 'INVALID_ARRAY_ITEM', 'Array item must be a non-empty string')
      return
    }
    if (item.length > MAX_REFERENCE_CHARS) {
      issue(issues, itemPath, 'STRING_TOO_LONG', 'Array item exceeds its character budget')
    }
    if (options.identifier && (item.length > MAX_IDENTIFIER_CHARS || !IDENTIFIER_RE.test(item))) {
      issue(issues, itemPath, 'INVALID_IDENTIFIER', 'Array item is not a valid stable identifier')
    }
    if (seen.has(item)) {
      issue(issues, itemPath, 'DUPLICATE_ITEM', `Duplicate array item ${item}`)
    } else {
      seen.add(item)
    }
    result.push(item)
  })
  return result
}

const validateJsonValue = (
  value: unknown,
  path: string,
  issues: ContractValidationIssue[],
  active: Set<object>,
  depth: number,
): void => {
  if (depth > 32) {
    issue(issues, path, 'JSON_DEPTH_EXCEEDED', 'JSON value exceeds maximum nesting depth')
    return
  }
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) issue(issues, path, 'NON_FINITE_NUMBER', 'JSON number must be finite')
    return
  }
  if (typeof value !== 'object') {
    issue(issues, path, 'NON_JSON_VALUE', 'Value is not JSON-compatible')
    return
  }
  if (active.has(value)) {
    issue(issues, path, 'JSON_CYCLE', 'JSON value must not contain cycles')
    return
  }
  active.add(value)
  try {
    if (Array.isArray(value)) {
      value.forEach((item, index) => validateJsonValue(item, `${path}[${index}]`, issues, active, depth + 1))
      return
    }
    const prototype = Object.getPrototypeOf(value)
    if (prototype !== Object.prototype && prototype !== null) {
      issue(issues, path, 'NON_PLAIN_OBJECT', 'JSON object must be a plain object')
      return
    }
    for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
      if (HIDDEN_REASONING_KEY_RE.test(key)) {
        issue(issues, `${path}.${key}`, 'HIDDEN_REASONING_FORBIDDEN', 'Hidden/private reasoning must not enter public execution contracts')
      }
      validateJsonValue(item, `${path}.${key}`, issues, active, depth + 1)
    }
  } finally {
    active.delete(value)
  }
}

const boundedJsonRecord = (
  value: unknown,
  path: string,
  issues: ContractValidationIssue[],
  maxBytes: number,
): Record<string, unknown> | undefined => {
  const record = recordOf(value)
  if (!record) {
    issue(issues, path, 'REQUIRED_OBJECT', `${path} must be a plain object`)
    return undefined
  }
  validateJsonValue(record, path, issues, new Set<object>(), 0)
  try {
    const bytes = canonicalJsonBytes(record)
    if (bytes > maxBytes) {
      issue(issues, path, 'JSON_BUDGET_EXCEEDED', `${path} is ${bytes} bytes; maximum is ${maxBytes}`)
    }
  } catch (error) {
    issue(issues, path, 'NON_CANONICAL_JSON', error instanceof Error ? error.message : String(error))
  }
  return record
}

const validationResult = <T>(
  value: unknown,
  issues: ContractValidationIssue[],
): ContractValidationResult<T> => issues.length === 0
  ? { valid: true, issues: [], value: value as T }
  : { valid: false, issues }

const validateCompletionPolicyRecord = (
  value: unknown,
  path: string,
  issues: ContractValidationIssue[],
): CompletionPolicyV01 | undefined => {
  const record = recordOf(value)
  if (!record) {
    issue(issues, path, 'REQUIRED_OBJECT', 'completionPolicy must be an object')
    return undefined
  }
  exactKeys(record, [
    'requireAllMustSatisfied',
    'requireNoViolations',
    'requireReflection',
    'requireKnowledgeDecision',
    'requireContextUpdate',
    'requireClosureReceipt',
    'allowShouldWarnings',
    'requiredClosureModuleIds',
  ], path, issues)
  requireBoolean(record, 'requireAllMustSatisfied', path, issues)
  requireBoolean(record, 'requireNoViolations', path, issues)
  requireBoolean(record, 'requireReflection', path, issues)
  requireBoolean(record, 'requireKnowledgeDecision', path, issues)
  requireBoolean(record, 'requireContextUpdate', path, issues)
  requireBoolean(record, 'requireClosureReceipt', path, issues)
  requireBoolean(record, 'allowShouldWarnings', path, issues)
  stringArray(record.requiredClosureModuleIds, `${path}.requiredClosureModuleIds`, issues, {
    allowEmpty: true,
    identifier: true,
    maxItems: 64,
  })
  return record as unknown as CompletionPolicyV01
}

const dependencyCycle = (
  obligations: readonly ObligationDefinitionV01[],
): string[] | undefined => {
  const graph = new Map(obligations.map(item => [item.id, item.dependencies ?? []]))
  const visiting = new Set<string>()
  const visited = new Set<string>()
  const stack: string[] = []
  const visit = (id: string): string[] | undefined => {
    if (visiting.has(id)) {
      const start = stack.indexOf(id)
      return [...stack.slice(start), id]
    }
    if (visited.has(id)) return undefined
    visiting.add(id)
    stack.push(id)
    for (const dependency of graph.get(id) ?? []) {
      const cycle = visit(dependency)
      if (cycle) return cycle
    }
    stack.pop()
    visiting.delete(id)
    visited.add(id)
    return undefined
  }
  for (const id of graph.keys()) {
    const cycle = visit(id)
    if (cycle) return cycle
  }
  return undefined
}

export const validateTaskSupervisionContract = (
  value: unknown,
): ContractValidationResult<TaskSupervisionContractV01> => {
  const issues: ContractValidationIssue[] = []
  const record = recordOf(value)
  if (!record) {
    issue(issues, '$', 'REQUIRED_OBJECT', 'Task Supervision Contract must be an object')
    return { valid: false, issues }
  }
  exactKeys(record, [
    'schema',
    'projectId',
    'taskId',
    'agentId',
    'contextHash',
    'routeHash',
    'projectRevision',
    'supervisionLevel',
    'obligations',
    'evidencePolicies',
    'completionPolicy',
  ], '$', issues)
  if (record.schema !== TASK_SUPERVISION_CONTRACT_SCHEMA) {
    issue(issues, '$.schema', 'INVALID_SCHEMA', `schema must be ${TASK_SUPERVISION_CONTRACT_SCHEMA}`)
  }
  requireString(record, 'projectId', '$', issues, { identifier: true })
  requireString(record, 'taskId', '$', issues, { identifier: true })
  requireString(record, 'agentId', '$', issues, { identifier: true })
  requireString(record, 'contextHash', '$', issues, { hash: true })
  requireString(record, 'routeHash', '$', issues, { hash: true })
  optionalString(record, 'projectRevision', '$', issues, { max: MAX_REFERENCE_CHARS })
  requireEnum(record, 'supervisionLevel', SUPERVISION_LEVELS, '$', issues)

  let obligations: ObligationDefinitionV01[] = []
  if (!Array.isArray(record.obligations)) {
    issue(issues, '$.obligations', 'REQUIRED_ARRAY', 'obligations must be an array')
  } else {
    if (record.obligations.length === 0) {
      issue(issues, '$.obligations', 'EMPTY_ARRAY', 'A governed task must contain at least one obligation')
    }
    if (record.obligations.length > MAX_OBLIGATION_COUNT) {
      issue(issues, '$.obligations', 'ARRAY_TOO_LARGE', `obligations exceeds ${MAX_OBLIGATION_COUNT}`)
    }
    const seen = new Set<string>()
    obligations = record.obligations.flatMap((item, index) => {
      const path = `$.obligations[${index}]`
      const obligation = recordOf(item)
      if (!obligation) {
        issue(issues, path, 'REQUIRED_OBJECT', 'obligation must be an object')
        return []
      }
      exactKeys(obligation, [
        'id',
        'kind',
        'severity',
        'sourceRefs',
        'target',
        'satisfaction',
        'dependencies',
      ], path, issues)
      const id = requireString(obligation, 'id', path, issues, { identifier: true })
      requireEnum(obligation, 'kind', OBLIGATION_KINDS, path, issues)
      requireEnum(obligation, 'severity', OBLIGATION_SEVERITIES, path, issues)
      stringArray(obligation.sourceRefs, `${path}.sourceRefs`, issues, {
        allowEmpty: true,
        maxItems: 256,
      })
      boundedJsonRecord(obligation.target, `${path}.target`, issues, MAX_EXECUTION_EVENT_PAYLOAD_BYTES)
      boundedJsonRecord(obligation.satisfaction, `${path}.satisfaction`, issues, MAX_EXECUTION_EVENT_PAYLOAD_BYTES)
      if ('dependencies' in obligation) {
        stringArray(obligation.dependencies, `${path}.dependencies`, issues, {
          allowEmpty: true,
          identifier: true,
          maxItems: 256,
        })
      }
      if (id) {
        if (seen.has(id)) issue(issues, `${path}.id`, 'DUPLICATE_OBLIGATION_ID', `Duplicate obligation id ${id}`)
        seen.add(id)
      }
      return [obligation as unknown as ObligationDefinitionV01]
    })
    const ids = new Set(obligations.map(item => item.id))
    obligations.forEach((item, index) => {
      for (const dependency of item.dependencies ?? []) {
        if (dependency === item.id) {
          issue(issues, `$.obligations[${index}].dependencies`, 'SELF_DEPENDENCY', `${item.id} cannot depend on itself`)
        } else if (!ids.has(dependency)) {
          issue(issues, `$.obligations[${index}].dependencies`, 'UNKNOWN_DEPENDENCY', `Unknown obligation dependency ${dependency}`)
        }
      }
    })
    const cycle = dependencyCycle(obligations)
    if (cycle) issue(issues, '$.obligations', 'DEPENDENCY_CYCLE', `Obligation dependency cycle: ${cycle.join(' -> ')}`)
  }

  if (!Array.isArray(record.evidencePolicies)) {
    issue(issues, '$.evidencePolicies', 'REQUIRED_ARRAY', 'evidencePolicies must be an array')
  } else {
    if (record.evidencePolicies.length > MAX_EVIDENCE_POLICY_COUNT) {
      issue(issues, '$.evidencePolicies', 'ARRAY_TOO_LARGE', `evidencePolicies exceeds ${MAX_EVIDENCE_POLICY_COUNT}`)
    }
    const obligationIds = new Set(obligations.map(item => item.id))
    const seen = new Set<string>()
    record.evidencePolicies.forEach((item, index) => {
      const path = `$.evidencePolicies[${index}]`
      const policy = recordOf(item)
      if (!policy) {
        issue(issues, path, 'REQUIRED_OBJECT', 'evidence policy must be an object')
        return
      }
      exactKeys(policy, [
        'id',
        'obligationIds',
        'acceptedProviderIds',
        'acceptedProviderKinds',
        'acceptedResultStatuses',
        'requireExactContextHash',
        'requireExactProjectRevision',
        'requireExactTargetIdentity',
        'maxAgeSeconds',
      ], path, issues)
      const id = requireString(policy, 'id', path, issues, { identifier: true })
      if (id) {
        if (seen.has(id)) issue(issues, `${path}.id`, 'DUPLICATE_EVIDENCE_POLICY_ID', `Duplicate evidence policy id ${id}`)
        seen.add(id)
      }
      const applies = stringArray(policy.obligationIds, `${path}.obligationIds`, issues, {
        identifier: true,
        maxItems: 256,
      })
      for (const obligationId of applies ?? []) {
        if (!obligationIds.has(obligationId)) {
          issue(issues, `${path}.obligationIds`, 'UNKNOWN_OBLIGATION', `Evidence policy references unknown obligation ${obligationId}`)
        }
      }
      const providerIds = stringArray(policy.acceptedProviderIds, `${path}.acceptedProviderIds`, issues, {
        allowEmpty: true,
        identifier: true,
        maxItems: 256,
      })
      const providerKinds = policy.acceptedProviderKinds
      if (!Array.isArray(providerKinds)) {
        issue(issues, `${path}.acceptedProviderKinds`, 'REQUIRED_ARRAY', 'acceptedProviderKinds must be an array')
      } else {
        providerKinds.forEach((kind, kindIndex) => {
          if (typeof kind !== 'string' || !EVIDENCE_PROVIDER_KINDS.includes(kind as never)) {
            issue(issues, `${path}.acceptedProviderKinds[${kindIndex}]`, 'INVALID_ENUM', `Unknown evidence provider kind ${String(kind)}`)
          }
        })
        if (new Set(providerKinds).size !== providerKinds.length) {
          issue(issues, `${path}.acceptedProviderKinds`, 'DUPLICATE_ITEM', 'acceptedProviderKinds must be unique')
        }
      }
      if ((providerIds?.length ?? 0) === 0 && (Array.isArray(providerKinds) ? providerKinds.length : 0) === 0) {
        issue(issues, path, 'NO_TRUSTED_PROVIDER', 'Evidence policy must authorize at least one provider id or kind')
      }
      const resultStatuses = policy.acceptedResultStatuses
      if (!Array.isArray(resultStatuses) || resultStatuses.length === 0) {
        issue(issues, `${path}.acceptedResultStatuses`, 'REQUIRED_ARRAY', 'acceptedResultStatuses must be a non-empty array')
      } else {
        resultStatuses.forEach((status, statusIndex) => {
          if (typeof status !== 'string' || !EVIDENCE_RESULT_STATUSES.includes(status as never)) {
            issue(issues, `${path}.acceptedResultStatuses[${statusIndex}]`, 'INVALID_ENUM', `Unknown evidence result status ${String(status)}`)
          }
        })
        if (new Set(resultStatuses).size !== resultStatuses.length) {
          issue(issues, `${path}.acceptedResultStatuses`, 'DUPLICATE_ITEM', 'acceptedResultStatuses must be unique')
        }
      }
      requireBoolean(policy, 'requireExactContextHash', path, issues)
      requireBoolean(policy, 'requireExactProjectRevision', path, issues)
      requireBoolean(policy, 'requireExactTargetIdentity', path, issues)
      if ('maxAgeSeconds' in policy) requireInteger(policy, 'maxAgeSeconds', path, issues, 1)
    })
  }

  validateCompletionPolicyRecord(record.completionPolicy, '$.completionPolicy', issues)
  try {
    const bytes = canonicalJsonBytes(record)
    if (bytes > MAX_TASK_SUPERVISION_CONTRACT_BYTES) {
      issue(issues, '$', 'CONTRACT_BUDGET_EXCEEDED', `Task Supervision Contract is ${bytes} bytes; maximum is ${MAX_TASK_SUPERVISION_CONTRACT_BYTES}`)
    }
  } catch (error) {
    issue(issues, '$', 'NON_CANONICAL_JSON', error instanceof Error ? error.message : String(error))
  }
  return validationResult<TaskSupervisionContractV01>(value, issues)
}

export const validateExecutionEventEnvelope = (
  value: unknown,
): ContractValidationResult<ExecutionEventEnvelopeV01> => {
  const issues: ContractValidationIssue[] = []
  const record = recordOf(value)
  if (!record) {
    issue(issues, '$', 'REQUIRED_OBJECT', 'Execution Event must be an object')
    return { valid: false, issues }
  }
  exactKeys(record, [
    'schema',
    'requestId',
    'runtimeId',
    'projectId',
    'taskId',
    'turnId',
    'agentId',
    'contextHash',
    'sequence',
    'eventId',
    'timestamp',
    'kind',
    'payloadHash',
    'payload',
  ], '$', issues)
  if (record.schema !== EXECUTION_EVENT_SCHEMA) {
    issue(issues, '$.schema', 'INVALID_SCHEMA', `schema must be ${EXECUTION_EVENT_SCHEMA}`)
  }
  for (const key of ['requestId', 'runtimeId', 'projectId', 'taskId', 'turnId', 'agentId', 'eventId']) {
    requireString(record, key, '$', issues, { identifier: true })
  }
  requireString(record, 'contextHash', '$', issues, { hash: true })
  requireInteger(record, 'sequence', '$', issues, 1)
  requireTimestamp(record, 'timestamp', '$', issues)
  requireEnum(record, 'kind', EXECUTION_EVENT_KINDS, '$', issues)
  const payloadHash = requireString(record, 'payloadHash', '$', issues, { hash: true })
  const payload = boundedJsonRecord(record.payload, '$.payload', issues, MAX_EXECUTION_EVENT_PAYLOAD_BYTES)
  if (payload && payloadHash) {
    try {
      const actual = hashCanonicalJson(payload)
      if (actual !== payloadHash) {
        issue(issues, '$.payloadHash', 'PAYLOAD_HASH_MISMATCH', `payloadHash ${payloadHash} does not match canonical payload hash ${actual}`)
      }
    } catch (error) {
      issue(issues, '$.payload', 'NON_CANONICAL_JSON', error instanceof Error ? error.message : String(error))
    }
  }
  return validationResult<ExecutionEventEnvelopeV01>(value, issues)
}

export const validateExecutionEventStoreBinding = (
  value: unknown,
): ContractValidationResult<ExecutionEventStoreBindingV01> => {
  const issues: ContractValidationIssue[] = []
  const record = recordOf(value)
  if (!record) {
    issue(issues, '$', 'REQUIRED_OBJECT', 'Execution Event Store binding must be an object')
    return { valid: false, issues }
  }
  exactKeys(record, ['requestId', 'runtimeId', 'turnId', 'contract'], '$', issues)
  requireString(record, 'requestId', '$', issues, { identifier: true })
  requireString(record, 'runtimeId', '$', issues, { identifier: true })
  requireString(record, 'turnId', '$', issues, { identifier: true })
  const contract = validateTaskSupervisionContract(record.contract)
  if (!contract.valid) {
    for (const nested of contract.issues) {
      const suffix = nested.path === '$' ? '' : nested.path.slice(1)
      issue(issues, `$.contract${suffix}`, nested.code, nested.message)
    }
  }
  return validationResult<ExecutionEventStoreBindingV01>(value, issues)
}

export const validateExecutionEventStoreLimits = (
  value: unknown,
): ContractValidationResult<ExecutionEventStoreLimitsV01> => {
  const issues: ContractValidationIssue[] = []
  const record = recordOf(value)
  if (!record) {
    issue(issues, '$', 'REQUIRED_OBJECT', 'Execution Event Store limits must be an object')
    return { valid: false, issues }
  }
  exactKeys(record, ['maxEvents', 'maxStoreBytes', 'maxReplayEvents'], '$', issues)
  const maxEvents = requireInteger(record, 'maxEvents', '$', issues, 1)
  requireInteger(record, 'maxStoreBytes', '$', issues, 1)
  const maxReplayEvents = requireInteger(record, 'maxReplayEvents', '$', issues, 1)
  if (maxEvents !== undefined && maxReplayEvents !== undefined && maxReplayEvents > maxEvents) {
    issue(issues, '$.maxReplayEvents', 'REPLAY_LIMIT_EXCEEDS_STORE_LIMIT', 'maxReplayEvents cannot exceed maxEvents')
  }
  return validationResult<ExecutionEventStoreLimitsV01>(value, issues)
}

export const validateExecutionReplayCursor = (
  value: unknown,
): ContractValidationResult<ExecutionReplayCursorV01> => {
  const issues: ContractValidationIssue[] = []
  const record = recordOf(value)
  if (!record) {
    issue(issues, '$', 'REQUIRED_OBJECT', 'Execution replay cursor must be an object')
    return { valid: false, issues }
  }
  exactKeys(record, ['sequence', 'stateHash'], '$', issues)
  requireInteger(record, 'sequence', '$', issues, 0)
  requireString(record, 'stateHash', '$', issues, { hash: true })
  return validationResult<ExecutionReplayCursorV01>(value, issues)
}

export const validateHostCapabilityContract = (
  value: unknown,
): ContractValidationResult<HostCapabilityContractV01> => {
  const issues: ContractValidationIssue[] = []
  const record = recordOf(value)
  if (!record) {
    issue(issues, '$', 'REQUIRED_OBJECT', 'Host Capability Contract must be an object')
    return { valid: false, issues }
  }
  exactKeys(record, ['schema', 'hostId', 'adapterId', 'capabilities'], '$', issues)
  if (record.schema !== HOST_CAPABILITY_CONTRACT_SCHEMA) {
    issue(issues, '$.schema', 'INVALID_SCHEMA', `schema must be ${HOST_CAPABILITY_CONTRACT_SCHEMA}`)
  }
  requireString(record, 'hostId', '$', issues, { identifier: true })
  requireString(record, 'adapterId', '$', issues, { identifier: true })
  const capabilities = recordOf(record.capabilities)
  if (!capabilities) {
    issue(issues, '$.capabilities', 'REQUIRED_OBJECT', 'capabilities must be an object')
  } else {
    const keys: (keyof HostCapabilityFlagsV01)[] = [
      'supportsPreflight',
      'supportsToolInterception',
      'supportsStableToolEventId',
      'supportsResourceHash',
      'supportsMessageRef',
      'supportsCrossProcessResume',
    ]
    exactKeys(capabilities, keys, '$.capabilities', issues)
    keys.forEach(key => requireBoolean(capabilities, key, '$.capabilities', issues))
  }
  return validationResult<HostCapabilityContractV01>(value, issues)
}

export const negotiateSupervisionLevel = (
  requestedLevel: SupervisionLevel,
  host: HostCapabilityContractV01,
): SupervisionNegotiationV01 => {
  if (requestedLevel === 'AUDIT') {
    return {
      requestedLevel,
      effectiveLevel: 'AUDIT',
      reasons: ['AUDIT was explicitly requested.'],
    }
  }
  const missing: string[] = []
  if (!host.capabilities.supportsPreflight) missing.push('supportsPreflight')
  if (!host.capabilities.supportsToolInterception) missing.push('supportsToolInterception')
  if (!host.capabilities.supportsStableToolEventId) missing.push('supportsStableToolEventId')
  return missing.length === 0
    ? {
        requestedLevel,
        effectiveLevel: 'ENFORCE',
        reasons: ['Host exposes the minimum preflight/interception/event-identity boundary required for ENFORCE.'],
      }
    : {
        requestedLevel,
        effectiveLevel: 'AUDIT',
        reasons: [`ENFORCE is unavailable because the Host lacks: ${missing.join(', ')}.`],
      }
}

export const validateCompletionDecision = (
  value: unknown,
): ContractValidationResult<CompletionDecisionV01> => {
  const issues: ContractValidationIssue[] = []
  const record = recordOf(value)
  if (!record) {
    issue(issues, '$', 'REQUIRED_OBJECT', 'Completion Decision must be an object')
    return { valid: false, issues }
  }
  exactKeys(record, [
    'status',
    'pendingObligationIds',
    'violatedObligationIds',
    'blockerRefs',
    'evidenceRefs',
    'closureRef',
  ], '$', issues)
  const status = requireEnum(record, 'status', COMPLETION_STATUSES, '$', issues)
  const pending = stringArray(record.pendingObligationIds, '$.pendingObligationIds', issues, {
    allowEmpty: true,
    identifier: true,
  })
  const violated = stringArray(record.violatedObligationIds, '$.violatedObligationIds', issues, {
    allowEmpty: true,
    identifier: true,
  })
  stringArray(record.blockerRefs, '$.blockerRefs', issues, { allowEmpty: true })
  stringArray(record.evidenceRefs, '$.evidenceRefs', issues, { allowEmpty: true })
  const closureRef = optionalString(record, 'closureRef', '$', issues)
  if ((status === 'READY_TO_CLOSE' || status === 'COMPLETE')
      && ((pending?.length ?? 0) > 0 || (violated?.length ?? 0) > 0)) {
    issue(issues, '$.status', 'UNRESOLVED_OBLIGATIONS', `${status} cannot contain pending or violated obligations`)
  }
  if (status === 'COMPLETE' && !closureRef) {
    issue(issues, '$.closureRef', 'CLOSURE_REQUIRED', 'COMPLETE requires a valid Closure Receipt reference')
  }
  if (status !== 'COMPLETE' && closureRef) {
    issue(issues, '$.closureRef', 'PREMATURE_CLOSURE_REF', 'closureRef is only valid for COMPLETE')
  }
  return validationResult<CompletionDecisionV01>(value, issues)
}

const validateBaselineSample = (
  value: unknown,
  path: string,
  issues: ContractValidationIssue[],
): PerformanceBaselineSampleV01 | undefined => {
  const record = recordOf(value)
  if (!record) {
    issue(issues, path, 'REQUIRED_OBJECT', 'Performance baseline sample must be an object')
    return undefined
  }
  exactKeys(record, [
    'scenario',
    'warmupIterations',
    'sampleIterations',
    'inputBytes',
    'p50Micros',
    'p95Micros',
    'p99Micros',
    'meanMicros',
    'maxMicros',
  ], path, issues)
  requireString(record, 'scenario', path, issues, { identifier: true })
  requireInteger(record, 'warmupIterations', path, issues, 0)
  requireInteger(record, 'sampleIterations', path, issues, 1)
  requireInteger(record, 'inputBytes', path, issues, 1)
  const p50 = requireFiniteNumber(record, 'p50Micros', path, issues)
  const p95 = requireFiniteNumber(record, 'p95Micros', path, issues)
  const p99 = requireFiniteNumber(record, 'p99Micros', path, issues)
  const mean = requireFiniteNumber(record, 'meanMicros', path, issues)
  const max = requireFiniteNumber(record, 'maxMicros', path, issues)
  if (p50 !== undefined && p95 !== undefined && p99 !== undefined && max !== undefined
      && !(p50 <= p95 && p95 <= p99 && p99 <= max)) {
    issue(issues, path, 'INVALID_PERCENTILES', 'Expected p50 <= p95 <= p99 <= max')
  }
  if (mean !== undefined && max !== undefined && mean > max) {
    issue(issues, `${path}.meanMicros`, 'INVALID_MEAN', 'meanMicros cannot exceed maxMicros')
  }
  return record as unknown as PerformanceBaselineSampleV01
}

export const validatePerformanceBaselineReport = (
  value: unknown,
): ContractValidationResult<PerformanceBaselineReportV01> => {
  const issues: ContractValidationIssue[] = []
  const record = recordOf(value)
  if (!record) {
    issue(issues, '$', 'REQUIRED_OBJECT', 'Performance Baseline Report must be an object')
    return { valid: false, issues }
  }
  exactKeys(record, [
    'schema',
    'baselineId',
    'capturedAt',
    'sourceRevision',
    'environment',
    'thresholdsFrozen',
    'invariants',
    'samples',
    'notes',
  ], '$', issues)
  if (record.schema !== PERFORMANCE_BASELINE_REPORT_SCHEMA) {
    issue(issues, '$.schema', 'INVALID_SCHEMA', `schema must be ${PERFORMANCE_BASELINE_REPORT_SCHEMA}`)
  }
  requireString(record, 'baselineId', '$', issues, { identifier: true })
  requireTimestamp(record, 'capturedAt', '$', issues)
  requireString(record, 'sourceRevision', '$', issues)
  if (record.thresholdsFrozen !== false) {
    issue(issues, '$.thresholdsFrozen', 'PHASE0_THRESHOLDS_MUST_REMAIN_UNFROZEN', 'Phase 0 captures measurements but does not freeze numeric SLOs')
  }
  const environment = recordOf(record.environment)
  if (!environment) {
    issue(issues, '$.environment', 'REQUIRED_OBJECT', 'environment must be an object')
  } else {
    exactKeys(environment, ['nodeVersion', 'platform', 'architecture'], '$.environment', issues)
    requireString(environment, 'nodeVersion', '$.environment', issues)
    requireString(environment, 'platform', '$.environment', issues, { identifier: true })
    requireString(environment, 'architecture', '$.environment', issues, { identifier: true })
  }
  const invariants = recordOf(record.invariants)
  if (!invariants) {
    issue(issues, '$.invariants', 'REQUIRED_OBJECT', 'invariants must be an object')
  } else {
    exactKeys(invariants, [
      'noSemanticCallOnHotPath',
      'noFullRerouteForOrdinaryRead',
      'maxUnifiedReflectionsPerTurn',
      'maxEventPayloadBytes',
      'maxTaskContractBytes',
    ], '$.invariants', issues)
    if (invariants.noSemanticCallOnHotPath !== true) {
      issue(issues, '$.invariants.noSemanticCallOnHotPath', 'HOT_PATH_SEMANTIC_CALL_FORBIDDEN', 'Hot path must not invoke a semantic model')
    }
    if (invariants.noFullRerouteForOrdinaryRead !== true) {
      issue(issues, '$.invariants.noFullRerouteForOrdinaryRead', 'ORDINARY_READ_REROUTE_FORBIDDEN', 'Ordinary reads must not trigger a full route refresh')
    }
    if (invariants.maxUnifiedReflectionsPerTurn !== 1) {
      issue(issues, '$.invariants.maxUnifiedReflectionsPerTurn', 'REFLECTION_BUDGET_INVALID', 'Maximum Unified Reflections per Turn must be one')
    }
    if (invariants.maxEventPayloadBytes !== MAX_EXECUTION_EVENT_PAYLOAD_BYTES) {
      issue(issues, '$.invariants.maxEventPayloadBytes', 'PAYLOAD_BUDGET_MISMATCH', 'Baseline payload budget does not match the contract constant')
    }
    if (invariants.maxTaskContractBytes !== MAX_TASK_SUPERVISION_CONTRACT_BYTES) {
      issue(issues, '$.invariants.maxTaskContractBytes', 'CONTRACT_BUDGET_MISMATCH', 'Baseline contract budget does not match the contract constant')
    }
  }
  if (!Array.isArray(record.samples) || record.samples.length === 0) {
    issue(issues, '$.samples', 'REQUIRED_ARRAY', 'samples must be a non-empty array')
  } else {
    const scenarios = new Set<string>()
    record.samples.forEach((sample, index) => {
      const validated = validateBaselineSample(sample, `$.samples[${index}]`, issues)
      if (validated) {
        if (scenarios.has(validated.scenario)) {
          issue(issues, `$.samples[${index}].scenario`, 'DUPLICATE_SCENARIO', `Duplicate scenario ${validated.scenario}`)
        }
        scenarios.add(validated.scenario)
      }
    })
  }
  stringArray(record.notes, '$.notes', issues, { allowEmpty: true, maxItems: 64 })
  return validationResult<PerformanceBaselineReportV01>(value, issues)
}

export const assertValidTaskSupervisionContract = (
  value: unknown,
): TaskSupervisionContractV01 => {
  const result = validateTaskSupervisionContract(value)
  if (!result.valid) throw new TypeError(result.issues.map(item => `${item.path} ${item.code}: ${item.message}`).join('\n'))
  return result.value
}

export const assertValidExecutionEventEnvelope = (
  value: unknown,
): ExecutionEventEnvelopeV01 => {
  const result = validateExecutionEventEnvelope(value)
  if (!result.valid) throw new TypeError(result.issues.map(item => `${item.path} ${item.code}: ${item.message}`).join('\n'))
  return result.value
}

export const assertValidExecutionEventStoreBinding = (
  value: unknown,
): ExecutionEventStoreBindingV01 => {
  const result = validateExecutionEventStoreBinding(value)
  if (!result.valid) throw new TypeError(result.issues.map(item => `${item.path} ${item.code}: ${item.message}`).join('\n'))
  return result.value
}

export const assertValidExecutionEventStoreLimits = (
  value: unknown,
): ExecutionEventStoreLimitsV01 => {
  const result = validateExecutionEventStoreLimits(value)
  if (!result.valid) throw new TypeError(result.issues.map(item => `${item.path} ${item.code}: ${item.message}`).join('\n'))
  return result.value
}

export const assertValidExecutionReplayCursor = (
  value: unknown,
): ExecutionReplayCursorV01 => {
  const result = validateExecutionReplayCursor(value)
  if (!result.valid) throw new TypeError(result.issues.map(item => `${item.path} ${item.code}: ${item.message}`).join('\n'))
  return result.value
}
