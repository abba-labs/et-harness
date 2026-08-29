# Execution Supervisor Phase 6 Host Enforcement Context v0.1

> Status: **FROZEN IMPLEMENTATION CONTEXT / NO SOURCE IMPLEMENTATION YET**
> Date: 2026-08-29
> Branch: `feat/execution-supervisor-phase6-host-enforcement-profiles-v0.1`
> Starting HEAD: `d5c01f9f109fb79337eed3f99038d195d657edbc`
> Phase 5 source: `feat/execution-supervisor-phase5-lifecycle-closure-v0.1`

## 1. Authority and execution container

This context compiles the Phase 6 boundary from:

```text
root AGENTS.md
Codex Local Development And Validation Charter v0.1
Execution Supervisor Phase 5 Completion Handoff v0.1
Execution Supervisor And Obligation Ledger Design 25 v0.1
Public Governance Runtime And External Boundaries Design 21 v0.1
current source and tests at d5c01f9f109fb79337eed3f99038d195d657edbc
```

The repository does not contain the later `compile_task_context.py`/R002
compiler named by an outer workspace rule, so this persisted context follows the
repository's existing manual frozen-context convention and fails closed on any
scope expansion.

The user explicitly requires work to remain in this conversation, with child
Agents used only as observers/explorers beneath it. Observer findings can expose
defects but cannot establish PASS. Only mechanical tests and persisted evidence
can establish an acceptance conclusion.

## 2. Phase objective

Phase 6 adds the smallest truthful Host boundary around the existing public
contracts and Runtime:

```text
Host capability facts
  -> strict validation and existing AUDIT/ENFORCE negotiation
  -> exact Runtime supervision binding and visible effective claim

AUDIT Host
  -> observe completed work
  -> existing Event Store/Ledger/Completion/Closure path
  -> never claims pre-execution interception

ENFORCE Host
  -> existing Governed Tool Gateway
  -> Runtime preflightAction
  -> Supervisor WRITE_SCOPE check + existing Auto Governance guard
  -> raw executor only after ALLOW
  -> existing observation and supervision path
```

The phase connects existing pieces. It does not introduce another Gateway,
policy engine, lifecycle, registry, workflow or adapter framework.

## 3. Exact deliverables

Deliver only:

```text
strict HostCapabilityContract validation at supervised Runtime binding
requested/effective AUDIT or ENFORCE negotiation bound to the live Runtime
truthful Host identity, adapter identity and effective claim in Runtime status
AUDIT observation profile that cannot claim mechanical interception
ENFORCE admission through the existing Governed Tool Gateway
trusted registration-side tool effect declaration
structured mutation intent passed to Supervisor without parsing tool arguments
deterministic WRITE_SCOPE preflight using the existing Ledger scope semantics
stable tool event identity required for supervised ENFORCE execution
mechanical block before raw executor for unauthorized or unprovable action
same public supervision contract exercised with multiple Host profiles
```

Capability metadata is a Host wiring assertion, not cryptographic Host
attestation and never Agent evidence. Negotiation changes only the truthful
enforcement claim; it never changes Project policy or marks an obligation PASS.

## 4. Frozen semantics

### AUDIT

```text
effectiveLevel = AUDIT
completed/parallel receipts may be ingested
missing proof still blocks completion
out-of-scope work already performed becomes a Ledger violation
mechanical interception and pre-execution blocking are not claimed
```

An explicit ENFORCE request may negotiate to AUDIT when required Host capability
facts are missing, as already defined by the frozen public contract. That result
must remain explicit in status and must never enter the ENFORCE execution path.

### ENFORCE

ENFORCE requires the existing minimum capability set:

```text
supportsPreflight
supportsToolInterception
supportsStableToolEventId
```

For a supervised ENFORCE action, the trusted tool registration declares whether
the action is read-only or supplies a structured mutation intent. Unknown tool
effects, missing stable event identity, malformed mutation intent, unsupported
MOVE/COPY proof, or an out-of-scope target fail closed before the raw executor.

The Agent may supply ordinary tool arguments but cannot supply or replace the
trusted effect mapper, scope decision, raw executor, Host profile or stable event
identity policy.

## 5. Ownership boundaries

