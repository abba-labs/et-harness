# P0 Lifecycle Repair V0.1 — Test Matrix

**Canonical base**: `41784d8cfc02ed02a057aa0c37320cf8ad529f9b`  
**Behavioral Evidence**: `fea9e454d100eaf175bfa8f9ed0589a104488d15`

| Requirement | Exact-owner coverage | Composed coverage | Required outcome |
|---|---|---|---|
| R1 frozen Validation rerun | `mcp_gateway_fast_track/tests/trusted-checkpoint.test.mjs` | existing supervised Runtime + checkpoint tests | SATISFIED and VIOLATED validation obligations both execute again on explicit checkpoint |
| R1 completion freshness | `mcp_gateway_fast_track/tests/fresh-completion.test.mjs` | Gateway public completion path | first completion checkpoints; failed checkpoint blocks; COMPLETE replay adds no checkpoint |
| R2 Context atomicity | `context_builder/tests/context-lifecycle-repair.test.ts` | Closure adapter production module test | one CAS contains ledger/progress/working set; invalid input commits nothing |
| R2 terminalization | `context_builder/tests/context-lifecycle-repair.test.ts` | Governance Runtime completion/replay tests | one exact Closure identity terminalizes once; conflicting identity fails closed |
| R3 prior Context | `context_builder/tests/context-continuity.test.ts` | real related/unrelated ATP behavioral retest | related task inherits bounded facts; unrelated/ABORTED task does not |
| R4 failed begin | Kernel Journal + Context lifecycle tests | `mcp_gateway_fast_track/tests/governance.test.mjs` | PREPARING becomes durable FAILED + ABORTED compensation; no unreachable active state |
| R5 closed replay | Kernel Closure existing idempotency tests | Governance Runtime/Gateway completion replay | same request returns original closure without new TASK_END/Reflection/modules/finalization |
| Public surface | existing MCP protocol tests | Harness Public Baseline | exact eight tools unchanged |
| Project boundary | repository diff + existing ATP routing tests | real ATP behavioral retest | no ATP/SRPWM semantics introduced into public Framework |
| Machine boundary | repository diff + existing launcher/environment tests | no local activation during repair | no D-drive environment, Launcher, Node, Toolchain or active Runtime mutation |

Acceptance is not granted by this matrix alone. The exact repair HEAD must pass the applicable package builds/tests, Harness Public Baseline, mandatory non-regression, and a real ATP lifecycle retest before merge.
