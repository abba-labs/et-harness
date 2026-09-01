# Round 3 P0 Repair — Codex Test Charter

## 0. Role

You are the **Test Executor** for the architecture-owner repair already committed to this branch.

You do not redesign ET Harness in this round.

Your job is limited to:

1. pull the architecture-owner repair;
2. build only the affected packages/artifacts once as required by the existing deployment path;
3. run focused mechanical tests;
4. run one real ATP governed task through the repaired path;
5. preserve exact evidence;
6. commit/push test evidence and only minimal test/compile corrections if the repair itself contains a direct syntax/type defect.

Do not expand the repair into a new architecture.

---

## 1. Repository baseline

- Repository: `abba-labs/et-harness`
- Branch: `codex/fast-track-pure-mcp-atp-v0.1`
- Round 3 failing baseline: `1301fa36395a7bb1ea06ae307936ac2339d922e5`
- Pull the latest branch head containing this charter before testing.

Before testing:

```text
git fetch
git checkout codex/fast-track-pure-mcp-atp-v0.1
git pull --ff-only
```

Verify the worktree is clean.

---

## 2. What the architecture owner changed

The repair intentionally changes only two P0 boundaries.

### P0-A — Explicit WRITE_SCOPE preflight

A new Runtime service wrapper keeps all canonical Runtime identity/Turn/policy checks, then applies deterministic `evaluateMutationPreflight(...)` to an explicit mutation preflight even when the Host can only negotiate `AUDIT`.

This does **not** claim that Pure MCP intercepts every Codex native tool.

Expected semantics:

```text
explicit harness_preflight + allowed path   -> ALLOWED
explicit harness_preflight + outside scope  -> BLOCKED
Pure MCP Host capability                    -> remains AUDIT
claimsMechanicalInterception                -> remains false
```

Do not change Host capabilities to fake ENFORCE.

### P0-B — Trusted execution facts without Hook/Watcher

Two bounded MCP capabilities were added:

```text
harness_read_required(taskId, resourceRef)
harness_checkpoint(taskId)
```

`harness_read_required`:

- accepts only an exact required `mustRead` resource from the frozen Task Context / supervision contract;
- reads the real bounded text file itself;
- hashes the real content;
- sends a Runtime-owned `RESOURCE_READ` event through existing `ingestExecutionEvent()`;
- is not a general filesystem tool.

`harness_checkpoint`:

- accepts only `taskId`;
- the Agent cannot supply commands, PASS/FAIL, receipts, provider IDs or obligation results;
- refuses to run validation while required-read obligations remain pending;
- runs only validation commands frozen in the Task Context;
- emits Runtime-owned `TOOL_RESULT` and `VALIDATION_RESULT` events;
- uses the Host-independent built-in trusted provider identity `et-harness`;
- ATP explicitly authorizes that provider for its validation policies while retaining its existing project Gate providers.

No Hook, Plugin reinstall, Watcher, second Ledger, second Event Store or second Closure implementation was added.

---

## 3. Files changed by the architecture repair

Expected architecture-owner files are limited to:

```text
agent_harness/public_plugins/governance_runtime/src/scope-safe-service.ts
agent_harness/public_plugins/governance_runtime/src/index.ts
agent_harness/projects/automated_testing_platform/src/checkpoint-context-contributor.ts
agent_harness/projects/automated_testing_platform/src/index.ts
agent_harness/mcp_gateway_fast_track/src/trusted-checkpoint.mjs
agent_harness/mcp_gateway_fast_track/src/gateway.mjs
```

Do not modify unrelated Framework/Runtime/Project files during testing.

---

## 4. Allowed Codex changes

Allowed only when required to make the architecture-owner patch compile/test exactly as designed:

- direct TypeScript/JavaScript syntax or type correction inside the six files above;
- focused unit/regression tests for the repaired behavior;
- this campaign's evidence/report files;
- existing deployment artifact refresh required to load the new committed source.

Any semantic change beyond that is forbidden. Record it as `ARCHITECTURE_REVIEW_REQUIRED` instead.

---

## 5. Forbidden changes

Do not:

