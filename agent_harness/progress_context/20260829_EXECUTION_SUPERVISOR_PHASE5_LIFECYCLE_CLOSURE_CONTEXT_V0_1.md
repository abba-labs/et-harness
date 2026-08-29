# Execution Supervisor Phase 5 Lifecycle Closure Context v0.1

> Status: **FROZEN IMPLEMENTATION CONTEXT / NO SOURCE IMPLEMENTATION YET**
> Date: 2026-08-29
> Branch: `feat/execution-supervisor-phase5-lifecycle-closure-v0.1`
> Starting HEAD: `b69f47bd399fd672ecd23e19a69a9611905df9e5`
> Phase 3+4 source: `feat/execution-supervisor-phase3-4-trusted-evaluation-v0.1`

## 1. Authority and explicit conversation decision

This context compiles the Phase 5 boundary from:

```text
root AGENTS.md
Codex Local Development And Validation Charter v0.1
Execution Supervisor Phase 3+4 Completion Handoff v0.1
Execution Supervisor And Obligation Ledger Design 25 v0.1
Public Governance Runtime And External Boundaries Design 21 v0.1
Public Agent Governance Kernel Design 21 v0.1
current source and tests at b69f47bd399fd672ecd23e19a69a9611905df9e5
```

The user explicitly directed Phase 5 to remain visible in the current primary
conversation and to use child Agents beneath that conversation rather than
creating separate Codex tasks. This is an explicit override of the
conversation-container part of `one conversation = one phase`. It does not
weaken the separate clean branch, frozen scope, mechanical evidence or Handoff
requirements. Phase 5 remains the only active implementation phase.

Observer Agents are read-only and may report rule or implementation defects.
They cannot establish PASS. Only exact mechanical commands and persisted
evidence establish an acceptance conclusion.

## 2. Phase objective

Phase 3+4 stops at:

```text
trusted execution events
  -> Obligation Ledger
  -> READY_TO_CLOSE
```

Phase 5 adds only the trusted bridge from that state into the already existing
Runtime and Kernel close path:

```text
exact READY_TO_CLOSE snapshot
  -> one existing Unified Reflection
  -> existing eight Mandatory Closure Modules
  -> existing Kernel Closure Receipt COMPLETE
  -> exact durable supervision/Closure binding
  -> Supervisor COMPLETE
  -> Runtime task completion admission
```

Reflection, Knowledge, Context and Closure are already implemented by the
Kernel and Managers. This phase must connect them; it must not reimplement them.

## 3. Exact deliverables

Deliver only:

```text
content-addressed Supervision Readiness Receipt
exact contract/task/turn/agent/context/event-cursor/decision binding
Framework-only lifecycle Closure attachment API
existing Kernel Closure Receipt binding to the readiness fingerprint
deterministic lifecycle-obligation projection
Runtime close admission before Reflection and Closure
Runtime completeTask gate after Supervisor COMPLETE
same-process and cross-process idempotent recovery
trusted execution observations projected into the existing bounded Turn Journal
```

The governed close policy requires:

```text
requireAllMustSatisfied = true
requireNoViolations = true
requireReflection = true
requireKnowledgeDecision = true
requireContextUpdate = true
requireClosureReceipt = true
all eight existing Mandatory Closure Module IDs
```

Execution-only tests may continue using reduced policies to isolate pre-Closure
evaluation, but Runtime governed completion must fail closed on a reduced close
policy.

## 4. Frozen ownership boundaries

```text
Governance Runtime
  remains the only public lifecycle entrypoint and close/complete admission owner

Execution Supervisor
  owns the exact readiness snapshot, lifecycle-obligation projection and final
  COMPLETE decision; it never performs Reflection or Manager work

Governance Kernel
  remains the only owner of Turn Journal, Unified Reflection, Mandatory Closure
  sequencing, replay and Turn Closure Receipt

Closure Adapters and Managers
  retain Context, Knowledge, Experience, Architecture, Rule, Evidence, Working
  Set and Obligation/Gate deterministic actions

Agent / Semantic Executor
  supplies the structured Reflection semantic decision only; it cannot attach a
  Closure Receipt, satisfy an obligation or complete a task
```

No Supervisor package dependency may be introduced into the Kernel. The Kernel
may accept a generic content-addressed readiness binding as part of its existing
Reflection/Closure input fingerprint.

## 5. Required close ordering

The only valid order is:

```text
ledger.synchronize()
verify exact latest decision is READY_TO_CLOSE
freeze readiness receipt at the exact Event Store cursor/state hash
seal/project bounded trusted observations into the existing Turn Journal
invoke existing Unified Reflection once
invoke existing eight-module Kernel Closure once/replay missing work only
verify Kernel Closure Receipt is COMPLETE and identity/fingerprint match
Framework attaches exact Closure receipt to Supervisor state
Supervisor returns COMPLETE with exact closureRef
Runtime completeTask verifies the same final binding
```

