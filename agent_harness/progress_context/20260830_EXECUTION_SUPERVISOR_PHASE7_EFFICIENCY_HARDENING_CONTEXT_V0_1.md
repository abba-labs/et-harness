# Execution Supervisor Phase 7 Efficiency Hardening Context v0.1

> Status: **FROZEN IMPLEMENTATION CONTEXT / NO SOURCE IMPLEMENTATION YET**
> Date: 2026-08-30
> Branch: `feat/execution-supervisor-phase7-efficiency-hardening-v0.1`
> Starting HEAD: `08e0bc7e2a038ccbeab05e12489158850e080bc2`
> Phase 6 source: `feat/execution-supervisor-phase6-host-enforcement-profiles-v0.1`

## 1. Authority and execution container

This context compiles the Phase 7 boundary from:

```text
root AGENTS.md
Codex Local Development And Validation Charter v0.1
Execution Supervisor Phase 6 Completion Handoff v0.1
Execution Supervisor And Obligation Ledger Design 25 v0.1
Framework Efficiency Observer Design 20 v0.1
Public Governance Runtime And External Boundaries Design 21 v0.1
current source and tests at 08e0bc7e2a038ccbeab05e12489158850e080bc2
```

This branch does not contain the later `compile_task_context.py`/R002 compiler
named by the outer workspace rule. This document therefore follows the
repository's existing manual frozen-context convention and fails closed on any
scope expansion.

Child Agents may inspect rules, implementation and tests and report defects.
They cannot decide PASS. Only commands executed against the exact source and
persisted evidence can establish acceptance.

## 2. Phase objective

Phase 7 hardens the already delivered Event Store, Obligation Ledger, Runtime
and optional Efficiency Observer without adding another framework layer:

```text
canonical durable events remain exact and replayable
  -> bounded deterministic Ledger projections and targeted indexes
  -> ordinary observations reuse unchanged Context and route state
  -> package benchmark measures the real Store/Ledger hot path
  -> optional Observer analyzes bounded numeric metrics without authority
```

Priority remains:

```text
reliable > stable > lightweight > extensible
```

No durable receipt, violation, hash-chain fact, lifecycle binding or trusted
Evidence may be discarded to improve a benchmark.

## 3. Exact deliverables

Deliver only:

```text
deterministic repeated-resource receipt projection with an access count
bounded state references while canonical events remain available in Event Store
targeted REQUIRED_RESOURCE/SOURCE_DISPOSITION/WRITE_SCOPE lookup on ingest
bounded incomplete external-Agent span using the already frozen Bridge budgets
O(1) duplicate eventId lookup without weakening identity/hash checks
unchanged ordinary Context envelope reuse without A/R/K/G reroute or full frame rebuild
Phase 7 benchmark measuring Store ingest, Ledger transition, replay, bytes and projection size
frozen Node 22 linux-x64 Phase 7 SLO profile with explicit regression headroom
public CI benchmark execution and persisted report artifact
Observer analysis of Supervisor benchmark metrics with on/off/failure equivalence tests
```

Existing Context Builder, Turn Observation Store, external Bridge, Event Store
limits, dependency graph, Reflection deduplication and Observer fail-open helper
must be reused.

## 4. Frozen semantics

### Canonical events versus compact projections

```text
Event Store
  exact accepted events, hash chain, cursor, replay and finalization remain unchanged

Ledger status/projection
  repeated matching resource/hash/disposition receipts retain bounded representative refs
  accessCount records the deterministic number of matching accepted receipts
  replay and uninterrupted execution produce the same status and completion decision
```

Compaction never deletes critical persisted events. Duplicate `eventId` with the
same full envelope remains an idempotent no-op; the same ID with different
content remains an integrity conflict.

### Incremental evaluation and Context

```text
ordinary read/tool observation
  -> no route refresh
  -> no full Context frame rebuild when Context stateVersion is unchanged

mutation/error/material lifecycle change
  -> existing targeted route/Context refresh behavior remains authoritative
```

Task end may perform bounded close-path reevaluation. Phase 7 does not rewrite
the existing completion or dependency engine.

### Observer boundary

The Supervisor remains mandatory and does not import or require the Observer.
The Observer receives only bounded numeric/small-tag metrics through the
existing Governance Core fail-open metric contract or offline benchmark input.
Observer disabled, full, broken or absent must not change supervision state.

## 5. SLO freeze rule

The Phase 0 baseline schema remains historical and keeps
`thresholdsFrozen=false`. Phase 7 will not reinterpret it.

