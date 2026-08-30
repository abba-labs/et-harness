import { createHash } from 'node:crypto'
import { spawnSync } from 'node:child_process'
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { isAbsolute, resolve } from 'node:path'
import { Service, type Context } from '@deepseek-ai/cordis'
import {
  PROJECT_CONTEXT_CONTRIBUTION_REQUEST_SCHEMA,
  PROJECT_CONTEXT_CONTRIBUTION_SCHEMA,
  PROJECT_SUPERVISION_CONTRIBUTION_SCHEMA,
  type ProjectContextContributionRequestV01,
  type ProjectContextContributionProviderResult,
  type ProjectContextContributionV01,
} from '@agent-harness/auto-governance-engine'
import {
  MANDATORY_LIFECYCLE_CLOSURE_MODULE_IDS,
  type EvidencePolicyV01,
  type ObligationDefinitionV01,
} from '@agent-harness/execution-supervisor'
import { findAutomatedTestingPlatformRoot } from './root-discovery.js'

export const ATP_PROJECT_ID = 'et-automated-testing-platform'
export const ATP_CONTEXT_CONTRIBUTOR_PLUGIN_ID =
  'project.automated-testing-platform'
export const ATP_CONTEXT_CONTRIBUTOR_PROVIDER_ID =
  'project.automated-testing-platform.context'
export const ATP_CONTEXT_CONTRIBUTOR_SERVICE = 'atpContextContributor'
export const ATP_TASK_CONTEXT_RELATIVE_PATH =
  'project-governance/runtime/current_task_context.json'

const ATP_TASK_CONTEXT_COMPILER = 'tools/governance/compile_task_context.py'
const ATP_IP_SOURCE_REGISTRY = 'project-governance/ip-analysis-sources.yaml'
const IDENTIFIER_RE = /^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/
const IP_ANALYSIS_MARKER_RE =
  /(?:分析|解析|梳理|研究|评估|说明|analy[sz]e|analysis|review|document)/i
const IP_MARKER_RE = /(?:^|[^A-Za-z0-9])IP(?=$|[^A-Za-z0-9])/i
const IP_STOP_WORDS = new Set([
  'analyze',
  'analysis',
  'review',
  'document',
  'chip',
  'soc',
  'this',
  'the',
  'an',
  'a',
  'ip',
])

export interface AtpIpAnalysisTask {
  readonly kind: 'ip-analysis'
  readonly module: 'ip-package'
  readonly change: 'analysis'
  readonly chip: string
  readonly chipUpper: string
  readonly ip: string
}

export interface AtpCompiledTaskContext {
  readonly schema: 'et.task-context.v1'
  readonly generated_at?: string
  readonly fingerprint: string
  readonly integrity_fingerprint: string
  readonly task: {
    readonly id: string
    readonly intent: string
    readonly modules: readonly string[]
    readonly changes: readonly string[]
    readonly lanes: readonly string[]
    readonly chip: string | null
    readonly ip: string | null
    readonly matched_changes_by_module?: Readonly<Record<string, readonly string[]>>
  }
  readonly repository?: Readonly<Record<string, unknown>>
  readonly source_inputs: readonly {
    readonly path: string
    readonly sha256: string
  }[]
  readonly architecture: readonly {
    readonly module: string
    readonly summary?: string
    readonly chain?: readonly unknown[]
  }[]
  readonly must_read: readonly {
    readonly path: string
    readonly reason: string
    readonly required: boolean
    readonly exists: boolean
  }[]
  readonly rule_owners: readonly {
    readonly owner_id: string
    readonly rule_id: string
    readonly source: string
    readonly heading: string
  }[]
  readonly write_scope: {
    readonly allowed: readonly string[]
    readonly protected: readonly string[]
  }
  readonly validation: readonly string[]
}

export interface CompileAtpTaskContextOptions {
  readonly outputPath?: string
  readonly pythonCommand?: string
}

const recordOf = (value: unknown): Record<string, unknown> | undefined =>
  typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : undefined

const stringValue = (value: unknown): string | undefined =>
  typeof value === 'string' && value.trim() ? value.trim() : undefined