Any new accepted execution event after readiness invalidates that readiness
receipt. A stale Closure binding must be rejected rather than completing the
newer stream.

## 6. Readiness and Closure binding

The readiness receipt must bind at least:

```text
Task Supervision Contract hash
request/runtime/project/task/turn/agent/context identity
event cursor sequence and state hash
Obligation Ledger status hash
READY_TO_CLOSE Completion Decision hash
TASK_END event identity
created-at or deterministic source timestamp
```

The final lifecycle binding must bind at least:

```text
readiness receipt/hash
Kernel journalRef
Kernel reflectionRef and reflection input fingerprint
explicit NONE/PROJECT/PUBLIC/BOTH Knowledge decision
Kernel Closure Receipt ref and input fingerprint
all required module IDs, versions and APPLIED/NO_CHANGE statuses
final Supervisor COMPLETE decision and closureRef
```

This is a content-addressed binding receipt, not a second Turn lifecycle or a
second Closure store. Replaying the same exact receipt is an idempotent no-op.
A different receipt for the same readiness state or a receipt against a changed
cursor fails closed.

## 7. Lifecycle obligation rules

Only Framework-validated lifecycle facts may project:

```text
REFLECTION
KNOWLEDGE_DECISION
CONTEXT_UPDATE
CLOSURE
```

Agent prose, `TurnReflectionResult.obligations.resolved[]`, `TASK_END_REQUEST`, a
plain closure URI or a caller-supplied `COMPLETE` value never satisfies these
obligations.

Lifecycle satisfaction requires the exact Kernel Reflection and Closure
receipts. Missing classification blocks Knowledge persistence. `NO_CHANGE` is a
successful module outcome. `BLOCKED` or `FAILED` keeps the Turn
`CLOSURE_PENDING` and keeps Supervisor completion non-COMPLETE.

## 8. Existing lifecycle reuse

Phase 5 must reuse:

```text
GovernanceRuntimeService.closeTurn()/completeTask()
AgentGovernanceKernelService.reflectTurn()/closeTurn()
TurnReflectionController and TurnReflectionStore
ClosureCoordinator and TurnClosureStore
the existing eight Mandatory Closure Adapters
Knowledge category validation in existing Reflection/Closure code
Context and Working Set closure adapters
Phase 1 Event Store and Phase 2 Ledger projection
Phase 3+4 trusted admission and claim/evidence evaluator
```

The existing Kernel module idempotency key remains authoritative. The readiness
binding must become part of the existing Reflection/Closure input fingerprint so
replay cannot close against different supervision state.

## 9. Allowed implementation surface

Expected bounded files:

```text
agent_harness/public_plugins/execution_supervisor/src/contracts.ts
agent_harness/public_plugins/execution_supervisor/src/lifecycle-closure.ts (new)
agent_harness/public_plugins/execution_supervisor/src/obligation-ledger.ts
agent_harness/public_plugins/execution_supervisor/src/validation.ts
agent_harness/public_plugins/execution_supervisor/src/index.ts
agent_harness/public_plugins/execution_supervisor/tests/lifecycle-closure.test.ts (new)

agent_harness/public_plugins/agent_governance_kernel/src/contracts.ts
agent_harness/public_plugins/agent_governance_kernel/src/reflection.ts
agent_harness/public_plugins/agent_governance_kernel/src/turn-reflection-controller.ts
agent_harness/public_plugins/agent_governance_kernel/src/turn-reflection-store.ts
agent_harness/public_plugins/agent_governance_kernel/src/closure-coordinator.ts
agent_harness/public_plugins/agent_governance_kernel/src/turn-closure-store.ts
agent_harness/public_plugins/agent_governance_kernel/tests/* focused lifecycle tests

agent_harness/public_plugins/governance_runtime/package.json
agent_harness/public_plugins/governance_runtime/src/contracts.ts
agent_harness/public_plugins/governance_runtime/src/service.ts
agent_harness/public_plugins/governance_runtime/src/turn-observation-store.ts
agent_harness/public_plugins/governance_runtime/tests/supervised-lifecycle.test.ts (new)

agent_harness/public_plugins/agent_governance_closure_adapters/src/remaining-modules.ts
agent_harness/public_plugins/agent_governance_closure_adapters/tests/* focused reconcile test
```

Not every listed file must change. Modify only files mechanically required by
the final design. Any other source package or public contract expansion requires
this context to be updated and re-frozen first.

## 10. Explicit non-goals

