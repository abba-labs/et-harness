# Shared Toolchain / Runtime Environment Validation Requirement V1

## Role and boundary

Role: Codex = independent Test Executor only.

Architecture/Repair Owner: ChatGPT.
Project Owner: user.

Candidate branch: `architecture/shared-toolchain-runtime-env-v0.1`.
The Test Executor MUST lock the exact remote HEAD at execution time and record the exact tested SHA.

This campaign validates public ET Harness infrastructure only. ATP remains the real validation project, but ATP-specific Architecture / Rules / Knowledge / Gates / Validation MUST NOT be modified to make this environment campaign pass.

## Primary acceptance statement

A clean ET Harness checkout or worktree MUST NOT require checkout-local `node_modules`.

If one machine-level Toolchain for the current Node/platform/package-lock already exists, every branch/worktree with the same dependency lock MUST reuse it without `npm install` / `npm ci`.

Source checkout location MUST NOT own or infer Runtime state/dependency storage.

Candidate build and candidate verification MUST NOT mutate the active Runtime pointer, current Gateway PID, persistent Runtime state, Ledger/Event Store, or stable release.

A v2 Runtime release MUST contain a bundled Gateway that is mechanically bound to its own Runtime release, so one process cannot mix Gateway code from release A with Runtime code from release B.

Activation and rollback MUST be explicit pointer operations and MUST remain separate from build/verification.

## Hard constraints for this machine

- DO NOT install or upgrade Node, Cordis, TypeScript, Rolldown, MCP SDK, Zod, YAML or other dependencies during this validation.
- First Toolchain preparation MUST use `prepare-toolchain.cmd --seed-only`.
- If no fully verified package-lock-compatible seed exists, STOP and report `ENVIRONMENT_SEED_UNAVAILABLE`; do not fall back to npm.
- Do not alter the stable active release/Gateway until source verification + candidate build + candidate isolated verification all PASS.
- Do not modify product source while testing.
- Do not modify ATP Project Plugin or public Framework to make a test pass.
- Do not create a second Runtime state owner, watcher, daemon, service, or alternate Gateway.
- Do not use historical PASS as current candidate PASS.
- Preserve exact before/after hashes for active pointer and relevant stable state.

## Baseline capture

Before any Toolchain preparation or candidate build, record:

1. tested repository SHA and clean worktree status;
2. current active-release pointer bytes + SHA256;
3. current active release manifest path, schema, source revision/signature, and artifact verification result;
4. current external Gateway PID, command line, `/health` result, and MCP direct health when available;
5. hashes/counts for existing persistent Runtime state directories;
6. current package.json/package-lock SHA256;
7. presence/absence of checkout-local `agent_harness/mcp_gateway_fast_track/node_modules`;
8. existing stable source worktree path from the active v1 release, if applicable.

No baseline action may stop/restart the Gateway.

## A. Checkout-independent Environment Root

Prove:

1. `ET_HARNESS_ENV_ROOT` is the authoritative machine environment root when configured.
2. Current migration fallback resolves the existing machine environment from the existing absolute Gateway release pointer without deriving it from the current repository parent path.
3. Two different source worktree paths resolve the exact same Node runtime root, Toolchains root, active-release pointer, persistent state root, cache and temp roots.
4. A relative explicit environment root fails closed.
5. Moving/creating a worktree does not create another environment/state tree adjacent to that worktree.

## B. Shared immutable Toolchain

Use the prescribed Node `v22.23.2`.

Run:

`prepare-toolchain.cmd --seed-only`

Expected on the current machine:

- package.json/package-lock are unchanged from the previously verified stable environment;
- a package-lock-compatible stable seed is found;
- preparation source is `verified-seed:<path>` or an already-valid shared Toolchain is `REUSED`;
- npm is NOT invoked;
- no checkout-local `node_modules` is created;
- the seed source is unmodified.

Mechanically prove:

1. Toolchain ID depends on Node version + platform/arch + package.json hash + package-lock hash, not repository path/branch.
2. Two separate worktrees with the same package/lock produce the same Toolchain ID.
3. Synthetic lock change produces a different Toolchain ID without altering the old Toolchain.
4. Toolchain manifest matches exact Node/platform/arch/package hashes.
5. Every direct pinned dependency version matches.
6. Every installed non-optional lockfile package exists and matches the exact lock version.
7. Missing platform-optional packages are permitted; installed optional packages must still match their locked version.
8. Corrupted/mismatched Toolchain directories fail closed and are not mutated in place.

## C. Source verification without checkout node_modules

Use a clean candidate checkout/worktree with no local `node_modules`.

Run `verify-environment.cmd`.

Expected:

- `SOURCE_ENVIRONMENT_VERIFIED`;
- checkoutNodeModulesRequired=false;
- shared Toolchain ID is reported;
- every Gateway/infrastructure `.mjs` under `src/` and `scripts/` passes fixed-Node `--check`;
- Runtime TypeScript verification passes using shared Toolchain paths;
- Gateway source regression tests pass using the shared Toolchain loader;
- active frozen Runtime behavior is NOT used as current candidate evidence.

After source verification, prove active pointer bytes, stable Gateway PID, and persistent stable state are unchanged.

## D. Candidate build is non-activating

Run `build-runtime.cmd` only after B/C PASS.

