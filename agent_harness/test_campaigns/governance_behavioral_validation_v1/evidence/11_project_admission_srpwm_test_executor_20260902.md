# Project Admission SRPWM Test Executor Evidence — 2026-09-02

## 1. Execution identity and verdict

- Role: `Test Executor`
- Repository: `abba-labs/et-harness`
- Tested branch: `architecture/project-admission-bootstrap-v0.1`
- Tested source SHA: `67676a2916b01316794da042a813d0c338d14182`
- Human request: `项目：ET Automated Testing Platform，帮我分析SRPWM这个ip。`
- Human-declared project: `ET Automated Testing Platform`
- Intended IP: `SRPWM`
- Execution date: `2026-09-02` (`Asia/Shanghai`)
- Node: `v24.16.0`
- Product/framework repair authorized: `NO`
- Environment/dependency change authorized: `NO`
- Stable D-drive Runtime access authorized: `NO`
- Evidence commit: the Git commit containing this file; resolve with `git log -1 --format=%H -- <this-file>`
- Test verdict: `FAIL / NOT ACCEPTED`

The new admission happy path and its focused source regressions pass, including the intended
ET6801/ETIMER `and` case when the Agent supplies the correct structured TaskIntent. The tested
source nevertheless violates the required admission invariant in two adversarial cases:

1. a cached stale fingerprint is accepted without re-reading current Architecture and opens the
   original governance chain;
2. a structurally valid but semantically contradictory TaskIntent (`ip=AND`) is accepted and opens
   the original governance chain.

The repository software gate also fails at the tested SHA. Full frozen Runtime, Pure MCP,
Supervisor, Ledger and Closure end-to-end validation was not executed because the user explicitly
forbade touching the stable D-drive environment and this checkout has no installed Gateway
dependencies.

No Framework, ATP Plugin, Supervisor, Ledger, Closure, environment configuration or dependency was
modified during this test. Only this evidence record is added after measurement.

## 2. Tested change surface

Diff from pre-admission baseline `8cb771f6` to tested SHA:

```text
M agent_harness/mcp_gateway_fast_track/scripts/runtime-bundle-inputs.mjs
M agent_harness/mcp_gateway_fast_track/src/gateway.mjs
A agent_harness/mcp_gateway_fast_track/src/project-admission.mjs
A agent_harness/mcp_gateway_fast_track/src/project-bootstrap.ts
M agent_harness/mcp_gateway_fast_track/src/runtime-owner.ts
M agent_harness/mcp_gateway_fast_track/src/runtime-release.mjs
A agent_harness/mcp_gateway_fast_track/tests/project-admission.test.mjs
```

The ATP manifest and Architecture bootstrap used by the black-box controller tests were the actual
files from this checkout. The configured project resolved as:

- project ID: `et-automated-testing-platform`
- display name: `ET Automated Testing Platform`
- declared full project name accepted: `YES`
- relevant Architecture route observed: `A010.020.010 Analysis And Contract`

## 3. Required Project Admission sequence

Expected sequence frozen before execution:

```text
human explicitly declares project
  -> no valid Project Context fingerprint
  -> return bounded Architecture Bootstrap
  -> MUST NOT open Runtime Turn
  -> Agent supplies structured TaskIntent based on Architecture
  -> only current fingerprint + valid TaskIntent may enter original governance
```

### 3.1 Positive integration result

A black-box controller integration used the real `createProjectAdmissionController`, the real
`createGovernanceController`, the actual ATP project manifest/Architecture files, and a deterministic
in-memory Runtime double. It did not modify product source or persisted Runtime state.

| Stage | Input | Observed result | Runtime open count | Result |
|---|---|---|---:|---|
| 1 | full human-declared project, no fingerprint, no TaskIntent | `PROJECT_CONTEXT_REQUIRED`; bounded Architecture included `A010.020.010`; no `runtimeId` | 0 | CORRECT |
| 2 | returned fingerprint, no TaskIntent | `TASK_INTENT_REQUIRED`; no `runtimeId` | 0 | CORRECT |
| 3 | returned fingerprint plus structured SRPWM TaskIntent | original governance opened once | 1 | CORRECT |

Structured TaskIntent used at Stage 3:

```json
{
  "taskType": "IP_ANALYSIS",
  "entities": [
    { "kind": "ip", "id": "SRPWM" }
  ],
  "constraints": [
    "Architecture route A010.020.010"
  ]
}
```

