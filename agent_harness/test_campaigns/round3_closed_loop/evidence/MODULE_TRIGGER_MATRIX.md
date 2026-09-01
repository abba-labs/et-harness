# Round 3 Module Trigger Matrix

| Module | Result | Enforcement | Evidence |
|---|---|---|---|
| Gateway health | TRIGGERED_PASS | MECHANICAL | `01_gateway_health.md` |
| Project routing | TRIGGERED_PASS | MECHANICAL | `02_begin_and_routing.json` |
| Invalid workspace rejection | TRIGGERED_PASS | MECHANICAL | `02_begin_and_routing.json` |
| Task Context compilation | TRIGGERED_PASS | MECHANICAL | `03_context_contract.json`, `08_validation.md` |
| Architecture/rule routing | TRIGGERED_PASS | WORKFLOW_ENFORCED | `03_context_contract.json` |
| Knowledge consultation | TRIGGERED_PASS | WORKFLOW_ENFORCED | `04_knowledge_consult.md` |
| Evidence observation | TRIGGERED_PASS | MECHANICAL | `05_work_observations.jsonl` |
| Allowed write preflight | TRIGGERED_PASS | MECHANICAL | `06_preflight_negative.md` |
| Protected write preflight | TRIGGERED_FAIL | MECHANICAL | `06_preflight_negative.md` |
| Output scope | TRIGGERED_PASS | MECHANICAL | `07_outputs.md`, `08_validation.md` |
| Validation commands | TRIGGERED_PASS | MECHANICAL | `08_validation.md` |
| Supervisor validation acceptance | EXPECTED_BUT_NOT_TRIGGERED | MECHANICAL | `08_validation.md`, `12_final_closure.md` |
| Premature completion block | TRIGGERED_PASS | MECHANICAL | `09_premature_complete.md` |
| Knowledge capture decision | TRIGGERED_PASS | WORKFLOW_ENFORCED | `10_knowledge_capture.md` |
| Knowledge classification/promotion | NOT_APPLICABLE | MECHANICAL | `10_knowledge_capture.md` |
| Context update/persistence | EXPECTED_BUT_NOT_TRIGGERED | MECHANICAL | `11_context_update.md` |
| Obligation ledger | TRIGGERED_FAIL | MECHANICAL | `12_final_closure.md` |
| Reflection | EXPECTED_BUT_NOT_TRIGGERED | MECHANICAL | `12_final_closure.md` |
| Closure | EXPECTED_BUT_NOT_TRIGGERED | MECHANICAL | `12_final_closure.md` |
| Next-task rehydration | EXPECTED_BUT_NOT_TRIGGERED | WORKFLOW_ENFORCED | `13_rehydration.md` |

## Mandatory negative controls

| Control | Result | Evidence |
|---|---|---|
| Invalid workspace rejects | PASS | `02_begin_and_routing.json` |
| Protected/out-of-scope preflight rejects without mutation | FAIL_CRITICAL (allowed, no mutation performed) | `06_preflight_negative.md` |
| Premature completion blocked | PASS | `09_premature_complete.md` |
| Unsupported knowledge not promoted | PASS | `10_knowledge_capture.md` |
| Follow-up has no manual previous-task injection | PENDING upstream Closure gap | `13_rehydration.md` |
