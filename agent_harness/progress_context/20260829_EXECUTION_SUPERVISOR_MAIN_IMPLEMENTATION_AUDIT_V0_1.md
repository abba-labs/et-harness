# Execution Supervisor Main Implementation Audit v0.1

> Status: **MECHANICAL / SOURCE-BASED AUDIT BASELINE**  
> Date: 2026-08-29  
> Repository: `abba-labs/et-harness`  
> Audited branch: `main`  
> Audited HEAD: `0474cea6da2b9618fd40a0167099f2c8477a0e3c`  
> Normative design: `agent_harness/design/25_EXECUTION_SUPERVISOR_AND_OBLIGATION_LEDGER_V0_1.md`  
> Purpose: stop parallel drift, identify what is truly implemented, and define the only safe next step.

---

# 0. Executive conclusion

The previous development is **not all wrong**. The architecture direction in Design 25 remains valid, and a useful Phase 0 contract core exists.

However, the current `main` branch **must not be treated as a validated Phase 0 PASS**.

The audit found three separate facts:

1. A small, internally aligned Phase 0 contract/validation core already existed before PR #12.
2. PR #12 added a second set of Phase 0/runtime prototype files that use a different contract/type model and are not aligned with the canonical exported contract surface.
3. GitHub Actions did not actually execute the required tests/builds before or after PR #12 was merged; the jobs failed before runner allocation with zero executed steps.

Therefore the current source state is:

```text
Design 25 direction                         VALID / KEEP
Pre-PR12 contract + validation core         KEEP / NEEDS REAL VALIDATION
PR12 extra runtime/protocol prototypes      INCONSISTENT / MUST CLEAN UP
PR13 Phase 1 Contract Builder               OBSOLETE AS PHASE 1
Current Phase 0 overall status              FAIL / NOT VERIFIED
Current Phase 1 overall status              NOT IMPLEMENTED
Overall Execution Supervisor                INCOMPLETE
```

The immediate task is **not** to continue Phase 1 development.

The immediate task is:

```text
repair current main to one canonical Phase 0 contract model
→ make the package build/test/benchmark cleanly
→ obtain mechanical PASS evidence
→ only then implement Design 25 Phase 1: persistent event store + replay
```

---

# 1. Canonical design phase definitions

Design 25 freezes the following sequence:

```text
Phase 0  Freeze contracts and baselines
Phase 1  Persistent event store and replay
Phase 2  Obligation Ledger
Phase 3  External Agent Response/Event Bridge
Phase 4  Claim, Evidence and Completion evaluator
Phase 5  Reflection / Knowledge / Context / Closure integration
Phase 6  Host/Tool enforcement profiles
Phase 7  Efficiency hardening
Phase 8  Real ATP Pilot rerun
```

This sequence is normative.

A future implementation must not rename or reinterpret these phases merely because another implementation order is easier.

In particular:

> **A “Contract Builder” is not Design 25 Phase 1.**

Task Supervision Contract semantics belong to the Phase 0 contract boundary. Design 25 Phase 1 begins only after Phase 0 is validated and is specifically the durable execution-event store / replay layer.

---

# 2. Exact current `main` state

## 2.1 Current HEAD

```text
main HEAD:
0474cea6da2b9618fd40a0167099f2c8477a0e3c

commit:
Merge pull request #12 from abba-labs/feat/public-execution-supervisor-phase0-v0.1
feat: freeze Execution Supervisor Phase 0 contracts
```

PR #12 was merged into `main`.

## 2.2 GitHub Actions did not validate the merge

The post-merge `Harness Public Baseline` run on the exact `main` HEAD failed before any runner executed the job:

```text
run: 33192376336
head: 0474cea6da2b9618fd40a0167099f2c8477a0e3c
job: repository-boundary
conclusion: failure
runner_id: 0
steps: []
```

The downstream jobs were skipped.

The PR #12 head runs show the same failure pattern. Therefore no mechanical evidence currently proves that:

```text
npm test
npm run build
npm run benchmark
Harness Public Baseline
```

passed for the merged source.

This is a CI/runner-start failure, not proof that the source tests failed. But it also means the source cannot be called validated.

---

# 3. The useful canonical Phase 0 core

Before the PR #12 merge, commit:

```text
4d7c2ffcfe05f938ac309a98f80e37576a2db552
```

already contained this compact public source surface:

```text
agent_harness/public_plugins/execution_supervisor/src/
  baseline.ts
  contracts.ts
  hash.ts
  index.ts
  validation.ts
```

The current `index.ts` still exports exactly this surface:

```text
baseline
contracts
hash
validation
```

The package README also states that Phase 0 currently freezes only:

```text
Task Supervision Contract
Execution Event Envelope
Obligation kinds/severities/states
Evidence Policy
Completion Policy / Completion Decision
Host Capability Contract
AUDIT/ENFORCE negotiation
performance-baseline report
```

and explicitly says Phase 0 does **not** yet provide:

```text
Runtime service
event persistence
live Obligation Ledger
claim evaluation
Closure triggering
```

This compact contract/validator boundary is aligned with Design 25 Phase 0 and should be preserved as the starting point for repair.

It is still `NOT VERIFIED` until real tests/builds run.

---

# 4. Current `main` source inconsistency introduced by the merged Phase 0 branch

PR #12 added additional files such as:

```text
canonical-json.ts
canonical.ts
completion.ts
event-batch.ts
event-chain.ts
factory.ts
limits.ts
phase0-runtime.ts
receipt-validation.ts
```

plus additional tests and schema files.

These are not simply private helper implementations of the exported canonical contracts. Several of them use a different incompatible type model.

## 4.1 Canonical `contracts.ts` model

Current exported `contracts.ts` defines names such as:

```text
TASK_SUPERVISION_CONTRACT_SCHEMA
EXECUTION_EVENT_SCHEMA
TaskSupervisionContractV01
ExecutionEventEnvelopeV01
ObligationDefinitionV01
EvidencePolicyV01
CompletionDecisionV01
HostCapabilityContractV01
```

## 4.2 `event-chain.ts` uses another model

`event-chain.ts` imports:

```text
ExecutionEvent
TaskSupervisionContract
```

and reads fields such as:

```text
event.previousEventHash
event.eventHash
```

Those types/fields are not the canonical exported Phase 0 contract surface above.

## 4.3 `event-batch.ts` uses another model

`event-batch.ts` imports:

```text
EXECUTION_SUPERVISOR_CONTRACT_VERSION
ExecutionEventV01
SupervisionIdentityV01
```

and expects nested structures such as:

```text
event.identity
event.integrity.contractHash
event.integrity.previousEventHash
event.integrity.eventHash
```

Those symbols are not defined by the canonical exported `contracts.ts` model.

## 4.4 `phase0-runtime.ts` uses another model

`phase0-runtime.ts` imports symbols such as:

```text
COMPLETION_DECISION_SCHEMA
EXECUTION_SUPERVISOR_CONTRACT_VERSION
OBLIGATION_LEDGER_SCHEMA
SUPERVISION_VIOLATION_SCHEMA
ExecutionEventV01
ObligationLedgerSnapshotV01
SupervisionIdentityV01
```

which are not provided by the canonical current `contracts.ts` surface.

## 4.5 `completion.ts` uses another model

`completion.ts` imports symbols such as:

```text
COMPLETION_EVALUATION_SCHEMA
EXECUTION_SUPERVISOR_CONTRACT_VERSION
ObligationLedger
ObligationSpec
TaskSupervisionContract
ViolationRecord
```

again using a different contract family.

## 4.6 Why these files cannot simply be ignored

The package TypeScript configuration includes:

```text
src/**/*.ts
```

Therefore `npm run build` compiles every TypeScript file in `src/`, not only modules exported from `index.ts`.

