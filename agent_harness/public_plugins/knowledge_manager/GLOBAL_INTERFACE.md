# Knowledge Manager Global Interface v0.2

## 1. Ownership

Global Knowledge is a Harness-level shared resource.

```text
Harness
└─ global_knowledge/
```

It is not owned by a Project Plugin and is not stored in the Knowledge Manager package directory.

## 2. Mount

Knowledge Manager mounts Global Knowledge from an explicit root:

```text
AGENT_HARNESS_GLOBAL_KNOWLEDGE_ROOT
```

or:

```text
mountGlobalLibrary(path)
```

Standard repository location:

```text
agent_harness/global_knowledge
```

## 3. Canonical files

```text
TAXONOMY.yaml
SOURCES.yaml
VERIFICATIONS.jsonl
NNN_*.md
```

`SOURCES.yaml` / `VERIFICATIONS.jsonl` may be absent before their first record.

`00_INDEX.md` and machine indexes are generated artifacts.

Global Library must use `knowledge-library-v0.2`; legacy v0.1 is not accepted for Global scope.

## 4. Qualified address

Knowledge:

```text
knowledge://global/K001.001
```

Source:

```text
source://global/SRC000001
```

The same local K-ID / Source ID may exist in a Project Library without collision.

## 5. Query

```text
searchGlobalKnowledge(input)
searchKnowledgeCombined({ projectId, ... })
resolveKnowledgeReference(uri)
listGlobalSources()
resolveSourceReference(uri)
listVerifications(knowledgeUri)
getVerificationSummary(knowledgeUri)
```

Combined Search returns Global candidates before Project candidates and preserves the source scope. It does not automatically decide semantic conflicts.

## 6. Mutation

Global Knowledge uses the same light transaction rules as Project Knowledge:

```text
submitGlobalKnowledgeCandidate
updateGlobalKnowledgeCandidate
reclassifyGlobalKnowledge
deprecateGlobalKnowledge
addGlobalCategory
renameGlobalCategory
deprecateGlobalCategory
```

Source registration:

```text
registerGlobalSource
```

Verification:

```text
recordVerification({
  knowledgeUri,
  basisRef,
  relation: SUPPORT | CONTRADICT
})
```

New Knowledge contributions always enter as `CANDIDATE`.

## 7. Global verification boundary

Global Knowledge can be supported / contradicted by:

```text
Global Source
Project Evidence
```

It cannot use a Project-private Source directly. A reusable source should first be registered into Global Source Registry.

Evidence remains owned by Evidence / State Manager. Knowledge Manager stores only the Evidence URI in append-only Verification records.

## 8. Lifecycle

Project unload must never remove, reindex from project data, or invalidate Global Knowledge / Global Source / Global Verification history.

A Verification may retain an `evidence://project/...` URI after project unload; Evidence content is not copied into Global Knowledge.

Global Knowledge survives independently as long as the Harness-level storage exists.

## 9. Scope decision

Agent chooses the target library.

```text
Reusable outside current project -> Global
Project implementation / layout / project-only decision / exception -> Project
```

Knowledge Manager enforces the chosen boundary but does not use an LLM to auto-classify scope.
