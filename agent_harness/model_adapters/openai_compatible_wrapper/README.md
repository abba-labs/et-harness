# OpenAI-Compatible Model Wrapper v0.1

Provider-layer wrapper for the Generic Model Adapter JSON process protocol.

It is **not** a Public Governance Plugin and owns no Context, Knowledge, Rule,
Gate, Reflection, Closure, Project, Host, or Tool-System behavior.

```text
GenericModelGenerateRequest (stdin)
        ↓
OpenAI-Compatible Model Wrapper
        ↓
HTTP provider
        ↓
GenericModelGenerateResponse (stdout)
```

## Supported API styles

The API style is explicit. The wrapper never guesses from a provider hostname.

```text
OPENAI_COMPAT_API_STYLE=responses
OPENAI_COMPAT_API_STYLE=chat_completions
```

`responses` maps JSON requests to `text.format.type=json_schema` with strict
schema output.

`chat_completions` supports three JSON strategies:

```text
OPENAI_COMPAT_CHAT_JSON_MODE=json_schema
OPENAI_COMPAT_CHAT_JSON_MODE=json_object
OPENAI_COMPAT_CHAT_JSON_MODE=prompt_only
```

`json_object` is the broad compatibility option for providers that expose the
OpenAI Chat Completions shape but do not implement Chat Structured Outputs.
The Generic Model Adapter prompt still includes the full expected Reflection
schema and the Governance Kernel remains the authoritative validator.

## Required environment

```text
OPENAI_COMPAT_BASE_URL
OPENAI_COMPAT_API_KEY
OPENAI_COMPAT_MODEL
OPENAI_COMPAT_API_STYLE
```

Examples of base URL shape:

```text
https://api.openai.com/v1
https://api.deepseek.com
```

The wrapper appends `/responses` or `/chat/completions` itself.

## Optional environment

```text
OPENAI_COMPAT_PROVIDER_ID
OPENAI_COMPAT_CHAT_JSON_MODE
OPENAI_COMPAT_TIMEOUT_MS
OPENAI_COMPAT_MAX_RESPONSE_BYTES
OPENAI_COMPAT_MAX_OUTPUT_TOKENS
OPENAI_COMPAT_EXTRA_BODY_JSON
OPENAI_COMPAT_EXTRA_HEADERS_JSON
```

Provider-specific non-core parameters such as reasoning/thinking controls may
be placed in `OPENAI_COMPAT_EXTRA_BODY_JSON`. Core request fields cannot be
overridden through that object.

Additional headers cannot override `Authorization` or `Content-Type`.

## Security boundary

The wrapper receives credentials only because the outer Model Adapter process
explicitly forwards them. The generic JSON process bridge does not inherit
arbitrary parent secrets.

The wrapper never emits the API key, provider reasoning content, or hidden
chain-of-thought into `GenericModelGenerateResponse`. Only the provider's final
visible text is returned.

## Response contract

For WORK, final visible provider text becomes `outputText`.

For GOVERNANCE_REFLECTION, the same final visible text is returned. The Generic
Model Adapter parses it as JSON and the Governance Kernel independently
validates the complete `TurnReflectionResult`, including scope/category rules.
