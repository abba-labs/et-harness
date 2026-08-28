import { createHash } from 'node:crypto'
import { isAbsolute } from 'node:path'
import type { GovernanceProviderRegistration } from '@agent-harness/governance-core'
import type { ProjectContext } from '@agent-harness/project-contract'
import type {
  ContextPriority,
  ContextReference,
  InlineContextItem,
} from '@agent-harness/context-builder'
import type { AutoGovernanceRouteSnapshot } from './contracts.js'

export const PROJECT_CONTEXT_CONTRIBUTION_CAPABILITY = 'context.contribute'
export const PROJECT_CONTEXT_CONTRIBUTION_REQUEST_SCHEMA =
  'agent-harness.project-context-contribution-request.v0.1'
export const PROJECT_CONTEXT_CONTRIBUTION_SCHEMA =
  'agent-harness.project-context-contribution.v0.1'

const MAX_CONTRIBUTION_REFERENCES = 32
const MAX_CONTRIBUTION_INLINE_ITEMS = 24
const MAX_INLINE_ITEM_CHARS = 8_000
const MAX_TOTAL_INLINE_CHARS = 16_000
const MAX_SCOPE_ENTRIES = 128
const MAX_VALIDATION_OBLIGATIONS = 64
const IDENTIFIER_RE = /^[A-Za-z0-9._:-]+$/
const RESOURCE_ID_RE: Readonly<Record<ContextReference['kind'], RegExp>> = {
  architecture: /^A\d{3}(?:\.\d{3})*$/,
  rule: /^R\d{3}(?:\.\d{3})*$/,
  knowledge: /^K\d{3}(?:\.\d{3})*$/,
  gate: /^G\d{3}(?:\.\d{3})*$/,
}

export interface ProjectContextContributionRequestV01 {
  readonly schema: typeof PROJECT_CONTEXT_CONTRIBUTION_REQUEST_SCHEMA
  readonly projectId: string
  readonly taskId: string
  readonly rawTask: string
  readonly phase: 'analysis' | 'implementation'
  readonly workspacePath: string
  readonly initialRoute: AutoGovernanceRouteSnapshot
}

export interface ProjectContextContributionWriteScope {
  readonly allowed: readonly string[]
  readonly protected: readonly string[]
}

export interface ProjectContextContributionValidationObligation {
  readonly id: string
  readonly summary: string
  readonly command?: string
}

export interface ProjectContextContributionOutputContract {
  readonly id: string
  readonly title: string
  readonly content: string
}

export interface ProjectContextContributionV01 {
  readonly schema: typeof PROJECT_CONTEXT_CONTRIBUTION_SCHEMA
  readonly projectId: string
  readonly taskId: string
  readonly contributionId: string
  readonly provenance: string
  readonly references?: readonly ContextReference[]
  readonly inlineItems?: readonly InlineContextItem[]
  readonly readScope?: readonly string[]
  readonly writeScope?: ProjectContextContributionWriteScope
  readonly validation?: readonly ProjectContextContributionValidationObligation[]
  readonly outputContract?: ProjectContextContributionOutputContract
}

export type ProjectContextContributionProviderResult =
  | {
      readonly applicable: false
      readonly reason: string
    }
  | {
      readonly applicable: true
      readonly contribution: ProjectContextContributionV01
    }

export interface NormalizedProjectContextContribution {
  readonly providerId: string
  readonly contributionId: string
  readonly fingerprint: string
  readonly references: readonly ContextReference[]
  readonly inlineItems: readonly InlineContextItem[]
}

export interface ProjectContextContributionReceipt {
  readonly providerId: string
  readonly contributionId: string
  readonly fingerprint: string
  readonly referenceIds: readonly string[]
  readonly inlineItemIds: readonly string[]
}

export interface ResolveDeclaredProjectContextContributionsInput {
  readonly project: ProjectContext
  readonly request: ProjectContextContributionRequestV01
  readonly providers: readonly GovernanceProviderRegistration[]
  readonly serviceLookup: (serviceName: string) => unknown
}

