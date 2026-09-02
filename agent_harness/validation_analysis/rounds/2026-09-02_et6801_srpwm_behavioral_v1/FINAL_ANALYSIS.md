# ET6801 SRPWM Behavioral Validation v1 — Final Architecture Analysis

## 0. Frozen Identity / Evidence Boundary

### 0.1 Tested product

- Canonical development baseline at test start: `development/et-harness-mainline-v0.1`
- Tested source SHA: `b3f32b3002d576ff75f3c4edee7fdd643bf415e0`
- Behavioral validation branch: `validation/et6801-srpwm-behavioral-v0.1`
- Final Evidence commit: `fea9e454d100eaf175bfa8f9ed0589a104488d15`
- Active Runtime release during test: `f976d8e32df64fa78075`
- Gateway PID during campaign: `20124`
- Node: `v22.23.2`
- checkout-local `node_modules`: absent
- npm/npm ci/npm update/npx: not invoked
- Framework product code modified during measurement: **NO**
- FPGA/HIL/hardware execution: `NOT_EXECUTED`

### 0.2 Primary Codex Evidence

All behavioral conclusions below are derived first from the exact Evidence at SHA `fea9e454...`:

- `agent_harness/test_campaigns/governance_behavioral_validation_v1/evidence/et6801_srpwm_behavioral_20260902/FINAL_REPORT.md`
- `.../module_behavior_matrix.json`
- `.../negative_controls.json`
- `.../observer_trace.jsonl`
- `.../state_diffs.json`
- `.../defect_backlog.md`
- `.../baseline.md`
- `.../expected_trigger_plan.json`
- `.../module_inventory.json`

Task output under measurement:

- `test_case_doc/srpwm/srpwm.md`
- `test_case_doc/srpwm/ET6801_srpwm.md`

### 0.3 Analysis discipline

This document distinguishes four levels:

- `PROVEN_OBSERVATION`: Codex mechanically observed it in the real campaign;
- `PROVEN_ROOT_CAUSE`: Evidence and exact source jointly isolate the causal boundary;
- `STRONG_CAUSE_CANDIDATE`: source can explain the observation, but existing Evidence does not uniquely distinguish it from another cause;
- `PREDICTED_NOT_OBSERVED`: derived simulation only; must not be reported as an already observed defect.

No repair is allowed to rely on a `STRONG_CAUSE_CANDIDATE` as if it were uniquely proven.

---

# 1. Executive Conclusion

一句话：

> **单次治理链已经能可靠完成，但 Validation 恢复、Context 生命周期与跨任务连续性、失败原子性、Closure replay 和长期可审计数据仍不合格；本轮没有证据证明这些问题是最近 Environment/Machine Launcher 优化新引入的 regression。**

Codex module result:

- PASS: 25
- FAIL: 9
- OBSERVABILITY_GAP: 4
- NOT_EXECUTED: 2

当前应分成三层：

### 已形成稳定资产

- fixed Machine Environment / machine-local launcher
- exact 8 MCP tools
- Project Admission
- TaskIntent fail-closed
- ET6801/SRPWM classification
- Required Read trusted event
- WRITE_SCOPE
- forged validation rejection
- premature completion block
- Supervisor basic decisions
- meaningful Reflection
- one-shot 8-module happy-path Closure
- Knowledge negative no-pollution boundary

### Framework 核心缺陷 / 恢复缺口

1. validation FAIL 后当前 Turn 不能恢复；
2. Context task lifecycle 未真正 terminalize；
3. related Task B 未获得 priorContext；
4. successful completion 不能 replay；
5. failed begin 可形成 Gateway 不可达的 orphan Turn；
6. Work Observation body 不 durable。

### 质量与项目内容问题

- Context / Route 接近预算上限且泛化；
- Architecture / Knowledge / Gate 的 agent-facing 解释不足；
- ATP Knowledge taxonomy 无芯片/IP领域分类；
- SRPWM SDK / UnitTest / Requirement / Capability 有真实项目缺口。

---

# 2. Evidence Inventory — 只记录事实

## E-001 Validation failure cannot recover

**PROVEN_OBSERVATION**

Task A：

1. trusted validator 真实 FAIL；
2. Agent 只修改允许范围内 `test_case_doc/srpwm/**`；
3. 修正后相同 validator 直接执行已 PASS；
4. 再调用 `harness_checkpoint` 返回 `validations=[]`；
5. 原 validation obligation 保持 `VIOLATED`；
6. Task A 无法 Closure，只能创建 A-retry。

Evidence: `FINAL_REPORT.md`, `defect_backlog.md` GOV-SRPWM-001, `observer_trace.jsonl` Task A corrected output event.

## E-002 A-retry Context persists but B receives no priorContext

**PROVEN_OBSERVATION**

A-retry COMPLETE 后：

- Context version 14；
- 5 confirmed；
- 3 openIssues；
- Context status = `ACTIVE`；
- finalization exists。

Task B：

- same ET6801/SRPWM related follow-up；
- `harness_begin` has no `priorContext`；
- B initial confirmed/openIssues empty；
- Worker rereads A output/SVD/Driver independently。

Evidence: `state_diffs.json`, `module_behavior_matrix.json` M13/M14/M31, `negative_controls.json` NC-CONTEXT-001.

