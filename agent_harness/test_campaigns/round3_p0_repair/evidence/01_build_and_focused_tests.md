# Round 3 P0 Repair - T1/T2 Build and Focused Tests

## Source baseline

- Branch: `codex/fast-track-pure-mcp-atp-v0.1`
- HEAD under test: `997cd63251955d920ffedbf0522f03dc9cfcf4b6`
- Node used for builds/tests: `D:\lihuan\vibe_code\codex\et_harness_env\runtimes\node-v22.23.2-win-x64\node.exe`
- npm cache and temporary files remained under `D:\lihuan\vibe_code\codex\et_harness_env\`.
- No Codex plugin/cache/Hook/Marketplace content was changed.

## Reproducibility findings

1. `npm run build --prefix agent_harness/public_plugins/governance_runtime` stopped in 759 ms because no Windows `tsc` was visible.
2. No reusable Windows `tsc.cmd` existed in the current worktree or shared environment root.
3. Two bounded `npm install` attempts failed before installing the target package because npm executed `prepare` for local `file:` dependencies whose own `tsc` was unavailable. Logs stayed in the D-drive npm cache.
4. The reusable Phase 0 dependency tree was Linux-created. Its TypeScript JavaScript was reusable, but its Vitest/Rolldown native binding was not Windows-compatible.
5. Current source APIs were newer than Phase 0 declaration artifacts. Builds therefore used ignored D-drive Junctions and generated only required current dependency artifacts; no dependency or generated artifact is intended for commit.

This is a missing deterministic Windows bootstrap/deployment contract, not an ATP product-code failure.

## Mechanical build results

| Artifact | Exit | Duration | Notes |
|---|---:|---:|---|
| Execution Supervisor dependency artifact | 0 | 7159 ms | Required by current Runtime types |
| Governance Core dependency artifact | 0 | 1117 ms | Current declarations |
| Governance Kernel dependency artifact | 0 | 1987 ms | Current Reflection/Closure declarations |
| Project Contract dependency artifact | 0 | 2195 ms | Reused D-drive `yaml` dependency |
| Project Manager dependency artifact | 0 | 1531 ms | Current adapter types |
| Gate Manager dependency artifact | 0 | 1815 ms | Current `GateStep.role` contract |
| Auto Governance Engine dependency artifact | 0 | 2179 ms | Current supervision contribution contract |
| Governance Runtime | 0 | 2325 ms | P0 source compiles |
| ATP Project Plugin | 0 | 4198 ms | P0 source compiles |

No direct TypeScript syntax/type correction was required in the six architecture-owner source files.

## Focused tests

### Gateway

Initial result: 16 PASS / 2 FAIL.

- Failure 1: the bounded MCP instructions grew to 666 characters while the existing contract requires at most 512.
- Failure 2: the old `tools/list` fixture still expected six tools and omitted `harness_read_required` and `harness_checkpoint`.

Allowed direct corrections:

- compressed instructions without changing tool or Runtime semantics; final length `506`;
- updated the tool-list test fixture to include the two committed P0 tools.

Final command:

```text
D:\lihuan\vibe_code\codex\et_harness_env\runtimes\node-v22.23.2-win-x64\node.exe --test tests/*.test.mjs
```

Final result: `18 PASS / 0 FAIL / 0 SKIP`, duration about 0.88 s.

### Runtime focused tests

The first test attempt stopped before collection because the reused Linux Vitest lacked a Windows Rolldown native binding. A minimal Windows Vitest 4.1.11 toolchain was installed once under this external state directory.

The Windows run then produced:

```text
host-runtime-port.test.ts: 4 PASS
host-enforcement.test.ts: suite import failure
```

Exact import failure:

```text
Cannot find package '@agent-harness/agent-governance-kernel' imported from the old Phase 0 agent_governance_closure_adapters/dist/index.js
```

This result is `NOT_VERIFIED`, not a Runtime semantic FAIL. The repair commit added no focused `scope-safe-service` test and the branch provides no deterministic current dependency bootstrap.

## T1/T2 result

- Current Runtime source compile: `PASS`
- Current ATP Project Plugin source compile: `PASS`
- Gateway focused suite: `PASS`
- Runtime P0 focused semantic suite: `NOT_VERIFIED` because the committed build/test bootstrap is incomplete
- Architecture review required: `YES`

## Task Context scope result

- `compile_task_context.py check`: exit `0`, current.
- `compile_task_context.py scope-check`: exit `1` only for the nine Charter-mandated files under `agent_harness/test_campaigns/round3_p0_repair/evidence/`.
- The two bounded Gateway corrections are inside the compiled `harness-host-adapter/mcp-gateway` scope.
- The campaign requires the evidence directory, but the module profile does not authorize it. The checker was not weakened and the map was not widened during testing.
