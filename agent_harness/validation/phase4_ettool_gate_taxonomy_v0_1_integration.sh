#!/usr/bin/env bash
set -euo pipefail

CORDIS_VERSION="${CORDIS_VERSION:-4.0.1}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${PHASE4_ETTOOL_GATE_WORK_DIR:-$(mktemp -d)}"
SMOKE_DIR="$WORK_DIR/cordis-smoke"
PACK_DIR="$WORK_DIR/packs"
RUNTIME_ROOT="$WORK_DIR/runtime"
source "$ROOT_DIR/agent_harness/validation/lib/common_runtime.sh"
trap 'rm -rf "$WORK_DIR"' EXIT
mkdir -p "$SMOKE_DIR" "$PACK_DIR" "$RUNTIME_ROOT"
export npm_config_registry="$NPM_REGISTRY"
export AGENT_HARNESS_STATE_ROOT="$RUNTIME_ROOT"

PROJECT_PLUGIN_ROOT="$ROOT_DIR/agent_harness/projects/et_tool"
GATE_ROOT="$PROJECT_PLUGIN_ROOT/gates"

echo '[0/5] ET-TOOL Gate Taxonomy v0.1 static precheck'
test -f "$GATE_ROOT/00_INDEX.md"
for file in \
  010_change_scope_review.yaml \
  020_architecture_boundary_review.yaml \
  030_rule_compliance_review.yaml \
  040_logic_static_review.yaml \
  050_resource_lifecycle_review.yaml \
  060_regression_impact_review.yaml \
  070_contract_compatibility_review.yaml; do
  test -f "$GATE_ROOT/$file"
done
[[ "$(find "$GATE_ROOT" -maxdepth 1 -type f -name '[0-9][0-9][0-9]_*.yaml' | wc -l)" -eq 7 ]]
[[ "$(grep -h -c '^[[:space:]]*gate:$' "$GATE_ROOT"/[0-9][0-9][0-9]_*.yaml | awk '{s+=$1} END {print s}')" -eq 18 ]]
if grep -Eh '^[[:space:]]*tool:[[:space:]]*(build\.execute|test\.execute|hardware\.validate)[[:space:]]*$' "$GATE_ROOT"/[0-9][0-9][0-9]_*.yaml; then
  echo 'ET-TOOL Code Gate must not execute build/test/hardware validation directly' >&2
  exit 1
fi
echo '  7 Gate domains + 18 executable Code Gates; no build/test/hardware tool steps = PASS'

echo '[1/5] Build Gate Manager / Project Contract / ET-TOOL Project'
for dir in project_contract governance_core public_plugins/project_manager public_plugins/evidence_state_manager public_plugins/gate_manager projects/et_tool; do
  npm_install_if_needed "$ROOT_DIR/agent_harness/$dir" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
  (cd "$ROOT_DIR/agent_harness/$dir" && npm test && npm run build)
done
(cd "$PROJECT_PLUGIN_ROOT" && npm pack --pack-destination "$PACK_DIR" >/dev/null)
PROJECT_TGZ="$(find "$PACK_DIR" -maxdepth 1 -name 'agent-harness-project-et-tool-*.tgz' -print -quit)"
test -n "$PROJECT_TGZ"
PACK_LIST="$WORK_DIR/project-gate-package.list"
tar -tzf "$PROJECT_TGZ" > "$PACK_LIST"
for entry in \
  package/gates/00_INDEX.md \
  package/gates/010_change_scope_review.yaml \
  package/gates/020_architecture_boundary_review.yaml \
  package/gates/030_rule_compliance_review.yaml \
  package/gates/040_logic_static_review.yaml \
  package/gates/050_resource_lifecycle_review.yaml \
  package/gates/060_regression_impact_review.yaml \
  package/gates/070_contract_compatibility_review.yaml; do
  grep -Fxq "$entry" "$PACK_LIST"
done
echo '  Gate taxonomy packaged with ET-TOOL Project Plugin = PASS'

echo '[2/5] Prepare real Cordis Runtime'
cd "$SMOKE_DIR"
npm init -y >/dev/null
npm pkg set type=module >/dev/null
npm_install_if_needed "$SMOKE_DIR" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS" \
  "@deepseek-ai/cordis@$CORDIS_VERSION" \
  "$ROOT_DIR/agent_harness/governance_core" \
  "$ROOT_DIR/agent_harness/project_contract" \
  "$ROOT_DIR/agent_harness/public_plugins/project_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/evidence_state_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/gate_manager" \
  "$PROJECT_TGZ"

echo '[3/5] Gate parsing / routing / execution plan / evidence smoke'
cat > "$SMOKE_DIR/smoke.mjs" <<'EOF'
import { Context } from '@deepseek-ai/cordis'
import GovernanceCatalogService from '@agent-harness/governance-core'
import * as projectManagerPlugin from '@agent-harness/project-manager'
import * as evidencePlugin from '@agent-harness/evidence-state-manager'
import * as gatePlugin from '@agent-harness/gate-manager'
import * as etToolProjectPlugin from '@agent-harness/project-et-tool'

