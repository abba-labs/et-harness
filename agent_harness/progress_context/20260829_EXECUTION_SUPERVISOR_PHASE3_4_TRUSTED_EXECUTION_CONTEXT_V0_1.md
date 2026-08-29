# Execution Supervisor Phase 3+4 Trusted Execution Context v0.1

> Status: **FROZEN MERGED IMPLEMENTATION CONTEXT / NO SOURCE IMPLEMENTATION YET**
> Date: 2026-08-29
> Branch: `feat/execution-supervisor-phase3-4-trusted-evaluation-v0.1`
> Starting HEAD: `04f3e9ab767fb063d6f160b5c6b5a108a4d5afb5`
> Phase 2 source: `feat/execution-supervisor-phase2-obligation-ledger-v0.1`

## 1. Authority and merge decision

This context compiles the merged Phase 3 and Phase 4 implementation boundary
from:

```text
root AGENTS.md
Codex Local Development And Validation Charter v0.1
Execution Supervisor Phase 2 Completion Handoff v0.1
Execution Supervisor And Obligation Ledger Design 25 v0.1
Public Governance Runtime And External Boundaries Design 21 v0.1
current Phase 2 source and tests at 04f3e9ab767fb063d6f160b5c6b5a108a4d5afb5
```

The user explicitly approved merging Design 25 Phase 3 and Phase 4 to reduce
repeated environment setup and repository-wide close gates. This is one bounded
macro phase with one responsibility:

```text
trusted external execution facts
  -> durable canonical events
  -> deterministic claim/evidence evaluation
  -> pre-Closure completion readiness
```

The merge changes execution grouping only. It does not weaken either phase's
contracts, negative tests, persisted evidence, ownership boundaries or acceptance
semantics. Bridge and evaluator remain separate internal checkpoints and commits.

Observer Agents may inspect scope and behavior, but only mechanical commands and
persisted artifacts establish PASS.

## 2. Exact deliverables

Deliver only:

```text
strict external Agent request manifest
strict external Agent response manifest
bounded execution event bundle
data-only ingestion runner with whole-bundle prevalidation
actual user-visible request/response persistence
exact expected/actual provider, model, Agent and Context binding
structured Agent claim records; no prose parsing
kind-specific source-disposition, output, validation, rule and claim evaluation
trusted Evidence Policy matching
deterministic stale/future evidence evaluation
unsupported-PASS violation records
pre-Closure completion readiness
cross-instance replay of manifests, receipts, claims, violations and decision
```

Required acceptance:

```text
exact request/runtime/project/task/turn/agent/context identity is preserved
actual bounded user-visible response is durably recorded without trim or summary
source/tool/output/validation receipts replay identically
expected and actual provider/model mismatch is rejected before append
an invalid later bundle event causes no earlier bundle event to append
fabricated PASS is rejected with a typed violation
NOT_EXECUTED is retained as an honest fact but never satisfies required PASS
stale, future, wrong-provider or wrong-identity Evidence does not satisfy
all execution-stage MUST obligations are required for READY_TO_CLOSE
the evaluator never returns COMPLETE or a Closure Receipt
```

## 3. Explicit non-goals

Do not implement:

```text
Phase 5 Reflection, Knowledge, Context or Closure integration
Closure Receipt creation or validation beyond the existing structural contract
task COMPLETE admission
Governance Runtime lifecycle entrypoints
Kernel, Auto Governance Engine or Manager changes
Phase 6 Tool Gateway preflight enforcement or Host SDK interception
cryptographic Host/model/provider authentication
network/model calls or mailbox orchestration
project-specific obligation compilation or prose parsing
ATP, ET6801, eTimer, MCU or any project business logic
Phase 7 event compaction or numeric SLO freezing
a second Event Store, Evidence Store, lifecycle, Registry, Workflow or DI layer
```

## 4. Frozen ownership boundaries

