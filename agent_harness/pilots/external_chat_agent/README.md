# External Chat Agent Governance Pilot v0.1

This Pilot validates the Public Governance Runtime against an **external conversational Agent** without using OpenAI API, DeepSeek API, DSH lifecycle events, or any other Agent Harness lifecycle integration.

The external Agent for the first real Pilot is the current ChatGPT conversation. A private GitHub Issue is used only as a mailbox.

## Purpose

Prove this boundary:

```text
ordinary business task
  ↓
Public Governance Runtime
  ↓
automatic Project + Context + Architecture / Rules / Knowledge / Gates
  ↓
Generic Model WORK request
  ↓
GitHub Issue mailbox
  ↓
external conversational Agent
  ↓
visible work response
  ↓
Runtime observation
  ↓
Runtime automatically triggers GOVERNANCE_REFLECTION
  ↓
GitHub Issue mailbox
  ↓
external conversational Agent semantic response
  ↓
Kernel validation
  ↓
8/8 Mandatory Closure
  ↓
TURN_CLOSED
```

## Hard boundary

`GitHubIssueModelClient` is a transport only. It MUST NOT:

- resolve a Project;
- create or update Context;
- select Architecture resources;
- select Rules;
- search or write Knowledge;
- select Gates;
- trigger Reflection itself;
- choose semantic scope;
- execute Closure;
- synthesize a PASS/BLOCK decision.

It receives the existing `GenericModelGenerateRequest` and transports it without semantic transformation. It returns only the external Agent's response.

The Public Governance Runtime remains the sole owner of governance lifecycle semantics.

## Mailbox protocol

Normal Framework request comment:

```text
<!-- ET_TOOL_EXTERNAL_AGENT_REQUEST:<requestId> -->
{ GenericModelGenerateRequest JSON }
```

If the UTF-8 request would exceed the safe single-comment transport limit, the bridge splits only the serialized transport payload into ordered comments:

```text
<!-- ET_TOOL_EXTERNAL_AGENT_REQUEST_PART:<requestId>:1/2 -->
{ first UTF-8 slice ...
```

```text
<!-- ET_TOOL_EXTERNAL_AGENT_REQUEST_PART:<requestId>:2/2 -->
... second UTF-8 slice }
```

The external Agent reconstructs the original request by concatenating the part bodies in numeric order after the marker line. Chunking MUST NOT remove, summarize, reorder, or reinterpret any request field. UTF-8 characters are never split across chunk boundaries.

External Agent response comment:

```text
<!-- ET_TOOL_EXTERNAL_AGENT_RESPONSE:<requestId> -->
{
  "contractVersion": "0.1",
  "requestId": "...",
  "outputText": "..."
}
```

or, for Reflection:

```text
<!-- ET_TOOL_EXTERNAL_AGENT_RESPONSE:<requestId> -->
{
  "contractVersion": "0.1",
  "requestId": "...",
  "outputJson": { ...TurnReflectionResult... }
}
```

## Acceptance

PASS requires mechanical evidence that:

- the business task contains no governance hints;
- exactly two external-Agent calls occur in order: `WORK`, then `GOVERNANCE_REFLECTION`;
- ET-TOOL Project is bound automatically;
- Architecture, Rules, Knowledge and Gates are routed automatically;
- TASK_INPUT and ASSISTANT_MESSAGE Observations exist;
- the Runtime, not the Agent task text, triggers Reflection;
- all 8 fixed Mandatory Closure receipts are `APPLIED` or `NO_CHANGE`;
- aggregate Closure is `COMPLETE`;
- Kernel Journal is `CLOSED`.

Agent answer quality is not the acceptance criterion. Framework control is.