Expected candidate release schema: `et-harness.pure-mcp-runtime-release.v2`.

Prove:

1. build uses shared Toolchain, never checkout-local node_modules;
2. candidate release contains runtime, ATP plugin, deployment, bundled Gateway, release-local Runtime pointer, generated Gateway config, manifest and chunks;
3. manifest records exact source signature/revision/workspace deployment fingerprint/Toolchain ID/lock hash/dependency versions;
4. source signature is content-based and does not include absolute checkout path;
5. deployment fingerprint remains workspace-bound;
6. identical source in a second worktree preserves source signature and Toolchain ID but may have different deployment/release identity;
7. candidate build does NOT write active/previous pointers;
8. candidate build does NOT stop/start/change stable Gateway PID;
9. candidate build does NOT write stable Runtime state/Event Store/Context/Knowledge state.

Invalid existing candidate directories must fail closed rather than be overwritten.

## E. Candidate release self-integrity and isolated Runtime composition

Run `verify-candidate-runtime.cmd <candidate release.json>`.

Expected:

- current source/workspace/Toolchain identity matches candidate;
- dirty-source candidate is rejected;
- all artifact hashes pass;
- v2 release-local Runtime pointer targets that exact release's own `release.json`;
- bundled Gateway config targets the release-local pointer, NOT global active pointer;
- candidate Runtime composes against isolated temporary state;
- configured project resolves;
- Architecture Bootstrap returns valid `sha256:` fingerprint and non-empty roots;
- isolated state is removed and process environment restored;
- stable active pointer/PID/persistent state remain unchanged.

Negative controls:

1. release-local pointer targets another release => FAIL;
2. Gateway config points to global active pointer => FAIL;
3. tampered Runtime artifact => FAIL;
4. stale source signature => FAIL;
5. wrong workspace => FAIL;
6. wrong Toolchain ID => FAIL.

## F. Stable v1 migration / rollback compatibility

Before v2 activation, prove stable v1 release still verifies independently of current candidate checkout identity.

Only if Project Owner authorizes a controlled restart, prove legacy v1 can start using its recorded stable source/dependency path without candidate checkout node_modules.

This is rollback safety evidence, not candidate PASS evidence.

## G. Explicit activation boundary

DO NOT execute until B-F PASS and Project Owner / Architecture Owner authorize activation.

Run `activate-runtime.cmd <candidate release.json>`.

Prove:

1. candidate is re-verified at activation time;
2. source change after candidate verification blocks activation;
3. previous stable pointer is preserved before active changes;
4. active pointer changes to candidate;
5. activation does NOT silently restart Gateway;
6. running Gateway remains old release until separate controlled external refresh;
7. after refresh, command line points to release-bundled `gateway.mjs`, not checkout `src/gateway.mjs`;
8. bundled Gateway loads its own Runtime through release-local pointer;
9. direct MCP initialize/tools/list/health passes and exactly 8 public tools remain;
10. v2 running Gateway requires no checkout-local node_modules.

## H. Rollback

After authorized activation validation, stop candidate Gateway through approved external lifecycle and execute rollback.

Prove:

1. prior release restored active;
2. candidate retained as previous where applicable;
3. rollback needs no candidate checkout-local dependencies;
4. old stable v1 Gateway can start again;
5. `/health` and direct MCP pass;
6. persistent Runtime state remains one canonical tree.

Rollback failure is a release blocker.

## I. Cross-worktree proof

Use two clean worktrees at distinct absolute paths with the same package-lock. Neither may contain local `mcp_gateway_fast_track/node_modules`.

Prove same environment root, Toolchain ID and Node runtime; source verification succeeds from both; no install occurs; identical content source signatures match; no worktree-local state/cache/runtime tree is created.

## J. Business-layer non-regression

Diff attribution MUST confirm this environment repair changes only public MCP Gateway environment/build/release/launcher infrastructure plus tests/docs.

There must be no ATP task-classification semantic fix, no Context/Knowledge/Rule/Gate/Supervisor business change, and no dependency version change in this repair.

After authorized v2 activation, rerun executable Gateway/Project Admission/8-tool contract regressions.

## Required evidence

Produce at minimum:

- `FINAL_REPORT.md`
- `baseline.json`
- `environment_root.json`
- `toolchain.json`
- `source_verify.json`
- `candidate_build.json`
- `candidate_verify.json`
- `release_self_binding.json`
- `stable_compatibility.json`
- `activation.json` if authorized/executed
- `rollback.json` if activation executed
- `cross_worktree.json`
- `state_diffs.json`
- `negative_controls.json`
- `defect_backlog.md`
- raw command logs

Use only PASS / FAIL / NOT_EXECUTED / BLOCKED_BY_UPSTREAM / OBSERVABILITY_GAP. Always record first failing boundary and attribution.

## Final acceptance

Environment infrastructure is accepted only if mechanically true:

> A clean ET Harness branch/worktree with no local node_modules can reuse one immutable machine Toolchain, verify/build the current candidate without touching stable Runtime, run a self-contained v2 Gateway+Runtime after explicit activation, and rollback to prior stable; worktree path and branch changes do not create or require another dependency environment.

Only after this campaign passes should real ET6801 SRPWM module-behavior validation resume.
