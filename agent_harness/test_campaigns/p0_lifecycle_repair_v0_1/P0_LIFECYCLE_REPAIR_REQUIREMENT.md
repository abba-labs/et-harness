# ET Harness P0 Lifecycle Repair Requirement V0.1

**Status**: FROZEN BEFORE PRODUCT REPAIR  
**Base branch**: `development/et-harness-mainline-v0.1`  
**Base SHA**: `41784d8cfc02ed02a057aa0c37320cf8ad529f9b`  
**Repair branch**: `fix/p0-lifecycle-repair-v0.1`  
**Source analysis**: `agent_harness/validation_analysis/rounds/2026-09-02_et6801_srpwm_behavioral_v1/FINAL_ANALYSIS.md`  
**Mechanical Evidence**: `fea9e454d100eaf175bfa8f9ed0589a104488d15`

## 1. Frozen boundaries

This repair is limited to public Framework lifecycle owners. It must not:

- change ATP Project Plugin Architecture, Rules, Knowledge, Gates, Validation commands or SRPWM semantics;
- change the D-drive machine environment, Node, Toolchain, Launcher, active Runtime release or machine state;
- add a second Runtime, Ledger, Event Store, Context Store, Knowledge Store or completion authority;
- add a watcher, daemon, polling loop, Windows Service or new MCP tool;
- weaken WRITE_SCOPE, trusted Evidence, Project Admission, Required Read or completion checks;
- mix route/knowledge quality optimization, Observation durability, SDK repair or hardware work into P0.

Priority remains:

```text
reliable > stable > lightweight > extensible
```

## 2. R1 — Validation current state and freshness

### Required behavior

1. Every explicit `harness_checkpoint` reruns every frozen `VALIDATION` obligation after required reads are satisfied.
2. A trusted FAIL remains append-only Evidence and makes the current validation state `VIOLATED`.
3. A later trusted PASS for the same `validationId + targetIdentity` may make only that validation obligation currently `SATISFIED`.
4. Generic safety violations, including WRITE_SCOPE, are not recoverable through validation PASS.
5. Before the first successful `harness_complete`, the Gateway performs one final trusted checkpoint so an old PASS cannot silently authorize newer workspace content.
6. Completion replay of an already COMPLETE task does not rerun validators or append new events.

### Acceptance

- FAIL -> correction -> same-Turn checkpoint -> PASS;
- PASS -> later validator FAIL -> current VIOLATED;
- PASS -> relevant file mutation -> next checkpoint actually reruns;
- stale PASS -> direct complete is rejected by the final checkpoint;
- old FAIL event/violation remains auditable after later PASS;
- forged Agent PASS remains non-authoritative;
- WRITE_SCOPE violation remains violated.

## 3. R2 — Context Turn closure and Task terminalization

### Required behavior

1. `context-closure` atomically prepares Task Ledger, Progress Ledger and final Working Set through one ContextManager CAS update.
2. The existing `working-set-closure` module remains registered; after atomic context preparation it becomes deterministic `NO_CHANGE`.
3. Kernel Closure and Supervisor lifecycle finalization remain the only completion authority.
4. After exact Kernel/Supervisor COMPLETE, Runtime terminalizes the Context task exactly once as `COMPLETED`, `phase=complete`.
5. Repeating the same terminalization returns the existing terminal Context state without a new state version.
6. A different Turn/Closure identity conflicts instead of overwriting a completed task.

### Acceptance

- exactly eight mandatory Closure modules remain;
- one Context CAS contains ledger/progress/working-set preparation;
- injected failure before that CAS leaves no partial semantic closure;
- successful public completion leaves no ACTIVE Context;
- replay does not create another Context version;
- legacy ACTIVE + close-marker history remains readable only as compatibility.

## 4. R3 — Related prior Context

### Required behavior

