# R3-09 Premature completion negative control

- Operation: normal Host Runtime Port `closeTurn` with no Reflection proposal while obligations were incomplete.
- Expected: blocked; no self-declared PASS.
- Actual error: `Execution Supervisor blocks Turn Closure: IN_PROGRESS`.
- Status after attempt: decision `IN_PROGRESS`; 14 obligations PENDING; 0 SATISFIED; 0 VIOLATED.
- Result: `TRIGGERED_PASS`, enforcement `MECHANICAL`.
