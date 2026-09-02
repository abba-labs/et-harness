# Machine-local Launcher Freeze v0.1 Final Report

## Outcome

`MACHINE_LOCAL_ENVIRONMENT_FREEZE_PASS`

The fixed D-drive launcher now owns Runtime lifecycle independently of the active
Git branch, checkout location, working directory and the two ET Harness environment
variables. A deliberately historical checkout at
`7ce711a882da7807d996684c27313221fa359c00`, which contains no machine launcher,
successfully stopped PID 34828 and started the same frozen v2 release as PID 46040
using only the installed D-drive entry. A second explicitly no-environment-variable
cycle ended healthy at PID 20124.

## Identities

- Product SHA: `6aaefb28a4c6776fb241617d3735b5c313ca4c7e`
- Installed launcher SHA256: `f4973e07baae0063a59735d9d6a182e183c6295571b3ef7a72a89af377de8c04`
- Installed command SHA256: `5ed9c410ba54f145809806554fa47e514c0fa663ce5a9b11e59b78cfe0a397b3`
- Environment Root: `D:\lihuan\vibe_code\codex\et_harness_env`
- Node: `v22.23.2`
- Active Runtime: `f976d8e32df64fa78075`
- Active schema: `et-harness.pure-mcp-runtime-release.v2`
- Final PID: `20124`
- Dependency mode: `release-bundled`

## Mechanical results

| Boundary | Result | Evidence |
|---|---:|---|
| Targeted launcher/resolver tests | PASS, 24/24 | `raw_logs/test_summary.txt` |
| Full Gateway package tests, clean checkout | PASS, 66/66 | `raw_logs/test_summary.txt` |
| First launcher install | PASS | `launcher_install.json` |
| Identical reinstall | PASS, `REUSED_UNCHANGED` | `launcher_install.json` |
| Non-repository cwd status/health | PASS | `machine_status.json`, `machine_health.json` |
| Historical SHA D-drive stop/start | PASS | `historical_branch_restart.json`, `raw_logs/historical-start.jsonl` |
| Explicit no-env stop/start/status/health | PASS | `no_env_var_restart.json`, `raw_logs/no-env-start.jsonl` |
| HTTP health | PASS | `machine_health.json` |
| MCP initialize and exact 8 tools | PASS | `machine_health.json` |
| Project Admission bootstrap | PASS | `project_admission.json` |
| Direct Codex-owned start safety boundary | PASS, blocked | `negative_controls.json` |
| checkout-local `node_modules` | ABSENT | `baseline.json`, `state_diffs.json` |
| npm/npx invocation count by this campaign | 0 | `raw_logs/test_summary.txt` |

Project Admission returned `PROJECT_CONTEXT_REQUIRED`, the bounded Architecture
Bootstrap and a current fingerprint for the declared ET Automated Testing Platform.
Runtime State, Event Store and Task Snapshot summaries were byte-identical before
and after, so the bootstrap did not open a Runtime Turn.

## State isolation

The active and previous pointer hashes, Runtime State digest, Event Store digest,
Task Snapshot digest and installed launcher hash were unchanged across installation,
historical checkout switching, health checks and Project Admission bootstrap. The
PID changed only through the two approved stop/start cycles. The final Gateway
command line references only the fixed machine Node and the D-drive frozen release.

No Runtime release, Toolchain, governance business module, dependency, pointer or
historical v1 rollback record was modified. No repository-wide software gate was
run, per the user's explicit instruction for this environment-only campaign.

## Remaining blockers

None for the declared freeze acceptance. The live destructive wrong-PID forgery
case was intentionally not injected into stable state; all non-destructive integrity,
release-boundary and launcher-ancestry negative controls passed.
