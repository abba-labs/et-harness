#!/usr/bin/env bash
set -euo pipefail

CORDIS_VERSION="${CORDIS_VERSION:-4.0.1}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${PHASE4_ETTOOL_RULES_WORK_DIR:-$(mktemp -d)}"
SMOKE_DIR="$WORK_DIR/cordis-smoke"
PACK_DIR="$WORK_DIR/packs"
RUNTIME_ROOT="$WORK_DIR/runtime"

source "$ROOT_DIR/agent_harness/validation/lib/common_runtime.sh"

cleanup() {
  if [[ "${PHASE4_ETTOOL_RULES_KEEP_WORK_DIR:-0}" != "1" ]]; then
    rm -rf "$WORK_DIR"
  else
    echo "保留验证目录: $WORK_DIR"
  fi
}
trap cleanup EXIT

mkdir -p "$SMOKE_DIR" "$PACK_DIR" "$RUNTIME_ROOT"
export npm_config_registry="$NPM_REGISTRY"
export AGENT_HARNESS_STATE_ROOT="$RUNTIME_ROOT"

PROJECT_PLUGIN_ROOT="$ROOT_DIR/agent_harness/projects/et_tool"
RULE_ROOT="$PROJECT_PLUGIN_ROOT/rules"

printf '%s\n' '[0/5] ET-TOOL Rule Taxonomy v0.1 静态预检'
RULE_FILES=(
  100_gui_rules.md
  200_cli_rules.md
  300_application_workflow_rules.md
  400_backend_protocol_transport_rules.md
  500_probe_hardware_rules.md
  600_chip_route_rules.md
  700_profile_capability_rules.md
  800_test_automation_evidence_rules.md
  900_engineering_release_delivery_rules.md
)
test -f "$RULE_ROOT/00_INDEX.md"
for file in "${RULE_FILES[@]}"; do
  test -f "$RULE_ROOT/$file"
done

grep -q 'id: R100' "$RULE_ROOT/00_INDEX.md"
grep -q 'id: R900' "$RULE_ROOT/00_INDEX.md"
grep -q 'R100.100.020.*Layout Must Be Compact And Structured' "$RULE_ROOT/100_gui_rules.md"
grep -q 'R100.100.030.*GUI Must Follow ET Red And White Visual Baseline' "$RULE_ROOT/100_gui_rules.md"
grep -q 'R100.200.020.*Connection Page Must Be The Initial Page' "$RULE_ROOT/100_gui_rules.md"
grep -q 'R100.200.030.*Function Workspace Requires Successful Connection' "$RULE_ROOT/100_gui_rules.md"
grep -q 'R100.300.010.*Timeout Must Close Operation Lifecycle' "$RULE_ROOT/100_gui_rules.md"
grep -q 'R100.400.020.*Active Progress Must Refresh Continuously' "$RULE_ROOT/100_gui_rules.md"
grep -q 'R100.700.010.*Chip GUI Implementations Must Remain Independent' "$RULE_ROOT/100_gui_rules.md"
grep -q 'R100.700.020.*All Chip GUIs Must Share One Visual Language' "$RULE_ROOT/100_gui_rules.md"
grep -q 'R100.800.010.*Controls Must Use Semantic Functional Colors' "$RULE_ROOT/100_gui_rules.md"
grep -q 'R100.900.010.*Primary Functional Controls Must Be Directly Visible' "$RULE_ROOT/100_gui_rules.md"
grep -q 'R100.900.020.*Desktop Function Workspace Must Not Require Horizontal Scrolling' "$RULE_ROOT/100_gui_rules.md"
grep -q 'R200.400.020.*Progress Must Be Published Incrementally' "$RULE_ROOT/200_cli_rules.md"
grep -q 'R300.600.020.*Every Exit Path Must Converge On Cleanup' "$RULE_ROOT/300_application_workflow_rules.md"
grep -q 'R600.600.010.*Unsupported Route Must Not Gain Synthetic Implementation' "$RULE_ROOT/600_chip_route_rules.md"
grep -q 'R600.700.010.*Local Change Must Not Affect Unrelated Chip Route Or Feature' "$RULE_ROOT/600_chip_route_rules.md"
grep -q 'R800.200.010.*Product Automation Must Exercise Formal CLI Boundary' "$RULE_ROOT/800_test_automation_evidence_rules.md"
grep -q 'R900.300.020.*Compilation And Build Must Use Release Scripts' "$RULE_ROOT/900_engineering_release_delivery_rules.md"
printf '%s\n' '  nine rule-domain files + routing index = PASS'

