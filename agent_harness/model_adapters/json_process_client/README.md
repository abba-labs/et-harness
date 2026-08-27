# JSON Process Model Client v0.1

Provider-neutral model transport for Level 2 governance testing.

The client launches one executable **without a shell** for each model request:

```text
stdin  = one GenericModelGenerateRequest JSON object
stdout = one GenericModelGenerateResponse JSON object
stderr = wrapper diagnostics only
```

This package does not know whether the wrapper uses GPT, DeepSeek, Claude, a local model, or another provider.

## Request

```json
{
  "contractVersion": "0.1",
  "requestId": "...",
  "purpose": "WORK | GOVERNANCE_REFLECTION",
  "systemText": "...",
  "userText": "...",
  "response": {
    "kind": "TEXT | JSON",
    "jsonSchema": {}
  }
}
```

## Response

```json
{
  "contractVersion": "0.1",
  "requestId": "same request id",
  "outputText": "optional text output",
  "outputJson": {},
  "providerId": "optional",
  "modelId": "optional"
}
```

- WORK must ultimately provide non-empty `outputText`.
- GOVERNANCE_REFLECTION may provide `outputJson` directly or strict JSON text.
- stdout must contain only the response JSON. Wrapper logs belong on stderr.
- process timeout/output limits are enforced by the client.

## Environment boundary

The model process does **not** inherit the entire parent environment. Only ordinary runtime fields such as PATH/HOME/TEMP/locale/proxy are inherited automatically.

Provider credentials or provider-specific settings must be passed explicitly through `JsonProcessModelClientConfig.env`.

The Level 2 real-model validation supports an allowlist-style handoff using:

```text
GOVERNANCE_MODEL_BRIDGE_ENV_NAMES=NAME1,NAME2,...
```

Only named variables are copied into the model wrapper process.

Provider-specific wrappers are intentionally outside Public Governance Runtime and outside Tool Plugin System.
