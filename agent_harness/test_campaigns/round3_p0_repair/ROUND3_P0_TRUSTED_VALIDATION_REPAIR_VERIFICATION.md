# Round 3 P0 — Trusted Validation Repair Verification

## 0. Role and baseline

You are the Test Executor. Do not redesign ET Harness.

Repository/branch:

```text
abba-labs/et-harness
codex/fast-track-pure-mcp-atp-v0.1
```

Architecture Owner repair baseline:

```text
ef31b59637937b96d4c3a152f650aa7de999b2f3
```

Pull latest branch head before testing. The repair intentionally does **not** modify Execution Supervisor, Obligation Ledger, ATP rules, Closure, or the deterministic environment.

The repair changes only:

```text
agent_harness/mcp_gateway_fast_track/src/runtime-owner.ts
agent_harness/mcp_gateway_fast_track/src/runtime-release.mjs
agent_harness/mcp_gateway_fast_track/src/trusted-checkpoint.mjs
agent_harness/mcp_gateway_fast_track/tests/frozen-runtime-wiring.test.mjs
```

The design reuses the existing durable whole-span Evidence admission already implemented and replay-tested by Execution Supervisor. Runtime Owner internally queues an empty-message/no-claim span around the Runtime-owned validation receipt so that:

```text
ordinary direct VALIDATION_RESULT -> remains untrusted / obligation stays PENDING
Runtime-owned checkpoint validation -> admitted by existing trusted span rules
```

The empty visible messages are intentional: they provide the existing durable span binding without becoming task text during Runtime rehydration.

---

## 1. Hard boundaries

Do not:

- modify Node/npm/dependency bootstrap;
- run ad-hoc npm install;
- modify `prepare-environment.cmd`, `freeze-runtime.cmd`, `verify-environment.cmd`, or `refresh-gateway.cmd` unless a direct defect in those unchanged scripts is independently proven;
- modify Execution Supervisor or Obligation Ledger to accept raw direct `VALIDATION_RESULT`;
- weaken the existing trust-boundary regression that requires raw direct validation to remain PENDING;
- modify ATP WRITE_SCOPE, validation commands, Evidence Policy, Supervisor contract, Closure, or Context just to make the test pass;
- expose the internal trusted span method as an MCP tool;
- allow the Agent to supply request/response manifests, provider identity, validation receipts, PASS state, command, or event payloads;
- restore Plugin/Hook/Marketplace/Watcher/Windows Service;
- claim ENFORCE or mechanical interception; Pure MCP remains AUDIT.

If any broader architecture change appears necessary, preserve evidence and stop with `ARCHITECTURE_REVIEW_REQUIRED`.

---

## 2. Mandatory static/source review

Before execution confirm mechanically:

1. `runtime-owner.ts` still installs `ScopeSafeGovernanceRuntimeService`.
2. `ingestTrustedValidationSpan` is available only on the frozen Runtime module/internal access path, not `GovernanceHostRuntimePortV01` and not MCP `tools/list`.
3. The three events are queued synchronously before awaiting them:
   - `USER_MESSAGE` with bounded request manifest;
   - `VALIDATION_RESULT`;
   - `ASSISTANT_MESSAGE` with bounded response manifest.
4. Both visible message contents are empty strings and their hashes bind exactly to the empty content.
5. Response `receiptRefs` binds the exact validation event ID and canonical payload hash.
6. Existing Execution Supervisor test `trust-boundary-regressions.test.ts` still requires an ordinary direct `VALIDATION_RESULT` without a valid persisted span to leave the obligation PENDING.
7. No Execution Supervisor / Ledger source changed in the repair diff.

Record the review result before running the environment chain.

---

## 3. Deterministic environment verification

Use only the committed environment:

```text
agent_harness/mcp_gateway_fast_track/scripts/freeze-runtime.cmd
agent_harness/mcp_gateway_fast_track/scripts/verify-environment.cmd
```

Do not run `prepare-environment.cmd` unless the existing pinned environment is genuinely missing/invalid.

Required result:

```text
freeze-runtime        PASS
verify-environment    PASS
```

The updated `frozen-runtime-wiring.test.mjs` must prove in the real frozen Runtime + real ATP Project Plugin path:

```text
AUDIT remains truthful                         PASS
protected WRITE_SCOPE preflight blocks         PASS
checkpoint before required reads blocks        PASS
required reads advance obligations              PASS
forged direct VALIDATION_RESULT is ACCEPTED
  by Event Store but does NOT satisfy Ledger    PASS
Runtime-owned trusted checkpoint validations    PASS
all validation commands exit 0                  PASS
all matching VALIDATION obligations SATISFIED   PASS
```

This regression is the primary repair gate. Do not replace it with a fake Runtime or mock Ledger.

---

## 4. Existing Supervisor safety regression

Run the smallest existing Execution Supervisor tests needed to prove that the old trust boundary was not weakened, including at least:

```text
agent_harness/public_plugins/execution_supervisor/tests/trust-boundary-regressions.test.ts
agent_harness/public_plugins/execution_supervisor/tests/trusted-execution-replay.test.ts
```

Required invariant:

```text
raw/direct VALIDATION_RESULT without durable admitted span
-> validation obligation remains PENDING
```

and the existing admitted external span replay behavior must remain unchanged.

If these regressions fail, stop. Do not weaken them.

---

## 5. External Gateway activation

Only after Sections 2-4 pass:

```text
agent_harness/mcp_gateway_fast_track/scripts/refresh-gateway.cmd
```

Verify:

```text
GET /health = 200
status = UP/READY
pinned Windows Node 22
required = false
all eight existing MCP tools visible
```

The internal trusted validation span method must **not** appear in MCP `tools/list`.

---

## 6. Fresh Round 3 P0 real task

Run a fresh ATP governed task using the existing intent:

```text
分析6801芯片etimer这个IP，复核现有两份文档是否仍符合当前项目规则；不要修改PC、Firmware或Harness框架代码。
```

Run the existing Round 3 P0 chain in order. At minimum reconfirm:

```text
PROTECTED_PREFLIGHT_BLOCKS                 PASS
AUDIT_CAPABILITY_REMAINS_TRUTHFUL          PASS
CHECKPOINT_REJECTS_PENDING_READS           PASS
REQUIRED_READ_TRUSTED_EVENTS               PASS
REQUIRED_READ_OBLIGATIONS_ADVANCE          PASS
AGENT_CANNOT_FORGE_TRUSTED_RESULT          PASS
PREMATURE_COMPLETE_STILL_BLOCKED           PASS
CHECKPOINT_TRUSTED_VALIDATION_EVENTS       PASS
VALIDATION_OBLIGATIONS_ADVANCE             PASS
REFLECTION_TRIGGERED                       PASS
CLOSURE_REACHED_COMPLETE                   PASS
CONTEXT_UPDATE_REACHED                     PASS
GATEWAY_SURVIVES_CODEX_RESTART             PASS
REAL_DESKTOP_BLACK_BOX                     PASS
```

The crucial repaired boundary is:

```text
all frozen validation commands PASS
+ trusted span admission succeeds
+ matching VALIDATION obligations move PENDING -> SATISFIED
```

Do not self-translate a blocked Runtime result into PASS.

---

## 7. Evidence

Update the existing Round 3 evidence rather than creating a parallel campaign.

Record at minimum:

- exact tested HEAD;
- frozen release/source signature;
- `verify-environment` command/result/count;
- direct forged validation event acceptance and proof its obligation stayed PENDING;
- trusted checkpoint span request/validation/response event refs;
- validation exit codes;
- validation obligation states before/after;
- Supervisor safety regression results;
- Closure/Reflection/Context results;
- external Gateway PID/health/tools;
- Desktop restart/black-box result.

Do not commit secrets, raw hidden reasoning, huge logs, node_modules, caches, or Runtime artifacts.

---

## 8. Stop condition and report

If a new semantic failure appears outside this repair boundary, stop and preserve the first failing boundary.

After testing, commit/push bounded evidence and report only:

```text
Final Commit SHA:
Repair Baseline SHA:
Deterministic Environment: PASS / FAIL
Direct Validation Still Untrusted: PASS / FAIL
Trusted Validation Obligations Advance: PASS / FAIL
Supervisor Safety Regressions: PASS / FAIL
Overall Round3 P0 Status:
Failed Checks:
Architecture Review Required:
Evidence Directory:
```

Do not declare final Architecture Owner acceptance. The pushed SHA and evidence must be reviewed after execution.
