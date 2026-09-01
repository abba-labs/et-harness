# Round 3 P0 Repair — Runtime Wiring Architecture Review Requirement

> Architecture Owner amendment for the existing Round 3 P0 campaign.
>
> This document does **not** replace `ROUND3_P0_CODEX_TEST_CHARTER.md` or `ROUND3_P0_EXECUTION_ORDER.md`. Those two files remain authoritative for the overall campaign. This amendment changes only one narrow point: after the deterministic Runtime environment was committed, Codex is authorized to **prove or disprove one specific Runtime composition risk**, make the smallest correction only if the risk is real, add a real frozen-Runtime regression, then continue the existing Round 3 P0 execution order.

## 0. Current baseline

Repository:

```text
abba-labs/et-harness
```

Branch:

```text
codex/fast-track-pure-mcp-atp-v0.1
```

Deterministic Runtime environment baseline:

```text
f9073f0980b0a545c3dfd605007ee4a9e6569b0e
fix(mcp-gateway): freeze deterministic runtime environment
```

The previous Round 3 P0 run stopped at:

```text
T3_RUNTIME_DEPLOYMENT_ARTIFACT_REFRESH
```

That earlier failure was valid: repaired source existed, but the live Gateway still used an older Runtime artifact. Commit `f9073f...` addresses that deployment boundary by introducing the pinned Windows Node 22 environment, deterministic source signature, content-addressed Runtime release, ATP Project Plugin bundling, artifact hashes, active release pointer, verification, and controlled Gateway refresh.

Treat this deterministic environment as the new baseline. **Do not replace it with another deployment system.**

---

## 1. Environment rules for this continuation

Use only the committed Pure MCP fast-track environment entry points:

```text
agent_harness/mcp_gateway_fast_track/scripts/prepare-environment.cmd
agent_harness/mcp_gateway_fast_track/scripts/freeze-runtime.cmd
agent_harness/mcp_gateway_fast_track/scripts/verify-environment.cmd
agent_harness/mcp_gateway_fast_track/scripts/refresh-gateway.cmd
```

Rules:

1. `prepare-environment.cmd` is a bootstrap/recovery operation, not a per-edit step. Run it only if the pinned dependency environment is actually missing or invalid.
2. Do not run ad-hoc `npm install` commands.
3. Do not reuse Linux `node_modules`, historical Phase 0/8 dependency trees, old Junction workarounds, or `codex-plugin-pilot/releases/32e6...` artifacts.
4. Do not restore Codex Plugin, Hook, Marketplace, Watcher, Windows Service, or a second Runtime owner.
5. Keep the external Gateway independent from Codex Desktop.
6. Keep `et_harness` MCP `required=false`.
7. Keep Pure MCP supervision truthful: no native interception means no fake ENFORCE claim.
8. Do not modify Runtime/Ledger/Event Store/Closure semantics merely to make a test green.

Expected invariant before any semantic test:

```text
current source signature
== active Runtime release sourceSignature
== verified artifact hashes
```

If `freeze-runtime --verify-only` reports stale/damaged/different-worktree/wrong-Node state, stop and repair the deterministic environment itself before continuing. Do not bypass the verifier.

---

## 2. Architecture Owner finding to investigate — NOT yet a confirmed bug

The current frozen Runtime owner at `f9073f...` composes the Runtime with:

```text
GovernanceRuntimeService
```

inside:

```text
agent_harness/mcp_gateway_fast_track/src/runtime-owner.ts
```

The P0-A repair introduced:

```text
ScopeSafeGovernanceRuntimeService
```

inside:

```text
agent_harness/public_plugins/governance_runtime/src/scope-safe-service.ts
```

and the public Governance Runtime plugin installs that scope-safe service from:

```text
agent_harness/public_plugins/governance_runtime/src/index.ts
```

The purpose of `ScopeSafeGovernanceRuntimeService` is narrow and important: an **explicit** mutation preflight must still evaluate the frozen Task Contract WRITE_SCOPE when the Host can negotiate only `AUDIT`. This does not claim universal native-tool interception.

The base `GovernanceRuntimeService.preflightAction()` performs `evaluateMutationPreflight(...)` as part of the ENFORCE path, while Pure MCP truthfully advertises:

```text
supportsPreflight = true
supportsToolInterception = false
supportsStableToolEventId = false
supervision = AUDIT
```

Therefore there is a credible wiring risk:

```text
Pure MCP frozen Runtime owner
  -> GovernanceRuntimeService
  -> AUDIT
  -> explicit mutation preflight may bypass the P0-A ScopeSafe override
  -> protected/out-of-scope preflight could incorrectly return allowed=true
```

This is an **Architecture Owner hypothesis, not an instruction to edit the class name blindly**.