const stringArray = (value: unknown): string[] | undefined =>
  Array.isArray(value) && value.every(item => typeof item === 'string')
    ? value as string[]
    : undefined

const escapeRegExp = (value: string): string =>
  value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

const normalizeTaskText = (value: string): string =>
  value.normalize('NFKC').replace(/\s+/g, ' ').trim()

const normalizedPath = (value: string): string => {
  const full = resolve(value)
  return process.platform === 'win32' ? full.toLowerCase() : full
}

const samePath = (left: string, right: string): boolean =>
  normalizedPath(left) === normalizedPath(right)

const sha256 = (value: string): string =>
  createHash('sha256').update(value).digest('hex')

const registeredChipIds = (rootPath: string): string[] => {
  const result = new Set<string>()
  const registryPath = resolve(rootPath, ATP_IP_SOURCE_REGISTRY)
  if (existsSync(registryPath)) {
    const lines = readFileSync(registryPath, 'utf8').split(/\r?\n/)
    let inChips = false
    for (const line of lines) {
      if (!inChips) {
        if (line.trim() === 'chips:' && !/^\s/.test(line)) inChips = true
        continue
      }
      if (line.trim() && !/^\s/.test(line)) break
      const match = /^ {2}([A-Za-z0-9][A-Za-z0-9_-]*):\s*$/.exec(line)
      if (match) result.add(match[1].toLowerCase())
    }
  }

  const chipRoot = resolve(rootPath, 'firmware/chips')
  if (existsSync(chipRoot)) {
    for (const entry of readdirSync(chipRoot, { withFileTypes: true })) {
      if (entry.isDirectory() && !entry.name.startsWith('_')) {
        result.add(entry.name.toLowerCase())
      }
    }
  }
  return [...result].sort((left, right) =>
    right.length - left.length || left.localeCompare(right),
  )
}

const chipAliases = (chipId: string): string[] => {
  const aliases = [chipId]
  if (/^et\d/i.test(chipId)) aliases.push(chipId.slice(2))
  return aliases
}

const resolveChipId = (
  taskText: string,
  chipIds: readonly string[],
): string | undefined => {
  const lower = taskText.toLowerCase()

  for (const chipId of chipIds) {
    const direct = new RegExp(
      `(?:^|[^a-z0-9])${escapeRegExp(chipId)}(?=$|[^a-z0-9])`,
      'i',
    )
    if (direct.test(lower)) return chipId
  }

  for (const chipId of chipIds) {
    for (const alias of chipAliases(chipId)) {
      const escaped = escapeRegExp(alias)
      const chineseBefore = new RegExp(
        `(?:^|[^a-z0-9])${escaped}\\s*芯片`,
        'i',
      )
      const englishBefore = new RegExp(
        `(?:^|[^a-z0-9])${escaped}\\s*(?:chip|soc)(?=$|[^a-z0-9])`,
        'i',
      )
      const chineseAfter = new RegExp(
        `芯片\\s*${escaped}(?=$|[^a-z0-9])`,
        'i',
      )
      const englishAfter = new RegExp(
        `(?:chip|soc)\\s*${escaped}(?=$|[^a-z0-9])`,
        'i',
      )
      if (
        chineseBefore.test(lower)
        || englishBefore.test(lower)
        || chineseAfter.test(lower)
        || englishAfter.test(lower)
      ) {
        return chipId
      }
    }
  }
  return undefined
}

const resolveIpId = (
  taskText: string,
  chipIds: readonly string[],
): string | undefined => {
  const lower = taskText.toLowerCase()
  const chipNames = new Set(
    chipIds.flatMap(chipId => chipAliases(chipId)).map(value => value.toLowerCase()),
  )
  const acceptable = (candidate: string): string | undefined => {
    const normalized = candidate.toLowerCase()
    if (!IDENTIFIER_RE.test(normalized)) return undefined
    if (IP_STOP_WORDS.has(normalized) || chipNames.has(normalized)) return undefined
    return normalized
  }

  const after = /(?:^|[^a-z0-9])ip\s*(?:[:=\-]|of)?\s*([a-z][a-z0-9_-]{0,63})/gi
  for (const match of lower.matchAll(after)) {
    const candidate = acceptable(match[1])
    if (candidate) return candidate
  }

  const candidates: string[] = []
  const before = /([a-z][a-z0-9_-]{0,63})(?:这个|的)?\s*ip(?=$|[^a-z0-9])/gi
  for (const match of lower.matchAll(before)) {
    const candidate = acceptable(match[1])
    if (candidate) candidates.push(candidate)
  }
  return candidates.at(-1)
}