const recordOf = (value: unknown): Record<string, unknown> | undefined =>
  typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : undefined

const nonEmpty = (label: string, value: unknown): string => {
  if (typeof value !== 'string' || !value.trim()) throw new Error(`${label} cannot be empty`)
  return value.trim()
}

const singleLine = (label: string, value: unknown, maximum = 2_000): string => {
  const normalized = nonEmpty(label, value)
  if (/\r|\n/.test(normalized)) throw new Error(`${label} must be a single line`)
  if (normalized.length > maximum) throw new Error(`${label} exceeds ${maximum} characters`)
  return normalized
}

const identifier = (label: string, value: unknown): string => {
  const normalized = singleLine(label, value, 160)
  if (!IDENTIFIER_RE.test(normalized)) throw new Error(`${label} contains unsupported characters`)
  return normalized
}

const stableStringify = (value: unknown): string => {
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>
    return `{${Object.keys(record).sort().map(key =>
      `${JSON.stringify(key)}:${stableStringify(record[key])}`,
    ).join(',')}}`
  }
  return JSON.stringify(value)
}

const sha256 = (value: unknown): string =>
  `sha256:${createHash('sha256').update(stableStringify(value)).digest('hex')}`

const uniqueStrings = (values: readonly string[]): string[] =>
  [...new Set(values.map(value => value.trim()).filter(Boolean))]

const safeProjectRelativePath = (label: string, value: unknown): string => {
  const normalized = singleLine(label, value, 1_000).replaceAll('\\', '/')
  const segments = normalized.split('/')
  const windowsAbsolute = /^[A-Za-z]:\//.test(normalized)
  const uriLike = /^[A-Za-z][A-Za-z0-9+.-]*:\/\//.test(normalized)
  if (isAbsolute(normalized) || windowsAbsolute || uriLike
    || normalized.startsWith('/') || normalized.startsWith('//')
    || segments.includes('..')) {
    throw new Error(`${label} must be a safe project-relative path or glob`)
  }
  return normalized
}

const READ_SCOPE_URI_RE = /^(?:source|project|knowledge|evidence|runtime|provider):\/\/\S+$/

const safeReadScopeEntry = (label: string, value: unknown): string => {
  const normalized = singleLine(label, value, 1_000).replaceAll('\\', '/')
  if (READ_SCOPE_URI_RE.test(normalized)) return normalized
  if (/^[A-Za-z]:\//.test(normalized)) {
    throw new Error(`${label} must not use an absolute Windows path`)
  }
  return safeProjectRelativePath(label, normalized)
}

const normalizeReadScope = (values: readonly string[] | undefined): string[] => {
  if (!values) return []
  if (values.length > MAX_SCOPE_ENTRIES) throw new Error('readScope exceeds its entry budget')
  return uniqueStrings(values.map((value, index) => safeReadScopeEntry(`readScope[${index}]`, value)))
}

const normalizeWriteScope = (
  input: ProjectContextContributionWriteScope | undefined,
): ProjectContextContributionWriteScope | undefined => {
  if (!input) return undefined
  if (input.allowed.length > MAX_SCOPE_ENTRIES || input.protected.length > MAX_SCOPE_ENTRIES) {
    throw new Error('writeScope exceeds its entry budget')
  }
  return {
    allowed: uniqueStrings(input.allowed.map((value, index) =>
      safeProjectRelativePath(`writeScope.allowed[${index}]`, value),
    )),
    protected: uniqueStrings(input.protected.map((value, index) =>
      safeProjectRelativePath(`writeScope.protected[${index}]`, value),
    )),
  }
}