## E-003 Successful complete is not idempotently replayable

**PROVEN_OBSERVATION**

- First A-retry `harness_complete` => COMPLETE；
- exact same request retry => `RUNTIME_UNAVAILABLE` / active Turn none；
- no duplicate finalization was written。

Evidence: `negative_controls.json` NC-CLOSE-002, `defect_backlog.md` GOV-SRPWM-002.

## E-004 Failed unrelated Task C leaves orphan durable state

**PROVEN_OBSERVATION**

- valid ATP project + unrelated Companion/FPGA/Instrument intent；
- `harness_begin` returns ERROR；
- Runtime already persisted OPEN Turn；
- ACTIVE Context exists；
- one USER_MESSAGE Event Store exists；
- Gateway snapshot absent；
- public `harness_status` => `TASK_NOT_FOUND`；
- repeated begin => persisted unresolved Turn / `RUNTIME_UNAVAILABLE`。

Evidence: `negative_controls.json` NC-POLLUTION-001, `state_diffs.json`, `defect_backlog.md` GOV-SRPWM-004.

## E-005 Work Observation body is not durable

**PROVEN_OBSERVATION**

- live `harness_observe` changes Knowledge CHECK/OPTIONAL/REQUIRED behavior；
- durable journal/event evidence preserves observation/ref identity；
- source summary/body cannot be reconstructed from durable state。

Evidence: `module_behavior_matrix.json` M19, `defect_backlog.md` GOV-SRPWM-005.

## E-006 Context is near budget and route is broad

**PROVEN_OBSERVATION**

Task A initial Context:

- 17,485 / 18,000 chars；
- 55 refs；
- selected sets include Architecture/Rule/Knowledge/Gate plus broad adjacent PC/Firmware/Companion/CI material；
- public projection proves IDs/trace, not full semantic content/trust/use for all selected objects。

Evidence: M08/M10/M12/M15/M16 and GOV-SRPWM-006.

## E-007 Knowledge safe-negative path passes, positive path unproven

**PROVEN_OBSERVATION**

- ordinary Agent prose did not become trusted Knowledge；
- candidate count remained zero；
- no duplicate candidate pollution；
- positive SRPWM candidate/promotion/update/reuse path not executed because current project taxonomy has no precise chip/IP hardware/driver category。

Evidence: M10/M11/M29/M32, ATP `knowledge/TAXONOMY.yaml`.

## E-008 Internal Gate/Evidence/Experience behavior is under-observed

**PROVEN_OBSERVATION / OBSERVABILITY_GAP**

- effects can be observed indirectly；
- complete per-gate decision state, canonical Evidence State readback, Experience positive capture/reuse are not independently provable through current campaign surface。

---

# 3. Evidence → Code Trace / Root Cause

## 3.1 Validation recovery

### Source chain

`trusted-checkpoint.mjs` creates:

```text
pending = ledger.pendingObligationIds
```

then executes validator only when:

```text
obligation.kind === VALIDATION && pending.has(obligation.id)
```

Therefore `VIOLATED` validation is not eligible for a later checkpoint execution.

`execution_supervisor/obligation-ledger.ts` on trusted validation FAIL sets:

```text
state = VIOLATED
```

and several recomputation paths explicitly preserve/skip `VIOLATED`.

### Root-cause verdict

**PROVEN_ROOT_CAUSE**

There are two coupled old semantics:

1. trusted validation FAIL makes the current validation state terminal `VIOLATED`；
2. checkpoint scheduler only runs `PENDING` validation obligations。

This makes `FAIL -> correction -> revalidate -> PASS` impossible inside one Turn.

### Defect provenance

`PRE_EXISTING_ROOT_DEFECT + TEST_GAP`

- Obligation Ledger existed before the latest P0 continuity repair and was not modified in the Environment/Machine Launcher rounds；
- previous tests validate trusted FAIL identification but do not exercise a chronological `FAIL -> later PASS` sequence through real checkpoint scheduling。

---

## 3.2 Context lifecycle and Task B inheritance

### Confirmed old lifecycle defect

`ContextManagementService` has a real:

```text
complete(projectId, taskId)
  -> status = COMPLETED
  -> phase = complete
```

But `createContextClosureModule()` only receives/uses:

- getTask
- updateTaskLedger
- updateProgressLedger
- replaceWorkingSet

It does not call `complete()`.

It writes Task Ledger, Progress Ledger and Working Set, then reports Closure `APPLIED` while canonical Context status remains `ACTIVE`.

### Proven lifecycle verdict

**PROVEN_ROOT_CAUSE for non-terminal Context lifecycle.**

This defect predates the previous continuity repair. The closure-adapter file has effectively carried this behavior since the imported Harness snapshot.

### Previous repair behavior

Previous continuity repair added `selectRelevantContextHistory()` and later added compatibility:

```text
ACTIVE + lastAction startsWith "Close governed Turn "
```

as an eligible historical candidate.

Therefore `status=ACTIVE` **alone does not uniquely explain why Task B had no priorContext**.

### Additional code-supported candidates for B omission

#### Candidate C1 — Inline budget starvation

Selector computes:

```text
remaining = min(4000, 16000 - existingInlineChars)
if remaining <= 0 => []
```

The previous unit test explicitly treats “existing inline context already consumes 16,000 chars => no inherited context” as PASS.