A separate package-owned Phase 7 SLO profile will be frozen only after repeated
Node 22 linux-x64 measurements of the implemented hot path. It must:

```text
identify platform/runtime/scenario/sample size
set reviewed p95 and bounded-size limits with explicit variance headroom
fail the benchmark command when a measured limit regresses
retain correctness invariants as hard zero/one/count limits
avoid comparing incompatible platforms
```

Absolute latency is a regression guard, not a claim that Host I/O or hardware
has been validated.

## 6. Allowed implementation surface

Expected bounded files:

```text
agent_harness/public_plugins/execution_supervisor/src/contracts.ts
agent_harness/public_plugins/execution_supervisor/src/event-store.ts
agent_harness/public_plugins/execution_supervisor/src/obligation-ledger.ts
agent_harness/public_plugins/execution_supervisor/src/index.ts
agent_harness/public_plugins/execution_supervisor/tests/* focused Phase 7 tests
agent_harness/public_plugins/execution_supervisor/benchmarks/phase7-efficiency.mjs
agent_harness/public_plugins/execution_supervisor/baselines/phase7-*.json
agent_harness/public_plugins/execution_supervisor/package.json
agent_harness/public_plugins/execution_supervisor/README.md

agent_harness/public_plugins/auto_governance_engine/src/service.ts
agent_harness/public_plugins/auto_governance_engine/tests/* focused Context reuse test

agent_harness/public_plugins/governance_runtime/src/service.ts
agent_harness/public_plugins/governance_runtime/tests/* focused hot-path invariant test

agent_harness/public_plugins/framework_efficiency_observer/tests/* focused report/equivalence test
.github/workflows/harness-public-baseline.yml
```

Not every listed file must change. Any new Manager, Store, Router, Gateway,
Registry, daemon or package requires a new context and explicit user approval.

## 7. Explicit non-goals

Do not implement:

```text
physical Event Store truncation, chain rewriting or lossy critical-event retention
a second Event Store, Compactor service, Context system, Router or metrics plane
an LLM/network call on ingest, replay, routing or metric collection
independent semantic calls by Managers
Observer-backed authorization, Evidence, completion or backpressure
Host-specific Codex/Claude/DSH SDK code
ATP/eTimer/project-specific policy
Phase 8 real Pilot or hardware execution
unrelated contract cleanup, dependency upgrades or repository formatting
```

## 8. Mandatory focused acceptance

At minimum mechanically prove:

```text
1000 ordinary matching read events produce no semantic call and no route refresh
repeated same resource/hash/disposition compacts to bounded refs plus accessCount=1000
different resource/hash/disposition receipts are not incorrectly merged
uninterrupted and cross-process replay produce identical compact status/decision
ordinary unchanged observations do not rebuild Context frames
mutation/error still follows the existing refresh path
incomplete external spans fail closed at the existing Bridge budget
duplicate eventId lookup preserves exact idempotency/conflict behavior
one Turn causes at most one normal Reflection
Observer disabled/enabled/broken produces the same supervision result
benchmark reports ingest p50/p95, Ledger transition p50/p95, replay duration,
event/projection/Context bytes, reroute count, semantic count and Reflection count
the Node 22 linux-x64 measurement remains within the frozen Phase 7 SLO profile
```

## 9. D-drive environment and validation ladder

All commands use this worktree explicitly:

```text
D:\lihuan\vibe_code\codex\et_harness_env\workspaces\phase7_efficiency_hardening
```

All HOME, temp, npm cache, metrics, benchmark output, state and logs remain under:

```text
D:\lihuan\vibe_code\codex\et_harness_env
```

Reuse the existing Node 22 runtime, npm cache and dependency trees. Dependency
manifests are compared to the exact Phase 6 base; unchanged signatures forbid
another install.

Validation ladder:

```text
edit loop       focused compaction/incremental/Observer tests only
checkpoint      affected package tests and builds
logic complete  only directly related Runtime/Observer integration
phase close     public boundary + 21 packages + 7 integrations exactly once
always          git diff --check and explicit status audit
```

No more than two large executions may run concurrently. Long commands write
logs to D drive and use low-frequency polling so Codex remains responsive.

## 10. Step exit condition

Source implementation begins only after this context is the sole committed
change and the worktree is clean. Phase 7 completes only after a completion
Handoff records the exact commits, commands, measurements, failures and known
limits. Phase 8 remains forbidden on this branch.