1. Completed related tasks are candidates through project identity and route/reference overlap.
2. A task-level route match may carry bounded confirmed/open-issue/next facts when exact fact refs use source URIs rather than route IDs.
3. Unrelated tasks with no route/reference overlap receive no prior facts.
4. Selection remains bounded by existing item/task/character limits.
5. No ATP/SRPWM-specific token or rule may be introduced in public selection logic.

### Acceptance

- completed A with confirmed/open issues -> related B receives bounded `prior-context-*`;
- unrelated C receives zero A facts;
- source-URI fact refs do not prevent inheritance after a valid task-level route match;
- zero budget remains an explicit deterministic selector outcome in diagnostic tests;
- existing limits and ordering remain deterministic.

## 5. R4 — Begin failure atomicity

### Required behavior

1. Gateway persists a bounded PREPARING snapshot with stable task/runtime/turn identities before Runtime open.
2. Any ordinary failure after Runtime open calls the existing Runtime owner compensation path.
3. Compensation appends terminal ABORTED state; it never deletes Turn Journal or Event Store history.
4. Context for an aborted begin becomes `ABORTED` and is never eligible for prior Context.
5. Gateway stores a bounded FAILED snapshot, so the failure is publicly inspectable rather than `TASK_NOT_FOUND`.
6. Runtime owner closes/removes the failed Turn's live Event Store handle.
7. A process loss after Runtime open remains recoverable from the PREPARING snapshot and stable identities; retry/status may compensate it instead of creating a second Turn.

### Acceptance

- contributor unavailable;
- malformed Context projection;
- snapshot finalization failure;
- explicit fault after Runtime open;

For each: no unreachable OPEN/ACTIVE governed task remains after compensation; durable audit records are retained; no second Runtime state system is introduced.

## 6. R5 — Closed Turn replay

### Required behavior

1. Kernel Closure receipt remains the sole completion authority.
2. Runtime recognizes a CLOSED Turn with one COMPLETE receipt before enforcing active-Turn-only logic.
3. Exact/compatible replay returns the original Closure identity with zero new TASK_END, Reflection, Closure-module, Knowledge or finalization effects.
4. Supplied replay candidate refs must reproduce the stored Reflection input fingerprint.
5. A supplied replay semantic Reflection must equal the stored normalized Reflection; a differing proposal conflicts.
6. Replay repairs a missing Context task terminalization idempotently if a crash occurred after Kernel COMPLETE.

### Acceptance

- same request twice in one process;
- same request after Gateway restart;
- same request after Runtime rehydrate;
- changed candidate refs or semantic Reflection -> explicit conflict;
- finalization count remains one;
- Closure attempt/receipt identity remains unchanged.

## 7. Mandatory non-regression

Every repair commit and final campaign must preserve:

1. D-drive machine environment ownership;
2. Node `v22.23.2` machine baseline;
3. checkout-local `node_modules` absent in the frozen machine campaign;
4. machine npm invocation count zero;
5. exact eight MCP tools;
6. wrong project rejection before Runtime state;
7. fingerprint staging;
8. missing/malformed TaskIntent fail-closed;
9. ET6801/SRPWM classification and generic public Framework separation;
10. natural-language `and` classification regression remains fixed;
11. Required Read 7/7 trusted ingress;
12. protected/outside WRITE_SCOPE block;
13. forged validation non-authoritative;
14. premature completion block;
15. Supervisor pending/satisfied/violated/COMPLETE semantics;
16. meaningful Reflection validation;
17. eight-module one-shot happy path;
18. Knowledge narrative no-pollution;
19. no silent machine Runtime activation;
20. no second canonical store or authority.

## 8. Validation layers

A repair is accepted only after all applicable layers pass:

```text
exact owner unit tests
+ composed public lifecycle tests
+ existing public package regression
+ GitHub CI for the exact repair SHA
+ real ATP behavioral retest without changing ATP Project Plugin
```

Hardware/FPGA/HIL remains `NOT_EXECUTED` for this Framework repair.
