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

The Runtime release is built directly from the current public Runtime and ATP Project Plugin sources. It is content-addressed, records the source revision and artifact hashes, and is verified before every production start. Unchanged sources reuse the existing release without rebuilding. A stale or damaged release is rejected instead of silently mixing new Gateway code with an old Runtime artifact.

```cmd
scripts\prepare-environment.cmd  rem one-time pinned D-drive dependency install
scripts\freeze-runtime.cmd       rem build only when the relevant source signature changes
scripts\verify-environment.cmd   rem one bounded typecheck + focused regression batch
scripts\refresh-gateway.cmd      rem freeze, stop, and externally restart the Gateway
```

Start the Gateway by double-clicking `start-et-harness-gateway.cmd` in Windows Explorer or from an independent terminal. The launcher fails closed when Codex Desktop, a Codex hook, a Codex plugin, or a marketplace process appears in its ancestor chain. `GET http://127.0.0.1:8765/health` reports only the Gateway process itself and does not load the Governance Runtime or any Project Plugin.