This is a serious candidate because the real Task A/B compiled Context is already near the 18K pack limit.

#### Candidate C2 — Ref overlap mismatch

Prior-context candidate requires overlap between current route reference tokens and historical working-set/scope/confirmed/openIssue/touched refs. Exact B selector candidate/matchedRefs were not persisted in this campaign.

#### Candidate C3 — Projection loss after selection

Gateway now parses `prior-context-*` inline items and would expose them if present. Current Evidence does not show whether B lacked the inline item before Gateway or whether it was omitted earlier by Context assembly. Existing evidence strongly places the missing boundary before/at `replaceWorkingSet -> selectRelevantContextHistory`, but does not uniquely distinguish C1 vs C2.

### Root-cause verdict for B

- `Context never terminalizes`: **PROVEN_ROOT_CAUSE**
- `B priorContext absence exact sub-cause`: **STRONG_CAUSE_CANDIDATES; NOT YET UNIQUELY PROVEN**

### Defect provenance

`INCOMPLETE_PREVIOUS_FIX` built on top of a `PRE_EXISTING_ROOT_DEFECT`.

It is **not** a confirmed `NEW_REGRESSION`: there is no mechanically proven older baseline where real A->B continuity worked and the previous repair broke it.

---

## 3.3 Context provenance granularity

`context-closure` calculates one global:

```text
refs = reflection.context.touchedRefs
```

and attaches the same full list to every Decision/Confirmed/Assumption/OpenIssue entry.

### Root-cause verdict

**PROVEN_ROOT_CAUSE** for semantic over-association.

The persisted `refs` do not prove which exact source supports which exact fact. This can later distort prior-context matching.

Classification: `PRE_EXISTING_ROOT_DEFECT / DATA_QUALITY_GAP`.

---

## 3.4 Successful Closure replay

Kernel `ClosureCoordinator.closeTurn()` already supports:

```text
existing COMPLETE receipt -> return existing
```

But `GovernanceRuntimeService.closeTurn()` checks active Turn first. If activeTurnId differs and journal is CLOSED, it throws before the request can reach Kernel idempotent receipt logic.

Gateway `complete()` simply loads snapshot and calls Runtime close again; it has no independent persisted replay result.

### Root-cause verdict

**PROVEN_ROOT_CAUSE**

The broken boundary is Runtime/Gateway closed-turn replay, not the Kernel Closure Coordinator's core idempotency logic.

Classification: `PRE_EXISTING_ROOT_DEFECT + TEST_GAP`.

The `harness_complete` public path had this shape from its initial Round3 exposure; previous Gateway tests invoked complete only once.

---

## 3.5 Begin failure atomicity / orphan Turn

Gateway `begin()` order is:

```text
runtimeAccess.openTurn()
-> projectContextFromOpenTurn(opened)
-> snapshotStore.put(snapshot)
```

Any exception after `openTurn()` but before successful snapshot write can leave Runtime durable state without a Gateway task identity.

The original Gateway implementation already used this order.

### Root-cause verdict

**PROVEN_ROOT_CAUSE**

Task C is one instance of a generic partial-commit window.

Classification: `PRE_EXISTING_ROOT_DEFECT + TEST_GAP`.

Previous test `T8 contributor failure` asserted only:

```text
Gateway snapshot == undefined
```

It used a fake Runtime and did **not** assert:

```text
Runtime Turn / Context / Event Store == zero or terminally compensated
```

The old unit test therefore accidentally accepted exactly the state split now exposed by Task C.

---

## 3.6 Work Observation durability

`GovernanceTurnObservationStore` is:

```text
private observations = new Map<task::turn, observation[]>()
```

It creates content-addressed refs but has no durable backing. The file history shows this is original imported Framework behavior, not a recent Environment change.

### Root-cause verdict

**PROVEN_ROOT_CAUSE**

Observation currently has live-decision value but not durable replay/audit value.

Classification: `PRE_EXISTING_ROOT_DEFECT / NEWLY_TESTED_CAPABILITY_GAP`.

---

## 3.7 Context/Route breadth and agent-facing opacity

This campaign mechanically proves high char/ref usage, but not one unique algorithmic bug. Architecture and Rule route core selections are mostly reasonable; excess breadth results from combined route + project inline contribution + generic Knowledge/Gate content.

Classification:

`NEWLY_TESTED_CAPABILITY_GAP + OBSERVABILITY_GAP`, not a confirmed regression.

Do not optimize this before P0 lifecycle correctness is stable.

---

# 4. Defect Provenance Matrix

