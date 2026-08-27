# Real Provider Governance Pilot v0.1

Level 2C validates Public Governance Runtime against a **real external model provider** without DSH and without Tool Plugins.

## Lanes

### `synthetic`

Isolates provider/runtime integration against a deterministic synthetic Project Contract.

### `et-tool`

Loads the real `@agent-harness/project-et-tool` plugin and the repository's real Architecture / Rules / Knowledge / Gates through a **disposable runtime snapshot**.

The snapshot copies only:

```text
project.yaml
architecture/
rules/
knowledge/
gates/
source/CMakeLists.txt
source/apps/ root marker
```

The Project Plugin still discovers/registers ET-TOOL normally, but Context/Knowledge/Closure mutations happen only inside the temporary snapshot. The source checkout is never used as the writable project root for this Pilot.

Default business task:

> 分析 ET-TOOL 中 Code Gate、Release 构建与验证证据之间的执行关系，并给出简洁结论。

The task contains no instruction to manage Context, Knowledge, Reflection, scope classification, or Closure.

## Required provider configuration

```text
OPENAI_COMPAT_BASE_URL
OPENAI_COMPAT_API_KEY
OPENAI_COMPAT_MODEL
OPENAI_COMPAT_API_STYLE=responses|chat_completions
```

Optional provider configuration is owned by `@agent-harness/openai-compatible-model-wrapper`.

The API key must be supplied out-of-band by the process environment or a secret manager. Do not commit a populated credential file.

## Optional pilot configuration

```text
REAL_PROVIDER_LANE=synthetic|et-tool
REAL_PROVIDER_PROJECT_ROOT=<source ET-TOOL repo root copied into a disposable snapshot>
REAL_PROVIDER_TASK=<ordinary business task override>
REAL_PROVIDER_RUN_ID=<stable audit id>
REAL_PROVIDER_RUNTIME_ID=<runtime id>
REAL_PROVIDER_TURN_ID=<turn id>
REAL_PROVIDER_ENABLE_GLOBAL_KNOWLEDGE=0|1
AGENT_HARNESS_STATE_ROOT=<runtime state root>
AGENT_HARNESS_REAL_PROVIDER_AUDIT_ROOT=<audit output root>
```

By default runtime state, ET-TOOL project snapshots and audits are stored under the operating-system temporary directory, not in the repository.

## PASS contract

A run is PASS only when all conditions hold:

1. exactly two model calls occurred;
2. call 1 is `WORK`;
3. call 2 is automatically triggered `GOVERNANCE_REFLECTION`;
4. model visible output is non-empty;
5. Runtime and Journal are bound to the expected Project (`synthetic-level2c` or `et-tool`);
6. Architecture / Rule / Knowledge / Gate routing all produced candidates;
7. `TASK_INPUT` exists and exactly matches the original business task;
8. `ASSISTANT_MESSAGE` exists and exactly matches the visible model answer;
9. Knowledge scope is explicitly `NONE / PROJECT / PUBLIC / BOTH`;
10. all fixed 8 Mandatory Closure receipts are `APPLIED / NO_CHANGE`;
11. aggregate Closure is `COMPLETE`;
12. Kernel Journal is `CLOSED`.

A Knowledge Candidate is **not required**. `NONE` is valid if the model finds no durable new knowledge.

## Audit receipt

Every sufficiently initialized run writes:

```text
<AGENT_HARNESS_REAL_PROVIDER_AUDIT_ROOT>/<runId>.json
<AGENT_HARNESS_REAL_PROVIDER_AUDIT_ROOT>/latest.json
```

The receipt contains:

- provider origin / configured provider id / model id / API style;
- task hash and length, not task prompt duplication;
- model call purpose/order/status/duration;
- routed A/R/K/G IDs;
- bounded Observation refs and content hashes, not hidden reasoning;
- Reflection scope decisions and candidate counts;
- all Closure module receipt statuses;
- final Journal state;
- mechanical PASS/blocking reasons.

It never writes API keys, complete provider requests, complete model prompts, full model output, or hidden chain-of-thought. Provider error strings are redacted against the configured API key before persistence.

## Layer boundary

```text
real provider
  ↓
OpenAI-compatible model wrapper
  ↓
JSON Process Model Client
  ↓
Generic Model Adapter
  ↓
Generic Model Pilot Driver
  ↓
PUBLIC GOVERNANCE RUNTIME
```

This pilot must not add provider-specific behavior to Governance Runtime, Auto Governance Engine, Kernel, Project Plugin, or Tool System.