export const looksLikeAutomatedTestingPlatformIpAnalysis = (
  rawTask: string,
): boolean => {
  const normalized = normalizeTaskText(rawTask)
  return IP_ANALYSIS_MARKER_RE.test(normalized) && IP_MARKER_RE.test(normalized)
}

export function classifyAutomatedTestingPlatformTask(
  rawTask: string,
  rootPath: string = findAutomatedTestingPlatformRoot(),
): AtpIpAnalysisTask | undefined {
  const normalized = normalizeTaskText(rawTask)
  if (!looksLikeAutomatedTestingPlatformIpAnalysis(normalized)) return undefined

  const chipIds = registeredChipIds(rootPath)
  if (chipIds.length === 0) {
    throw new Error('ATP IP analysis cannot resolve a chip because the project source registry is empty')
  }
  const chip = resolveChipId(normalized, chipIds)
  if (!chip) {
    throw new Error('ATP IP analysis task did not resolve one registered chip; fail closed instead of guessing')
  }
  const ip = resolveIpId(normalized, chipIds)
  if (!ip) {
    throw new Error('ATP IP analysis task did not resolve one IP identifier; fail closed instead of guessing')
  }
  return {
    kind: 'ip-analysis',
    module: 'ip-package',
    change: 'analysis',
    chip,
    chipUpper: chip.toUpperCase(),
    ip,
  }
}

const outputPathFor = (
  rootPath: string,
  outputPath: string | undefined,
): string => outputPath
  ? (isAbsolute(outputPath) ? resolve(outputPath) : resolve(rootPath, outputPath))
  : resolve(rootPath, ATP_TASK_CONTEXT_RELATIVE_PATH)

interface PythonCandidate {
  readonly command: string
  readonly prefix: readonly string[]
}

const pythonCandidates = (preferred?: string): PythonCandidate[] => {
  const candidates: PythonCandidate[] = []
  const append = (command: string | undefined, prefix: readonly string[] = []) => {
    const normalized = command?.trim()
    if (!normalized) return
    if (!candidates.some(item =>
      item.command === normalized && item.prefix.join('\0') === prefix.join('\0'),
    )) {
      candidates.push({ command: normalized, prefix })
    }
  }
  append(preferred)
  append(process.env.PYTHON)
  append('python')
  append('python3')
  if (process.platform === 'win32') append('py', ['-3'])
  return candidates
}

const runCompiler = (
  rootPath: string,
  arguments_: readonly string[],
  preferredPython?: string,
): void => {
  const compiler = resolve(rootPath, ATP_TASK_CONTEXT_COMPILER)
  if (!existsSync(compiler)) {
    throw new Error(`ATP Task Context compiler is missing: ${ATP_TASK_CONTEXT_COMPILER}`)
  }

  const unavailable: string[] = []
  for (const candidate of pythonCandidates(preferredPython)) {
    const result = spawnSync(
      candidate.command,
      [...candidate.prefix, compiler, ...arguments_],
      {
        cwd: rootPath,
        encoding: 'utf8',
        windowsHide: true,
      },
    )
    if (result.error) {
      const error = result.error as NodeJS.ErrnoException
      if (error.code === 'ENOENT') {
        unavailable.push(candidate.command)
        continue
      }
      throw new Error(`ATP Task Context compiler could not start: ${error.message}`)
    }
    if (result.status !== 0) {
      const detail = [result.stderr, result.stdout]
        .filter((value): value is string => typeof value === 'string' && Boolean(value.trim()))
        .join('\n')
        .trim()
      throw new Error(
        `ATP Task Context compiler failed with exit ${result.status}${detail ? `: ${detail}` : ''}`,
      )
    }
    return
  }
  throw new Error(
    `ATP Task Context compiler requires Python; unavailable launchers: ${unavailable.join(', ')}`,
  )
}

