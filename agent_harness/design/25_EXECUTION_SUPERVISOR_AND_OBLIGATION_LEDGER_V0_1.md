# Execution Supervisor And Obligation Ledger v0.1

> Status: **DESIGN BASELINE / NORMATIVE FOR NEXT IMPLEMENTATION**  
> Date: 2026-08-28  
> Scope: Public ET Harness / Agent Governance  
> First real validation project: Automated Testing Platform  
> First frozen task: `分析6801芯片etimer这个IP。`  
> Change control: this design may be revised only by a new version with explicit reasons; later implementation must not silently weaken the guarantees defined here.

---

# 0. Executive decision

The current ET Harness already has most of the required governance capabilities:

```text
Project resolution
Architecture / Rule / Knowledge / Gate routing
Project Context Contribution
Task Context compilation
Context management
Evidence storage
Unified Reflection
Knowledge classification and candidate persistence
8/8 Mandatory Closure
Turn Journal and Closure Receipt
```

The ATP real-project Pilot exposed one missing public execution-plane capability:

> **The Framework can generate a governed task for an external Agent, but it cannot yet reliably supervise, ingest, replay and evaluate the external Agent's actual execution from task handoff through final Closure.**

The missing capability is defined here as:

```text
Public Execution Supervisor
+ Obligation Ledger
+ Host-neutral Execution Event / Receipt contract
+ Cross-process execution-state persistence and replay
+ Deterministic Completion Evaluator
```

This capability is **mandatory** for a reliable governance framework.

It is not a second Governance Kernel, not a second Context system, not a project-specific eTimer module, not an Efficiency Observer, and not another Agent. It is a deterministic public Runtime service that connects the existing modules into one enforceable and auditable execution loop.

The one-line invariant is:

> **The Agent may propose work and semantic conclusions; only the Framework may decide whether the governed task obligations are satisfied, whether claims have valid Evidence, whether Reflection and classification occurred, and whether the Turn or Task may close.**

---

# 1. Current problem and mechanical facts

## 1.1 What the ATP Pilot has proved

The current ChatGPT real-project Pilot has mechanically proved the front half of the chain:

```text
raw task preserved
→ ATP project resolved
→ project root bound
→ ATP Context Contributor invoked
→ Task Context compiled
→ Architecture routed
→ Rules routed
→ Knowledge routed
→ Gates routed
→ read/write scope generated
→ validation obligations generated
→ output contract generated
→ Turn Journal opened
```

The clean v0.3 Route and Context workflow passed on the exact frozen task. This means the Project Plugin and public routing/context path can produce a relevant governed request without manually adding eTimer file paths, Rule IDs or output instructions outside the Framework.

## 1.2 What the ATP Pilot has not proved

It has not yet mechanically proved the back half:

```text
current ChatGPT receives the request
→ actual tool/resource operations are ingested
→ execution order and identity are verified
→ violations are detected
→ required sources are proven handled
→ output claims are bound to Evidence
→ completion obligations are evaluated
→ Unified Reflection is triggered
→ Knowledge is explicitly classified
→ Context is updated
→ Mandatory Closure modules run
→ Closure Receipt is COMPLETE
→ Task is COMPLETED
→ next Turn reuses the resulting Context/Knowledge
```

A correct-looking eTimer document does not prove this chain.

## 1.3 Root cause

The original Public Governance Runtime was primarily implemented around a same-process topology:

```text
Runtime process
  ├─ openTurn()
  ├─ Agent/Host work
  ├─ observeWork()
  ├─ closeTurn()
  └─ Reflection / Closure
```

The current ChatGPT Pilot is a distributed topology:

```text
Process A: GitHub Actions / Runtime opens Turn and writes handoff
        ↓
Host B: current ChatGPT conversation performs work
        ↓
Process C: another Runtime process must ingest work and close Turn
```

Important Runtime state was previously held in memory:

```text
runtime sessions
activeTurnId binding
bounded Turn observations
semantic executor binding
reflection jobs
current review packets
```

The persistent stores preserved parts of the Task Context and Turn Journal, but there was no complete public contract for:

```text
cross-process Runtime rehydration
external Agent event ingestion
response/event ordering
idempotent replay
execution receipt validation
obligation state transitions
completion evaluation
```

The existing `rehydrateTask()` and `rehydrateTurn()` work is the first repair step. It restores the original Task/Turn identity and route in a new Host process, but it does not by itself provide a complete external execution event stream, live Obligation Ledger, claim/evidence evaluation, or end-to-end Closure runner.

## 1.4 Why existing modules are not enough by themselves

The missing capability must not be confused with existing modules:

| Existing module | What it already does | What it does not currently do |
|---|---|---|
| Auto Governance Engine | Resolves project, routes A/R/K/G, builds context, reacts to observed mutations | Does not own a durable external-Agent event stream or full task obligation state machine |
| Governance Runtime | Owns `openTurn / observeWork / closeTurn` lifecycle APIs | Does not yet fully transport and replay cross-Host Agent execution |
| Turn Journal / Kernel | Persists Turn lifecycle refs and coordinates Reflection/Closure | Does not independently know the actual external tool/resource events unless the Host reports them |
| Gate Manager | Evaluates declared Gate Evidence | Does not cover every task obligation such as required reads, source dispositions and output contract |
| Evidence State Manager | Stores Evidence facts | Does not decide whether every task obligation is satisfied |
| Context Manager | Persists Task/Progress/Working Set state | Does not supervise whether the Agent followed the task contract |
| Knowledge Manager | Routes and persists classified Knowledge candidates | Cannot trigger classification without a valid observed Turn and Reflection |
| Obligation/Gate Closure module | Reconciles existing obligations at Closure | Does not provide live event-driven obligation tracking during external execution |
| Framework Efficiency Observer | Measures framework efficiency and must remain optional/fail-open | Must not become a mandatory execution control plane |

