# Round 3 — ET Harness Closed-Loop Test Execution Charter

## 0. Baseline

- Repository: `abba-labs/et-harness`
- Branch: `codex/fast-track-pure-mcp-atp-v0.1`
- Required starting commit: `e3a43e9c1a03afd502a21bb03092a8e1a78d805f`
- This round is a **real governance closed-loop test**, not an architecture refactor round.

Before starting:

1. `git fetch`
2. checkout this branch
3. verify `HEAD == e3a43e9c1a03afd502a21bb03092a8e1a78d805f` or a later commit created only by this Round 3 work
4. verify the worktree is clean
5. do not switch to another implementation branch

---

# 1. Your role

You are the **Round 3 Test Executor**.

Your job is to:

- make only the minimum test-enabling code changes required to expose existing ET Harness Runtime capabilities through the fixed MCP Gateway;
- execute one real ATP task through the governance chain;
- deliberately exercise automatic routing, rules, knowledge, context, evidence, validation, supervision and closure;
- record raw evidence and exact observed behavior;
- report gaps without redesigning the framework;
- commit and push the test code, test artifacts and evidence.

You are **not** the architecture owner for this round.

Do not redesign ET Harness because a test fails. Record the failure and preserve evidence.

---

# 2. Round 3 objective

Prove or disprove that ET Harness can govern a real Agent task as one closed loop:

```text
User task
  -> Project routing
  -> Project Context contribution
  -> Task Context compilation
  -> Architecture / Rule routing
  -> Knowledge consultation decision
  -> Scope + validation + obligations
  -> Agent work
  -> Work/evidence observation
  -> Gate / validation state
  -> Knowledge capture decision
  -> Mandatory knowledge classification / verification
  -> Context update
  -> Reflection
  -> Obligation evaluation
  -> Runtime closure
  -> Next-task rehydration
```

The test is successful only if the chain is demonstrated with persisted evidence.

Do not treat a correct technical answer as proof that the governance system worked.

---

# 3. Real task to use

Use this natural-language task as the Round 3 workload:

> 分析6801芯片etimer这个IP，最终输出两份文档。

Important:

- Do **not** manually inject eTimer source paths, Rule IDs, knowledge categories, output paths, must-read lists or validation commands into the test prompt.
- These must come from ET Harness routing/context where the project configuration provides them.
- Do not reuse conclusions from previous chats as evidence.
- Evidence must come from the actual project/repository sources reached during this run.

---

# 4. Minimum code changes that are allowed

The current fixed MCP Gateway already exposes `harness_begin` and `harness_status` and already reuses the existing Runtime bridge.

You may add only thin MCP wrappers necessary to execute the existing Runtime Port during the closed-loop test.

Allowed additions include, if required by the test:

- `harness_observe` -> existing Runtime `observeWork(...)`
- `harness_preflight` -> existing Runtime `preflightAction(...)`
- `harness_complete` -> existing Runtime `closeTurn(...)`
- a bounded test/evidence helper needed to persist Round 3 observations
- focused tests for those wrappers
- focused test scripts used only by this campaign
- Round 3 evidence/report files under this campaign folder

Rules for these changes:

1. The Gateway must remain a thin adapter.
2. Reuse the existing `GovernanceHostRuntimePortV01` operations.
3. Do not reimplement Project Manager, Rule Manager, Knowledge Manager, Context Builder, Gate Manager, Ledger, Supervisor, Kernel, Reflection or Closure logic in the Gateway.
4. Do not add project-specific business logic to the Gateway.
5. Do not add an eTimer-specific MCP tool.
6. Keep tool responses bounded and structured.
7. Preserve existing Runtime authority for PASS / COMPLETE / Closure.

If a required capability cannot be reached through the current Host Runtime Port, stop that subtest and record the missing boundary. Do not redesign the Runtime Port without architecture-owner review.

---

# 5. Changes that are conditionally allowed

One known Round 2 risk must be tested before modification:

Current Gateway status mapping may read the Runtime completion decision from the wrong level.

Do this in order:

1. reproduce the status behavior against real Runtime status;
2. save evidence showing the mismatch;
3. only if confirmed, make the smallest mapping correction;
4. add a focused regression test;
5. do not change Runtime/Supervisor semantics.

No other speculative cleanup is allowed.

