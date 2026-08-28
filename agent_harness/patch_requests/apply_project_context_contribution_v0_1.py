#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_once(relative: str, old: str, new: str) -> None:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{relative}: expected one replacement, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def require_contains(relative: str, value: str) -> None:
    path = ROOT / relative
    if value not in path.read_text(encoding="utf-8"):
        raise SystemExit(f"{relative}: expected marker missing: {value}")


# ---------------------------------------------------------------------------
# governance_core: one optional, provider-neutral capability contract.
# ---------------------------------------------------------------------------
replace_once(
    "agent_harness/governance_core/src/contracts.ts",
    """  {
    id: 'context.manage',
    version: '0.1',
    summary: '管理 Bootstrap、Task/Progress Ledger、Working Set、Recent Tail、Handles、Rebuild 与 Handoff 生命周期',
    criticality: 'core',
  },
  {
    id: 'experience.manage',
""",
    """  {
    id: 'context.manage',
    version: '0.1',
    summary: '管理 Bootstrap、Task/Progress Ledger、Working Set、Recent Tail、Handles、Rebuild 与 Handoff 生命周期',
    criticality: 'core',
  },
  {
    id: 'context.contribute',
    version: '0.1',
    summary: '允许项目通过可选 Provider 在初始 A/R/K/G 路由后贡献任务特定 Context、Scope、Validation 与 Output Contract；未声明 Provider 的项目保持原行为',
    criticality: 'optional',
    inputSchema: 'agent-harness.project-context-contribution-request.v0.1',
    outputSchema: 'agent-harness.project-context-contribution.v0.1',
  },
  {
    id: 'experience.manage',
""",
)

# ---------------------------------------------------------------------------
# context_builder contracts: persist provider-contributed inline items.
# ---------------------------------------------------------------------------
replace_once(
    "agent_harness/public_plugins/context_builder/src/contracts.ts",
    """  readonly workingSet: readonly ContextReference[]
  readonly handles: readonly ContextHandle[]
  readonly recentTail: readonly ContextRecentEvent[]
}
""",
    """  readonly workingSet: readonly ContextReference[]
  readonly inlineItems: readonly InlineContextItem[]
  readonly handles: readonly ContextHandle[]
  readonly recentTail: readonly ContextRecentEvent[]
}
""",
)
replace_once(
    "agent_harness/public_plugins/context_builder/src/contracts.ts",
    """  readonly goal: string
  readonly maxChars?: number
  readonly recentTailLimit?: number
}
""",
    """  readonly goal: string
  readonly maxChars?: number
  readonly recentTailLimit?: number
  readonly inlineItems?: readonly InlineContextItem[]
}
""",
)
replace_once(
    "agent_harness/public_plugins/context_builder/src/contracts.ts",
    """  readonly phase?: ContextLifecyclePhase
  readonly workingSet?: readonly ContextReference[]
  readonly clearRecentTail?: boolean
""",
    """  readonly phase?: ContextLifecyclePhase
  readonly workingSet?: readonly ContextReference[]
  readonly inlineItems?: readonly InlineContextItem[]
  readonly clearRecentTail?: boolean
""",
)
replace_once(
    "agent_harness/public_plugins/context_builder/src/contracts.ts",
    """  readonly progressLedger: ContextProgressLedger
  readonly workingSet: readonly ContextReference[]
  readonly handles: readonly ContextHandle[]
}
""",
    """  readonly progressLedger: ContextProgressLedger
  readonly workingSet: readonly ContextReference[]
  readonly inlineItems: readonly InlineContextItem[]
  readonly handles: readonly ContextHandle[]
}
""",
)

