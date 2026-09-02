# ET Harness Governance Behavioral Validation Requirement V0.1

## 1. Purpose

Round 3 P0 proved that the ET Harness closed loop can execute end to end through real Pure MCP, a real ATP Project Plugin, trusted reads, trusted validation, replay, Reflection, Context Update and Closure.

This next campaign has a different purpose:

> Prove that every mandatory governance module is not only reachable, but automatically triggers at the correct time, receives the correct inputs, makes the correct bounded decision, actually changes or constrains Worker Agent behavior, updates the correct downstream state, and remains correct after persistence/replay.

The campaign is intentionally designed to **find defects**. A completed task is not sufficient evidence of governance correctness.

The primary behavioral chain under test is:

```text
REAL TASK / STIMULUS
  -> SHOULD A MODULE TRIGGER?
  -> DID IT TRIGGER?
  -> DID IT RECEIVE THE CORRECT INPUT?
  -> DID IT ROUTE / DECIDE CORRECTLY?
  -> DID THE WORKER AGENT ACT DIFFERENTLY OR GET BLOCKED?
  -> DID THE CORRECT DOWNSTREAM STATE CHANGE?
  -> WAS THE RESULT DURABLE AND REPLAYABLE?
```

A module may not be marked PASS merely because its service exists, its route count is non-zero, or the overall task reaches `COMPLETE`.

---

## 2. Frozen Baseline and Non-Negotiable Boundaries

Round 3 P0 accepted baseline:

- final evidence commit: `d472ef1f16a648e82ef0042ca10a04680ae29ec7`
- tested Gateway/Runtime source in that campaign: `1f7e317219f39a2096e3201ddbea51513d47bf91`
- deterministic Windows Node runtime remains pinned on the existing D-drive ET Harness environment
- Pure MCP remains truthful `AUDIT`
- MCP remains `required=false`
- Gateway remains an external process independent of Codex

Before campaign execution, Codex must record the actual current branch HEAD and must use that exact source as the campaign baseline. If the branch has advanced legitimately, the new SHA becomes the recorded test baseline; it must not silently fall back to historical artifacts.

This campaign MUST NOT redesign or replace:

- Runtime
- Execution Supervisor
- Obligation Ledger
- Event Store
- Closure
- Project Plugin architecture
- deterministic runtime environment
- Node/npm installation model
- Pure MCP transport

Forbidden during the measurement phase:

- ad-hoc `npm install`
- environment re-bootstrap when the existing environment is healthy
- Plugin/Hook/Marketplace recovery paths
- Watcher/polling daemon
- Windows Service
- second Runtime/Ledger/Event Store/Closure
- broad instrumentation changes
- changing rules, WRITE_SCOPE, Evidence Policy, Knowledge policy, Context policy or Closure policy to make a test pass

The normal deterministic path remains:

```text
freeze-runtime -> verify-environment -> refresh-gateway
```

If the deterministic environment is invalid, record the exact failure and stop environment-dependent testing. Do not improvise a new environment.

---

## 3. Roles

### Project Owner

The user owns product intent and final project acceptance.

### Architecture Owner

ChatGPT owns architecture interpretation, behavioral acceptance criteria, defect classification and authorization of architecture repair.

### Worker Agent

Codex or another target Agent performs the real ATP engineering task. The Worker must behave as a normal governed Agent and must not receive hidden test-oracle answers.

### Governance Observer Agent

A separate observation role is mandatory for this campaign.

The Governance Observer:

- does not perform project implementation work;
- does not mutate product/framework source during measurement;
- does not manufacture trusted Evidence;
- does not decide Supervisor PASS/Closure authority;
- does not tell the Worker which hidden test expectation it must satisfy;
- records governance behavior after each meaningful lifecycle boundary;
- compares the frozen expected behavior with observed behavior;
- identifies the first failing governance boundary;
- continues independent scenarios when safe so the campaign can discover more than one defect.

“Real-time observation” means observation at the same task/checkpoint/lifecycle boundaries using existing Harness status, durable state and Evidence. It MUST NOT be implemented as a new polling daemon, watcher, background service or second governance runtime.

---

## 4. Mandatory First Step: Build the Actual Module Inventory

Do not test from a guessed module list alone.

Before the Worker starts the first real scenario, Codex must derive the current mandatory governance-module inventory from committed architecture documents, Project manifests, Runtime composition and source registrations.

