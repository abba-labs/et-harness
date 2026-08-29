# Execution Supervisor Phase 2 Implementation Context v0.1

> Status: **FROZEN IMPLEMENTATION CONTEXT / NO PHASE 2 SOURCE IMPLEMENTATION YET**
> Date: 2026-08-29
> Branch: `feat/execution-supervisor-phase2-obligation-ledger-v0.1`
> Starting HEAD: `10adbcb7298e1ee809057e5ff37d09bd89ff12f7`
> Phase 1 source base: `origin/feat/execution-supervisor-phase1-event-store-replay-v0.1`

## 1. Authority and purpose

This context compiles the Phase 2 implementation boundary from:

```text
root AGENTS.md
Codex Local Development And Validation Charter v0.1
Execution Supervisor Phase 1 Completion Handoff v0.1
Execution Supervisor Phase 1 Implementation Context v0.1
Execution Supervisor And Obligation Ledger Design 25 v0.1
Execution Supervisor Phase 0 Repair Worklog v0.1
Public Governance Runtime And External Boundaries Design 21 v0.1
current Phase 1 source and tests at 10adbcb7298e1ee809057e5ff37d09bd89ff12f7
```

The purpose of this phase is to add the deterministic Obligation Ledger projection
on top of the accepted Phase 1 durable Execution Event Store. It does not create a
second lifecycle controller, event vocabulary, project-policy engine or completion
authority.

Observer Agent findings are advisory. Only repository commands and persisted
artifacts may establish mechanical PASS.

## 2. Exact Phase 2 scope

Deliver only:

```text
structured obligation contribution accepted through TaskSupervisionContractV01
ledger creation from the validated immutable task contract
deterministic obligation state transitions
dependency blocking and deterministic unblocking/cascade
durable-event-driven violation records
immutable status query
cross-instance ledger reconstruction from Phase 1 replay
```

Required acceptance:

```text
missing required read remains PENDING
valid trusted RESOURCE_READ receipt satisfies the matching obligation
out-of-scope RESOURCE_WRITE becomes VIOLATED with a violation record
Agent/assistant content cannot directly mark an obligation SATISFIED
```

Do not implement:

```text
Phase 3 External Agent Response/Event Bridge
claim/Evidence or fabricated-PASS evaluation from Phase 4
Completion evaluation or READY_TO_CLOSE/COMPLETE decisions
Reflection, Knowledge, Context or Closure integration
Host-specific SDK, tool interception or preflight enforcement
project-specific obligation compilation or prose parsing
ATP, ET6801, eTimer, MCU or other project business logic
waiver authorization workflow
new Governance Runtime lifecycle entrypoints
second event store, lifecycle state machine, Registry, Workflow or DI framework
```

## 3. Frozen ownership boundaries

```text
Project Plugin / Context Contributor
  owns concrete project obligations and compiles structured targets/policies

Phase 1 Execution Event Store
  owns durable accepted event identity, binding, sequence, hash and replay

Phase 2 Obligation Ledger
  owns deterministic projection of accepted events into obligation states,
  dependency blockers, violations and status

Host Adapter / Tool Plugin
  supplies observable structured receipts; it does not decide satisfaction

Agent
  performs semantic work; its message or assertion is never a state transition

Future Completion Evaluator / Kernel
  remain the only completion and closure authorities
```

The existing `TaskSupervisionContractV01`, `ObligationDefinitionV01`,
`ExecutionEventEnvelopeV01`, receipt types and `ObligationStateRecordV01` remain
the canonical vocabulary. Phase 2 may add ledger/status/violation types and
kind-specific structured validation, but it must not duplicate or rename these
contracts.

## 4. Phase 1 integration and persistence decision

The accepted Phase 1 Event Store is the trusted input boundary:

```text
raw event
  -> Phase 1 validate/bind/hash/sequence/append
  -> ACCEPTED durable event
  -> Phase 2 affected-obligation projection
```

`REJECTED` events never mutate the ledger. `DUPLICATE` events are idempotent
no-ops. Phase 2 status is a deterministic projection of the immutable Task
Supervision Contract plus the accepted Phase 1 event stream.

