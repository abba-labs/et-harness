# [K001] Project Governance Knowledge

## [K001.001] AGENTS Is The Project Constitution

Status: VALIDATED
Category: C010.010
Fact: AGENTS.md is the ATP project constitution and the Agent's project entry; the public Project Plugin supplies routing context but does not replace that contract.
Scope: all governed work in et-automated-testing-platform
Provenance: source://project/et-automated-testing-platform/SRC000001
Tags: [agents, constitution, governance, entry]
Refs: [A010.010.010, R010.010.010]
Sources: [source://project/et-automated-testing-platform/SRC000001]

## [K001.002] Active Rule Text Has One Canonical Location

Status: VALIDATED
Category: C010.020
Fact: Active rule text is owned by report/design/rules/Rxxx_*.md; report/design/rule_owner_catalog.yaml is the machine Owner index, and Project Plugin Rule nodes are only routing projections.
Scope: rule discovery and rule maintenance
Provenance: source://project/et-automated-testing-platform/SRC000005
Tags: [rule-owner, canonical-source, projection]
Refs: [A010.010.030, R010.020.010]
Sources: [source://project/et-automated-testing-platform/SRC000001, source://project/et-automated-testing-platform/SRC000005, source://project/et-automated-testing-platform/SRC000009]

## [K001.003] Non-Trivial Work Requires A Compiled Task Context

Status: VALIDATED
Category: C020.010
Fact: Every new non-trivial task and every material scope expansion must compile a Task Context before reading or modifying project resources.
Scope: task start, resume and scope expansion
Provenance: source://project/et-automated-testing-platform/SRC000006
Tags: [task-context, compile, scope-expansion]
Refs: [A010.010.020, R010.010.020, G010.010.010]
Sources: [source://project/et-automated-testing-platform/SRC000001, source://project/et-automated-testing-platform/SRC000006]

## [K001.004] Missing Governance Routes Fail Closed

Status: VALIDATED
Category: C020.010
Fact: Missing module, change, rule Owner or required route data must fail closed; the Agent must not infer authority from filenames, history or conversation memory.
Scope: Task Context compilation and project routing
Provenance: source://project/et-automated-testing-platform/SRC000006
Tags: [fail-closed, route-miss, no-guessing]
Refs: [A010.010.020, R010.010.020]
Sources: [source://project/et-automated-testing-platform/SRC000004, source://project/et-automated-testing-platform/SRC000006]

## [K001.005] Scope Check Precedes Validation

Status: VALIDATED
Category: C020.020
Fact: After the task creates tracked changes and before project validation, scope-check must confirm that every new change is inside the compiled write_scope.allowed.
Scope: changed code, configuration, rules, documents and tools
Provenance: source://project/et-automated-testing-platform/SRC000006
Tags: [scope-check, write-scope, validation]
Refs: [A010.010.020, R010.010.030, G010.010.020]
Sources: [source://project/et-automated-testing-platform/SRC000001, source://project/et-automated-testing-platform/SRC000006]

## [K001.006] The Project Map Has Six Stable Modules

Status: VALIDATED
Category: C030.010
Fact: The current project system map defines six stable modules: ip-package, pc-platform, firmware-platform, operator-pipeline, companion-platform and governance.
Scope: project module selection and Architecture routing
Provenance: source://project/et-automated-testing-platform/SRC000002
Tags: [system-map, module, architecture]
Refs: [A010.010, A010.020, A010.030, A010.040, A010.050, A010.060]
Sources: [source://project/et-automated-testing-platform/SRC000002]

## [K001.007] Project Governance Files Are Navigation Resources

Status: VALIDATED
Category: C030.020
Fact: project-governance/system-map.yaml and project-governance/modules/*.yaml route tasks to code, Owner rules, write scopes and validation; they are not a second rule body, project-state store or history archive.
Scope: project-governance directory
Provenance: source://project/et-automated-testing-platform/SRC000004
Tags: [navigation, module-profile, projection-boundary]
Refs: [A010.010.020, R010.020.010]
Sources: [source://project/et-automated-testing-platform/SRC000003, source://project/et-automated-testing-platform/SRC000004]

## [K001.008] Validation Evidence Classes Are Not Interchangeable

Status: VALIDATED
Category: C040.020
Fact: Software, Keil, FPGA, SIL and HIL results must reflect what was actually executed; an unexecuted check is not PASS, and evidence from one backend or validation class cannot substitute for another.
Scope: validation results, reports and completion claims
Provenance: source://project/et-automated-testing-platform/SRC000001
Tags: [evidence, pass, not-executed, backend]
Refs: [R010.020.030]
Sources: [source://project/et-automated-testing-platform/SRC000001, source://project/et-automated-testing-platform/SRC000007]

## [K001.009] Project Software Validation Has A Fixed Minimum

Status: VALIDATED
Category: C040.010
Fact: Before committing code, configuration, rule, documentation or tool changes, the task-specific validation runs first, followed by python tools/validate_pc.py, git diff --check and git status --short.
Scope: tracked project changes before commit
Provenance: source://project/et-automated-testing-platform/SRC000001
Tags: [validate-pc, diff-check, git-status, software-gate]
Refs: [A010.050.010, R010.060.030, G010.010.030]
Sources: [source://project/et-automated-testing-platform/SRC000001]

## [K001.010] CI Closure Is Bound To The Exact Commit

Status: VALIDATED
Category: C040.030
Fact: GitHub CI is closure evidence only when every required workflow used for the claim has head_sha equal to the submitted commit SHA and conclusion success.
Scope: pushed branches and CI-backed completion claims
Provenance: source://project/et-automated-testing-platform/SRC000001
Tags: [ci, head-sha, exact-commit, closure]
Refs: [R010.060.040, G010.010.040]
Sources: [source://project/et-automated-testing-platform/SRC000001]

## [K001.011] ATP Work Is Isolated From Public Main

Status: VALIDATED
Category: C010.010
Fact: In abba-labs/et-harness, public main is Harness-only; ATP work derives from project/automated-testing-platform, and the project branch must not be merged wholesale back to main.
Scope: branch selection, project changes and repository integration
Provenance: source://project/et-automated-testing-platform/SRC000010
Tags: [project-branch, public-main, isolation, git]
Refs: [A010.010.010, R010.010.040]
Sources: [source://project/et-automated-testing-platform/SRC000010]

## [K001.012] Plans Reviews And Archives Are Not Active Rules

Status: VALIDATED
Category: C050.020
Fact: report/plans, report/review and report/archive contain intent, review or history and cannot override AGENTS.md, active Rxxx Owner text or current source and tests.
Scope: historical and planning material
Provenance: source://project/et-automated-testing-platform/SRC000001
Tags: [plans, review, archive, historical]
Refs: [R010.020.040]
Sources: [source://project/et-automated-testing-platform/SRC000001]

## [K001.013] Adapter Knowledge Is Project Scoped

Status: VALIDATED
Category: C050.010
Fact: Knowledge stored under agent_harness/projects/automated_testing_platform/knowledge belongs to et-automated-testing-platform scope; it must remain isolated from other projects and is not automatically public or global knowledge.
Scope: ET Harness ATP Project Knowledge library
Provenance: source://project/et-automated-testing-platform/SRC000009
Tags: [project-knowledge, scope, isolation, public-plugin]
Refs: [R010.020.010]
Sources: [source://project/et-automated-testing-platform/SRC000009]