The inventory must at least account for the following capabilities when they exist in the current source:

1. Governance Catalog / Bootstrap
2. Project Manager / Project Discovery
3. Project Router
4. Task Classification
5. Architecture Navigator / Architecture Route
6. Rule Manager / Rule Route
7. Knowledge Manager / Knowledge Consult
8. Knowledge Validation Policy
9. Context Builder
10. Context Management / Context Update
11. Gate Manager / Gate Route
12. Evidence State Manager
13. Experience Memory Manager
14. Auto Governance Engine
15. Runtime Work Observation
16. Execution Supervisor
17. Obligation Ledger
18. WRITE_SCOPE / Mutation Preflight
19. Required Resource enforcement
20. Trusted Validation / Evidence admission
21. Reflection
22. Knowledge Decision / Classification / Promotion
23. Lifecycle / Closure adapters
24. Closure
25. Runtime/Gateway rehydrate and replay

If current architecture contains additional mandatory modules, add them. If one of the above names has been superseded, map the old capability to the current owner instead of creating a duplicate concept.

For every stateful or decision-making module, identify:

- owner/service
- trigger condition
- expected inputs
- expected outputs
- downstream consumer
- durable state or Evidence surface
- negative/non-trigger behavior
- enforcement behavior, where applicable
- replay expectation, where applicable

No mandatory module may disappear from the final report because it was difficult to observe.

---

## 5. Freeze an Expected Trigger Plan Before Each Scenario

The test oracle must be frozen **before** the Worker performs the scenario. This prevents hindsight-based PASS decisions.

For each real scenario, create an Expected Trigger Plan containing, for every relevant module:

- `shouldTrigger`: `YES` / `NO`
- trigger reason
- expected input category or exact governed refs where deterministic
- expected route/decision or bounded set of acceptable decisions
- expected Agent effect: guide / require read / block / allow / require validation / classify / persist / no-op
- expected downstream state change
- expected durable Evidence surface

Do not over-specify semantic wording. For semantic modules, freeze the required meaning and allowed decision class rather than exact prose.

Negative expectations are equally important. If a module should **not** trigger, a spurious trigger is a behavioral defect.

---

## 6. Real Project Scenario Portfolio

A single happy-path task cannot prove every module. The campaign must use multiple real ATP tasks/scenarios.

Synthetic tests may support diagnosis, but **global behavioral PASS cannot be based only on synthetic fixtures**.

The minimum portfolio is:

### Scenario A — Real Production IP Analysis / Test Development

Use a real ET6801 engineering task from the active ATP backlog, preferably a production task such as XBAR analysis/test development or another currently needed IP task.

Purpose:

- project routing
- task classification
- architecture routing
- rule routing
- knowledge consult
- context construction
- required reads
- Worker guidance
- validation/gates
- evidence binding
- lifecycle progression

The Worker must perform useful project work; the task must not exist only to exercise the Harness.

### Scenario B — Controlled Protected / Out-of-Scope Request

Use a bounded real-project mutation request that intentionally falls outside the task WRITE_SCOPE.

Purpose:

- prove correct rule/scope selection;
- prove preflight enforcement affects Worker behavior;
- prove no forbidden mutation occurs;
- prove the task cannot paper over the violation at completion.

### Scenario C — Reusable New Project Knowledge

Choose a real engineering task expected to discover a reusable project fact that is not already captured in the governed knowledge state.

Purpose:

- knowledge consult before work;
- candidate creation only after evidence exists;
- forced classification;
- correct `PROJECT`/`PUBLIC`/other supported scope decision;
- correct validation before promotion;
- persistence and later reuse.

### Scenario D — No-Reusable-Knowledge Task

Choose a real task whose result should not create reusable knowledge.

Purpose:

- prove Knowledge Decision still occurs when required;
- prove `NONE`/no-capture is an intentional decision rather than a skipped module;
- prove the knowledge store is not polluted.

### Scenario E — Mid-Task Context Change and Later Consumption

Use a real task where a confirmed fact, decision, blocker or next step changes during execution.

Purpose:

- identify the exact fact that should enter Context;
- prove Context Update occurs;
- prove unsupported assumptions do not enter confirmed context;
- start a later turn or resumed task and prove the Worker receives/uses the updated context.

### Scenario F — Restart / Resume