- change `required=false` to `required=true`;
- install/re-enable Codex Plugin, Hook or Marketplace;
- modify Codex installation/cache;
- claim Pure MCP has native tool interception;
- set `supportsToolInterception=true` or `supportsStableToolEventId=true` unless the Host truly gains those capabilities (it does not in this round);
- expose raw `ingestExecutionEvent` as an MCP tool;
- let the Agent submit trusted receipts or PASS states;
- make `observeWork()` satisfy Supervisor obligations;
- duplicate Ledger, Event Store, Runtime, Gate, Closure or Knowledge logic;
- add filesystem watcher/background polling;
- redesign ATP rules, validation commands or Project Context to make tests pass;
- run broad repository rebuilds repeatedly.

---

## 6. Build/deployment discipline

Use the existing local development/deployment mechanism already used by the Pure MCP fast track.

Rules:

1. no `npm install` unless a dependency is actually missing;
2. build only affected packages and required bridge/runtime artifact once;
3. do not reinstall a Codex Plugin;
4. do not copy anything into Codex C-drive plugin cache;
5. do not change Marketplace/Hook trust state;
6. keep `et_harness` MCP `required=false`;
7. if Codex config has an `enabled_tools` allowlist, append only:
   - `harness_preflight`
   - `harness_read_required`
   - `harness_checkpoint`
   and preserve the existing tools.

The externally owned production Gateway must not be launched as a child that dies with Codex Desktop. For focused automated tests, an ephemeral test Gateway is allowed. Before the final Desktop black-box check, use the already established external Gateway launcher/lifecycle procedure; do not invent a Windows Service or new launcher architecture.

---

# 7. Required focused tests

Run the smallest relevant tests first.

## T1 — Compile/build

Verify the affected packages compile:

- Governance Runtime
- ATP Project Plugin
- MCP Gateway focused suite

Record exact commands and exit codes.

If a direct syntax/type defect exists in the architecture-owner patch, fix only that defect and record the diff.

## T2 — Preflight regression

Create a fresh governed ATP eTimer task and verify both:

```text
CREATE test_case_doc/etimer/round3_p0_probe.md
-> allowed=true
```

and, without performing the mutation:

```text
CREATE pc/et_test_platform/core/forbidden_round3_p0.py
-> allowed=false
```

Requirements:

- Pure MCP / Codex capability remains `AUDIT`;
- no claim of mechanical interception;
- forbidden file must not exist after the test.

This test is PASS only if the explicit protected/out-of-scope mutation is blocked.

## T3 — Required-read trust boundary

For the fresh task:

1. call `harness_checkpoint` before required reads;
2. expect `status=BLOCKED`, `reason=REQUIRED_READS_PENDING`;
3. obtain the required filesystem `mustRead` refs from `harness_begin`;
4. read each filesystem-backed required resource using `harness_read_required`;
5. do not fabricate events for URI/non-filesystem resources;
6. after each read, verify a Runtime-owned event is accepted and the relevant REQUIRED_RESOURCE obligation advances.

Negative controls:

- a path not present in required `mustRead` -> reject;
- path traversal / different arbitrary file -> reject;
- oversized/unsupported resource -> fail closed rather than emit a partial trusted read.

## T4 — Trusted checkpoint

After required filesystem reads are satisfied:

1. call `harness_checkpoint(taskId)` with no other fields;
2. verify the caller cannot inject a validation command or PASS status;
3. verify only frozen Task Context validation commands run;
4. verify validation results create trusted Runtime execution events;
5. verify PASS validations advance the corresponding Supervisor obligations;
6. if one validation fails, checkpoint stops/fails closed and Closure remains blocked.

Do not accept `harness_observe` records as a substitute for trusted validation events.

## T5 — Premature completion remains blocked

Before successful checkpoint completion, call the normal completion path once.

Expected:

```text
IN_PROGRESS / BLOCKED
```

The repair must not weaken Closure.

## T6 — Closure after trusted evidence

After required reads and all frozen validations PASS:

- query `harness_status`;
- verify execution-stage obligations have actually moved out of PENDING as appropriate;
- call `harness_complete` using a bounded truthful semantic Reflection proposal;
- verify Runtime, not the Agent, decides the final Closure result;
- record Reflection, Closure, Knowledge decision, Context update and final Supervisor status.

