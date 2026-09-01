# Round 3 P0 Repair - Runtime Wiring and Focused Verification

## Runtime wiring hypothesis

Result: `CONFIRMED`.

The production frozen Runtime used `GovernanceRuntimeService` directly even though the public Governance Runtime plugin registers `ScopeSafeGovernanceRuntimeService`. The real call chain was:

```text
MCP harness_preflight
-> Gateway controller
-> createFrozenRuntimeAccess
-> frozen Runtime owner
-> createGovernanceHostRuntimePortV01
-> installed GovernanceRuntimeService
-> AUDIT preflight returned ALLOWED without scope evaluation
```

Real ATP reproduction before repair allowed a protected probe under `pc/et_test_platform/core/**`; the forbidden file was never created.

## Minimal authorized repair

- `agent_harness/mcp_gateway_fast_track/src/runtime-owner.ts` now installs the existing `ScopeSafeGovernanceRuntimeService`.
- No Governance Runtime, ATP Project Plugin, Supervisor, Ledger, Event Store, Closure, Plugin, Hook or Marketplace source was changed.
- Added `frozen-runtime-wiring.test.mjs`, which loads the real frozen Runtime and bundled ATP Project Plugin in isolated D-drive state and proves:
  - effective supervision remains `AUDIT`;
  - `claimsMechanicalInterception=false`;
  - allowed eTimer path is allowed;
  - protected ATP path is blocked;
  - no forbidden file is created.

Repair commits before campaign evidence:

- `d2b4169` wire scope-safe Runtime service and add frozen wiring regression
- `eb4ec21` assert the real capability location
- `b8f5869` isolate frozen Runtime regression state
- `fd5edaa` assert the stable WRITE_SCOPE denial contract

## Verification

- Focused Gateway typecheck and existing tests: `PASS` (18 focused tests before frozen regression integration).
- Formal `freeze-runtime -> verify-environment -> refresh-gateway` chain: `PASS`.
- `verify-environment.cmd`: `22 PASS / 0 FAIL`.
- No dependency reinstall was performed.
- Direct MCP smoke after external refresh: eight tools visible and Runtime connected.

Result: `PASS`.
