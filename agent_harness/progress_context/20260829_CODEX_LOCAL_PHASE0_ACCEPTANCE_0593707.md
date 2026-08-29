# Codex Local Phase 0 Acceptance — 0593707

> Status: **LOCAL_MECHANICAL_ACCEPTED**
> Date: 2026-08-29
> Repository: `abba-labs/et-harness`
> Acceptance source: `origin/main@059370706221a5af48686e3e93390c400b9795fa`

## 1. Source and environment identity

```text
remote: https://github.com/abba-labs/et-harness.git
source branch: origin/main
source HEAD: 059370706221a5af48686e3e93390c400b9795fa
recording branch: feat/execution-supervisor-phase1-event-store-replay-v0.1
recording branch base: f2a1dfa72ac585e02b01bbc70786eb77b9f1ad64
start source status: clean
Node: v22.23.2
npm: 10.9.8
host: Windows x64
shells: Git Bash and WSL2 Ubuntu/Linux
Linux kernel: 6.6.114.1-microsoft-standard-WSL2 x86_64
```

The final Linux-only gates used an archive created by Linux Git directly from the exact source HEAD. Runtime, npm cache, temporary directories, workspace and logs were all placed under:

```text
D:\lihuan\vibe_code\codex\et_harness_env\
```

## 2. Phase 0 package gate

Package:

```text
agent_harness/public_plugins/execution_supervisor
```

| Command | Result |
|---|---|
| `npm install --ignore-scripts --no-audit --no-fund` | PASS / exit 0 |
| `npm test` | PASS / 4 files / 17 tests |
| `npm run build` | PASS / exit 0 |
| `npm run benchmark -- --output ./baselines/phase0-local-current.json` | PASS / exit 0 |
| `validatePerformanceBaselineReport(generatedReport)` | PASS / valid report / 2 samples |

No canonical Phase 0 production source or test file changed during acceptance.

## 3. Benchmark evidence

Committed artifact:

```text
agent_harness/public_plugins/execution_supervisor/baselines/phase0-local-current.json
SHA-256: F83B4DF9126E39F0A41447D538A080AED0D51736B515FB2765C84FCD271471AB
sourceRevision: 059370706221a5af48686e3e93390c400b9795fa
thresholdsFrozen: false
```

Measurements, each after 2,000 warmups and across 10,000 samples:

| Scenario | p50 | p95 | p99 | mean | max |
|---|---:|---:|---:|---:|---:|
| Task-contract validation | 42.1 µs | 93.2 µs | 177.501 µs | 50.124 µs | 750 µs |
| Execution-event validation | 10.4 µs | 18.9 µs | 41.709 µs | 13.049 µs | 624.8 µs |

Phase 0 remains measurement-only; no numeric SLO was frozen.

## 4. Public repository and package gates

| Gate | Result |
|---|---|
| Public repository boundary checks | PASS / exit 0 |
| `git diff --check` within the boundary gate | PASS / exit 0 |
| Public package dependency-order loop | PASS / 21 of 21 packages tested and built |

Packages declaring `--passWithNoTests` retained their repository-declared command semantics; they were not converted into a stronger test claim.

## 5. Public integration gates

| Script | Final mechanical result |
|---|---|
| `phase3_public_plugins_v0_1_integration.sh` | PASS |
| `phase3_public_layer_v0_2_current_policy_integration.sh` | PASS |
| `phase4_public_auto_governance_orchestrator_v0_1_integration.sh` | PASS |
| `phase4a_public_agent_governance_kernel_step5_v0_1.sh` | PASS |
| `phase4a_public_governance_runtime_v0_1.sh` | PASS |
| `phase4a_public_governance_runtime_level2_model_v0_1.sh` | PASS |
| `phase4a_openai_compatible_model_wrapper_v0_1.sh` | PASS |

Final Linux log evidence for the two platform-sensitive gates:

```text
D:\lihuan\vibe_code\codex\et_harness_env\logs\level2_model_linux_d_drive.log
SHA-256: 605DC0A5B3C6E536F7266DEEF3065EF4E3D495E32497D769AB20AFF6B9882563

D:\lihuan\vibe_code\codex\et_harness_env\logs\openai_wrapper_linux_d_drive.log
SHA-256: 6F40077FAECCC3627B5C0748789D69711D5A45614F48D19E15B08ABA93A4C4A1
```

The Level-2 gate proved business-task preservation, automatic Context, visible-output observation, automatic Reflection, Knowledge classification, 8/8 Closure, exact Turn closure, provider independence, a thin model adapter and a Host-independent Pilot.

The wrapper gate additionally passed both OpenAI-compatible `responses` and `chat_completions` styles and emitted:

```text
PHASE4A_OPENAI_COMPATIBLE_MODEL_WRAPPER_V0_1=PASS
```

## 6. Preserved environment observations

Two Windows-only attempts did not count as final PASS evidence:

1. Git Bash mapped `/tmp` incorrectly for a nested Windows Node child process.
2. Windows npm Junction traversal caused the Python boundary scanner to inspect dependency source below `node_modules`, producing a false coupling match.

The scripts and checkers were not weakened. Both gates were rerun unchanged with Linux Node 22 against the exact main source archive, with every task-created artifact on D drive, and passed.

