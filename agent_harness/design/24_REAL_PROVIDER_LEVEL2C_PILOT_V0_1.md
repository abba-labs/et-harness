# Real Provider Governance Pilot v0.1 — Level 2C

## 1. Purpose

Level 2C proves that a real external model provider can be governed by the Public Governance Runtime **without DSH and without Tool Plugins**.

The target chain is:

```text
ordinary business task
  ↓
Generic Host / Real Provider Pilot
  ↓
Public Governance Runtime.openTurn()
  ↓
automatic Project + Context + A/R/K/G
  ↓
real model WORK call
  ↓
visible output Observation
  ↓
Public Governance Runtime.closeTurn()
  ↓
automatic real model GOVERNANCE_REFLECTION call
  ↓
Kernel validation
  ↓
8/8 Mandatory Closure
  ↓
TURN_CLOSED
```

Provider/model-specific HTTP behavior remains outside Public Governance Runtime.

## 2. Two real-provider lanes

### 2C-1 — synthetic Project

Purpose: isolate real Provider/API behavior from ET-TOOL Project routing quality.

PASS proves:

```text
Provider protocol
→ Generic Model Adapter
→ Governance Runtime
→ automatic Reflection / Closure
```

### 2C-2 — real ET-TOOL Project Plugin

Purpose: prove the same Provider can work with the actual ET-TOOL Architecture / Rules / Knowledge / Gates.

The Pilot creates a disposable ET-TOOL Project snapshot and then lets the real `@agent-harness/project-et-tool` plugin discover/register that snapshot normally.

The snapshot contains only:

```text
project.yaml
architecture/
rules/
knowledge/
gates/
source/CMakeLists.txt
source/apps/ root marker
```

This preserves the real Project Contract while ensuring automatic Context/Knowledge/Closure writes cannot mutate the source checkout. Package build output, `node_modules`, and product source are not copied into the writable project snapshot.

Default ordinary business task:

> 分析 ET-TOOL 中 Code Gate、Release 构建与验证证据之间的执行关系，并给出简洁结论。

The task deliberately contains no instruction to:

- manage Context;
- search Knowledge;
- classify PROJECT/PUBLIC scope;
- perform Reflection;
- execute Closure.

Those are Runtime responsibilities.

## 3. Tool System exclusion

Level 2C does not expose filesystem, GitHub, Google Drive, Web, J-Link, shell, or other external tools to the model.

This is intentional.

The ET-TOOL lane measures whether the automatically routed Project governance context is sufficient for the selected read-only analysis task.

Tool discovery/registration/authentication belongs to a future independent Tool Plugin System.

## 4. Real Provider Pilot CLI

Package:

```text
@agent-harness/real-provider-governance-pilot
```

The CLI mounts:

```text
Governance Catalog
Project Manager
Architecture Navigator
Rule Manager
Knowledge Manager
Gate Manager
Evidence / Context / Experience Managers
Agent Governance Kernel
8/8 Closure Adapters
Auto Governance Engine
Public Governance Runtime
ET-TOOL Project Plugin (2C-2 only)
```

It then connects the existing model layer:

```text
OpenAI-compatible Wrapper
→ JSON Process Model Client
→ Generic Model Adapter
→ Generic Model Pilot Driver
```

The CLI owns no Context/Knowledge/Reflection/Closure business logic.

## 5. Mechanical PASS criteria

A Level 2C run is PASS only when:

1. exactly two model calls were observed;
2. call 1 is `WORK`;
3. call 2 is `GOVERNANCE_REFLECTION`;
4. both model calls succeeded;
5. visible work output is non-empty;
6. Runtime project identity matches the selected lane;
7. Kernel Journal is BOUND to the same expected project;
8. Architecture route is non-empty;
9. Rule route is non-empty;
10. Knowledge route is non-empty;
11. Gate route is non-empty;
12. TASK_INPUT Observation exists and exactly equals the original business task;
13. ASSISTANT_MESSAGE Observation exists and exactly equals the visible model answer;
14. Knowledge scope is explicitly NONE / PROJECT / PUBLIC / BOTH;
15. all fixed mandatory Closure module receipts exist;
16. every mandatory receipt is APPLIED / NO_CHANGE;
17. aggregate Closure status is COMPLETE;
18. Kernel Journal status is CLOSED.

No predetermined Knowledge Candidate is required.

`NONE` is a valid Knowledge classification.

## 6. Audit Receipt

Every sufficiently initialized run writes one sanitized JSON receipt.

Audit stores:

- lane/run/provider origin/provider id/model/API style;
- task SHA-256 + character count;
- model call purpose/order/status/duration;
- routed Architecture/Rule/Knowledge/Gate IDs;
- governed Observation refs + content SHA-256/length;
- Reflection scope decisions + candidate counts;
- Closure module statuses/counts;
- Journal project binding/status;
- PASS / blocking reasons.

Audit does not store:

- API key;
- full provider request;
- complete system/user prompts;
- full model answer;
- hidden chain-of-thought/private reasoning.

Provider error text is redacted against the configured API key before persistence.

## 7. Provider configuration boundary

Required:

```text
OPENAI_COMPAT_BASE_URL
OPENAI_COMPAT_API_KEY
OPENAI_COMPAT_MODEL
OPENAI_COMPAT_API_STYLE
```

These values exist only at the Model/Pilot boundary.

Public Governance Runtime source must contain no `OPENAI_COMPAT_*` references.

## 8. Contract validation vs real external Provider

### Repository contract validation

`phase4a_real_provider_governance_pilot_v0_1.sh`

starts a local mock OpenAI-compatible HTTP server and runs the **same real-provider CLI** twice:

```text
responses + synthetic
chat_completions + real ET-TOOL Project Plugin over disposable snapshot
```

It also verifies that a fixture API key does not appear in generated Audit artifacts.

This proves the execution/audit contract without requiring a credential.

### Real external Provider validation

Real validation supplies actual Provider configuration externally and runs the same CLI.

No repository code change is permitted between contract and real-provider execution.

## 9. Failure localization

```text
2C-1 FAIL
→ Provider/model/adapter/runtime integration issue

2C-1 PASS + 2C-2 FAIL
→ ET-TOOL Project Context/routing issue

2C-1 PASS + 2C-2 PASS
→ model-independent project governance works without DSH/Tool System
```

Only after this should Host integration or Tool Plugin System work proceed.
