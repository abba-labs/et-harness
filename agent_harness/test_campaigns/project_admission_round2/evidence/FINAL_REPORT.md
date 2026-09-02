# Project Admission Round 2 Independent Validation Report

## Executive result

- Tested source SHA: `2bf842597415ef235d52fc213c197e50ac2cb89e`
- Tested branch: `architecture/project-admission-bootstrap-v0.1`
- Project Admission stale-fingerprint repair: `PASS`
- Natural-language-to-correct-TaskIntent admission path: `PASS`
- Real original Governance Runtime chain at this SHA: `NOT_EXECUTED`
- Overall current-SHA Governance validation: `INCOMPLETE_RUNTIME_EXECUTION`
- New product defects found in executed Admission scope: `0`
- Open prior semantic-binding issue carried forward: `PA-SRPWM-002`
- Stable D-drive Runtime touched: `NO`
- Product/environment/dependency changed by Test Executor: `NO`
- Total software gate: `FAIL — 1 failed, 842 passed, 9 skipped`

This is not an Overall PASS. The repaired Project Admission boundary is independently verified in
the executable isolated scope, while the real Supervisor/Ledger/Event Store/Closure chain remains
unexecuted because current-checkout dependencies are absent and controlled activation of the stable
D-drive Runtime was explicitly prohibited.

## Tested repair surface

The branch was fast-forwarded from remote and locked before measurement. From prior evidence HEAD
`e950e2449848306dc6819f553eb12afcb65329bd` to the tested SHA, only these files changed:

```text
agent_harness/mcp_gateway_fast_track/src/project-admission.mjs
agent_harness/mcp_gateway_fast_track/tests/project-admission.test.mjs
```

The production change removes the Gateway-local `bootstrapByWorkspace` cache and calls
`runtimeAccess.projectBootstrap(workspacePath)` for every admission attempt. The target test commit
adds same-controller Architecture v1-to-v2 coverage. ATP Plugin, Runtime Owner, Supervisor, Ledger,
Closure, Context, Knowledge, configuration and dependencies were unchanged by the repair range.

## Evidence levels and truth boundary

1. `Product module executed`: real `project-admission.mjs` and real `buildProjectBootstrap()` ran.
2. `Instrumented downstream boundary`: a deterministic counter replaced original Governance begin
   to prove whether Admission crossed the boundary. It is not a Runtime implementation.
3. `Committed wrapper regression`: real Gateway Governance wrapper ran with its committed
   `fakeRuntime`; this proves wrapper parsing/binding only.
4. `Real Runtime`: not executed. No wrapper result, source inspection or test-double count is used
   to claim Supervisor, Ledger, Event Store, Reflection or Closure PASS.

## Project Admission test results

| Test ID | Input / stimulus | Expected trigger | Actual module/decision | Runtime Turn | Ledger / Event Store | Result | First failing boundary | Attribution |
|---|---|---|---|---:|---|---|---|---|
| PA2-A01 | Exact project, SRPWM intent, no fingerprint | Admission + Bootstrap | `PROJECT_CONTEXT_REQUIRED`; A010.020.010 returned | 0 instrumented | 0 / 0 instrumented | PASS | none | none |
| PA2-A02 | Missing project declaration | Admission input validation | `INVALID_ARGUMENT: project is required` | 0 | 0 / 0 | PASS | none | none |
| PA2-A03 | Wrong project `APT` | Bootstrap + selector | `PROJECT_DECLARATION_MISMATCH` | 0 | 0 / 0 | PASS | none | none |
| PA2-A04 | Unknown fingerprint + valid TaskIntent | Fresh Bootstrap | `PROJECT_CONTEXT_REQUIRED` with current fingerprint | 0 | 0 / 0 | PASS | none | none |
| PA2-A05 | Same controller, v1 accepted context then Architecture v2, submit v1 | Fresh Bootstrap v2 | v1 rejected; v2 Bootstrap/fingerprint returned | 0 | 0 / 0 | PASS | none | Framework repair verified |
| PA2-A06 | Current fingerprint, missing TaskIntent | Admission + fresh Bootstrap | `TASK_INTENT_REQUIRED` | 0 | 0 / 0 | PASS | none | none |
| PA2-A07 | Current fingerprint, malformed TaskIntent | Structural TaskIntent validator | `INVALID_ARGUMENT` | 0 | 0 / 0 | PASS | none | none |
| PA2-A08 | Current v2 fingerprint + valid ETIMER TaskIntent | Canonicalization + original Governance begin | `ACTIVE`; exactly one downstream begin | 1 instrumented | 1 / 1 instrumented | PASS | none | none |

For PA2-A01/A03/A04/A05/A06/A07, zero means the downstream Governance boundary was never called.
Durable Runtime/Ledger/Event Store zero-state is separately classified `NOT_EXECUTED /
OBSERVABILITY_GAP`, because the real owners were not activated or queried.

### Stale fingerprint mechanical values