The new Supervisor fills the missing execution connection; it does not replace these modules.

---

# 2. Why this capability is mandatory

## 2.1 Without it, Harness is only a routing and prompt system

If the Framework can only generate a good Context but cannot supervise the resulting work, it cannot reliably distinguish:

```text
Agent followed the routed rules
vs.
Agent ignored them and independently guessed a plausible result
```

It also cannot distinguish:

```text
real validator PASS
vs.
Agent prose claiming PASS
```

A reliable governance framework must govern both:

```text
before execution: what should be done
and
after/during execution: what was actually done and whether it satisfies the contract
```

## 2.2 The Framework must own completion

The Agent cannot be the authority that declares its own task complete.

A task is complete only when the Framework can prove:

```text
all mandatory obligations are satisfied
no unresolved violation remains
required outputs exist and match the contract
required validation has real Evidence
unexecuted checks are not reported as PASS
Reflection completed
Knowledge classification completed
Context Closure completed
all Mandatory Closure modules succeeded
Turn is CLOSED
Task completion policy admits completion
```

## 2.3 The Framework must own automatic learning triggers

Knowledge and Context updates cannot depend on the Agent remembering to call a Manager.

The Framework must automatically require a closing decision for each domain:

```text
NONE | PROJECT | PUBLIC | BOTH
```

The Agent provides semantic judgment. The Framework ensures the judgment happens, validates its structure and provenance, and invokes the deterministic Managers.

## 2.4 The capability belongs to the public framework

Every real project and every Host has the same generic lifecycle problem:

```text
receive task
→ execute work
→ prove actions/results
→ evaluate obligations
→ reflect
→ persist learning
→ close
```

If each Project Plugin or Host Adapter reimplements this lifecycle, ET Harness loses portability and becomes a set of project/Host forks.

Therefore:

```text
Execution supervision semantics = Public Harness
Project-specific obligations      = Project Plugin
Host-specific event translation   = Host Adapter
Tool-specific execution           = Tool Plugin / Tool Gateway
Semantic judgment                 = Agent / Semantic Executor
```

---

# 3. Scope and non-goals

## 3.1 The Supervisor must do

```text
bind Agent / Runtime / Project / Task / Turn identity
compile or accept a structured task supervision contract
create and maintain an Obligation Ledger
ingest ordered execution events and receipts
validate event identity, sequence, hash and idempotency
track required resource/source handling
track actual writes and scope compliance
separate Agent claims from trusted Evidence
update obligation states incrementally
detect observable violations and missing proof
support cross-process rehydration and replay
produce a deterministic completion decision
trigger the existing Reflection / Knowledge / Context / Closure path
persist a supervision and completion receipt
```

## 3.2 The Supervisor must not do

```text
understand eTimer, MCU, academic papers or any project domain directly
parse hidden chain-of-thought
replace Project Rules or Task Context Compiler
replace the Governance Kernel
replace Evidence / Knowledge / Context / Gate Managers
call a model on every event
create a second A/R/K/G resource system
turn every tool event into permanent Knowledge
silently convert Agent claims into PASS Evidence
claim mechanical Tool enforcement when the Host only supports semantic audit
```

## 3.3 Observable guarantee boundary

No framework can prove that a model internally “understood” a document.

The Supervisor can prove observable facts such as:

```text
the required resource was accessed at a specified identity/revision/hash
the access produced FOUND / NO_MATCH / UNAVAILABLE disposition
the final claim references the relevant source receipt
the output satisfies structural and rule validation
the claimed PASS has a trusted executor receipt
```

This is the correct governance boundary: observable behavior, durable receipts, evidence-backed claims and deterministic completion.

---

# 4. Architecture position

```text
┌──────────────────────────────────────────────────────────────┐
│ Agent / Semantic Executor                                   │
│ Current ChatGPT | GPT | DeepSeek | Claude | Codex          │
└────────────────────────────┬─────────────────────────────────┘
                             │ work output / reflection
┌────────────────────────────▼─────────────────────────────────┐
│ Host Adapter / External Chat Bridge                         │
│ translates Host events; owns no governance policy           │
└────────────────────────────┬─────────────────────────────────┘
                             │ ExecutionEventEnvelope
═════════════════════════════▼═══════════════════════════════════
                PUBLIC GOVERNANCE RUNTIME
═════════════════════════════┬═══════════════════════════════════
                             │
┌────────────────────────────▼─────────────────────────────────┐
│ PUBLIC EXECUTION SUPERVISOR                                 │
│ - Task Supervision Contract                                │
│ - Execution Event Store                                   │
│ - Obligation Ledger                                       │
│ - Evidence/Claim Evaluator                                │
│ - Violation Evaluator                                     │
│ - Completion Evaluator                                    │
│ - Replay / Rehydration                                    │
└──────────────┬──────────────────┬────────────────────────────┘
               │                  │
               │ state/evidence   │ completion-ready
               ▼                  ▼
┌─────────────────────────┐  ┌─────────────────────────────────┐
│ Existing Public Managers│  │ Governance Kernel              │
│ Context / Evidence      │  │ Unified Reflection             │
│ Rule / Knowledge / Gate │  │ 8/8 Closure / Receipt          │
└─────────────────────────┘  └─────────────────────────────────┘
               ▲
               │ structured obligations / evidence policies
┌──────────────┴──────────────────────────────────────────────┐
│ Project Plugin / Project Context Contributor               │
│ domain rules, source map, scope, validation, output contract│
└─────────────────────────────────────────────────────────────┘
```

