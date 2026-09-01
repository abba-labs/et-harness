# Round 3 P0 Repair Verification - Final Evidence Report

## Boundaries

- Repair baseline: `ef31b59637937b96d4c3a152f650aa7de999b2f3`.
- Tested Gateway/Runtime source HEAD and ATP project revision: `1f7e317219f39a2096e3201ddbea51513d47bf91`.
- Role: Test Executor.
- Architecture Owner final acceptance: `NOT_DECLARED`.
- Pure MCP supervision level: `AUDIT`.
- Product source changed during this final verification batch: `NO`.
- Earlier failure evidence in `00_environment.md` through `07_black_box.md` is retained as the historical first-failure record. Post-repair closure evidence is in `08_full_data_chain.json`, `09_codex_desktop_blackbox.json`, and `10_post_repair_environment.md`.

## Result matrix

| Check | Result | Evidence |
|---|---|---|
| DETERMINISTIC_ENVIRONMENT_22_OF_22 | PASS | `10_post_repair_environment.md` |
| SUPERVISOR_SAFETY_REGRESSIONS_15 | PASS | `10_post_repair_environment.md` |
| DIRECT_VALIDATION_STILL_UNTRUSTED | PASS | `08_full_data_chain.json` |
| TRUSTED_CHECKPOINT_ADVANCES_VALIDATION | PASS | `08_full_data_chain.json` |
| PROJECT_ROUTE | PASS | `08_full_data_chain.json`, `09_codex_desktop_blackbox.json` |
| ARCHITECTURE_ROUTE | PASS | `08_full_data_chain.json`, `09_codex_desktop_blackbox.json` |
| RULE_ROUTE | PASS | `08_full_data_chain.json`, `09_codex_desktop_blackbox.json` |
| KNOWLEDGE_ROUTE | PASS | `08_full_data_chain.json`, `09_codex_desktop_blackbox.json` |
| GATE_ROUTE | PASS | `08_full_data_chain.json`, `09_codex_desktop_blackbox.json` |
| AUDIT_CAPABILITY_REMAINS_TRUTHFUL | PASS | `08_full_data_chain.json` |
| PROTECTED_PREFLIGHT_BLOCKS | PASS | `08_full_data_chain.json`, `09_codex_desktop_blackbox.json` |
| CHECKPOINT_REJECTS_PENDING_READS | PASS | `08_full_data_chain.json`, `09_codex_desktop_blackbox.json` |
| NON_REQUIRED_READS_FAIL_CLOSED | PASS | `08_full_data_chain.json` |
| REQUIRED_READ_TRUSTED_EVENTS | PASS | `08_full_data_chain.json`, `09_codex_desktop_blackbox.json` |
| REQUIRED_READ_OBLIGATIONS_ADVANCE | PASS | `08_full_data_chain.json`, `09_codex_desktop_blackbox.json` |
| AGENT_CANNOT_FORGE_TRUSTED_RESULT | PASS | `08_full_data_chain.json` |
| PREMATURE_COMPLETE_STILL_BLOCKED | PASS | `08_full_data_chain.json` |
| CHECKPOINT_TRUSTED_VALIDATION_EVENTS | PASS | `08_full_data_chain.json`, `09_codex_desktop_blackbox.json` |
| VALIDATION_OBLIGATIONS_ADVANCE | PASS | `08_full_data_chain.json`, `09_codex_desktop_blackbox.json` |
| REPLAY_PRESERVES_VALIDATION_STATE | PASS | `08_full_data_chain.json` |
| REFLECTION_TRIGGERED | PASS | `08_full_data_chain.json`, `09_codex_desktop_blackbox.json` |
| KNOWLEDGE_CLASSIFICATION | PASS (`NONE`) | `08_full_data_chain.json`, `09_codex_desktop_blackbox.json` |
| CONTEXT_UPDATE_REACHED | PASS | `08_full_data_chain.json`, `09_codex_desktop_blackbox.json` |
| CLOSURE_REACHED_COMPLETE | PASS | `08_full_data_chain.json`, `09_codex_desktop_blackbox.json` |
| GATEWAY_SURVIVES_CODEX_RESTART | PASS | `09_codex_desktop_blackbox.json`, `10_post_repair_environment.md` |
| REAL_CODEX_DESKTOP_BLACK_BOX | PASS | `09_codex_desktop_blackbox.json` |

## Closed first-failure boundary

The prior first failure was not lost durable evidence. A fresh Gateway process did not bind and rehydrate the existing supervised Turn before status/closure operations. Commit `39b1aa7` added idempotent Runtime rehydration from the existing Event Store, and commit `1f7e317` persisted the task-end request before existing Runtime closure. The post-repair task preserved the same 13 satisfied execution obligations across Gateway restart and then reached all 17 final obligations with no pending or violated items.

## Real Codex Desktop result

The black-box task was invoked through the tools exposed to this Codex Desktop process, not through the standalone test client. It proved:

- all eight public MCP tools were active;
- project, architecture, rule, knowledge and Gate routes were contributed by the ATP Project Plugin;
- protected preflight blocked while an allowed probe remained allowed;
- seven required reads produced accepted execution events;
- five frozen validations exited `0` and produced trusted request/validation/response spans;
- Reflection, Knowledge Classification, Context Update and eight-module Closure reached `COMPLETE`;
- Gateway PID `22000` survived Desktop restart and the Desktop reconnected without a Gateway restart.

## eTimer review truthfulness

The public eTimer contract remained chip-neutral with 10 stable features and 8 planned cases; the ET6801 mapping covered the same 10 features and 8 cases. Existing implementation/mapping/bench gaps and `ETIM_CLAIM_009` remained explicit. Software, FPGA and HIL execution was not performed and is recorded as `NOT_EXECUTED`.

## Overall

- Deterministic environment: `PASS`.
- Direct Validation still untrusted: `PASS`.
- Trusted checkpoint Validation advances: `PASS`.
- Replay preserves Validation state: `PASS`.
- Codex Desktop black-box: `PASS`.
- Overall Round 3 P0 status: `PASS`.
- Failed checks: `NONE`.
- Architecture review required: `NO`.
- Architecture Owner final acceptance: `NOT_DECLARED`.
