# Execution Supervisor Phase 1 Codex Handoff v0.1

> **Status: FROZEN / NORMATIVE NEXT-DEVELOPMENT HANDOFF**  
> **Date: 2026-08-29**  
> **Repository: `abba-labs/et-harness`**  
> **Public framework: ET Harness / Agent Governance**  
> **Developer Host for this phase: local Codex**  
> **Normative design: `agent_harness/design/25_EXECUTION_SUPERVISOR_AND_OBLIGATION_LEDGER_V0_1.md`**  
> **Local validation policy: `20260829_CODEX_LOCAL_DEVELOPMENT_AND_VALIDATION_CHARTER_V0_1.md`**

---

# 0. Read this before changing code

Codex has not previously been the developer Agent for this work. Do not infer the current direction from branch names or from the amount of code present in historical branches.

The correct authority order is:

```text
latest main source
+ Design 25
+ Phase 0 repair evidence
+ this Handoff
> historical feature branches
> old chat summaries
> Agent assumptions
```

Before editing anything, Codex must record:

```bash
git remote -v
git fetch --all --prune
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
git status --short
```

Do not proceed from a dirty or stale base without first understanding why.

---

# 1. Current canonical state

The public canonical branch is:

```text
repo:   abba-labs/et-harness
branch: main
```

The source-repair lineage that must be preserved is:

```text
PR #15
fix: repair Execution Supervisor Phase 0 canonical contracts

source repair merge:
cae6c15ccea1aaa100db756bf943895e6af51e8c
```

After the repair, the public Execution Supervisor Phase 0 package contains one canonical contract model only.

Canonical source:

```text
agent_harness/public_plugins/execution_supervisor/src/
  baseline.ts
  contracts.ts
  hash.ts
  index.ts
  validation.ts
```

Canonical tests:

```text
agent_harness/public_plugins/execution_supervisor/tests/
  committed-baseline.test.ts
  contracts.test.ts
  negative-contracts.test.ts
  performance-baseline.test.ts
```

The Phase 0 repair worklog records:

```text
single contract model                    PASS
conflicting PR #12 prototypes removed    PASS
local repository test logic              PASS 17/17
additional fail-closed assertions         PASS 22/22
full benchmark                            PASS 2 x 10000 samples
GitHub-hosted runner                      BLOCKED by hosted execution/budget condition
```

Codex must first run the exact local Phase 0 acceptance defined by the local-development charter. Only a real local mechanical PASS authorizes Phase 1 implementation.

---

# 2. Branches that must NOT be used

There are historical branches whose names look relevant but are not valid development bases.

## 2.1 Old event-store branch

```text
feat/execution-supervisor-phase1-event-store-v0.1
```

This branch points to an old pre-repair source state around:

```text
464f275f0cd10087344cdd0be41380985a455f82
```

It predates the Phase 0 repair and must not be continued, rebased as a hidden shortcut, or treated as current Phase 1 work.

It may be inspected only as historical material if useful:

```bash
git show feat/execution-supervisor-phase1-event-store-v0.1:<path>
```

Do not cherry-pick its old Execution Supervisor implementation into the new branch.

## 2.2 Obsolete Contract Builder branch

```text
feat/public-execution-supervisor-phase1-contract-builder-v0.1
```

PR #13 was explicitly closed as `[OBSOLETE]`.

Reason:

> Design 25 Phase 1 is **Persistent Event Store + Cross-Process Replay**, not a Contract Builder.

Do not revive this branch or reinterpret it as Phase 1.

## 2.3 Old PR #12 prototypes

The following experimental files were deliberately removed from Phase 0 because they formed a second incompatible contract vocabulary:

```text
canonical-json.ts
canonical.ts
completion.ts
event-batch.ts
event-chain.ts
factory.ts
limits.ts
phase0-runtime.ts
receipt-validation.ts
and their associated prototype tests/schema
```

Their removal was a deliberate repair decision.

Phase 1 must be implemented from the current canonical Phase 0 contracts, not by restoring the deleted prototype set wholesale.

---

# 3. The branch Codex should use

The authorized Phase 1 branch is:

```text
feat/execution-supervisor-phase1-event-store-replay-v0.1
```

This branch must be created from the latest clean `main` after the Codex Handoff documents are merged.

Codex workflow:

```bash
git checkout main
git pull --ff-only origin main

# Phase 0 local mechanical acceptance first
# only after it passes:

git checkout feat/execution-supervisor-phase1-event-store-replay-v0.1
```

If the local branch does not exist yet:

```bash
git checkout -b feat/execution-supervisor-phase1-event-store-replay-v0.1 origin/main
```

Before implementation, verify:

```bash
git merge-base --is-ancestor origin/main HEAD
```

At the start of real Phase 1 development, the branch should have no source divergence from its recorded `main` base.

---

# 4. Why Phase 1 exists

Phase 1 is not an abstract persistence exercise.

It fixes the concrete architecture gap exposed by the current ChatGPT real-project Pilot.

The original Governance Runtime assumed roughly:

```text
one process
  → open Turn
  → Agent works
  → observe work
  → Reflection
  → Closure
```

The real external-Agent topology is distributed:

```text
Process A
  Framework opens Task/Turn
      ↓
External Host / Agent
  performs work elsewhere
      ↓
Process B or C
  Framework must ingest/recover/close the same governed Task/Turn
```

Important runtime state previously lived in process memory. When process A exited, the Framework could retain some persisted Task/Turn material but could not reliably reconstruct the exact external execution stream and continue from it.

Without durable execution events and replay, later supervision cannot reliably answer:

```text
what actually happened?
in what order?
under which Task/Turn/Agent identity?
was an event replayed or tampered with?
what evidence was really returned?
where should supervision resume after a process restart?
```

Therefore Phase 1 supplies the durable execution substrate required by all later phases.

---

# 5. Why this Phase 1 test matters

The objective is not merely:

```text
"write events to a JSON file"
```

The objective is to prove a public, Host-neutral invariant:

> **A governed external Agent execution can leave one process, return through another process, and still be reconstructed as the same ordered, integrity-bound Task/Turn execution without rerouting, inventing state, or trusting Agent self-report.**

This matters because later capabilities depend on it:

```text
Phase 2 Obligation Ledger
Phase 3 External Agent Event Bridge
Phase 4 Claim/Evidence/Completion evaluation
Phase 5 Reflection / Knowledge / Context / Closure integration
Phase 8 ATP real-project Pilot
```

If Phase 1 is weak, all later supervision becomes unreliable.

---

# 6. Exact Phase 1 scope

Design 25 defines Phase 1 as:

```text
Persistent event store and replay
```

Deliver only the minimum public substrate necessary for that responsibility.

Required capabilities:

```text
append-only durable execution-event storage
Task/Turn/Agent/Project/Runtime identity binding
contract/context/route/revision binding where the contract exposes them
sequence enforcement
hash/integrity enforcement
idempotent replay
replay cursor persistence
cross-process reopen / rehydrate
corrupt or inconsistent store failure behavior
bounded event acceptance using Phase 0 limits
Host-neutral interfaces
```

The implementation may introduce names such as:

```text
event-store.ts
rehydration.ts
replay.ts
```

or equivalent names if the separation is clearer.

The names are not the contract. The responsibility boundary is.

---

# 7. Explicit Phase 1 non-goals

Do NOT implement later phases during this step.

Specifically, Phase 1 must not become:

```text
live project-specific obligation evaluation
full Obligation Ledger state transitions
claim-versus-Evidence semantic evaluation
final task completion authority
External Chat mailbox implementation
ATP Project Plugin changes
Reflection invocation
Knowledge classification
Context Closure
8/8 Closure orchestration
Tool Gateway enforcement
project-specific event parsing
eTimer logic
ET6801 logic
```

If a later feature seems necessary, first prove whether a small neutral Phase 1 interface is sufficient.

Do not expand scope merely to make a demo look complete.

---

# 8. Contract and ownership boundaries

Phase 1 must preserve the architecture frozen by Design 21 and Design 25.

## Public Execution Supervisor

Owns generic execution-event persistence/replay semantics.

It may know:

```text
Task ID
Turn ID
Agent ID
Project ID
Runtime ID
context/contract hashes
sequence
event IDs
payload hash
store cursor
```

It must not know:

```text
ATP
ET6801
eTimer
project Rule IDs
project file paths
Google Drive folders
```

## Governance Runtime

Remains the public lifecycle entrypoint.

Do not create a second independent lifecycle controller inside the Event Store.

## Host Adapter

Will later translate Host-native execution events into the public event contract.

Do not put Host-specific SDK or policy into Phase 1 persistence code.

## Project Plugin

Will later contribute project-specific obligations/policies.

Phase 1 persistence must not parse project prose to discover obligations.

---

# 9. Phase 0 contract is the only contract base

Codex must inspect and reuse the current types in:

```text
agent_harness/public_plugins/execution_supervisor/src/contracts.ts
```

Before creating a new public type, answer:

```text
Can the existing Phase 0 contract represent this identity/state?
Is this truly persistence/replay state rather than a new business contract?
Would adding this field create a second vocabulary?
Can it remain an internal store record instead?
```

Do not casually rename the existing canonical contract fields.

If a public contract change is genuinely required:

```text
1. explain why Phase 0 cannot represent the requirement;
2. preserve backward compatibility where reasonable;
3. add positive and negative contract tests;
4. never create a parallel V0.1 vocabulary with different names for the same concept.
```

---

# 10. Required Phase 1 tests

The phase is not complete because one happy path works.

At minimum implement deterministic tests for the following.

## 10.1 Create and append

```text
open store for one exact supervised execution
append event sequence 1
append sequence 2
read events back in identical order
replay cursor advances deterministically
```

## 10.2 Cross-instance / cross-process reconstruction

Simulation:

```text
Instance A opens/binds execution and writes events
A exits
Instance B opens the same persisted store
B verifies exact binding
B restores cursor and accepted events
B continues with the next valid sequence
```

The reconstructed state must be equivalent to uninterrupted execution for Phase 1-owned state.

## 10.3 Idempotent replay

```text
same eventId + same canonical payload/hash
→ deterministic duplicate/no-op acceptance
→ no duplicate durable event
→ cursor/state not corrupted
```

## 10.4 Tampered replay

```text
same eventId + different payload/hash
→ integrity conflict
→ fail closed
→ original accepted event remains authoritative
```

## 10.5 Sequence gap

```text
expected N
received N+1 or later
→ reject/block
→ do not silently skip missing event
```

## 10.6 Wrong identity

Reject mismatched:

```text
projectId
taskId
turnId
agentId
runtime/binding identity where applicable
context/contract hash where required
```

## 10.7 Corrupt persisted state

Examples:

```text
truncated record
invalid canonical JSON
wrong state hash
invalid cursor
hash-chain mismatch
```

Expected behavior:

```text
fail closed with specific diagnostic
never silently rebuild a different execution history
```

## 10.8 Empty/new store

A new store must have deterministic initial state and cannot claim that events were previously observed.

## 10.9 Boundedness

Reject or safely handle events that exceed Phase 0 payload/identifier/reference limits.

Do not retain unlimited raw model/tool output in memory.

## 10.10 Public genericity

Production source and tests must not require:

```text
ATP
ET6801
eTimer
MCU
specific real-project paths
specific model/provider SDK
```

Use synthetic identities.

---

# 11. Efficiency test objective

Phase 1 is on the execution hot path. Persistence cannot make the framework unusably slow.

The test must prove structural efficiency first:

```text
event append/replay path calls no LLM
ordinary append performs no A/R/K/G reroute
ordinary append performs no full Context rebuild
no network dependency is required by the public Event Store
replay is incremental from a cursor, not full-project reconstruction
store indexes are bounded or reconstructible
```

Measure at least:

```text
append latency
read/replay latency
1000-event append/replay wall time
persisted bytes per bounded synthetic event
memory behavior for the configured event budget
```

Do not freeze arbitrary performance SLOs before collecting measurements.

If performance is unexpectedly poor, optimize data structures and I/O behavior before adding caching complexity.

---

# 12. Phase 1 acceptance scenarios