---

# 6. Changes that are forbidden

Do not perform any of the following during Round 3:

- redesign ET Harness architecture;
- replace or rewrite Governance Runtime;
- replace or rewrite Execution Supervisor;
- replace or rewrite Obligation Ledger;
- replace or rewrite Event Store;
- replace or rewrite Kernel / Closure;
- redesign Project Plugin / Project Context model;
- redesign Knowledge Manager or knowledge taxonomy;
- redesign Context Manager / context persistence model;
- redesign Rule Manager / Architecture Navigator;
- install or rebuild a Codex Plugin;
- make the old Codex Plugin installation path part of the normal development loop;
- modify Codex Desktop installation/cache as a test step;
- move the fixed MCP architecture back into plugin-owned STDIO MCP;
- run broad refactors because of naming/style issues;
- upgrade dependencies unless a Round 3 blocker proves it is necessary;
- run full-repository gates after every edit;
- fix unrelated ATP legacy failures;
- change project rules to make a failing test pass;
- manually mark evidence, knowledge, obligations or closure as PASS when Runtime did not do so.

If one of these appears necessary, record it as `ARCHITECTURE_REVIEW_REQUIRED` and continue with other independent tests where possible.

---

# 7. Required test sequence

Execute in this order.

## R3-01 — Baseline and Gateway health

Verify:

- branch/SHA/worktree;
- fixed MCP Gateway starts without Codex Plugin reinstall;
- health/readiness works;
- Runtime bridge can be reached;
- configured ATP project is visible.

Save commands and outputs.

## R3-02 — Project routing

Call `harness_begin` with the real ATP workspace and the exact natural-language task.

Record at minimum:

- taskId
- runtimeId
- turnId
- projectId
- projectRevision
- contextRevision
- contribution receipts

Verify that project selection came from configured workspace routing, not manual project injection.

## R3-03 — Task Context / architecture / rule routing

From the returned Context, record:

- `mustRead`
- `ruleOwners`
- read scope
- allowed write scope
- protected write scope
- validation contract
- route data
- warnings / known conflicts if present

Then actually follow the returned navigation for the eTimer analysis.

Do not replace Harness routing with manual repository browsing before this step.

## R3-04 — Knowledge consultation

Determine from Runtime/Context whether knowledge consultation is `NONE`, `OPTIONAL` or `REQUIRED`.

If knowledge sources are routed, inspect them and record exact refs.

If consultation was expected by existing policy but no knowledge route occurred, record:

`EXPECTED_BUT_NOT_TRIGGERED`.

Do not manually patch the result by directly injecting knowledge files into the Agent prompt.

## R3-05 — Governed work and evidence observation

Perform the actual eTimer source analysis.

For material facts, use the thin observation path to submit bounded, source-backed work observations to Runtime.

At minimum record facts for:

- IP/source identity;
- relevant architecture/driver/test relationships discovered from real source;
- conflicts or missing integration layers if found;
- the basis for the two requested output documents.

Every material fact must have source/resource refs where the Runtime contract allows them.

Do not submit hidden reasoning or chain-of-thought.

## R3-06 — Preflight / scope enforcement

Where the Agent is about to create or modify the two requested documents, run the existing Runtime preflight path if exposed.

Verify that the planned writes are inside the compiled write scope.

Also perform one safe negative preflight test against a protected/out-of-scope path without actually modifying that path.

Expected result: the invalid action is rejected or clearly reported as not allowed according to existing policy.

Do not perform the forbidden mutation.

## R3-07 — Produce the two requested documents

Create the two documents only in Harness-allowed output locations.

Their technical content must be based on the real run.

The exact document names/paths should follow project context/rules where provided. Do not invent a conflicting output convention.

Record hashes or Git diff references for the produced documents.

## R3-08 — Validation / gate evidence

Execute the validation commands returned by the compiled Task Context that are applicable to this task.

Record:

- command
- exit code
- relevant stdout/stderr excerpt
- timestamp
- evidence file path

Do not run unrelated full-repository validation merely to make the report look stronger.

If an existing unrelated legacy failure appears, classify it as such and preserve the evidence; do not fix it in this round.

## R3-09 — Premature completion negative control

Before all required obligations/evidence are satisfied, attempt the normal completion path once.

Expected behavior:

- Runtime/Closure must not accept an unsupported self-declared completion;
- missing/pending obligations should remain visible;
- the Agent must not be able to manufacture PASS.

Record the exact response.

If completion is incorrectly accepted, mark this test `FAIL_CRITICAL` and do not hide or compensate for it.

## R3-10 — Knowledge capture and classification

After real analysis has produced at least one reusable project fact, execute the existing knowledge-decision/closure flow.

Verify and record:

- capture decision;
- project/public scope decision;
- category decision;
- source/evidence refs;
- verification result;
- resulting knowledge status;
- promotion or rejection result;
- warnings.

Critical requirement:

A knowledge candidate must not silently become trusted knowledge without the classification/verification required by current Runtime policy.

If classification is not triggered where existing policy says it should be required, record `EXPECTED_BUT_NOT_TRIGGERED`.

Do not redesign categories during the test.

## R3-11 — Context update

Record the initial `contextRevision` from `harness_begin`.

After meaningful work/closure, inspect the Runtime/context state and determine whether the existing framework produced a new context contribution/revision or persisted the relevant task state.

Record:

- before revision/ref;
- after revision/ref;
- what durable facts changed;
- evidence basis.

Do not create a fake context-update file solely to make this test pass.

## R3-12 — Final closure

After required evidence/validation is present, call the normal Runtime closure path.

Record bounded final results including:

- Reflection result/status
- Closure result/status
- knowledge decision summary
- knowledge verification/promotion summary
- supervision decision
- pending/satisfied/violated obligation IDs

The Agent must not translate an incomplete Runtime result into its own `PASS`.

## R3-13 — Rehydration / next-task check

Start a new governed task/session against the same ATP project after the first task is closed.

Use a minimal follow-up intent that requires awareness of the just-completed eTimer work.

Verify whether the project/context/knowledge state that is supposed to be durable is discoverable through normal Harness routing.

Do not manually inject the previous task summary into the follow-up prompt.

Record exactly what was and was not rehydrated.

---

# 8. Required negative controls

The following are mandatory and must be evidence-backed:

1. invalid/unmatched workspace -> project routing rejects or fails closed;
2. protected/out-of-scope write preflight -> rejected without performing mutation;
3. premature completion -> blocked while mandatory obligations are incomplete;
4. unsupported/unverified knowledge candidate -> not promoted as trusted knowledge;
5. next task -> no manual previous-task prompt injection.

A negative control that unexpectedly succeeds is a real Round 3 failure. Do not patch the evidence.

---

# 9. How to classify each module

For every tested governance module, record both a result and an enforcement level.

Result must be one of:

- `TRIGGERED_PASS`
- `TRIGGERED_FAIL`
- `EXPECTED_BUT_NOT_TRIGGERED`
- `NOT_APPLICABLE`

Enforcement must be one of:

- `MECHANICAL` — Framework executes/decides without model discretion.
- `WORKFLOW_ENFORCED` — model can attempt to skip, but Framework blocks completion/action.
- `GUIDED` — Context/instructions guide the model, but Host/Framework does not mechanically prevent bypass.

Never label a GUIDED behavior as mechanically enforced.

At minimum classify:

- Project routing
- Project Context contribution
- Task Context compilation
- Architecture routing
- Rule routing
- Knowledge consultation
- Scope enforcement
- Validation/gates
- Evidence observation
- Execution supervision
- Obligation ledger
- Knowledge capture decision
- Knowledge classification
- Knowledge verification/promotion
- Context update/persistence
- Reflection
- Closure
- Next-task rehydration

---

# 10. Evidence storage

All Round 3 test evidence committed to this repository must live under:

```text
agent_harness/test_campaigns/round3_closed_loop/evidence/
```

Use this layout:

```text
evidence/
├── 00_environment.md
├── 01_gateway_health.md
├── 02_begin_and_routing.json
├── 03_context_contract.json
├── 04_knowledge_consult.md
├── 05_work_observations.jsonl
├── 06_preflight_negative.md
├── 07_outputs.md
├── 08_validation.md
├── 09_premature_complete.md
├── 10_knowledge_capture.md
├── 11_context_update.md
├── 12_final_closure.md
├── 13_rehydration.md
├── MODULE_TRIGGER_MATRIX.md
└── ROUND3_FINAL_REPORT.md
```