## 4.1 Mandatory but modular

The Supervisor should be implemented as a dedicated public plugin/service for clear contracts, persistence and tests:

```text
agent_harness/public_plugins/execution_supervisor/
```

In governance mode it is mandatory and injected by Governance Runtime.

It remains modular in code ownership, but Runtime must fail closed if the Supervisor required by the selected governance profile is unavailable.

## 4.2 Not a new fifth project resource

The Obligation Ledger is runtime state, not a new project resource category.

Projects continue to own only:

```text
Architecture
Rules
Knowledge
Gates
Project Context / optional adapters
```

Structured obligations are compiled from these existing project-owned sources and contributed at runtime. Do not add an `obligations/` resource tree parallel to A/R/K/G.

---

# 5. Ownership boundaries

## 5.1 Project Plugin / Context Contributor

The Project Plugin knows the domain and supplies structured task requirements:

```text
required resources and source dispositions
allowed and protected write scope
required outputs
validation commands/providers
claim-to-evidence policy
rule-compliance checks
completion requirements
Knowledge taxonomies and project sources
```

For ATP, the existing Task Context Compiler already produces much of this data:

```text
must_read
rule_owners
write_scope
validation
chip / ip / module / change
```

The ATP Context Contributor also produces source-disposition and output contracts. The next contract version must expose the necessary obligations structurally rather than requiring the public Supervisor to parse project prose.

## 5.2 Host Adapter / External Chat Bridge

The Host Adapter only translates real Host events into the public event contract:

```text
Host tool call/result
Host resource read/write
Host user-visible assistant output
Host validation result
Host final response manifest
```

It must not decide:

```text
which Rule applies
which obligation is satisfied
whether Knowledge is PROJECT/PUBLIC
whether a claim is PASS
whether Closure may complete
```

## 5.3 Execution Supervisor

The Supervisor is deterministic. It owns:

```text
event identity and order
receipt normalization
obligation state transition
scope and evidence checks
observable violation detection
completion readiness
```

It does not perform project semantic analysis.

## 5.4 Agent / Semantic Executor

The Agent owns semantic work:

```text
analysis
interpretation
conflict explanation
user-visible output
Unified Reflection classifications and proposals
```

It cannot self-certify completion, Evidence or Closure.

## 5.5 Trusted Evidence providers

Validators, CI, Tool Gateway, hardware adapters and other trusted executors produce Evidence receipts. Only evidence sources allowed by the Project/Gate policy may satisfy a PASS obligation.

---

# 6. Core contracts

The following contracts are conceptual v0.1 requirements. Exact TypeScript names may change, but their semantics must not be weakened.

## 6.1 Task Supervision Contract

```ts
interface TaskSupervisionContractV01 {
  schema: 'agent-harness.task-supervision.v0.1'
  projectId: string
  taskId: string
  agentId: string
  contextHash: string
  routeHash: string
  projectRevision?: string
  supervisionLevel: 'AUDIT' | 'ENFORCE'
  obligations: ObligationDefinitionV01[]
  evidencePolicies: EvidencePolicyV01[]
  completionPolicy: CompletionPolicyV01
}
```

This contract is generated by the Framework after project routing and Context Contribution. The Host must not manually insert project business guidance.

## 6.2 Obligation definition

```ts
interface ObligationDefinitionV01 {
  id: string
  kind:
    | 'REQUIRED_RESOURCE'
    | 'SOURCE_DISPOSITION'
    | 'OUTPUT'
    | 'WRITE_SCOPE'
    | 'VALIDATION'
    | 'CLAIM_EVIDENCE'
    | 'RULE_COMPLIANCE'
    | 'KNOWLEDGE_DECISION'
    | 'CONTEXT_UPDATE'
    | 'REFLECTION'
    | 'CLOSURE'
  severity: 'MUST' | 'SHOULD'
  sourceRefs: string[]
  target: Record<string, unknown>
  satisfaction: Record<string, unknown>
  dependencies?: string[]
}
```

## 6.3 Obligation state

```text
PENDING
SATISFIED
BLOCKED
VIOLATED
NOT_APPLICABLE
WAIVED
```

Rules:

```text
Agent cannot set SATISFIED directly.
Agent cannot waive an obligation.
WAIVED requires an authorized non-Agent decision, reason and receipt.
MUST PENDING/BLOCKED/VIOLATED prevents task completion.
SHOULD may create a warning but must remain visible.
```