Do not implement:

```text
a second Runtime, Turn lifecycle, Reflection engine or Closure Coordinator
a second Event Store, Context Store, Knowledge Store or receipt authority
new Manager implementations or rewrites of the eight Closure Adapters
Phase 6 AUDIT/ENFORCE Host profiles, Tool interception or capability negotiation
Host SDKs, network/model calls, mailbox orchestration or provider attestation
cryptographic Host/model/provider authentication
ATP, ET6801, eTimer, MCU or other project business logic
Phase 7 compaction, numeric SLO changes or Efficiency Observer coupling
Phase 8 ATP Pilot execution or hardware validation
automatic canonical Knowledge/Rule/Architecture promotion
```

## 11. Recovery and persistence

Same-process retry and cross-process recovery must prove:

```text
same Task/Turn and Event Store binding are restored
same readiness hash is reconstructed from the durable stream
existing Reflection is reused for the same sealed input
successful Closure Module receipts are not repeated
one unique COMPLETE Kernel Closure Receipt remains authoritative
one unique Supervisor lifecycle binding remains authoritative
no duplicate Context, Knowledge or candidate write is produced
newer event cursor rejects an older readiness/Closure binding
```

Runtime in-memory session state or observation text is not completion evidence.
Recovery must derive trusted observations from the accepted durable event stream
and existing Kernel stores. It must not re-interpret Agent prose or silently
reroute to a different Context/route hash.

## 12. Mandatory focused acceptance

At minimum mechanically prove:

```text
READY_TO_CLOSE without Kernel Closure cannot become COMPLETE
Agent cannot call or forge lifecycle attachment
one Unified Reflection is invoked for one Turn
all eight mandatory modules are invoked
all APPLIED/NO_CHANGE admits COMPLETE
Knowledge NONE is valid and Knowledge Closure is NO_CHANGE
missing/invalid category blocks Knowledge write and keeps CLOSURE_PENDING
Reflection failure keeps CLOSURE_PENDING
one module failure keeps CLOSURE_PENDING and retry does not duplicate prior writes
Closure Receipt for a stale event cursor is rejected
closure/task/turn/context identity mismatch is rejected
Runtime completeTask is blocked before Supervisor COMPLETE
Runtime completeTask is admitted only for the exact bound closureRef
cross-process reopen reuses Reflection/Closure and does not duplicate side effects
ordinary execution events do not trigger Reflection, full Context rebuild or reroute
```

Tests assert typed states, hashes, refs and durable records. Observer narrative is
never substituted for a mechanical assertion.

## 13. D-drive environment and efficiency gates

All commands use this worktree explicitly:

```text
D:\lihuan\vibe_code\codex\et_harness_env\workspaces\phase5_lifecycle_closure
```

All runtime state and development artifacts must remain below:

```text
D:\lihuan\vibe_code\codex\et_harness_env
```

Every test invocation must explicitly set at least:

```text
HOME
TMPDIR/TEMP/TMP
npm cache
AGENT_HARNESS_STATE_ROOT
test logs and generated state roots
```

to D-drive paths. Node `v22.23.2` and npm `10.9.8` are reused from the existing
D-drive runtime. Dependency trees are materialized only when required and must
reuse the existing D-drive npm cache; there is no repeated install between edit
iterations.

Validation ladder:

```text
edit loop       only the directly affected Phase 5 focused test file(s)
checkpoint      execution_supervisor + kernel + runtime affected package tests
logic complete  affected package builds and directly related integrations
phase close     21 public packages plus 7 integrations exactly once
always          public boundary scan, git diff --check and clean/status audit
```

No more than two large executions may run concurrently. Long execution writes a
D-drive log and uses long, low-frequency polling. Integration reuses built `dist`
and must not repeat package builds.

## 14. Known starting risks

```text
current Runtime completeTask has no Supervisor gate
current Ledger cannot attach a trusted Closure Receipt or return COMPLETE
current Kernel Closure fingerprint does not expose supervision readiness
Runtime sessions and Turn observations are in-memory
EventStore close is not a persistent cross-process seal
governed close policy can currently be configured below the mandatory Phase 5 set
obligation-gate reconcile currently sees Agent Reflection obligation text
default Kernel/Manager state paths can fall back to the user home directory
```

Each reproduced risk must be fixed or explicitly preserved as a non-PASS blocker.
The implementation may not hide it through a weaker assertion or a broader
allowlist.

## 15. Step exit condition

Implementation may begin only after this context is committed with a clean
tracked worktree. Phase 5 completes only after the final Handoff records exact
commits, mechanical evidence, failures, remaining limitations and the next
authorized phase. Phase 6 and later remain forbidden in this branch.
