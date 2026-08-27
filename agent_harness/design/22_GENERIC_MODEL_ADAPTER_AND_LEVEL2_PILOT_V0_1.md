# Generic Model Adapter And Level 2 Pilot v0.1

## 1. Purpose

Level 2 proves that a **real model can be only a worker/semantic judge** while Public Governance Runtime remains the sole owner of governance lifecycle.

This phase must not depend on DSH or Tool Plugin System.

## 2. Layering

```text
Model Provider / Local Model / Model CLI
              ↓
Provider wrapper
              ↓
GenericModelClient
              ↓
Generic Model Adapter
       ├─ Governed Work Executor
       └─ GovernanceSemanticExecutor
              ↓
Generic Model Pilot Driver
              ↓
PUBLIC GOVERNANCE RUNTIME
              ↓
Auto Governance Engine
              ↓
Kernel + Managers + 8/8 Closure
              ↓
Project Plugin
```

A JSON stdin/stdout process bridge is one optional model transport. It is not a Host Adapter and not a Tool Plugin.

## 3. Business task invariant

The business task given to the work model is preserved verbatim.

Governance information is supplied separately as an automatically generated Context Envelope.

The business task MUST NOT contain reminders such as:

- manage Context;
- search Knowledge;
- classify PROJECT/PUBLIC;
- run Reflection;
- run Closure.

Those are Runtime responsibilities.

## 4. Turn Observation Ledger

A stateless semantic model cannot reliably reflect on a Turn if it only receives opaque message/tool refs.

Therefore Governance Runtime owns a bounded Host-neutral observation ledger.

Allowed observation classes:

```text
TASK_INPUT
USER_MESSAGE
ASSISTANT_MESSAGE
TOOL_RESULT
RESOURCE_TOUCH
```

Only visible/durable facts belong here:

- original business task;
- user-visible model answer;
- bounded tool result summary;
- resource references / bounded summary.

Hidden chain-of-thought/private reasoning MUST NOT be stored.

Each observation is bounded and receives a SHA-256 observation ref. The ref is appended into the Kernel Turn Journal before sealing. Consequently the Reflection fingerprint is bound to the observation content without copying raw content into the Kernel contract.

## 5. Model work

The work model receives:

```text
original task
+
automatic Governance Context
```

It returns only a user-visible business answer.

The Generic Pilot Driver then records that answer through `GovernanceRuntime.observeWork()`.

It does not call any Manager directly.

## 6. Semantic Reflection

`GovernanceRuntime.closeTurn()` automatically invokes `GovernanceSemanticExecutor`.

The generic model adapter sends:

- current Context;
- bounded Turn Observations;
- Project/Public Knowledge categories;
- required classification rules;
- strict TurnReflectionResult JSON schema.

The model output is fail-closed:

1. model bridge contract/request identity must match;
2. output must be one JSON value (direct JSON or strict JSON text);
3. Kernel validates task/turn identity, sections, candidate domains, scope consistency and UNBOUND constraints;
4. Closure modules enforce manager-specific classification/persistence rules.

No adapter auto-corrects semantic classifications or invents Knowledge categories.

## 7. Model transport

The canonical Level 2 transport contract is provider-neutral:

```text
stdin  GenericModelGenerateRequest JSON
stdout GenericModelGenerateResponse JSON
```

A wrapper may use GPT, DeepSeek, Claude, a local model or another provider.

Public Governance Runtime has no provider API key/environment variable and no provider SDK.

## 8. Validation separation

### Level 2A — contract

Deterministic fake model process validates:

- work call occurs first;
- business task remains unchanged;
- automatic Governance Context reaches the work model;
- visible answer enters Turn Observation Ledger;
- Reflection call occurs automatically second;
- semantic request sees TASK_INPUT + ASSISTANT_MESSAGE;
- Knowledge category list is supplied;
- Project Knowledge Candidate can be classified and persisted;
- all 8 Closure modules complete;
- Turn becomes CLOSED.

### Level 2B — real

Replace only the JSON process bridge command with a real model wrapper.

Acceptance does not require a predetermined Knowledge finding. `NONE` is legal. It requires:

- non-empty user-visible work output;
- automatic Reflection;
- explicit valid Knowledge scope decision;
- valid 8/8 Closure;
- TURN_CLOSED.

A model that produces invalid structured Reflection fails the Pilot; Runtime must not silently repair it.

## 9. Explicit exclusions

Level 2 does not test:

- filesystem tools;
- GitHub tools;
- Google Drive;
- web search;
- J-Link/hardware;
- DSH/Codex/Claude Host lifecycle events.

Those belong to later Tool-System and Host-Adapter phases.
