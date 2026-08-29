# Execution Supervisor Phase 1 Implementation Context v0.1

> Status: **FROZEN IMPLEMENTATION CONTEXT / NO PHASE 1 SOURCE IMPLEMENTATION YET**
> Date: 2026-08-29
> Branch: `feat/execution-supervisor-phase1-event-store-replay-v0.1`
> Starting HEAD: `048bf21a9ec4b186af090972fe999bff5f2efc82`
> Main source base: `059370706221a5af48686e3e93390c400b9795fa`

## 1. Authority and purpose

This context compiles the implementation boundary from:

```text
root AGENTS.md
Codex Local Development And Validation Charter v0.1
Execution Supervisor Phase 1 Codex Handoff v0.1
Execution Supervisor And Obligation Ledger Design 25 v0.1
Public Governance Runtime And External Boundaries Design 21 v0.1
current Phase 0 source and tests
three independent read-only Agent audits
```

Agent audit findings are advisory. Only repository commands and persisted artifacts may establish mechanical PASS.

## 2. Exact Phase 1 scope

Deliver only:

```text
append-only durable Execution Event storage
exact request/runtime/project/task/turn/agent/context/contract binding
full-envelope hash, sequence and idempotency enforcement
persistent replay cursor and bounded pagination
cross-instance and actual cross-process reopen/reconstruction
corrupt/inconsistent/bounded-state failure behavior
```

Do not implement:

```text
Obligation Ledger evaluation or state transitions
claim/Evidence evaluation
Completion evaluation
External Agent/Chat Bridge
Governance Runtime lifecycle APIs
Reflection, Knowledge, Context or Closure
Host-specific SDK or Tool policy
ATP, ET6801, eTimer or other project business logic
```

Design 25 references to restoring an identical ledger are interpreted in this phase as restoring Phase 1-owned execution event state only. Live Obligation Ledger behavior remains Phase 2.

## 3. Contract decision

The existing canonical types remain the only task/event vocabulary:

```text
TaskSupervisionContractV01
ExecutionEventEnvelopeV01
ExecutionEventAcceptanceV01
canonicalJson / hashCanonicalJson / sha256Hex
validateTaskSupervisionContract()
validateExecutionEventEnvelope()
```

Phase 1 may add only persistence/replay types:

```ts
interface ExecutionEventStoreBindingV01 {
  readonly requestId: string
  readonly runtimeId: string
  readonly turnId: string
  readonly contract: TaskSupervisionContractV01
}

interface ExecutionEventStoreLimitsV01 {
  readonly maxEvents: number
  readonly maxStoreBytes: number
  readonly maxReplayEvents: number
}

interface ExecutionReplayCursorV01 {
  readonly sequence: number
  readonly stateHash: string
}

interface ExecutionReplayPageV01 {
  readonly events: readonly ExecutionEventEnvelopeV01[]
  readonly cursor: ExecutionReplayCursorV01
  readonly hasMore: boolean
}
```

The binding persists the full validated Task contract. Project/task/agent/context/route/revision are derived from that contract. Request/runtime/turn come from the binding. `routeHash` and `projectRevision` must not be duplicated onto the Event Envelope.

`runtimeId` is a stable logical governed Runtime identity, not an operating-system process ID.

## 4. Public API decision

The minimum API is:

```ts
interface ExecutionEventStoreV01 {
  readonly binding: ExecutionEventStoreBindingV01
  readonly limits: ExecutionEventStoreLimitsV01
  readonly cursor: ExecutionReplayCursorV01
  readonly eventCount: number

  append(
    event: ExecutionEventEnvelopeV01,
  ): Promise<ExecutionEventAcceptanceV01>

  replay(input: {
    readonly after?: ExecutionReplayCursorV01
    readonly limit: number
  }): Promise<ExecutionReplayPageV01>

  close(): Promise<void>
}

createFileExecutionEventStore(input)
openFileExecutionEventStore(input)
```

Rules:

```text
create and open are separate operations
openOrCreate is forbidden
create fails if the target already exists
open fails if the target is absent
open requires the expected exact binding
the caller supplies a controlled directory; identifiers are not interpolated into paths
open restores only binding, event indexes and cursor
no openTurn/closeTurn/completeTask/rehydrateTurn API is introduced
```

## 5. Persistent format decision

Use two files within one caller-supplied store directory:

```text
manifest.json
events.jsonl
```

`manifest.json` is immutable and contains an internal format version, the full binding, binding/contract hash, persisted limits and genesis state hash.

Each canonical JSONL record contains the exact existing Event Envelope plus internal persistence metadata:

```text
complete envelope hash
previous state hash
new state hash
accepted timestamp
```

Internal record/manifest types are not exported and do not rename Event fields.

Persistence rules:

```text
manifest creation is exclusive
events are appended as one canonical JSON line
accepted appends are flushed before return
cursor is the tail record sequence + stateHash
no mutable cursor.json is written
reopen validates every record, sequence, envelope hash and state-hash link
non-canonical JSON, truncation or mismatch fails closed
the store never truncates, repairs or invents history automatically
```

The eventId index and replay-offset index are bounded by persisted `maxEvents`. Replay is paginated and cannot return more than `maxReplayEvents` in one page.

## 6. Identity, ordering and idempotency

Append validates the existing Phase 0 Envelope before any persistence.

Exact event binding checks:

```text
requestId
runtimeId
projectId
taskId
turnId
agentId
contextHash
```

Ordering rules:

```text
new event sequence must equal cursor.sequence + 1
sequence gaps do not mutate the store
same eventId + same full canonical Envelope hash = DUPLICATE
same eventId + different full Envelope hash = integrity conflict
duplicate does not change event count, cursor, state hash or durable bytes
```