const normalizeReferences = (
  references: readonly ContextReference[] | undefined,
): ContextReference[] => {
  if (!references) return []
  if (references.length > MAX_CONTRIBUTION_REFERENCES) {
    throw new Error('context contribution references exceed their budget')
  }
  const deduped = new Map<string, ContextReference>()
  for (const reference of references) {
    const id = singleLine(`reference.${reference.kind}`, reference.id, 160).toUpperCase()
    if (!RESOURCE_ID_RE[reference.kind].test(id)) {
      throw new Error(`context contribution reference kind/id mismatch: ${reference.kind}:${id}`)
    }
    const normalized: ContextReference = {
      kind: reference.kind,
      id,
      ...(reference.priority ? { priority: reference.priority } : {}),
    }
    deduped.set(`${normalized.kind}:${normalized.id}`, normalized)
  }
  return [...deduped.values()]
}

const normalizeInlineItems = (
  items: readonly InlineContextItem[] | undefined,
  providerId: string,
  contributionId: string,
): InlineContextItem[] => {
  if (!items) return []
  if (items.length > MAX_CONTRIBUTION_INLINE_ITEMS) {
    throw new Error('context contribution inline items exceed their budget')
  }
  return items.map((item, index) => {
    const id = identifier(`inlineItems[${index}].id`, item.id)
    const content = nonEmpty(`inlineItems[${index}].content`, item.content)
    if (content.length > MAX_INLINE_ITEM_CHARS) {
      throw new Error(`inlineItems[${index}].content exceeds ${MAX_INLINE_ITEM_CHARS} characters`)
    }
    return {
      id: `contribution:${providerId}:${contributionId}:${id}`,
      title: singleLine(`inlineItems[${index}].title`, item.title, 240),
      content,
      priority: item.priority ?? 'high',
      provenance: nonEmpty(`inlineItems[${index}].provenance`, item.provenance),
    }
  })
}

const renderScopeItem = (
  providerId: string,
  contributionId: string,
  provenance: string,
  readScope: readonly string[],
  writeScope: ProjectContextContributionWriteScope | undefined,
): InlineContextItem | undefined => {
  if (readScope.length === 0 && !writeScope) return undefined
  const content = [
    'read_scope:',
    ...(readScope.length > 0 ? readScope.map(value => `- ${value}`) : ['-']),
    'write_scope:',
    '  allowed:',
    ...(writeScope?.allowed.length
      ? writeScope.allowed.map(value => `  - ${value}`)
      : ['  -']),
    '  protected:',
    ...(writeScope?.protected.length
      ? writeScope.protected.map(value => `  - ${value}`)
      : ['  -']),
  ].join('\n')
  return {
    id: `contribution:${providerId}:${contributionId}:scope`,
    title: 'Project Read / Write Scope Contract',
    content,
    priority: 'required',
    provenance,
  }
}

const renderValidationItem = (
  providerId: string,
  contributionId: string,
  provenance: string,
  validation: readonly ProjectContextContributionValidationObligation[] | undefined,
): InlineContextItem | undefined => {
  if (!validation || validation.length === 0) return undefined
  if (validation.length > MAX_VALIDATION_OBLIGATIONS) {
    throw new Error('validation obligations exceed their budget')
  }
  const entries = validation.map((item, index) => {
    const id = identifier(`validation[${index}].id`, item.id)
    const summary = singleLine(`validation[${index}].summary`, item.summary, 500)
    const command = item.command === undefined
      ? undefined
      : singleLine(`validation[${index}].command`, item.command, 2_000)
    return { id, summary, ...(command ? { command } : {}) }
  })
  return {
    id: `contribution:${providerId}:${contributionId}:validation`,
    title: 'Project Validation Obligations',
    content: entries.map(item =>
      `- ${item.id}: ${item.summary}${item.command ? ` | command=${item.command}` : ''}`,
    ).join('\n'),
    priority: 'required',
    provenance,
  }
}

const renderOutputContractItem = (
  providerId: string,
  contributionId: string,
  provenance: string,
  output: ProjectContextContributionOutputContract | undefined,
): InlineContextItem | undefined => {
  if (!output) return undefined
  const id = identifier('outputContract.id', output.id)
  const content = nonEmpty('outputContract.content', output.content)
  if (content.length > MAX_INLINE_ITEM_CHARS) {
    throw new Error(`outputContract.content exceeds ${MAX_INLINE_ITEM_CHARS} characters`)
  }
  return {
    id: `contribution:${providerId}:${contributionId}:output:${id}`,
    title: singleLine('outputContract.title', output.title, 240),
    content,
    priority: 'required',
    provenance,
  }
}

