# Round 3 P0 Repair - T3 Live MCP Activation

## Expected

Refresh the committed repaired Runtime/ATP artifacts, restart the independently owned Gateway, and prove all eight tools through direct MCP `initialize` and `tools/list`.

## Actual

- Existing external Gateway: PID `9220`, `GET /health` HTTP `200`.
- Existing Gateway parent process had exited, so lifecycle independence remained intact.
- Existing Runtime release: `D:\lihuan\vibe_code\codex\et_harness_env\state\codex-plugin-pilot\releases\32e6bd27cfdd0268\`.
- Release creation: `2026-09-01T02:25:20.0703779Z` (`2026-09-01 10:25:20 +08:00`).
- P0 source commits began at `2026-09-01 17:57:58 +08:00`; therefore the active `owner-cli.js` predates the repair.
- The current branch contains the repaired Runtime/ATP source but no Pure MCP Runtime bundle build/refresh entry. Repository search found only the Gateway launcher; it launches `src/gateway.mjs` and does not rebuild `owner-cli.js`.

Direct MCP smoke against PID `9220` returned:

```json
{
  "serverInfo": {"name": "et-harness-mcp-fast-track", "version": "0.1.0"},
  "instructionsPresent": true,
  "tools": ["harness_health", "harness_begin", "harness_status"],
  "health": {
    "status": "READY",
    "runtimePortVersion": "0.1",
    "runtimeConnected": true,
    "projects": ["et-automated-testing-platform"]
  }
}
```

`harness_read_required` and `harness_checkpoint` were not live. The Gateway was not restarted from inside Codex, because doing so would violate the established external lifecycle boundary and still leave the old Runtime owner bundle active.

## Failure record

```text
Check: LIVE_MCP_NEW_TOOLS_ACTIVE
Expected: Repaired source is deployable and all eight tools are active against the repaired Runtime.
Actual: Active MCP exposes only three tools; active Runtime bundle predates the repair; no committed refresh path exists.
Reproduction: run Node 22 agent_harness/mcp_gateway_fast_track/scripts/smoke.mjs against http://127.0.0.1:8765/mcp.
Evidence: direct smoke JSON above; release timestamp; Git commit timestamps.
First failing boundary: Runtime deployment artifact refresh before external Gateway restart.
Suspected component: Pure MCP local build/deployment contract.
Architecture change required: YES.
```

T3 result: `FAIL`. Execution stopped before T4 as required.