const tick = () => new Promise(resolve => setTimeout(resolve, 0))
const assert = (condition, message) => { if (!condition) throw new Error(message) }
const ctx = new Context(); const fibers = []
fibers.push(ctx.plugin(GovernanceCatalogService)); await tick()
fibers.push(ctx.plugin(projectManagerPlugin)); await tick()
fibers.push(ctx.plugin(evidencePlugin)); await tick()
fibers.push(ctx.plugin(gatePlugin)); await tick()
const projectFiber = ctx.plugin(etToolProjectPlugin); await tick()

const gates = ctx.get('gateManager')
const evidence = ctx.get('evidenceStateManager')
assert(gates && evidence, 'Gate/Evidence public services missing')
const snapshot = gates.refreshProject('et-tool')
assert(snapshot.state === 'ready', 'ET-TOOL Gates must be READY')
assert(snapshot.files.length === 7, `expected 7 Gate files, got ${snapshot.files.length}`)
assert(snapshot.nodeCount === 42, `expected 42 Gate nodes including 7 file roots, got ${snapshot.nodeCount}`)
assert(snapshot.gateCount === 18, `expected 18 executable Gates, got ${snapshot.gateCount}`)

const ids = [
  'G010.010.010','G010.010.020','G010.020.010',
  'G020.010.010','G020.020.010','G020.030.010',
  'G030.010.010','G030.020.010',
  'G040.010.010','G040.020.010','G040.030.010',
  'G050.010.010','G050.020.010','G050.030.010',
  'G060.010.010','G060.020.010',
  'G070.010.010','G070.020.010',
]
const banned = new Set(['build.execute','test.execute','hardware.validate'])
for (const id of ids) {
  const result = gates.getNode('et-tool', id)
  assert(result?.node?.gate?.level === 'MUST', `${id} must be MUST executable Gate`)
  const plan = gates.getExecutionPlan('et-tool', id)
  assert(plan?.steps?.length > 0, `missing execution plan for ${id}`)
  for (const step of plan.steps) assert(!banned.has(step.tool), `${id} illegally executes ${step.tool}`)
}
assert(gates.getExecutionPlan('et-tool', 'G040.030.010')?.steps[0]?.tool === 'code.review', 'static sanity must use code.review')
assert(gates.getExecutionPlan('et-tool', 'G060.020.010')?.steps[0]?.tool === 'validation.plan', 'post-gate validation must only produce a plan')

assert(gates.searchGates({ projectId: 'et-tool', query: 'unexpected change scope diff' }).some(item => item.id === 'G010.010.020'), 'change-scope routing failed')
assert(gates.searchGates({ projectId: 'et-tool', query: 'chip isolation architecture dependency' }).some(item => item.id === 'G020.020.010'), 'architecture routing failed')
assert(gates.searchGates({ projectId: 'et-tool', query: 'logic early return error path' }).some(item => item.id === 'G040.020.010'), 'logic routing failed')
assert(gates.searchGates({ projectId: 'et-tool', query: 'cleanup exit qprocess lifecycle' }).some(item => item.id === 'G050.020.010'), 'cleanup routing failed')
assert(gates.searchGates({ projectId: 'et-tool', query: 'uart can regression affected scope' }).some(item => item.id === 'G060.010.010'), 'regression routing failed')
assert(gates.searchGates({ projectId: 'et-tool', query: 'profile progress schema compatibility' }).some(item => item.id === 'G070.020.010'), 'contract routing failed')

const taskId = 'GATE-TAXONOMY-SMOKE'
const before = gates.checkGateSetEvidence('et-tool', taskId, ['G010.010.010'])
assert(before.canComplete === false, 'MUST Code Gate without PASS evidence must block completion')
const recorded = evidence.recordEvidence({
  projectId: 'et-tool',
  taskId,
  kind: 'gate',
  result: 'PASS',
  summary: 'Change scope code review passed in Gate Taxonomy smoke.',
  source: 'phase4-ettool-gate-taxonomy-smoke',
  gateId: 'G010.010.010',
})
const after = gates.checkGateSetEvidence('et-tool', taskId, ['G010.010.010'])
assert(after.canComplete === true, 'MUST Code Gate PASS evidence should release the Gate')
assert(after.gates[0].evidenceRefs.includes(recorded.evidenceId), 'Gate PASS evidence not linked')

console.log(`  Gate files=${snapshot.files.length}; nodes=${snapshot.nodeCount}; executable=${snapshot.gateCount}`)
console.log('  routing + review-only execution plans + MUST evidence guard = PASS')
await projectFiber.dispose(); await tick()
for (let i = fibers.length - 1; i >= 0; i -= 1) { await fibers[i].dispose(); await tick() }
EOF
ET_TOOL_PROJECT_ROOT="$ROOT_DIR" node "$SMOKE_DIR/smoke.mjs"

echo '[4/5] Gate Taxonomy Contract result'
printf '%s\n' \
  'PHASE4_ETTOOL_GATE_TAXONOMY_V0_1_INTEGRATION=PASS' \
  'ETTOOL_GATE_FILES=7' \
  'ETTOOL_GATE_NODES=42' \
  'ETTOOL_EXECUTABLE_GATES=18' \
  "CORDIS_VERSION=$CORDIS_VERSION"
echo '[5/5] DONE'
