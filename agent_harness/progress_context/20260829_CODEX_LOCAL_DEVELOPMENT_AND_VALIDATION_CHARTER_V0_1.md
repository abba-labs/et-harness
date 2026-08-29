# Codex Local Development And Validation Charter v0.1

> **Status: FROZEN / NORMATIVE FOR LOCAL DEVELOPMENT**  
> **Date: 2026-08-29**  
> **Repository: `abba-labs/et-harness`**  
> **Owner intent: user-defined and user-controlled**  
> **Primary local development Host: Codex in a local clone / WSL or Linux shell**  
> **Change rule: do not silently weaken this charter; any material change must be recorded in a new version or an explicit superseding decision.**

---

# 0. Why this charter exists

ET Harness development previously relied heavily on GitHub-hosted Actions for short feedback loops. That became inefficient for this repository because private-repository Actions usage reached the configured billing/budget boundary and GitHub began creating jobs without allocating a hosted runner.

Observed failure mode:

```text
workflow run created
job created
runner_id = 0
steps = []
conclusion = failure
```

This is not a source-code test failure, but it also means GitHub-hosted CI cannot currently be the only development gate.

The project therefore adopts a local-first development model:

```text
local Codex + local repository
        ↓
exact repository tests / build / benchmark / integration gates
        ↓
mechanical evidence bound to exact Git commit
        ↓
commit / push / PR
        ↓
GitHub primarily provides version history, review and remote backup
```

The purpose is **higher development efficiency without weakening governance correctness**.

The key rule is:

> **We are changing where mechanical validation executes, not what must be validated.**

---

# 1. Codex's role in this workflow

Codex has two conceptually different possible roles in ET Harness. They must not be confused.

## 1.1 Current role: development Agent

In this charter, Codex is the local software-development Agent that:

```text
reads the ET Harness repository
reads the frozen design and Handoff documents
modifies public Harness code on an authorized feature branch
runs local deterministic tests, builds and benchmarks
records exact evidence
commits and pushes reviewed changes
```

Codex is **not** allowed to redefine the framework objective merely because another implementation is easier.

## 1.2 Not the current ATP Agent-under-test

The frozen ATP real-project charter has a different subject:

```text
Current ChatGPT conversation / GPT-5.6 Pro
= external governed Agent under test
```

Codex local development must not be reported as proof that the ATP current-ChatGPT real-project charter passed.

Historical ATP charter can be inspected without switching the working branch:

```bash
git show project/automated-testing-platform:agent_harness/progress_context/20260828_ATP_CURRENT_CHATGPT_REAL_PROJECT_TEST_CHARTER_V0_1.md
```

That charter established an important testing principle reused here:

> A PASS at one layer must not be presented as a PASS for a later layer.

Codex may later be tested as a Host or semantic executor under a separate compatibility charter. That is not the present task.

---

# 2. Evidence authority hierarchy

For development-state claims, use this order:

```text
exact source tree / Git commit
> exact executed command and exit status
> generated test / benchmark / evidence artifact
> persisted Handoff / progress document
> Agent narrative or chat statement
```

Examples:

```text
"I think tests pass"                         = not evidence
"npm test exited 0 on commit X"             = evidence
"GitHub job existed but steps=[]"           = not executed
"benchmark JSON validates against contract" = evidence
```

No Agent, including Codex, may self-certify a stage PASS without the required mechanical evidence.

---

# 3. Canonical repository and branch model

The long-lived model remains:

```text
main
= public ET Harness canonical upstream

feat/<public-capability>
= one public capability / one development phase from a clean main

project/<name>
= public main + one real project + Project Plugin / A/R/K/G / project Knowledge

pilot/<name>
= real Pilot orchestration and evidence, not a public Runtime implementation base
```

Synchronization remains one-way:

```text
validated main
  ↓
project/<name>
  ↓
clean pilot branch
```

Project or Pilot branches must never be merged wholesale back into public `main`.

---

# 4. One conversation = one phase

To prevent drift and duplicated implementations:

```text
one conversation = one phase / one repair target
one phase         = one responsibility
one branch        = one phase
one canonical contract model
```

Before starting a new phase:

```text
previous phase has mechanical evidence
current main is clean
current main is pulled locally
new feature branch is created from that exact main
```

Do not run multiple public implementation phases in parallel unless the user explicitly approves it.

---

# 5. Local development environment

Preferred environment:

```text
Windows host
+ WSL/Linux working tree
+ Git
+ Node.js 22
+ npm
+ Codex local
```

The repository's CI currently uses Node 22, so local acceptance should also use Node 22 unless a test explicitly covers another runtime.

Codex must begin every development conversation by recording:

```bash
git remote -v
git branch --show-current
git rev-parse HEAD
git status --short
node --version
npm --version
```

Expected start condition for public development:

```text
working tree clean
remote points to abba-labs/et-harness
main fetched before branch creation
```

If the worktree is dirty, Codex must inspect the changes before proceeding. It must not silently discard user work.

---

# 6. Local mechanical acceptance model

GitHub-hosted Actions are no longer the mandatory high-frequency developer gate while hosted-runner billing is blocked.

Instead, we distinguish two evidence labels:

```text
LOCAL_MECHANICAL_ACCEPTED
HOSTED_CI_ACCEPTED
```

They are different claims.

## 6.1 LOCAL_MECHANICAL_ACCEPTED

A phase may receive local mechanical acceptance only when:

```text
exact Git source HEAD recorded
working tree clean before acceptance
repository-declared dependencies installed
repository-declared test commands executed
repository-declared build commands executed
required benchmark / integration commands executed
all required exit statuses are zero
negative/fail-closed tests pass
produced evidence is bound to the same source HEAD
working tree contains no unexplained source mutation after validation
```

Local mechanical acceptance may authorize development of the next phase when GitHub-hosted Actions are unavailable for billing/platform reasons.

## 6.2 HOSTED_CI_ACCEPTED

This label is used only when GitHub Actions actually allocates a runner and executes the steps successfully.

A job with:

```text
runner_id = 0
steps = []
```

can never be called `HOSTED_CI_ACCEPTED`.

## 6.3 Why local acceptance is not a weaker test

The local gate must execute the same substantive repository commands as CI.

Hosted CI provides an independent execution environment, but it is not the only possible source of mechanical truth.

When the project later uses a local/self-hosted runner, the same commands can become automated again without changing the validation semantics.

---

# 7. Phase 0 local acceptance procedure

Before Codex starts Execution Supervisor Phase 1, it must first perform one exact local acceptance of the repaired Phase 0 from current `main`.

The repaired Phase 0 public package is:

```text
agent_harness/public_plugins/execution_supervisor/
```

Its canonical source surface is intentionally small:

```text
src/baseline.ts
src/contracts.ts
src/hash.ts
src/index.ts
src/validation.ts
```

Its canonical tests are:

```text
tests/contracts.test.ts
tests/negative-contracts.test.ts
tests/performance-baseline.test.ts
tests/committed-baseline.test.ts
```

No removed PR #12 prototypes may be restored during acceptance.

## 7.1 Package gate

From the package directory:

```bash
cd agent_harness/public_plugins/execution_supervisor
npm install --ignore-scripts --no-audit --no-fund
npm test
npm run build
npm run benchmark -- --output ./baselines/phase0-local-current.json
```

The generated benchmark must also validate against the package's own `validatePerformanceBaselineReport()` contract.

The benchmark remains a measurement baseline. Numeric SLOs are not silently frozen in Phase 0.

## 7.2 Public repository boundary gate

Execute the same substantive boundary checks as `.github/workflows/harness-public-baseline.yml`:

```bash
set -euo pipefail

test -f agent_harness/projects/README.md
test ! -d agent_harness/projects/et_tool
test ! -d agent_harness/pilots/external_chat_agent
test ! -d agent_harness/pilots/real_provider
test ! -d source
test ! -d doc
test ! -d html

! grep -RIl --exclude='*.md' --exclude-dir=dist \
  -E '@agent-harness/project-et-tool|projects/et_tool' \
  agent_harness/governance_core \
  agent_harness/project_contract \
  agent_harness/public_plugins \
  agent_harness/model_adapters \
  agent_harness/pilots/generic_model

git diff --check
```

## 7.3 Public package build/test gate

Use the dependency order defined by `.github/workflows/harness-public-baseline.yml`.

Codex should reuse:

```bash
source agent_harness/validation/lib/common_runtime.sh
```

and run the public package loop from the workflow instead of inventing a different package subset.

## 7.4 Public integration gate

Run the same public integration scripts declared by the workflow:

```text
agent_harness/validation/phase3_public_plugins_v0_1_integration.sh
agent_harness/validation/phase3_public_layer_v0_2_current_policy_integration.sh
agent_harness/validation/phase4_public_auto_governance_orchestrator_v0_1_integration.sh
agent_harness/validation/phase4a_public_agent_governance_kernel_step5_v0_1.sh
agent_harness/validation/phase4a_public_governance_runtime_v0_1.sh
agent_harness/validation/phase4a_public_governance_runtime_level2_model_v0_1.sh
agent_harness/validation/phase4a_openai_compatible_model_wrapper_v0_1.sh
```

Local validation may call these scripts directly under WSL/Linux.

---

# 8. Local acceptance evidence record

Codex must not leave validation only in terminal scrollback.

After Phase 0 local acceptance, create a concise evidence document under:

```text
agent_harness/progress_context/
```

Recommended name:

```text
YYYYMMDD_CODEX_LOCAL_PHASE0_ACCEPTANCE_<SHORT_SHA>.md
```

It must include:

```text
repository
branch
source HEAD
remote HEAD checked against
Node version
npm version
OS / WSL environment
start git status
commands actually executed
exit status for every required gate
test counts
benchmark artifact path + SHA-256
public integration results
end git status
known limitations
final status
```

The final status must be one of:

```text
LOCAL_MECHANICAL_ACCEPTED
LOCAL_MECHANICAL_FAILED
BLOCKED_BY_ENVIRONMENT
```

If source code changes during the acceptance attempt, the acceptance is invalid for the original HEAD. Fix the code on an authorized branch and rerun against the new exact HEAD.

---

# 9. Efficiency rules for local Codex development

The development process itself must not become a source of waste.

Use this ladder:

```text
edit one bounded capability
→ run focused unit tests
→ run package build
→ run affected integration gate
→ only at phase completion run the full public baseline locally
```

Do not run the entire public repository after every line change.

For Execution Supervisor runtime design, preserve these product-level efficiency invariants:

```text
no LLM call on execution-event hot path
no full A/R/K/G reroute for ordinary event ingest
no full Context rebuild for ordinary event ingest
bounded event payloads
bounded in-memory indexes
idempotent replay
one normal Unified Reflection per Turn
```

Framework efficiency is achieved by incremental deterministic processing, not by dropping mandatory evidence or closure.

---

# 10. Forbidden shortcuts

Codex must not:

```text
modify main directly for feature implementation
continue from a stale Phase 1 branch
restore deleted PR #12 prototypes by cherry-pick
reuse the obsolete Contract Builder branch as Phase 1
hard-code ATP / ET6801 / eTimer into the public Execution Supervisor
introduce a second Task Supervision contract vocabulary
move project-specific obligations into public contracts
use Agent prose as trusted PASS evidence
skip negative tests because positive tests pass
call a model/network on the event-store hot path
start Phase 2 while Phase 1 acceptance is incomplete
claim GitHub CI PASS while GitHub jobs have steps=[]
```

---

# 11. Relationship to previous testing documents

This charter deliberately follows the structure learned from earlier ET Harness Test Charters and Handoffs:

```text
freeze the exact objective
freeze the Agent/Host role
freeze the branch and source identity
state what is under test
state what is not under test
separate evidence layers
state automatic FAIL conditions
preserve failure evidence instead of weakening the test
```

Historical references:

```bash
git show project/automated-testing-platform:agent_harness/progress_context/20260828_ATP_CURRENT_CHATGPT_REAL_PROJECT_TEST_CHARTER_V0_1.md

git show project/automated-testing-platform:agent_harness/progress_context/20260828_ATP_CURRENT_CHATGPT_CONTEXT_CONTRIBUTION_AND_PILOT_HANDOFF_V0_1.md
```

Those documents are historical/project-specific references. The current public Execution Supervisor development must follow Design 25 and this local-development charter.

---

# 12. Change control

A future Agent may not silently rewrite this development model.

Permitted change process:

```text
1. identify a concrete problem with the current local-development gate;
2. preserve the existing evidence;
3. propose a new charter version or explicit superseding decision;
4. explain whether the validation semantics become stronger, weaker or merely execute elsewhere;
5. update the progress-context recovery order;
6. never reinterpret old PASS/FAIL evidence after the fact.
```

---

# 13. One-line invariant

> **Codex may accelerate ET Harness development locally, but acceleration must come from faster deterministic feedback and clean phase boundaries—not from weakening contracts, evidence, negative tests, or Framework-owned completion semantics.**
