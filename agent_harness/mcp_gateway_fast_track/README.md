# ET Harness MCP Gateway Fast Track

Thin Codex Streamable HTTP MCP transport for the existing ET Harness Governance Runtime.

Round 1 exposes only `harness_health` and deliberately reports `runtimeConnected: false`.
It does not import ATP project code, install a Codex Plugin/Hook, or implement governance lifecycle state.

```cmd
scripts\start-gateway.cmd
scripts\smoke.cmd
scripts\stop-gateway.cmd
```

The fixed production endpoint is `http://127.0.0.1:8765/mcp`. Process state and logs are stored under the shared D-drive ET Harness environment.