const assertCompiledTaskContext = (
  payload: unknown,
  request: ProjectContextContributionRequestV01,
  task: AtpIpAnalysisTask,
): AtpCompiledTaskContext => {
  const context = recordOf(payload)
  if (!context || context.schema !== 'et.task-context.v1') {
    throw new Error('ATP compiler returned an unsupported Task Context schema')
  }
  const compiledTask = recordOf(context.task)
  const modules = stringArray(compiledTask?.modules)
  const changes = stringArray(compiledTask?.changes)
  const lanes = stringArray(compiledTask?.lanes)
  if (
    !compiledTask
    || stringValue(compiledTask.id) !== request.taskId
    || stringValue(compiledTask.intent) !== request.rawTask
    || !modules?.includes(task.module)
    || !changes?.includes(task.change)
    || !lanes
    || stringValue(compiledTask.chip) !== task.chip
    || stringValue(compiledTask.ip) !== task.ip
  ) {
    throw new Error('ATP compiler result does not match the governed request and resolved IP analysis task')
  }
  if (!stringValue(context.fingerprint) || !stringValue(context.integrity_fingerprint)) {
    throw new Error('ATP compiler result has no stable fingerprint and integrity fingerprint')
  }

  const mustRead = context.must_read
  const ruleOwners = context.rule_owners
  const sourceInputs = context.source_inputs
  const architecture = context.architecture
  const writeScope = recordOf(context.write_scope)
  const allowed = stringArray(writeScope?.allowed)
  const protected_ = stringArray(writeScope?.protected)
  const validation = stringArray(context.validation)
  if (
    !Array.isArray(mustRead)
    || !Array.isArray(ruleOwners)
    || !Array.isArray(sourceInputs)
    || !Array.isArray(architecture)
    || !allowed
    || !protected_
    || !validation
  ) {
    throw new Error('ATP compiler result is missing navigation, scope or validation fields')
  }
  if (mustRead.some(item => {
    const record = recordOf(item)
    return !record
      || !stringValue(record.path)
      || !stringValue(record.reason)
      || typeof record.required !== 'boolean'
      || typeof record.exists !== 'boolean'
      || (record.required && !record.exists)
  })) {
    throw new Error('ATP compiler result contains an invalid or missing required must_read item')
  }
  if (ruleOwners.some(item => {
    const record = recordOf(item)
    return !record
      || !stringValue(record.owner_id)
      || !stringValue(record.rule_id)
      || !stringValue(record.source)
      || !stringValue(record.heading)
  })) {
    throw new Error('ATP compiler result contains an invalid Rule Owner entry')
  }
  if (!allowed.includes(`test_case_doc/${task.ip}/**`)) {
    throw new Error('ATP compiler result did not authorize the project-owned IP analysis output scope')
  }

  return payload as AtpCompiledTaskContext
}

const readCompiledTaskContext = (
  outputPath: string,
  request: ProjectContextContributionRequestV01,
  task: AtpIpAnalysisTask,
): AtpCompiledTaskContext => {
  let payload: unknown
  try {
    payload = JSON.parse(readFileSync(outputPath, 'utf8'))
  } catch (error) {
    throw new Error(
      `ATP Task Context output cannot be read: ${error instanceof Error ? error.message : String(error)}`,
    )
  }
  return assertCompiledTaskContext(payload, request, task)
}

export function compileAtpTaskContext(
  rootPath: string,
  request: ProjectContextContributionRequestV01,
  task: AtpIpAnalysisTask,
  options: CompileAtpTaskContextOptions = {},
): AtpCompiledTaskContext {
  const outputPath = outputPathFor(rootPath, options.outputPath)
  runCompiler(rootPath, [
    'compile',
    '--task-id', request.taskId,
    '--intent', request.rawTask,
    '--module', task.module,
    '--change', task.change,
    '--chip', task.chip,
    '--ip', task.ip,
    '--output', outputPath,
  ], options.pythonCommand)
  return readCompiledTaskContext(outputPath, request, task)
}