```text
Execution Supervisor
  owns Host capability contract validation/negotiation and deterministic
  WRITE_SCOPE evaluation against the Task Supervision Contract

Governance Runtime
  owns the live Task/Turn/Host-profile binding and combines Supervisor scope
  preflight with the existing Auto Governance action guard

Governed Tool Gateway
  remains the only model-facing ENFORCE execution boundary and guarantees that
  BLOCKED means executorCalled=false

Host Adapter
  translates Host events and injects capability facts; it owns no Project policy

Agent
  cannot establish capability, authorization, Evidence, PASS or completion
```

## 6. Compatibility and recovery

Existing non-supervised Gateway behavior remains compatible. Existing AUDIT
supervision callers without a Host profile remain truthful because they make no
mechanical-interception claim. Any supervised ENFORCE binding requires an
explicit valid Host profile.

A live Runtime cannot replace its bound Host/adapter profile with a different
profile. Cross-process ENFORCE rehydration requires an explicit valid Host
profile with cross-process-resume capability; it reconstructs Ledger state from
the existing Event Store and creates no second persistence authority.

## 7. Allowed implementation surface

Expected bounded files:

```text
agent_harness/public_plugins/execution_supervisor/src/contracts.ts
agent_harness/public_plugins/execution_supervisor/src/obligation-ledger.ts
agent_harness/public_plugins/execution_supervisor/src/validation.ts
agent_harness/public_plugins/execution_supervisor/src/index.ts
agent_harness/public_plugins/execution_supervisor/tests/* focused Phase 6 tests

agent_harness/public_plugins/governance_runtime/src/contracts.ts
agent_harness/public_plugins/governance_runtime/src/service.ts
agent_harness/public_plugins/governance_runtime/src/tool-gateway.ts
agent_harness/public_plugins/governance_runtime/src/index.ts
agent_harness/public_plugins/governance_runtime/tests/tool-gateway.test.ts
agent_harness/public_plugins/governance_runtime/tests/* one focused Host-profile integration

agent_harness/public_plugins/execution_supervisor/README.md
agent_harness/public_plugins/governance_runtime/README.md
```

Not every listed file must change. Any other source package or public contract
expansion requires this context to be updated and re-frozen first.

## 8. Explicit non-goals

Do not implement:

```text
a second Tool Gateway, policy engine, Host registry, adapter registry or DI layer
Codex/Claude/DSH-specific SDK integrations or one package per Host
shell/MCP/tool argument parsing inside the public Supervisor
cryptographic Host/provider/model authentication
network or model calls on the event/preflight hot path
new Manager, Reflection, Closure, Event Store or task lifecycle implementations
Project-specific or ATP business policy in the public Harness
Phase 7 compaction, benchmarks, Observer coupling or numeric SLO changes
Phase 8 Pilot or hardware execution
```

## 9. Mandatory focused acceptance

At minimum mechanically prove:

```text
the same Task Supervision Contract binds two distinct Host profiles
AUDIT remains AUDIT and does not expose an interception claim
requested ENFORCE with an incomplete capability set reports effective AUDIT
malformed Host capability contracts are rejected
supervised ENFORCE without an explicit capable Host profile is rejected
a live supervised Runtime rejects Host/adapter profile replacement
AUDIT completed out-of-scope work is recorded as VIOLATED and blocks completion
ENFORCE out-of-scope mutation is BLOCKED before raw executor invocation
ENFORCE unknown effect or missing stable event identity fails closed
ENFORCE allowed mutation executes and preserves one stable event identity
Agent/tool result cannot replace the registration-side scope decision
existing non-supervised Gateway behavior remains compatible
```

## 10. D-drive environment and validation ladder

All commands use this worktree explicitly:

```text
D:\lihuan\vibe_code\codex\et_harness_env\workspaces\phase6_host_profiles
```

All HOME, temp, npm cache, state, log and build paths remain below:

```text
D:\lihuan\vibe_code\codex\et_harness_env
```

Reuse the existing Node 22 runtime, npm cache and dependency tree. Do not run an
install while dependency signatures are unchanged.

Validation ladder:

```text
edit loop       only focused Host-profile/Gateway tests
checkpoint      execution_supervisor + governance_runtime package tests/builds
logic complete  only directly related supervised lifecycle integration
phase close     21 public packages plus 7 integrations exactly once
always          public boundary scan, git diff --check and status audit
```

No more than two large executions run concurrently. Long executions write D
drive logs and use low-frequency polling.

## 11. Step exit condition

Implementation begins only after this context is committed with no other
worktree change. Phase 6 completes only after a completion Handoff records exact
commits, mechanical evidence, failures and remaining limitations. Phase 7 and
later remain forbidden on this branch.
