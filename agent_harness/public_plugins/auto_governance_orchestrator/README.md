# Public Auto Governance Orchestrator v0.1 — DEPRECATED HOST-COUPLED REFERENCE

> **Deprecated in Host-Independent Public Governance Runtime Step 7.**
>
> This package is no longer listed in `public_plugins.v0.1.yaml` and is not a canonical public governance entrypoint.

This implementation predates `@agent-harness/auto-governance-engine` and `@agent-harness/governance-runtime`. It mixes two responsibilities:

```text
DSH/Harness event translation
+
project governance business logic
```

That coupling is now explicitly forbidden by:

`agent_harness/design/21_PUBLIC_GOVERNANCE_RUNTIME_AND_EXTERNAL_BOUNDARIES_V0_1.md`

## Do not extend this package

Do not add new Context / Knowledge / Gate / Reflection / Closure behavior here.

The canonical governance path is now:

```text
Host-specific event
→ thin Host Adapter
→ Governance Runtime
→ Auto Governance Engine
→ Kernel / Managers / 8-of-8 Closure
```

The old event hooks below remain only as migration reference for a future DSH Adapter:

```text
agent/pre-step
tools/result
tools/pre-execute
agent/disposed
```

A future DSH Adapter may translate those events into:

```text
governanceRuntime.openTurn()
governanceRuntime.observeWork()
governanceRuntime.preflightAction()
governanceRuntime.closeTurn()
```

It must not copy the governance logic that currently remains in this legacy source.

## Historical behavior

The old Orchestrator performed:

```text
Human task
→ project resolve
→ Context begin/resume + frame injection
→ Architecture / Rule / Knowledge / Gate routing
→ code-changing tool result
→ Gate refresh + project review-provider packets
→ Agent PASS/BLOCK decisions
→ hard pre-build/test Gate evidence guard
→ Context progress / handoff / completion
```

That business behavior has been extracted into the Host-independent `@agent-harness/auto-governance-engine`.

## Removal condition

This package can be removed after the future DSH Host Adapter has been implemented against `@agent-harness/governance-runtime` and equivalent integration coverage exists.