```text
v1 fingerprint: sha256:32294eba5c6475443ce52537e50252e895dd410cea392c4a1f49dc9fb1d0aa73
v2 fingerprint: sha256:53eaf5cde3b6ed1d50727ecd513061f85248c68ca0865341b0c6ac0dc6273b07
bootstrap reads after initial v1 + stale-v1 attempt: 2
stale-v1 decision: PROJECT_CONTEXT_REQUIRED
Runtime/downstream begins after stale-v1 attempt: 0
fresh-v2 decision with valid TaskIntent: ACTIVE
bootstrap reads after fresh-v2 attempt: 3
Runtime/downstream begins after fresh-v2 attempt: 1
```

The former Gateway cache therefore no longer acts as freshness authority in the tested controller.

## Natural-language task entry results

Every case first executed without a fingerprint and returned `PROJECT_CONTEXT_REQUIRED` before any
downstream Governance call. The second attempt used the returned current fingerprint plus an
Agent-authored structured TaskIntent.

| Test ID | Human intent | Agent entity | First canonical IP candidate | Bootstrap-stage old classifier reached? | Result |
|---|---|---|---|---|---|
| PA2-NL01 | ET6801 ETIMER `IP and SDK` | `chip=ET6801; ip=ETIMER` | `etimer` | NO | PASS |
| PA2-NL02 | Chinese ET6801 XBAR registers/routes/test boundary | `chip=ET6801; ip=XBAR` | `xbar` | NO | PASS |
| PA2-NL03 | `项目：ET Automated Testing Platform，帮我分析SRPWM这个ip。` | `chip=ET6801; ip=SRPWM` | `srpwm` | NO | PASS |
| PA2-NL04 | Long mixed Chinese/English SRPWM IP-and-SDK request with constraints | `chip=ET6801; ip=SRPWM` | `srpwm` | NO | PASS |

Proven:

- Bootstrap succeeds before the ATP open-language classifier is reachable.
- Correct Agent TaskIntent entities are placed before original human prose.
- `and` is not the first IP candidate when the Agent supplies `ip=ETIMER`.
- Long complex human prose does not fail during the bootstrap stage.

Not proven:

- The real ATP Context Contributor was not executed in this isolated checkout.
- A semantically wrong but structurally valid Agent TaskIntent is not reclassified by Admission;
  prior finding `PA-SRPWM-002` remains for Architecture Owner disposition.

## Committed regression results

### Project Admission

```text
command: node --test agent_harness/mcp_gateway_fast_track/tests/project-admission.test.mjs
tests: 6
pass: 6
fail: 0
exit: 0
```

The passing set includes exact aliases, canonical entity ordering, three-stage admission, unknown
fingerprint rejection, same-controller Architecture freshness, and bounded TaskIntent validation.

### Gateway Governance wrapper and launcher policy

```text
command: node --test agent_harness/mcp_gateway_fast_track/tests/governance.test.mjs agent_harness/mcp_gateway_fast_track/tests/launcher-policy.test.mjs
tests: 11
pass: 11
fail: 0
exit: 0
```

What this proves: the Gateway wrapper still resolves configured project roots, fails closed for
missing/ambiguous bindings, parses fake Runtime context fields, preserves task identity, forwards
observe/preflight/complete and keeps launcher ancestry policy.

What it does not prove: the committed tests use `fakeRuntime`; they do not execute real Project,
Architecture, Rule, Knowledge, Gate, Supervisor, Ledger, Event Store, Reflection or Closure owners.

### Independent Admission probe

```text
command: node --experimental-strip-types agent_harness/test_campaigns/project_admission_round2/evidence/admission_probe.mjs
records: 12
pass: 12
fail: 0
exit: 0
```

The probe reads the actual ATP project manifest and Architecture file identity, invokes the real
`buildProjectBootstrap()` and real Project Admission module, and emits one JSONL record per test.

## Runtime-dependent test entry results

These are test-entry failures before any Runtime test body. They are `NOT_EXECUTED`, not product
FAIL and not PASS.

| Entry | Load failure | Test body | Classification |
|---|---|---|---|
| `frozen-runtime-wiring.test.mjs` | package `zod` absent | not entered | NOT_EXECUTED / Environment limitation |
| `runtime-release.test.mjs` | module `@deepseek-ai/cordis` absent | not entered | NOT_EXECUTED / Environment limitation |
| `mcp-protocol.test.mjs` | package `@modelcontextprotocol/sdk` absent | not entered | NOT_EXECUTED / Environment limitation |

Environment facts:

```text
Node: v24.16.0
agent_harness/mcp_gateway_fast_track/node_modules: ABSENT
dependency install: NOT PERFORMED
stable D-drive Runtime fallback: NOT ACCESSED
```

## Original Governance chain capability result