Canonical intent passed to the original governance chain:

```text
Task type: IP_ANALYSIS
Entities: ip=SRPWM
Objective: 分析 SRPWM IP
Constraints: Architecture route A010.020.010
Original user request: 项目：ET Automated Testing Platform，帮我分析SRPWM这个ip。
```

Positive integration aggregate: `3 passed / 0 failed`.

### 3.2 ET6801/ETIMER natural-language `and` regression

Stimulus included ET6801, ETIMER and natural English conjunction `and`. The Agent-supplied
structured TaskIntent explicitly selected `chip=ET6801` and `ip=ETIMER`.

Observed:

- admission result entered the original governance chain;
- canonical entity order contained `chip=ET6801; ip=ETIMER`;
- `AND` was not selected as the IP in this correct structured-input path;
- the first IP candidate presented to the original governance logic was `ETIMER`.

Result for this bounded positive case: `CORRECT`.

This does **not** prove that arbitrary Agent output is safe. Section 5.2 demonstrates that
`ip=AND` is still accepted when supplied as a structurally valid TaskIntent.

### 3.3 Invalid fingerprint negative control

Input: a fingerprint that did not equal the returned Architecture fingerprint, with an otherwise
valid structured TaskIntent.

Observed:

- status: `PROJECT_CONTEXT_REQUIRED`;
- Architecture Bootstrap returned;
- original governance was not opened;
- no Runtime identity was exposed.

Result: `CORRECT` for an unknown/invalid fingerprint when it is not equal to the cached value.

## 4. Focused committed regressions

Command:

```powershell
node --test `
  agent_harness/mcp_gateway_fast_track/tests/project-admission.test.mjs `
  agent_harness/mcp_gateway_fast_track/tests/governance.test.mjs `
  agent_harness/mcp_gateway_fast_track/tests/launcher-policy.test.mjs