Restart or reconnect after meaningful governed progress but before final completion, and separately test replay of a completed or ready-to-close state where appropriate.

Purpose:

- Event Store replay;
- Runtime rehydrate;
- Ledger state consistency;
- Context/Knowledge state consistency;
- no duplicate events/effects;
- Worker continuity.

### Scenario G — Contradictory / Insufficient Knowledge or Evidence

Use a real source conflict, stale claim, incomplete source set or other genuine ATP uncertainty where available.

Purpose:

- Knowledge Validation Policy;
- Evidence State handling;
- no unsupported promotion;
- no unsupported PASS;
- visible unresolved/open state when proof is insufficient.

The Architecture Owner may refine exact real tasks before execution. Codex must not invent fake product defects merely to satisfy a test row.

---

## 7. Per-Module Behavioral Test Contract

Every mandatory module must be evaluated through this sequence:

### A. Trigger correctness

- Did the expected stimulus exist?
- Should the module trigger?
- Did it actually trigger?
- Did it trigger only when appropriate?

### B. Input correctness

- Did it receive the correct task/project/context/evidence refs?
- Did it use current rather than stale state?
- Were required inputs missing or irrelevant inputs injected?

### C. Decision / route correctness

- Did it select the correct project/module/architecture/rule/knowledge/gate/policy?
- Was selection too broad, too narrow, stale or unrelated?
- For semantic decisions, was the decision consistent with the frozen expected meaning and direct evidence?

### D. Agent effect

This is mandatory.

Prove that the module actually affected the Worker:

- required material was read before work;
- the Worker followed routed rules;
- a prohibited action was blocked;
- a required validation occurred;
- a missing obligation prevented completion;
- a context/knowledge decision changed later work;
- a no-op decision correctly avoided unnecessary work.

A correct-looking route with no demonstrated Worker effect is not sufficient for PASS where the module is intended to guide or constrain execution.

### E. Downstream state correctness

Compare state before and after:

- Context
- Knowledge
- Evidence State
- Experience Memory
- Gate state
- Ledger obligations
- Reflection / lifecycle state

The expected downstream consumer must receive the result.

### F. Durability / replay correctness

For stateful modules:

- restart/reconnect;
- replay existing state;
- compare identities, hashes/status or semantic state as appropriate;
- verify no duplicate side effect;
- verify no state loss or silent reclassification.

---

## 8. Module-Specific Checks

### Project / Task Classification

PASS requires the correct real project and task/module/change classification. A task that merely happens to find the right files later is not enough if routing/classification was wrong.

### Architecture Navigator

Verify that the selected architecture path is relevant to the requested engineering change and that the Worker uses it to choose the correct implementation/analysis surface.

### Rule Manager

For each scenario:

- freeze which rules should apply;
- compare actual routed rules;
- flag missing rules;
- flag irrelevant over-routing;
- prove Worker behavior follows the routed rules;
- use at least one controlled violation to prove enforcement or failure propagation where the rule is enforceable.

### Context Builder / Context Management

Verify:

- initial context is current, bounded and relevant;
- confirmed discoveries are added when they should be;
- unsupported assumptions are not promoted as confirmed facts;
- obsolete state is removed or superseded according to policy;
- a later Worker turn actually receives and uses updated context.

### Knowledge Manager / Knowledge Validation / Classification

Verify:

- relevant existing knowledge is consulted when it should be;
- irrelevant knowledge is not forced into the task;
- reusable findings become candidates only with evidence;
- classification is mandatory when the lifecycle requires it;
- `PROJECT`, `PUBLIC`, `BOTH`, `NONE` or current equivalent is semantically correct;
- insufficient/contradictory evidence does not promote knowledge;
- `NONE` does not pollute stores;
- promoted knowledge is durable and can be reused by a later relevant task.

### Gate Manager

Verify the correct Gate/step/capability is selected from the actual task. A failed mandatory Gate must affect downstream readiness/closure. A Gate must not be reported PASS from Agent assertion alone.

### Evidence State / Trusted Evidence

Verify:

- producer identity/trust source is correct;
- evidence is bound to the correct task/context/target/obligation;
- missing evidence leaves the obligation unresolved;
- forged direct evidence cannot advance state;
- stale/wrong-context/wrong-target evidence is rejected or ignored according to policy;
- trusted evidence remains valid after replay.