## 6.4 Execution event envelope

```ts
interface ExecutionEventEnvelopeV01 {
  schema: 'agent-harness.execution-event.v0.1'
  requestId: string
  runtimeId: string
  projectId: string
  taskId: string
  turnId: string
  agentId: string
  contextHash: string
  sequence: number
  eventId: string
  timestamp: string
  kind: ExecutionEventKind
  payloadHash: string
  payload: Record<string, unknown>
}
```

Minimum event kinds:

```text
RESOURCE_SEARCH
RESOURCE_READ
RESOURCE_WRITE
TOOL_CALL
TOOL_RESULT
SOURCE_DISPOSITION
OUTPUT_EMITTED
VALIDATION_RESULT
ASSISTANT_MESSAGE
USER_MESSAGE
TASK_END_REQUEST
```

The event body contains only visible/durable facts and bounded summaries. Hidden reasoning is forbidden.

## 6.5 Receipts

The public contract must preserve enough information to evaluate obligations without storing unlimited raw content.

### Resource receipt

```text
provider
resource identity/path/item ID
revision or modified time
content hash when read
access status
purpose
claim refs
error when unavailable
```

### Mutation receipt

```text
path/resource
before hash when available
after hash
action
scope decision
executor identity
```

### Validation receipt

```text
validator/provider identity
command or test identity
project revision
context hash
target identity
exit/result status
artifact/evidence refs
timestamp
```

### Output receipt

```text
output contract ID
path/resource identity
content hash
structural validation status
rule validation refs
```

## 6.6 Completion decision

```ts
interface CompletionDecisionV01 {
  status:
    | 'IN_PROGRESS'
    | 'READY_TO_CLOSE'
    | 'BLOCKED'
    | 'FAILED'
    | 'COMPLETE'
  pendingObligationIds: string[]
  violatedObligationIds: string[]
  blockerRefs: string[]
  evidenceRefs: string[]
  closureRef?: string
}
```

`COMPLETE` is impossible before a valid Closure Receipt.

---

# 7. How supervision decisions are made

## 7.1 How to determine whether required resources were handled

The public framework does not decide which eTimer documents are important. The Project Plugin compiles `REQUIRED_RESOURCE` and `SOURCE_DISPOSITION` obligations from project rules and source maps.

The Host reports actual resource events. The Supervisor matches:

```text
obligation target
↔ provider/resource identity
↔ revision/hash
↔ access/disposition receipt
↔ final claim references
```

Examples:

```text
Required SVD read + matching FOUND receipt + hash → resource obligation SATISFIED
Required source unavailable + UNAVAILABLE receipt + reason → disposition SATISFIED, fact obligation may remain BLOCKED
No receipt → NOT_PROVEN / PENDING
Agent prose “I read it” without receipt → PENDING
```

Opening a file proves access, not understanding. Understanding is tested indirectly through output/rule validation and claim/source linkage.

## 7.2 How to detect fabricated PASS or unsupported claims

The Supervisor separates:

```text
Agent Claim
from
Trusted Evidence
```

An Agent message may create a claim candidate but never a trusted PASS.

A PASS claim is accepted only when the matching Evidence Policy is satisfied by an authorized provider and exact identity:

```text
same project/task/turn
same context hash
same project revision/target
allowed validator/executor
valid result status
non-stale Evidence
```

Examples:

```text
Agent says “FPGA test passed” + no FPGA receipt → VIOLATION / unsupported claim
Old log exists + current commit differs → HISTORICAL, not current PASS
Validator command actually ran and produced trusted PASS receipt → validation obligation SATISFIED
Test not executed and output says NOT_EXECUTED → honest state, no fabrication violation
```

## 7.3 How to determine whether the task is complete

The Completion Evaluator performs no domain reasoning. It evaluates the structured contract:

```text
all MUST obligations satisfied
required outputs exist
write scope clean
required source dispositions complete
required validators have acceptable receipts
no forbidden claim/evidence mismatch
no open mandatory Gate blocker
Reflection obligation satisfied
Knowledge decision obligation satisfied
Context update obligation satisfied
Closure obligation satisfied
```

The Agent may request completion through `TASK_END_REQUEST`; the Framework decides whether the request is admitted.

## 7.4 How to decide whether Knowledge should update

The Framework uses deterministic triggers to decide whether semantic classification must be checked:

```text
registered source observed
new durable project fact
contradiction/conflict discovered
tool or validation failure with reusable value
new Evidence
stable workflow lesson
architecture/rule mismatch
```

At Turn close, one Unified Reflection receives bounded observations and available taxonomies. It must explicitly choose:

```text
NONE | PROJECT | PUBLIC | BOTH
```

Candidate persistence requires:

```text
valid active category
provenance/source refs
Evidence refs when claimed
scope consistency
single-line stable fact/proposal
Manager duplicate/conflict checks
```

New candidates remain `CANDIDATE` unless existing validation policy and real Evidence admit promotion. Architecture and Rules remain change candidates, not direct canonical edits.

## 7.5 How Context updates

Context Closure remains mandatory. It updates only the bounded task state:

```text
confirmed facts
decisions
assumptions
open issues
next steps
working set
touched refs
evidence refs
state version
```

