# Round 3 P0 Repair — Codex Execution Order

## 0. Role

You are the **Test Executor**.

The architecture repair has already been made by the Architecture Owner. Your job is to execute, verify, preserve evidence, and stop.

Do not redesign ET Harness. Do not expand this round.

You may make only a direct syntax/type/test-fixture correction if the committed repair cannot compile or execute as written. Any semantic or architectural problem must be recorded and handed back as `ARCHITECTURE_REVIEW_REQUIRED`.

---

## 1. Objective

Verify that the two Round 3 P0 defects are actually fixed in the real Pure MCP path without weakening existing governance semantics.

### P0-A — WRITE_SCOPE / protected-path preflight

Expected:

```text
explicit harness_preflight + allowed path      -> ALLOWED
explicit harness_preflight + outside scope     -> BLOCKED
Pure MCP Host supervision capability           -> remains AUDIT
claimsMechanicalInterception                   -> remains false
```

Do not fake `ENFORCE`.

### P0-B — Trusted execution evidence

Expected:

```text
harness_read_required
    -> Harness itself reads frozen required resource
    -> Harness hashes real content
    -> Runtime-owned RESOURCE_READ event
    -> REQUIRED_RESOURCE obligation advances

harness_checkpoint
    -> caller supplies only taskId
    -> Harness executes only frozen Task Context validations
    -> Runtime-owned TOOL_RESULT / VALIDATION_RESULT events
    -> VALIDATION obligations advance
```

The Agent must never be able to provide PASS state, trusted receipt, provider identity, arbitrary validation command, or raw execution event.

---

## 2. Baseline

Repository:

```text
abba-labs/et-harness
```

Branch:

```text
codex/fast-track-pure-mcp-atp-v0.1
```

Round 3 failing baseline:

```text
1301fa36395a7bb1ea06ae307936ac2339d922e5
```

Pull the current branch head before testing:

```text
git fetch
git checkout codex/fast-track-pure-mcp-atp-v0.1
git pull --ff-only
git status --short
```

The worktree must be clean before execution.

Read these two files before doing anything else:

```text
agent_harness/test_campaigns/round3_p0_repair/ROUND3_P0_CODEX_TEST_CHARTER.md
agent_harness/test_campaigns/round3_p0_repair/ROUND3_P0_EXECUTION_ORDER.md
```

This execution order is the operational sequence. The Test Charter remains the policy boundary.

---

# 3. Hard prohibitions

Do not:

- enable `required=true`;
- reinstall/re-enable Codex Plugin;
- enable Hook or Marketplace;
- modify Codex installation/cache;
- add filesystem watchers, polling loops, background scanners or Windows services;
- expose `ingestExecutionEvent()` directly as MCP;
- make `harness_observe` satisfy Supervisor obligations;
- let Agent-provided data become a trusted validation receipt;
- set `supportsToolInterception=true` or `supportsStableToolEventId=true`;
- duplicate Runtime, Ledger, Event Store, Gate, Closure or Context logic;
- rewrite ATP Project Plugin rules/validation just to pass the test;
- run repeated full-repository builds;
- continue into Round 4.

Do not modify unrelated user/project files.

---

# 4. Evidence rule

During the governed ATP task, **do not write campaign evidence inside the governed ATP workspace** because campaign evidence is not part of the ATP task business write scope.

Use an external temporary evidence directory during execution:

```text
D:\lihuan\vibe_code\codex\et_harness_env\state\pure-mcp-fast-track\round3-p0-repair\
```

After the governed task reaches its final Runtime result, copy only bounded evidence into:

```text
agent_harness/test_campaigns/round3_p0_repair/evidence/
```

Do not commit secrets, auth material, hidden reasoning, huge logs, node_modules, build caches, or raw binary dumps.

Every PASS/FAIL statement must point to at least one exact command, MCP response field, event reference, Runtime status field, or file hash.

---

# 5. Execution sequence

Run in this exact order.

## T0 — Environment and branch check

Record:

- current branch;
- HEAD SHA;
- `git status --short`;
- Node version;
- npm version if used;
- Gateway config path;
- current `required` value for `et_harness` MCP;
- external Gateway PID if running;
- whether port 8765 is listening.

