# Public Execution Supervisor

## Phase 7 status

This package provides the Phase 0 Host-neutral public contracts and deterministic validators, the bounded Phase 1 durable execution-event boundary, the Phase 2 deterministic Obligation Ledger projection, the merged Phase 3+4 trusted external execution evaluation boundary, Phase 5 lifecycle receipts, the Phase 6 deterministic mutation preflight used by the public Runtime, and the Phase 7 bounded/incremental projection plus regression benchmark:

```text
Task Supervision Contract
Execution Event Envelope
Obligation kinds, severities and states
Evidence Policy
Completion Policy and Completion Decision
Host Capability Contract and truthful AUDIT/ENFORCE negotiation
Exact-key mutation intent and deterministic WRITE_SCOPE preflight
Phase 0 performance-baseline report
Immutable Task Contract and execution identity binding
Append-only canonical JSONL event records
Full-envelope idempotency and sequence/hash-chain integrity
Bounded cursor replay across sequential process handoff
Structured REQUIRED_RESOURCE and WRITE_SCOPE contribution validation
Deterministic PENDING / BLOCKED / SATISFIED / VIOLATED transitions
Dependency blocking and unblocking without automatic satisfaction
Out-of-scope mutation violation records
Immutable status query and replay-equivalent reconstruction
Strict external Agent request and response manifests
Whole-bundle prevalidation before durable event ingestion
Exact visible request/response content and identity binding
Structured claim records without free-form prose parsing
Trusted Evidence Policy matching with deterministic stale checks
SOURCE_DISPOSITION / OUTPUT / VALIDATION / CLAIM_EVIDENCE / RULE_COMPLIANCE evaluation
Unsupported-PASS and trusted-validation-failure violation records
IN_PROGRESS / BLOCKED / FAILED / READY_TO_CLOSE pre-Closure decisions
Bounded repeated-resource projections with deterministic access counts
Incremental Ledger synchronization and indexed duplicate/resource lookup
Node 22 linux-x64 Phase 7 Store/Ledger SLO profile and CI report
```

It intentionally does **not** register a Governance Runtime lifecycle service, call a model or network service, cryptographically authenticate a Host/provider/model or own a Host tool boundary. Runtime lifecycle and mechanical interception remain in the public Governance Runtime and its single Governed Tool Gateway.

The data-only Bridge validates the complete bundle before the first append and calls only the Ledger ingestion API. The Ledger consumes only events accepted by the Phase 1 Event Store. Assistant or user prose cannot set obligation state, rejected events cannot mutate the Ledger and duplicate events are idempotent. Expected and actual provider/model identity must match, but a data-only manifest does not cryptographically prove who emitted it. Mechanical ENFORCE is claimed only when the Runtime binds a capable Host profile and the existing Tool Gateway owns preflight.

Phase 7 compacts only the public status projection used for bounded progress and
Context deltas. Lifecycle readiness keeps the published Phase 6 authority
identity: at the close path, the Ledger replays the bounded canonical Event
Store into the legacy authority projection once and caches that receipt for the
exact cursor. Compact counters and truncated representative refs therefore do
not silently invalidate an already persisted Reflection/Closure binding.

Evidence evaluation requires contributed provider, Context, revision, target, result and deterministic timestamp policy matches. `NOT_EXECUTED`, `NOT_VERIFIED` and `HISTORICAL` remain honest visible facts but cannot satisfy required PASS. A structured PASS claim without matching prior trusted Evidence creates a deterministic violation. Free-form text is never parsed into trusted Evidence.

Completion evaluation in this phase is pre-Closure only. It may return `READY_TO_CLOSE` after all execution-stage MUST obligations resolve, while explicitly reporting deferred Reflection/Knowledge/Context/Closure obligations. It never returns `COMPLETE`, creates a Closure Receipt or calls a Runtime lifecycle entrypoint.

## Minimal degraded-mode rule

When an external/web Host cannot reach the Framework entry path itself (for example health/capability/bootstrap transport failure), it should surface `GOVERNANCE_DEGRADED` through `createGovernanceDegradedNotice()`. Useful read-only analysis may continue, but that work is not represented as Framework-governed completion and `formalPassCloseAllowed` remains `false`.

An Agent statement such as `PASS`, `CLOSE` or “task complete” is never final authorization. Formal completion remains owned by the existing Framework lifecycle authority: the Kernel/Closure binding must be verified, durable lifecycle finalization must exist, and only then may the Ledger report `COMPLETE`. This adds no new normal lifecycle state and no per-action Gate.

Phase 2 v0.1 accepts one `WRITE_SCOPE` obligation. It computes scope from the contributed resource/path allowlist rather than trusting `MutationReceipt.scopeDecision`. `MOVE` and `COPY` fail closed because the v0.1 receipt cannot represent both endpoints.

Phase 6 preflight reuses exactly that WRITE_SCOPE rule. A mutation intent accepts only `resourceId`, optional `path` and `action`; Agent-supplied scope decisions or extra fields fail closed. Preflight is deterministic and does not mutate Ledger state.

The file store requires a caller-controlled absolute directory and separates create from open. It supports one active writer with sequential process handoff. It detects a stale instance when the durable files change, but does not claim concurrent multi-writer coordination, crash atomicity, power-loss durability or protection from an attacker with write access.

The hash chain detects mutation, deletion or reordering inside the retained history. Under the frozen no-authoritative-cursor design, replacing the whole event log with an earlier complete valid prefix cannot be distinguished from a store that legitimately stopped at that prefix; stronger rollback detection requires a separately trusted external checkpoint. Replay equivalence in this phase means the exact event projection and sequence, not identical wall-clock-derived state hashes across independently created stores.

## Invariants

```text
No project/domain business terms in public contract source
No semantic model call in contract validation
No routing, Context or Knowledge dependency in the event hot path
Canonical payload hashing and bounded payload/contract sizes
Fail-closed schema validation
ENFORCE is never claimed when the Host cannot intercept and preflight tools
Preflight and post-execution evaluation use the same frozen Ledger contract
COMPLETE is impossible without a Closure Receipt reference
Numeric performance SLOs remain unfrozen in Phase 0
Phase 7 SLOs apply only to the exact Node 22 linux-x64 1,000-event profile
Store size, event count and replay page size are bounded by validated caller configuration
Corrupt, truncated, non-canonical or wrongly bound stores fail closed
Required resources are satisfied only by exact, allowlisted `FOUND` receipts
Ledger replay is deterministic and produces no duplicate violations
Ordinary event ingestion does not build a full status snapshot
Bridge validation performs no model or network call
Invalid bundles append no prefix; runtime append failures report the exact durable prefix
Evidence freshness uses accepted event time, never wall-clock time
Provider ID and kind use conjunctive policy matching when both are declared
Agent claims never become Evidence by self-certification
Pre-Closure evaluation never returns COMPLETE
Compact status metadata does not redefine the Phase 6 lifecycle readiness hash
```

## Commands

```bash
npm install --ignore-scripts
npm test
npm run build
npm run test:phase1-process
npm run benchmark -- --output ./baselines/phase0-performance-baseline.json
npm run benchmark:phase1
PHASE7_TMP_ROOT=/absolute/temp/root npm run benchmark:phase7 -- --slo baselines/phase7-ci-linux-x64-node22-slo.json --output /absolute/report.json
```

The Phase 0 benchmark publishes deterministic contract-validation measurements. The Phase 1 benchmark measures 1,000 durable appends plus paginated replay. Those two remain measurement artifacts, not frozen performance thresholds. The separate Phase 7 benchmark enforces the exact environment/scenario SLO while preserving canonical events and measuring compact projection size.
