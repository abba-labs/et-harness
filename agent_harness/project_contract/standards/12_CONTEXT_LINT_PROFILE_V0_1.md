# Context Lint Profile v0.1

> Profile ID: `context-lint-v0.1`  
> Parent Standard: `context-record-v0.1`  
> Purpose: define only deterministic machine checks. Semantic task judgment remains with Agent.

## ERROR — reject write

```text
EMPTY_TEXT
MULTILINE_TEXT
TEXT_TOO_LONG
CONFIRMED_WITHOUT_REF
CONFIRMED_UNCERTAIN
FACT_ASSUMPTION_COLLISION
```

Current hard limits:

```text
Goal                 <= 400 chars
Ledger entry         <= 300 chars
Plan / Next item     <= 220 chars
Progress field       <= 300 chars
Recent summary       <= 300 chars
Handle title         <= 120 chars
Handle summary       <= 220 chars
Reference            <= 500 chars
```

Confirmed rules:

```text
Confirmed must contain at least one Ref.
Confirmed must not contain obvious uncertainty markers such as:
可能 / 猜测 / 似乎 / 预计 / 大概 / 也许 / 怀疑
maybe / probably / likely / seem / suspect / assume
```

The same normalized statement must not appear in both `Confirmed` and `Assumptions`.

## WARNING — do not block Agent

```text
DUPLICATE_ENTRY
NON_STANDARD_REFERENCE
```

Unknown reference syntax is warning-only because Project/Tool extensions may introduce new stable URI forms.

## Guard timing

Context Manager must run Lint:

```text
before State write
before Context Frame build
before Handoff creation
```

Rejected writes must not change State version or partially persist invalid Context.

## Boundary

Context Lint does not decide:

```text
whether an Agent conclusion is actually true
whether a task plan is good
whether an assumption is reasonable
which Architecture / Rule / Knowledge should be selected
```

Those remain Agent responsibilities. Lint only prevents structurally unsafe Context from entering the governed Context State.