Required result:

```text
branch = codex/fast-track-pure-mcp-atp-v0.1
worktree = clean
required = false
```

Save to temporary evidence as `00_environment.md`.

If branch/worktree/config is not as expected, stop before modifying code.

---

## T1 — Minimal build / compile

Build only what is required for the changed source to execute in the existing local deployment path.

Affected areas:

```text
agent_harness/public_plugins/governance_runtime/
agent_harness/projects/automated_testing_platform/
agent_harness/mcp_gateway_fast_track/
```

Rules:

1. No `npm install` unless an actual missing dependency error proves it is needed.
2. Build each affected package/artifact at most once unless a direct compile defect is corrected.
3. Do not build all unrelated packages.
4. Do not reinstall any Codex plugin.

Record exact commands, duration, exit codes, and any compile/test correction.

If a semantic change appears necessary, stop and report `ARCHITECTURE_REVIEW_REQUIRED`.

---

## T2 — Focused Gateway / Runtime regression tests

Run the smallest existing tests that cover:

- Gateway tool registration;
- `harness_preflight`;
- `harness_read_required`;
- `harness_checkpoint`;
- Runtime scope-safe service;
- ATP checkpoint/context contribution needed by this repair.

Do not run broad repository CI unless the focused tests indicate cross-package breakage.

Record:

```text
command
exit code
passed
failed
skipped
```

A focused test failure is not permission to redesign. Preserve evidence and isolate the exact failing boundary.

---

## T3 — Activate the real external Gateway

The externally owned Gateway must be independent of Codex Desktop.

Use the existing external launcher/lifecycle procedure only.

After refreshing the required local artifact/source:

1. stop the old Gateway cleanly if needed;
2. start the Gateway outside Codex Desktop;
3. verify the new PID;
4. verify `127.0.0.1:8765` is listening;
5. verify `GET /health` returns HTTP 200;
6. verify MCP initialize succeeds;
7. verify `tools/list` exposes at least:

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

If the live Gateway does not expose the new tools, stop. Do not perform a Runtime-port-only substitute and call it live MCP success.

---

## T4 — Create one fresh governed ATP task

Use the real ATP workspace and a fresh eTimer task.

User intent for this mechanical test should remain simple and should not inject source paths, rules, validation commands, expected results, or prior conclusions.

Use:

```text
分析6801芯片etimer这个IP，复核现有两份文档是否仍符合当前项目规则；不要修改PC、Firmware或Harness框架代码。
```

Call:

```text
harness_begin
```

Record exactly:

- `taskId`;
- `runtimeId`;
- `turnId`;
- `projectId`;
- `projectRevision` / `contextRevision` if returned;
- required `mustRead` entries;
- `writeScope`;
- protected paths;
- validations;
- Supervisor status / pending obligation count.

Do not alter the Task Context to make later tests easier.

---

## T5 — WRITE_SCOPE / protected-path preflight

Use the fresh task.

### Allowed probe

Call explicit preflight for:

```text
CREATE test_case_doc/etimer/round3_p0_probe.md
```

Expected:

```text
allowed = true
```

Do not create this probe file unless the later real task genuinely needs it.

### Forbidden probe

Call explicit preflight for:

```text
CREATE pc/et_test_platform/core/forbidden_round3_p0.py
```

Expected:

```text
allowed = false
```

Then verify the forbidden file does not exist.

Also record the negotiated supervision capability and confirm:

```text
effective level remains AUDIT
no claim of universal mechanical interception
```

PASS condition:

```text
allowed path -> true
outside/protected path -> false
forbidden file absent
AUDIT remains truthful
```

If the forbidden probe returns `allowed=true`, stop the round immediately and report P0-A failure.

Save bounded result as `02_preflight.json`.

---

## T6 — Required-read trusted evidence

Before reading required resources, call:

```text
harness_checkpoint(taskId)
```

Expected:

```text
status = BLOCKED
reason = REQUIRED_READS_PENDING
```