| Problem | Classification | Earliest/older source evidence | Owner changed by latest Environment/Machine Launcher work? | Previous real baseline proven good? | Regression verdict |
|---|---|---|---|---|---|
| Validation FAIL cannot recover | PRE_EXISTING_ROOT_DEFECT + TEST_GAP | Obligation Ledger Phase2/4 existed before current continuity work | NO | NO | NOT_NEW_REGRESSION |
| Context Closure leaves ACTIVE | PRE_EXISTING_ROOT_DEFECT | Context `complete()` exists but closure adapter never calls it | NO | NO | NOT_NEW_REGRESSION |
| Task B no priorContext | INCOMPLETE_PREVIOUS_FIX + unresolved selector sub-cause | continuity selector added last round; old lifecycle gap predates it | selector YES; closure owner NO | NO real A->B PASS baseline | NOT_CONFIRMED_REGRESSION |
| Context fact refs over-broad | PRE_EXISTING_ROOT_DEFECT | closure adapter global touchedRefs behavior | NO | NO | NOT_NEW_REGRESSION |
| Complete replay fails | PRE_EXISTING_ROOT_DEFECT + TEST_GAP | initial harness_complete path called close once and Runtime requires active turn | NO in env rounds | NO | NOT_NEW_REGRESSION |
| Failed begin orphan | PRE_EXISTING_ROOT_DEFECT + TEST_GAP | initial Gateway begin open->project->snapshot order | NO in env rounds | NO | NOT_NEW_REGRESSION |
| Observation body not durable | PRE_EXISTING_ROOT_DEFECT | imported in-memory observation store | NO | NO | NOT_NEW_REGRESSION |
| Context/route too broad | NEWLY_TESTED_CAPABILITY_GAP | existing routing/budget design | no causal env change | NO | NOT_NEW_REGRESSION |
| Knowledge positive path missing | PROJECT_CONTENT_GAP + NOT_EXECUTED | ATP taxonomy has governance categories only | N/A | N/A | NOT_FRAMEWORK_REGRESSION |
| SRPWM 18 vs 12 / DMA / UnitTest / Requirement | PROJECT_CONTENT_GAP | target SDK/project sources | N/A | N/A | NOT_FRAMEWORK_REGRESSION |

### Overall regression conclusion

**No current Evidence establishes a confirmed `NEW_REGRESSION` caused by the recent Environment / Machine Launcher optimization.**

The Context continuity work is the only `INCOMPLETE_PREVIOUS_FIX`: previous work added selection/compatibility behavior without closing the underlying Context lifecycle contract.

---

# 5. Why Previous Tests Missed These Problems

This section is mandatory because these gaps, not only product bugs, create the risk of endless fix/test cycles.

## 5.1 Context continuity unit test is selector-only

`context-continuity.test.ts` directly constructs synthetic ContextSession values and calls `selectRelevantContextHistory()`.

It does not compose:

```text
real Context Manager
-> real Context Closure Adapter
-> EvidenceState persistence
-> next task bootstrap
-> real Gateway harness_begin
```

Therefore it can prove selector logic on synthetic state but cannot prove the producer produces the correct terminal state or that the next task actually receives it.

## 5.2 Context Closure Adapter test codifies partial behavior

`agent_governance_closure_adapters/tests/modules.test.ts` uses a fake manager with only:

- getTask
- updateTaskLedger
- updateProgressLedger
- replaceWorkingSet

and expects `APPLIED` after those three writes. It does not offer/assert `complete()`.

Therefore previous test success actually proves the adapter's current incomplete contract, not end-to-end task terminalization.

## 5.3 Gateway contributor-failure test checked only one side of the transaction

Gateway test T8:

- fake openTurn returns contributor-less context；
- begin rejects；
- assertion: no Gateway snapshot。

It never checks whether Runtime durable state was opened. With a fake Runtime, it cannot reveal orphan Turn/Context/Event Store.

## 5.4 Gateway complete test executes only once

T10 invokes `controller.complete()` one time. No exact replay, response-loss, restart or different-input replay test exists at the composed Gateway/Runtime boundary.

## 5.5 Validation tests check static Evidence semantics, not chronological recovery

Evidence policy test proves trusted FAIL is recognized as `trustedFailure`. Obligation tests cover pending/satisfied and dependency behavior. They do not execute:

```text
FAIL event
-> correction / new checkpoint
-> PASS event
```

through the real checkpoint scheduler.

## 5.6 Observation store lacks restart/replay acceptance

Current implementation/test model validates bounded in-memory observation semantics. The campaign is the first layer that asked whether the same body can be reconstructed later from durable state.

## 5.7 Previous real campaigns were mostly single-turn happy-path oriented

They established:

- trigger correctness；
- trust boundaries；
- one-shot closure；

but did not systematically execute:

- fail->fix->retry；
- task A->related B；
- task A->unrelated C；
- complete->same complete；
- failure between Runtime open and Gateway snapshot；
- process restart after active/closed task。

### Test-process root cause

The central test gap is:

> **synthetic module tests validated local return values, while real lifecycle composition and durable state invariants were not always asserted together.**

Future regression must always include both unit-level exact owner tests and one composed lifecycle test.

---

# 6. Root-Cause Grouping — Do Not Repair 9 FAILs Separately

| Repair line | Symptoms covered | Root owner(s) | Core invariant |
|---|---|---|---|
| R1 Validation Current-State Recovery | GOV-001, M21, Task A forced retry | trusted-checkpoint + execution_supervisor ledger | current validation state may recover from trusted later PASS while failure history remains append-only |
| R2 Context Task Lifecycle | M14/M31, all sessions ACTIVE | context closure adapter + ContextManager | successful task closure must produce one canonical terminal Context state |
| R3 Prior Context Selection/Quality | M13/B missing inheritance, future pollution risk | ContextManager selector/budget + Reflection provenance contract | related completed facts are selected; unrelated facts and budget starvation are explainable/controlled |
| R4 Begin Transaction/Compensation | M06/M40/C orphan | Gateway + Governance Runtime lifecycle | begin is externally atomic: success is reachable; failure leaves no unreachable active state |
| R5 Closed-Turn Replay | M39/M40/complete retry | Governance Runtime + Gateway projection | same completion request returns same durable closure result without new effects |
| R6 Observation Durability | M19/audit replay | Governance Runtime + existing Event Store | consumer-relevant bounded observation can be reconstructed after process/session loss |
| R7 Governance Content Precision | M08/M10/M12/M15/M16 | routing/projection | selected content is relevant, bounded, explainable and does not crowd out continuity |

