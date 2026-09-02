# Project Admission Round 2 Baseline

- Captured: `2026-09-02` (`Asia/Shanghai`)
- Role: `Test Executor`
- Repository: `abba-labs/et-harness`
- Branch: `architecture/project-admission-bootstrap-v0.1`
- Tested source SHA: `2bf842597415ef235d52fc213c197e50ac2cb89e`
- Repair parent SHA: `47b384c19636ca29a504be0413c7aa4bdad0fe7b`
- Previous evidence HEAD: `e950e2449848306dc6819f553eb12afcb65329bd`
- Previous defective implementation SHA: `67676a2916b01316794da042a813d0c338d14182`
- Task Context: `TASK-20260902-PROJECT-ADMISSION-SRPWM-ROUND2`
- Allowed write scope: `agent_harness/test_campaigns/**/evidence/**`
- Stable D-drive Runtime activation: `PROHIBITED`
- Dependency installation/change: `PROHIBITED`
- Product/framework mutation during measurement: `PROHIBITED`

From `e950e2449848306dc6819f553eb12afcb65329bd` through the tested SHA, only these
tracked product/test files changed:

```text
agent_harness/mcp_gateway_fast_track/src/project-admission.mjs
agent_harness/mcp_gateway_fast_track/tests/project-admission.test.mjs
```

The source repair removes Gateway-local fingerprint freshness authority. The target test commit
adds the same-process Architecture v1-to-v2 regression.

Real frozen Runtime, Pure MCP Gateway, Supervisor, Ledger, Event Store and Closure behavior will be
marked `NOT_EXECUTED` unless it can be exercised without accessing the prohibited stable D-drive
environment and without installing dependencies. Source inspection or an in-memory test double must
not be promoted to Runtime PASS.