If raw logs are large, do not dump unbounded logs into Markdown. Save bounded excerpts plus stable file/path/hash/command references. Small JSON/JSONL evidence is preferred for machine-checkable results.

Do not store:

- auth tokens;
- secrets;
- hidden model reasoning;
- private chain-of-thought;
- unrelated full build logs;
- generated dependency directories.

---

# 11. Evidence requirements

Every PASS/FAIL claim in `MODULE_TRIGGER_MATRIX.md` must point to a concrete evidence file/ref.

For each test record:

```text
Test ID:
Expected:
Actual:
Result:
Enforcement:
Task/Runtime/Turn IDs:
Command or MCP operation:
Evidence refs:
Observed limitation:
Architecture review required: YES/NO
```

Do not write conclusions such as "系统整体正常" without evidence links.

Do not reinterpret a Runtime failure as success.

---

# 12. Testing/build discipline

Use the smallest validation ladder possible.

For Gateway wrapper changes:

1. run the directly affected Node tests;
2. run the Gateway focused test suite;
3. start/restart the fixed Gateway;
4. run a synthetic MCP smoke only if needed;
5. run the real ATP Round 3 task.

Do not reinstall the Codex Plugin.

Do not run `npm install` unless dependencies are actually missing and the current lockfile cannot satisfy the existing setup.

Do not repeatedly rebuild unrelated packages.

Do not run the full repository gate until the Round 3 implementation/test checkpoint is complete, and only run it if existing project instructions explicitly require it for the final commit.

---

# 13. Failure handling

When a test fails:

1. stop the affected sub-flow;
2. capture exact reproduction/evidence;
3. identify the narrow failing boundary, if observable;
4. classify it as one of:
   - `GATEWAY_WRAPPER_BUG`
   - `PROJECT_ROUTING_GAP`
   - `PROJECT_CONTEXT_GAP`
   - `RULE_ROUTING_GAP`
   - `KNOWLEDGE_GOVERNANCE_GAP`
   - `CONTEXT_PERSISTENCE_GAP`
   - `SUPERVISION_LEDGER_GAP`
   - `CLOSURE_GAP`
   - `HOST_CAPABILITY_GAP`
   - `UNKNOWN`
5. set `ARCHITECTURE_REVIEW_REQUIRED: YES` for anything beyond a thin adapter/test defect;
6. continue other independent tests when safe.

Do not perform a broad repair in the same round.

---

# 14. Round 3 final report

`ROUND3_FINAL_REPORT.md` must contain only evidence-backed sections:

1. baseline SHA and final SHA;
2. code changes made for test enablement;
3. real task used;
4. module trigger matrix summary;
5. negative-control results;
6. produced document refs;
7. knowledge capture/classification result;
8. context persistence/rehydration result;
9. closure/obligation result;
10. unresolved defects;
11. items requiring architecture-owner action;
12. final classification.

Final classification must be exactly one of:

- `ROUND3_CLOSED_LOOP_PASS`
- `ROUND3_CLOSED_LOOP_PARTIAL`
- `ROUND3_CLOSED_LOOP_FAIL`

Do not use `PASS` if a required module is `EXPECTED_BUT_NOT_TRIGGERED`, a critical negative control fails, or Runtime closure is not valid.

---

# 15. Commit and push requirements

Keep Round 3 work on:

`codex/fast-track-pure-mcp-atp-v0.1`

Before commit:

1. confirm no secret/token/log pollution;
2. confirm only minimum Gateway/test changes plus requested output/evidence files are present;
3. confirm evidence paths are under the Round 3 campaign folder;
4. run focused tests;
5. record final `git status` and relevant test results in the report.

Recommended commit sequence:

1. `test(round3): expose minimal runtime operations for closed-loop test` — only if thin Gateway wrappers are needed;
2. `test(round3): record ATP closed-loop governance evidence` — evidence + reports + task outputs as applicable.

Then push the same branch.

Final handoff must report:

```text
Branch:
Final commit SHA:
Remote SHA:
Local/remote SHA match: YES/NO
Worktree clean: YES/NO
Round 3 classification:
Evidence root:
Architecture review required: YES/NO
Critical failed test IDs:
```

Do not start Round 4. Stop after push and handoff.