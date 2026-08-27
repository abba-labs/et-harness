#!/usr/bin/env bash
set -euo pipefail

CORDIS_VERSION="${CORDIS_VERSION:-4.0.1}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${PHASE4_ETTOOL_SHELL_WORK_DIR:-$(mktemp -d)}"
SMOKE_DIR="$WORK_DIR/cordis-smoke"
PACK_DIR="$WORK_DIR/packs"
RUNTIME_ROOT="$WORK_DIR/runtime"
source "$ROOT_DIR/agent_harness/validation/lib/common_runtime.sh"
trap 'rm -rf "$WORK_DIR"' EXIT
mkdir -p "$SMOKE_DIR" "$PACK_DIR" "$RUNTIME_ROOT"
export npm_config_registry="$NPM_REGISTRY"
export AGENT_HARNESS_STATE_ROOT="$RUNTIME_ROOT"

PROJECT_PLUGIN_ROOT="$ROOT_DIR/agent_harness/projects/et_tool"
PROJECT_MANIFEST="$PROJECT_PLUGIN_ROOT/project.yaml"

echo '[0/5] ET-TOOL Project Plugin Shell static precheck'
test -f "$ROOT_DIR/source/CMakeLists.txt"
test -f "$PROJECT_MANIFEST"
for path in "$PROJECT_PLUGIN_ROOT/architecture/00_INDEX.md" "$PROJECT_PLUGIN_ROOT/rules/00_INDEX.md" "$PROJECT_PLUGIN_ROOT/knowledge/TAXONOMY.yaml" "$PROJECT_PLUGIN_ROOT/gates/00_INDEX.md"; do test -f "$path"; done
grep -q 'contract_version: "0.1"' "$PROJECT_MANIFEST"
grep -q 'standard: architecture-v0.1' "$PROJECT_MANIFEST"
grep -q 'standard: rule-v0.1' "$PROJECT_MANIFEST"
grep -q 'standard: knowledge-v0.1' "$PROJECT_MANIFEST"
grep -q 'standard: gate-v0.1' "$PROJECT_MANIFEST"
grep -q '^adapters:$' "$PROJECT_MANIFEST"
for capability in change.analyze code.review architecture.review rule.review lifecycle.review contract.review validation.plan; do
  grep -Fq "capability: $capability" "$PROJECT_MANIFEST"
done

echo '[1/5] Build Public Routers / ET-TOOL Project'
for dir in project_contract governance_core public_plugins/project_manager public_plugins/architecture_navigator public_plugins/rule_manager public_plugins/knowledge_manager public_plugins/evidence_state_manager public_plugins/gate_manager projects/et_tool; do
  npm_install_if_needed "$ROOT_DIR/agent_harness/$dir" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
  (cd "$ROOT_DIR/agent_harness/$dir" && npm test && npm run build)
done
(cd "$PROJECT_PLUGIN_ROOT" && npm pack --pack-destination "$PACK_DIR" >/dev/null)
PROJECT_TGZ="$(find "$PACK_DIR" -maxdepth 1 -name 'agent-harness-project-et-tool-*.tgz' -print -quit)"
test -n "$PROJECT_TGZ"
PACK_LIST="$WORK_DIR/project-shell-package.list"
tar -tzf "$PROJECT_TGZ" > "$PACK_LIST"
for entry in \
  package/project.yaml \
  package/architecture/00_INDEX.md \
  package/rules/00_INDEX.md \
  package/knowledge/TAXONOMY.yaml \
  package/knowledge/SOURCES.yaml \
  package/gates/00_INDEX.md \
  package/gates/010_change_scope_review.yaml \
  package/gates/070_contract_compatibility_review.yaml \
  package/dist/review-adapter.js \
  package/dist/review-service.js \
  package/dist/review-contracts.js; do
  grep -Fxq "$entry" "$PACK_LIST"
done

echo '[2/5] Prepare real Cordis Runtime'
cd "$SMOKE_DIR"
npm init -y >/dev/null
npm pkg set type=module >/dev/null
npm_install_if_needed "$SMOKE_DIR" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS" \
  "@deepseek-ai/cordis@$CORDIS_VERSION" \
  "$ROOT_DIR/agent_harness/governance_core" \
  "$ROOT_DIR/agent_harness/project_contract" \
  "$ROOT_DIR/agent_harness/public_plugins/project_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/architecture_navigator" \
  "$ROOT_DIR/agent_harness/public_plugins/rule_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/knowledge_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/evidence_state_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/gate_manager" \
  "$PROJECT_TGZ"