For v0.1, the canonical event stream is the durable source of truth. Rehydration
must replay the Phase 1 store and produce the same ledger/status/violations as an
uninterrupted instance. A second independently mutable ledger file is forbidden
in this phase because it would introduce dual-write and split-authority failure
modes. Snapshot optimization, if later justified by measured evidence, is outside
this phase.

## 5. State and dependency rules

Initial state:

```text
obligation with no dependencies                    -> PENDING
obligation with any unresolved dependency          -> BLOCKED
```

Transition authority:

```text
matching accepted durable receipt                  -> evaluator may transition
missing or non-matching receipt                    -> no transition
assistant/user prose or requested state field      -> no transition
out-of-scope mutation                              -> WRITE_SCOPE VIOLATED
```

Dependency rules:

```text
only declared obligation IDs may be dependencies
contract validation continues to reject missing IDs and cycles
all dependencies resolved acceptably               -> dependent BLOCKED to PENDING
pending/blocked/violated dependency                 -> dependent remains BLOCKED
replay order must produce the same dependency result
```

`SATISFIED`, `VIOLATED` and dependency changes must be produced only by the
deterministic evaluator. No public `setState()`, `markSatisfied()` or equivalent
Agent-controlled mutation API is allowed.

## 6. Receipt and violation boundary

Phase 2 evaluates only the minimum structured receipts needed by its acceptance:

```text
RESOURCE_READ  -> ResourceReceiptV01
RESOURCE_WRITE -> MutationReceiptV01
```

Required-resource matching must use declared structured identity and satisfaction
policy, including the allowed provider/disposition and any declared exact
revision/content-hash requirements. A generic statement that a resource was read
is not proof.

For Phase 2 v0.1, `REQUIRED_RESOURCE` accepts only `FOUND`. `NO_MATCH` and
`UNAVAILABLE` remain durable facts but cannot satisfy the resource obligation;
their separate `SOURCE_DISPOSITION` semantics are outside this phase. A matching
provider ID means only that the receipt matches the Project-contributed allowlist
at the trusted Event Store input boundary. Phase 2 does not claim cryptographic
provider authentication, which requires the later Host/Event Bridge boundary.

Write-scope evaluation must compare the mutation's structured resource/path
identity with the contributed scope policy. It must not trust an Agent assertion
that a write was allowed. An out-of-scope event creates one deterministic,
queryable violation record and transitions the applicable `WRITE_SCOPE`
obligation to `VIOLATED`. Replay and duplicate ingestion must not create duplicate
violations.

Phase 2 v0.1 accepts at most one `WRITE_SCOPE` obligation so multiple-scope union
or intersection semantics cannot be guessed. Because the current mutation receipt
contains only one resource/path identity, `MOVE` and `COPY` fail closed until a
future reviewed contract can represent both endpoints.

Unsupported obligation kinds remain visible and truthfully unresolved; Phase 2
must not invent future Phase 4 or Phase 5 semantics to satisfy them.

## 7. Status and boundedness

The status query must return an immutable bounded snapshot containing at least:

```text
exact request/runtime/project/task/turn/agent/context/contract binding
event replay cursor used by the projection
one state record per contract obligation in deterministic contract order
pending, blocked, satisfied and violated obligation IDs
deterministic violation records and their event/obligation references
```

All externally returned arrays/records must be defensive immutable copies. State,
event references, blocker references and violation records must remain bounded by
the already validated contract/event-store limits. Event hot-path processing may
update only directly affected obligations and their dependency descendants; it
must not invoke a model, reroute A/R/K/G, rebuild Context, search Knowledge or call
a network service.

## 8. Expected source and test ownership

Production changes are limited to the existing public package:

```text
agent_harness/public_plugins/execution_supervisor/src/contracts.ts
agent_harness/public_plugins/execution_supervisor/src/validation.ts
agent_harness/public_plugins/execution_supervisor/src/obligation-ledger.ts
agent_harness/public_plugins/execution_supervisor/src/violation-evaluator.ts
agent_harness/public_plugins/execution_supervisor/src/service.ts (only if a thin
  Event Store -> Ledger coordinator is required)
agent_harness/public_plugins/execution_supervisor/src/index.ts
package README/package scripts only when required by the implementation
```

The existing Phase 1 `event-store.ts` and internal persistence/replay modules may
receive only the smallest compatibility change required to expose already
accepted events. Their storage format, ordering, binding and replay semantics are
frozen unless a proven blocking defect is reported before expansion.

Focused tests:

```text
tests/obligation-ledger.test.ts
tests/scope-violation.test.ts
tests/obligation-replay.test.ts
shared synthetic fixtures only where necessary
```

## 9. Frozen focused test matrix

```text
contract obligations create exactly one deterministic state record each
required read begins PENDING when no matching event exists
wrong resource/provider/disposition/revision/hash leaves it PENDING
accepted matching read transitions it to SATISFIED
assistant message claiming SATISFIED leaves it PENDING
event rejected by Phase 1 leaves ledger and violations unchanged
exact duplicate is a no-op
dependency starts BLOCKED and becomes PENDING after prerequisites satisfy
dependency cascade is deterministic and does not auto-satisfy dependents
out-of-scope write transitions WRITE_SCOPE to VIOLATED
allowed write does not create an out-of-scope violation
replay does not duplicate the violation
cross-instance replay reconstructs byte-equivalent canonical status
status results cannot mutate internal ledger state
public source contains no project-specific business term or provider SDK
```

Tests must assert typed codes/IDs/state and durable replay evidence rather than
complete human-readable messages. No test may weaken contract validation, accept
Agent self-certification or replace a missing receipt with prose.

## 10. D-drive environment and efficiency gates

All commands use the Phase 2 worktree explicitly:

```text
D:\lihuan\vibe_code\codex\et_harness_env\workspaces\phase2_obligation_ledger
```

Reused environment:

```text
Node v22.23.2
npm 10.9.8
TypeScript 6.0.3
Vitest 4.1.11
D:\lihuan\vibe_code\codex\et_harness_env\runtimes\node-v22.23.2-linux-x64
D-drive npm cache, node_modules, temp and logs
```

The Phase 2 package manifest is dependency-equivalent to the validated Phase 1
manifest. The worktree therefore reuses the existing D-drive `node_modules`
through an ignored local junction. Dependency installation is forbidden unless
the declared dependency signature changes and the reason is reported first.

Every WSL command must use an isolated environment with `HOME`, `TMPDIR`, `TMP`,
`TEMP`, `XDG_CACHE_HOME`, `npm_config_cache` and `NODE_COMPILE_CACHE` explicitly
pointing below `D:\lihuan\vibe_code\codex\et_harness_env`. Task dependencies,
caches, temporary files, logs and build outputs must not be written to C.

Validation ladder:

```text
during edits       focused Obligation Ledger tests only
logic checkpoint   execution_supervisor package test + one package build
integration        directly affected integration only; reuse existing dist
phase close        21 public packages + 7 integrations exactly once
always             git diff --check + clean-scope/status inspection
```

No more than two large executions may run concurrently. Empty asynchronous polls
must follow the root `AGENTS.md` long-wait requirements. A successful observer
review is never reported as test PASS.

## 11. Known limitations and forbidden claims

Phase 2 acceptance will not prove:

```text
claim/Evidence authenticity or fabricated-PASS prevention beyond Agent state denial
Completion readiness or task COMPLETE
Reflection/Knowledge/Context/Closure behavior
Host interception or ENFORCE preflight blocking
project-specific obligation generation
simultaneous Event Store multi-writer coordination
power-loss guarantees beyond Phase 1 behavior
Hosted CI acceptance
ATP Pilot or real hardware execution
```

## 12. Step exit condition

Implementation may begin only after this context is committed with a clean tracked
worktree. Any material expansion must first update and re-freeze this context.
Phase 3 remains forbidden in this conversation.