Do not self-translate a non-COMPLETE result into PASS.

---

# 8. Final live MCP activation test

Round 3 previously failed to activate new wrappers in the externally owned Gateway process.

For this repair:

1. restart the externally owned Gateway using the existing independent launcher procedure after the affected artifact is refreshed;
2. verify `/health` is HTTP 200;
3. verify Desktop-visible `tools/list` includes at least:

```text
harness_health
harness_begin
harness_status
harness_observe
harness_preflight
harness_complete
harness_read_required
harness_checkpoint
```

4. fully exit/reopen Codex Desktop once;
5. verify the independently launched Gateway remains alive;
6. verify MCP reconnects without changing `required=false`.

Do not report a direct Runtime-port call as a live MCP PASS.

---

# 9. Real black-box task

After all focused tests above pass, run one real Codex Desktop task through the live MCP:

> 分析6801芯片etimer这个IP，复核现有两份文档是否仍符合当前项目规则；不要修改PC、Firmware或Harness框架代码。

Do not inject source paths, rules, validation commands or previous conclusions into the user task.

Required chain:

```text
harness_begin
-> project/context/rule/knowledge route
-> harness_read_required for required filesystem resources
-> real bounded analysis / harness_observe
-> harness_preflight before any planned mutation
-> harness_checkpoint
-> harness_status
-> harness_complete
```

The black-box result is PASS only if the repaired trusted event path is actually used through live MCP.

---

# 10. Evidence storage

During the governed ATP task, do **not** write campaign evidence inside the repository because those files are outside the ATP task's business write scope.

During execution, store raw/bounded temporary evidence outside the governed workspace, for example under the existing ET Harness state area:

```text
D:\lihuan\vibe_code\codex\et_harness_env\state\pure-mcp-fast-track\round3-p0-repair\
```

Only **after the governed task has reached its final Runtime result**, copy bounded evidence into:

```text
agent_harness/test_campaigns/round3_p0_repair/evidence/
```

Commit only bounded evidence, never secrets, auth data, hidden reasoning or huge logs.

Required final files:

```text
evidence/
├── 00_environment.md
├── 01_build_and_focused_tests.md
├── 02_preflight.json
├── 03_required_reads.jsonl
├── 04_checkpoint.json
├── 05_closure.json
├── 06_live_mcp.md
├── 07_black_box.md
└── ROUND3_P0_FINAL_REPORT.md
```

Every PASS/FAIL claim must point to an exact command, MCP result, event ref or status field.

---

# 11. Result classification

Final status must be exactly one of:

```text
ROUND3_P0_REPAIR_PASS
ROUND3_P0_REPAIR_PARTIAL
ROUND3_P0_REPAIR_FAIL
```

PASS requires all of the following:

```text
PROTECTED_PREFLIGHT_BLOCKS                 PASS
AUDIT_CAPABILITY_REMAINS_TRUTHFUL          PASS
REQUIRED_READ_TRUSTED_EVENTS               PASS
CHECKPOINT_REJECTS_PENDING_READS            PASS
CHECKPOINT_TRUSTED_VALIDATION_EVENTS        PASS
VALIDATION_OBLIGATIONS_ADVANCE              PASS
PREMATURE_COMPLETE_STILL_BLOCKED            PASS
REFLECTION_TRIGGERED                        PASS
CLOSURE_REACHED_COMPLETE                    PASS
CONTEXT_UPDATE_REACHED                      PASS
LIVE_MCP_NEW_TOOLS_ACTIVE                   PASS
GATEWAY_SURVIVES_CODEX_RESTART              PASS
REAL_DESKTOP_BLACK_BOX                      PASS
```

Rehydration and Knowledge promotion may be reported separately if the actual task policy makes them applicable; do not manufacture them just to make this P0 repair pass.

---

# 12. Stop / handoff

At the end:

1. ensure worktree is clean;
2. commit only test evidence plus any narrowly necessary compile/test correction;
3. push to the same branch;
4. do not start another round;
5. report only:

```text
Final Commit SHA:
Overall Status:
Failed Checks:
Architecture Review Required:
Evidence Directory:
```

If a repaired P0 still fails for a semantic/architecture reason, preserve the evidence and stop. The architecture owner will decide the next change.
