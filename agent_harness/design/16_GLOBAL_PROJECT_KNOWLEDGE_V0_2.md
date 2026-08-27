# Global + Project Knowledge v0.2

## Decision

Knowledge Manager owns one library mechanism and two storage scopes:

```text
Knowledge Manager
├─ Global Library  -> Harness-level shared resource
└─ Project Library -> Project Plugin private resource
```

No second Knowledge Manager implementation is introduced.

## Storage

```text
agent_harness/global_knowledge/

agent_harness/projects/<project>/knowledge/
```

Global data is outside `public_plugins/knowledge_manager/` so plugin upgrades do not own or delete shared knowledge.

## Scope rule

```text
Reusable without current project -> Global
Project implementation / path / project-only decision / exception -> Project
```

Agent selects the scope. Plugin does not auto-classify it.

## Address

Local address:

```text
K001.001
```

Qualified address:

```text
knowledge://global/K001.001
knowledge://project/et-tool/K001.001
```

The same K-ID may exist in both libraries safely.

## Query

```text
Global Search
Project Search
Combined Search = Global first + Project delta
```

Combined Search does not auto-resolve conflicts. Scope and URI are returned to Agent.

## Contribution

Both scopes use exactly the same rules:

```text
explicit existing Category
new item = CANDIDATE
exact deterministic duplicate guard
atomic mutation
validate + reindex
rollback on failure
```

No automatic Global-to-Project copying.

## Lifecycle

```text
Project unload
-> remove project cache
-> project files follow project lifecycle
-> Global Library remains mounted and unchanged
```

## Mount

Harness supplies Global Library root explicitly:

```text
AGENT_HARNESS_GLOBAL_KNOWLEDGE_ROOT
```

Repository default data location:

```text
agent_harness/global_knowledge
```

## Intentionally deferred

```text
knowledge validation / confidence promotion
cross-library semantic deduplication
automatic scope classification
automatic conflict resolution
```

These are separate concerns and are not required for the dual-scope foundation.