Codex must first prove whether the real frozen Runtime has this defect.

---

## 3. Mandatory evidence-first diagnosis

Before changing Runtime composition, test the current `f9073f...` design as committed.

### A. Verify the deterministic release

Record:

```text
branch
HEAD
git status --short
Node executable + version
active-release.json path
release sourceRevision
release sourceSignature
release nodeVersion
packageLockSha256
runtime.mjs hash
atp-project-plugin.mjs hash
deployment.json hash
```

Use the committed freeze/verify commands. Do not manufacture these values manually.

### B. Exercise the actual frozen Runtime path

The critical test must use the **real frozen Runtime and real ATP Project Plugin**, not a fake Runtime object and not a stubbed `preflightAction()`.

A valid diagnostic path may use either:

- the externally launched live MCP Gateway after the committed refresh procedure; or
- an automated integration test that loads the verified frozen Runtime release through the same `createFrozenRuntimeAccess` / Runtime owner path used by production.

It must not replace the Runtime with `fakeRuntime()`.

Create one fresh ATP eTimer governed task using the existing simple task intent:

```text
分析6801芯片etimer这个IP，复核现有两份文档是否仍符合当前项目规则；不要修改PC、Firmware或Harness框架代码。
```

Obtain the real Task Context and record:

```text
taskId
runtimeId
turnId
projectId
projectRevision/contextRevision
writeScope.allowed
writeScope.protected
effective supervision level
claimsMechanicalInterception if available
```

Then perform explicit preflight only; do not create either probe file.

Allowed probe:

```text
CREATE test_case_doc/etimer/round3_p0_probe.md
```

Expected:

```text
allowed = true
```

Protected/out-of-scope probe:

```text
CREATE pc/et_test_platform/core/forbidden_round3_p0.py
```

Expected:

```text
allowed = false
```

Confirm the forbidden file does not exist.

Also prove:

```text
effective supervision = AUDIT
claimsMechanicalInterception = false (or equivalent truthful capability fact)
```

Do not change capability negotiation to obtain the expected result.

---

## 4. Decision gate — change code only if the defect is proven

### Case A — current frozen Runtime already blocks the protected path

If the real protected probe returns `allowed=false` while the allowed probe returns `allowed=true`:

1. mark the Architecture Owner hypothesis `NOT_REPRODUCED`;
2. do **not** change Runtime composition merely because the class names look suspicious;
3. determine and record the actual call path that makes the scope check truthful;
4. add the missing real frozen-Runtime regression described in Section 5 if current tests do not already protect this behavior;
5. continue the original Round 3 P0 execution order.

### Case B — current frozen Runtime allows the protected path

If the protected probe returns `allowed=true`:

1. mark the hypothesis `CONFIRMED`;
2. identify the exact call chain and prove the first failing boundary;
3. determine whether `runtime-owner.ts` bypasses the P0-A scope-safe Runtime service;
4. make the **smallest composition/wiring correction** that restores the already-designed P0-A semantics;
5. do not change Supervisor obligation semantics, Ledger, Event Store, Closure, ATP WRITE_SCOPE, Host capability facts, or Gateway API just to pass the test.

The expected likely repair boundary is Runtime composition, but the exact patch must follow evidence. Do not blindly replace a class if the actual root cause is elsewhere.

If the proven fix requires a broader architecture change than Runtime composition plus focused regression coverage, stop with:

```text
ARCHITECTURE_REVIEW_REQUIRED
```

and preserve evidence instead of redesigning the Framework.

---

## 5. Required regression before continuation

Whether the hypothesis is confirmed or disproved, the deterministic environment must gain a regression that protects the **real frozen Runtime wiring**.

Current unit coverage that uses a fake Runtime is not sufficient for this boundary.

The regression must exercise, directly or through MCP:

```text
verified active release
-> frozen runtime.mjs
-> real Runtime owner composition
-> real ATP Project Plugin apply/readiness
-> real project supervision contribution
-> AUDIT host capability
-> explicit mutation preflight
```

Required assertions:

```text
allowed Task Contract path       -> allowed=true
protected/out-of-scope path      -> allowed=false
forbidden file                   -> absent
supervision                      -> AUDIT
mechanical interception claim    -> false
```

This regression must be included in the normal `verify-environment.cmd` test batch, directly or through the existing `tests/*.test.mjs` pattern, so a future wrong Runtime composition causes environment verification to fail before a live Round 3 task starts.

Do not weaken the assertion into a mocked return value.

---

## 6. After diagnosis/fix — use the official refresh chain

After any permitted source/test change:

```text
freeze-runtime.cmd
verify-environment.cmd
refresh-gateway.cmd
```

Required behavior:

1. changed Runtime-relevant source produces a new content-addressed release;
2. unchanged source reuses the verified release;
3. damaged/stale release fails closed;
4. Gateway is stopped only after freeze + verification succeed;
5. new external Gateway starts under pinned Node 22;
6. `/health` returns HTTP 200;
7. MCP initialize succeeds;
8. `tools/list` exposes all eight required tools.

Do not manually edit `active-release.json` or release manifests.

---

## 7. Continue the existing Round 3 P0 campaign

After Section 3 is proven and Section 5 regression passes, continue the existing campaign. Do not create Round 4 and do not invent a new test charter.

Use:

```text
ROUND3_P0_CODEX_TEST_CHARTER.md
ROUND3_P0_EXECUTION_ORDER.md
```

Resume the real path from live Gateway activation / fresh ATP task and execute the remaining checks in the existing order:

```text
LIVE_MCP_NEW_TOOLS_ACTIVE
PROTECTED_PREFLIGHT_BLOCKS
AUDIT_CAPABILITY_REMAINS_TRUTHFUL
CHECKPOINT_REJECTS_PENDING_READS
REQUIRED_READ_TRUSTED_EVENTS
REQUIRED_READ_OBLIGATIONS_ADVANCE
AGENT_CANNOT_FORGE_TRUSTED_RESULT
PREMATURE_COMPLETE_STILL_BLOCKED
CHECKPOINT_TRUSTED_VALIDATION_EVENTS
VALIDATION_OBLIGATIONS_ADVANCE
REFLECTION_TRIGGERED
CLOSURE_REACHED_COMPLETE
CONTEXT_UPDATE_REACHED
GATEWAY_SURVIVES_CODEX_RESTART
REAL_DESKTOP_BLACK_BOX
```

Rules remain unchanged:

- `harness_read_required` must itself read/hash the authorized frozen required resource and emit Runtime-owned trusted evidence;
- `harness_checkpoint` accepts only `taskId`, runs only frozen validations, and the caller cannot provide command/PASS/provider/receipt;
- `harness_observe` is not trusted validation evidence;
- premature completion must remain blocked;
- Runtime/Supervisor/Closure remain the completion authority;
- do not translate blocked or incomplete state into PASS;
- Pure MCP must remain AUDIT unless its real Host capabilities change in a future separately approved architecture task.

---

## 8. Evidence and reporting

Use the existing campaign evidence contract. During the governed ATP task, keep temporary campaign evidence outside the governed business workspace as already required by the Charter.

Update the existing bounded evidence files instead of creating a parallel campaign. At minimum, the new execution must overwrite/supersede the stale `997cd...` observations with evidence from the new exact HEAD/release.

In `01_build_and_focused_tests.md` record:

```text
deterministic environment verification
Runtime wiring diagnosis: CONFIRMED / NOT_REPRODUCED
root cause if confirmed
minimal diff if changed
real frozen-Runtime regression command/result
release sourceSignature/sourceRevision
```

In `02_preflight.json` record the actual real Runtime preflight results, not `NOT_EXECUTED`.

Then continue updating `03_required_reads.jsonl` through `07_black_box.md` and `ROUND3_P0_FINAL_REPORT.md` according to the existing Execution Order.

Every PASS/FAIL must point to an exact MCP result, command result, Runtime status, trusted event reference, or release/artifact identity.

Codex may report the mechanical campaign classification required by the existing Charter, but that report is **test evidence, not Architecture Owner acceptance**. Do not claim that ET Harness architecture is finally accepted; the user/Architecture Owner reviews the pushed evidence and final SHA.

---

## 9. Allowed changes for this amendment

Only if evidence requires them:

```text
agent_harness/mcp_gateway_fast_track/src/runtime-owner.ts
agent_harness/mcp_gateway_fast_track/tests/**
agent_harness/mcp_gateway_fast_track/scripts/verify-environment.cmd
```

A narrowly necessary import/export or test fixture change in the existing Governance Runtime package is allowed only if directly required for the proven composition fix and must be explained.

Campaign evidence/report updates are allowed under the existing campaign contract.

Do not modify ATP rules, validation commands, WRITE_SCOPE, Host capability truth, Supervisor semantics, Ledger/Event Store/Closure, or unrelated project code to make the test pass.

---

## 10. Final handoff format

After the permitted diagnosis/fix and continuation tests are committed and pushed, report:

```text
Final Commit SHA:
Runtime Wiring Hypothesis: CONFIRMED / NOT_REPRODUCED
Runtime Wiring Change Made: YES / NO
Deterministic Environment: PASS / FAIL
Overall Round3 P0 Test Status:
Failed Checks:
Architecture Review Required:
Evidence Directory:
```

Do not start another repair cycle after reporting. If a new semantic/architecture defect outside this explicitly authorized Runtime-wiring boundary appears, preserve evidence and stop for Architecture Owner review.
