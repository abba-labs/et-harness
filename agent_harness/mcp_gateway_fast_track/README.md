# ET Harness MCP Gateway Fast Track

Thin Streamable HTTP MCP transport for the existing ET Harness Governance Runtime.

The public MCP surface remains the bounded eight-tool contract:

- `harness_health`
- `harness_begin`
- `harness_status`
- `harness_observe`
- `harness_preflight`
- `harness_complete`
- `harness_read_required`
- `harness_checkpoint`

The fixed production endpoint is `http://127.0.0.1:8765/mcp`.

## Machine environment ownership

Source branches/worktrees do **not** own Node dependencies, Runtime state, cache, or the active release.

`ET_HARNESS_ENV_ROOT` is the machine-level environment owner. Configure it once for future shells when needed:

```cmd
scripts\configure-machine-environment.cmd D:\path\to\et_harness_env
```

During migration, the command resolver can recover the existing environment root from the already-committed absolute Gateway release pointer. New worktrees must not create their own adjacent Runtime/state/dependency trees.

## Shared immutable Toolchain

`package.json` and `package-lock.json` remain the source-controlled environment definition. Actual `node_modules` live once under:

```text
%ET_HARNESS_ENV_ROOT%\toolchains\<toolchain-id>\node_modules
```

The Toolchain ID is content-addressed by Node version, platform/arch, package.json, and package-lock.json. Branches with the same lock reuse the same Toolchain.

On the current migration machine, prefer the already-verified stable dependency tree without network/install churn:

```cmd
scripts\prepare-toolchain.cmd --seed-only
```

If no compatible seed exists, seed-only mode fails closed and does not run npm. On a genuinely new machine or after an intentional dependency-lock change, `scripts\prepare-toolchain.cmd` may be run once to materialize the new Toolchain.

No checkout-local `node_modules` is required afterward.

## Candidate release workflow

Build, verify, activation, Gateway refresh, and rollback are separate authority boundaries:

```cmd
scripts\verify-environment.cmd
scripts\build-runtime.cmd
scripts\verify-candidate-runtime.cmd <candidate-release.json>
scripts\activate-runtime.cmd <candidate-release.json>
scripts\refresh-gateway.cmd
```

`verify-environment.cmd` uses the shared Toolchain, syntax-checks Gateway infrastructure modules, type-checks Runtime source, and runs source regressions without treating an old active Runtime as current candidate evidence.

`build-runtime.cmd` creates a content-addressed **candidate** release only. It does not change the active release or restart the Gateway.

`verify-candidate-runtime.cmd` verifies source/workspace/Toolchain identity and artifact integrity, then composes the candidate Runtime against isolated temporary state. Stable Runtime state and the active pointer are not used as candidate state.

`activate-runtime.cmd` is the explicit active-pointer authority. It preserves the previous release pointer and does not restart the Gateway.

`refresh-gateway.cmd` only verifies and restarts the already-active release. It does not build or activate anything.

Restore the prior release explicitly with:

```cmd
scripts\rollback-runtime.cmd
```

## Self-contained v2 releases

A v2 release contains the Runtime bundle, Project Plugin bundle, bundled Gateway, deployment, generated Gateway config, and a release-local Runtime pointer.

The bundled Gateway is mechanically bound to its own release-local Runtime pointer. Changing the global active pointer cannot make a running Gateway from release A lazily load Runtime B. A controlled Gateway restart is required to begin serving a newly activated release.

Legacy v1 releases remain verifiable for migration/rollback. When a legacy release is active, its recorded stable source/dependency path may still be used to restart that legacy Gateway.

## External Gateway lifecycle

Start the Gateway by double-clicking `start-et-harness-gateway.cmd` in Windows Explorer or from an independent terminal. The launcher fails closed when Codex Desktop, a Codex hook/plugin, or another disallowed process appears in its ancestor chain.

After a reviewed launcher revision is explicitly installed with
`scripts\install-machine-launcher.cmd`, the only stable lifecycle entry is:

```text
<ET_HARNESS_ENV_ROOT>\bin\et-harness.cmd start
<ET_HARNESS_ENV_ROOT>\bin\et-harness.cmd stop
<ET_HARNESS_ENV_ROOT>\bin\et-harness.cmd status
<ET_HARNESS_ENV_ROOT>\bin\et-harness.cmd health
```

The installed launcher derives the Environment Root from its own `bin` location,
uses the fixed machine Node, and contains the complete release verification and
process-control implementation using only Node built-ins. It does not import or
execute lifecycle code from a Git checkout. Editing or switching a branch cannot
change the installed launcher; only an explicit installer run can update it.

Useful commands:

```cmd
start-et-harness-gateway.cmd
scripts\smoke.cmd
scripts\stop-gateway.cmd
```

`GET http://127.0.0.1:8765/health` reports the Gateway process itself. Direct MCP smoke should be used after an authorized external refresh to prove the active release and eight-tool surface.