The first integration script also emitted one non-fatal temporary working-directory `grep` diagnostic before its explicit PASS marker and exit 0. It is recorded here rather than hidden.

An initial WSL `/tmp` attempt was aborted and its task-created files were removed. The accepted Linux runs used only the D-drive environment listed above.

The authorized Phase 1 branch-base receipt `f2a1dfa` was created before this local acceptance was recorded. That differs from the ideal ordering in the Handoff. The receipt added only provenance documentation, explicitly prohibited implementation before acceptance, and introduced no production source or test divergence from main. This ordering deviation is preserved here and is not presented as strict sequence compliance.

## 7. End-state audit

The exact captured `git status --short` from the disposable main validation worktree was:

```text
 M agent_harness/examples/governance_demo_plugin/dist/index.d.ts
 M agent_harness/examples/governance_demo_plugin/dist/index.js
 M agent_harness/governance_core/dist/catalog-engine.d.ts
 M agent_harness/governance_core/dist/catalog-engine.js
 M agent_harness/governance_core/dist/contracts.d.ts
 M agent_harness/governance_core/dist/contracts.js
 M agent_harness/governance_core/dist/cordis-service.d.ts
 M agent_harness/governance_core/dist/cordis-service.js
 M agent_harness/governance_core/dist/events.d.ts
 M agent_harness/governance_core/dist/events.js
 M agent_harness/governance_core/dist/index.d.ts
 M agent_harness/governance_core/dist/index.js
 M agent_harness/governance_core/dist/validator.d.ts
 M agent_harness/governance_core/dist/validator.js
?? agent_harness/governance_core/dist/metrics.d.ts
?? agent_harness/governance_core/dist/metrics.js
?? agent_harness/model_adapters/generic_model/dist/
?? agent_harness/model_adapters/generic_model/package-lock.json
?? agent_harness/model_adapters/json_process_client/dist/
?? agent_harness/model_adapters/json_process_client/package-lock.json
?? agent_harness/model_adapters/openai_compatible_wrapper/dist/
?? agent_harness/model_adapters/openai_compatible_wrapper/package-lock.json
?? agent_harness/pilots/generic_model/dist/
?? agent_harness/pilots/generic_model/package-lock.json
?? agent_harness/project_contract/dist/
?? agent_harness/project_contract/package-lock.json
?? agent_harness/public_plugins/agent_governance_closure_adapters/dist/
?? agent_harness/public_plugins/agent_governance_closure_adapters/package-lock.json
?? agent_harness/public_plugins/agent_governance_kernel/dist/
?? agent_harness/public_plugins/agent_governance_kernel/package-lock.json
?? agent_harness/public_plugins/architecture_navigator/dist/
?? agent_harness/public_plugins/architecture_navigator/package-lock.json
?? agent_harness/public_plugins/auto_governance_engine/dist/
?? agent_harness/public_plugins/auto_governance_engine/package-lock.json
?? agent_harness/public_plugins/auto_governance_orchestrator/dist/
?? agent_harness/public_plugins/auto_governance_orchestrator/package-lock.json
?? agent_harness/public_plugins/context_builder/dist/
?? agent_harness/public_plugins/context_builder/package-lock.json
?? agent_harness/public_plugins/evidence_state_manager/dist/
?? agent_harness/public_plugins/evidence_state_manager/package-lock.json
?? agent_harness/public_plugins/execution_supervisor/baselines/phase0-local-current.json
?? agent_harness/public_plugins/execution_supervisor/dist/
?? agent_harness/public_plugins/execution_supervisor/package-lock.json
?? agent_harness/public_plugins/experience_memory_manager/dist/
?? agent_harness/public_plugins/experience_memory_manager/package-lock.json
?? agent_harness/public_plugins/framework_efficiency_observer/dist/
?? agent_harness/public_plugins/framework_efficiency_observer/package-lock.json
?? agent_harness/public_plugins/gate_manager/dist/
?? agent_harness/public_plugins/gate_manager/package-lock.json
?? agent_harness/public_plugins/governance_runtime/dist/
?? agent_harness/public_plugins/governance_runtime/package-lock.json
?? agent_harness/public_plugins/knowledge_manager/dist/
?? agent_harness/public_plugins/knowledge_manager/package-lock.json
?? agent_harness/public_plugins/project_manager/dist/
?? agent_harness/public_plugins/project_manager/package-lock.json
?? agent_harness/public_plugins/rule_manager/dist/
?? agent_harness/public_plugins/rule_manager/package-lock.json
```

These were explained build/install outputs and the generated local benchmark. Canonical `execution_supervisor/src` and `execution_supervisor/tests` had no diff. None of the generated dist, dependency or lock files were transferred to the Phase 1 development worktree.

The authorized Phase 1 worktree was clean before this evidence record was added and its production source still had no divergence from main.

## 8. Acceptance decision

```text
LOCAL_MECHANICAL_ACCEPTED
```

This decision authorizes Phase 1 local development under the frozen Handoff. It does not claim:

```text
HOSTED_CI_ACCEPTED
ATP current-ChatGPT Pilot PASS
Phase 1 implementation PASS
Phase 2 authorization
```
