# Public Execution Supervisor

## Phase 0 status

This package currently freezes only the Host-neutral public contracts and their deterministic validators:

```text
Task Supervision Contract
Execution Event Envelope
Obligation kinds, severities and states
Evidence Policy
Completion Policy and Completion Decision
Host Capability Contract and truthful AUDIT/ENFORCE negotiation
Phase 0 performance-baseline report
```

It intentionally does **not** yet register a Runtime service, persist events, maintain a live Obligation Ledger, evaluate claims, trigger Closure or modify another public package. Those capabilities belong to the later implementation phases in the normative design.

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
```

## Commands

```bash
npm install --ignore-scripts
npm test
npm run build
npm run benchmark -- --output ./baselines/phase0-performance-baseline.json
```

The benchmark publishes p50/p95/p99 measurements for deterministic Task Contract and Execution Event validation. It is a baseline artifact, not a frozen performance threshold.
