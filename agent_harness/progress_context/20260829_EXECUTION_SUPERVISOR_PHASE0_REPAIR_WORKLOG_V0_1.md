# Execution Supervisor Phase 0 Repair Worklog v0.1

> Status: **SOURCE REPAIRED / LOCAL MECHANICAL VALIDATION PASS / GITHUB CI BLOCKED**
> Date: 2026-08-29
> Repair branch: `feat/execution-supervisor-phase0-repair-v0.1`
> Repair PR: `#15`
> Normative design: `agent_harness/design/25_EXECUTION_SUPERVISOR_AND_OBLIGATION_LEDGER_V0_1.md`
> Audit baseline: `agent_harness/progress_context/20260829_EXECUTION_SUPERVISOR_MAIN_IMPLEMENTATION_AUDIT_V0_1.md`

## 1. Scope

This repair performs Design 25 Phase 0 only. It does not implement Phase 1 or any later runtime behavior.

Authorized Phase 0 scope:

- one canonical Host-neutral contract model;
- deterministic contract hashing and validation;
- negative contract/protocol validation;
- performance baseline utilities and benchmark contract;
- truthful AUDIT/ENFORCE capability negotiation;
- no project/domain business logic;
- no Event Store, persistent replay, live Obligation Ledger Runtime, Host Bridge, claim evaluator, Reflection integration, or Closure orchestration.

## 2. Repair decision and source result

The compact pre-PR12 Phase 0 core is the canonical source model:

```text
src/contracts.ts
src/hash.ts
src/validation.ts
src/baseline.ts
src/index.ts

tests/contracts.test.ts
tests/negative-contracts.test.ts
tests/performance-baseline.test.ts
tests/committed-baseline.test.ts
```

The later PR #12 experimental/runtime prototype files used a second incompatible contract vocabulary. They were removed from the repair branch rather than retained as hidden or unused prototypes.

Removed from Phase 0:

```text
schemas/execution-supervisor-v0.1.schema.json
src/canonical-json.ts
src/canonical.ts
src/completion.ts
src/event-batch.ts
src/event-chain.ts
src/factory.ts
src/limits.ts
src/phase0-runtime.ts
src/receipt-validation.ts

tests/completion.test.ts
tests/event-batch.test.ts
tests/event-chain.test.ts
tests/fixtures.ts
tests/performance.test.ts
tests/protocol.test.ts
tests/public-boundary.test.ts
tests/receipts.test.ts
tests/schema.test.ts
vitest.config.ts
```

Tree-level comparison against the pre-PR12 canonical Phase 0 commit `4d7c2ffcfe05f938ac309a98f80e37576a2db552` shows **no remaining Execution Supervisor package diff**. Only progress/audit documentation differs. This is the mechanical proof that the package has been restored to one contract model.

Repair source commit:

```text
5af47a8c481d6138b559299df9ed527f2ce8ca32
fix(supervisor): restore canonical Phase 0 contract core
```

## 3. Local isolated mechanical validation

Because GitHub Actions currently fails before runner allocation, the canonical package was reconstructed from the exact GitHub blobs in an isolated Linux environment and validated without modifying repository source.

Environment:

```text
Node: v22.16.0
Platform: linux x64
TypeScript available locally: 5.8.3
```

The repository package declares TypeScript `^6.0.3`; therefore the local TypeScript compile is strong source evidence but is not a substitute for the final repository CI environment.

### 3.1 Source compile

The exact canonical `src/*.ts` files compiled successfully with strict settings matching the repository `tsconfig.json` semantics.

Result:

```text
LOCAL_PHASE0_SOURCE_COMPILE=PASS
```

### 3.2 Exact repository test logic

The four repository Phase 0 test files were compiled and executed in isolation. A minimal local Vitest-compatible runner was used only because dependency installation is unavailable in the current execution environment; the test source and assertions are the repository tests themselves.

Results:

```text
contracts.test.ts              6 PASS / 0 FAIL
negative-contracts.test.ts     9 PASS / 0 FAIL
performance-baseline.test.ts   1 PASS / 0 FAIL
committed-baseline.test.ts     1 PASS / 0 FAIL
---------------------------------------------
TOTAL                          17 PASS / 0 FAIL
```