```text
Host Adapter / data-only Bridge
  translates and binds externally visible Host facts
  never decides obligation state, Evidence acceptance, PASS or completion

Phase 1 Execution Event Store
  remains the only durable event identity/order/hash/idempotency/replay authority

Phase 2 Obligation Ledger
  remains the only deterministic obligation projection and status authority

Phase 4 Evidence evaluator
  matches accepted durable receipts against the contributed Evidence Policy
  never trusts Agent prose or receipt provider strings without Bridge ingress

Pre-Closure Completion evaluator
  decides IN_PROGRESS/BLOCKED/FAILED/READY_TO_CLOSE only

Governance Runtime / Kernel / Managers
  remain untouched; Phase 5 owns lifecycle integration and COMPLETE
```

The following packages are read-only in this macro phase:

```text
governance_runtime
agent_governance_kernel
auto_governance_engine
evidence_state_manager
all model_adapters
all project plugins and pilots
```

## 5. External data-only Bridge contract

The Bridge is implemented inside the existing public `execution_supervisor`
package. It performs no network or model call.

The request manifest must bind at least:

```text
schema
request/runtime/project/task/turn/agent/context identity
exact Task Supervision Contract hash
expected Host/provider/model identity
bounded user-visible request message ID, content and content hash
issued timestamp
```

The response manifest must bind at least:

```text
schema
exact request manifest hash and execution identity
response ID
actual Host/provider/model/Agent identity
bounded user-visible assistant message ID, content and content hash
structured Agent claims
referenced receipt event IDs and payload hashes
completed timestamp
```

The bundle must bind:

```text
schema and bundle ID
request and response manifest hashes
one ordered bounded array of original ExecutionEventEnvelopeV01 values
one USER_MESSAGE event containing the exact request manifest
one ASSISTANT_MESSAGE event containing the exact response manifest
all response-declared receipt event references
```

The manifests are persisted inside the canonical USER_MESSAGE and
ASSISTANT_MESSAGE event payloads. There is no second manifest store. Replay of the
Phase 1 stream therefore preserves the exact request/response relationship.

Whole-bundle prevalidation occurs before the first append:

```text
strict schema and unknown-field rejection
canonical hash and byte-budget checks
exact ledger binding and contract hash
exact expected/actual provider, model and Agent identity
internally contiguous ordered event sequence
exact USER_MESSAGE/ASSISTANT_MESSAGE manifest references
complete receipt event ID/payload-hash references
no hidden reasoning field or unbounded raw tool output
```

After prevalidation, the runner calls only `ExecutionObligationLedgerV01.ingest()`
in event order. It returns the existing `ExecutionEventAcceptanceV01` values and
does not invent a second acceptance vocabulary. A runtime append failure may leave
an accepted prefix; the runner must report the failure and exact accepted prefix,
and a retry relies on Phase 1 event idempotency. It must never report the entire
bundle accepted when only a prefix is durable.

The Bridge proves manifest and event identity consistency at a trusted Runtime
ingress. It does not cryptographically prove that an external Host actually ran a
named model/provider. Final claims must preserve this limitation until Phase 6.

## 6. Structured claim and receipt boundary

Free-form assistant text is never parsed for governance state. Only a structured,
bounded claim in the accepted response manifest is a claim candidate.

A claim binds at least:

```text
claim ID
claim kind
target identity
result status
validation/output identity when applicable
declared evidence refs
```

An Agent claim is never trusted Evidence. A structured PASS claim is supported
only when matching accepted Evidence already exists in the durable event order.
A later receipt does not erase an earlier unsupported-PASS violation.

Validation and output receipts must carry enough structured identity for policy
matching:

```text
provider ID and provider kind
validation/output/target identity
context hash
project revision when applicable
result/structural status
artifact/evidence/claim refs
receipt timestamp
```

The Bridge validates receipt payload structure and trusted ingress provider IDs.
The Supervisor evaluator still independently applies Project-contributed Evidence
Policies. The Bridge never decides that a receipt satisfies an obligation.

## 7. Frozen Phase 4 obligation structures

This macro phase adds strict structures only for these existing obligation kinds:

```text
SOURCE_DISPOSITION
OUTPUT
VALIDATION
CLAIM_EVIDENCE
RULE_COMPLIANCE
```

`REQUIRED_RESOURCE` and `WRITE_SCOPE` retain the accepted Phase 2 structures.
Reflection, Knowledge, Context and Closure kinds remain visible and unresolved.

