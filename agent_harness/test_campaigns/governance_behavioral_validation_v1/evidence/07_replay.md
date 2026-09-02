# Governance Behavioral Validation V1 Replay Evidence

## Controlled boundary

Only the externally owned MCP Gateway was restarted. No Runtime build, dependency install, plugin install, Codex restart, environment rewrite or product modification was used.

- Before restart Gateway PID: `7520`
- After manual external start Gateway PID: `46224`
- Post-restart `/health`: HTTP 200, `status=UP`
- Direct MCP after restart: `initialize`, `tools/list`, `harness_health` PASS

## Pre-restart supervised state

Task `gbv1-restart-replay`:

- Runtime: `codex-runtime-642241ba-68c0-4272-aeaa-bbc421f64914`
- Turn: `codex-turn-18e69c76-a838-4122-83a2-6d1129a6b54c`
- Project revision: `aa01338ca7682661d4150c39c3d0706d6702d95f`
- Context revision: `e1ccf7044ffc55f8b5b97e022781bb3d770197e816d3da2deff0a4c0f2268145`
- Satisfied: 7 REQUIRED_RESOURCE + 5 VALIDATION obligations
- Pending: `OBL-ATP-WRITE-SCOPE`, `OBL-BASELINE-REFLECTION`
- Violated: none

## Post-restart result

The first `harness_status` access rehydrated the same Runtime/Turn and returned the exact revisions and obligation sets above. No duplicate Turn was created.

An additional `harness_status` query left the Execution Event Store unchanged:

- file: `execution-events/7f12d823f6cce57f9ec2ace503af12ca81f4fbc724b4cf4aa5b83fdf691658b0/events.jsonl`
- lines before/after: `28 / 28`
- SHA256 before/after: `99408569FEAAE2A919F0904356FCD5F56BB105B9AC1A482990459E8939EE4C8F`

Protected preflight for `pc/et_test_platform/core/result.py` remained `BLOCKED` after recovery.

Result for active supervised state replay: `PASS`.

## Closure recovery negative

A completion request with a malformed Reflection (missing `contractVersion`) returned an error, but the Turn had already entered `CLOSURE_PENDING` and its observations were sealed. The immediately corrected Reflection was then rejected:

`Turn ... is CLOSURE_PENDING; governed observations are sealed`

The Runtime status exposed `READY_TO_CLOSE` with only Reflection pending, while the Kernel journal could not accept the corrected Reflection. This is an atomicity/order defect between Reflection validation and irreversible lifecycle sealing.

Result for closure failure recovery/retry: `FAIL`.

## Scoped conclusion

The durable Event Store, Ledger and active Turn rehydrate correctly. The result must not be generalized to Closure recovery: an invalid completion attempt can poison retry state, so the global Runtime/Gateway replay row remains `FAIL` until that lifecycle boundary is repaired and regression-tested.