| Capability | Current-SHA real module result | What was observed without overstating it |
|---|---|---|
| Project Route | NOT_EXECUTED | Gateway wrapper test parsed a fake Runtime project binding |
| Architecture Route | NOT_EXECUTED | Bootstrap builder emitted A010.020.010 from instrumented Navigator data |
| Rule Route | NOT_EXECUTED | Gateway wrapper parsed a fake rule owner |
| Knowledge Route | NOT_EXECUTED | no real owner invoked |
| Gate Route | NOT_EXECUTED | Gateway wrapper parsed fake gate/validation fields |
| WRITE_SCOPE | NOT_EXECUTED | fakeRuntime returned BLOCKED; not accepted as real enforcement |
| Required Read | NOT_EXECUTED | frozen wiring entry failed before test body |
| Trusted Validation | NOT_EXECUTED | frozen wiring entry failed before test body |
| Execution Supervisor | NOT_EXECUTED | no real Supervisor constructed |
| Obligation Ledger | NOT_EXECUTED | no real Ledger constructed or changed |
| Completion | NOT_EXECUTED | fakeRuntime COMPLETE is not accepted as real Completion evidence |
| Reflection | NOT_EXECUTED | no real Reflection validated or persisted |
| Closure | NOT_EXECUTED | no real Closure receipt generated |

The full 39-row inventory, including Project Admission, Project Bootstrap and the original 37
mandatory governance modules, is in `module_behavior_matrix.json`.

## Negative controls

| Control | Result | First failing boundary | Attribution |
|---|---|---|---|
| missing human project | PASS | none | none |
| wrong project | PASS | none | none |
| unknown fingerprint | PASS | none | none |
| stale fingerprint | PASS | none | Framework repair verified |
| malformed TaskIntent | PASS | none | none |
| missing TaskIntent | PASS | none | none |
| forged validation cannot satisfy Ledger | NOT_EXECUTED | dependency resolution before Runtime | Environment limitation |
| premature completion must BLOCK | NOT_EXECUTED | dependency resolution before Runtime | Environment limitation |
| protected WRITE_SCOPE must BLOCK | NOT_EXECUTED | dependency resolution before Runtime | Environment limitation |

Exact per-control fields are in `negative_controls.json`.

## State and mutation result

- Product diff from tested SHA after measurement: none.
- Protected scope diff: none.
- Admission source blob remained `e20de6b9b908f87530fd04184a231f56c55dcd7e`.
- ATP project manifest blob remained `e71294cf379587f909988ff2cbbd79b3b197b2e9`.
- No local Runtime state, Ledger, Event Store or Gateway snapshot directory was created under the
  isolated checkout.
- Stable D-drive Runtime/state was neither read nor modified.
- Only `agent_harness/test_campaigns/project_admission_round2/evidence/` was written.

See `state_diffs.json` for the exact boundary counters and blob checks.

## Defect and gap summary

- `PA-SRPWM-001`: verified fixed at Project Admission boundary.
- New product defects in executed Admission scope: `0`.
- `PA-SRPWM-002`: prior semantic-binding finding remains open/outside this repair; positive correct
  TaskIntent behavior passes.
- `PA2-ENV-001`: current checkout cannot load real Runtime/Pure MCP tests without forbidden
  dependency/environment action.
- `PA2-OBS-001`: real durable zero-state before admission remains unproven; only the downstream
  begin boundary is directly counted.
- `PA2-BASELINE-001`: total software gate fails repository-layout policy because tracked `docs/`
  and pre-existing ignored local `tmp/` are present at the formal code root. Neither came from this
  repair or test evidence.

## Final software gate

```text
command: .\.venv\Scripts\python.exe tools\validate_pc.py
exit: 1
pytest: 1 failed, 842 passed, 9 skipped
failure: pc/et_test_platform/framework_validation/unit/code_quality/test_repository_layout.py::test_formal_code_root_has_only_stable_categories
unexpected root directories: docs, tmp
```

Attribution:

- `docs/` is tracked at the tested SHA; first-add history points to
  `fe4fdeafcda47195f169f29539c2e3c21e19ef0e`.
- `tmp/` is ignored, untracked, and has local creation/last-write timestamp `2026-08-31 12:41:39`,
  before this campaign.
- Project Admission repair range touched neither path.
- No cleanup or product change was authorized or performed.

## Required completion fields

```text
Final Evidence Commit SHA: pending evidence-only commit
Baseline Source SHA: 2bf842597415ef235d52fc213c197e50ac2cb89e
Real Scenarios Executed: Project Admission/Bootstrap only; original Runtime chain NOT_EXECUTED
Mandatory Modules Inventoried: 39 (2 admission/bootstrap + original 37)
Mandatory Modules Fully Covered In This Round: 2
Project Admission Repair Result: PASS
Original Governance Runtime Result: NOT_EXECUTED
Behavioral Validation Result: INCOMPLETE_RUNTIME_EXECUTION
Total Software Gate: FAIL (1 failed, 842 passed, 9 skipped)
New Product Defects Found: 0
Carried-Forward Open Finding: PA-SRPWM-002
Observability Gaps: 1 (PA2-OBS-001, blocked by environment)
Environment Limitations: 1 (PA2-ENV-001)
Environment Changed: NO
Stable D-drive Runtime Touched: NO
Architecture Review Required: YES for PA-SRPWM-002 and any controlled activation
Evidence Directory: agent_harness/test_campaigns/project_admission_round2/evidence/
```

Test Executor conclusion: the specific cached-stale-fingerprint defect is fixed at the independently
executable Admission boundary. No conclusion is made that the full Governance system passes at this
SHA until an Architecture Owner authorizes a controlled real Runtime activation or provides another
approved executable environment.
