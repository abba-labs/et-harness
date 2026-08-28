#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_once(relative: str, old: str, new: str) -> None:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"{relative}: expected exactly one structural marker, found {count}: {old[:120]!r}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


CONTRIBUTION = "agent_harness/public_plugins/auto_governance_engine/src/context-contribution.ts"
SERVICE = "agent_harness/public_plugins/auto_governance_engine/src/service.ts"
TEST = "agent_harness/public_plugins/auto_governance_engine/tests/context-contribution.test.ts"

replace_once(
    CONTRIBUTION,
    """const safeProjectRelativePath = (label: string, value: unknown): string => {
  const normalized = singleLine(label, value, 1_000).replaceAll('\\\\', '/')
  const segments = normalized.split('/')
  if (isAbsolute(normalized) || normalized.startsWith('/') || segments.includes('..')) {
    throw new Error(`${label} must be a safe project-relative path or glob`)
  }
  return normalized
}
""",
    """const safeProjectRelativePath = (label: string, value: unknown): string => {
  const normalized = singleLine(label, value, 1_000).replaceAll('\\\\', '/')
  const segments = normalized.split('/')
  const windowsAbsolute = /^[A-Za-z]:\\//.test(normalized)
  const uriLike = /^[A-Za-z][A-Za-z0-9+.-]*:\\/\\//.test(normalized)
  if (isAbsolute(normalized) || windowsAbsolute || uriLike
    || normalized.startsWith('/') || normalized.startsWith('//')
    || segments.includes('..')) {
    throw new Error(`${label} must be a safe project-relative path or glob`)
  }
  return normalized
}
""",
)

replace_once(
    CONTRIBUTION,
    """export const mergeContributionReferences = (
  contributions: readonly NormalizedProjectContextContribution[],
): ContextReference[] => {
""",
    """export const replaceContributionInlineItems = (
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
""",
)

replace_once(
    SERVICE,
    """  contributionReceipt,
  mergeContributionInlineItems,
  mergeContributionReferences,
  resolveDeclaredProjectContextContributions,
""",
    """  contributionReceipt,
  mergeContributionReferences,
  replaceContributionInlineItems,
  resolveDeclaredProjectContextContributions,
""",
)

replace_once(
    SERVICE,
    """    if (phase === 'analysis' || runtime.contextContributions.length === 0) {
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
""",
    """    runtime.contextContributions = resolveDeclaredProjectContextContributions({
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
""",
)

replace_once(
    SERVICE,
    """    this.runtimeContext.contextManager.replaceInlineItems(
      runtime.projectId,
      runtime.taskId,
      mergeContributionInlineItems(runtime.contextContributions),
    )
""",
    """    const existingInlineItems = this.runtimeContext.contextManager
      .getTask(runtime.projectId, runtime.taskId).session.inlineItems
    this.runtimeContext.contextManager.replaceInlineItems(
      runtime.projectId,
      runtime.taskId,
      replaceContributionInlineItems(existingInlineItems, runtime.contextContributions),
    )
""",
)

replace_once(
    TEST,
    """  mergeContributionInlineItems,
  mergeContributionReferences,
  resolveDeclaredProjectContextContributions,
""",
    """  mergeContributionInlineItems,
  mergeContributionReferences,
  replaceContributionInlineItems,
  resolveDeclaredProjectContextContributions,
""",
)

replace_once(
    TEST,
    """  it('allows a declared provider to report that the task is not applicable', () => {
""",
    """  it('replaces only prior contribution items and preserves host-owned Inline Context', () => {
    const contributions = resolveDeclaredProjectContextContributions({
      project: adapterProject(),
      request,
      providers: [provider],
      serviceLookup: () => validService,
    })
    const merged = replaceContributionInlineItems([
      {
        id: 'host-owned',
        title: 'Host Owned',
        content: 'keep me',
        provenance: 'runtime://synthetic/host',
      },
      {
        id: 'contribution:stale:scope',
        title: 'Stale',
        content: 'remove me',
        provenance: 'provider://stale/context',
      },
    ], contributions)
    expect(merged.some(item => item.id === 'host-owned')).toBe(true)
    expect(merged.some(item => item.id === 'contribution:stale:scope')).toBe(false)
    expect(merged.some(item => item.id.includes('synthetic-analysis'))).toBe(true)
  })

  it('allows a declared provider to report that the task is not applicable', () => {
""",
)

replace_once(
    TEST,
    """  it('rejects cross-project providers and asynchronous providers', () => {
""",
    """  it('rejects cross-platform absolute and URI-like write scopes', () => {
    for (const unsafe of ['C:/other-project/**', 'source://external/write']) {
      expect(() => resolveDeclaredProjectContextContributions({
        project: adapterProject(),
        request,
        providers: [provider],
        serviceLookup: () => ({
          contributeContext: () => ({
            applicable: true,
            contribution: {
              schema: PROJECT_CONTEXT_CONTRIBUTION_SCHEMA,
              projectId: PROJECT_ID,
              taskId: 'TASK-1',
              contributionId: 'unsafe-cross-platform',
              provenance: 'provider://synthetic.context-provider/TASK-1',
              writeScope: { allowed: [unsafe], protected: [] },
            },
          }),
        }),
      })).toThrow(/safe project-relative path/)
    }
  })

  it('rejects cross-project providers and asynchronous providers', () => {
""",
)

for relative, required in {
    CONTRIBUTION: ["windowsAbsolute", "replaceContributionInlineItems"],
    SERVICE: ["replaceContributionInlineItems(existingInlineItems", "runtime.contextContributions = resolveDeclaredProjectContextContributions"],
    TEST: ["preserves host-owned Inline Context", "URI-like write scopes"],
}.items():
    text = (ROOT / relative).read_text(encoding="utf-8")
    for marker in required:
      if marker not in text:
          raise SystemExit(f"{relative}: hardening marker missing: {marker}")

print("Context contribution hardening transformations applied.")