R1-R5 are lifecycle correctness. R6-R7 are P1 after lifecycle stabilization.

---

# 7. Predictive Simulation — Current Code, Same Codex Testing Style

Every row below is `PREDICTED_NOT_OBSERVED` unless explicitly stated otherwise.

## P-001 PASS validation may remain stale after a later mutation

**Basis**

Checkpoint executes only PENDING validation obligations. Current failure shows mutation/correction did not make a VIOLATED validation pending. The symmetric state risk is that a SATISFIED validation may also remain satisfied after output changes.

**Predicted sequence**

```text
checkpoint -> PASS -> SATISFIED
-> allowed output mutation
-> checkpoint
-> validation not rerun because not PENDING
-> stale PASS survives
```

**Probability:** HIGH
**Impact:** CRITICAL — could allow Closure against code/output newer than trusted validator evidence.

**Minimal discriminating test:** clean task, PASS all validators, mutate one validated output within write scope, checkpoint again, assert validator actually reruns and old PASS cannot authorize new content.

This test must be executed before finalizing R1 design.

---

## P-002 Prior Context can be starved by inline budget even after lifecycle fix

**Basis**

Current selector intentionally returns no history when existing inline context reaches 16,000 chars. Existing unit test treats this as expected. Real task pack is already 17,485/18,000 chars.

**Probability:** HIGH
**Impact:** HIGH — continuity may still fail after `status=COMPLETED` is fixed.

**Minimal discriminating test:** real/synthetic composed B task with exact ATP contribution sizes near current campaign; record base inline chars, remaining prior budget, candidate sessions, selected/omitted reasons.

**Important:** do not declare Context continuity repaired merely because closure starts calling `complete()`.

---

## P-003 Fixing inheritance without provenance precision may create false cross-task pollution

**Basis**

Every confirmed/openIssue currently receives the same full touchedRefs. Selector uses these refs for matching. Once priorContext begins flowing reliably, broad refs can make facts appear relevant to tasks they do not actually support.

**Probability:** HIGH
**Impact:** HIGH — hidden long-term semantic pollution.

**Minimal test:** Task A produces two facts with disjoint source domains; Task B overlaps only one domain; B must receive only the matching fact. Task C overlaps generic Architecture but not SRPWM fact sources; no SRPWM fact should appear.

---

## P-004 ACTIVE + close-marker compatibility can inherit a task too early

**Basis**

Selector treats `ACTIVE` session with `lastAction = Close governed Turn ...` as historical. A task can conceptually contain more than one Turn or be reopened. A previous closed-turn marker does not necessarily mean task-level completion.

**Probability:** MEDIUM-HIGH
**Impact:** HIGH

**Minimal test:** close Turn 1 but keep task logically active/rebuild for Turn 2; open related task concurrently; verify unfinished task state is not inherited as completed history.

Long term the ACTIVE compatibility path should be legacy fallback only, not the normal success path.

---

## P-005 Context Closure can partially mutate state if one internal call fails

**Basis**

Current adapter performs sequential durable writes:

```text
updateTaskLedger
-> updateProgressLedger
-> replaceWorkingSet
```

before returning one module receipt. If write 2 or 3 fails, earlier state writes remain although module receipt is FAILED.

**Probability:** HIGH under injected failure
**Impact:** HIGH — module-level failure atomicity violation and retry ambiguity.

**Minimal test:** inject failure at each Context closure write boundary and compare state before/after; failed module must not expose partially committed semantic closure.

---

## P-006 Any post-open Gateway error can create an orphan, not only contributor failure

**Basis**

The partial-commit window spans from Runtime `openTurn` until successful snapshot persistence.

Potential triggers:

- missing required inline item；
- malformed rendered Context；
- invalid validation contract；
- project/context revision missing；
- snapshot filesystem write failure；
- process termination between open and snapshot。

**Probability:** HIGH
**Impact:** CRITICAL

**Minimal tests:** fault inject each boundary after openTurn; assert no unreachable ACTIVE Turn/Context remains.

---

## P-007 Closed completion after process restart may also be unrecoverable

**Basis**

Same-process repeated complete already fails at Runtime active-turn contract. Full restart regression was `NOT_EXECUTED`.

**Probability:** HIGH
**Impact:** HIGH

**Minimal test:** complete task, restart Gateway/Runtime through machine launcher, repeat exact complete; must return same closure identity.

---

## P-008 Active task restart may expose another rehydrate gap

**Basis**

Governance Runtime contains cross-process rehydrate logic, but current campaign did not restart active A/B. Semantic executor, Context route hash and event cursor must all reconstruct consistently.

**Probability:** MEDIUM
**Impact:** HIGH

**Minimal test:** pause after reads/checkpoint but before complete, restart Gateway, status/observe/checkpoint/complete same task.

