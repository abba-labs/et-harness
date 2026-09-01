# Round 3 P0 Repair Verification Final Report

## Baseline

- Branch: `codex/fast-track-pure-mcp-atp-v0.1`
- Required repair HEAD: `997cd63251955d920ffedbf0522f03dc9cfcf4b6`
- Role: Test Executor
- Source redesign performed: `NO`
- Direct test/compile correction: bounded MCP instructions shortened to 506 characters and tool-list fixture updated for the two committed tools.

## Result matrix

| Check | Result | Exact Evidence | Notes |
|---|---|---|---|
| PROTECTED_PREFLIGHT_BLOCKS | FAIL | `02_preflight.json`, `06_live_mcp.md` | Not executed against repaired live Runtime; T3 failed first |
| AUDIT_CAPABILITY_REMAINS_TRUTHFUL | FAIL | `02_preflight.json`, `06_live_mcp.md` | Not verified on repaired live Runtime; no ENFORCE claim was made |
| CHECKPOINT_REJECTS_PENDING_READS | FAIL | `04_checkpoint.json`, `06_live_mcp.md` | Tool not active in live MCP |
| REQUIRED_READ_TRUSTED_EVENTS | FAIL | `03_required_reads.jsonl`, `06_live_mcp.md` | Tool not active in live MCP |
| REQUIRED_READ_OBLIGATIONS_ADVANCE | FAIL | `03_required_reads.jsonl` | No event was fabricated |
| CHECKPOINT_TRUSTED_VALIDATION_EVENTS | FAIL | `04_checkpoint.json` | Not executed |
| VALIDATION_OBLIGATIONS_ADVANCE | FAIL | `04_checkpoint.json` | Not executed |
| AGENT_CANNOT_FORGE_TRUSTED_RESULT | FAIL | `04_checkpoint.json`, `06_live_mcp.md` | Static input schema exists, but real repaired path was not active |
| PREMATURE_COMPLETE_STILL_BLOCKED | FAIL | `05_closure.json` | Not executed on a fresh repaired task |
| REFLECTION_TRIGGERED | BLOCKED_BY_UPSTREAM | `05_closure.json` | T3 failed |
| CLOSURE_REACHED_COMPLETE | BLOCKED_BY_UPSTREAM | `05_closure.json` | T3 failed |
| CONTEXT_UPDATE_REACHED | BLOCKED_BY_UPSTREAM | `05_closure.json` | T3 failed |
| LIVE_MCP_NEW_TOOLS_ACTIVE | FAIL | `06_live_mcp.md` | Direct MCP listed only three tools |
| GATEWAY_SURVIVES_CODEX_RESTART | FAIL | `06_live_mcp.md` | Restart test not justified after T3 failure |
| REAL_DESKTOP_BLACK_BOX | FAIL | `07_black_box.md` | Not executed |

## First failing boundary

`T3_RUNTIME_DEPLOYMENT_ARTIFACT_REFRESH`

The repaired source compiles, but the active Runtime owner bundle predates the repair and the branch has no deterministic, committed Pure MCP artifact refresh path. Restarting only `src/gateway.mjs` would expose tool names while still exercising old Runtime semantics, so that action was rejected as false evidence.

## Required architecture-owner action

Provide one deterministic local verification/deployment entry that, from a clean worktree and pinned Windows Node 22 environment:

1. prepares or verifies the dependency signature without relying on a historical Linux worktree;
2. compiles the affected current package graph;
3. builds a new Runtime owner/bridge artifact from the same Git SHA;
4. refreshes the ATP Project Plugin artifact from the same Git SHA;
5. records artifact hashes and source SHA;
6. runs MCP initialize/tools/list plus one bounded preflight/checkpoint smoke before the repair is handed to the Test Executor.

Also align the campaign evidence path with a deterministic Test Executor Task Context route. The current scope checker correctly rejects the required evidence directory; this round did not widen the map or weaken the checker.

This report does not restore the old Codex Plugin/Hook/Marketplace path and does not create a second Runtime.

## Overall

- Overall status: `ROUND3_P0_REPAIR_FAIL`
- Architecture review required: `YES`
- No Round 4 work started.
