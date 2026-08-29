# Public Execution Supervisor

## Phase 3+4 status

This package provides the Phase 0 Host-neutral public contracts and deterministic validators, the bounded Phase 1 durable execution-event boundary, the Phase 2 deterministic Obligation Ledger projection, and the merged Phase 3+4 trusted external execution evaluation boundary:

```text
Task Supervision Contract
Execution Event Envelope
Obligation kinds, severities and states
Evidence Policy
Completion Policy and Completion Decision
Host Capability Contract and truthful AUDIT/ENFORCE negotiation
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
```

It intentionally does **not** register a Governance Runtime lifecycle service, call a model or network service, cryptographically authenticate a Host/provider/model, trigger Reflection/Knowledge/Context/Closure or modify another public package. Those capabilities belong to later implementation phases in the normative design.

The data-only Bridge validates the complete bundle before the first append and calls only the Ledger ingestion API. The Ledger consumes only events accepted by the Phase 1 Event Store. Assistant or user prose cannot set obligation state, rejected events cannot mutate the Ledger and duplicate events are idempotent. Expected and actual provider/model identity must match, but a data-only manifest does not cryptographically prove who emitted it; mechanical Host enforcement remains a later phase.

Evidence evaluation requires contributed provider, Context, revision, target, result and deterministic timestamp policy matches. `NOT_EXECUTED`, `NOT_VERIFIED` and `HISTORICAL` remain honest visible facts but cannot satisfy required PASS. A structured PASS claim without matching prior trusted Evidence creates a deterministic violation. Free-form text is never parsed into trusted Evidence.

Completion evaluation in this phase is pre-Closure only. It may return `READY_TO_CLOSE` after all execution-stage MUST obligations resolve, while explicitly reporting deferred Reflection/Knowledge/Context/Closure obligations. It never returns `COMPLETE`, creates a Closure Receipt or calls a Runtime lifecycle entrypoint.

Phase 2 v0.1 accepts one `WRITE_SCOPE` obligation. It computes scope from the contributed resource/path allowlist rather than trusting `MutationReceipt.scopeDecision`. `MOVE` and `COPY` fail closed because the v0.1 receipt cannot represent both endpoints.

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
COMPLETE is impossible without a Closure Receipt reference
Numeric performance SLOs remain unfrozen in Phase 0
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
```

## Commands

```bash
npm install --ignore-scripts
npm test
npm run build
npm run test:phase1-process
npm run benchmark -- --output ./baselines/phase0-performance-baseline.json
npm run benchmark:phase1
```

The Phase 0 benchmark publishes deterministic contract-validation measurements. The Phase 1 benchmark measures 1,000 durable appends plus paginated replay. Both are measurement artifacts, not frozen performance thresholds.