So the extra incompatible files make the current package source tree internally inconsistent even though `index.ts` does not export them.

The current `main` package must therefore be classified:

```text
SOURCE PRESENT
but
BUILD NOT PROVEN
and
STATIC CONTRACT CONSISTENCY = FAIL
```

until this is repaired.

---

# 5. PR #13 audit

PR #13:

```text
branch:
feat/public-execution-supervisor-phase1-contract-builder-v0.1

head:
307eeb4c3c1f546d203f7b9e5c09465ca541a488
```

contains useful ideas:

```text
ProjectSupervisionContribution
Task Supervision Contract builder
mandatory public lifecycle obligations
provenance checks
AUDIT/ENFORCE capability checks
negative tests
```

However it must not be merged as current Phase 1 for two reasons.

## 5.1 Wrong phase definition

Design 25 Phase 1 is:

```text
persistent event store
sequence/hash/idempotency
Runtime/Task/Turn binding persistence
cross-process replay cursor
```

PR #13 instead implements a Contract Builder.

That is a direction/phase mismatch.

## 5.2 It was created before the Phase 0 merge was finalized

The branch is based on the older main lineage and diverged from current `main`.

It also uses the alternate contract vocabulary seen in the incompatible Phase 0 prototypes.

Therefore PR #13 should be treated as:

```text
DESIGN/IMPLEMENTATION REFERENCE ONLY
NOT A MERGE CANDIDATE
```

Any useful business-neutral ideas may be reimplemented later against the one canonical contract model.

---

# 6. Design 25 × current `main` implementation matrix

Legend:

```text
PASS            mechanically verified and usable
PARTIAL         useful implementation exists but scope is incomplete
SOURCE_ONLY     code/prototype exists but is not validated/canonical
NOT_IMPLEMENTED required implementation does not exist on canonical main
BLOCKED         cannot progress safely because an upstream phase is invalid
```

