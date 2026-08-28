# ATP Current ChatGPT Real-Project Test Charter v0.1

> **Status: FROZEN / NORMATIVE**  
> **Owner intent: User-defined and user-controlled**  
> **Scope: ET Harness + Automated Testing Platform real-project validation**  
> **Agent under test: the current ChatGPT conversation running GPT-5.6 Pro**  
> **Version: 0.1**  
> **Change rule: this charter must not be weakened, reinterpreted, or replaced without explicit user approval.**

---

## 0. Why this charter exists

This charter freezes the real test objective after repeated route drift.

Previous work mixed together several different questions:

```text
Can Public Harness packages build?
Can a synthetic provider close a turn?
Can GitHub Actions invoke Copilot CLI?
Can a provider token authenticate?
Can the current ChatGPT conversation work through Harness on a real project?
```

These are different tests. Treating one as evidence for another caused repeated wrong turns, especially the substitution of Copilot CLI for the current ChatGPT conversation.

From this document onward, the primary ATP real-project test has one fixed objective and one fixed Agent identity.

---

# 1. The single primary objective

The only primary objective is:

> **Prove whether the current ChatGPT conversation, running GPT-5.6 Pro, can act as an external Agent through ET Harness, automatically receive the Automated Testing Platform project context, Architecture, Rules, Knowledge and Gates, and complete a real project task under those constraints.**

The purpose is not to prove that GPT is intelligent enough to guess the project structure.

The purpose is to prove that:

```text
ET Harness
can turn a general-purpose GPT
into a governed project Agent
for a real existing project.
```

---

# 2. What exactly is under test

The end-to-end subject is:

```text
User raw business task
        ↓
ET Harness Runtime
        ↓
ATP Project Plugin
        ↓
Project resolve
        ↓
Task Context
        ↓
Architecture / Rule / Knowledge / Gate routing
        ↓
External Chat Agent request package
        ↓
Current ChatGPT conversation / GPT-5.6 Pro
        ↓
Project and authorized external-source work
        ↓
Structured response
        ↓
Framework validation
        ↓
Evidence
        ↓
Reflection
        ↓
Closure
        ↓
Knowledge candidate / next-turn reuse
```

Every layer above must be distinguished in evidence. A PASS at one layer must not be presented as a PASS for a later layer.

---

# 3. Fixed Agent identity

The Agent under test is fixed as:

```text
Current ChatGPT conversation
Model: GPT-5.6 Pro
Role: External governed Agent
```

The following are not equivalent substitutes:

```text
Copilot CLI
GitHub Actions hosted model calls
OpenAI API invoked by CI
DeepSeek API
Claude Code
Codex CLI
Mock provider
Deterministic provider
Synthetic semantic provider
```

Those providers may be tested later in separate provider-compatibility matrices, but they cannot be used as evidence that the current ChatGPT conversation passed this charter.

If the Agent identity changes, the run is a different test and must use a different charter or version.

---

# 4. Fixed project identity

The real project is fixed as:

```text
Repository: abba-labs/et-harness
Long-lived project branch: project/automated-testing-platform
Project ID: et-automated-testing-platform
Project: Automated Testing Platform
```

The project is an existing, self-contained system. Harness does not redesign it and does not take ownership of its business implementation.

Responsibilities remain:

```text
Automated Testing Platform
= project code, project rules, project tests, project business truth

ATP Project Plugin
= standard identity and A/R/K/G projection

ET Harness
= Agent governance, routing, context, evidence, reflection and closure
```

---

# 5. Fixed transport model

The transport for this test is fixed as a data-only External Chat Agent Bridge, preferably the existing GitHub Issue mailbox pattern.

Correct role separation:

```text
Harness Runtime
    ↓ creates GenericModelGenerateRequest
External Chat Agent Bridge / Mailbox
    ↓ transports request only
Current ChatGPT conversation
    ↓ produces GenericModelGenerateResponse
External Chat Agent Bridge / Mailbox
    ↓ transports response only
Harness Runtime
    ↓ validates and closes
```

The transport must not own:

```text
project selection
Architecture routing
Rule routing
Knowledge policy
Gate decisions
Reflection trigger
Closure decision
Knowledge promotion
```

GitHub Actions may orchestrate request creation, persistence, validation and CI. It must not replace the current ChatGPT conversation with Copilot or another model.

---

# 6. The first frozen real task

The first real ATP Pilot input is exactly:

```text
分析6801芯片etimer这个IP。
```

The user supplies only this raw task.

No test coordinator, Harness developer, outer assistant, Workflow, mailbox text or hidden prompt may add manual business guidance such as:

```text
which eTimer source files to read
which Google Drive folders to search
which Rule IDs to apply
which Architecture IDs to apply
which output files to create
which output chapters to use
which register fields to inspect
which Driver APIs to analyze
```

Those decisions must come from the automatic ATP project route, Task Context and routed project rules.

A Harness-generated request containing automatically selected A/R/K/G, scope and output contract is not considered an improper hint; generating that request is the capability being tested.

---

# 7. What “automatic” means in this charter

A step counts as automatic only when its occurrence and result are produced by the Framework from the raw task and persisted as evidence.

The following must be automatic:

```text
ATP project resolution
project root binding
Task Context compilation or equivalent governed context construction
Architecture selection
Rule selection
Knowledge selection and trust policy
Gate selection
read/write scope construction
output contract construction
response validation
Reflection requirement
Closure decision
Knowledge capture decision
```

The following do not prove automatic routing by themselves:

```text
GPT guessed a relevant file name
GPT already knew a likely rule
an operator manually pasted Rule IDs into the request
an operator told GPT where the eTimer Driver lives
an output happened to look correct
```

---

# 8. Google Drive and external sources

Google Drive is allowed as an external read-only project source for this analysis task.

Its role is:

```text
External Read-Only Source Capability
```

It is not:

```text
an Agent
a replacement for Project Knowledge
an ATP business Adapter
a source that automatically overrides current code or active rules
```

For each Drive source used, the execution record must preserve at least:

```text
source identity or file ID
file name
data-source category
access result: FOUND / NO_MATCH / UNAVAILABLE
what conclusion the source supports
whether the source is current, historical, planned or uncertain
```

Drive material cannot automatically become VALIDATED Project Knowledge. It must follow the Knowledge provenance and validation policy.

---

# 9. Two test layers that must never be confused

## 9.1 Layer A — Semantic governance with the current ChatGPT conversation

This is the immediate test.

It can prove:

```text
Harness generated the correct governed request
current GPT received A/R/K/G and task scope
current GPT followed or violated the request
Framework validated the returned result
Reflection and Closure occurred
knowledge was captured and reused
```

The current ChatGPT host may expose GitHub and Google Drive connectors directly. In this layer, those accesses must be reported and audited, but Harness cannot automatically claim that it mechanically intercepted every built-in connector call.

## 9.2 Layer B — Mechanical tool enforcement by a Host / Tool Bridge

This is a separate later test.

It must prove:

```text
every file read
every file mutation
every Drive access
every shell or build action
```

passes through Harness Tool Gateway before execution.

This requires a Host integration such as Codex, Claude Code, a self-hosted Agent, MCP Tool Proxy, or another environment where Harness owns the tool boundary.

**Layer A PASS must never be presented as Layer B PASS.**

---

# 10. Required evidence for a valid run

A valid run must preserve four evidence groups.

## 10.1 Routing evidence

At minimum:

```text
raw user task
request ID
project ID
project root or project binding
Task Context hash
Architecture IDs
Rule IDs
Knowledge IDs and trust tiers
Gate IDs
read scope
write scope
output contract
```

## 10.2 Execution evidence

At minimum:

```text
files and sources actually consulted
reason each source was consulted
Google Drive source disposition
Agent response payload
requested operations
actual project changes, if any
tool receipts available at this test layer
```

## 10.3 Rule-compliance evidence

The Framework must check, based on automatically routed ATP rules:

```text
output location and form
required sections or machine contracts
public IP semantics versus ET6801 chip facts
source completeness and disposition
confirmed facts versus unknowns
scope compliance
validation claims versus actual execution
forbidden project areas remain unchanged
```

The Agent’s own statement that it followed the rules is not sufficient.

## 10.4 Closure and learning evidence

At minimum:

```text
Framework-owned Evidence state
Reflection result
Closure Receipt
closure blockers, if any
Knowledge capture decision
Knowledge Candidate or explicit NONE decision
next-turn route showing reuse when applicable
```

---

# 11. PASS criteria

The real-task Pilot passes only when all of the following are true:

1. The Agent is the current ChatGPT conversation running GPT-5.6 Pro.
2. The user input is the frozen raw task without manual business hints.
3. Harness automatically resolves the ATP project.
4. Harness produces non-empty and task-relevant A/R/K/G routing.
5. The routed rules include the project’s actual IP-analysis obligations rather than only generic governance rules.
6. The current GPT performs the task through the external bridge.
7. External sources are used only within the authorized scope and are recorded with provenance.
8. The output is validated against the routed project rules.
9. Any project changes remain inside the generated write scope.
10. Unexecuted validation is reported as NOT_EXECUTED, never PASS.
11. Reflection is Framework-required and persisted.
12. Closure is decided by Framework and produces a Closure Receipt.
13. The final claim is tied to exact request, response, state and commit/run evidence.
14. A follow-up turn demonstrates appropriate knowledge/context reuse when the charter calls for learning validation.