Execution events update live supervision state, but full semantic Context consolidation occurs once at Closure through the existing Context Closure module.

---

# 8. Efficiency design

The goal is **strong closure without heavy per-action governance**.

## 8.1 Three execution paths

### Hot path — ordinary reads and tool results

Allowed work:

```text
validate envelope identity/hash/sequence
append one bounded event/receipt
update only affected obligation states
return a small supervision delta
```

Forbidden work:

```text
LLM call
full A/R/K/G reroute
full Context rebuild
full Knowledge search
synchronous report generation
copying raw large tool output
```

### Escalation path — material risk events

Triggered by:

```text
mutation
scope risk
tool error
validation result
claim of PASS
source conflict
stale context/revision
```

Only the affected rules, gates, evidence policies and obligations are reevaluated.

### Close path — one bounded semantic closure

At Turn end:

```text
one Unified Reflection
→ explicit classification
→ deterministic 8/8 Closure
→ one Completion decision
```

Each Manager must not call a separate model.

## 8.2 Event compaction

Use deterministic compaction:

```text
repeated read of same resource/hash → one satisfied resource receipt + access count
repeated search query → bounded aggregate
large tool result → hash + bounded summary + artifact ref
unchanged resource touch → deduplicate
identical replay eventId/payloadHash → idempotent no-op
```

Critical supervision events may not be dropped. Optional efficiency metrics may be dropped because the Efficiency Observer remains fail-open.

## 8.3 Incremental routing and Context

```text
ordinary read → no reroute
new non-conflicting source → obligation delta only
mutation → implementation-phase route refresh
material evidence invalidating route → targeted route refresh
Turn Closure → bounded Context delta
```

No operation should rebuild the entire project knowledge/context graph unless the task identity or project binding changes.

## 8.4 Risk-based supervision without weakening mandatory closure

Different task classes may use different obligation profiles:

```text
analysis/documentation
code change
release/build
hardware execution
```

This changes which obligations exist, not whether supervision exists.

Examples:

```text
pure analysis → source/output/claim/closure obligations
code change    → adds mutation/review/build Gate obligations
hardware task  → adds device/executor/physical Evidence obligations
```

## 8.5 Semantic audit versus mechanical enforcement

The same public contract supports two truthful levels:

### AUDIT

Used when the Host cannot intercept every built-in tool call, such as the current ChatGPT web Host.

```text
events/receipts are ingested after or alongside work
missing proof blocks completion
the Framework can audit compliance
pre-execution blocking of every Host tool is not claimed
```

### ENFORCE

Used when the Host/Tool Gateway owns the tool boundary, such as Codex/Claude Code/self-hosted Agent/MCP proxy.

```text
preflightAction before execution
every tool action passes through the Supervisor/Gateway
unauthorized action can be blocked mechanically
```

`AUDIT PASS` must never be presented as `ENFORCE PASS`.

## 8.6 Efficiency acceptance must be measured

The implementation must add CI benchmarks and use Framework Efficiency Observer for measurement, but the Supervisor must not depend on the Observer.

Before freezing numeric SLOs, Phase 0 must capture baselines. At minimum CI must prove:

```text
no LLM on event hot path
no full reroute for ordinary read events
no more than one Unified Reflection per Turn
bounded event payload and observation text
bounded in-memory indexes
idempotent replay
Context growth remains bounded
Supervisor absent is not allowed in governed mode
Efficiency Observer failure does not block Supervisor
```

Measured p50/p95 latency, event count, Context size and token overhead must be reported before performance thresholds are finalized.

---

# 9. Generality design

## 9.1 Public contracts contain no project business terms

The public plugin must not contain:

```text
ATP
ET6801
eTimer
MCU
specific Rule IDs
specific output paths
specific Drive folders
```

All domain specialization comes through the Project Context/Supervision Contract.

## 9.2 Host adapters contain no governance policy

A ChatGPT, Codex, Claude Code or DSH adapter only maps Host events to the common event API.

A Host adapter may expose capability metadata such as:

```text
supportsPreflight
supportsToolInterception
supportsStableToolEventId
supportsResourceHash
supportsMessageRef
supportsCrossProcessResume
```

The Supervisor uses capability negotiation to select `AUDIT` or `ENFORCE` claims. It does not change project policy.

## 9.3 Existing Project Context Contribution evolves compatibly

Preferred next contract direction:

```ts
ProjectContextContributionV02 {
  ...v0.1 fields
  supervision?: {
    obligations: ObligationDefinitionV01[]
    evidencePolicies: EvidencePolicyV01[]
    completionPolicy: CompletionPolicyV01
  }
}
```

This is an optional contract extension for compatibility, not a new resource type.

For projects without a structured supervision contribution, the Runtime may provide only baseline lifecycle governance. It must not claim full project-task supervision. A Project/Gate that requires full supervision must fail closed until the structured contract is available.

## 9.4 Examples across domains

The same public obligation types support:

```text
software task      → read source, modify scope, run tests, produce patch
research task      → read sources, provenance, output report, uncertainty
document task      → use template, required sections, citation validation
data task          → dataset identity, query/result evidence, report output
hardware task      → device identity, operation receipt, physical evidence
```

Only Project Plugins define the concrete targets and policies.