---

## P-009 Context history scan may degrade with long-lived project state

**Basis**

Prior selector reads full project Evidence State snapshot then filters Context sessions. Campaign already has 31 Context sessions, all ACTIVE.

**Probability:** MEDIUM over long operation
**Impact:** MEDIUM (latency/memory)

**Minimal test:** synthetic 1k/10k historical Context records, measure deterministic bootstrap time and bounded selection.

Do not build an index now; first terminalize state and measure real scaling.

---

## P-010 Knowledge positive-path work may reveal route/taxonomy competition

**Basis**

Current route selects generic K001 governance Knowledge. Once chip/IP categories are added, domain facts may compete with generic governance nodes under fixed Context budgets.

**Probability:** MEDIUM
**Impact:** MEDIUM-HIGH

**Minimal test after project taxonomy change:** A creates source-backed SRPWM candidate; validation/promotion; B must select domain fact; unrelated C must not.

---

# 8. Repair Decision Matrix

| Problem | Must repair? | Owner | Minimal direction | Decision |
|---|---|---|---|---|
| Validation FAIL recovery + stale PASS symmetry | YES P0 | checkpoint + Ledger | current validation state recoverable; failure history preserved; checkpoint/freshness semantics explicit | REPAIR_NOW after P-001 discriminating test |
| Context successful task never terminalizes | YES P0 | context closure + ContextManager | one canonical terminal Context commit | REPAIR_NOW |
| Task B exact priorContext omission cause | YES, but isolate first | Context selector/budget | instrument/compose exact candidate, overlap, budget, omission reasons | OBSERVE_FIRST |
| Context fact provenance over-broad | YES before broad continuity rollout | Reflection/Context contract | fact-level or non-misleading refs; do not widen selector blindly | DESIGN_BEFORE_REPAIR |
| Begin orphan | YES P0 | Gateway/Runtime lifecycle | explicit transactional/compensated failure path; no unreachable active state | REPAIR_NOW, design gate required |
| Complete replay | YES P0 | Governance Runtime/Gateway | allow CLOSED Turn to return existing COMPLETE receipt; preserve input identity/idempotency | REPAIR_NOW |
| Observation durability | YES P1 | Governance Runtime / existing Event Store | persist bounded untrusted observation body/ref in existing durable plane | DEFER_UNTIL_P0_STABLE |
| Route/Context breadth | YES P1 | routing/projection | measure selection value/budget; reduce generic content after continuity | DEFER |
| Gate/Evidence/Experience observability | YES P1 | existing status/receipt projection | expose bounded receipts through existing tools, no new tool | DEFER |
| ATP Knowledge taxonomy | YES project work | ATP project knowledge owner | add chip/IP hardware, driver gap, test constraint categories | PROJECT_OWNER AFTER P0 |
| SRPWM SDK/content defects | YES project backlog | SDK/test/capability owners | separate project remediation | PROJECT_OWNER |

---

# 9. Repair Architecture / Reliability Requirements

## R1 Validation recovery — minimum reliable invariant

### What must change

- Historical trusted FAIL must remain append-only evidence.
- Current validation obligation state must not treat trusted FAIL as an irreversible terminal state.
- A later trusted PASS for the same validation/target may change **current** state to SATISFIED while preserving old violation history.
- A validation already SATISFIED must not silently remain fresh after a relevant later mutation.

### Lightweight direction

Do not make all `VIOLATED` states recoverable. Only `VALIDATION` semantics may recover from later trusted Evidence. WRITE_SCOPE and structural safety violations must remain fail-closed unless an explicit safe policy exists.

Checkpoint scheduling must not be `PENDING-only` for recoverable validation. Candidate strategies, ordered from simpler to more complex:

1. run all frozen validation obligations on every explicit checkpoint; or
2. maintain a small validation-dirty state/epoch and run PENDING/VIOLATED/dirty validations.

Before choosing, execute P-001 to prove whether stale PASS already exists. If yes, design must solve FAIL recovery and PASS invalidation together; do not patch only `VIOLATED -> PENDING`.

### Required tests

- FAIL -> PASS same Turn;
- PASS -> FAIL;
- PASS -> allowed mutation -> checkpoint must not reuse stale PASS;
- old failure remains in history but no longer current blocker after later trusted PASS;
- forged Agent PASS still cannot recover violation;
- WRITE_SCOPE violation remains non-recoverable by validation PASS.

---

## R2 Context lifecycle — minimum reliable invariant

### What must change now

Successful governed Task closure must end with canonical Context state `COMPLETED` and `phase=complete`.

Current adapter should not perform several semantically coupled durable writes and then separately rely on status compatibility.

### Preferred lightweight architecture

Add one ContextManager-owned operation such as:

```text
finalizeTaskClosure(...)
```

which:

1. loads current session + version；
2. validates all proposed TaskLedger/Progress/WorkingSet changes in memory；
3. builds the final `COMPLETED` ContextSession；
4. performs one CAS/state update；
5. returns the final state version used in closure receipt。

This is lighter and safer than:

```text
update ledger
update progress
replace working set
complete
```

because it removes partial closure windows and makes Context lifecycle owned by ContextManager.

### What must NOT happen

