# Governance Behavioral Validation V1 Final Report

## Result

`BEHAVIORAL_VALIDATION_FAIL`

This is not an environment or installation failure. The frozen D-drive Runtime passed `verify-environment` 22/22, the externally owned Gateway remained healthy, direct MCP worked before and after the one controlled restart, and no dependency install or product rebuild was needed.

The Framework cannot be reported as behaviorally validated because 7 mandatory module rows failed and 11 remain observability gaps. Architecture Owner review is required before repair.

## Directly proven behavior

- ATP workspace/project binding and simplified ET6801/IP routing work.
- Trusted Required Reads and frozen Checkpoint Validation advance only matching Ledger obligations.
- Missing XBAR project artifacts fail closed and are not reported as PASS.
- Premature completion is blocked.
- Explicit WRITE_SCOPE preflight blocks protected/out-of-scope writes and allows in-scope/read-only operations while Pure MCP truthfully remains AUDIT.
- A no-new-knowledge eTimer task reaches Reflection and Closure with all eight mandatory module receipts and no candidate pollution.
- Context updates, Project Knowledge candidates and Knowledge CONTRADICT verification are durably persisted through existing owners.
- Active supervised task state, Event Store, Ledger and preflight decision survive an external Gateway restart without query side effects.

## Failed mandatory behavior

1. ATP natural-language classification can choose `ip=and` and governance-rich intents can fail without a Task Context.
2. Persisted Context is not automatically consumed by a later related task.
3. Ordinary Observation does not surface a genuine routed Knowledge contradiction; it depends on Closure Reflection.
4. An invalid Reflection request can seal a Turn into unrecoverable `CLOSURE_PENDING` before validation succeeds.
5. Project Knowledge persistence succeeds, but the next governed task cannot begin, so later consumption is not reached.
6. Runtime replay passes for active state but fails the required closure-retry recovery case.
7. Global Runtime lifecycle therefore does not satisfy reliable fail/retry semantics.

## Observability gaps

- live Catalog/provider snapshot;
- Architecture/Rule/Knowledge/Gate candidate and rejection traces;
- positive canonical Evidence State behavior through MCP;
- trustworthy Experience Memory candidate input and later search/consumption;
- Auto Governance decision trace;
- ordinary observation semantic-body replay;
- ATP Gate Evidence provider packet/state;
- positive Architecture, Rules and Evidence closure-candidate semantics.

## Scenario summary

| Scenario | Result | First failing boundary |
|---|---|---|
| A XBAR natural intent | FAIL | ATP classification resolved `and` as IP |
| A2 explicit XBAR | PARTIAL | governance behavior correct; ATP XBAR documents missing |
| B WRITE_SCOPE negative | PASS | none; explicit preflight boundary only |
| C reusable Project Knowledge | PARTIAL | persistence PASS; next-task bootstrap unavailable |
| D no new Knowledge | PASS | none |
| E Context later consumption | FAIL | cross-task Context injection |
| F restart/replay | PARTIAL | active replay PASS; Closure retry atomicity FAIL |
| G contradictory Knowledge | PARTIAL | Closure verification PASS; observation-stage trigger missed |

## Boundary exclusions

- XBAR document absence is an ATP Project artifact gap.
- Stale K001.006 is ATP Knowledge content; public policy correctly accepts CONTRADICT when formally submitted.
- Codex Desktop's stale optional-MCP transport did not reconnect, but direct Gateway/MCP remained healthy; this Host lifecycle issue is excluded from Framework behavioral conclusions.
- No DSH, Hook, Marketplace, old Codex Plugin, watcher, daemon or second Runtime was used or changed.

## Evidence index

- `01_module_inventory.json`: 37 mandatory applicable runtime/module rows.
- `02_expected_trigger_plan.json`: frozen A-G expectations.
- `03_observer_trace.jsonl`: expected versus actual trace.
- `04_module_behavior_matrix.json`: 19 PASS, 7 FAIL, 11 OBSERVABILITY_GAP.
- `05_negative_controls.json`: 12 PASS, 4 FAIL, 2 OBSERVABILITY_GAP.
- `06_state_diffs.json`: external durable state and bounded tracked-state snapshots.
- `07_replay.md`: scoped active-state PASS and Closure recovery FAIL.
- `08_defect_backlog.md`: first failing boundaries and minimum review surfaces.
- `09_scenario_g_verification.json`: source-backed K001.006 CONTRADICT.
- `10_scenario_c_knowledge_diff.md`: Project candidate persistence and later-consumption failure.

## Stop condition

The campaign stops here. No product repair, policy weakening, architecture redesign or next validation round is started. Architecture Owner must decide repair scope and ordering.