To avoid guessing policy composition, Phase 3+4 v0.1 accepts exactly one Evidence
Policy for every OUTPUT, VALIDATION, CLAIM_EVIDENCE or RULE_COMPLIANCE obligation.
Multiple-policy OR/AND semantics are outside this macro phase and fail contract
validation closed.

SOURCE_DISPOSITION accepts only a matching structured `NO_MATCH` or `UNAVAILABLE`
resource receipt under the contributed provider/disposition policy. It never
satisfies REQUIRED_RESOURCE.

OUTPUT requires the exact output contract/resource identity and content hash.
Output existence alone is not trusted structural or rule PASS; the associated
Evidence Policy and matching trusted receipt must also accept it.

VALIDATION and RULE_COMPLIANCE require a matching Validation Receipt and policy.
CLAIM_EVIDENCE requires every structured PASS claim in its declared target scope
to have matching current Evidence.

## 8. Evidence Policy evaluation

Evidence matching is deterministic and fail-closed:

```text
provider ID matches when the policy declares provider IDs
AND provider kind matches when the policy declares provider kinds
AND accepted result status matches
AND exact Context hash matches when required
AND exact project revision matches when required
AND exact target identity matches when required
AND receipt timestamp is not in the future
AND maxAgeSeconds has not expired
```

If exact project revision is required but the Task contract has no project
revision, contribution validation fails closed.

`PASS` may satisfy a required PASS obligation. `NOT_EXECUTED`, `NOT_VERIFIED` and
`HISTORICAL` remain visible honest evidence states but never satisfy required
PASS. Matching trusted `FAIL` makes the applicable MUST validation obligation
VIOLATED and may produce FAILED at task-end evaluation.

Time evaluation never uses `Date.now()`. At ordinary receipt ingestion, the
accepted event timestamp is the deterministic evaluation point. At
TASK_END_REQUEST, the end-request event timestamp is the deterministic close-path
evaluation point. The bounded close path re-evaluates evidence freshness and may
return a formerly satisfied Evidence-controlled obligation to PENDING, with its
dependents BLOCKED again. Replay must produce the same result.

Ordinary event ingestion remains incremental. Only the task-end close path may
perform one bounded full refresh of Phase 4 Evidence-controlled obligations.

## 9. Violation and completion rules

Add typed deterministic violations for at least:

```text
UNSUPPORTED_PASS_CLAIM
TRUSTED_VALIDATION_FAILED
```

Violation IDs derive from stable claim/event/obligation identity and must not
duplicate during replay or retry.

TASK_END_REQUEST is only a request. It cannot directly set an obligation or task
state. The pre-Closure evaluator returns:

```text
IN_PROGRESS
  no accepted TASK_END_REQUEST has been evaluated

FAILED
  a MUST obligation has current matching trusted FAIL Evidence

BLOCKED
  task end was requested but an execution-stage MUST is pending, blocked or
  violated, including unsupported PASS

READY_TO_CLOSE
  task end was requested, every execution-stage MUST is satisfied, WRITE_SCOPE
  has no violation, and no blocking trusted failure exists
```

Execution-stage obligation kinds are:

```text
REQUIRED_RESOURCE
SOURCE_DISPOSITION
OUTPUT
WRITE_SCOPE
VALIDATION
CLAIM_EVIDENCE
RULE_COMPLIANCE
```

This is an explicit pre-Closure interpretation of Design 25's flow. The remaining
REFLECTION, KNOWLEDGE_DECISION, CONTEXT_UPDATE and CLOSURE obligations are reported
as deferred close-path blockers and remain unresolved until Phase 5. They are not
silently satisfied or waived.

The evaluator in this macro phase must never return `COMPLETE`, set `closureRef`,
invoke Reflection/Managers or call `completeTask()`.

At TASK_END_REQUEST, a non-violated WRITE_SCOPE obligation becomes SATISFIED only
as the deterministic statement that every accepted mutation observed so far was
inside its contributed scope. Any write-scope violation remains terminal.

## 10. Expected source and test ownership

Production changes are limited to:

