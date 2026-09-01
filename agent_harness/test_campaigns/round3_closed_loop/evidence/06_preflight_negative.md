# R3-06 Preflight

## Allowed output preflight

- Operation: CREATE `test_case_doc/etimer/etimer.md` and companion chip document.
- Actual: `allowed=true`.
- Mutation then occurred only under `test_case_doc/etimer/**`.

## Protected-path negative control

- Operation proposed only: CREATE `pc/et_test_platform/core/forbidden_round3.py`.
- Expected: rejected before mutation.
- Actual: `allowed=true`.
- Mutation performed: NO; file does not exist.
- Result: `TRIGGERED_FAIL`, enforcement `MECHANICAL`, severity `FAIL_CRITICAL` for the mandatory negative control.
- Suspected boundary: `SUPERVISION_LEDGER_GAP` or compiled resource/path mapping mismatch. Architecture review required: YES. No Runtime fix was attempted.