### Experience Memory

Where applicable, verify that an experience is captured only when policy says it is reusable and that a later relevant task can actually consume it. Absence of capture may be correct, but the decision must be observable.

### Runtime Work Observation

Verify recorded observations correspond to actual visible Worker actions and do not contain invented work or hidden chain-of-thought. Confirm observations reach the consumers that need them.

### Reflection

Verify Reflection occurs at the correct lifecycle point, is grounded in visible/durable evidence, and produces domain decisions consistent with actual work. A generic Reflection emitted only to unlock Closure is a defect.

### Closure

Verify Closure is the result of satisfied upstream obligations, not a substitute for them. Missing Rule/Knowledge/Context/Evidence obligations must prevent `COMPLETE` when policy requires them.

### Rehydrate / Replay

Verify recovered state is semantically equivalent to pre-restart state, no duplicate execution facts are appended by read/status recovery, and work can continue using the same governed task identity.

---

## 9. Evidence Model

PASS must be evidence-backed. Use the strongest available evidence and preserve exact refs.

### Level 1 — Trusted Mechanical Evidence

Examples:

- Event Store events
- trusted receipts
- hashes
- preflight decisions
- validation results
- Gate results
- Ledger obligation transitions

### Level 2 — Durable State Evidence

Before/after snapshots or durable refs for:

- Context
- Knowledge
- Evidence State
- Experience Memory
- Gate state
- lifecycle state

### Level 3 — Worker Behavioral Evidence

Examples:

- Worker reads a routed required resource before proceeding;
- Worker changes implementation approach because a rule/context item directs it;
- Worker is prevented from a forbidden mutation;
- Worker cannot close while a required module remains unresolved;
- later Worker turn uses newly persisted context/knowledge.

### Level 4 — Observer Judgment

The Observer explains whether observed behavior matches the frozen Expected Trigger Plan.

**A mandatory module may not PASS from Level 4 alone.**

For semantic correctness, use durable/mechanical evidence plus visible Worker behavior whenever the module is intended to affect the Worker.

If no existing surface can prove a mandatory behavior, record `OBSERVABILITY_GAP`. Do not automatically add instrumentation.

---

## 10. Behavioral Result Codes

Use these result codes at module/scenario level:

- `CORRECT`
- `MISSED_TRIGGER`
- `SPURIOUS_TRIGGER`
- `WRONG_ROUTE`
- `WRONG_INPUT`
- `WRONG_DECISION`
- `NOT_ENFORCED`
- `DOWNSTREAM_NOT_UPDATED`
- `NOT_PERSISTED`
- `REPLAY_DIVERGENCE`
- `OBSERVABILITY_GAP`
- `EVIDENCE_INSUFFICIENT`
- `BLOCKED_BY_UPSTREAM`
- `NOT_APPLICABLE`

`OBSERVABILITY_GAP` and `EVIDENCE_INSUFFICIENT` are findings, not PASS.

Do not collapse all problems into “task failed”. Identify the first governance boundary that behaved incorrectly.

---

## 11. Coverage Matrix — How We Prove Every Module Was Tested

Create a module coverage matrix with one row per mandatory module and these columns:

| Module | Owner | Positive Trigger Scenario | Negative / Non-trigger Scenario | Enforcement / Failure Scenario | Downstream State Check | Replay Check | Evidence Refs | Result |
|---|---|---|---|---|---|---|---|---|

Rules:

- every mandatory module needs a positive trigger test;
- every module where non-trigger behavior matters needs a negative/non-trigger test;
- every enforcing module needs a violation/failure test;
- every stateful module needs persistence/replay coverage;
- `NOT_TESTED` cannot count toward PASS;
- global PASS requires 100% coverage of mandatory applicable rows;
- aggregate percentages may be reported, but they may not hide one failed mandatory module.

---

## 12. Defect Discovery Protocol

This campaign is **observation-first**.

### Measurement phase

Do not modify production/framework source while measuring a scenario.

When a defect appears:

1. record the exact scenario and stimulus;
2. record the frozen expected behavior;
3. capture actual module inputs/outputs/state;
4. identify the first failing governance boundary;
5. mark dependent downstream checks `BLOCKED_BY_UPSTREAM` instead of inventing independent failures;
6. do not repair the source during that scenario;
7. continue other independent scenarios/modules when safe, so the campaign discovers additional defects;
8. add the finding to the defect backlog.