```text
agent_harness/public_plugins/execution_supervisor/src/contracts.ts
agent_harness/public_plugins/execution_supervisor/src/validation.ts
agent_harness/public_plugins/execution_supervisor/src/external-agent-bridge.ts
agent_harness/public_plugins/execution_supervisor/src/trusted-evaluation.ts
agent_harness/public_plugins/execution_supervisor/src/obligation-ledger.ts
agent_harness/public_plugins/execution_supervisor/src/index.ts
agent_harness/public_plugins/execution_supervisor/README.md
```

The accepted Phase 1 Event Store persistence format and ordering remain frozen.
The ledger may receive the minimum deterministic extension required to project
accepted Phase 3+4 events; it may not become a second lifecycle or Evidence Store.

Focused tests are limited to:

```text
tests/external-agent-bridge.test.ts
tests/evidence-policy.test.ts
tests/completion.test.ts
tests/trusted-execution-replay.test.ts
shared synthetic fixtures only where necessary
```

## 11. Frozen focused test matrix

```text
valid manifests/bundle ingest through Ledger and persist both manifests
wrong request/runtime/project/task/turn/agent/context/contract hash rejects all
expected/actual provider or model mismatch rejects all before append
missing/duplicate/mismatched visible response rejects all before append
missing or mismatched receipt reference rejects all before append
retry returns durable Phase 1 duplicates without duplicate Ledger effects
runtime append failure reports the exact accepted prefix, never whole-bundle PASS
free-form Assistant PASS text creates no trusted Evidence
structured PASS claim without matching prior Evidence creates a violation
wrong provider ID or provider kind remains PENDING
wrong context/revision/target remains PENDING
future, stale and boundary-age Evidence is deterministic
NOT_EXECUTED/NOT_VERIFIED/HISTORICAL remain honest but do not satisfy PASS
trusted current PASS satisfies validation/rule/output/claim obligations
trusted current FAIL violates the applicable MUST validation obligation
output presence without trusted structural/rule Evidence remains PENDING
SOURCE_DISPOSITION does not satisfy REQUIRED_RESOURCE
task-end re-evaluation can expire Evidence and re-block dependents
no task-end request returns IN_PROGRESS
pending execution MUST returns BLOCKED
trusted MUST FAIL returns FAILED
all execution MUST satisfied returns READY_TO_CLOSE
evaluator never returns COMPLETE or closureRef
cross-instance replay reconstructs manifests, claims, Evidence and decision
public package contains no project, Host SDK, network or model-client dependency
```

Tests assert typed codes/IDs/states and durable event references, not complete
human-readable messages. A test may not weaken policy validation or replace a
missing receipt with Agent prose.

## 12. D-drive environment and efficiency gates

All commands use this worktree explicitly:

```text
D:\lihuan\vibe_code\codex\et_harness_env\workspaces\phase34_trusted_execution_evaluation
```

The package manifest is byte-identical to Phase 2. The ignored package
`node_modules` junction reuses the accepted D-drive dependency tree. No dependency
installation is authorized unless the declared dependency signature changes.

All task HOME, cache, temp, compile cache, logs and build outputs remain below:

```text
D:\lihuan\vibe_code\codex\et_harness_env
```

Validation ladder:

```text
Bridge edits        external-agent-bridge focused tests only
Evaluator edits     evidence/completion focused tests only
checkpoint          execution_supervisor package test and one build
integration         only directly affected existing integration, reuse dist
macro-phase close   21 public packages plus 7 integrations exactly once
always              public boundary scan, git diff --check and clean status
```

No more than two large executions may run concurrently. Observer findings are
advisory. The final 21+7 close gate is not repeated for internal Phase 3 and Phase
4 checkpoints.

## 13. Known limitations and forbidden claims

This macro phase does not prove:

```text
cryptographic provider/model/Host authenticity
mechanical preflight interception in AUDIT Hosts
Phase 5 Reflection/Knowledge/Context/Closure completion
task COMPLETE
multiple Evidence Policy composition
concurrent Event Store multi-writer coordination beyond Phase 1
Hosted CI acceptance
ATP Pilot or real hardware execution
```

## 14. Step exit condition

Implementation may begin only after this context is committed with a clean tracked
worktree. Any material expansion first updates and re-freezes this context.
Phase 5 and later phases remain forbidden in this macro-phase branch.