Comparing only `payloadHash` is forbidden because kind, sequence, timestamp or identity could differ while payload remains identical.

## 7. Machine-readable failure decision

Preserve the existing acceptance status and reasons. Add a backward-compatible optional structured issue list and a typed store error for create/open/replay corruption failures.

Minimum codes:

```text
EVENT_INVALID
EVENT_ID_INTEGRITY_CONFLICT
SEQUENCE_GAP
EVENT_BINDING_MISMATCH
STORE_BINDING_MISMATCH
STORE_ALREADY_EXISTS
STORE_NOT_FOUND
STORE_LIMIT_EXCEEDED
STORE_TRUNCATED_RECORD
STORE_INVALID_CANONICAL_JSON
STORE_STATE_HASH_MISMATCH
STORE_CURSOR_INVALID
STORE_EVENT_CHAIN_MISMATCH
STORE_CHANGED
STORE_CLOSED
```

Tests assert codes and structured field/sequence/offset metadata, not complete human messages.

All rejected append paths must prove:

```text
event count unchanged
cursor unchanged
state hash unchanged
original accepted record unchanged
same state remains after reopen
```

## 8. Writer and recovery boundary

Phase 1 proves sequential process handoff, not simultaneous multi-writer coordination.

```text
one active writer per execution store
append compares the current durable file state with the instance cursor before writing
an externally changed/stale instance fails closed with STORE_CHANGED
concurrent multi-writer acceptance is not claimed
normal close/reopen is not described as power-loss crash atomicity
```

No dependency-heavy lock/registry/workflow framework is added in this phase.

## 9. File ownership and layout

Production owner: root Codex Agent.

```text
src/contracts.ts
src/validation.ts
src/event-store.ts
src/internal/store-format.ts
src/internal/replay-state.ts
src/index.ts
package.json / README.md when required
```

Test owner: one dedicated implementation Agent after this context is committed.

```text
tests/event-store.test.ts
tests/replay.test.ts
tests/corruption.test.ts
tests/performance-fast-path.test.ts
tests/fixtures/*
benchmarks/phase1-event-store.mjs
```

Contract and governance observer Agents remain read-only. No Agent may create a second implementation or decide PASS.

## 10. Frozen deterministic test matrix

### Event Store tests

```text
empty store: eventCount 0, sequence 0, next 1, deterministic genesis
append sequence 1 and 2; replay exact order
exact duplicate returns DUPLICATE with no mutation
tampered duplicate uses a changed payload plus a newly valid payloadHash
sequence gap rejects without mutation; missing event can then be supplied
each binding identity field is independently mismatched and rejected
Phase 0 payload/identifier/contract bounds reject before persistence
configured maxEvents/maxStoreBytes reject without partial write
```

### Replay/rehydration tests

```text
instance A writes, closes; instance B opens same binding and continues at K+1
actual independent Node process reopens and continues the same logical Runtime
reconstructed Phase 1 state equals uninterrupted semantic projection
wrong contract/route/revision/request/runtime/project/task/turn/agent/context fails on open
invalid replay cursor fails without changing state
```

### Corruption tests

```text
truncated final record
invalid JSON
valid but non-canonical JSON
wrong envelope hash
wrong previous state hash
wrong current state hash
missing/reordered/modified event record
invalid sequence/cursor
```

Every corruption case must leave the original files untouched and fail again on a second open.

### Fast-path and benchmark tests

```text
1000 bounded synthetic event appends
paginated replay with exact count/order/hash/final cursor
append p50/p95 measurement
replay wall time
total 1000-event wall time
persisted bytes per event
memory delta for the configured budget
```

Numeric SLOs remain unfrozen. Tests assert correctness and finite non-negative measurements, not an arbitrary latency threshold.

Production source must have no model, network, A/R/K/G reroute, full Context rebuild, project business term or specific provider SDK dependency.

## 11. Actual cross-process gate

Vitest cross-instance tests are not sufficient to claim cross-process reconstruction.

Add a deterministic post-build Node script using a small fixture that imports `dist`:

```text
npm run build
npm run test:phase1-process
```

The script must launch independent Node processes against one D-drive temporary store and prove A create/append, B reopen/append, C replay. It must emit a single mechanical PASS marker and preserve failure details in a D-drive log.

## 12. Environment and Git gates

All validation commands explicitly use:

```text
Node v22.23.2
npm 10.9.8
D:\lihuan\vibe_code\codex\et_harness_env\runtimes\node-v22.23.2-linux-x64
D-drive npm cache, temp, workspace and logs
```

The ambient Windows Node 24/npm 11 must not be used for acceptance.

Before implementation and before every commit:

```text
fetch/remote/branch/HEAD/origin-main/status recorded
focused tests first
package test and build
affected integration only during iteration
git diff --check
no node_modules/dist/package-lock/temp/logs in the logical commit
```

Full public baseline runs only at the Phase 1 completion checkpoint and remains separate from Hosted CI claims.

## 13. Known limitations and forbidden claims

Phase 1 acceptance will not prove:

```text
concurrent multi-writer coordination
power-loss atomicity beyond explicit fsync behavior
resistance to an attacker with full store write access
Obligation Ledger/Completion/Evidence/Reflection/Knowledge/Context/Closure
ATP Pilot or real-project completion
Hosted CI acceptance
production-scale or unbounded event growth safety
```

Hash chaining detects accidental or untrusted mutation against the persisted chain; without an external trust anchor or MAC it is not an anti-tamper guarantee against a fully privileged writer.

## 14. Step exit condition

Implementation may begin only after this context is committed with a clean worktree. Phase 2 remains forbidden in this conversation.
