#!/usr/bin/env bash
set -euo pipefail

CORDIS_VERSION="${CORDIS_VERSION:-4.0.1}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${PHASE4_ETTOOL_KNOWLEDGE_WORK_DIR:-$(mktemp -d)}"
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

echo '[0/5] ET-TOOL Knowledge Taxonomy v0.1 static precheck'
test -f "$KNOWLEDGE_ROOT/TAXONOMY.yaml"
test -f "$KNOWLEDGE_ROOT/SOURCES.yaml"
grep -q '^standard: knowledge-library-v0.2$' "$KNOWLEDGE_ROOT/TAXONOMY.yaml"
grep -q '^standard: knowledge-source-registry-v0.1$' "$KNOWLEDGE_ROOT/SOURCES.yaml"
for id in C010 C020 C030 C040 C050 C060 C070 C080 C090; do grep -q "id: $id" "$KNOWLEDGE_ROOT/TAXONOMY.yaml"; done
echo '  taxonomy + Source Registry interface = PASS'

echo '[1/5] Build Knowledge Manager / Project Contract / ET-TOOL Project'
for dir in project_contract governance_core public_plugins/project_manager public_plugins/knowledge_manager projects/et_tool; do
  npm_install_if_needed "$ROOT_DIR/agent_harness/$dir" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
  (cd "$ROOT_DIR/agent_harness/$dir" && npm test && npm run build)
done
(cd "$PROJECT_PLUGIN_ROOT" && npm pack --pack-destination "$PACK_DIR" >/dev/null)
PROJECT_TGZ="$(find "$PACK_DIR" -maxdepth 1 -name 'agent-harness-project-et-tool-*.tgz' -print -quit)"
test -n "$PROJECT_TGZ"
PACK_LIST="$WORK_DIR/taxonomy-package.list"
tar -tzf "$PROJECT_TGZ" > "$PACK_LIST"
grep -Fxq 'package/knowledge/TAXONOMY.yaml' "$PACK_LIST"
grep -Fxq 'package/knowledge/SOURCES.yaml' "$PACK_LIST"

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

echo '[3/5] Knowledge taxonomy admission smoke'
cat > "$SMOKE_DIR/smoke.mjs" <<'EOF'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { Context } from '@deepseek-ai/cordis'
import GovernanceCatalogService from '@agent-harness/governance-core'
import * as projectManagerPlugin from '@agent-harness/project-manager'
import * as knowledgePlugin from '@agent-harness/knowledge-manager'
import * as etToolProjectPlugin from '@agent-harness/project-et-tool'

const tick = () => new Promise(resolve => setTimeout(resolve, 0))
const assert = (condition, message) => { if (!condition) throw new Error(message) }
const root = process.env.ET_TOOL_PROJECT_ROOT
const ctx = new Context()
const fibers = []
fibers.push(ctx.plugin(GovernanceCatalogService)); await tick()
fibers.push(ctx.plugin(projectManagerPlugin)); await tick()
fibers.push(ctx.plugin(knowledgePlugin)); await tick()
const projectFiber = ctx.plugin(etToolProjectPlugin); await tick()
const pm = ctx.get('projectManager')
const knowledge = ctx.get('knowledgeManager')
assert(pm && knowledge, 'Knowledge services missing')

const snapshot = knowledge.refreshProject('et-tool')
assert(snapshot.state === 'ready', 'ET-TOOL Knowledge must be READY')
assert(snapshot.libraryMode === 'library-v0.2', `unexpected library mode: ${snapshot.libraryMode}`)
assert(snapshot.warnings.length === 0, `unexpected warnings: ${snapshot.warnings.join('; ')}`)
const taxonomy = knowledge.getTaxonomy('et-tool')
const expectedRoots = ['C010','C020','C030','C040','C050','C060','C070','C080','C090']
assert(taxonomy && JSON.stringify(taxonomy.roots) === JSON.stringify(expectedRoots), 'taxonomy roots changed')
const stats = knowledge.getLibraryStats('et-tool')
assert(stats.categoryCount === 45, `expected 45 categories, got ${stats.categoryCount}`)
for (const id of ['C010.010','C010.020','C010.030','C010.040','C020.060','C040.030','C050.010','C060.010','C070.030','C080.010','C090.040']) {
  assert(taxonomy.categories[id]?.status === 'ACTIVE', `category missing/inactive: ${id}`)
}
const validation = knowledge.validateProjectLibrary('et-tool')
assert(validation.valid, `library validation failed: ${validation.errors.join('; ')}`)
const knowledgeRoot = pm.getResourcePath('et-tool', 'knowledge')
const generated = readFileSync(join(knowledgeRoot, '00_INDEX.md'), 'utf-8')
assert(generated.includes('generated: true') && generated.includes('generator: knowledge-manager-v0.2'), 'generated index marker missing')
console.log(`  categories=${stats.categoryCount} knowledge=${stats.knowledgeCount} files=${snapshot.files.length}`)
console.log('  taxonomy + generated index = PASS')

await projectFiber.dispose(); await tick()
for (let i = fibers.length - 1; i >= 0; i -= 1) { await fibers[i].dispose(); await tick() }
EOF
ET_TOOL_PROJECT_ROOT="$ROOT_DIR" node "$SMOKE_DIR/smoke.mjs"

echo '[4/5] Knowledge Taxonomy Contract result'
printf '%s\n' 'PHASE4_ETTOOL_KNOWLEDGE_TAXONOMY_V0_1_INTEGRATION=PASS' 'ETTOOL_KNOWLEDGE_ROOT_CATEGORIES=9' 'ETTOOL_KNOWLEDGE_CATEGORIES=45' "CORDIS_VERSION=$CORDIS_VERSION"
echo '[5/5] DONE'
