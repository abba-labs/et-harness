# Public Governance Runtime And External Boundaries v0.1

> Status: Step 7 architecture correction after the DSH + Google Drive pilot coupling failure.

## 1. Core decision

Governance is the reusable core. DSH is only one Host. GPT / DeepSeek / Claude / Codex are only semantic executors. Google Drive / GitHub / Web / J-Link are Tool plugins. ET-TOOL is one Project plugin.

```text
┌──────────────────────────────────────────────────────────────┐
│ Model / Semantic Executors                                  │
│ GPT | DeepSeek | Claude | Codex | Mock                      │
└─────────────────────────────┬────────────────────────────────┘
                              │ GovernanceSemanticExecutor
┌─────────────────────────────▼────────────────────────────────┐
│ Host Adapters                                                │
│ DSH | Codex | Claude Code | Generic Test Host               │
└─────────────────────────────┬────────────────────────────────┘
                              │ openTurn / observeWork /
                              │ preflightAction / closeTurn
══════════════════════════════▼══════════════════════════════════
               PUBLIC GOVERNANCE RUNTIME
══════════════════════════════┬══════════════════════════════════
                              │
┌─────────────────────────────▼────────────────────────────────┐
│ Governance Business                                         │
│ Auto Governance Engine                                      │
│ Project / Context / Architecture / Rules / Knowledge / Gate │
│ Evidence / Experience / Working Set / Obligations           │
└─────────────────────────────┬────────────────────────────────┘
                              │
┌─────────────────────────────▼────────────────────────────────┐
│ Kernel                                                       │
│ Turn Journal | Unified Reflection | 8/8 Closure | Receipt   │
└─────────────────────────────┬────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        │                                           │
┌───────▼──────────────────┐              ┌─────────▼──────────┐
│ Project Plugin System    │              │ Tool Plugin System │
│ ET-TOOL / other projects │              │ filesystem / git   │
│ A/R/K/G resources        │              │ web / Drive / JLink│
└──────────────────────────┘              └────────────────────┘
```

## 2. Governance Runtime owns lifecycle semantics

The canonical Runtime API is Host-neutral:

```text
openTurn()
observeWork()
preflightAction()
recordReviewDecision()
closeTurn()
completeTask()
pauseTask()
```

`openTurn()` owns:

```text
Project resolve
→ Context create/resume
→ Architecture / Rule / Knowledge / Gate route
→ Context Envelope
→ Kernel Turn Journal OPEN
```

`closeTurn()` owns:

```text
SemanticExecutor
→ Unified Reflection
→ mandatory scope classification
→ 8/8 Mandatory Closure
→ Closure Receipt
→ TURN_CLOSED
```

A Host may not bypass this lifecycle by directly reimplementing Context / Knowledge / Reflection / Closure logic.

## 3. Model boundary

A model adapter implements only:

```ts
interface GovernanceSemanticExecutor {
  executorId: string
  reflect(request: GovernanceSemanticRequest): Promise<unknown> | unknown
}
```

The Runtime supplies the semantic request. The model is not responsible for remembering that governance exists.

The Runtime request must force explicit domain classification:

```text
NONE
PROJECT
PUBLIC
BOTH
```

Knowledge candidates must also choose valid Knowledge category references before persistence.

The same Runtime can therefore be tested with a Mock executor and later run with GPT / DeepSeek / Claude / Codex without changing governance lifecycle code.

## 4. Host boundary

A Host Adapter translates Host-specific events into Runtime calls only.

Example mapping:

```text
Host turn begins     -> governanceRuntime.openTurn()
Host tool completes  -> governanceRuntime.observeWork()
Host action planned  -> governanceRuntime.preflightAction()
Host turn ends       -> governanceRuntime.closeTurn()
```

Host Adapter may additionally translate Runtime Context into the Host's message/context shape and expose Runtime review decisions through Host-native controls.

Host Adapter MUST NOT contain:

```text
Architecture search policy
Rule search policy
Knowledge routing policy
Knowledge classification policy
Gate evidence semantics
Reflection lifecycle
Closure sequencing
Evolution persistence logic
```

These belong to public Governance Runtime / Engine / Managers.

## 5. Tool System boundary

Tool plugins are external capabilities, not governance managers.

Examples:

```text
filesystem
git / GitHub
web
database
Google Drive
J-Link / CMSIS-DAP
oscilloscope / instruments
```

The future Tool Plugin System owns:

```text
registration
discovery
permissions
credentials
connection lifecycle
capability metadata
model-visible tool schema
execution
```

Governance Runtime sees only standard observations such as:

```text
tool-result
resource-touch
```

It does not import Google Drive OAuth, MCP, GitHub API, J-Link or any other tool implementation.

## 6. Project Plugin boundary

Project Plugin supplies domain specialization:

```text
project identity
Architecture resources
Rules
Knowledge
Gates
Project-specific review providers
```

Governance Runtime does not contain ET-TOOL business rules. ET-TOOL is the first validation project, not a dependency of the public Runtime.

## 7. Why the previous Step 7 was superseded

The superseded pilot combined:

```text
DeepSeek model
+ DSH Runtime
+ DSH lifecycle events
+ Governance Kernel
+ Google Drive MCP
+ OAuth credentials
+ ET3101 real business task
```

A failure could therefore originate from any of six unrelated layers. It was not a valid isolation test of Governance itself.

Correct validation ladder:

### Level 1 — Deterministic Governance Runtime

```text
Mock SemanticExecutor
→ Generic Runtime Driver
→ Public Governance Runtime
→ synthetic/real Project Plugin
```

No Host-specific runtime, no external tools, no network model dependency.

Must validate lifecycle, Context, routing, scope classification, Closure and recovery.

### Level 2 — Real Model, Generic Host

```text
GPT / DeepSeek / Claude / Codex
→ one thin Generic model adapter
→ same Governance Runtime
```

Tests whether strong/weak real models can satisfy the semantic contract while the Runtime still owns governance triggering.

### Level 3 — Host Integration

```text
DSH / Codex / Claude Code / other Host
→ thin Host Adapter
→ same Governance Runtime
```

At this stage failures are Host-adapter failures, not ambiguous Governance failures.

### Level 4 — Tool Integration

External Tool Plugin System is connected only after the governance lifecycle has independently passed.

## 8. Current Step 7 acceptance

Host-independent Governance Runtime v0.1 is accepted only when deterministic validation proves:

```text
Project auto resolve               PASS
Context create/resume              PASS
Architecture routing               PASS
Rule routing                       PASS
Knowledge routing                  PASS
Gate routing                       PASS
SemanticExecutor auto trigger      PASS
Knowledge category classification  PASS
8/8 Closure                        PASS
TURN_CLOSED                        PASS
multi-Turn Context reuse           PASS
failed Reflection auto recovery    PASS
no Host event references           PASS
no external Tool coupling          PASS
```

DSH integration and Google Drive are explicitly NOT Step 7 acceptance conditions.

## 9. Known next runtime gap

v0.1 supports automatic unresolved-Turn recovery while the Runtime session remains in memory.

After a whole process restart, Kernel state may still contain unresolved Turns but the Runtime's actor/task binding is not yet persisted. v0.1 fails closed in that condition.

This must later be solved through a public Runtime State Store / rehydration contract, never by putting recovery state into a DSH/Codex/Claude Host Adapter.