| Design 25 capability | Current evidence | Status | Decision |
|---|---|---|---|
| Public Host-neutral contract package | `contracts.ts`, `validation.ts`, `hash.ts`, `baseline.ts` | PARTIAL | Keep canonical core; validate after cleanup |
| Task Supervision Contract schema | Canonical v0.1 contract exists | PARTIAL | Keep |
| Execution Event Envelope | Canonical v0.1 envelope exists | PARTIAL | Keep; choose one hash/chain representation before Phase 1 |
| Obligation kinds/states | Canonical types exist | PARTIAL | Keep |
| Evidence Policy contract | Canonical type exists | PARTIAL | Keep |
| Completion Decision contract | Canonical type exists | PARTIAL | Keep contract only |
| Host Capability / AUDIT vs ENFORCE | Canonical contract + validation support exists | PARTIAL | Keep contract; runtime profile still absent |
| Phase 0 performance baseline utility | `baseline.ts` + benchmark script/workflow | SOURCE_ONLY | Benchmark did not mechanically run |
| Phase 0 build/test evidence | GitHub runner never started | BLOCKED | Must obtain real PASS before Phase 1 |
| Event hash-chain prototypes | `event-chain.ts`, `event-batch.ts` | SOURCE_ONLY | Incompatible with canonical contracts; do not treat as implementation |
| Persistent Execution Event Store | no canonical durable store | NOT_IMPLEMENTED | Design 25 Phase 1 |
| Durable Runtime/Task/Turn binding store | no Supervisor state store | NOT_IMPLEMENTED | Design 25 Phase 1 |
| Cross-process replay cursor | prototypes only, not durable/integrated | NOT_IMPLEMENTED | Design 25 Phase 1 |
| Governance Runtime cross-process rehydrate | `main` explicitly says host-independent rehydration is not implemented | NOT_IMPLEMENTED | Must be implemented after/with Phase 1 integration |
| Structured Project supervision contribution | PR #13 prototype only | NOT_IMPLEMENTED on canonical main | Design 25 Phase 2 input contract; reimplement after Phase 1 |
| Live Obligation Ledger | incompatible prototype helpers only | NOT_IMPLEMENTED | Design 25 Phase 2 |
| Obligation dependency/state engine | no canonical engine | NOT_IMPLEMENTED | Phase 2 |
| Violation evaluator | prototype records only | NOT_IMPLEMENTED | Phase 2/4 according to responsibility split |
| External Agent Response/Event Bridge | no canonical bridge | NOT_IMPLEMENTED | Phase 3 |
| Current ChatGPT event bundle ingestion | no canonical runner | NOT_IMPLEMENTED | Phase 3 |
| Claim vs trusted Evidence evaluator | incompatible prototype only | NOT_IMPLEMENTED | Phase 4 |
| Stale Evidence / provider policy runtime | contracts only | NOT_IMPLEMENTED | Phase 4 |
| Deterministic completion authority | contracts + incompatible prototypes | NOT_IMPLEMENTED | Phase 4 |
| Unified Reflection | existing Governance Runtime/Kernel capability | PARTIAL OUTSIDE SUPERVISOR | Keep existing implementation; later wire Supervisor to it |
| Knowledge forced classification | existing Runtime/Closure capability | PARTIAL OUTSIDE SUPERVISOR | Keep; not yet triggered from Supervisor state |
| Context Closure / 8/8 Closure | existing Kernel/Closure modules | PARTIAL OUTSIDE SUPERVISOR | Keep; integration is Design 25 Phase 5 |
| Supervisor → Reflection/Closure integration | none | NOT_IMPLEMENTED | Phase 5 |
| AUDIT Host profile | contract-level only | PARTIAL | Phase 6 runtime/adapter work remains |
| ENFORCE Tool Gateway profile | not implemented | NOT_IMPLEMENTED | Phase 6 |
| Event compaction | no canonical implementation | NOT_IMPLEMENTED | Phase 7 |
| Incremental obligation evaluation | no canonical implementation | NOT_IMPLEMENTED | Phase 7 after evaluator exists |
| Efficiency SLO / regression gate | workflow exists but no successful benchmark evidence | NOT_IMPLEMENTED | Phase 7, after Phase 0 baseline is real |
| ATP frozen eTimer rerun | not run through Supervisor | NOT_IMPLEMENTED | Phase 8 |
| Follow-up Context/Knowledge reuse proof | not run | NOT_IMPLEMENTED | Phase 8 final acceptance |

---

# 7. What is definitely worth keeping

The audit does **not** recommend discarding the existing Harness architecture.

Keep:

```text
Design 25
Governance Runtime lifecycle ownership
Governance Kernel
Unified Reflection
8/8 Closure
Context / Knowledge / Evidence / Gate Managers
Project Context Contribution design
canonical Phase 0 contract vocabulary
canonical validation/hashing/baseline utilities
AUDIT vs ENFORCE truth boundary
```

These remain aligned with the product goal:

> General Agent intelligence stays in the model; project truth stays in the Project Plugin; deterministic governance and completion authority stay in the public Harness.

---

# 8. What must be cleaned up before any new feature work

The current `main` must first return to a single contract model.

## 8.1 Preserve the canonical contract surface

Use the currently exported Phase 0 surface as the starting authority:

```text
baseline.ts
contracts.ts
hash.ts
validation.ts
index.ts
```

The exact contract can still be corrected through a deliberate v0.1 cleanup, but there must be only one vocabulary and one structure.

## 8.2 Quarantine/remove incompatible prototypes

The following current files must not remain compiled against incompatible contract types:

```text
canonical-json.ts
canonical.ts
completion.ts
event-batch.ts
event-chain.ts
factory.ts
limits.ts
phase0-runtime.ts
receipt-validation.ts
```

For each file choose one action:

```text
DELETE as obsolete prototype
or
REWRITE against canonical contracts
```

