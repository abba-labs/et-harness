# OpenAI-Compatible Model Wrapper / Level 2B v0.1

## Purpose

Level 2B proves that a real provider protocol can be attached outside Public
Governance without changing Governance Runtime, Auto Governance Engine, Kernel,
Managers, or Project Plugins.

The boundary is:

```text
OpenAI / DeepSeek / other compatible provider
                    ↓
OpenAI-Compatible Model Wrapper
                    ↓
JSON Process Model Client
                    ↓
Generic Model Adapter
                    ↓
Generic Model Pilot Driver
                    ↓
PUBLIC GOVERNANCE RUNTIME
```

The wrapper is a **Model Adapter**, not a Public Governance Plugin and not a
Tool Plugin.

## Explicit provider protocol selection

The wrapper never infers provider behavior from hostnames.

```text
OPENAI_COMPAT_API_STYLE=responses
OPENAI_COMPAT_API_STYLE=chat_completions
```

This is deliberate because OpenAI and OpenAI-compatible providers do not expose
an identical feature matrix at all times.

### Responses

```text
POST <base>/responses
```

WORK uses plain text output.

GOVERNANCE_REFLECTION uses strict `text.format.type=json_schema` with the
schema supplied by Generic Model Adapter.

### Chat Completions

```text
POST <base>/chat/completions
```

JSON strategy is explicit:

```text
json_schema
json_object
prompt_only
```

`json_object` is the broad compatibility mode. Even when the provider only
guarantees valid JSON, the Governance Kernel still performs authoritative
TurnReflectionResult validation, including exact task/turn identity and scope
classification.

## Governance ownership remains unchanged

The wrapper must never:

- create/resume Context;
- search or write Knowledge;
- decide when Reflection occurs;
- close a Turn;
- create Evidence/Gate PASS;
- register Host events;
- register Tool plugins.

Its only job is model transport.

## Hidden reasoning boundary

Provider reasoning/thinking fields are intentionally ignored. Only final
visible text is returned to Generic Model Adapter.

Governance Reflection is therefore based on the bounded Turn Observation Ledger
and visible/durable work facts, not provider-private chain-of-thought.

## Credential boundary

The JSON Process bridge inherits only ordinary runtime environment. Provider
credentials and settings are forwarded only when explicitly named by the outer
Model Adapter configuration.

The wrapper requires:

```text
OPENAI_COMPAT_BASE_URL
OPENAI_COMPAT_API_KEY
OPENAI_COMPAT_MODEL
OPENAI_COMPAT_API_STYLE
```

No credential is persisted in Governance Runtime or repository state.

## Level 2B contract validation

`phase4a_openai_compatible_model_wrapper_v0_1.sh` runs a local mock HTTP
provider and executes the existing Level 2 Generic Model Pilot twice:

```text
Responses style
  WORK
  automatic GOVERNANCE_REFLECTION
  8/8 Closure
  TURN_CLOSED

Chat Completions style
  WORK
  automatic GOVERNANCE_REFLECTION
  8/8 Closure
  TURN_CLOSED
```

The mock HTTP provider is only a protocol fixture. It does not bypass the JSON
Process Client, Generic Model Adapter, Generic Pilot Driver, Governance Runtime,
or Kernel Closure path.

## Real-provider validation

After the contract lane passes, real validation changes only these model-layer
values:

```text
OPENAI_COMPAT_BASE_URL
OPENAI_COMPAT_API_KEY
OPENAI_COMPAT_MODEL
OPENAI_COMPAT_API_STYLE
OPENAI_COMPAT_CHAT_JSON_MODE (when chat is used)
```

A real-provider PASS is:

```text
normal business task
→ non-empty visible model output
→ automatic Reflection model call
→ explicit valid scope classification
→ 8/8 Closure COMPLETE
→ TURN_CLOSED
```

No predetermined Knowledge Candidate is required; `NONE` is valid.

## Exclusions

This step does not add:

- DSH Host integration;
- Google Drive / GitHub / Web / filesystem tools;
- provider-specific SDK dependencies;
- ET-TOOL product build changes.
