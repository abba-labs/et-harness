import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { readFileSync, statSync } from 'node:fs'
import { resolve, sep } from 'node:path'
import { Service, type Context } from '@deepseek-ai/cordis'
import '@agent-harness/project-manager'
import type { ProjectCandidateResult, ProjectQueryRequest } from '@agent-harness/project-contract'
import {
  ET_TOOL_REVIEW_CAPABILITIES,
  type EtToolChangeScopeHints,
  type EtToolReviewCandidate,
  type EtToolReviewCapability,
  type EtToolReviewChangeInput,
  type EtToolReviewDecisionInput,
  type EtToolReviewDecisionResult,
  type EtToolReviewPacket,
  type EtToolReviewRequest,
  type EtToolValidationPlanHint,
} from './review-contracts.js'

const MAX_PATCH_CHARS = 120_000
const MAX_UNTRACKED_FILE_CHARS = 12_000
const MAX_UNTRACKED_TOTAL_CHARS = 30_000

const GUIDANCE: Readonly<Record<EtToolReviewCapability, readonly string[]>> = {
  'change.analyze': [
    'Compare the human task intent with the actual changed files and patch.',
    'Identify unrelated chip, route, feature, layer, configuration, release or test changes.',
    'If a shared layer changed, declare the direct and transitive blast radius before build/test.',
  ],
  'code.review': [
    'Review branches, state transitions, early returns, error paths and terminal outcomes.',
    'Check obvious syntax/API/type/null/uninitialized misuse without pretending to replace the compiler.',
    'Block logic that can continue side effects after failure, timeout or cancellation.',
  ],
  'architecture.review': [
    'Check that changed code stays in the architecture layer that owns the responsibility.',
    'Check chip-local and route-local independence; cross-chip implementation dependencies are blocking.',
    'Check that GUI/CLI/hardware actions do not bypass the formal product execution path.',
  ],
  'rule.review': [
    'Use the selected Rule candidates as hard constraints, not suggestions.',
    'Check every applicable MUST and MUST_NOT against the actual diff.',
    'Do not mark PASS when applicability is unclear; request a narrower scope or additional Rule context.',
  ],
  'lifecycle.review': [
    'Identify creator, owner and release path for every changed runtime resource.',
    'Trace cleanup across success, fail, timeout, cancel, disconnect, chip switch, back-home and application exit where applicable.',
    'Keep host resource cleanup separate from target MCU state recovery and close async/progress lifecycle.',
  ],
  'contract.review': [
    'Trace changed public/typed interfaces to callers and consumers.',
    'Check CLI args, Request/Result, Profile, Progress, release metadata and structured payload compatibility.',
    'Block silent schema or semantic changes that leave dependent callers unchanged.',
  ],
  'validation.plan': [
    'Produce the required post-Gate build/test/hardware validation scope only; do not execute it.',
    'Expand validation scope when shared layers or cross-route contracts changed.',
    'Keep no-hardware validation distinct from hardware evidence requirements.',
  ],
}

interface ProjectSearchService {
  searchArchitecture?(request: ProjectQueryRequest): readonly ProjectCandidateResult[]
  searchRules?(request: ProjectQueryRequest): readonly ProjectCandidateResult[]
  searchKnowledge?(request: ProjectQueryRequest): readonly ProjectCandidateResult[]
}

interface GateExecutionPlanLite {
  readonly gateId: string
  readonly steps: readonly {
    readonly id: string
    readonly tool: string
    readonly args?: Readonly<Record<string, unknown>>
  }[]
  readonly refs: readonly string[]
}

interface GateServiceLite {
  getExecutionPlan(projectId: string, gateId: string): GateExecutionPlanLite | undefined
}

interface EvidenceServiceLite {
  recordEvidence(input: {
    readonly projectId: string
    readonly taskId: string
    readonly kind: string
    readonly result: 'PASS' | 'FAIL' | 'INFO' | 'SKIP'
    readonly summary: string
    readonly source: string
    readonly gateId?: string
    readonly metadata?: Readonly<Record<string, unknown>>
  }): { readonly evidenceId: string }
}

