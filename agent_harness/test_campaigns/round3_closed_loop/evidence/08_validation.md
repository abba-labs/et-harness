# R3-08 Validation

Timestamp: `2026-09-01T17:08:58+08:00` (first ladder), followed by one corrected rerun.

| Validation | Final exit | Bounded result |
|---|---:|---|
| `python tools/governance/compile_task_context.py check --context project-governance/runtime/current_task_context.json` | 0 | Task Context is current |
| `python tools/governance/compile_task_context.py scope-check --context project-governance/runtime/current_task_context.json` | 0 | 2 changed paths, both in scope |
| `python tools/quality/check_public_ip_contracts.py` | 0 | 14 documents passed |
| `python tools/quality/validate_case_plans.py test_case_doc/etimer/etimer.md` | 0 | 1 document passed |
| `python tools/quality/validate_chip_ip_docs.py` | 0 | passed |

First document run found invalid `semantic_ref` levels and a malformed Chip Summary row. The output documents were corrected to the frozen schema; no Checker or rule was changed.

Observed limitation: submitting these successful tool observations through `observeWork` created OBS records but did not satisfy any Supervisor validation obligation. All validation obligations remained PENDING because no trusted Host execution-event producer is reachable through the fixed MCP adapter.

Campaign-level final scope-check returned exit 1 only for the 16 files under `agent_harness/test_campaigns/round3_closed_loop/evidence/**`: the eTimer Project Context allows only `test_case_doc/etimer/**`, while the user-authorized Charter requires committed evidence in the campaign directory. The two product documents remained in scope. This is recorded as a routing mismatch and was not bypassed by widening the project map or weakening the checker.
