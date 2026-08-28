# Execution Supervisor Phase 0 Repair Worklog v0.1

> Status: ACTIVE REPAIR RECORD
> Date: 2026-08-29
> Base branch: main
> Normative design: agent_harness/design/25_EXECUTION_SUPERVISOR_AND_OBLIGATION_LEDGER_V0_1.md
> Audit baseline: agent_harness/progress_context/20260829_EXECUTION_SUPERVISOR_MAIN_IMPLEMENTATION_AUDIT_V0_1.md

## Scope

This repair performs Phase 0 only. It does not implement Design 25 Phase 1 or later runtime behavior.

Authorized Phase 0 scope:

- one canonical Host-neutral contract model;
- deterministic contract hashing and validation;
- negative contract/protocol validation;
- performance baseline utilities and benchmark contract;
- truthful AUDIT/ENFORCE capability negotiation;
- no project/domain business logic;
- no Event Store, live Obligation Ledger Runtime, Host Bridge, Reflection integration, or Closure orchestration.

## Repair decision

The compact pre-PR12 Phase 0 core is the canonical source model:

- src/contracts.ts
- src/hash.ts
- src/validation.ts
- src/baseline.ts
- src/index.ts
- tests/contracts.test.ts
- tests/negative-contracts.test.ts
- tests/performance-baseline.test.ts
- tests/committed-baseline.test.ts

Files introduced later with incompatible Phase 0/runtime vocabularies are removed from the repair branch rather than silently retained as unused prototypes. Later phases will re-introduce durable event/replay/ledger logic from the latest canonical contracts only.

## Acceptance

Phase 0 can be marked PASS only after the repaired branch proves:

1. exactly one contract vocabulary compiles;
2. package `npm test` passes;
3. package `npm run build` passes;
4. package benchmark executes and its report validates;
5. public boundary check proves no ATP/ET6801/eTimer/MCU terms in public source;
6. normal public baseline passes;
7. GitHub Actions jobs actually execute steps; `runner_id=0` / `steps=[]` is NOT validation evidence.

Until those conditions are mechanically proven, status remains `REPAIR / NOT VERIFIED`.
