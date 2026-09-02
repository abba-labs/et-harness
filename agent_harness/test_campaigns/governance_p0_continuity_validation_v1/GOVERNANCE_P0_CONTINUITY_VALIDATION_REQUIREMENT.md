# Governance P0 Continuity / Closure Validation Requirement V1

## Role and target

Role: Test Executor only.

Repository: `abba-labs/et-harness`
Branch: `architecture/governance-p0-continuity-closure-v0.1`
Candidate product baseline before this requirement document: `6ef5a4cdc541483917c1cff8ef6663290f25b589`

The Test Executor MUST lock the exact remote HEAD before execution and record both the tested commit and the product-file blob identities. This requirement document is evidence/test-only and does not authorize product repair.

## Hard constraints

- Do not modify Framework product source while testing.
- Do not modify ATP Project Plugin, Architecture, Rules, Knowledge, Gates or Validation to make tests pass.
- Do not modify Supervisor, Ledger, Closure, Context or Knowledge policy during the campaign.
- Do not install/upgrade dependencies merely to make a test green.
- Do not weaken trusted Evidence, Required Read, WRITE_SCOPE, Gate or Completion boundaries.
- Do not introduce a second Context Store, Knowledge Store, Event Store, Runtime, watcher or daemon.
- Preserve the currently stable D-drive Runtime until focused candidate checks are green. Any later real Runtime activation must use the existing deterministic freeze/verify/controlled-refresh process and preserve a rollback point.
- On a failure: record first failing boundary and mechanical evidence; do not repair automatically.

## Validation goals

### A. Closure Atomicity / Retry

Prove on the real public Kernel and, when real Runtime activation is available, through the Runtime/Gateway path:

1. Open Turn + malformed Reflection (for example missing `contractVersion`) returns ERROR.
2. After that error, the Turn remains `OPEN`.
3. `closingAt` is not persisted by the failed attempt.
4. `closureAttemptCount` is not advanced by a pre-seal validation failure.
5. New observations/refs can still be appended if the Host has not frozen supervised readiness.
6. Corrected Reflection on the same Turn succeeds.
7. The Turn is sealed exactly once only after the corrected Reflection validates.
8. Reflection is persisted once and Closure can reach COMPLETE.
9. If the OPEN Turn changes while Reflection is being prepared, the stale prepared Reflection is rejected and a retry using current Turn state succeeds.
10. Existing successful Reflection replay/content-address behavior does not regress.

### B. Cross-task Context Continuity

Use two distinct taskIds in the same project.

Task A must persist a confirmed item and an open issue with concrete Architecture/Rule/Knowledge/Gate refs through the existing Context Closure path.

Then prove:

1. Task B with a related route automatically receives a bounded `prior-context-*` item.
2. The prior open issue is visible to the Agent through the public `harness_begin` result as `context.priorContext`.
3. A prior Task whose Turn was closed but Context task status is still ACTIVE is eligible only when its durable progress ledger carries the `Close governed Turn ...` closure marker.
4. A separate live ACTIVE task without that closure marker is not inherited.
5. An unrelated Task C with no route-ref overlap does not receive Task A context.
6. Maximum inherited tasks <= 4.
7. Inherited Context total <= 4 KiB and each item <= 1.6 KiB.
8. Existing Project Context contribution inline items are preserved.
9. No second Context persistence owner is created; Evidence State remains the canonical backing state.

### C. Knowledge Later Consumption

Do not change Knowledge Manager unless this test proves a Knowledge-owned defect.

1. Task A creates one uniquely identifiable Project Knowledge Candidate through normal Reflection/Closure.
2. Confirm Candidate persistence and reindex.
3. Confirm direct Knowledge Manager search can return the Candidate after persistence.
4. Start a new related Task B after bootstrap/admission succeeds.
5. Confirm real Auto Governance `route.knowledgeIds` reaches that Candidate when the task query is relevant.
6. Confirm the Agent receives the routed Knowledge through the normal governed Context.
7. Confirm Candidate trust remains `EXPLORATORY / HYPOTHESIS_AND_TEST_LEAD_ONLY`; do not treat it as validated fact.
8. An unrelated Task C must not receive the Candidate merely because it exists.
9. If later consumption still fails, distinguish Knowledge search/index failure from upstream project/context routing failure.