## Scenario A — uninterrupted execution

```text
A opens store
A writes events 1..N
A replays
PASS if exact order and integrity are preserved
```

## Scenario B — process handoff

```text
A writes 1..K
A disappears
B reopens the persisted execution
B resumes at K+1
PASS if no reroute/new Turn/new execution history is invented
```

## Scenario C — exact duplicate

```text
submit event K again with identical identity/hash
PASS if idempotent and durable log remains unique
```

## Scenario D — tampered duplicate

```text
submit event K with changed content
PASS if rejected as integrity violation
```

## Scenario E — missing event

```text
submit K+2 when K+1 is missing
PASS if fail closed / blocked rather than silently advancing
```

## Scenario F — wrong Task/Turn

```text
submit valid-looking event from another Task/Turn
PASS if rejected before persistence
```

## Scenario G — persisted state corruption

```text
modify/corrupt persisted state
PASS if recovery fails explicitly rather than inventing history
```

---

# 13. What does NOT count as Phase 1 PASS

The following are insufficient:

```text
one JSON file exists
one event can be serialized
a unit test checks a pure hash function
in-memory Map survives within one process
Codex says persistence is implemented
an old PR #12 event-chain test is copied back
GitHub Actions job exists but steps=[]
Phase 2 Obligation tests pass while cross-process replay is unproven
```

Phase 1 PASS requires actual durable reconstruction across independently created runtime/store instances.

---

# 14. Local validation ladder during implementation

For efficient iteration:

```text
1. focused Phase 1 unit tests
2. execution_supervisor package npm test
3. execution_supervisor package npm run build
4. Phase 1 performance/replay benchmark
5. affected public Runtime/integration tests if touched
6. full local public baseline only at phase-completion checkpoint
```

Do not run the full repository after every edit.

At the final checkpoint, follow the local-development charter and record exact local mechanical evidence.

---

# 15. Required final Handoff from Codex

Before the Phase 1 conversation ends, Codex must add a new progress document, not overwrite this Handoff.

Recommended name:

```text
YYYYMMDD_EXECUTION_SUPERVISOR_PHASE1_EVENT_STORE_REPLAY_HANDOFF_V0_1.md
```

It must record:

```text
starting main HEAD
feature branch
final branch HEAD
files changed
contract changes, if any
implementation ownership boundaries
tests executed
negative tests executed
cross-instance/replay evidence
performance measurements
known limitations
what remains explicitly Phase 2+
exact PASS / FAIL / BLOCKED status
next authorized branch/phase
```

A later Agent should be able to resume from that document without reading the original chat.

---

# 16. First actions Codex should take

Codex should execute this order exactly:

```text
1. clone/fetch abba-labs/et-harness
2. checkout main
3. read root AGENTS.md
4. read local-development charter
5. read this Phase 1 Handoff
6. read Design 25
7. read Phase 0 repair worklog
8. inspect current execution_supervisor canonical source/tests
9. run Phase 0 local mechanical acceptance on main
10. record Phase 0 local acceptance evidence
11. checkout the clean authorized Phase 1 branch
12. design the smallest persistent Event Store / replay contract
13. implement focused tests first or alongside implementation
14. run the Phase 1 local validation ladder
15. write the Phase 1 final Handoff
16. commit/push the branch; do not start Phase 2 in the same conversation
```

Historical ATP context, if Codex needs to understand why this gap matters, may be read using:

```bash
git show project/automated-testing-platform:agent_harness/progress_context/20260828_ATP_CURRENT_CHATGPT_REAL_PROJECT_TEST_CHARTER_V0_1.md

git show project/automated-testing-platform:agent_harness/progress_context/20260828_ATP_CURRENT_CHATGPT_CONTEXT_CONTRIBUTION_AND_PILOT_HANDOFF_V0_1.md
```

Do not make ATP project changes from the public Phase 1 branch.

---

# 17. One-line invariant

> **Phase 1 exists to make the external Agent's observable execution survive process boundaries as one exact, ordered, integrity-bound public execution history; it does not yet decide project obligations, Evidence truth, Reflection or Closure.**