# ---------------------------------------------------------------------------
# context lint: validate dynamic inline context without banning multiline body.
# ---------------------------------------------------------------------------
replace_once(
    "agent_harness/public_plugins/context_builder/src/context-lint.ts",
    """  ContextHandleInput,
  ContextLedgerEntry,
""",
    """  ContextHandleInput,
  InlineContextItem,
  ContextLedgerEntry,
""",
)
replace_once(
    "agent_harness/public_plugins/context_builder/src/context-lint.ts",
    """  handleSummary: 220,
  reference: 500,
} as const
""",
    """  handleSummary: 220,
  inlineId: 160,
  inlineTitle: 240,
  inlineContent: 8_000,
  reference: 500,
} as const
""",
)
replace_once(
    "agent_harness/public_plugins/context_builder/src/context-lint.ts",
    """const STABLE_REFERENCE_RE = /^(?:[ARKG]\\d{3}(?:\\.\\d{3})*|(?:knowledge|source|evidence|project|file|runtime):\\/\\/\\S+)$/i
""",
    """const STABLE_REFERENCE_RE = /^(?:[ARKG]\\d{3}(?:\\.\\d{3})*|(?:knowledge|source|evidence|project|file|runtime|provider):\\/\\/\\S+)$/i
""",
)
replace_once(
    "agent_harness/public_plugins/context_builder/src/context-lint.ts",
    """export function lintHandle(input: ContextHandleInput): ContextLintResult {
  const issues: ContextLintIssue[] = []
  lintReference(input.reference, 'handle.reference', issues)
  if (input.title !== undefined) lintSingleLine(input.title, 'handle.title', LIMITS.handleTitle, issues)
  if (input.summary !== undefined) lintSingleLine(input.summary, 'handle.summary', LIMITS.handleSummary, issues)
  return toResult(issues)
}

export function lintContextSession(session: ContextSession): ContextLintResult {
""",
    """export function lintHandle(input: ContextHandleInput): ContextLintResult {
  const issues: ContextLintIssue[] = []
  lintReference(input.reference, 'handle.reference', issues)
  if (input.title !== undefined) lintSingleLine(input.title, 'handle.title', LIMITS.handleTitle, issues)
  if (input.summary !== undefined) lintSingleLine(input.summary, 'handle.summary', LIMITS.handleSummary, issues)
  return toResult(issues)
}

export function lintInlineContextItem(input: InlineContextItem): ContextLintResult {
  const issues: ContextLintIssue[] = []
  lintSingleLine(input.id, 'inline.id', LIMITS.inlineId, issues)
  lintSingleLine(input.title, 'inline.title', LIMITS.inlineTitle, issues)
  lintReference(input.provenance, 'inline.provenance', issues)
  const content = input.content.trim()
  if (!content) issues.push(issue('ERROR', 'EMPTY_TEXT', 'inline.content', 'inline.content 不能为空'))
  if (content.length > LIMITS.inlineContent) {
    issues.push(issue('ERROR', 'TEXT_TOO_LONG', 'inline.content', `inline.content 超过 ${LIMITS.inlineContent} 字符上限`))
  }
  return toResult(issues)
}

export function lintContextSession(session: ContextSession): ContextLintResult {
""",
)
replace_once(
    "agent_harness/public_plugins/context_builder/src/context-lint.ts",
    """  session.handles.forEach((handle, index) => {
    const result = lintHandle(handle)
    for (const item of [...result.errors, ...result.warnings]) {
      issues.push({ ...item, field: `handles[${index}].${item.field.replace(/^handle\\./, '')}` })
    }
  })
  return toResult(issues)
}
""",
    """  session.inlineItems.forEach((item, index) => {
    const result = lintInlineContextItem(item)
    for (const issueItem of [...result.errors, ...result.warnings]) {
      issues.push({ ...issueItem, field: `inlineItems[${index}].${issueItem.field.replace(/^inline\\./, '')}` })
    }
  })
  session.handles.forEach((handle, index) => {
    const result = lintHandle(handle)
    for (const item of [...result.errors, ...result.warnings]) {
      issues.push({ ...item, field: `handles[${index}].${item.field.replace(/^handle\\./, '')}` })
    }
  })
  return toResult(issues)
}
""",
)

