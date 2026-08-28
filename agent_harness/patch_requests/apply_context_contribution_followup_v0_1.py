#!/usr/bin/env python3
from pathlib import Path


def replace_once(path_value: str, old: str, new: str) -> None:
    path = Path(path_value)
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path_value}: expected one replacement, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


manager = "agent_harness/public_plugins/context_builder/src/context-management-service.ts"
replace_once(
    manager,
    "const inlineItems = normalizeInlineContextItems([...snapshot.session.inlineItems, ...items])",
    "const inlineItems = normalizeInlineContextItems([...(snapshot.session.inlineItems ?? []), ...items])",
)
replace_once(
    manager,
    """    const inlineItems = input.inlineItems !== undefined
      ? normalizeInlineContextItems(input.inlineItems)
      : snapshot.session.inlineItems
""",
    """    const inlineItems = input.inlineItems !== undefined
      ? normalizeInlineContextItems(input.inlineItems)
      : snapshot.session.inlineItems ?? []
""",
)
replace_once(
    manager,
    "      inlineItems: session.inlineItems,",
    "      inlineItems: session.inlineItems ?? [],",
)
replace_once(
    manager,
    "        ...session.inlineItems,",
    "        ...(session.inlineItems ?? []),",
)

service = "agent_harness/public_plugins/auto_governance_engine/src/service.ts"
replace_once(
    service,
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
    """    const hasDeclaredContextContributor = Object.values(project.adapters).some(
      adapter => adapter.capability === PROJECT_CONTEXT_CONTRIBUTION_CAPABILITY,
    )
    runtime.contextContributions = hasDeclaredContextContributor
      ? resolveDeclaredProjectContextContributions({
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
      : []
""",
)
replace_once(
    service,
    """    this.runtimeContext.contextManager.replaceInlineItems(
      runtime.projectId,
      runtime.taskId,
      mergeContributionInlineItems(runtime.contextContributions),
    )
""",
    """    const existingInlineItems =
      this.runtimeContext.contextManager.getTask(runtime.projectId, runtime.taskId).session.inlineItems ?? []
    const contributionInlineItems = mergeContributionInlineItems(runtime.contextContributions)
    this.runtimeContext.contextManager.replaceInlineItems(
      runtime.projectId,
      runtime.taskId,
      [
        ...existingInlineItems.filter(item => !item.id.startsWith('contribution:')),
        ...contributionInlineItems,
      ],
    )
""",
)

contribution = "agent_harness/public_plugins/auto_governance_engine/src/context-contribution.ts"
replace_once(
    contribution,
    """const normalizeReadScope = (values: readonly string[] | undefined): string[] => {
  if (!values) return []
  if (values.length > MAX_SCOPE_ENTRIES) throw new Error('readScope exceeds its entry budget')
  return uniqueStrings(values.map((value, index) => singleLine(`readScope[${index}]`, value, 1_000)))
}
""",
    """const READ_SCOPE_URI_RE = /^(?:source|project|knowledge|evidence|runtime|provider):\/\/\S+$/

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
""",
)

test_path = Path("agent_harness/public_plugins/auto_governance_engine/tests/context-contribution.test.ts")
test_text = test_path.read_text(encoding="utf-8")
marker = """  it('rejects cross-project providers and asynchronous providers', () => {
"""
addition = """  it('rejects unsafe project read scopes while allowing stable source URIs', () => {
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
            contributionId: 'unsafe-read',
            provenance: 'provider://synthetic.context-provider/TASK-1',
            readScope: ['C:/other-project/secrets/**'],
          },
        }),
      }),
    })).toThrow(/absolute Windows path/)

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
            contributionId: 'unsafe-read-parent',
            provenance: 'provider://synthetic.context-provider/TASK-1',
            readScope: ['../other-project/**'],
          },
        }),
      }),
    })).toThrow(/safe project-relative path/)
  })

"""
if test_text.count(marker) != 1:
    raise SystemExit("context contribution test insertion marker mismatch")
test_path.write_text(test_text.replace(marker, addition + marker, 1), encoding="utf-8")

print("Applied context contribution compatibility and isolation follow-up.")
