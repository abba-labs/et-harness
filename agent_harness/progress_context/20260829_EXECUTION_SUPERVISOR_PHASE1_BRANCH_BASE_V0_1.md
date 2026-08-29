# Execution Supervisor Phase 1 Branch Base v0.1

> Status: **CLEAN BRANCH BASE / NO PHASE 1 SOURCE IMPLEMENTATION YET**  
> Date: 2026-08-29  
> Branch: `feat/execution-supervisor-phase1-event-store-replay-v0.1`  
> Base repository: `abba-labs/et-harness`  
> Base `main` HEAD: `059370706221a5af48686e3e93390c400b9795fa`

This branch was created directly from the final `main` that contains:

- the repaired single-vocabulary Execution Supervisor Phase 0 source;
- the Codex local-development charter;
- the Phase 1 Codex Handoff;
- root `AGENTS.md`;
- the updated progress-context recovery order.

At branch creation there was **no Phase 1 production source divergence** from `main`.

Codex must not start implementation until the local Phase 0 acceptance on `main` is mechanically executed and recorded as:

```text
LOCAL_MECHANICAL_ACCEPTED
```

After that, this is the only authorized branch for Design 25 Phase 1:

```text
Persistent Event Store
+ exact execution identity binding
+ sequence/hash/idempotency enforcement
+ cross-process replay / rehydration cursor
```

Do not use or cherry-pick the historical branches:

```text
feat/execution-supervisor-phase1-event-store-v0.1
feat/public-execution-supervisor-phase1-contract-builder-v0.1
```

Read before implementation:

```text
AGENTS.md
agent_harness/progress_context/20260829_CODEX_LOCAL_DEVELOPMENT_AND_VALIDATION_CHARTER_V0_1.md
agent_harness/progress_context/20260829_EXECUTION_SUPERVISOR_PHASE1_CODEX_HANDOFF_V0_1.md
agent_harness/design/25_EXECUTION_SUPERVISOR_AND_OBLIGATION_LEDGER_V0_1.md
agent_harness/progress_context/20260829_EXECUTION_SUPERVISOR_PHASE0_REPAIR_WORKLOG_V0_1.md
```

This file is a branch provenance receipt, not Phase 1 completion evidence.