This campaign intentionally differs from a repair campaign: discovering one defect does not require abandoning all independent behavioral coverage, but Codex still has **no authority to redesign or repair architecture** unless the Architecture Owner later authorizes a repair phase.

### Repair phase

Only after the measurement report is reviewed by the Architecture Owner may a defect receive a bounded repair requirement.

After any repair, rerun:

- the defect-specific regression;
- all affected module behavior tests;
- the full accepted Round 3 P0 regression;
- any replay/closure checks affected by the repair.

---

## 13. Observability Gaps Are First-Class Defects

The Framework must eventually be able to prove its own governance behavior without depending on Agent self-report.

If the Observer cannot determine whether a mandatory module triggered, what it selected, or whether its result reached downstream state:

- record `OBSERVABILITY_GAP`;
- preserve the exact missing proof;
- do not infer PASS from the final task result;
- do not add a watcher, debug daemon, second Event Store or invasive logging automatically;
- request Architecture Owner review for the smallest read-only observability surface if one is required.

An unobservable mandatory governance behavior prevents global behavioral PASS.

---

## 14. Required Evidence Layout

Create evidence under:

```text
agent_harness/test_campaigns/governance_behavioral_validation_v1/evidence/
```

Minimum deliverables:

```text
00_baseline.md
01_module_inventory.json
02_expected_trigger_plan.json
03_observer_trace.jsonl
04_module_behavior_matrix.json
05_negative_controls.json
06_state_diffs.json
07_replay.md
08_defect_backlog.md
FINAL_REPORT.md
```

For multiple real tasks, scenario-specific subdirectories may be added, but the global inventory/matrix/final report must remain authoritative.

The observer trace should record at least:

```text
scenarioId
taskId
runtimeId
turnId
timestamp
stimulusOrWorkerAction
expectedModules
actualModules
inputRefs
decisionOrRoute
workerEffect
stateBeforeRefs
stateAfterRefs
evidenceRefs
resultCode
notes
```

Do not store hidden chain-of-thought.

---

## 15. Global Acceptance Criteria

The campaign may report `BEHAVIORAL_VALIDATION_PASS` only when all of the following are proven:

1. the actual mandatory module inventory is complete;
2. every applicable mandatory module has required behavioral coverage;
3. expected positive triggers occur;
4. expected non-triggers do not spuriously occur;
5. routes/inputs/decisions are correct against the frozen oracle;
6. guidance/enforcement has demonstrated effect on the Worker where required;
7. downstream state changes correctly;
8. stateful modules persist/replay correctly;
9. no Agent self-certification is accepted as trusted proof;
10. required Knowledge classification/update/no-update behavior is correct;
11. required Context update and later consumption are correct;
12. Rule routing is both relevant and sufficiently complete;
13. Evidence/Gate/Ledger binding is correct and fail-closed;
14. mandatory modules have no unresolved `OBSERVABILITY_GAP`;
15. the accepted Round 3 P0 regression remains green;
16. environment and architecture boundaries remain truthful and unchanged unless separately authorized.

If defects exist, report:

`BEHAVIORAL_VALIDATION_FAIL`

If mandatory behavior cannot yet be observed/proven, report:

`BEHAVIORAL_VALIDATION_INCOMPLETE_OBSERVABILITY`

A task reaching `COMPLETE` does not override either result.

---

## 16. Final Report Format

Codex must finish with:

```text
Final Commit SHA:
Baseline Source SHA:
Real Scenarios Executed:
Mandatory Modules Inventoried:
Mandatory Modules Fully Covered:
Behavioral Validation Result: PASS / FAIL / INCOMPLETE_OBSERVABILITY
Defects Found:
Observability Gaps:
Round3 Regression: PASS / FAIL
Environment Changed: NO / YES
Architecture Review Required: YES / NO
Evidence Directory:
```

Codex is the Test Executor. It may report mechanical campaign results, but it must not declare Architecture Owner final acceptance.

---

## 17. Core Principle

The purpose of this phase is not to prove that the Framework can produce a green final status.

The purpose is to prove, with real project work and durable evidence, that:

> **every governance module does the right work, at the right time, for the right reason, produces the right downstream effect, and can be independently verified.**

When that cannot be proven, the campaign must expose the defect rather than hide it behind successful task completion.
