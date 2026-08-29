# Execution Supervisor Phase 1 Completion Handoff v0.1

> Status: **LOCAL_MECHANICAL_ACCEPTED / HOSTED_CI_NOT_VERIFIED**
> Date: 2026-08-29
> Branch: `feat/execution-supervisor-phase1-event-store-replay-v0.1`
> Implementation commit: `7e8395e52966a361df34245eea8689dc08c2cf14`
> Normative design: `agent_harness/design/25_EXECUTION_SUPERVISOR_AND_OBLIGATION_LEDGER_V0_1.md`

## 1. Outcome

Design 25 Phase 1 is implemented and locally mechanically accepted at the exact implementation commit above.

Delivered only:

```text
append-only bounded durable Execution Event Store
exact Runtime/Task/Turn and contract binding persistence
full-envelope sequence/hash/idempotency enforcement
persistent replay cursor and bounded pagination
cross-instance and actual independent-process replay
fail-closed corruption, stale-store and configured-bound handling
```

No Phase 2 Obligation Ledger, claim/Evidence evaluation, External Agent Bridge, Reflection, Knowledge, Context or Closure implementation was started.

## 2. Implementation

The public package now exposes validated create/open, append and replay contracts. The file implementation persists:

```text
manifest.json   immutable binding, limits and deterministic genesis
events.jsonl    canonical append-only records with envelope and state-chain hashes
```

Important behavior:

```text
create and open remain separate
open requires the exact expected binding
accepted appends are flushed before return
exact duplicates are idempotent and do not mutate state
sequence gaps, identity mismatch and event-ID conflicts are rejected
reopen validates the complete canonical chain
replay is cursor-bound, ordered and limited
returned bindings, events and payloads are detached and deeply frozen
```

The logical source change is one commit with 16 files changed, 3,129 insertions and 5 deletions.

## 3. Acceptance evidence

Exact detached acceptance worktree:

```text
D:\lihuan\vibe_code\codex\et_harness_env\workspaces\phase1_acceptance_7e8395e
HEAD = 7e8395e52966a361df34245eea8689dc08c2cf14
Node = v22.23.2
npm = 10.9.8
```

### Package gate

```text
8 test files / 69 tests                         PASS
TypeScript build                                PASS
independent process A -> B -> C replay          PASS
Phase 0 baseline generation/validation          PASS
Phase 1 benchmark correctness                   PASS
PHASE1_PACKAGE_GATE_PASS                        PASS
```

Phase 1 benchmark, 1,000 events and replay page limit 128:

```text
append p50                    16483.213 us
append p95                    20700.17545 us
replay wall                   19.15432 ms
total wall                    16747.036496 ms
persisted bytes/event         936.004
memory delta                  2809736 bytes
count/order/payload/cursor    all true
thresholdsFrozen              false
```

### Repository compatibility gate

```text
public boundary checks                            PASS
workflow-declared public package test/build       PASS 21/21
workflow-declared public integration scripts      PASS 7/7
Windows git diff --check                          PASS
```

Packages whose repository scripts use `--passWithNoTests` are recorded only as exit-zero package results; they are not claimed as test coverage.

### Logs

All acceptance logs are on D drive:

```text
D:\lihuan\vibe_code\codex\et_harness_env\logs\phase1-acceptance-package.log
SHA256 A91A89C21A9A77E6928BD543290213D4258E5E0DFD86BBBB283D755FD894EE94

D:\lihuan\vibe_code\codex\et_harness_env\logs\phase1-acceptance-package-loop.log
SHA256 B8AFA8DAA53714FFF60AE12FBF497D69066F0C86BD0A5F9C6129C67BBBABE545

D:\lihuan\vibe_code\codex\et_harness_env\logs\phase1-acceptance-integrations.log
SHA256 B651506C80EF52FD5D3549DE56A94539FCC6117FFFC23FFA0E8BFA3FE84FE59C
```

## 4. Problems found and resolved

```text
missing D-worktree dependencies
  -> installed into the reusable D environment

exactOptionalPropertyTypes compile failures
  -> corrected optional source-code construction

mutable caller/return aliases could mutate trusted state
  -> canonical detached deep clone plus deep freeze; adversarial tests added

invalid-event rejection identity could change across the first await
  -> captured event identity before asynchronous work; regression test added

cross-process fixture compared event 3 against event 1 payload data
  -> corrected sequence-based fixture selection; invalid earlier result discarded

genericity coverage did not scan the whole package recursively
  -> expanded scans across production and test trees

WSL Git could not parse a Windows worktree gitdir pointer
  -> ran Linux boundary checks and Windows Git diff check separately

Windows CRLF caused validation shell scripts to fail before execution
  -> mechanically normalized only the disposable acceptance copy and reran all gates
```

The three observing Agents only inspected behavior, scope and test coverage. They did not decide acceptance. Mechanical commands and persisted artifacts establish the result.

## 5. Environment and C-drive check

Acceptance cache, dependencies, temporary files, worktrees and logs were directed to:

```text
D:\lihuan\vibe_code\codex\et_harness_env
```

Two task-attributable WSL `/tmp/node-compile-cache` files were detected during worker runs, uniquely verified, and precisely removed. Final check:

```text
WSL_TMP_NODE_CACHE_RECENT_COUNT=0
```

Subsequent commands explicitly set `TMPDIR`, `TMP`, `TEMP` and `NODE_COMPILE_CACHE` to the D-drive environment. Generated acceptance outputs remain only in the reusable detached D-drive acceptance worktree and are not part of the implementation commit.

## 6. Honest limitations

Phase 1 does not claim:

```text
concurrent multi-writer coordination
power-loss atomicity beyond the implemented flush boundary
protection from a privileged writer that can replace the full store
externally anchored detection of replacement by an earlier complete valid prefix
production-scale or unbounded growth safety
hardware/HIL validation
Hosted CI acceptance
```

The complete-prefix rollback limitation cannot be closed by an internal hash chain alone. It requires a separately authoritative cursor/checkpoint or another external trust anchor, which is outside the frozen Phase 1 design and was not added speculatively.

## 7. Status and next boundary

```text
Phase 1 implementation                  PASS
Phase 1 focused/package tests           PASS
Phase 1 cross-process replay            PASS
Public package compatibility            PASS 21/21
Public integration compatibility        PASS 7/7
Local mechanical acceptance             PASS
Hosted CI exact-SHA acceptance           NOT_VERIFIED
Hardware/HIL                            NOT_EXECUTED / NOT_APPLICABLE
Phase 2 Obligation Ledger               NOT_STARTED
```

The next Design 25 step is Phase 2, which would deliver structured obligation contribution, ledger creation, state transitions, dependency handling, violation records and status query. It requires a fresh Task Context, explicit authorization and a separate implementation boundary. This handoff does not authorize or begin Phase 2.
