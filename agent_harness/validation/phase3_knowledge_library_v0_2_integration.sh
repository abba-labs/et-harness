#!/usr/bin/env bash
set -euo pipefail

NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${KNOWLEDGE_LIBRARY_V02_WORK_DIR:-$(mktemp -d)}"
LIB_DIR="$WORK_DIR/knowledge"

source "$ROOT_DIR/agent_harness/validation/lib/common_runtime.sh"
trap 'rm -rf "$WORK_DIR"' EXIT
mkdir -p "$LIB_DIR"

assert_contains() {
  local pattern="$1"
  local file="$2"
  local label="$3"
  if ! grep -q -- "$pattern" "$file"; then
    echo "ASSERT_FAIL: $label" >&2
    echo "pattern=$pattern" >&2
    echo "file=$file" >&2
    sed -n '1,200p' "$file" >&2 || true
    exit 1
  fi
}

assert_file() {
  local file="$1"
  local label="$2"
  if [[ ! -f "$file" ]]; then
    echo "ASSERT_FAIL: $label" >&2
    echo "missing_file=$file" >&2
    exit 1
  fi
}

echo '[0/8] Build and unit-test Knowledge Library dependencies'
npm_install_if_needed "$ROOT_DIR/agent_harness/project_contract" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
(cd "$ROOT_DIR/agent_harness/project_contract" && npm test && npm run build)

npm_install_if_needed "$ROOT_DIR/agent_harness/governance_core" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
(cd "$ROOT_DIR/agent_harness/governance_core" && npm test && npm run build)

npm_install_if_needed "$ROOT_DIR/agent_harness/public_plugins/project_manager" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
(cd "$ROOT_DIR/agent_harness/public_plugins/project_manager" && npm test && npm run build)

KNOWLEDGE_MANAGER_DIR="$ROOT_DIR/agent_harness/public_plugins/knowledge_manager"
npm_install_if_needed "$KNOWLEDGE_MANAGER_DIR" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
(cd "$KNOWLEDGE_MANAGER_DIR" && npm test && npm run build)
echo '  package build/test = PASS'

cat > "$LIB_DIR/TAXONOMY.yaml" <<'EOF'
standard: knowledge-library-v0.2
categories:
  - id: C010
    title: Knowledge
    aliases: [knowledge]
    children:
      - id: C010.010
        title: Chips
        aliases: [chip]
        children:
          - id: C010.010.010
            title: DMA
            aliases: [dmac]
  - id: C020
    title: Experience
    aliases: [experience]
    children:
      - id: C020.010
        title: Debug
        aliases: [debug]
EOF

cat > "$LIB_DIR/010_platform.md" <<'EOF'
# [K010] Platform Knowledge

## [K010.010] DMA

### [K010.010.010] DMA DTCM Access
Status: VALIDATED
Category: C010.010.010
Fact: DMA master cannot directly access the current DTCM address space.
Scope: dma dtcm chip
Provenance: SRC-001
Tags: [dma, dtcm]
Refs: [K010.020.010]

## [K010.020] Debug

### [K010.020.010] DMA Debug Method
Status: VALIDATED
Category: C020.010
Fact: Check the DMA bus-visible address map before debugging transfer failures.
Scope: dma debug
Provenance: TASK-003
Tags: [dma, debug]
Refs: [K010.010.010]
EOF

CLI="$ROOT_DIR/agent_harness/public_plugins/knowledge_manager/dist/cli.js"

echo '[1/8] Reindex, tree, search, get and related'
node "$CLI" reindex "$LIB_DIR" > "$WORK_DIR/reindex.json"
assert_contains '"reindexed": true' "$WORK_DIR/reindex.json" 'reindex result'
assert_contains 'AUTO GENERATED — DO NOT EDIT' "$LIB_DIR/00_INDEX.md" 'generated index marker'
assert_contains '\[C010.010.010\] DMA' "$LIB_DIR/00_INDEX.md" 'generated taxonomy tree'

node "$CLI" tree "$LIB_DIR" > "$WORK_DIR/tree.txt"
assert_contains '\[C010.010.010\] DMA' "$WORK_DIR/tree.txt" 'tree output'

node "$CLI" search "$LIB_DIR" 'chip dmac dtcm' --category C010 > "$WORK_DIR/search.json"
assert_contains 'K010.010.010' "$WORK_DIR/search.json" 'search output'

node "$CLI" get "$LIB_DIR" K010.010.010 > "$WORK_DIR/get.json"
assert_contains 'DMA DTCM Access' "$WORK_DIR/get.json" 'get output'

