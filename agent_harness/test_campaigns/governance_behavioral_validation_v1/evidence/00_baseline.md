# Governance Behavioral Validation V1 Baseline

- Captured: 2026-09-02 (Asia/Shanghai)
- Repository: `abba-labs/et-harness`
- Branch: `codex/fast-track-pure-mcp-atp-v0.1`
- Baseline source SHA: `21c0fcc8523e9aa48fbc81459895b4d9510bc909`
- Worktree: `D:\\lihuan\\vibe_code\\codex\\et_harness_env\\workspaces\\pure_mcp_atp_fast_track`
- User checkout mutation: `NO`
- Product source mutation authorized: `NO`
- Evidence-only Task Context: `20260902-governance-behavioral-validation-v1`
- Allowed write scope: `agent_harness/test_campaigns/**/evidence/**`
- Test role: `Test Executor`
- Observer role: independent Governance Observer; read-only, no implementation or PASS authority

## Deterministic environment baseline

The existing D-drive frozen Runtime was reused. No dependency install, package upgrade, environment rewrite, or product build was performed.

- `freeze-runtime`: PASS; existing signature reused (`8a1e3c292a27720d99d0eec5e9cec54194bab41426a525e52b8ce6bf442ab7be`)
- `verify-environment`: PASS (22/22), including the real frozen Runtime regressions and eight-tool Gateway contract
- `refresh-gateway`: NOT COMPLETED from Codex; it stopped external PID 22000 and then correctly rejected a Codex-owned restart because `codex.exe` was in the launcher ancestry
- Interpretation: lifecycle isolation policy behaved as designed; external Explorer launch is required before black-box scenarios
- Environment content changed: `NO`

## External Gateway lifecycle used by scenarios

- First external PID: `7520`; launched manually outside Codex and served `/health` plus direct MCP.
- Controlled replay restart: old PID stopped; user started new external PID `46224` without rebuilding or reinstalling.
- Post-restart `/health`: `200 UP`; direct MCP `initialize`, `tools/list` and `harness_health` passed.
- Gateway remained externally owned for all subsequent scenarios. Codex Desktop was not routinely restarted.
- Desktop transport created while the Gateway was absent did not reconnect automatically; this is recorded as a Host transport defect and was not used as Framework behavioral evidence.

## Measurement rules

1. A final `COMPLETE` never substitutes for module-level evidence.
2. Missing direct evidence is `OBSERVABILITY_GAP`, not PASS.
3. First failing boundary is recorded; dependants become `BLOCKED_BY_UPSTREAM` while independent checks continue.
4. Observer findings are observations only; mechanical evidence establishes results.
5. No Framework, Runtime, ATP Project Plugin, policy, environment, Hook, Plugin, Marketplace, watcher, daemon, or second Runtime may be changed to make a scenario pass.
