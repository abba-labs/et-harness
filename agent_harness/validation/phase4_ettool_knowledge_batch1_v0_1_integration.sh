#!/usr/bin/env bash
set -euo pipefail

CORDIS_VERSION="${CORDIS_VERSION:-4.0.1}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${PHASE4_ETTOOL_KNOWLEDGE_BATCH1_WORK_DIR:-$(mktemp -d)}"
SMOKE_DIR="$WORK_DIR/cordis-smoke"
PACK_DIR="$WORK_DIR/packs"
RUNTIME_ROOT="$WORK_DIR/runtime"
source "$ROOT_DIR/agent_harness/validation/lib/common_runtime.sh"
trap 'rm -rf "$WORK_DIR"' EXIT
mkdir -p "$SMOKE_DIR" "$PACK_DIR" "$RUNTIME_ROOT"
export npm_config_registry="$NPM_REGISTRY"
export AGENT_HARNESS_STATE_ROOT="$RUNTIME_ROOT"

PROJECT_PLUGIN_ROOT="$ROOT_DIR/agent_harness/projects/et_tool"
KNOWLEDGE_ROOT="$PROJECT_PLUGIN_ROOT/knowledge"

echo '[0/5] ET-TOOL Knowledge Batch 1 static precheck'
test -f "$KNOWLEDGE_ROOT/001_library.md"
test -f "$KNOWLEDGE_ROOT/SOURCES.yaml"
test -f "$KNOWLEDGE_ROOT/VERIFICATIONS.jsonl"
grep -q '^# \[K001\] Managed Knowledge Shard K001$' "$KNOWLEDGE_ROOT/001_library.md"
[[ "$(grep -c '^## \[K001\.[0-9][0-9][0-9]\]' "$KNOWLEDGE_ROOT/001_library.md")" -eq 28 ]]
[[ "$(grep -c '^  - sourceId: SRC' "$KNOWLEDGE_ROOT/SOURCES.yaml")" -eq 9 ]]
[[ "$(wc -l < "$KNOWLEDGE_ROOT/VERIFICATIONS.jsonl")" -eq 28 ]]
echo '  28 Knowledge + 9 Sources + 28 Verifications = PASS'

echo '[1/5] Build Knowledge Manager / Project Contract / ET-TOOL Project'
for dir in project_contract governance_core public_plugins/project_manager public_plugins/knowledge_manager projects/et_tool; do
  npm_install_if_needed "$ROOT_DIR/agent_harness/$dir" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
  (cd "$ROOT_DIR/agent_harness/$dir" && npm test && npm run build)
done
(cd "$PROJECT_PLUGIN_ROOT" && npm pack --pack-destination "$PACK_DIR" >/dev/null)
PROJECT_TGZ="$(find "$PACK_DIR" -maxdepth 1 -name 'agent-harness-project-et-tool-*.tgz' -print -quit)"
test -n "$PROJECT_TGZ"
PACK_LIST="$WORK_DIR/batch1-package.list"
tar -tzf "$PROJECT_TGZ" > "$PACK_LIST"
for entry in package/knowledge/TAXONOMY.yaml package/knowledge/SOURCES.yaml package/knowledge/VERIFICATIONS.jsonl package/knowledge/001_library.md; do grep -Fxq "$entry" "$PACK_LIST"; done

echo '[2/5] Prepare real Cordis Runtime'
cd "$SMOKE_DIR"
npm init -y >/dev/null
npm pkg set type=module >/dev/null
npm_install_if_needed "$SMOKE_DIR" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS" \
  "@deepseek-ai/cordis@$CORDIS_VERSION" \
  "$ROOT_DIR/agent_harness/governance_core" \
  "$ROOT_DIR/agent_harness/project_contract" \
  "$ROOT_DIR/agent_harness/public_plugins/project_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/knowledge_manager" \
  "$PROJECT_TGZ"

echo '[3/5] Batch 1 source / verification / validation / promotion smoke'
cat > "$SMOKE_DIR/smoke.mjs" <<'EOF'
import { Context } from '@deepseek-ai/cordis'
import GovernanceCatalogService from '@agent-harness/governance-core'
import * as projectManagerPlugin from '@agent-harness/project-manager'
import * as knowledgePlugin from '@agent-harness/knowledge-manager'
import * as etToolProjectPlugin from '@agent-harness/project-et-tool'

const tick = () => new Promise(resolve => setTimeout(resolve, 0))
const assert = (condition, message) => { if (!condition) throw new Error(message) }
const ctx = new Context(); const fibers = []
fibers.push(ctx.plugin(GovernanceCatalogService)); await tick()
fibers.push(ctx.plugin(projectManagerPlugin)); await tick()
fibers.push(ctx.plugin(knowledgePlugin)); await tick()
const projectFiber = ctx.plugin(etToolProjectPlugin); await tick()
const knowledge = ctx.get('knowledgeManager')
const validation = ctx.get('knowledgeValidationPolicy')
assert(knowledge && validation, 'Knowledge services missing')