printf '%s\n' '[1/5] 构建 Rule Manager / Project Contract / ET-TOOL Project'
PACKAGES=(
  project_contract
  governance_core
  public_plugins/project_manager
  public_plugins/rule_manager
  projects/et_tool
)
for dir in "${PACKAGES[@]}"; do
  npm_install_if_needed "$ROOT_DIR/agent_harness/$dir" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
  (cd "$ROOT_DIR/agent_harness/$dir" && npm test && npm run build)
done

(cd "$PROJECT_PLUGIN_ROOT" && npm pack --pack-destination "$PACK_DIR" >/dev/null)
PROJECT_TGZ="$(find "$PACK_DIR" -maxdepth 1 -name 'agent-harness-project-et-tool-*.tgz' -print -quit)"
test -n "$PROJECT_TGZ"

printf '%s\n' '[2/5] 准备真实 Cordis Runtime'
cd "$SMOKE_DIR"
npm init -y >/dev/null
npm pkg set type=module >/dev/null
npm_install_if_needed "$SMOKE_DIR" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS" \
  "@deepseek-ai/cordis@$CORDIS_VERSION" \
  "$ROOT_DIR/agent_harness/governance_core" \
  "$ROOT_DIR/agent_harness/project_contract" \
  "$ROOT_DIR/agent_harness/public_plugins/project_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/rule_manager" \
  "$PROJECT_TGZ"

printf '%s\n' '[3/5] Rule Manager taxonomy / routing smoke'
cat > "$SMOKE_DIR/smoke.mjs" <<'EOF'
import { Context } from '@deepseek-ai/cordis'
import GovernanceCatalogService from '@agent-harness/governance-core'
import * as projectManagerPlugin from '@agent-harness/project-manager'
import * as rulePlugin from '@agent-harness/rule-manager'
import * as etToolProjectPlugin from '@agent-harness/project-et-tool'

const tick = () => new Promise(resolve => setTimeout(resolve, 0))
const assert = (condition, message) => { if (!condition) throw new Error(message) }
const hasId = (items, id) => items.some(item => item.id === id)

const ctx = new Context()
const fibers = []
fibers.push(ctx.plugin(GovernanceCatalogService)); await tick()
fibers.push(ctx.plugin(projectManagerPlugin)); await tick()
fibers.push(ctx.plugin(rulePlugin)); await tick()
const projectFiber = ctx.plugin(etToolProjectPlugin); await tick()

const rules = ctx.get('ruleManager')
assert(rules, 'ruleManager missing')
const snapshot = rules.refreshProject('et-tool')
assert(snapshot.state === 'ready', `rules state is ${snapshot.state}`)
assert(snapshot.files.length === 9, `expected 9 rule files, got ${snapshot.files.length}`)
assert(snapshot.nodeCount === 135, `expected 135 rule nodes, got ${snapshot.nodeCount}`)
assert(snapshot.ruleCount === 68, `expected 68 rule leaves, got ${snapshot.ruleCount}`)
assert(snapshot.warnings.length === 0, `unexpected rule warnings: ${snapshot.warnings.join('; ')}`)

const exact = rules.getNode('et-tool', 'R100.300.010')
assert(exact?.node.level === 'MUST', 'exact Rule ID lookup failed')
assert(exact.node.rule?.includes('子进程'), 'timeout cleanup rule content missing')

const guiBaseline = rules.getNode('et-tool', 'R100.100.030')
assert(guiBaseline?.node.level === 'MUST', 'GUI visual baseline rule lookup failed')
assert(guiBaseline.node.rule?.includes('ET 红白视觉基线'), 'GUI red-white baseline content missing')

const guiIsolation = rules.getNode('et-tool', 'R100.700.010')
assert(guiIsolation?.node.level === 'MUST', 'chip GUI isolation rule lookup failed')
assert(guiIsolation.node.rule?.includes('业务代码必须保持独立'), 'chip GUI isolation content missing')

const liveProgress = rules.getNode('et-tool', 'R100.400.020')
assert(liveProgress?.node.level === 'MUST', 'live GUI progress rule lookup failed')
assert(liveProgress.node.rule?.includes('elapsed time'), 'live GUI progress anti-fake guard missing')

const incrementalProgress = rules.getNode('et-tool', 'R200.400.020')
assert(incrementalProgress?.node.level === 'MUST', 'incremental progress publishing rule lookup failed')
assert(incrementalProgress.node.rule?.includes('持续增量发布'), 'incremental progress publishing content missing')