export function normalizeProjectContextContribution(
  providerIdInput: string,
  request: ProjectContextContributionRequestV01,
  contribution: ProjectContextContributionV01,
): NormalizedProjectContextContribution {
  const providerId = identifier('providerId', providerIdInput)
  if (contribution.schema !== PROJECT_CONTEXT_CONTRIBUTION_SCHEMA) {
    throw new Error(`unsupported context contribution schema: ${contribution.schema}`)
  }
  if (contribution.projectId !== request.projectId) {
    throw new Error(`context contribution project mismatch: ${contribution.projectId} != ${request.projectId}`)
  }
  if (contribution.taskId !== request.taskId) {
    throw new Error(`context contribution task mismatch: ${contribution.taskId} != ${request.taskId}`)
  }

  const contributionId = identifier('contributionId', contribution.contributionId)
  const provenance = nonEmpty('contribution.provenance', contribution.provenance)
  const references = normalizeReferences(contribution.references)
  const readScope = normalizeReadScope(contribution.readScope)
  const writeScope = normalizeWriteScope(contribution.writeScope)
  const inlineItems = normalizeInlineItems(
    contribution.inlineItems,
    providerId,
    contributionId,
  )
  const scopeItem = renderScopeItem(
    providerId,
    contributionId,
    provenance,
    readScope,
    writeScope,
  )
  const validationItem = renderValidationItem(
    providerId,
    contributionId,
    provenance,
    contribution.validation,
  )
  const outputItem = renderOutputContractItem(
    providerId,
    contributionId,
    provenance,
    contribution.outputContract,
  )
  const combined = [
    ...inlineItems,
    ...(scopeItem ? [scopeItem] : []),
    ...(validationItem ? [validationItem] : []),
    ...(outputItem ? [outputItem] : []),
  ]
  const deduped = new Map<string, InlineContextItem>()
  for (const item of combined) deduped.set(item.id, item)
  const normalizedItems = [...deduped.values()]
  if (normalizedItems.length > MAX_CONTRIBUTION_INLINE_ITEMS) {
    throw new Error('normalized context contribution inline items exceed their budget')
  }
  if (normalizedItems.reduce((total, item) => total + item.content.length, 0) > MAX_TOTAL_INLINE_CHARS) {
    throw new Error('normalized context contribution exceeds its total inline content budget')
  }

  const fingerprintPayload = {
    providerId,
    contributionId,
    projectId: request.projectId,
    taskId: request.taskId,
    references,
    inlineItems: normalizedItems,
  }
  return {
    providerId,
    contributionId,
    fingerprint: sha256(fingerprintPayload),
    references,
    inlineItems: normalizedItems,
  }
}