### D. Knowledge Trigger Contract V0.1

Prove the public trust boundary without weakening it:

1. Ordinary Agent prose saying knowledge is wrong does NOT become a trusted automatic verification.
2. `source://...` observation ref triggers `captureMode=CHECK` and `validationMode=DOCUMENT`.
3. `evidence://...` observation ref triggers `captureMode=CHECK` and `validationMode=EVIDENCE_CHECK`.
4. Runtime-owned tool error can trigger CHECK but does not manufacture verification evidence.
5. SUPPORT/CONTRADICT persistence still requires valid `source://` or `evidence://` basis refs.
6. A source-backed contradiction can be proposed by Reflection and recorded by the existing verification path.
7. No Agent narrative is accepted as trusted PASS/Evidence.

### E. Governance Decision Receipt / Observability

Prove the system exposes bounded read-only reasoning receipts without changing execution authority:

1. `AutoGovernanceTaskStatus.routeDecision.schema = auto-governance.route-decision.v0.1`.
2. Receipt exposes bounded query preview/hash, seed candidates, selected route, trace, omissions and Context contribution IDs.
3. `harness_status` exposes the same bounded `routeDecision`.
4. Existing selected Architecture/Rule/Knowledge/Gate route is unchanged by receipt generation.
5. Receipt generation does not alter ContextEnvelope, Context hash, Ledger, Event Store or Completion authority.
6. Knowledge observation/closure summaries use the actual `consultMode` field and expose it through `knowledgeConsultationMode` / `knowledge.consultationMode`.
7. Existing pending review packets continue to expose provider IDs through the current status path.
8. No watcher/daemon/new persistence owner is introduced.

## Mandatory regression set

In addition to A-E, rerun the strongest already-proven safety paths that are executable in the approved environment:

- Project Admission exact project / Architecture Bootstrap / TaskIntent sequence.
- stale Architecture fingerprint rejection.
- ET6801/ETIMER + `IP and SDK` does not become `ip=and` with correct TaskIntent.
- 8 intended public MCP tools only.
- Project/Architecture/Rule/Knowledge/Gate routing.
- Required Read trusted ingress.
- forged validation cannot satisfy Ledger.
- Runtime-owned trusted validation can satisfy matching obligations.
- protected WRITE_SCOPE preflight BLOCK.
- premature completion BLOCK.
- Execution Supervisor / Obligation Ledger / Event Store.
- normal Reflection + 8 mandatory Closure adapters.
- active Turn rehydrate/replay.
- Closure failure/retry recovery.

## Execution order

1. Lock SHA and record clean worktree.
2. Run focused/unit tests for the changed public owners only.
3. Run existing repository software gate without changing dependencies.
4. If focused tests fail: stop, preserve evidence, no activation.
5. If focused tests pass and the standard deterministic candidate Runtime can be produced without dependency churn, create a new candidate release using the existing freeze process. Do not mutate the stable release in place.
6. Verify candidate environment using the existing environment verifier.
7. Preserve stable release/Gateway rollback identity before any controlled refresh.
8. Controlled external Gateway refresh to the candidate only after environment verification passes.
9. Run direct MCP smoke and real black-box A-E + regression scenarios.
10. If candidate Runtime/Gateway fails, restore the previous stable release/Gateway and record rollback evidence.

## Evidence requirements

Produce at minimum:

- `FINAL_REPORT.md`
- `module_behavior_matrix.json`
- `negative_controls.json`
- `state_diffs.json`
- `replay_and_retry.md`
- `context_continuity.json`
- `knowledge_later_consumption.json`
- `knowledge_trigger_contract.json`
- `route_decision_receipt.json`
- `defect_backlog.md`
- raw command/test logs sufficient to reproduce every PASS/FAIL

For every result record:

- tested SHA
- test/scenario ID
- exact input/stimulus
- expected owner/trigger
- actual owner/decision
- before/after Runtime Turn status
- before/after Ledger/Event Store/Context/Knowledge state where applicable
- evidence/event refs
- PASS / FAIL / NOT_EXECUTED / OBSERVABILITY_GAP
- first failing boundary
- attribution: Framework defect / Project content gap / Test fixture / Environment limitation / Observability gap / Blocked by upstream

Do not convert NOT_EXECUTED or historical PASS into current-SHA PASS.