- do not add another Context store；
- do not make Closure Coordinator manipulate Context internals；
- do not keep adding special `ACTIVE + marker` cases as the normal path；
- do not broaden historical selection before provenance/budget behavior is understood。

### Backward compatibility

Existing historical `ACTIVE + Close governed Turn` records may remain readable as legacy compatibility, but all new successful closures must write `COMPLETED`.

---

## R3 Prior Context selection — diagnosis before patch

Because current code already accepts closed-marker ACTIVE sessions, B omission is not uniquely explained.

Before changing selection logic, add a deterministic composed test that records:

- current workingSet refs；
- historical candidate task IDs/status/lastAction；
- matchedRefs；
- base inline char count；
- remaining inherited budget；
- per-candidate omit reason；
- final generated `prior-context-*` item；
- Gateway projected `priorContext`。

Only then decide whether actual cause is:

- lifecycle；
- budget；
- reference matching；
- later projection。

This is a mandatory `OBSERVE_FIRST` boundary.

---

## R4 Begin atomicity — failure must be terminal/recoverable, not invisible

### Proven invariant violation

`openTurn` can commit durable state before Gateway knows it can publish a valid task snapshot.

### Repair requirements

Any failure after Runtime open must end in one of only two states:

1. **no governed task became durable**, or
2. **a durable explicitly terminal ABORTED/FAILED begin record exists and is publicly recoverable/inspectable**.

Unreachable ACTIVE state is forbidden.

### Reliability constraint

Do not “rollback by deleting” append-only Event Store history. If compensation is used, it must terminalize/abort state rather than erase evidence.

### Design options to evaluate

- prepare/commit split with no persistent open before Context structural validation；
- or explicit Runtime compensation/abort after post-open Gateway failure。

The chosen option must also handle snapshot I/O failure and process loss, not only `CONTEXT_CONTRIBUTOR_UNAVAILABLE`.

Because this spans Runtime, Context and Event lifecycle, implementation should not begin until exact terminal semantics are written in a small state transition table.

---

## R5 Completion replay — reuse existing Kernel authority

### Proven source fact

Kernel Closure Coordinator already returns existing COMPLETE receipt idempotently.

### Required change

Runtime must not reject a CLOSED Turn before consulting its durable closure state.

A same-input replay must return the same durable closure identity with zero new side effects.

Different replay input must fail closed with an explicit conflict/fingerprint mismatch, not silently return unrelated success.

### Minimal tests

- same request twice same process；
- same request after Gateway restart；
- same request after Runtime rehydrate；
- changed Reflection/request after COMPLETE => conflict；
- exactly one finalization/closure receipt remains。

Do not rewrite Closure Coordinator.

---

## R6 Observation durability — reuse existing durable plane

Do not create a second Event Store.

The existing bounded observation already has digest/ref semantics. Persist either:

- the bounded observation body as an explicitly untrusted Work Observation event in existing Execution Event Store；or
- a content-addressed durable object referenced by that Event Store。

Requirements:

- Agent observation remains untrusted；
- max item/turn limits remain bounded；
- restart/replay can reconstruct exact evaluated body；
- no ordinary narrative becomes trusted Evidence solely because it is durable。

P1; do after R1-R5.

---

# 10. Repair-Induced Risk Analysis

## Risk A — naive validation recovery weakens safety

If generic `VIOLATED -> PENDING/SATISFIED` is allowed, a later unrelated PASS could accidentally clear WRITE_SCOPE or other structural violations.

**Guard:** recovery transition only for VALIDATION obligations and exact validation target identity.

## Risk B — fixing Context inheritance may create pollution

If we only force `COMPLETED` or widen selector, current broad touchedRefs can push irrelevant facts into B/C.

**Guard:** composed related/unrelated tests and fact-level provenance plan before declaring continuity PASS.

## Risk C — naive begin rollback destroys audit history

Deleting Event Store/journal to simulate atomicity violates append-only Evidence principles.

**Guard:** two-phase prepare or explicit terminal compensation, never evidence deletion.

## Risk D — replay cache can create second completion authority

If Gateway stores its own independent completion truth, it can diverge from Kernel Closure.

**Guard:** Kernel/Runtime durable Closure remains sole authority; Gateway only projects it.

## Risk E — durable observations accidentally become trusted Evidence

Persistence is not trust.

**Guard:** durable Work Observation retains explicit Agent/untrusted provenance; Ledger trust policies unchanged.

## Risk F — extra observability bloats MCP Context

Adding full Architecture/Gate/Evidence payloads can worsen current 17.5K budget issue.

**Guard:** expose bounded decision receipts/omission reasons, not full libraries.

---

# 11. Required Fix Acceptance — Next Repair Campaign

Before repair, freeze exact source and create a dedicated branch from canonical mainline. Codex remains Test Executor unless explicitly reassigned.

## A. Validation lifecycle

A1. trusted FAIL -> current violation；
A2. allowed correction；
A3. same frozen validator actually reruns；
A4. later trusted PASS -> current SATISFIED；
A5. old FAIL event/violation remains auditable；
A6. PASS -> later mutation -> old validation cannot remain silently fresh；
A7. forged PASS cannot recover；
A8. WRITE_SCOPE violation cannot be cleared by validation recovery。

## B. Context lifecycle