export function loadCurrentAtpTaskContext(
  rootPath: string,
  request: ProjectContextContributionRequestV01,
  task: AtpIpAnalysisTask,
  options: CompileAtpTaskContextOptions = {},
): AtpCompiledTaskContext {
  const outputPath = outputPathFor(rootPath, options.outputPath)
  if (!existsSync(outputPath)) {
    throw new Error('ATP implementation-phase routing has no persisted Task Context; compile the analysis route first')
  }
  runCompiler(rootPath, [
    'check',
    '--context', outputPath,
  ], options.pythonCommand)
  return readCompiledTaskContext(outputPath, request, task)
}

const compiledCoreContent = (
  compiled: AtpCompiledTaskContext,
): string => JSON.stringify({
  schema: compiled.schema,
  fingerprint: compiled.fingerprint,
  integrity_fingerprint: compiled.integrity_fingerprint,
  generated_at: compiled.generated_at,
  task: compiled.task,
  repository: compiled.repository,
  architecture: compiled.architecture,
  source_inputs: compiled.source_inputs,
})

const compiledNavigationContent = (
  compiled: AtpCompiledTaskContext,
): string => JSON.stringify({
  must_read: compiled.must_read,
  rule_owners: compiled.rule_owners,
})

const validationObligations = (
  compiled: AtpCompiledTaskContext,
): NonNullable<ProjectContextContributionV01['validation']> => [
  {
    id: 'task-context-current',
    summary: 'Confirm that the persisted ATP Task Context still matches its project inputs and exact repository identity.',
    command: `python ${ATP_TASK_CONTEXT_COMPILER} check --context ${ATP_TASK_CONTEXT_RELATIVE_PATH}`,
  },
  {
    id: 'task-write-scope',
    summary: 'Before project validation, check all task changes against the compiled allowed and protected scopes.',
    command: `python ${ATP_TASK_CONTEXT_COMPILER} scope-check --context ${ATP_TASK_CONTEXT_RELATIVE_PATH}`,
  },
  ...compiled.validation.map((command, index) => ({
    id: `project-validation-${String(index + 1).padStart(2, '0')}`,
    summary: 'Run the project-owned validation command exactly as compiled for this task.',
    command,
  })),
]

const supervisionPathPrefix = (value: string): string =>
  value.replaceAll('\\', '/').replace(/\/\*\*$/, '').replace(/\/$/, '')

const structuredSupervision = (
  compiled: AtpCompiledTaskContext,
): NonNullable<ProjectContextContributionV01['supervision']> => {
  const requiredReads: ObligationDefinitionV01[] = compiled.must_read
    .filter(item => item.required)
    .map((item, index) => ({
      id: `OBL-ATP-READ-${String(index + 1).padStart(3, '0')}`,
      kind: 'REQUIRED_RESOURCE',
      severity: 'MUST',
      sourceRefs: compiled.rule_owners.map(owner => owner.rule_id),
      target: { resourceId: item.path.replaceAll('\\', '/') },
      satisfaction: {
        acceptedProviderIds: ['codex-host-adapter'],
        acceptedDispositions: ['FOUND'],
      },
    }))
  const validations = validationObligations(compiled)
  const validationDefinitions: ObligationDefinitionV01[] = validations.map(item => ({
    id: `OBL-ATP-VALIDATION-${item.id.toUpperCase()}`,
    kind: 'VALIDATION',
    severity: 'MUST',
    sourceRefs: compiled.rule_owners.map(owner => owner.rule_id),
    target: { validationId: item.id, targetIdentity: `validation:${item.id}` },
    satisfaction: { requiredResultStatus: 'PASS' },
  }))
  const evidencePolicies: EvidencePolicyV01[] = validations.map(item => ({
    id: `POLICY-ATP-VALIDATION-${item.id.toUpperCase()}`,
    obligationIds: [`OBL-ATP-VALIDATION-${item.id.toUpperCase()}`],
    acceptedProviderIds: ['codex-host-adapter'],
    acceptedProviderKinds: ['HOST_ADAPTER'],
    acceptedResultStatuses: ['PASS'],
    requireExactContextHash: true,
    requireExactProjectRevision: false,
    requireExactTargetIdentity: true,
  }))
  const repository = recordOf(compiled.repository)
  const projectRevision = stringValue(repository?.head)

  return {
    schema: PROJECT_SUPERVISION_CONTRIBUTION_SCHEMA,
    ...(projectRevision ? { projectRevision } : {}),
    obligations: [
      ...requiredReads,
      {
        id: 'OBL-ATP-WRITE-SCOPE',
        kind: 'WRITE_SCOPE',
        severity: 'MUST',
        sourceRefs: compiled.rule_owners.map(owner => owner.rule_id),
        target: {
          allowedResourceIds: [],
          allowedPathPrefixes: compiled.write_scope.allowed.map(supervisionPathPrefix),
        },
        satisfaction: { requireInScope: true },
      },
      ...validationDefinitions,
    ],
    evidencePolicies,
    completionPolicy: {
      requireAllMustSatisfied: true,
      requireNoViolations: true,
      requireReflection: true,
      requireKnowledgeDecision: true,
      requireContextUpdate: true,
      requireClosureReceipt: true,
      allowShouldWarnings: true,
      requiredClosureModuleIds: [...MANDATORY_LIFECYCLE_CLOSURE_MODULE_IDS],
    },
  }
}