---

# 10. Reliability, persistence and replay

## 10.1 Persistent Execution State Store

The Supervisor requires a public Host-neutral state store containing:

```text
Task Supervision Contract
Obligation Ledger snapshots/deltas
Execution Event append log
accepted receipt index
violation records
Completion decisions
Runtime/Task/Turn binding
context/route/revision hashes
```

This state cannot remain only in process memory.

## 10.2 Rehydration

A new Runtime process must:

```text
load exact persisted Task/Turn binding
verify Agent/Project/Task/Turn identity
verify Context/Route/Revision hashes
restore event sequence cursor
restore obligation states
restore unresolved violations
replay missing deterministic transitions
resume the original OPEN Turn
```

It must not reroute silently or start a second Turn.

The current `rehydrateTask()` and `rehydrateTurn()` changes should be extracted into the canonical public implementation, tested and extended rather than left as Pilot-only code.

## 10.3 Sequence, hash and idempotency

Rules:

```text
sequence gap → BLOCKED until missing events are supplied or explicitly closed by policy
same eventId + same hash → idempotent replay
same eventId + different hash → integrity violation
wrong task/turn/context/agent → reject
stale project revision where policy requires exact revision → reject or mark stale
```

## 10.4 Failure behavior

```text
optional metric loss      → allowed
critical event store loss → fail closed
Reflection failure        → CLOSURE_PENDING
Closure module failure    → CLOSURE_PENDING/BLOCKED
missing required receipt  → Task BLOCKED/IN_PROGRESS
unsupported Host enforce  → downgrade claim to AUDIT, never pretend ENFORCE
```

---

# 11. Integration with existing modules

## 11.1 Governance Runtime

Runtime remains the only public lifecycle entrypoint.

Proposed high-level flow:

```text
openTurn()
  → build Context
  → compile Task Supervision Contract
  → supervisor.openLedger()

observeWork()/ingestExecutionEvents()
  → supervisor.ingest()
  → Evidence/Context lightweight updates

preflightAction()
  → supervisor + Auto Governance action guard

requestCloseTurn()
  → supervisor.evaluateCompletionReadiness()
  → if ready, closeTurn()

closeTurn()
  → Unified Reflection
  → 8/8 Closure
  → supervisor.attachClosureReceipt()
  → completeTask() only when admitted
```

## 11.2 Auto Governance Engine

Keep ownership of:

```text
project resolve
A/R/K/G routing
context contribution
mutation-triggered route/gate refresh
```

It should expose route/context identity to the Supervisor and consume only deterministic supervision signals; it should not absorb the whole Supervisor implementation.

## 11.3 Governance Kernel

Kernel remains owner of:

```text
Turn Journal
Unified Reflection
Mandatory Closure sequencing
Closure Receipt
```

The Supervisor supplies the complete bounded observation/event/evidence state required to close accurately.

## 11.4 Evidence State Manager

Receives normalized Evidence facts. The Supervisor decides whether a specific obligation accepts that Evidence under the declared policy; the Evidence Manager remains the evidence store, not the completion authority.

## 11.5 Knowledge Manager and Closure

The Supervisor only triggers/checks the required classification path. Knowledge Manager and Knowledge Closure keep ownership of category validation, deduplication, provenance and candidate persistence.

## 11.6 Context Manager

Supervisor events may produce small progress/violation deltas. Final semantic consolidation remains in mandatory Context Closure.

## 11.7 Efficiency Observer

Observer measures Supervisor overhead and bottlenecks but remains optional/fail-open. Supervisor is mandatory/fail-closed for governed completion. The two modules must not be merged.

---

# 12. Proposed code layout

```text
agent_harness/public_plugins/execution_supervisor/
  package.json
  cordis.patch.yml
  src/
    contracts.ts
    event-store.ts
    receipt-normalizer.ts
    obligation-ledger.ts
    evidence-policy-evaluator.ts
    violation-evaluator.ts
    completion-evaluator.ts
    rehydration.ts
    service.ts
    index.ts
  tests/
    contracts.test.ts
    event-ordering.test.ts
    obligation-ledger.test.ts
    evidence-policy.test.ts
    scope-violation.test.ts
    completion.test.ts
    replay.test.ts
    performance-fast-path.test.ts
```

Related public Runtime additions:

```text
GovernanceRuntime.ingestExecutionEvents()
GovernanceRuntime.getSupervisionStatus()
GovernanceRuntime.requestTaskCompletion()
GovernanceRuntime.rehydrateSupervisedTurn()
```

Names may be refined, but responsibility boundaries must remain.

---

# 13. Implementation plan

## Phase 0 — Freeze contracts and baselines

Deliver:

```text
Execution Event contract
Task Supervision Contract
Obligation types/states
Evidence policies
Completion decision contract
Host capability contract
current performance baseline
```

Acceptance:

```text
no ATP/eTimer terms in public contracts
schema validation and negative tests
existing public packages unchanged
```

## Phase 1 — Persistent event store and replay

Deliver:

```text
append-only bounded event store
sequence/hash/idempotency checks
Runtime/Task/Turn binding persistence
cross-process replay cursor
```

Acceptance:

```text
process A opens Turn
process B ingests events
process C rehydrates and sees identical ledger
out-of-order/tampered events fail closed
```