Do not keep two parallel contract families.

Associated tests must be treated the same way.

## 8.3 Re-run Phase 0 from zero

Required mechanical evidence:

```text
npm install --ignore-scripts
npm test
npm run build
npm run benchmark
Execution Supervisor Phase 0 workflow PASS
Harness Public Baseline PASS
```

A job with `runner_id=0` and `steps=[]` is not a test result.

Phase 0 is PASS only after real commands execute.

---

# 9. Correct next implementation sequence

After cleanup and real Phase 0 PASS:

```text
Phase 1A
Persistent append-only event store

Phase 1B
sequence + eventId + hash + idempotency enforcement

Phase 1C
persistent Runtime/Project/Task/Turn identity binding

Phase 1D
cross-process replay cursor + crash/restart test

Phase 1E
Governance Runtime rehydrate supervised OPEN Turn
```

Phase 1 acceptance remains exactly Design 25:

```text
process A opens Turn
process B ingests events
process C rehydrates and sees identical event/ledger state
out-of-order/tampered events fail closed
```

Do **not** start the Obligation Ledger engine, External Chat Bridge or ATP task before that passes.

---

# 10. Efficiency rule for the resumed development

The efficiency problem must be solved by implementation discipline, not by skipping governance.

For all future Phase 1+ work:

```text
one phase = one small public responsibility
one canonical contract model
one clean branch from latest validated main
focused unit/negative tests first
no ATP/eTimer code in public package
no LLM/network/project scan on hot path
no full reroute on ordinary execution events
no new phase until previous phase has real PASS evidence
```

The biggest current efficiency loss came from parallel source variants and advancing before the previous gate was mechanically closed.

Preventing that is itself an efficiency improvement.

---

# 11. Branch/PR decision

## PR #12

Already merged. Do not pretend it is validated.

Repair `main` through a new cleanup PR rather than rewriting history.

## PR #13

Decision:

```text
CLOSE AS OBSOLETE / NOT MERGEABLE
```

Reason:

```text
wrong Design 25 phase
stale base
alternate contract vocabulary
Phase 0 not yet validated
```

The branch may remain temporarily for reference until the cleanup is complete; do not merge or rebase it into the new implementation.

---

# 12. New canonical status after this audit

```text
Design 25                                             FROZEN / VALID DIRECTION
Execution Supervisor Phase 0 canonical contract core  PRESENT
Execution Supervisor Phase 0 source consistency       FAIL
Execution Supervisor Phase 0 mechanical CI            NOT EXECUTED
Execution Supervisor Phase 0 overall                   FAIL / INCOMPLETE
Execution Supervisor Phase 1                           NOT IMPLEMENTED
Execution Supervisor Phase 2                           NOT IMPLEMENTED
Execution Supervisor Phase 3                           NOT IMPLEMENTED
Execution Supervisor Phase 4                           NOT IMPLEMENTED
Execution Supervisor Phase 5                           NOT INTEGRATED
Execution Supervisor Phase 6                           CONTRACT-ONLY / INCOMPLETE
Execution Supervisor Phase 7                           BASELINE-ONLY / UNVERIFIED
Execution Supervisor Phase 8                           NOT EXECUTED
PR #13                                                 OBSOLETE
```

---

# 13. Immediate next action

Only one next task is authorized:

> **Create a clean Phase 0 repair branch from current `main`, remove/rewrite the incompatible alternate implementation until `@agent-harness/execution-supervisor` has one canonical contract model and real `test + build + benchmark + public baseline` PASS evidence.**

After that, and only after that, start Design 25 Phase 1 persistent event store and replay.

No eTimer business work, Mailbox expansion, Obligation Ledger implementation, Host Bridge or Closure integration should start before the repaired Phase 0 gate is green.

---

# 14. One-line recovery invariant

> **Do not continue from the latest-looking code; continue from the latest mechanically validated canonical contract state.**