An additional deterministic smoke set exercised 22 core contract/fail-closed assertions:

```text
LOCAL_PHASE0_SMOKE=PASS assertions=22
```

Covered behavior includes:

- valid Task Supervision Contract;
- valid bounded Execution Event;
- Host capability validation;
- truthful ENFORCE/AUDIT negotiation;
- COMPLETE requires Closure identity;
- wrong schema / unknown fields rejected;
- duplicate obligations / dependency cycles rejected;
- untrusted Evidence policy rejected;
- payload-hash tampering rejected;
- invalid event kind / sequence rejected;
- hidden reasoning rejected;
- oversized payload rejected;
- fake frozen Phase 0 SLOs rejected;
- public source free of ATP / ET6801 / eTimer / MCU terms.

### 3.3 Full Phase 0 benchmark

The exact repository benchmark `benchmarks/phase0-baseline.mjs` executed with its default full sample size:

```text
warmupIterations = 2000
sampleIterations = 10000
```

Measured on Node v22.16.0 / Linux x64:

```text
Task Contract validation
  input       1765 bytes
  p50         26.184 us
  p95         59.639 us
  p99         154.781 us
  mean        33.616 us
  max         2074.246 us

Execution Event validation
  input       745 bytes
  p50         6.241 us
  p95         8.114 us
  p99         43.267 us
  mean        8.044 us
  max         848.535 us
```

The generated report passed `validatePerformanceBaselineReport()` and preserved the Phase 0 invariants:

```text
noSemanticCallOnHotPath          true
noFullRerouteForOrdinaryRead     true
maxUnifiedReflectionsPerTurn     1
maxEventPayloadBytes             65536
maxTaskContractBytes             524288
thresholdsFrozen                 false
```

The committed reviewed baseline `baselines/phase0-ci-linux-x64-node22.json` also passed the current validator.

## 4. GitHub Actions blocker

PR #15 triggered the normal Phase 0 workflow. GitHub created the workflow run but did not allocate a runner or execute any step.

Latest observed run:

```text
run: 33220323233
workflow: Execution Supervisor Phase 0 Contracts
job: contracts-and-baseline
conclusion: failure
steps: []
```

A manual rerun was requested. The rerun again ended before runner allocation with `steps=[]`.

The same zero-step pattern also affects the repository public-baseline workflow. Therefore this is not evidence that the repaired source failed tests or build; it is an external GitHub Actions execution blocker.

This blocker must remain visible. We do **not** convert local validation into a claim that GitHub CI passed.

## 5. Phase 0 status

Current truthful status:

```text
Canonical single contract model       PASS
Conflicting PR12 prototypes removed   PASS
Source tree repair                    PASS
Local strict source compile           PASS (TS 5.8.3 isolation)
Repository test logic                 PASS (17/17 isolation)
Additional fail-closed smoke          PASS (22 assertions)
Full benchmark                        PASS (2 x 10,000 samples)
Committed baseline validation         PASS
Public/domain boundary                PASS
GitHub Actions runner execution       BLOCKED / NOT EXECUTED
Exact repository npm/Vitest/TS6 CI    BLOCKED BY RUNNER
Phase 0 final CI acceptance           BLOCKED
Design 25 Phase 1                     NOT STARTED
```

## 6. Merge and next-step rule

PR #15 is the only Phase 0 repair PR. It must not be confused with a Phase 1 implementation.

The source repair is ready, but **Phase 0 must not be declared fully accepted until GitHub Actions actually executes the repository test/build/benchmark/public-baseline steps successfully**.

No Design 25 Phase 1 work may begin from PR #13 or from the removed prototypes. When Phase 0 receives final mechanical acceptance, Phase 1 must start from the then-current clean `main` and implement only:

```text
persistent execution event store
+ sequence/hash/idempotency enforcement
+ Runtime/Task/Turn binding persistence
+ cross-process replay cursor
```