## Phase 2 — Obligation Ledger

Deliver:

```text
structured obligation contribution
ledger creation
state transitions
dependency handling
violation records
status query
```

Acceptance:

```text
missing required read remains PENDING
valid read receipt satisfies it
out-of-scope write becomes VIOLATED
Agent cannot directly mark obligation satisfied
```

## Phase 3 — External Agent Response/Event Bridge

Deliver:

```text
request manifest
response manifest
execution event bundle
ingestion runner
current ChatGPT data-only bridge
```

Acceptance:

```text
exact request/agent/context identity preserved
actual user-visible response recorded
source/tool receipts replayed
no alternate model substitution
```

## Phase 4 — Claim, Evidence and Completion evaluator

Deliver:

```text
claim/evidence separation
trusted provider policy
stale evidence checks
output/scope/validation obligations
completion readiness
```

Acceptance:

```text
fabricated PASS is rejected
NOT_EXECUTED is accepted as honest state but does not satisfy PASS obligation
all MUST obligations required for READY_TO_CLOSE
```

## Phase 5 — Reflection, Knowledge, Context and Closure integration

Deliver:

```text
one Unified Reflection per Turn
mandatory explicit classification
Context Closure
Knowledge/Experience/Architecture/Rule/Evidence/Working Set/Obligation closure
Closure Receipt binding to supervision state
```

Acceptance:

```text
all mandatory modules invoked
NO_CHANGE is valid
missing category blocks Knowledge write
Reflection failure leaves CLOSURE_PENDING
Task cannot complete before Closure COMPLETE
```

## Phase 6 — Host/Tool enforcement profiles

Deliver:

```text
AUDIT adapter profile
ENFORCE Tool Gateway profile
capability negotiation
truthful claim boundary
```

Acceptance:

```text
same public contract works with multiple Hosts
AUDIT never claims mechanical interception
ENFORCE blocks unauthorized preflight action
```

## Phase 7 — Efficiency hardening

Deliver:

```text
event compaction
incremental evaluation
bounded state/context
benchmark CI
Efficiency Observer reports
```

Acceptance:

```text
no semantic call on hot path
one Reflection per Turn
ordinary reads do not reroute
no unbounded event/context growth
measured overhead does not regress beyond frozen SLO
```

## Phase 8 — Real ATP Pilot rerun

Only after public synthetic and cross-process tests pass:

```text
main public Supervisor
  ↓ merge
project/automated-testing-platform
  ↓ clean Pilot branch
current ChatGPT frozen eTimer task
```

Do not continue developing public Runtime logic directly on a contaminated Pilot branch.

---

# 14. Test strategy

## 14.1 Unit and contract tests

Mandatory cases:

```text
valid/invalid schema
identity mismatch
context hash mismatch
duplicate event
tampered duplicate
sequence gap
unknown event kind
payload budget/truncation
obligation dependency transition
unauthorized waiver
stale evidence
unsupported PASS provider
```

## 14.2 Deterministic synthetic end-to-end tests

### Same-process

```text
open → events → obligations → reflection → 8/8 closure → complete
```

### Cross-process

```text
process A open
→ persist state
→ process B rehydrate and ingest
→ crash
→ process C replay and close
```

### Failure/recovery

```text
Reflection failure
Closure module failure
missing event
missing required receipt
partial event replay
```

All must prove idempotency and no duplicate writes.

## 14.3 Negative governance tests

```text
Agent ignores required source
Agent cites source without read receipt
Agent writes outside scope
Agent claims test PASS without Evidence
Agent uses wrong/stale context
Host submits wrong Agent identity
Host manually changes route/output contract
Knowledge candidate lacks category
Agent tries to self-close task
```

Expected result is a specific BLOCK/VIOLATION receipt, not a generic test failure.

## 14.4 Generality matrix

At least four synthetic Project Plugins:

```text
software code change
document/research analysis
data/report task
hardware operation task
```

At least three Host profiles:

```text
generic in-process Host
external data-only/AUDIT Host
Tool-Gateway/ENFORCE Host
```

The public Supervisor package must contain no test-project special cases.

## 14.5 Efficiency tests

Measure and persist:

```text
event ingest p50/p95
ledger transition p50/p95
number of reroutes
number of semantic calls
Context bytes/state versions
execution event bytes
Reflection input/output bytes
replay duration
```

Test invariants:

```text
1000 ordinary read events do not cause 1000 reroutes
repeated identical receipts compact deterministically
one Turn causes at most one normal Reflection call
Observer disabled/enabled does not change supervision result
```

## 14.6 ATP current ChatGPT real-project acceptance

The final real run must preserve the frozen task and prove each layer separately.

### Routing evidence

```text
raw task
Agent ID
Project ID/root
Task Context hash
A/R/K/G IDs
write/read scope
output/validation contract
Task Supervision Contract hash
```

### Execution evidence

```text
External Chat request/response identity
resource/source events
GitHub/Drive dispositions
actual output mutations
validation events
Agent-visible final output
```

### Supervision evidence

```text
complete Obligation Ledger
violations/warnings
claim/evidence decisions
completion decisions
```

### Closure evidence