```

Result:

```text
tests 16
suites 0
pass 16
fail 0
cancelled 0
skipped 0
todo 0
exit 0
```

Passing subtests:

```text
T1 resolves the ATP project root
T2 resolves an ATP subdirectory to the same project
T3 fails closed when no configured project matches
T4 fails closed when the strongest project match is ambiguous
T5-T7 begin returns XBAR context, revisions, scope, owners, and validation
T8 contributor failure fails closed and persists no snapshot
T9 status reads the existing Runtime state through the saved binding
T10 thin wrappers bind task identity and preserve Runtime authority
T11 requestedTaskId is idempotent for equal input and conflicts for changed input
launcher policy accepts an independent Explorer or terminal ancestry
launcher policy rejects Codex Desktop and Codex-owned integrations
Project Admission accepts exact project aliases and refuses guessed names
TaskIntent canonicalization puts Agent-understood entities before human prose
New project context is forced through Architecture bootstrap before Runtime opens
Stale project context fingerprint refreshes Architecture without opening Runtime
TaskIntent validation remains bounded and project-agnostic
```

Interpretation: the committed test named “Stale project context fingerprint...” covers a supplied
fingerprint that is not equal to the controller's cached value. It does not cover Architecture
changing while a previously cached fingerprint is resubmitted. The latter case fails in Section 5.1.

## 5. Defect evidence

No defect was repaired during measurement.

### 5.1 PA-SRPWM-001 — cached stale fingerprint opens Runtime

- Severity: `P1`
- Result code: `WRONG_INPUT / NOT_ENFORCED`
- First failing boundary: Project Admission current Architecture validation
- Required behavior: fingerprint validity must be checked against current Architecture before the
  original governance chain opens.
- Stimulus:
  1. read Architecture bootstrap version v1;
  2. change the Runtime double's current Architecture to v2 inside the same Gateway/controller;
  3. submit the cached v1 fingerprint with a valid structured TaskIntent.

Raw observation:

```json
{
  "architectureReads": 1,
  "runtimeOpensAcrossTwoProbes": 2,
  "staleFingerprintResult": "ACTIVE",
  "acceptedFingerprint": "sha256:v1",
  "currentFingerprint": "sha256:v2"
}
```

The first probe establishes the cache; the second is the stale-fingerprint attempt. The
Architecture provider was read only once, the stale v1 fingerprint was accepted, and the second
probe entered the original governance chain.

Relevant source:

```text
agent_harness/mcp_gateway_fast_track/src/project-admission.mjs:153-159
153: const bootstrapByWorkspace = new Map()
154: const currentBootstrap = async (workspacePath, suppliedFingerprint) => {
155:   const cached = bootstrapByWorkspace.get(workspacePath)
156:   if (cached && suppliedFingerprint === cached.fingerprint) return cached
157:   const fresh = await runtimeAccess.projectBootstrap(workspacePath)
158:   bootstrapByWorkspace.set(workspacePath, fresh)
159:   return fresh
```

Conclusion: equality with a same-process cache is treated as current validity, so an Architecture
change that occurs after caching is not observed. This violates “only a valid/current fingerprint
may enter the original governance chain.”

### 5.2 PA-SRPWM-002 — contradictory `ip=AND` TaskIntent is accepted

- Severity: `P2`
- Result code: `WRONG_DECISION / NOT_ENFORCED`
- First failing boundary: Project Admission semantic binding of TaskIntent
- Required behavior: the ET6801/ETIMER request must not be misclassified as IP `and`; structured
  TaskIntent must be based on the human request and bounded Architecture output before admission.
- Human stimulus: a request containing `ET6801`, `ETIMER`, and natural-language `and`.
- Submitted structured value: `chip=ET6801; ip=AND`.

Raw observation:

```json
{
  "contradictoryResult": "ACTIVE",
  "canonicalEntities": "Entities: chip=ET6801; ip=AND"
}
```

Relevant source:

```text
agent_harness/mcp_gateway_fast_track/src/project-admission.mjs:185-195
185: if (input.taskIntent === undefined) {
186:   return stagedResponse({ status: 'TASK_INTENT_REQUIRED', taskId, bootstrap })
187: }
189: const taskIntent = normalizeTaskIntent(input.taskIntent)
190: const canonicalIntent = canonicalTaskText(taskIntent, intent)
191: const opened = await baseGovernance.begin({
192:   workspacePath,
193:   intent: canonicalIntent,
194:   requestedTaskId: taskId,
195: })
```

Conclusion: Project Admission proves that a TaskIntent is structurally bounded, but does not prove
that its entities agree with the human request or Architecture. The positive ETIMER result therefore
depends on the Agent having already made the correct semantic decision. The known `and`
misclassification is not prevented at the Framework admission boundary.

## 6. Eight-tool MCP contract

A read-only registration inspection over the Gateway and trusted-checkpoint sources found exactly
the original eight public MCP tool names:

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

Source registration locations:

- `gateway.mjs`: `harness_health`, `harness_begin`, `harness_status`, `harness_observe`,
  `harness_preflight`, `harness_complete`;
- `trusted-checkpoint.mjs`: `harness_read_required`, `harness_checkpoint`.

Result: `CORRECT` for the source registration contract.

Limitation: this is not a live MCP `initialize`/`tools/list` protocol result. This checkout's
`agent_harness/mcp_gateway_fast_track/node_modules` is absent, dependency installation was forbidden,
and the stable D-drive Runtime/Gateway environment was out of scope. Live eight-tool protocol
behavior is therefore `NOT_EXECUTED`, not PASS.

## 7. Frozen Runtime release negative tests

Command:

```powershell
node --test --test-name-pattern='stale Runtime|damaged Runtime' `
  agent_harness/mcp_gateway_fast_track/tests/runtime-release.test.mjs
```

Observed before any test body executed:

```text
Error: Cannot find module '@deepseek-ai/cordis'
Require stack:
- D:\lihuan\vibe_code\codex\projects\ET_Harness_ATP\agent_harness\mcp_gateway_fast_track\package.json
code: MODULE_NOT_FOUND
Node.js v24.16.0
tests 1
pass 0
fail 1
exit 1
```

Classification: `NOT_EXECUTED — DEPENDENCY_UNAVAILABLE_UNDER_EXPLICIT_CONSTRAINT`.

This result is not classified as a DUT regression because the test module failed during load. No
dependency was installed and the stable D-drive environment was not accessed.

## 8. Repository software gate

Command executed at tested SHA:

```powershell
.\.venv\Scripts\python.exe tools\validate_pc.py
```

Observed result:

```text
1 failed, 842 passed, 9 skipped
FAIL: pc/et_test_platform/framework_validation/unit/code_quality/test_repository_layout.py::test_formal_code_root_has_only_stable_categories
extra formal-code-root directories: docs, tmp
```

Attribution checks:

- tracked `docs/` exists in the tested target and in baseline `8cb771f...`; it was introduced before
  the two Project Admission commits;
- ignored local `tmp/` pre-existed this measurement and was not created, modified or removed here;
- neither item was changed during this test;
- regardless of attribution, the total gate is red at the tested checkout, so regression closure
  cannot be claimed for SHA `67676a2916b01316794da042a813d0c338d14182`.

Result: `FAIL` for the exact tested checkout. Project Admission-specific attribution for this layout
failure is not established.

## 9. Test-executor fixture incident

An initial in-memory positive integration attempt used shortened contribution IDs instead of the
official contribution IDs expected by the real governance controller. The controller correctly
failed closed with `CONTEXT_INCOMPLETE`.

Classification: `INVALID_TEST_FIXTURE / NOT_A_DUT_FINDING`.

Action taken: no product change. The test-only in-memory fixture was corrected to use the official
contribution IDs and the positive integration was rerun, producing the 3/3 result in Section 3.1.

A later read-only source-location command first attempted the nonexistent path
`agent_harness/src/host/project-admission.mjs`; it terminated at `Get-Content`. The correct tracked path
was then resolved with `rg --files` and inspected. Classification:
`TEST_EXECUTOR_COMMAND_PATH_ERROR / NOT_A_DUT_FINDING`.

## 10. Safety-boundary observations

The following bounded safety properties were directly observed in source regressions or admission
integration:

- unknown project roots fail closed;
- ambiguous strongest project matches fail closed;
- exact declared project aliases are accepted and guessed project names are refused;
- Architecture bootstrap precedes any Runtime open when fingerprint is absent or unequal to cache;
- absent TaskIntent prevents Runtime open after a matching fingerprint;
- bounded TaskIntent structural validation remains project-agnostic;
- launcher policy accepts independent Explorer/terminal ancestry and rejects Codex-owned ancestry;
- existing eight public MCP registrations remain present in source.

These observations do not override PA-SRPWM-001 or PA-SRPWM-002, and they do not substitute for the
unexecuted frozen Runtime/Pure MCP checks.

## 11. Explicitly not executed

| Area | Status | Reason |
|---|---|---|
| real frozen D-drive Runtime Turn | NOT_EXECUTED | user explicitly prohibited touching the stable D-drive runtime environment |
| live Gateway/Pure MCP `initialize` and `tools/list` | NOT_EXECUTED | checkout dependencies absent; install forbidden; stable environment out of scope |
| real Execution Supervisor behavior | NOT_EXECUTED | would require opening real Runtime Turn |
| real Obligation Ledger transitions | NOT_EXECUTED | would require opening real Runtime Turn |
| real Closure lifecycle | NOT_EXECUTED | would require governed Runtime completion |
| Runtime release stale/damaged test bodies | NOT_EXECUTED | module load stopped on missing `@deepseek-ai/cordis` |
| hardware/Keil/FPGA/HIL | NOT_EXECUTED | not required for Project Admission and no hardware authorization |
| CI for evidence-only descendant commit | NOT_VERIFIED at capture | evidence commit did not yet exist during measurement |

No unexecuted item is reported as PASS, and source registration evidence is not used as a substitute
for live MCP behavior.

## 12. Final acceptance statement

```text
Tested Source SHA: 67676a2916b01316794da042a813d0c338d14182
Real user request represented: YES
Positive admission sequence: PASS (bounded in-memory Runtime integration)
ET6801/ETIMER correct structured path: PASS
Current-fingerprint enforcement: FAIL
TaskIntent semantic binding / ip=AND rejection: FAIL
Original eight-tool source contract: PASS
Original eight-tool live MCP contract: NOT_EXECUTED
Frozen Runtime/Supervisor/Ledger/Closure regression: NOT_EXECUTED
Repository software gate: FAIL
Protected architecture/environment changed: NO
Defects found: 2
Architecture review required: YES
Overall Test Executor result: FAIL / NOT ACCEPTED
```

This evidence records behavior only. It makes no repair recommendation beyond identifying the first
failing boundary, and it does not declare Architecture Owner acceptance.
