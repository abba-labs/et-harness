# ET Harness Canonical Mainline Baseline V0.1

Date: 2026-09-02

## Canonical development baseline

Long-term development branch:

`development/et-harness-mainline-v0.1`

Baseline before this policy commit:

`fee133c984c098407859a053678db62334c22f20`

This baseline includes the accepted Project Admission line, Governance P0 continuity/closure repairs, Context continuity, Knowledge trigger contract, Governance Decision Receipt, shared Toolchain / Runtime v2 environment, and the machine-local Launcher freeze evidence.

Machine environment ownership is external to Git:

`D:\lihuan\vibe_code\codex\et_harness_env`

Git branch/worktree changes MUST NOT implicitly modify Node, Toolchain, active Runtime, Machine Launcher, Runtime State, Event Store or Gateway lifecycle. Machine environment changes remain explicit through approved launcher install or Runtime build/verify/activate flows.

## Branch policy

1. All new product development starts from `development/et-harness-mainline-v0.1`.
2. Real validation campaigns use short-lived `validation/<campaign>` branches created from the exact mainline HEAD.
3. Repair branches use short-lived `fix/<defect>` or `architecture/<bounded-change>` branches and are retired after their accepted result is incorporated into mainline.
4. Do not create `work`, `work2`, `final`, `finalize`, `stage1`, `stage1a`, `hotfix` chains as long-lived remote branches.
5. Evidence belongs in the repository test campaign/evidence paths; evidence-only branch names are not required after evidence is anchored in mainline or the archive branch.
6. Historical divergent branch ancestry is retained only through:

   `archive/pre-mainline-history-2026-09-02`

   The archive branch is read-only history. Its legacy trees MUST NOT be merged back into active development wholesale.
7. `main` remains the repository default/legacy branch until a separate explicit promotion decision. Do not silently force-update it during validation work.

## Current active validation line

`validation/et6801-srpwm-behavioral-v0.1`

It must track the exact canonical mainline baseline at campaign start. Product fixes discovered during validation are made on bounded repair branches, mechanically revalidated, then incorporated into mainline before the next campaign baseline is cut.

## Deletion safety

Legacy remote branches may be deleted after verifying they are represented by the archive ancestry anchor. Deleting Git branches does not delete or change the machine-local ET Harness environment.

## Historical assets

Some old divergent branches contain superseded experiments, test evidence, or project-specific artifacts such as early ATP and IPCM analysis work. They are intentionally preserved through the archive ancestry anchor rather than merged wholesale into the canonical product tree.
