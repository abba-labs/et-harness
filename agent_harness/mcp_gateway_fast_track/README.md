# ET Harness MCP Gateway Fast Track

Thin Codex Streamable HTTP MCP transport for the existing ET Harness Governance Runtime.

Round 1 exposes only `harness_health` and deliberately reports `runtimeConnected: false`.
It does not import ATP project code, install a Codex Plugin/Hook, or implement governance lifecycle state.

```cmd
start-et-harness-gateway.cmd
scripts\smoke.cmd
scripts\stop-gateway.cmd
```

The fixed production endpoint is `http://127.0.0.1:8765/mcp`. Process state and logs are stored under the shared D-drive ET Harness environment.

Start the Gateway by double-clicking `start-et-harness-gateway.cmd` in Windows Explorer or from an independent terminal. The launcher fails closed when Codex Desktop, a Codex hook, a Codex plugin, or a marketplace process appears in its ancestor chain. `GET http://127.0.0.1:8765/health` reports only the Gateway process itself and does not load the Governance Runtime or any Project Plugin.
