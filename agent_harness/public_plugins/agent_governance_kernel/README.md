# Public Agent Governance Kernel v0.1 — Step 3

This package is the project-independent foundation for mandatory Agent lifecycle governance.

Implemented through Step 3:

- Agent / Task / Turn lifecycle contracts;
- `UNBOUND` / `BOUND(projectId)` project binding semantics;
- persistent Turn Journal records;
- `OPEN -> SEALED -> CLOSURE_PENDING -> CLOSED` state enforcement;
- atomic Journal writes and fail-closed unresolved-Turn guard;
- Unified Turn Reflection as a mandatory pre-closure stage;
- one Reflection Provider invocation per sealed Turn input, with persisted idempotent result;
- explicit reflection coverage for Context, Knowledge, Experience, Architecture, Rules, Evidence, Working Set and Obligations;
- common semantic scope decisions `NONE / PROJECT / PUBLIC / BOTH`;
- deterministic validation that `UNBOUND` Turns cannot create PROJECT/BOTH candidates;
- fixed Kernel Mandatory Closure Module set;
- Closure Module registration that cannot downgrade or extend the mandatory public set;
- Closure Coordinator that runs only after persisted Unified Reflection;
- fail-closed preflight when any Mandatory Closure Module is missing;
- persisted Turn Closure Receipt with per-module writes/candidate/evidence refs;
- per-module idempotency keys and replay that reuses successful module receipts while retrying failed modules;
- `BLOCKED`, `FAILED` or missing Mandatory modules leave the Turn `CLOSURE_PENDING`;
- only a COMPLETE persisted Closure Receipt can advance the Turn to `CLOSED`;
- recovery path for a crash after COMPLETE Receipt persistence but before Journal close.

## Fixed Mandatory Closure Module IDs

```text
context-closure
knowledge-closure
experience-memory-closure
architecture-closure
rules-closure
evidence-state-closure
working-set-closure
obligation-gate-reconcile
```

Step 3 establishes the coordinator, registry, idempotency and receipt/replay mechanics only. It still does **not** wire these module IDs to Context Manager, Knowledge Manager, Experience / Memory Manager, Architecture, Rules, Evidence / State, Working Set or Gate implementations. Those deterministic Manager adapters are the next Kernel step.

Hard boundaries:

- the Coordinator performs no semantic judgment; Unified Reflection remains the single Agent semantic judgment for the Turn;
- project code cannot disable, downgrade or redefine the fixed mandatory module set;
- project identity is not required to govern a Turn; `UNBOUND` Turns still require Reflection and Closure;
- no module may make the Turn `CLOSED` by itself; the Coordinator owns the final close decision.
