# Round 3 P0 Post-repair Environment and Regression Evidence

## Bound source and release

- Tested Gateway/Runtime source HEAD and ATP project revision: `1f7e317219f39a2096e3201ddbea51513d47bf91`.
- Repair baseline: `ef31b59637937b96d4c3a152f650aa7de999b2f3`.
- Frozen release: `D:\lihuan\vibe_code\codex\et_harness_env\state\pure-mcp-fast-track\releases\6ea5d462630eb5186076`.
- Frozen source signature: `8a1e3c292a27720d99d0eec5e9cec54194bab41426a525e52b8ce6bf442ab7be`.
- Pinned runtime: Node `v22.23.2` on D drive.
- No dependency installation or environment preparation was performed.

The frozen release metadata records the pre-commit freeze point `e16b764d7f86178a144ad8f1ecfa1005f238c59c` with `sourceDirty=true`. The source signature binds the frozen content that was later committed, and the deterministic verification matched that content rather than trusting the revision label alone.

## Deterministic and safety verification

- `freeze-runtime -> verify-environment`: `22 PASS / 0 FAIL`.
- Real frozen Runtime + real ATP Project Plugin wiring: `PASS`.
- Ordinary direct `VALIDATION_RESULT` remains untrusted: `PASS`.
- Runtime-owned checkpoint advances matching Validation obligations: `PASS`.
- Execution Supervisor `trust-boundary-regressions` and `trusted-execution-replay`: `2 files / 15 tests PASS`.
- Evidence-only Task Context route validation: `PASS`.
- Task Context governance regression after adding the bounded evidence route: `35 tests PASS`.

## Gateway and Desktop lifecycle

- External Gateway PID: `22000`.
- Executable: pinned D-drive Node `v22.23.2`.
- `GET /health`: HTTP 200 / `UP`.
- PID before Codex Desktop restart: `22000`.
- PID after Codex Desktop restart: `22000`.
- Desktop reconnected without restarting Gateway: `PASS`.
- All eight public MCP tools visible in Codex Desktop: `PASS`.
- Internal trusted-span admission is not exposed as an MCP tool: `PASS`.

## Scope and truthfulness

- Pure MCP remains `AUDIT`; no ENFORCE claim was made.
- Protected/out-of-scope preflight was blocked and no forbidden file was created.
- Software, FPGA and HIL execution for the eTimer documents was `NOT_EXECUTED`; none is represented as PASS.
- No Supervisor, Ledger, ATP rule, WRITE_SCOPE, Closure, Node/npm or environment script was modified during this verification batch.
