# Public Execution Supervisor

## Phase 2 status

This package provides the Phase 0 Host-neutral public contracts and deterministic validators, the bounded Phase 1 durable execution-event boundary, and the Phase 2 deterministic Obligation Ledger projection:

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
```

It intentionally does **not** register a Governance Runtime lifecycle service, evaluate claims or Completion, bridge a Host, authenticate receipt providers, trigger Reflection/Knowledge/Closure or modify another public package. Those capabilities belong to later implementation phases in the normative design.

The Ledger consumes only events accepted by the Phase 1 Event Store. Assistant or user messages cannot set obligation state, rejected events cannot mutate the Ledger and duplicate events are idempotent. A provider ID must match the Project-contributed allowlist, but Phase 2 does not prove who emitted the receipt; provider authentication remains a later Host/Event Bridge responsibility.

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