B1. real Context closure produces exactly one terminal `COMPLETED` session；
B2. no partial ledger/progress/working-set state under injected closure failure；
B3. closure receipt stateVersion points to final terminal record；
B4. historical legacy ACTIVE+close record remains readable only as compatibility。

## C. Cross-task Context

C1. A completed with source-specific confirmed/openIssues；
C2. related B gets bounded priorContext；
C3. unrelated C gets zero A facts；
C4. Context near current real project size cannot silently starve priorContext without an explicit omission reason；
C5. one domain-overlap B gets only matching facts；
C6. no task still ACTIVE after successful completion。

## D. Begin failure atomicity

D1. contributor unavailable；
D2. malformed/partial Context projection；
D3. snapshot write failure；
D4. fault after Runtime open before snapshot；

For all: no unreachable ACTIVE Turn/Context/Event Store. Any durable failure record must be terminal and recoverable.

## E. Completion replay

E1. exact COMPLETE replay same process；
E2. exact replay after Gateway restart；
E3. exact replay after Runtime rehydrate；
E4. changed request conflicts；
E5. finalization count remains 1。

---

# 12. Mandatory Non-Regression Contract

Every P0 repair must rerun the already-proven stable capabilities; otherwise a local fix cannot be accepted.

1. Machine Environment remains D-drive owned；
2. fixed Node `v22.23.2`；
3. checkout-local node_modules absent；
4. npm invocation count 0；
5. exact 8 MCP tools unchanged；
6. wrong project fails before Runtime；
7. missing/unknown fingerprint staged correctly；
8. missing/malformed TaskIntent fail-closed；
9. ET6801/SRPWM classification remains correct；
10. natural-language `and` not parsed as IP；
11. Required Read 7/7 trusted；
12. WRITE_SCOPE protected/outside path blocks；
13. Agent forged validation remains non-authoritative；
14. premature completion blocked；
15. Supervisor pending/satisfied/violated/complete stable；
16. meaningful Reflection accepted；
17. 8 mandatory Closure modules one-shot happy path PASS；
18. Knowledge narrative no-pollution boundary PASS；
19. stable Runtime/State owner unchanged unless candidate explicitly activated；
20. no second Runtime/Ledger/Event/Context/Knowledge store introduced。

This list is not optional. A repair is not accepted if its own tests pass but one of these proven behaviors regresses.

---

# 13. Do Not Fix In The P0 Framework Round

To prevent scope explosion, do not mix these into the lifecycle repair:

### Project content / SDK

- ET6801 hardware 18 SRPWM vs SDK Driver 12；
- DMA selection write commented out；
- SRPWM UnitTest API drift；
- missing ET6801 SRPWM requirement；
- mojibake cross-chip requirement JSON；
- 7,686 capability `no_semantic_mapping`；
- HIL/FPGA cases。

These belong to ATP/SDK owners.

### P1 quality work

- general Architecture route narrowing；
- generic Knowledge ranking optimization；
- Gate/Evidence/Experience richer projection；
- full Observation durability if it risks widening P0 scope。

### Knowledge taxonomy

Add chip/IP categories only after the P0 continuity path is stable enough to test A->Knowledge->B reuse without confusing framework and project taxonomy failures.

---

# 14. Remaining Unknowns / Required Discriminating Tests

The following must remain explicit unknowns:

1. **Why exactly B priorContext disappeared**: status lifecycle is wrong, but current selector allows closed-marker ACTIVE; budget/ref-match/selection omission must be distinguished mechanically.
2. **Does a trusted PASS remain stale after later allowed mutation?** High-risk symmetric prediction; not yet executed.
3. **Can active supervised Turn rehydrate across process restart and continue correctly?** Not executed.
4. **Can closed completion replay after restart?** Same-process replay already fails; restart not executed.
5. **What is desired semantics for a valid project task with no project Context contributor?** Project-level read-only generic fallback vs fail-closed needs architecture decision; regardless, no orphan is allowed.
6. **What exact fact-level provenance contract should Context Reflection use?** Current string + global touchedRefs is insufficient for precise cross-task inheritance.
7. **How much priorContext budget must be reserved under realistic ATP contribution size?** Current “zero if inline already 16K” policy conflicts with strong continuity goals.

No implementation should silently choose answers for these architectural questions.

---

# 15. Final Repair Readiness

Overall status:

`REPAIR_NOT_YET_PROVEN`

Reason:

- Validation root cause and Closure replay root cause are sufficiently isolated for targeted design/test-first repair；
- Context terminalization defect is proven, but Task B omission has at least budget/ref-match candidates that must be mechanically distinguished before selector changes；
- Begin orphan root cause is proven, but the final lightweight compensation/transaction semantics must be fixed on paper before implementation because deleting append-only audit state is forbidden。

### Safe next action

Before product repair, create a **P0 lifecycle repair requirement** containing only:

1. R1 Validation current-state recovery + stale-PASS discriminating test；
2. R2 Context terminalization + module atomicity；
3. R3 Prior-context diagnostic composed test before selector modification；
4. R4 Begin failure terminal/compensation semantics；
5. R5 Closed-turn idempotent replay；
6. exact non-regression matrix from Section 12。

Only after those acceptance criteria are frozen should code change.

This is the control that prevents “修复 -> 新测试 -> 不知道新问题来自哪里 -> 无限循环”。