A natural-language answer that looks correct is not enough.

---

# 12. Automatic FAIL conditions

The run is invalid or failed if any of the following occurs:

```text
Copilot or another provider replaces the current ChatGPT conversation
GitHub Actions directly calls a model and labels it the current ChatGPT test
manual paths, rules or output templates are added outside Harness routing
GPT is allowed to work directly before a Framework request exists
A/R/K/G is empty or generic-only for the IP-analysis task
rules are selected after the Agent output merely to justify it
Google Drive results have no source identity or provenance
Agent output is accepted without project-rule validation
Agent self-certifies Evidence or Closure
Reflection is skipped
Closure is inferred from a CI job exit code alone
Layer A semantic compliance is reported as Layer B mechanical enforcement
hardware, Keil, FPGA or HIL is reported PASS without execution
```

When a run fails, preserve the original task and acceptance criteria. Fix the responsible Framework layer and rerun without weakening the test.

---

# 13. Non-goals of this charter

This charter does not test:

```text
Copilot CLI authentication
GitHub organization Copilot policy
provider benchmark quality
which model is best
hardware execution
J-Link
Flash programming
FPGA programming
Keil product build
SIL/HIL
instrument control
full Tool Gateway enforcement in the ChatGPT host
```

These require separate charters and cannot block or substitute for this test.

---

# 14. Branch discipline

The contaminated Copilot Pilot branch is not the canonical base for this test.

The clean real-task route must be:

```text
project/automated-testing-platform
        ↓ clean dedicated branch
pilot/atp-et6801-etimer-external-chat-agent-v0.1
```

The dedicated branch may add:

```text
External Chat Agent mailbox orchestration
real-task request/response evidence
ATP-specific validation fixtures or receipts
Handoff records
```

It must not add:

```text
Copilot provider code
provider-specific authentication workarounds
manual eTimer paths in the task prompt
manual Rule IDs in the task prompt
weakened acceptance checks
```

No real-project Pilot changes may be merged to public `main`.

---

# 15. Roles and responsibilities

## User

```text
Defines the raw business task
Owns the purpose of the test
Approves any charter change
Decides whether the result is useful at the project level
```

## ET Harness Framework

```text
Resolves project
Builds governed context
Selects A/R/K/G
Defines scope and output contract
Validates results
Requires Reflection
Decides Closure
Manages Knowledge lifecycle
```

## Current ChatGPT / GPT-5.6 Pro

```text
Acts as the external Agent
Performs semantic analysis and judgment
Uses only the governed request and authorized sources
Returns structured results and honest uncertainty
Does not govern or certify itself
```

## External Chat Agent Bridge

```text
Transports request and response
Preserves correlation IDs and payload integrity
Does not implement governance logic
```

## GitHub Actions

```text
May run Harness and deterministic validators
May persist evidence and receipts
May orchestrate the mailbox
Must not replace the Agent with Copilot or another provider
```

---

# 16. Mandatory preflight before any future real-project run

Before starting, the operator or Agent must answer all items with exact evidence:

```text
[ ] Is the Agent under test the current ChatGPT conversation / GPT-5.6 Pro?
[ ] Is the base branch project/automated-testing-platform?
[ ] Is the Pilot branch clean and free of Copilot-provider substitutions?
[ ] Is the raw task unchanged?
[ ] Is the External Chat Agent bridge data-only?
[ ] Will Harness generate the request before GPT starts project work?
[ ] Will route IDs and context hash be persisted?
[ ] Are Google Drive permissions read-only and source-scoped?
[ ] Are semantic-governance and mechanical-tool claims separated?
[ ] Are output validation, Reflection and Closure Framework-owned?
```

If any answer is “no” or “unknown”, the run must not start.

---

# 17. Change control

This file is frozen.

Permitted change process:

```text
1. User explicitly approves a change in purpose, Agent identity or test scope.
2. Create a new charter version; do not silently rewrite the old evidence contract.
3. Record why the previous charter was insufficient.
4. Update the progress-context recovery order.
5. Rerun affected tests under the new version.
```

No Agent, Framework maintainer, Workflow or future conversation may redefine the objective merely because another route is easier to automate.

---

# 18. One-line invariant

> **This test exists to prove that the current ChatGPT conversation can work as a governed external Agent through ET Harness on the real Automated Testing Platform project; no other model, provider, automation environment or attractive shortcut may be substituted for that objective.**
