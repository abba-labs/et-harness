import { posix } from 'node:path'
import {
  OBLIGATION_LEDGER_STATUS_SCHEMA,
  type CreateExecutionObligationLedgerInputV01,
  type ContractValidationIssue,
  type ContractValidationResult,
  type ExecutionEventAcceptanceV01,
  type ExecutionEventEnvelopeV01,
  type ExecutionEventStoreBindingV01,
  type ExecutionEventStoreV01,
  type ExecutionObligationLedgerV01,
  type ExecutionReplayCursorV01,
  type JsonRecord,
  type MutationReceiptV01,
  type ObligationDefinitionV01,
  type ObligationLedgerStatusV01,
  type ObligationState,
  type ObligationStateRecordV01,
  type ObligationViolationRecordV01,
  type RequiredResourceSatisfactionV01,
  type RequiredResourceTargetV01,
  type ResourceReceiptV01,
  type SourceDisposition,
  type TaskSupervisionContractV01,
  type WriteScopeTargetV01,
} from './contracts.js'
import { canonicalJson, hashCanonicalJson } from './hash.js'
import { validateTaskSupervisionContract } from './validation.js'

const LEDGER_GENESIS_TIMESTAMP = '1970-01-01T00:00:00.000Z'
const SHA256_PATTERN = /^[0-9a-f]{64}$/

interface MutableObligationStateRecord {
  obligationId: string
  state: ObligationState
  updatedAt: string
  eventRefs: string[]
  evidenceRefs: string[]
  blockerRefs: string[]
  violationRefs: string[]
  reason?: string
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

const uniqueAppend = (values: string[], value: string): void => {
  if (!values.includes(value)) values.push(value)
}

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

const writeAllowed = (
  obligation: ObligationDefinitionV01,
  receipt: MutationReceiptV01,
): boolean => {
  // The v0.1 mutation receipt has only one path/resource identity and cannot
  // prove both endpoints of MOVE or COPY. Fail closed until that contract grows.
  if (receipt.action === 'MOVE' || receipt.action === 'COPY') return false
  const target = recordOf(obligation.target)
  const satisfaction = recordOf(obligation.satisfaction)
  if (!target || satisfaction?.requireInScope !== true) return false
  const allowedResourceIds = stringArray(target.allowedResourceIds)
  const allowedPathPrefixes = target.allowedPathPrefixes === undefined
    ? []
    : stringArray(target.allowedPathPrefixes)
  if (!allowedResourceIds || !allowedPathPrefixes) return false
  if (allowedResourceIds.includes(receipt.resourceId)) return true
  return receipt.path !== undefined
    && allowedPathPrefixes.some(prefix => pathWithinPrefix(receipt.path!, prefix))
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
  readonly #binding: ExecutionEventStoreBindingV01
  readonly #contractHash: string
  readonly #definitions: readonly ObligationDefinitionV01[]
  readonly #definitionsById: ReadonlyMap<string, ObligationDefinitionV01>
  readonly #dependentsById: ReadonlyMap<string, readonly string[]>
  readonly #states: Map<string, MutableObligationStateRecord>
  readonly #violations: ObligationViolationRecordV01[] = []
  readonly #violationIds = new Set<string>()
  #cursor: ExecutionReplayCursorV01 | undefined

  constructor(eventStore: ExecutionEventStoreV01) {
    this.#eventStore = eventStore
    this.#binding = immutableSnapshot(eventStore.binding)
    this.#contractHash = hashCanonicalJson(this.#binding.contract)
    this.#definitions = this.#binding.contract.obligations
    this.#definitionsById = new Map(this.#definitions.map(item => [item.id, item]))
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
    if (acceptance.status === 'ACCEPTED') await this.synchronize()
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
      if (!page.hasMore) return
    }
  }

  getStatus(): ObligationLedgerStatusV01 {
    if (!this.#cursor) throw new Error('Obligation Ledger has not synchronized')
    const obligations: ObligationStateRecordV01[] = this.#definitions.map(definition => {
      const state = this.#states.get(definition.id)!
      return {
        obligationId: state.obligationId,
        state: state.state,
        updatedAt: state.updatedAt,
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

  #applyEvent(event: ExecutionEventEnvelopeV01): void {
    if (event.kind === 'RESOURCE_READ') {
      const receipt = resourceReceipt(event)
      if (receipt) this.#applyResourceRead(event, receipt)
    } else if (event.kind === 'RESOURCE_WRITE') {
      const receipt = mutationReceipt(event)
      if (receipt) this.#applyResourceWrite(event, receipt)
    }
  }

  #applyResourceRead(
    event: ExecutionEventEnvelopeV01,
    receipt: ResourceReceiptV01,
  ): void {
    for (const definition of this.#definitions) {
      if (definition.kind !== 'REQUIRED_RESOURCE') continue
      const state = this.#states.get(definition.id)!
      if (state.state !== 'PENDING' || !readMatches(definition, receipt)) continue
      state.state = 'SATISFIED'
      state.updatedAt = event.timestamp
      uniqueAppend(state.eventRefs, event.eventId)
      state.reason = 'Matching accepted resource receipt'
      this.#updateDependencyDescendants(definition.id, event)
    }
  }

  #applyResourceWrite(
    event: ExecutionEventEnvelopeV01,
    receipt: MutationReceiptV01,
  ): void {
    for (const definition of this.#definitions) {
      if (definition.kind !== 'WRITE_SCOPE' || writeAllowed(definition, receipt)) continue
      const violation = violationFor(definition, event, receipt)
      if (this.#violationIds.has(violation.id)) continue
      this.#violationIds.add(violation.id)
      this.#violations.push(violation)
      const state = this.#states.get(definition.id)!
      state.state = 'VIOLATED'
      state.updatedAt = event.timestamp
      uniqueAppend(state.eventRefs, event.eventId)
      uniqueAppend(state.violationRefs, violation.id)
      state.reason = 'Observed write is outside the contributed scope'
      this.#updateDependencyDescendants(definition.id, event)
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
      if (state.state === 'BLOCKED') {
        const blockers = (definition.dependencies ?? []).filter(dependency => {
          const dependencyState = this.#states.get(dependency)!.state
          return !['SATISFIED', 'NOT_APPLICABLE', 'WAIVED'].includes(dependencyState)
        })
        state.blockerRefs = blockers
        state.updatedAt = event.timestamp
        uniqueAppend(state.eventRefs, event.eventId)
        if (blockers.length === 0) {
          state.state = 'PENDING'
          state.reason = 'All declared dependencies are satisfied'
        }
      }
      queue.push(...(this.#dependentsById.get(obligationId) ?? []))
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
  const ledger = new ExecutionObligationLedger(input.eventStore)
  await ledger.synchronize()
  return ledger
}
