# Project Admission Round 2 Defect Backlog

Tested source SHA: `2bf842597415ef235d52fc213c197e50ac2cb89e`

No product defect was repaired or modified during this campaign.

## PA-SRPWM-001 — verified fixed in the executable isolated scope

- Previous status: `OPEN / Framework defect`
- Round 2 status: `VERIFIED_FIXED` at the Project Admission boundary
- Severity: former `P1`
- Expected: after Architecture changes from v1 to v2 in the same Gateway/controller, submission
  of the old v1 fingerprint returns `PROJECT_CONTEXT_REQUIRED`, returns the v2 Architecture
  Bootstrap, and does not enter downstream Governance.
- Actual: old v1 was rejected; returned fingerprint was v2; Bootstrap title changed to v2;
  `bootstrapReads=2`; instrumented downstream Runtime/Library/Event counters remained `0/0/0`.
- Fresh control: submitting the returned v2 fingerprint plus valid TaskIntent produced `ACTIVE` and
  exactly one downstream Governance begin.
- Evidence: `raw_test_results.jsonl#PA2-A05`, `raw_test_results.jsonl#PA2-A08`, target committed test
  “Previously accepted fingerprint is revalidated after Architecture changes”.
- First failing boundary: none in the executed Project Admission scope.
- Attribution: Framework repair verified.
- Qualification: real durable Runtime/Ledger/Event Store zero-state was not independently queried;
  controlled activation remains prohibited.

## PA-SRPWM-002 — prior semantic-binding finding remains outside this repair

- Status: `OPEN / NOT_REPAIRED / NOT_RECLASSIFIED`
- Origin: first-round evidence at source SHA `67676a2916b01316794da042a813d0c338d14182`.
- Prior observation: a structurally valid but semantically contradictory TaskIntent containing
  `ip=AND` was accepted by Project Admission.
- Round 2 observation: this repair does not change TaskIntent semantic validation. Positive tests
  prove that when the Agent supplies correct ETIMER/XBAR/SRPWM entities, canonicalization places the
  concrete IP before human prose and `and` is not the first IP candidate.
- This round's requirement assigns open-language understanding to the Agent before TaskIntent, so
  no new expectation was introduced that Framework must semantically reclassify or reject a
  well-formed but wrong Agent TaskIntent.
- Evidence: `raw_test_results.jsonl#PA2-NL01..PA2-NL04`; first-round
  `11_project_admission_srpwm_test_executor_20260902.md#PA-SRPWM-002`.
- First failing boundary: not rerun as a negative semantic-binding control in Round 2.
- Attribution: Framework/Architecture contract boundary requires Architecture Owner disposition;
  it is not attributable to the stale-fingerprint repair.

## PA2-ENV-001 — real Governance chain unavailable in isolated checkout

- Status: `ENVIRONMENT_LIMITATION`
- Severity: blocks current-SHA Runtime regression evidence; not classified as a product failure.
- Stimulus: execute committed frozen Runtime wiring, Runtime release and MCP protocol tests from the
  current checkout without dependency installation.
- Actual:
  - `frozen-runtime-wiring.test.mjs`: module load failed because `zod` is absent;
  - `runtime-release.test.mjs`: module load failed because `@deepseek-ai/cordis` is absent;
  - `mcp-protocol.test.mjs`: module load failed because `@modelcontextprotocol/sdk` is absent.
- Test bodies executed: `NO`.
- Stable D-drive fallback used: `NO` (explicitly prohibited).
- Consequence: Project/Architecture/Rule/Knowledge/Gate routes inside the real Runtime, Required
  Read, Trusted Validation, Supervisor, Ledger, Event Store, Reflection and Closure are
  `NOT_EXECUTED` for this SHA.
- Evidence: `FINAL_REPORT.md#runtime-dependent-test-entry-results` and
  `module_behavior_matrix.json`.
- First failing boundary: isolated checkout dependency resolution before Runtime/MCP construction.
- Attribution: Environment limitation.

## PA2-OBS-001 — durable zero-state before admission not directly proven

- Status: `OBSERVABILITY_GAP / BLOCKED_BY_ENVIRONMENT`
- Expected proof: query real Runtime Turn, Ledger and Event Store before and after missing/unknown/
  stale fingerprint requests and show no identities, obligations or events were created.
- Available proof: Project Admission did not call the downstream Governance begin boundary; local
  checkout runtime-state directories remained absent.
- Missing proof: an independent query of the real Runtime owners at the tested SHA.
- Reason: stable Runtime activation was prohibited and the isolated Runtime entry could not load.
- First failing boundary: no authorized/executable read-only Runtime state surface in this checkout.
- Attribution: Observability gap blocked by Environment limitation.

## PA2-BASELINE-001 — total software gate rejects root layout

- Status: `FAIL / PRE-EXISTING BASELINE-AND-LOCAL-LAYOUT ISSUE`
- Test: `.\.venv\Scripts\python.exe tools\validate_pc.py`
- Actual: `1 failed, 842 passed, 9 skipped`.
- Failing check:
  `test_formal_code_root_has_only_stable_categories`.
- Unexpected root directories: tracked `docs/` and ignored local `tmp/`.
- Attribution evidence:
  - `docs/` is present in the tested SHA and was first added by
    `fe4fdeafcda47195f169f29539c2e3c21e19ef0e`;
  - `tmp/` is not tracked, is ignored, and predates this campaign (`2026-08-31 12:41:39`);
  - the Project Admission repair range changed only Project Admission source and its test.
- First failing boundary: repository formal-code-root layout policy.
- Attribution: Project content/baseline layout plus pre-existing local ignored content; not the
  stale-fingerprint repair.
- Action: evidence only; no cleanup or repair performed.

## New product defects discovered in Round 2

`0` in the executable Project Admission scope.

This statement does not convert `NOT_EXECUTED` or `OBSERVABILITY_GAP` modules into PASS and does not
close the prior `PA-SRPWM-002` Architecture contract question.