const cleanupRule = rules.getNode('et-tool', 'R300.600.020')
assert(cleanupRule?.node.level === 'MUST', 'unified cleanup rule lookup failed')
assert(cleanupRule.node.rule?.includes('QProcess/QTimer/QThread'), 'runtime cleanup ownership content missing')
assert(cleanupRule.node.rule?.includes('target state'), 'target-state cleanup distinction missing')

const changeIsolation = rules.getNode('et-tool', 'R600.700.010')
assert(changeIsolation?.node.level === 'MUST', 'change impact isolation rule lookup failed')
assert(changeIsolation.node.rule?.includes('目标 Chip × Route × Capability'), 'change impact target scope missing')
assert(changeIsolation.node.rule?.includes('无关 route'), 'unrelated route isolation content missing')

const noHorizontalScroll = rules.getNode('et-tool', 'R100.900.020')
assert(noHorizontalScroll?.node.level === 'MUST_NOT', 'desktop horizontal-scroll prohibition lookup failed')
assert(noHorizontalScroll.node.rule?.includes('左右滑动'), 'desktop horizontal-scroll prohibition content missing')

const buildGuard = rules.getNode('et-tool', 'R900.300.020')
assert(buildGuard?.node.level === 'MUST', 'release build pipeline guard lookup failed')
assert(buildGuard.node.rule?.includes('source/release/'), 'release build pipeline path missing')
assert(buildGuard.node.rule?.includes('手工拼接'), 'manual build command prohibition missing')

const search = (query, expectedId, scope = undefined) => {
  const results = rules.searchRules({ projectId: 'et-tool', query, limit: 12, ...(scope ? { scope } : {}) })
  assert(hasId(results, expectedId), `${query} did not hit ${expectedId}; got ${results.map(item => item.id).join(', ')}`)
}

search('GUI compact layout', 'R100.100.020')
search('ET red white GUI visual baseline', 'R100.100.030')
search('homepage connection page workspace', 'R100.200.020')
search('successful connection identify function workspace', 'R100.200.030')
search('timeout', 'R100.300.010', { surface: 'GUI', area: 'connection cleanup' })
search('GUI progress timeout', 'R100.400.010')
search('GUI realtime progress refresh', 'R100.400.020')
search('chip GUI independent ET3101 ET6003', 'R100.700.010')
search('all chip GUI consistent visual style', 'R100.700.020')
search('control semantic color danger success', 'R100.800.010')
search('primary functional controls visible not hidden', 'R100.900.010')
search('horizontal scroll swipe carousel GUI', 'R100.900.020')
search('CLI return code error', 'R200.300.010')
search('incremental progress stream CLI', 'R200.400.020')
search('program erase OTP safety', 'R300.300.010')
search('shutdown disconnect exit resource cleanup', 'R300.600.020')
search('protocol CAN physical device', 'R400.200.010')
search('J-Link chip algorithm', 'R500.300.010')
search('ET6002 CANFD unsupported', 'R600.600.010')
search('UART change must not affect CAN unrelated route', 'R600.700.010')
search('profile deferred supported', 'R700.200.010')
search('product automation et-cli evidence', 'R800.200.010')
search('release package delivery', 'R900.100.010')
search('compile build shell cmake ninja release script', 'R900.300.020')

const broadGui = rules.searchRules({ projectId: 'et-tool', query: 'GUI', limit: 24 })
assert(hasId(broadGui, 'R100'), 'broad GUI query must expose GUI rule-domain root')

console.log(`  Rule files=${snapshot.files.length} nodes=${snapshot.nodeCount} leaves=${snapshot.ruleCount}`)
console.log('  exact Rule ID lookup = PASS')
console.log('  GUI design contract routing = PASS')
console.log('  progress / cleanup / change-isolation routing = PASS')
console.log('  index aliases + branch/leaf routing = PASS')
console.log('  query scope narrowing = PASS')
console.log('  cross-domain user-language routing = PASS')

await projectFiber.dispose(); await tick()
for (let index = fibers.length - 1; index >= 0; index -= 1) {
  await fibers[index].dispose(); await tick()
}
EOF

ET_TOOL_PROJECT_ROOT="$ROOT_DIR" node "$SMOKE_DIR/smoke.mjs"

printf '%s\n' '[4/5] Rule Taxonomy Contract result'
printf '%s\n' \
  'PHASE4_ETTOOL_RULE_TAXONOMY_V0_1_INTEGRATION=PASS' \
  'ETTOOL_RULE_FILES=9' \
  'ETTOOL_RULE_LEAVES=68' \
  "CORDIS_VERSION=$CORDIS_VERSION"
printf '%s\n' '[5/5] DONE'