export function classifyEtToolChangeScope(files: readonly string[]): EtToolChangeScopeHints {
  const chips = new Set<string>()
  const routes = new Set<string>()
  const layers = new Set<string>()
  const unknownPaths: string[] = []
  let sharedLayerChange = false

  for (const original of files) {
    const path = original.replaceAll('\\', '/').toLowerCase()
    let recognized = false

    for (const chip of ['et3101', 'et6002', 'et6003']) {
      if (path.includes(chip)) {
        chips.add(chip.toUpperCase())
        recognized = true
      }
    }

    if (path.includes('canfd')) {
      routes.add('CANFD')
      recognized = true
    } else if (/(^|[\/_-])can([\/_-]|$)/.test(path)) {
      routes.add('CAN')
      recognized = true
    }
    if (/(^|[\/_-])uart([\/_-]|$)/.test(path)) {
      routes.add('UART')
      recognized = true
    }
    if (path.includes('jlink') || path.includes('j-link')) {
      routes.add('J-LINK')
      recognized = true
    }
    if (path.includes('cmsis-dap') || path.includes('cmsis_dap') || /(^|\/)dap(\/|$)/.test(path)) {
      routes.add('CMSIS-DAP')
      recognized = true
    }

    const layerMatchers: readonly [string, RegExp][] = [
      ['GUI', /source\/apps\/gui/],
      ['CLI', /source\/apps\/cli/],
      ['APPLICATION', /source\/application/],
      ['WORKFLOW', /source\/workflow/],
      ['BACKEND', /source\/backend/],
      ['PROTOCOL', /source\/protocol/],
      ['TRANSPORT', /source\/transport/],
      ['PROBE', /source\/probe/],
      ['PLATFORM', /source\/platform/],
      ['PROFILE', /source\/profiles/],
      ['RELEASE', /source\/release/],
      ['AUTOMATION', /source\/automation/],
      ['TEST', /(^|\/)tests?\//],
      ['AGENT_HARNESS', /agent_harness\//],
    ]
    for (const [layer, matcher] of layerMatchers) {
      if (matcher.test(path)) {
        layers.add(layer)
        recognized = true
      }
    }

    const hasChip = ['et3101', 'et6002', 'et6003'].some(chip => path.includes(chip))
    const sharedPrefix = [
      'source/application/',
      'source/workflow/',
      'source/backend/',
      'source/protocol/',
      'source/transport/',
      'source/probe/',
      'source/platform/',
      'source/apps/gui/shared/',
      'source/apps/cli/shared/',
    ].some(prefix => path.startsWith(prefix))
    if (sharedPrefix && !hasChip) sharedLayerChange = true

    if (!recognized) unknownPaths.push(original)
  }

  return {
    chips: [...chips].sort(),
    routes: [...routes].sort(),
    layers: [...layers].sort(),
    sharedLayerChange,
    unknownPaths,
  }
}

export function reviewGuidanceFor(capability: EtToolReviewCapability): readonly string[] {
  return GUIDANCE[capability]
}

function sha256(value: string): string {
  return createHash('sha256').update(value).digest('hex')
}

function normalizeFiles(files: readonly string[]): string[] {
  return [...new Set(files.map(file => file.replaceAll('\\', '/').trim()).filter(Boolean))].sort()
}

function normalizeProvidedChange(change: EtToolReviewChangeInput) {
  const files = normalizeFiles(change.files)
  const patch = change.patch.slice(0, MAX_PATCH_CHARS)
  return {
    source: 'provided' as const,
    files,
    patch,
    truncated: change.patch.length > MAX_PATCH_CHARS,
    fingerprint: sha256(`${files.join('\n')}\n---PATCH---\n${change.patch}`),
  }
}

function runGit(root: string, args: readonly string[]): string {
  return execFileSync('git', ['-C', root, ...args], {
    encoding: 'utf8',
    maxBuffer: 4 * 1024 * 1024,
    windowsHide: true,
  })
}

function parseStatusFiles(status: string): { files: string[]; untracked: string[] } {
  const files: string[] = []
  const untracked: string[] = []
  for (const line of status.split(/\r?\n/)) {
    if (line.length < 4) continue
    const code = line.slice(0, 2)
    let path = line.slice(3).trim()
    if (path.includes(' -> ')) path = path.split(' -> ').at(-1) ?? path
    path = path.replace(/^"|"$/g, '')
    if (!path) continue
    files.push(path)
    if (code === '??') untracked.push(path)
  }
  return { files: normalizeFiles(files), untracked: normalizeFiles(untracked) }
}

function appendUntrackedPatch(root: string, files: readonly string[]): string {
  let total = 0
  let output = ''
  for (const file of files) {
    if (total >= MAX_UNTRACKED_TOTAL_CHARS) break
    const absolute = resolve(root, file)
    const rootPrefix = root.endsWith(sep) ? root : `${root}${sep}`
    if (absolute !== root && !absolute.startsWith(rootPrefix)) continue
    try {
      const stat = statSync(absolute)
      if (!stat.isFile()) continue
      const raw = readFileSync(absolute)
      if (raw.includes(0)) continue
      const text = raw.toString('utf8').slice(0, MAX_UNTRACKED_FILE_CHARS)
      const block = `\n--- /dev/null\n+++ b/${file}\n@@ untracked file @@\n${text}\n`
      const remaining = MAX_UNTRACKED_TOTAL_CHARS - total
      output += block.slice(0, remaining)
      total += Math.min(block.length, remaining)
    } catch {
      // A concurrently removed or unreadable untracked file stays represented by status only.
    }
  }
  return output
}

function collectGitWorkingTree(root: string) {
  const status = runGit(root, ['status', '--porcelain=v1', '--untracked-files=all'])
  const { files, untracked } = parseStatusFiles(status)
  const unstaged = runGit(root, ['diff', '--no-ext-diff', '--unified=3', '--', '.'])
  const staged = runGit(root, ['diff', '--cached', '--no-ext-diff', '--unified=3', '--', '.'])
  const untrackedPatch = appendUntrackedPatch(root, untracked)
  const fullPatch = [unstaged, staged, untrackedPatch].filter(Boolean).join('\n')
  const patch = fullPatch.slice(0, MAX_PATCH_CHARS)
  return {
    source: 'git-working-tree' as const,
    files,
    patch,
    truncated: fullPatch.length > MAX_PATCH_CHARS,
    fingerprint: sha256(`${files.join('\n')}\n---PATCH---\n${fullPatch}`),
  }
}

function summarizeCandidates(candidates: readonly ProjectCandidateResult[]): readonly EtToolReviewCandidate[] {
  return candidates.map(candidate => ({
    id: candidate.id,
    title: candidate.title,
    location: candidate.location,
    ...(candidate.summary ? { summary: candidate.summary } : {}),
    ...(candidate.relevance !== undefined ? { relevance: candidate.relevance } : {}),
  }))
}

function buildValidationPlanHints(scope: EtToolChangeScopeHints): readonly EtToolValidationPlanHint[] {
  const hints: EtToolValidationPlanHint[] = [
    {
      kind: 'build',
      scope: 'affected ET-TOOL target through formal source/release pipeline',
      reason: 'All Code Gates run before compilation; build begins only after Gate PASS.',
    },
  ]

  if (scope.sharedLayerChange) {
    hints.push({
      kind: 'regression',
      scope: 'all Chip × Route consumers of the changed shared layer',
      reason: 'Shared-layer change requires expanded regression scope.',
    })
  } else if (scope.chips.length || scope.routes.length) {
    hints.push({
      kind: 'regression',
      scope: `${scope.chips.join(', ') || 'affected chip'} × ${scope.routes.join(', ') || 'affected route'}`,
      reason: 'Local change requires focused regression plus isolation checks.',
    })
  }

  const hardwareRelevant = scope.layers.some(layer =>
    ['BACKEND', 'PROTOCOL', 'TRANSPORT', 'PROBE', 'PLATFORM', 'PROFILE'].includes(layer),
  )
  if (hardwareRelevant) {
    hints.push({
      kind: 'hardware',
      scope: 'matching Chip × Route × Capability when claiming hardware behavior',
      reason: 'Software/no-hardware PASS must not be promoted to hardware PASS.',
    })
  }
  return hints
}

function assertCapability(value: string): asserts value is EtToolReviewCapability {
  if (!(ET_TOOL_REVIEW_CAPABILITIES as readonly string[]).includes(value)) {
    throw new Error(`ET-TOOL Review Adapter 不支持 capability: ${value}`)
  }
}

export class EtToolCodeReviewAdapterService extends Service {
  private readonly runtimeContext: Context
  private readonly packets = new Map<string, EtToolReviewPacket>()

  constructor(ctx: Context) {
    super(ctx, 'etToolCodeReviewAdapter')
    this.runtimeContext = ctx
    ctx.effect(() => () => this.packets.clear())
  }

  prepareReview(input: EtToolReviewRequest): EtToolReviewPacket {
    if (input.projectId !== 'et-tool') throw new Error('ET-TOOL Review Adapter 只允许 projectId=et-tool')
    if (!input.taskId.trim()) throw new Error('taskId 不能为空')
    if (!input.gateId.trim()) throw new Error('gateId 不能为空')
    if (!input.taskIntent.trim()) throw new Error('taskIntent 不能为空')
    assertCapability(input.capability)

    const project = this.runtimeContext.projectManager.getProjectContext(input.projectId)
    if (!project) throw new Error('ET-TOOL Project 尚未注册')
    const gateService = this.requireService<GateServiceLite>('gateManager')
    const plan = gateService.getExecutionPlan(input.projectId, input.gateId)
    if (!plan) throw new Error(`不是可执行 Gate: ${input.gateId}`)
    const step = plan.steps.find(item => item.tool === input.capability)
    if (!step) {
      throw new Error(`${input.gateId} Execution Plan 不包含 capability ${input.capability}`)
    }

    const change = input.change
      ? normalizeProvidedChange(input.change)
      : collectGitWorkingTree(project.projectRoot)
    if (change.files.length === 0 && !change.patch.trim()) {
      throw new Error('当前没有可供 Code Gate 审查的代码变化')
    }

    const focusFromGate = typeof step.args?.focus === 'string' ? step.args.focus : ''
    const focus = (input.focus?.trim() || focusFromGate || input.capability).trim()
    const scopeHints = classifyEtToolChangeScope(change.files)
    const query = [
      input.taskIntent,
      focus,
      ...scopeHints.chips,
      ...scopeHints.routes,
      ...scopeHints.layers,
      ...change.files.slice(0, 12),
    ].join(' ').replace(/\s+/g, ' ').slice(0, 4000)
    const request: ProjectQueryRequest = {
      projectId: input.projectId,
      query,
      scope: { taskId: input.taskId, concern: focus },
    }

    const architectureService = this.requireService<ProjectSearchService>('architectureNavigator')
    const ruleService = this.requireService<ProjectSearchService>('ruleManager')
    const knowledgeService = this.requireService<ProjectSearchService>('knowledgeManager')
    const architectureCandidates = summarizeCandidates(
      architectureService.searchArchitecture?.({ ...request, limit: 8 }) ?? [],
    )
    const ruleCandidates = summarizeCandidates(
      ruleService.searchRules?.({ ...request, limit: 12 }) ?? [],
    )
    const knowledgeCandidates = summarizeCandidates(
      knowledgeService.searchKnowledge?.({ ...request, limit: 8 }) ?? [],
    )

    const fingerprintMaterial = JSON.stringify({
      taskId: input.taskId,
      gateId: input.gateId,
      capability: input.capability,
      taskIntent: input.taskIntent,
      reviewEpoch: input.reviewEpoch ?? 0,
      focus,
      changeFingerprint: change.fingerprint,
    })
    const packetId = `ETR-${sha256(fingerprintMaterial).slice(0, 16)}`
    const packet: EtToolReviewPacket = {
      packetId,
      projectId: input.projectId,
      taskId: input.taskId,
      gateId: input.gateId,
      capability: input.capability,
      focus,
      taskIntent: input.taskIntent,
      ...(input.reviewEpoch !== undefined ? { reviewEpoch: input.reviewEpoch } : {}),
      change,
      scopeHints,
      architectureCandidates,
      ruleCandidates,
      knowledgeCandidates,
      gateRefs: [...plan.refs],
      reviewGuidance: reviewGuidanceFor(input.capability),
      validationPlanHints: buildValidationPlanHints(scopeHints),
      decisionPolicy:
        'Adapter only prepares deterministic project context. The Agent/Human reviewer must inspect the patch and explicitly submit PASS or BLOCK; the Adapter never auto-promotes a packet to PASS.',
    }
    this.packets.set(packetId, packet)
    return packet
  }

  getReviewPacket(packetId: string): EtToolReviewPacket | undefined {
    return this.packets.get(packetId)
  }

  recordReviewDecision(input: EtToolReviewDecisionInput): EtToolReviewDecisionResult {
    const packet = this.packets.get(input.packetId)
    if (!packet) throw new Error(`Review Packet 不存在或已失效: ${input.packetId}`)
    if (!input.summary.trim()) throw new Error('review summary 不能为空')
    if (!input.reviewerId.trim()) throw new Error('reviewerId 不能为空')
    const findings = input.findings ?? []
    if (input.result === 'PASS' && findings.some(item => item.severity === 'BLOCK')) {
      throw new Error('存在 BLOCK finding 时禁止记录 PASS Evidence')
    }

    const evidenceService = this.requireService<EvidenceServiceLite>('evidenceStateManager')
    const evidence = evidenceService.recordEvidence({
      projectId: packet.projectId,
      taskId: packet.taskId,
      kind: 'gate',
      result: input.result === 'PASS' ? 'PASS' : 'FAIL',
      summary: input.summary.trim(),
      source: 'et-tool-code-review-adapter/explicit-review-decision',
      gateId: packet.gateId,
      metadata: {
        packetId: packet.packetId,
        capability: packet.capability,
        focus: packet.focus,
        changeFingerprint: packet.change.fingerprint,
        ...(packet.reviewEpoch !== undefined ? { reviewEpoch: packet.reviewEpoch } : {}),
        reviewer: input.reviewer,
        reviewerId: input.reviewerId,
        findings,
        architectureRefs: packet.architectureCandidates.map(item => item.id),
        ruleRefs: packet.ruleCandidates.map(item => item.id),
        knowledgeRefs: packet.knowledgeCandidates.map(item => item.id),
        gateRefs: packet.gateRefs,
      },
    })

    return {
      packetId: packet.packetId,
      gateId: packet.gateId,
      taskId: packet.taskId,
      result: input.result,
      evidenceId: evidence.evidenceId,
    }
  }

  private requireService<T>(name: string): T {
    const dynamicContext = this.runtimeContext as unknown as { get(serviceName: string): unknown }
    const service = dynamicContext.get(name) as T | undefined
    if (!service) throw new Error(`ET-TOOL Review Adapter 缺少运行时依赖 Service: ${name}`)
    return service
  }
}

declare module '@deepseek-ai/cordis' {
  interface Context {
    etToolCodeReviewAdapter: EtToolCodeReviewAdapterService
  }
}

export default EtToolCodeReviewAdapterService