```text
Unified Reflection
explicit Knowledge classification
all Mandatory Module Receipts
Context state change
Knowledge Candidate or explicit NONE
Closure COMPLETE
Task COMPLETED
```

### Follow-up reuse evidence

Open a second Turn and prove that the resulting Context/Knowledge is routed or available according to policy. The first Turn alone cannot prove learning reuse.

---

# 15. Exact ATP Pilot scenarios after implementation

## Scenario A — Correct governed analysis

Expected:

```text
required source obligations satisfied/dispositioned
two output obligations satisfied
no protected/out-of-scope mutation
unexecuted hardware remains NOT_EXECUTED
Reflection and classification complete
Closure COMPLETE
```

## Scenario B — Missing critical source

Deliberately omit one required source receipt.

Expected:

```text
resource obligation PENDING/BLOCKED
Task cannot close
Framework identifies exact obligation
```

## Scenario C — Fabricated validation PASS

Return prose claiming PASS without trusted validator Evidence.

Expected:

```text
claim/evidence violation
validation obligation unsatisfied
Task blocked
```

## Scenario D — Out-of-scope write

Attempt to modify a protected/non-authorized path.

Expected:

```text
AUDIT Host: violation detected and task blocked
ENFORCE Host: action blocked before execution
```

## Scenario E — No new durable Knowledge

Expected:

```text
Knowledge classification = NONE
Knowledge Closure = NO_CHANGE
Turn may still close
```

## Scenario F — Project Knowledge candidate

Expected:

```text
valid PROJECT category required
candidate written once
replay produces no duplicate
next Turn can retrieve/reuse according to trust policy
```

## Scenario G — Cross-process crash/recovery

Expected:

```text
same Task/Turn identity restored
same event cursor/ledger restored
no second Turn created
Closure completes exactly once
```

---

# 16. What must not be called PASS

The following are partial results only:

```text
Route/Context workflow is green
Task Context compiler ran
Agent produced a plausible document
Agent says it followed the rules
CI job exited 0 without Closure Receipt
Knowledge Manager package tests pass
rehydrateTask()/rehydrateTurn() compile
one output file exists
```

Overall governed-task PASS requires:

```text
Execution events ingested
+ obligations evaluated
+ claims/evidence checked
+ Reflection completed
+ Knowledge/Context decisions persisted
+ Mandatory Closure COMPLETE
+ Task completion admitted
+ evidence bound to exact run/commit/request/response
```

---

# 17. Immediate next actions

1. Treat this document as the next implementation baseline.
2. Stop using eTimer document quality as the current primary success metric.
3. Create a clean public feature branch from `main` for generic Supervisor contracts and synthetic tests.
4. Extract the generic rehydration work from the Pilot into that public branch; do not merge the Pilot wholesale into `main`.
5. Implement persistent execution events and Obligation Ledger before adding more mailbox workflows.
6. Add cross-process and negative tests before the next real Agent run.
7. Merge the validated public capability to `main`.
8. Merge `main` into `project/automated-testing-platform`.
9. Extend the ATP Context Contributor with structured supervision obligations.
10. Create a clean current-ChatGPT Pilot and rerun the frozen eTimer task end to end.
11. Only after the full flow closes, review the detailed quality of the two eTimer documents.

---

# 18. Acceptance checklist for implementation completion

```text
[ ] Public contracts contain no ATP/eTimer special case
[ ] Project Context Contributor can supply structured obligations
[ ] Host-neutral event/receipt contract implemented
[ ] Critical events are durably persisted
[ ] Cross-process Task/Turn/Ledger rehydration works
[ ] Event ordering/hash/idempotency enforced
[ ] Required reads/source dispositions are evaluated
[ ] Write-scope violations are evaluated
[ ] Agent claims cannot create trusted PASS
[ ] Completion Evaluator owns task-complete decision
[ ] Unified Reflection automatically triggers once per Turn
[ ] NONE/PROJECT/PUBLIC/BOTH classification is mandatory
[ ] Context Closure automatically updates task state
[ ] Knowledge candidates require category/provenance
[ ] All Mandatory Closure modules produce receipts
[ ] Reflection/Closure failures remain replayable
[ ] Follow-up Turn proves Context/Knowledge reuse
[ ] AUDIT vs ENFORCE claims remain separated
[ ] Hot path has no LLM/full reroute/full Context rebuild
[ ] Efficiency benchmark and regression gates are in CI
[ ] ATP frozen real task passes with exact evidence
```

---

# 19. Final architectural conclusion

The current problem was caused by an incomplete execution-topology design: ET Harness had strong pre-execution routing and post-turn Closure components, but the external Agent execution between them was not yet represented as a durable, Host-neutral, supervised state machine.

The correct repair is not to add another intelligent Agent or another independent governance system.

The correct repair is:

```text
Public Execution Supervisor
= deterministic event ingestion
+ Obligation Ledger
+ evidence/claim/completion evaluation
+ cross-process replay
+ mandatory bridge into existing Reflection/Knowledge/Context/Closure
```

Implemented with the boundaries in this document, it provides the missing reliability while preserving efficiency and generality:

```text
Project Plugin supplies domain truth.
Host Adapter supplies observable events.
Agent supplies semantic judgment.
Execution Supervisor evaluates obligations.
Kernel and Managers close and persist the governed Turn.
```