node "$CLI" related "$LIB_DIR" K010.010.010 > "$WORK_DIR/related.json"
assert_contains 'K010.020.010' "$WORK_DIR/related.json" 'related output'
echo '  navigation/read path = PASS'

echo '[2/8] Taxonomy mutation commands'
node "$CLI" category-add "$LIB_DIR" --parent C010 --title Tools --aliases tool > "$WORK_DIR/category-add.json"
assert_contains 'C010.020' "$WORK_DIR/category-add.json" 'category-add output'
node "$CLI" category-rename "$LIB_DIR" C010.020 --title 'Tool Knowledge' --aliases tool,utility > "$WORK_DIR/category-rename.json"
assert_contains 'C010.020' "$WORK_DIR/category-rename.json" 'category-rename output'
node "$CLI" tree "$LIB_DIR" > "$WORK_DIR/tree-after-category.txt"
assert_contains '\[C010.020\] Tool Knowledge' "$WORK_DIR/tree-after-category.txt" 'renamed category tree'
echo '  taxonomy mutation = PASS'

echo '[3/8] Candidate contribution and managed shard allocation'
node "$CLI" add "$LIB_DIR" \
  --category C010.020 \
  --title 'Build Tool Fact' \
  --fact 'The build command resolves the project root before invoking the compiler.' \
  --provenance SRC-TOOL-001 \
  --tags build,tool > "$WORK_DIR/add.json"
assert_contains 'K001.001' "$WORK_DIR/add.json" 'candidate K-ID allocation'
assert_contains '"status": "CANDIDATE"' "$WORK_DIR/add.json" 'candidate status'
assert_file "$LIB_DIR/001_library.md" 'managed shard creation'
assert_contains '| K001 |' "$LIB_DIR/00_INDEX.md" 'managed shard generated index entry'
assert_contains '- CANDIDATE: 1' "$LIB_DIR/00_INDEX.md" 'candidate status summary'
echo '  candidate contribution = PASS'

echo '[4/8] Duplicate fact rejection'
if node "$CLI" add "$LIB_DIR" \
  --category C020.010 \
  --title Duplicate \
  --fact 'The build command resolves the project root before invoking the compiler!' \
  --provenance SRC-DUP > "$WORK_DIR/duplicate.json" 2>&1; then
  echo 'ASSERT_FAIL: duplicate knowledge unexpectedly accepted' >&2
  exit 1
fi
assert_contains '重复 Knowledge Fact: K001.001' "$WORK_DIR/duplicate.json" 'duplicate rejection reason'
echo '  duplicate rejection = PASS'

echo '[5/8] Stable K-ID reclassification'
node "$CLI" reclassify "$LIB_DIR" K001.001 --category C020.010 > "$WORK_DIR/reclassify.json"
assert_contains 'K001.001' "$WORK_DIR/reclassify.json" 'reclassify K-ID stability'
assert_contains 'C020.010' "$WORK_DIR/reclassify.json" 'reclassify category output'
assert_contains 'Category: C020.010' "$LIB_DIR/001_library.md" 'reclassified shard content'
echo '  reclassification = PASS'

echo '[6/8] Empty category deprecation'
node "$CLI" category-deprecate "$LIB_DIR" C010.020 > "$WORK_DIR/category-deprecate.json"
assert_contains '"status": "DEPRECATED"' "$WORK_DIR/category-deprecate.json" 'category deprecation status'
echo '  category deprecation = PASS'

echo '[7/8] Knowledge deprecation and final validation'
node "$CLI" deprecate "$LIB_DIR" K001.001 > "$WORK_DIR/deprecate.json"
assert_contains '"status": "DEPRECATED"' "$WORK_DIR/deprecate.json" 'knowledge deprecation output'
assert_contains 'Status: DEPRECATED' "$LIB_DIR/001_library.md" 'deprecated shard content'
assert_contains '| K001 |' "$LIB_DIR/00_INDEX.md" 'managed shard retained after deprecation'
assert_contains '- DEPRECATED: 1' "$LIB_DIR/00_INDEX.md" 'deprecated status summary'

node "$CLI" validate "$LIB_DIR" > "$WORK_DIR/final-validate.json"
assert_contains '"valid": true' "$WORK_DIR/final-validate.json" 'final validation result'
echo '  deprecation/final validation = PASS'

printf '%s\n' \
  'PHASE3_KNOWLEDGE_LIBRARY_V0_2_INTEGRATION=PASS' \
  "KNOWLEDGE_ROOT=$LIB_DIR"