const externalSourceContract = (
  task: AtpIpAnalysisTask,
): string => [
  `registry: ${ATP_IP_SOURCE_REGISTRY}`,
  `task_chip: ${task.chip}`,
  `task_ip: ${task.ip}`,
  'For every applicable registered source item, the Host/Agent response MUST preserve:',
  '- provider',
  '- locator and stable item_id',
  '- title or path',
  '- status: FOUND | NO_MATCH | UNAVAILABLE',
  '- purpose and supported claim_refs',
  '- retrieved_at and revision_or_modified_at when available',
  '- content_hash when content was read',
  '- error when unavailable',
  'Connector access is semantic-governance evidence only; it must not be claimed as mechanical Tool Gateway enforcement.',
].join('\n')

export function buildAtpIpAnalysisContribution(
  rootPath: string,
  request: ProjectContextContributionRequestV01,
  task: AtpIpAnalysisTask,
  compiled: AtpCompiledTaskContext,
): ProjectContextContributionV01 {
  assertCompiledTaskContext(compiled, request, task)
  const publicDocument = `test_case_doc/${task.ip}/${task.ip}.md`
  const chipDocument = `test_case_doc/${task.ip}/${task.chipUpper}_${task.ip}.md`
  const contributionId = `atp-${compiled.fingerprint.slice(0, 20)}`
  const provenance = [
    `provider://${ATP_CONTEXT_CONTRIBUTOR_PROVIDER_ID}`,
    `compiler=${ATP_TASK_CONTEXT_COMPILER}`,
    `fingerprint=${compiled.fingerprint}`,
    `integrity=${compiled.integrity_fingerprint}`,
  ].join(';')
  const ownerSources = compiled.rule_owners.map(owner => owner.source)

  return {
    schema: PROJECT_CONTEXT_CONTRIBUTION_SCHEMA,
    projectId: request.projectId,
    taskId: request.taskId,
    contributionId,
    provenance,
    references: [
      { kind: 'architecture', id: 'A010.010.020', priority: 'required' },
      { kind: 'architecture', id: 'A010.020.010', priority: 'required' },
      { kind: 'rule', id: 'R010.010.010', priority: 'required' },
      { kind: 'rule', id: 'R010.010.020', priority: 'required' },
      { kind: 'rule', id: 'R010.010.030', priority: 'required' },
      { kind: 'rule', id: 'R010.020.020', priority: 'required' },
      { kind: 'rule', id: 'R010.020.030', priority: 'required' },
      { kind: 'rule', id: 'R010.050.030', priority: 'required' },
      { kind: 'rule', id: 'R020.010', priority: 'required' },
      { kind: 'rule', id: 'R020.020', priority: 'required' },
      { kind: 'rule', id: 'R020.030', priority: 'required' },
      { kind: 'rule', id: 'R020.040', priority: 'required' },
      { kind: 'knowledge', id: 'K001.001', priority: 'high' },
      { kind: 'knowledge', id: 'K001.002', priority: 'high' },
      { kind: 'knowledge', id: 'K001.003', priority: 'required' },
      { kind: 'knowledge', id: 'K001.004', priority: 'required' },
      { kind: 'knowledge', id: 'K001.005', priority: 'required' },
      { kind: 'knowledge', id: 'K001.008', priority: 'required' },
      { kind: 'knowledge', id: 'K001.012', priority: 'high' },
      { kind: 'gate', id: 'G010.010.010', priority: 'required' },
      { kind: 'gate', id: 'G010.010.020', priority: 'required' },
      { kind: 'gate', id: 'G010.010.030', priority: 'required' },
    ],
    inlineItems: [
      {
        id: 'compiled-task-context-core',
        title: 'ATP Compiled Task Context Identity',
        content: compiledCoreContent(compiled),
        priority: 'required',
        provenance,
      },
      {
        id: 'compiled-task-context-navigation',
        title: 'ATP Must-Read And Active Rule Owners',
        content: compiledNavigationContent(compiled),
        priority: 'required',
        provenance,
      },
      {
        id: 'external-source-disposition-contract',
        title: 'ATP External Source Disposition Contract',
        content: externalSourceContract(task),
        priority: 'required',
        provenance: `project://${ATP_PROJECT_ID}/${ATP_IP_SOURCE_REGISTRY}`,
      },
    ],
    readScope: [
      ...compiled.must_read.map(item => item.path),
      ATP_TASK_CONTEXT_RELATIVE_PATH,
      `source://project/${ATP_PROJECT_ID}/ip-analysis/${task.chip}/${task.ip}`,
    ],
    writeScope: {
      allowed: compiled.write_scope.allowed,
      protected: compiled.write_scope.protected,
    },
    validation: validationObligations(compiled),
    outputContract: {
      id: 'atp-ip-analysis-documents',
      title: 'ATP IP Analysis Project Output Contract',
      content: [
        'Create exactly the project-owned analysis artifacts required by the compiled scope:',
        `- ${publicDocument}`,
        `- ${chipDocument}`,
        'The public document must keep stable public IP semantics separate from chip facts.',
        `The chip document must contain ${task.chipUpper} source dispositions, register/IRQ/driver/test facts, mappings, conflicts, unknowns and unblock conditions.`,
        'Required sections and machine-readable blocks are owned by the current active Rule Owners, not by this Provider.',
        ...ownerSources.map(source => `- owner: ${source}`),
        'Do not modify PC, firmware, SDK, capability or hardware execution paths in this analysis task.',
        'Never report unexecuted software, Keil, FPGA, SIL, HIL or hardware validation as PASS.',
      ].join('\n'),
    },
    supervision: structuredSupervision(compiled),
  }
}

