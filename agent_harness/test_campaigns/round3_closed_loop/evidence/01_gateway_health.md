# R3-01 Gateway health

- `GET http://127.0.0.1:8765/health`: HTTP 200; `status=UP`, service `et-harness-mcp-gateway`, PID `9220`, API `et-harness-mcp-fast-track.v1`.
- Listener: `127.0.0.1:8765`, owning process `node` PID `9220`.
- `harness_health`: `READY`, Runtime Port `0.1`, `runtimeConnected=true`, configured project `et-automated-testing-platform`.
- Focused Gateway suite: 18 tests PASS, 0 FAIL, duration about 1.0 s.

The process was the externally started Round 1 Gateway. No Codex Plugin reinstall or cache mutation occurred.