# ---------------------------------------------------------------------------
# ContextManagementService: normalize, persist, hand off and rebuild inline items.
# ---------------------------------------------------------------------------
replace_once(
    "agent_harness/public_plugins/context_builder/src/context-management-service.ts",
    """  ContextHandleInput,
  ContextHandoff,
""",
    """  ContextHandleInput,
  ContextHandoff,
  InlineContextItem,
""",
)
replace_once(
    "agent_harness/public_plugins/context_builder/src/context-management-service.ts",
    """const MAX_HANDLES = 128
const MAX_LEDGER_ENTRIES = 64
""",
    """const MAX_HANDLES = 128
const MAX_INLINE_ITEMS = 24
const MAX_INLINE_ITEM_CHARS = 8_000
const MAX_INLINE_TOTAL_CHARS = 16_000
const RESERVED_INLINE_IDS = new Set([
  'context-compass',
  'task-ledger',
  'progress-ledger',
  'recent-tail',
  'available-handles',
])
const MAX_LEDGER_ENTRIES = 64
""",
)
replace_once(
    "agent_harness/public_plugins/context_builder/src/context-management-service.ts",
    """const normalizeHandles = (handles: readonly ContextHandleInput[]): ContextHandle[] => {
""",
    """export const normalizeInlineContextItems = (
  items: readonly InlineContextItem[] | undefined,
): InlineContextItem[] => {
  if (!items) return []
  if (items.length > MAX_INLINE_ITEMS) throw new Error(`Inline Context Items 超过上限 ${MAX_INLINE_ITEMS}`)
  const deduped = new Map<string, InlineContextItem>()
  let totalChars = 0
  for (const item of items) {
    const id = nonEmpty('Inline Context item id', item.id)
    if (!/^[A-Za-z0-9._:-]+$/.test(id)) throw new Error(`Inline Context item id 非法: ${id}`)
    if (RESERVED_INLINE_IDS.has(id)) throw new Error(`Inline Context item id 与 Runtime 保留项冲突: ${id}`)
    if (deduped.has(id)) throw new Error(`Inline Context item id 重复: ${id}`)
    const content = nonEmpty(`Inline Context ${id} content`, item.content)
    if (content.length > MAX_INLINE_ITEM_CHARS) {
      throw new Error(`Inline Context ${id} 超过 ${MAX_INLINE_ITEM_CHARS} 字符上限`)
    }
    totalChars += content.length
    if (totalChars > MAX_INLINE_TOTAL_CHARS) {
      throw new Error(`Inline Context 总内容超过 ${MAX_INLINE_TOTAL_CHARS} 字符上限`)
    }
    deduped.set(id, {
      id,
      title: nonEmpty(`Inline Context ${id} title`, item.title),
      content,
      priority: item.priority ?? 'high',
      provenance: nonEmpty(`Inline Context ${id} provenance`, item.provenance),
    })
  }
  return [...deduped.values()]
}

const normalizeHandles = (handles: readonly ContextHandleInput[]): ContextHandle[] => {
""",
)
replace_once(
    "agent_harness/public_plugins/context_builder/src/context-management-service.ts",
    """    && Array.isArray(item.workingSet)
    && Array.isArray(item.handles)
""",
    """    && Array.isArray(item.workingSet)
    && (item.inlineItems === undefined || Array.isArray(item.inlineItems))
    && Array.isArray(item.handles)
""",
)
replace_once(
    "agent_harness/public_plugins/context_builder/src/context-management-service.ts",
    """      workingSet: [],
      handles: [],
""",
    """      workingSet: [],
      inlineItems: normalizeInlineContextItems(input.inlineItems),
      handles: [],
""",
)
replace_once(
    "agent_harness/public_plugins/context_builder/src/context-management-service.ts",
    """    if (record.value.projectId !== projectId || record.value.taskId !== taskId) {
      throw new Error(`Context task 项目隔离失败: ${projectId}/${taskId}`)
    }
    return { stateVersion: record.version, session: record.value }
""",
    """    if (record.value.projectId !== projectId || record.value.taskId !== taskId) {
      throw new Error(`Context task 项目隔离失败: ${projectId}/${taskId}`)
    }
    const session: ContextSession = record.value.inlineItems === undefined
      ? { ...record.value, inlineItems: [] }
      : record.value
    return { stateVersion: record.version, session }
""",
)
replace_once(
    "agent_harness/public_plugins/context_builder/src/context-management-service.ts",
    """  addHandles(projectId: string, taskId: string, inputs: readonly ContextHandleInput[]): ContextSessionSnapshot {
""",
    """  replaceInlineItems(
    projectId: string,
    taskId: string,
    items: readonly InlineContextItem[],
  ): ContextSessionSnapshot {
    const snapshot = this.getTask(projectId, taskId)
    const inlineItems = normalizeInlineContextItems(items)
    return this.commit(
      snapshot,
      { ...snapshot.session, inlineItems, updatedAt: now() },
      `Replace ${inlineItems.length} Inline Context Item(s)`,
    )
  }

  attachInlineItems(
    projectId: string,
    taskId: string,
    items: readonly InlineContextItem[],
  ): ContextSessionSnapshot {
    const snapshot = this.getTask(projectId, taskId)
    const inlineItems = normalizeInlineContextItems([...snapshot.session.inlineItems, ...items])
    return this.commit(
      snapshot,
      { ...snapshot.session, inlineItems, updatedAt: now() },
      `Attach ${items.length} Inline Context Item(s)`,
    )
  }

  addHandles(projectId: string, taskId: string, inputs: readonly ContextHandleInput[]): ContextSessionSnapshot {
""",
)
replace_once(
    "agent_harness/public_plugins/context_builder/src/context-management-service.ts",
    """    const workingSet = input.workingSet !== undefined
      ? normalizeReferences(input.workingSet)
      : snapshot.session.workingSet
    const next: ContextSession = {
""",
    """    const workingSet = input.workingSet !== undefined
      ? normalizeReferences(input.workingSet)
      : snapshot.session.workingSet
    const inlineItems = input.inlineItems !== undefined
      ? normalizeInlineContextItems(input.inlineItems)
      : snapshot.session.inlineItems
    const next: ContextSession = {
""",
)
replace_once(
    "agent_harness/public_plugins/context_builder/src/context-management-service.ts",
    """      taskLedger,
      workingSet,
      recentTail: input.clearRecentTail === false ? snapshot.session.recentTail : [],
""",
    """      taskLedger,
      workingSet,
      inlineItems,
      recentTail: input.clearRecentTail === false ? snapshot.session.recentTail : [],
""",
)
replace_once(
    "agent_harness/public_plugins/context_builder/src/context-management-service.ts",
    """      progressLedger: session.progressLedger,
      workingSet: session.workingSet,
      handles: session.handles,
""",
    """      progressLedger: session.progressLedger,
      workingSet: session.workingSet,
      inlineItems: session.inlineItems,
      handles: session.handles,
""",
)
replace_once(
    "agent_harness/public_plugins/context_builder/src/context-management-service.ts",
    """        {
          id: 'progress-ledger',
          title: 'Progress Ledger',
          content: this.renderProgressLedger(session.progressLedger),
          priority: 'high',
          provenance: `runtime://${projectId}/context/${taskId}/progress-ledger`,
        },
        ...(session.recentTail.length > 0 ? [{
""",
    """        {
          id: 'progress-ledger',
          title: 'Progress Ledger',
          content: this.renderProgressLedger(session.progressLedger),
          priority: 'high',
          provenance: `runtime://${projectId}/context/${taskId}/progress-ledger`,
        },
        ...session.inlineItems,
        ...(session.recentTail.length > 0 ? [{
""",
)