export class AtpContextContributorService extends Service {
  constructor(ctx: Context) {
    super(ctx, ATP_CONTEXT_CONTRIBUTOR_SERVICE)
  }

  contributeContext(
    request: ProjectContextContributionRequestV01,
  ): ProjectContextContributionProviderResult {
    if (request.schema !== PROJECT_CONTEXT_CONTRIBUTION_REQUEST_SCHEMA) {
      throw new Error(`ATP Context Contributor does not support request schema ${request.schema}`)
    }
    if (request.projectId !== ATP_PROJECT_ID) {
      throw new Error(`ATP Context Contributor project mismatch: ${request.projectId}`)
    }
    const rootPath = findAutomatedTestingPlatformRoot(request.workspacePath)
    if (!samePath(rootPath, request.workspacePath)) {
      throw new Error('ATP Context Contributor workspacePath is not the resolved project root')
    }
    const task = classifyAutomatedTestingPlatformTask(request.rawTask, rootPath)
    if (!task) {
      return {
        applicable: false,
        reason: 'The request is not an ATP IP-analysis task.',
      }
    }

    const compiled = request.phase === 'analysis'
      ? compileAtpTaskContext(rootPath, request, task)
      : loadCurrentAtpTaskContext(rootPath, request, task)
    return {
      applicable: true,
      contribution: buildAtpIpAnalysisContribution(rootPath, request, task, compiled),
    }
  }
}

declare module '@deepseek-ai/cordis' {
  interface Context {
    atpContextContributor: AtpContextContributorService
  }
}

export default AtpContextContributorService
