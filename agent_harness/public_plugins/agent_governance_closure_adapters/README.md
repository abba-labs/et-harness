# Public Agent Governance Closure Adapters v0.1

Step 5 connects the Kernel Closure Coordinator to **all eight fixed Mandatory Closure Modules** while keeping Manager/project dependencies outside the Kernel package.

Registered mandatory modules:

```text
context-closure
knowledge-closure
experience-memory-closure
architecture-closure
rules-closure
evidence-state-closure
working-set-closure
obligation-gate-reconcile
```

## Semantic boundary

The Agent remains the semantic judge. Adapters only execute the structured Unified Reflection result.

They do not:

- auto-PASS semantic review or Gates;
- auto-promote Knowledge to `VALIDATED`;
- directly rewrite formal Architecture or Rule resources;
- guess Project/Public scope or Knowledge taxonomy categories.

## Context and Working Set

`context-closure` synchronizes Context Task/Progress Ledger only. `working-set-closure` independently reconciles the Working Set, so both mandatory responsibilities have separate receipts and replay behavior.

Both currently require a BOUND project because Context Manager v0.2 has no public/unbound Context store. Replays compare current state first and avoid another write when the desired state is already present.

## Knowledge and Experience

Knowledge placement remains explicit. A Knowledge Reflection Candidate must include category references in `relatedRefs`:

```text
knowledge-category://project/<categoryId>
knowledge-category://public/<categoryId>
```

`PROJECT` requires the project category, `PUBLIC` requires the public category, and `BOTH` requires both. Missing or inactive categories BLOCK before Knowledge writes start. Knowledge writes create only `CANDIDATE` leaves and never auto-promote to `VALIDATED`.

Experience Closure currently supports evidence-backed `PROJECT` candidates. `PUBLIC` / `BOTH` Experience and `UNBOUND` Experience remain fail-closed because Experience / Memory Manager v0.2 has no global store.

## Architecture and Rules

Formal Architecture Navigator and Rule Manager remain read-only during Turn Closure. Reflection changes are persisted to a separate runtime Change Candidate Store:

```text
architecture-change://project/<projectId>/ARCHC-...
architecture-change://public/ARCHC-...
rule-change://project/<projectId>/RULEC-...
rule-change://public/RULEC-...
```

`BOTH` creates one project candidate and one public candidate. Stable semantic fingerprints make replay idempotent. Promotion into formal Architecture/Rules is deliberately outside Turn Closure.

## Evidence / State

Evidence Reflection creates project `INFO` Evidence only. It never creates `PASS` Evidence. A stable closure fingerprint is stored in Evidence metadata so replay reuses an existing record rather than appending another one.

Public/unbound Evidence remains fail-closed until a global Evidence store exists.

## Obligation / Gate Reconcile

The Adapter persists current open obligations in governed task State and extracts explicit `Gxxx...` references for Gate evidence reconciliation.

A Reflection may keep a MUST Gate open without blocking Turn Closure, but it **cannot claim the Gate is resolved unless Gate Manager can find real PASS Evidence**. A false resolution returns `BLOCKED` before obligation State changes.

## Step 5 boundary

All 8/8 fixed Mandatory Closure Module IDs are now registered. This makes a complete BOUND-project Turn Closure mechanically possible when:

- Context task bootstrap already exists;
- Reflection does not request unsupported public/unbound stores;
- required Knowledge categories are explicit and valid;
- project Experience candidates have Evidence;
- any claimed resolved MUST Gate has real PASS Evidence.

The next architectural step is the Harness Lifecycle Adapter and a real pure-analysis Pilot that automatically drives `TURN_START -> Reflection -> Closure -> Receipt -> TURN_CLOSED` without relying on a human to call the Kernel APIs manually.