# ---------------------------------------------------------------------------
# Auto Governance public contracts and runtime integration.
# ---------------------------------------------------------------------------
replace_once(
    "agent_harness/public_plugins/auto_governance_engine/src/contracts.ts",
    """export type AutoGovernanceReviewDecision = 'PENDING' | 'PASS' | 'BLOCK'
""",
    """export interface AutoGovernanceContextContributionReceipt {
  readonly providerId: string
  readonly contributionId: string
  readonly fingerprint: string
  readonly referenceIds: readonly string[]
  readonly inlineItemIds: readonly string[]
}

export type AutoGovernanceReviewDecision = 'PENDING' | 'PASS' | 'BLOCK'
""",
)
replace_once(
    "agent_harness/public_plugins/auto_governance_engine/src/contracts.ts",
    """  readonly route: AutoGovernanceRouteSnapshot
  readonly applicableGateIds: readonly string[]
  readonly pendingReviews: readonly AutoGovernancePendingReview[]
""",
    """  readonly route: AutoGovernanceRouteSnapshot
  readonly contextContributions: readonly AutoGovernanceContextContributionReceipt[]
  readonly applicableGateIds: readonly string[]
  readonly pendingReviews: readonly AutoGovernancePendingReview[]
""",
)
# The same structural block occurs twice (TaskStatus and ContextEnvelope).
replace_once(
    "agent_harness/public_plugins/auto_governance_engine/src/contracts.ts",
    """  readonly route: AutoGovernanceRouteSnapshot
  readonly applicableGateIds: readonly string[]
  readonly pendingReviews: readonly AutoGovernancePendingReview[]
""",
    """  readonly route: AutoGovernanceRouteSnapshot
  readonly contextContributions: readonly AutoGovernanceContextContributionReceipt[]
  readonly applicableGateIds: readonly string[]
  readonly pendingReviews: readonly AutoGovernancePendingReview[]
""",
)
replace_once(
    "agent_harness/public_plugins/auto_governance_engine/src/index.ts",
    """export * from './contracts.js'
export * from './service.js'
""",
    """export * from './contracts.js'
export * from './context-contribution.js'
export * from './route-resolver.js'
export * from './service.js'
""",
)
replace_once(
    "agent_harness/public_plugins/auto_governance_engine/src/index.ts",
    """    'context.build',
    'context.manage',
""",
    """    'context.build',
    'context.manage',
    'context.contribute',
""",
)
replace_once(
    "agent_harness/public_plugins/auto_governance_engine/src/service.ts",
    """  AutoGovernanceCompletionResult,
  AutoGovernanceContextEnvelope,
""",
    """  AutoGovernanceCompletionResult,
  AutoGovernanceContextContributionReceipt,
  AutoGovernanceContextEnvelope,
""",
)
replace_once(
    "agent_harness/public_plugins/auto_governance_engine/src/service.ts",
    """import {
  resolveGovernanceRouteGraph,
  type GovernanceRouteResourceKind,
} from './route-resolver.js'
""",
    """import {
  PROJECT_CONTEXT_CONTRIBUTION_CAPABILITY,
  PROJECT_CONTEXT_CONTRIBUTION_REQUEST_SCHEMA,
  contributionReceipt,
  mergeContributionInlineItems,
  mergeContributionReferences,
  resolveDeclaredProjectContextContributions,
  type NormalizedProjectContextContribution,
} from './context-contribution.js'
import {
  resolveGovernanceRouteGraph,
  type GovernanceRouteResourceKind,
} from './route-resolver.js'
""",
)
replace_once(
    "agent_harness/public_plugins/auto_governance_engine/src/service.ts",
    """  route: AutoGovernanceRouteSnapshot
  applicableGateIds: string[]
""",
    """  route: AutoGovernanceRouteSnapshot
  contextContributions: NormalizedProjectContextContribution[]
  applicableGateIds: string[]
""",
)
replace_once(
    "agent_harness/public_plugins/auto_governance_engine/src/service.ts",
    """const unique = (values: readonly string[]): string[] =>
  [...new Set(values.map(value => value.trim()).filter(Boolean))]

const normalizedPath = (value: string): string => {
""",
    """const unique = (values: readonly string[]): string[] =>
  [...new Set(values.map(value => value.trim()).filter(Boolean))]

const contributionReceipts = (
  contributions: readonly NormalizedProjectContextContribution[],
): AutoGovernanceContextContributionReceipt[] => contributions.map(contributionReceipt)

const mergeRouteReferences = (
  route: AutoGovernanceRouteSnapshot,
  references: readonly ContextReference[],
): AutoGovernanceRouteSnapshot => ({
  architectureIds: unique([
    ...route.architectureIds,
    ...references.filter(item => item.kind === 'architecture').map(item => item.id),
  ]),
  ruleIds: unique([
    ...route.ruleIds,
    ...references.filter(item => item.kind === 'rule').map(item => item.id),
  ]),
  knowledgeIds: unique([
    ...route.knowledgeIds,
    ...references.filter(item => item.kind === 'knowledge').map(item => item.id),
  ]),
  gateIds: unique([
    ...route.gateIds,
    ...references.filter(item => item.kind === 'gate').map(item => item.id),
  ]),
})

const normalizedPath = (value: string): string => {
""",
)
replace_once(
    "agent_harness/public_plugins/auto_governance_engine/src/service.ts",
    """      route: runtime.route,
      applicableGateIds: [...runtime.applicableGateIds],
""",
    """      route: runtime.route,
      contextContributions: contributionReceipts(runtime.contextContributions),
      applicableGateIds: [...runtime.applicableGateIds],
""",
)
# The same output fragment appears in both getTaskStatus and buildContextEnvelope.
replace_once(
    "agent_harness/public_plugins/auto_governance_engine/src/service.ts",
    """      route: runtime.route,
      applicableGateIds: [...runtime.applicableGateIds],
""",
    """      route: runtime.route,
      contextContributions: contributionReceipts(runtime.contextContributions),
      applicableGateIds: [...runtime.applicableGateIds],
""",
)
replace_once(
    "agent_harness/public_plugins/auto_governance_engine/src/service.ts",
    """      route: emptyRoute(),
      applicableGateIds: [],
""",
    """      route: emptyRoute(),
      contextContributions: [],
      applicableGateIds: [],
""",
)
replace_once(
    "agent_harness/public_plugins/auto_governance_engine/src/service.ts",
    """    const route: AutoGovernanceRouteSnapshot = {
      architectureIds: resolution.candidates.architecture.map(candidate => candidate.id),
      ruleIds: resolution.candidates.rule.map(candidate => candidate.id),
      knowledgeIds: resolution.candidates.knowledge.map(candidate => candidate.id),
      gateIds: resolution.candidates.gate.map(candidate => candidate.id),
    }
    const refs: ContextReference[] = [
""",
    """    let route: AutoGovernanceRouteSnapshot = {
      architectureIds: resolution.candidates.architecture.map(candidate => candidate.id),
      ruleIds: resolution.candidates.rule.map(candidate => candidate.id),
      knowledgeIds: resolution.candidates.knowledge.map(candidate => candidate.id),
      gateIds: resolution.candidates.gate.map(candidate => candidate.id),
    }
    const project = this.runtimeContext.projectManager.getProjectContext(runtime.projectId)
    if (!project) throw new Error(`Auto Governance project disappeared during routing: ${runtime.projectId}`)
    if (phase === 'analysis' || runtime.contextContributions.length === 0) {
      runtime.contextContributions = resolveDeclaredProjectContextContributions({
        project,
        request: {
          schema: PROJECT_CONTEXT_CONTRIBUTION_REQUEST_SCHEMA,
          projectId: runtime.projectId,
          taskId: runtime.taskId,
          rawTask: runtime.goal,
          phase,
          workspacePath: project.projectRoot,
          initialRoute: route,
        },
        providers: this.runtimeContext.governanceCatalog.listProviders(
          PROJECT_CONTEXT_CONTRIBUTION_CAPABILITY,
        ),
        serviceLookup: serviceName => this.dynamicContext().get(serviceName),
      })
    }
    const contributionReferences = mergeContributionReferences(runtime.contextContributions)
    for (const reference of contributionReferences) {
      const exists = reference.kind === 'architecture'
        ? this.runtimeContext.architectureNavigator.getNode(runtime.projectId, reference.id) !== undefined
        : reference.kind === 'rule'
          ? this.runtimeContext.ruleManager.getNode(runtime.projectId, reference.id) !== undefined
          : reference.kind === 'knowledge'
            ? this.runtimeContext.knowledgeManager.getNode(runtime.projectId, reference.id) !== undefined
            : this.runtimeContext.gateManager.getNode(runtime.projectId, reference.id) !== undefined
      if (!exists) {
        throw new Error(`Context contributor referenced missing ${reference.kind} resource: ${reference.id}`)
      }
    }
    route = mergeRouteReferences(route, contributionReferences)
    const refs: ContextReference[] = [
""",
)
replace_once(
    "agent_harness/public_plugins/auto_governance_engine/src/service.ts",
    """      ...route.gateIds.map(id => ({ kind: 'gate' as const, id, priority: 'high' as const })),
    ]
    if (replaceWorkingSet) {
""",
    """      ...route.gateIds.map(id => ({ kind: 'gate' as const, id, priority: 'high' as const })),
      ...contributionReferences,
    ]
    this.runtimeContext.contextManager.replaceInlineItems(
      runtime.projectId,
      runtime.taskId,
      mergeContributionInlineItems(runtime.contextContributions),
    )
    if (replaceWorkingSet) {
""",
)

# Ensure all expected public changes landed.
for relative, marker in [
    ("agent_harness/governance_core/src/contracts.ts", "id: 'context.contribute'"),
    ("agent_harness/public_plugins/context_builder/src/contracts.ts", "readonly inlineItems: readonly InlineContextItem[]"),
    ("agent_harness/public_plugins/context_builder/src/context-management-service.ts", "replaceInlineItems("),
    ("agent_harness/public_plugins/auto_governance_engine/src/index.ts", "./context-contribution.js"),
    ("agent_harness/public_plugins/auto_governance_engine/src/service.ts", "resolveDeclaredProjectContextContributions"),
]:
    require_contains(relative, marker)

print("Generic project context contribution patch applied.")
