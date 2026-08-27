# Knowledge Library Scope Standard v0.2

> Scope model: `global | project`
> Library model: `knowledge-library-v0.2`

## 1. Two independent libraries

Knowledge Manager manages two kinds of library instances with the same engine:

```text
Global Library
Project Library
```

Global Library is Harness-level shared state and is not owned by a Project Plugin.
Project Library belongs to one registered project and follows that project's lifecycle.

## 2. Scope rule

A Knowledge Candidate SHOULD target `global` when its fact remains reusable after removing the current project context.

A Knowledge Candidate SHOULD target `project` only when the fact describes project-specific implementation, layout, decisions, behavior, compatibility, or constraints.

The public plugin does not automatically decide scope. Agent selects the target and Knowledge Manager enforces the selected library boundary.

## 3. Qualified Knowledge URI

Library-local K-ID remains unchanged:

```text
K001.001
K010.020.010
```

Globally unique references use:

```text
knowledge://global/<K-ID>
knowledge://project/<project-id>/<K-ID>
```

Within a project library, a bare K-ID means the current project library only.

## 4. Search behavior

Knowledge Manager exposes:

```text
searchGlobalKnowledge
searchKnowledge            # existing project-only API
searchKnowledgeCombined
```

Combined search order is:

```text
Global first
Project second
```

The plugin does not resolve semantic conflicts between Global and Project knowledge. Results carry their library scope and qualified URI so Agent can interpret project-specific exceptions.

## 5. Mutation behavior

Global and Project libraries use the same mutation rules:

```text
new knowledge -> CANDIDATE
explicit category
pre-write duplicate guard
atomic write
validate + reindex
rollback on failure
```

Mutation never copies Global Knowledge into Project Knowledge automatically.

## 6. Lifecycle

```text
Unload Project A
-> unregister Project A Knowledge cache
-> Global Knowledge unchanged
-> other Project Knowledge unchanged
```

Global Library lifetime is tied to Harness storage, not to a project or to the Knowledge Manager package installation directory.

## 7. Mounting

Knowledge Manager accepts an explicit Global Library root.

Harness deployments SHOULD provide it through:

```text
AGENT_HARNESS_GLOBAL_KNOWLEDGE_ROOT
```

The standard repository root is:

```text
agent_harness/global_knowledge
```

Knowledge Manager must not guess Global Knowledge from a Project Plugin path.

## 8. Boundary

This standard intentionally does not define:

```text
cross-library automatic deduplication
automatic scope classification
automatic conflict resolution
validation threshold or automatic promotion policy
```

Those are separate governance concerns.
