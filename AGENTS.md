# ET Harness Codex Entry

This repository is governed by frozen design and Handoff documents. Do not begin by guessing from branch names.

## Mandatory start

Before changing public Harness code:

```bash
git fetch --all --prune
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git status --short
```

Then read, in order:

1. `agent_harness/progress_context/20260829_CODEX_LOCAL_DEVELOPMENT_AND_VALIDATION_CHARTER_V0_1.md`
2. `agent_harness/progress_context/20260829_EXECUTION_SUPERVISOR_PHASE1_CODEX_HANDOFF_V0_1.md`
3. `agent_harness/design/25_EXECUTION_SUPERVISOR_AND_OBLIGATION_LEDGER_V0_1.md`
4. `agent_harness/progress_context/20260829_EXECUTION_SUPERVISOR_PHASE0_REPAIR_WORKLOG_V0_1.md`
5. `agent_harness/design/21_PUBLIC_GOVERNANCE_RUNTIME_AND_EXTERNAL_BOUNDARIES_V0_1.md`

## Current development rule

```text
main = canonical public upstream
one conversation = one phase
one phase = one clean feature branch
local mechanical evidence is required before the next phase
```

Do not implement features directly on `main`.

The authorized next public implementation branch is:

```text
feat/execution-supervisor-phase1-event-store-replay-v0.1
```

Do NOT continue these stale/obsolete branches:

```text
feat/execution-supervisor-phase1-event-store-v0.1
feat/public-execution-supervisor-phase1-contract-builder-v0.1
```

Do not restore the deleted PR #12 Execution Supervisor prototype files wholesale.

## Phase 1 scope

Phase 1 is only:

```text
persistent execution-event store
+ exact identity binding
+ sequence/hash/idempotency enforcement
+ cross-process replay cursor / rehydration
```

It is NOT yet:

```text
Obligation Ledger evaluation
claim/Evidence evaluation
External Chat Bridge
Reflection
Knowledge/Context Closure
ATP/eTimer business logic
```

## Non-negotiable boundaries

- Public Harness contains no ATP / ET6801 / eTimer business rules.
- Do not create a second Task Supervision contract vocabulary.
- No LLM/network/full reroute on the execution-event hot path.
- Agent statements are not trusted PASS evidence.
- A GitHub Actions job with `steps=[]` is not executed CI evidence.
- Codex local development is not proof that the frozen current-ChatGPT ATP Pilot passed.

At phase completion, write a new progress/Handoff document with exact branch HEAD, tests, failures, performance evidence and the next authorized phase. Do not start Phase 2 in the same conversation.