export function resolveDeclaredProjectContextContributions(
  input: ResolveDeclaredProjectContextContributionsInput,
): NormalizedProjectContextContribution[] {
  const declared = Object.entries(input.project.adapters)
    .filter(([, adapter]) => adapter.capability === PROJECT_CONTEXT_CONTRIBUTION_CAPABILITY)
    .sort(([left], [right]) => left.localeCompare(right))
  if (declared.length === 0) return []

  const providers = new Map(input.providers.map(provider => [provider.providerId, provider]))
  const results: NormalizedProjectContextContribution[] = []
  for (const [adapterName, adapter] of declared) {
    const provider = providers.get(adapter.provider)
    if (!provider) {
      throw new Error(`Project context adapter ${adapterName} requires unavailable provider ${adapter.provider}`)
    }
    if (provider.capability !== PROJECT_CONTEXT_CONTRIBUTION_CAPABILITY) {
      throw new Error(`Provider ${provider.providerId} does not provide ${PROJECT_CONTEXT_CONTRIBUTION_CAPABILITY}`)
    }
    const metadata = recordOf(provider.metadata)
    if (typeof metadata?.projectId === 'string' && metadata.projectId !== input.project.projectId) {
      throw new Error(`Context contributor ${provider.providerId} belongs to another project`)
    }
    const serviceName = singleLine(`provider ${provider.providerId} service`, metadata?.service, 160)
    const methodName = metadata?.method === undefined
      ? 'contributeContext'
      : singleLine(`provider ${provider.providerId} method`, metadata.method, 160)
    const service = recordOf(input.serviceLookup(serviceName))
    const method = service?.[methodName]
    if (typeof method !== 'function') {
      throw new Error(`Context contributor ${provider.providerId} service method is unavailable: ${serviceName}.${methodName}`)
    }
    const raw = method.call(service, input.request)
    if (raw && typeof (raw as { then?: unknown }).then === 'function') {
      throw new Error(`Context contributor ${provider.providerId} must be synchronous in contract v0.1`)
    }
    const response = recordOf(raw)
    if (!response || typeof response.applicable !== 'boolean') {
      throw new Error(`Context contributor ${provider.providerId} returned an invalid result`)
    }
    if (response.applicable === false) {
      singleLine(`Context contributor ${provider.providerId} not-applicable reason`, response.reason, 1_000)
      continue
    }
    results.push(normalizeProjectContextContribution(
      provider.providerId,
      input.request,
      response.contribution as ProjectContextContributionV01,
    ))
  }
  return results
}

export const contributionReceipt = (
  contribution: NormalizedProjectContextContribution,
): ProjectContextContributionReceipt => ({
  providerId: contribution.providerId,
  contributionId: contribution.contributionId,
  fingerprint: contribution.fingerprint,
  referenceIds: contribution.references.map(reference => `${reference.kind}:${reference.id}`),
  inlineItemIds: contribution.inlineItems.map(item => item.id),
})

export const mergeContributionInlineItems = (
  contributions: readonly NormalizedProjectContextContribution[],
): InlineContextItem[] => {
  const merged = new Map<string, InlineContextItem>()
  for (const contribution of contributions) {
    for (const item of contribution.inlineItems) {
      if (merged.has(item.id)) throw new Error(`Duplicate contributed inline item: ${item.id}`)
      merged.set(item.id, item)
    }
  }
  const items = [...merged.values()]
  if (items.length > MAX_CONTRIBUTION_INLINE_ITEMS) {
    throw new Error('combined project context contributions exceed the inline item budget')
  }
  if (items.reduce((total, item) => total + item.content.length, 0) > MAX_TOTAL_INLINE_CHARS) {
    throw new Error('combined project context contributions exceed the content budget')
  }
  return items
}

export const replaceContributionInlineItems = (
  existing: readonly InlineContextItem[],
  contributions: readonly NormalizedProjectContextContribution[],
): InlineContextItem[] => {
  const contributed = mergeContributionInlineItems(contributions)
  const preserved = existing.filter(item => !item.id.startsWith('contribution:'))
  const ids = new Set(preserved.map(item => item.id))
  for (const item of contributed) {
    if (ids.has(item.id)) throw new Error(`Duplicate Inline Context item: ${item.id}`)
    ids.add(item.id)
  }
  return [...preserved, ...contributed]
}

export const mergeContributionReferences = (
  contributions: readonly NormalizedProjectContextContribution[],
): ContextReference[] => {
  const merged = new Map<string, ContextReference>()
  const priorityRank: Readonly<Record<ContextPriority, number>> = {
    required: 4,
    high: 3,
    normal: 2,
    low: 1,
  }
  for (const contribution of contributions) {
    for (const reference of contribution.references) {
      const key = `${reference.kind}:${reference.id}`
      const current = merged.get(key)
      if (!current || priorityRank[reference.priority ?? 'normal'] > priorityRank[current.priority ?? 'normal']) {
        merged.set(key, reference)
      }
    }
  }
  return [...merged.values()]
}
