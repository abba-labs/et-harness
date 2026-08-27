# Harness Global Knowledge

`global_knowledge/` is a Harness-level shared Knowledge Library.

It is not owned by any Project Plugin and is not stored inside the Knowledge Manager plugin package.

Canonical source:

```text
TAXONOMY.yaml
SOURCES.yaml
VERIFICATIONS.jsonl
NNN_*.md
```

`SOURCES.yaml` is the Global Source Registry. `VERIFICATIONS.jsonl` is append-only and records SUPPORT / CONTRADICT relations from Source or Evidence to Knowledge. The file may not exist before the first Verification.

Generated artifacts such as `00_INDEX.md` are maintained by Knowledge Manager and must not be edited manually.

Scope rule:

```text
Reusable outside the current project -> Global Knowledge Candidate
Only meaningful for one project implementation -> Project Knowledge Candidate
```

All new knowledge starts as `CANDIDATE`. A project being unloaded must not remove or invalidate Global Knowledge, Global Source, or Global Verification history that was previously contributed by that project.