echo '[3/5] ET-TOOL Project Interface smoke'
cat > "$SMOKE_DIR/smoke.mjs" <<'EOF'
import { Context } from '@deepseek-ai/cordis'
import GovernanceCatalogService from '@agent-harness/governance-core'
import * as projectManagerPlugin from '@agent-harness/project-manager'
import * as architecturePlugin from '@agent-harness/architecture-navigator'
import * as rulePlugin from '@agent-harness/rule-manager'
import * as knowledgePlugin from '@agent-harness/knowledge-manager'
import * as evidencePlugin from '@agent-harness/evidence-state-manager'
import * as gatePlugin from '@agent-harness/gate-manager'
import * as etToolProjectPlugin from '@agent-harness/project-et-tool'
const tick = () => new Promise(resolve => setTimeout(resolve, 0))
const assert = (condition, message) => { if (!condition) throw new Error(message) }
const root = process.env.ET_TOOL_PROJECT_ROOT
const ctx = new Context(); const fibers = []
fibers.push(ctx.plugin(GovernanceCatalogService)); await tick()
fibers.push(ctx.plugin(projectManagerPlugin)); await tick()
fibers.push(ctx.plugin(architecturePlugin)); await tick()
fibers.push(ctx.plugin(rulePlugin)); await tick()
fibers.push(ctx.plugin(knowledgePlugin)); await tick()
fibers.push(ctx.plugin(evidencePlugin)); await tick()
fibers.push(ctx.plugin(gatePlugin)); await tick()
const projectFiber = ctx.plugin(etToolProjectPlugin); await tick()
const pm = ctx.get('projectManager'); const arch = ctx.get('architectureNavigator'); const rules = ctx.get('ruleManager'); const knowledge = ctx.get('knowledgeManager'); const gates = ctx.get('gateManager')
assert(pm && arch && rules && knowledge && gates, 'required Public services missing')
const project = pm.getProjectContext('et-tool')
assert(project?.projectRoot === root, 'ET-TOOL project registration/root failed')
assert(Object.keys(project.adapters).length === 7, `ET-TOOL adapter declaration mismatch: ${Object.keys(project.adapters).length}`)
assert(Object.values(project.adapters).every(item => typeof item.capability === 'string'), 'adapter capability declaration missing')
assert(pm.resolveProject('ettool').some(item => item.projectId === 'et-tool'), 'project alias failed')
const a = arch.refreshProject('et-tool'); const r = rules.refreshProject('et-tool'); const k = knowledge.refreshProject('et-tool'); const g = gates.refreshProject('et-tool')
assert(a.state === 'ready' && a.nodeCount > 0, 'Architecture not READY')
assert(r.state === 'ready' && r.files.length === 9 && r.ruleCount >= 50, 'Rules not READY')
assert(k.state === 'ready' && k.libraryMode === 'library-v0.2', 'Knowledge library-v0.2 not READY')
assert(knowledge.getLibraryStats('et-tool').categoryCount === 45, 'Knowledge taxonomy mismatch')
assert(g.state === 'ready' && g.files.length === 7 && g.gateCount === 18, `Gate taxonomy mismatch: files=${g.files.length} gates=${g.gateCount}`)
assert(gates.searchGates({ projectId: 'et-tool', query: 'cleanup exit qprocess lifecycle' }).some(item => item.id === 'G050.020.010'), 'Gate routing failed')
assert(arch.searchArchitecture({ projectId: 'et-tool', query: 'ET6003 J-Link' }).length > 0, 'Architecture routing failed')
assert(rules.searchRules({ projectId: 'et-tool', query: 'GUI connection timeout' }).some(item => item.id === 'R100.300.010'), 'Rules routing failed')
console.log(`  Architecture nodes=${a.nodeCount}; Rule leaves=${r.ruleCount}; Knowledge leaves=${k.knowledgeCount}; Gate leaves=${g.gateCount}; Adapter declarations=${Object.keys(project.adapters).length}`)
console.log('  project resource + adapter declaration integration = PASS')
await projectFiber.dispose(); await tick()
assert(pm.getProjectContext('et-tool') === undefined, 'project unload cleanup failed')
for (let i = fibers.length - 1; i >= 0; i -= 1) { await fibers[i].dispose(); await tick() }
EOF
ET_TOOL_PROJECT_ROOT="$ROOT_DIR" node "$SMOKE_DIR/smoke.mjs"

echo '[4/5] Project Plugin Shell result'
printf '%s\n' 'PHASE4_ETTOOL_PROJECT_SHELL_V0_1_INTEGRATION=PASS' "CORDIS_VERSION=$CORDIS_VERSION" "PROJECT_ROOT=$ROOT_DIR"
echo '[5/5] DONE'
