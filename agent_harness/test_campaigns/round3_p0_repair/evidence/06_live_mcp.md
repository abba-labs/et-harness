# Round 3 P0 Trusted Validation Repair - Live MCP and Replay

## Live activation

- External Gateway PID: `31328`
- `GET /health`: HTTP 200 / `UP`
- Pinned D-drive Node 22: `PASS`
- `required=false`: `PASS`
- Runtime project: `et-automated-testing-platform`
- Eight public MCP tools visible: `PASS`
- Internal `ingestTrustedValidationSpan` absent from `tools/list`: `PASS`

## Fresh real ATP task

- Task: `round3-p0-trusted-validation-repair-20260901-2221`
- Runtime: `codex-runtime-8aa695d2-89ed-49ee-8b3e-a65f53957495`
- Turn: `codex-turn-18a49445-2d33-4ce3-8668-8cfbbedf4cbe`
- Project revision: `40b469d950959259a574e2952659e6c76eb0608e`
- Context revision: `dd52c701873d25bc495831aeb5c5577f4f91efa445de0c74a206f4a054a07b04`

Before restart, 7 Required Read and 5 Validation obligations were `SATISFIED`.

## Gateway restart and durable replay

- Before PID: `31328`
- After PID: `3064`
- New process `/health`: HTTP 200 / `UP`
- Same task/runtime/turn remained addressable.
- Status after restart reported:

```json
{
  "runtimeDecision": "IN_PROGRESS",
  "pendingObligationIds": [],
  "satisfiedObligationIds": [],
  "violatedObligationIds": []
}
```

This is `FAIL`, not an empty successful Ledger.

Durable state remained intact:

- Event Store: 27 accepted events, sequences 1..27.
- Kinds: 7 `RESOURCE_READ`, 5 `TOOL_RESULT`, 5 `USER_MESSAGE`, 5 `VALIDATION_RESULT`, 5 `ASSISTANT_MESSAGE`.
- All five trusted request/validation/response spans remained persisted.
- Kernel Turn remained `OPEN` with the same task/runtime/turn binding.

First failing boundary:

```text
createFrozenRuntimeAccess.getStatus
-> fresh GovernanceHostRuntimePortV01.getStatus
-> new in-memory Runtime has no restored session
-> undefined supervision status
-> Gateway status summary emits empty obligation arrays
```

The durable Event Store is not the failing boundary. The existing Runtime `rehydrateSupervisedTurn()` capability is not invoked by the Gateway frozen status/recovery path before status is queried.

Replay preserves Validation state: `FAIL`.
Architecture review required: `YES`.