Then obtain the required filesystem-backed mustRead refs from `harness_begin` and read them one by one using:

```text
harness_read_required(taskId, resourceRef)
```

For each required read record:

- resourceRef;
- bytes;
- content hash;
- eventRef;
- event acceptance;
- obligationId;
- Supervisor status before/after if available.

Expected:

```text
Harness reads real file itself
Runtime accepts trusted RESOURCE_READ event
matching REQUIRED_RESOURCE obligation advances
```

### Negative controls

Attempt each without modifying files:

1. a file that is not a required mustRead item;
2. path traversal / arbitrary different file;
3. unsupported URI or unsupported resource kind where applicable.

Expected: fail closed; no trusted read event should be emitted for an unauthorized resource.

Do not fabricate events for a non-filesystem resource.

Save bounded records as `03_required_reads.jsonl`.

If required reads do not advance their Supervisor obligations, stop and report P0-B failure.

---

## T7 — Premature completion must still fail

Before trusted validations are complete, call the normal completion path once.

Expected:

```text
Runtime remains IN_PROGRESS / BLOCKED
Closure is not COMPLETE
```

This proves the repair did not weaken Closure.

Record:

- pending obligation IDs/count;
- Runtime decision;
- Closure response/reason.

If premature completion succeeds, stop immediately. This is a critical regression.

---

## T8 — Trusted checkpoint / validation

After required filesystem reads are satisfied, call only:

```text
harness_checkpoint(taskId)
```

Do not provide:

- command;
- PASS/FAIL;
- validation receipt;
- provider ID;
- obligation ID result;
- arbitrary event payload.

Verify:

1. only validations frozen in the Task Context are executed;
2. the Agent cannot inject an arbitrary command;
3. the result includes trusted event references/acceptance;
4. actual exit codes are preserved;
5. PASS validations advance matching Supervisor validation obligations;
6. a failing validation does not become PASS;
7. `harness_observe` is not accepted as a substitute for trusted validation evidence.

Record per validation:

```text
validationId
frozen command identity/hash if returned
exitCode
result
trusted eventRef(s)
obligation state before
after
```

Save bounded result as `04_checkpoint.json`.

If checkpoint can execute caller-supplied arbitrary commands or caller-supplied PASS state, stop immediately and mark critical trust-boundary failure.

---

## T9 — Status, Reflection, Closure, Context

After all applicable required reads and validations are satisfied:

1. call `harness_status`;
2. verify the execution obligations actually moved from PENDING to SATISFIED as appropriate;
3. submit a bounded truthful Reflection proposal through the normal completion path;
4. call `harness_complete`;
5. accept only Runtime's result as authoritative.

Record:

- final pending/satisfied/violated counts;
- Reflection status/receipt;
- Closure status;
- Knowledge decision if returned;
- Context update/revision if returned;
- final Supervisor decision.

Expected target:

```text
no fake Agent PASS
Runtime decides final completion
Reflection is generated/accepted through normal chain
Closure reaches COMPLETE only when obligations allow it
Context update occurs if current policy requires it
```

If Closure remains blocked, record the exact remaining obligation IDs and stop. Do not modify the Framework to force completion.

Save as `05_closure.json`.

---

## T10 — Codex Desktop black-box check

Only after T0-T9 focused/mechanical checks pass sufficiently to justify a live run:

1. fully exit Codex Desktop;
2. verify the external Gateway PID remains alive and port 8765 remains listening;
3. reopen Codex Desktop;
4. verify MCP reconnects;
5. verify the new tools remain visible;
6. run the same simple eTimer review intent through Codex Desktop;
7. verify the actual path uses:

```text
harness_begin
-> harness_read_required
-> governed analysis / harness_observe as needed
-> harness_preflight before mutation if any
-> harness_checkpoint
-> harness_status
-> harness_complete
```

Do not count direct Runtime test calls as this black-box PASS.

Record to `06_live_mcp.md` and `07_black_box.md`.

---

# 6. What matters most

Priority order for this verification:

```text
P0  protected/out-of-scope preflight is blocked
P0  required-read event is genuinely trusted and advances Ledger
P0  checkpoint evidence is genuinely trusted and advances Ledger
P0  Agent cannot forge trusted events/PASS/commands
P0  premature complete remains blocked
P1  Reflection and Closure can now run after trusted evidence
P1  Context update can now occur after Closure
P1  live Gateway exposes repaired tools
P1  Gateway survives Codex restart
P1  real Desktop task uses the repaired path
```

Do not spend time polishing output text while any P0 is unresolved.

---

# 7. Required final evidence files

After the governed task reaches its final Runtime result, copy bounded evidence into:

```text
agent_harness/test_campaigns/round3_p0_repair/evidence/
```

Required files:

```text
00_environment.md
01_build_and_focused_tests.md
02_preflight.json
03_required_reads.jsonl
04_checkpoint.json
05_closure.json
06_live_mcp.md
07_black_box.md
ROUND3_P0_FINAL_REPORT.md
```

`ROUND3_P0_FINAL_REPORT.md` must contain this exact matrix:

| Check | Result | Exact Evidence | Notes |
|---|---|---|---|
| PROTECTED_PREFLIGHT_BLOCKS | PASS/FAIL | ref | |
| AUDIT_CAPABILITY_REMAINS_TRUTHFUL | PASS/FAIL | ref | |
| CHECKPOINT_REJECTS_PENDING_READS | PASS/FAIL | ref | |
| REQUIRED_READ_TRUSTED_EVENTS | PASS/FAIL | ref | |
| REQUIRED_READ_OBLIGATIONS_ADVANCE | PASS/FAIL | ref | |
| CHECKPOINT_TRUSTED_VALIDATION_EVENTS | PASS/FAIL | ref | |
| VALIDATION_OBLIGATIONS_ADVANCE | PASS/FAIL | ref | |
| AGENT_CANNOT_FORGE_TRUSTED_RESULT | PASS/FAIL | ref | |
| PREMATURE_COMPLETE_STILL_BLOCKED | PASS/FAIL | ref | |
| REFLECTION_TRIGGERED | PASS/FAIL/BLOCKED_BY_UPSTREAM | ref | |
| CLOSURE_REACHED_COMPLETE | PASS/FAIL/BLOCKED_BY_UPSTREAM | ref | |
| CONTEXT_UPDATE_REACHED | PASS/FAIL/BLOCKED_BY_UPSTREAM | ref | |
| LIVE_MCP_NEW_TOOLS_ACTIVE | PASS/FAIL | ref | |
| GATEWAY_SURVIVES_CODEX_RESTART | PASS/FAIL | ref | |
| REAL_DESKTOP_BLACK_BOX | PASS/FAIL | ref | |

Do not convert an upstream-blocked downstream check into PASS.

---

# 8. Failure record format

For every failure, record exactly:

```text
Check:
Expected:
Actual:
Reproduction:
Evidence:
First failing boundary:
Suspected component:
Architecture change required: YES/NO/UNKNOWN
```

Do not fix a semantic/architecture failure yourself.

---

# 9. Final status

Overall result must be exactly one of:

```text
ROUND3_P0_REPAIR_PASS
ROUND3_P0_REPAIR_PARTIAL
ROUND3_P0_REPAIR_FAIL
```

Use `PASS` only when all P0 checks pass and the live MCP black-box path proves the repaired boundary is active.

A downstream Reflection/Context issue discovered after both P0s pass may produce `PARTIAL`; preserve exact evidence and stop for Architecture Owner review.

---

# 10. Commit and push

After testing:

1. copy bounded evidence into the repository evidence directory;
2. verify no secrets or huge logs are included;
3. `git status` and inspect every changed file;
4. commit only:
   - evidence/report files;
   - narrowly necessary direct compile/type/test correction, if any;
5. push to the same branch.

Suggested evidence-only commit message:

```text
test(round3): verify P0 trusted execution repair
```

If a narrow direct correction was necessary, describe it explicitly in the commit message/body and final report.

Do not start another round after push.

Final response to the user must contain only:

```text
Final Commit SHA:
Overall Status:
Failed Checks:
Architecture Review Required:
Evidence Directory:
```
