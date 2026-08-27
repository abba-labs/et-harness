# Generic Model Governance Pilot v0.1

Level 2 test driver for Public Governance Runtime.

```text
Original business task
        ↓
GovernanceRuntime.openTurn()
        ↓
Automatic Context / A-R-K-G
        ↓
Generic governed model work
        ↓
GovernanceRuntime.observeWork(visible output)
        ↓
GovernanceRuntime.closeTurn()
        ↓
Automatic Semantic Reflection
        ↓
Scope classification + 8/8 Closure
        ↓
TURN_CLOSED
```

The driver never calls Context Manager, Knowledge Manager, Kernel Reflection, or Closure Manager directly.

## Two validation modes

`phase4a_public_governance_runtime_level2_model_v0_1.sh` supports:

### contract

Uses a deterministic fake JSON model process to prove the full adapter protocol and automatic governance chain in CI.

### real

Uses an external model bridge supplied through:

```text
MODEL_PILOT_MODE=real
GOVERNANCE_MODEL_BRIDGE_COMMAND=/absolute/or/PATH/executable
GOVERNANCE_MODEL_BRIDGE_ARGS_JSON=["arg1","arg2"]
GOVERNANCE_MODEL_BRIDGE_CLIENT_ID=my-model
GOVERNANCE_MODEL_BRIDGE_CWD=/optional/wrapper/cwd
GOVERNANCE_MODEL_BRIDGE_ENV_NAMES=VAR1,VAR2
```

Only the explicitly named `VAR1,VAR2` values are forwarded as provider-specific environment variables. The JSON Process Client does not copy arbitrary parent secrets.

The bridge can wrap any model provider. No DSH and no Tool Plugin are involved.

The real-mode business task is deliberately self-contained in a synthetic Project so Level 2 measures model/governance integration rather than filesystem/Drive/Web tooling.

A real-model PASS does not require a predetermined Knowledge candidate; `NONE` is valid. It does require non-empty visible work output, automatic Reflection, an explicit valid Knowledge scope decision, 8/8 Closure COMPLETE and `TURN_CLOSED`.
