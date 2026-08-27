#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: freeze_level2_runtime_artifact.py <validation-script>")

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

anchor = 'done\n\ncat > "$PROJECT_ROOT/architecture/00_INDEX.md" <<\'EOF\'\n'
insert = (
    'done\n\n'
    'RUNTIME_PACKAGE_DIR="$WORK_DIR/runtime-package"\n'
    'mkdir -p "$RUNTIME_PACKAGE_DIR"\n'
    'RUNTIME_TARBALL_NAME="$(cd "$ROOT_DIR/agent_harness/public_plugins/governance_runtime" '
    '&& npm pack --silent --pack-destination "$RUNTIME_PACKAGE_DIR")"\n'
    'GOVERNANCE_RUNTIME_TARBALL="$RUNTIME_PACKAGE_DIR/$RUNTIME_TARBALL_NAME"\n\n'
    'cat > "$PROJECT_ROOT/architecture/00_INDEX.md" <<\'EOF\'\n'
)
if text.count(anchor) != 1:
    raise SystemExit("Level2 validation script package-loop anchor mismatch")
text = text.replace(anchor, insert, 1)

runtime_dir = '  "$ROOT_DIR/agent_harness/public_plugins/governance_runtime" \\\n'
runtime_tar = '  "$GOVERNANCE_RUNTIME_TARBALL" \\\n'
if text.count(runtime_dir) != 1:
    raise SystemExit("Level2 validation script Runtime install anchor mismatch")
text = text.replace(runtime_dir, runtime_tar, 1)

smoke_anchor = (
    '  "$ROOT_DIR/agent_harness/pilots/generic_model"\n\n'
    'cat > "$SMOKE_DIR/smoke.mjs" <<\'EOF\'\n'
)
smoke_insert = (
    '  "$ROOT_DIR/agent_harness/pilots/generic_model"\n\n'
    'SOURCE_RUNTIME="$ROOT_DIR/agent_harness/public_plugins/governance_runtime/dist/service.js"\n'
    'INSTALLED_RUNTIME="$SMOKE_DIR/node_modules/@agent-harness/governance-runtime/dist/service.js"\n'
    'cmp "$SOURCE_RUNTIME" "$INSTALLED_RUNTIME"\n'
    'grep -q \'requireOpenJournal\' "$INSTALLED_RUNTIME"\n'
    'if grep -q \'requireLatestTurnJournal\' "$INSTALLED_RUNTIME"; then\n'
    '  echo \'Frozen Runtime artifact still contains stale requireLatestTurnJournal\' >&2\n'
    '  exit 1\n'
    'fi\n'
    'echo \'LEVEL2_MODEL_RUNTIME_ARTIFACT_FROZEN=PASS\'\n\n'
    'cat > "$SMOKE_DIR/smoke.mjs" <<\'EOF\'\n'
)
if text.count(smoke_anchor) != 1:
    raise SystemExit("Level2 validation script smoke install anchor mismatch")
text = text.replace(smoke_anchor, smoke_insert, 1)

path.write_text(text, encoding="utf-8")