const snapshot = knowledge.refreshProject('et-tool')
assert(snapshot.libraryMode === 'library-v0.2', 'library-v0.2 required')
assert(snapshot.files.length === 1, `expected 1 Knowledge shard, got ${snapshot.files.length}`)
assert(snapshot.nodeCount === 29, `expected 29 nodes, got ${snapshot.nodeCount}`)
assert(snapshot.knowledgeCount === 28, `expected 28 leaves, got ${snapshot.knowledgeCount}`)
assert(snapshot.statusCounts.DEPRECATED === 0, 'Batch 1 must not contain DEPRECATED Knowledge')
assert(snapshot.statusCounts.CANDIDATE + snapshot.statusCounts.VALIDATED === 28, 'unexpected Batch 1 status mix')
assert(snapshot.warnings.length === 0, `unexpected warnings: ${snapshot.warnings.join('; ')}`)
const sources = knowledge.listProjectSources('et-tool')
assert(sources.length === 9, `expected 9 Sources, got ${sources.length}`)
for (let n = 1; n <= 9; n += 1) {
  const id = `SRC${String(n).padStart(6, '0')}`
  assert(sources.some(source => source.sourceId === id && source.status === 'ACTIVE'), `missing source ${id}`)
}

let promotedInSmoke = 0
let existingValidated = 0
for (let n = 1; n <= 28; n += 1) {
  const id = `K001.${String(n).padStart(3, '0')}`
  const uri = `knowledge://project/et-tool/${id}`
  const node = knowledge.getNode('et-tool', id)?.node
  assert(node?.isLeaf, `missing Knowledge leaf ${id}`)
  assert(node.status === 'CANDIDATE' || node.status === 'VALIDATED', `bad status for ${id}: ${node?.status}`)
  const evaluation = validation.evaluate(uri)
  assert(evaluation.distinctSupportCount === 1, `${id} must have exactly one distinct SUPPORT`)
  assert(evaluation.contradictCount === 0, `${id} has CONTRADICT evidence`)

  if (node.status === 'CANDIDATE') {
    assert(
      evaluation.decision === 'READY' && evaluation.targetStatus === 'VALIDATED',
      `${id} candidate is not READY for validation: ${evaluation.decision} ${evaluation.reasons.join('; ')}`,
    )
    const result = validation.promote(uri)
    assert(result.mutation.status === 'VALIDATED', `promotion failed for ${id}`)
    promotedInSmoke += 1
  } else {
    assert(
      evaluation.decision === 'INSUFFICIENT' && evaluation.targetStatus === undefined,
      `${id} VALIDATED Knowledge must wait for scope-appropriate REAL_TEST Evidence: ${evaluation.decision} ${evaluation.reasons.join('; ')}`,
    )
    existingValidated += 1
  }
}
assert(existingValidated === snapshot.statusCounts.VALIDATED, 'existing VALIDATED count drifted during evaluation')
for (let n = 1; n <= 28; n += 1) {
  const id = `K001.${String(n).padStart(3, '0')}`
  assert(knowledge.getNode('et-tool', id)?.node.status === 'VALIDATED', `${id} not VALIDATED after smoke promotion`)
}
assert(knowledge.searchKnowledge({ projectId: 'et-tool', query: 'progress sidecar' }).some(item => item.id === 'K001.017' || item.id === 'K001.020'), 'validated progress Knowledge routing failed')
assert(knowledge.searchKnowledge({ projectId: 'et-tool', query: 'release build framework' }).some(item => item.id === 'K001.025'), 'validated release Knowledge routing failed')
console.log(`  initial candidates=${snapshot.statusCounts.CANDIDATE} validated=${snapshot.statusCounts.VALIDATED}`)
console.log(`  candidate-ready=${promotedInSmoke}; existing-validated-awaiting-real-test=${existingValidated}; final validated=28`)
console.log('  Batch 1 Knowledge validation chain = PASS')

await projectFiber.dispose(); await tick()
for (let i = fibers.length - 1; i >= 0; i -= 1) { await fibers[i].dispose(); await tick() }
EOF
ET_TOOL_PROJECT_ROOT="$ROOT_DIR" node "$SMOKE_DIR/smoke.mjs"

echo '[4/5] Batch 1 Contract result'
printf '%s\n' 'PHASE4_ETTOOL_KNOWLEDGE_BATCH1_V0_1_INTEGRATION=PASS' 'ETTOOL_KNOWLEDGE_BATCH1_LEAVES=28' 'ETTOOL_KNOWLEDGE_BATCH1_SOURCES=9' 'ETTOOL_KNOWLEDGE_BATCH1_VERIFICATIONS=28' "CORDIS_VERSION=$CORDIS_VERSION"
echo '[5/5] DONE'
