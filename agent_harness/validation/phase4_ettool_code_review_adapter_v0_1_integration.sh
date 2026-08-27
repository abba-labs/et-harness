#!/usr/bin/env bash
set -euo pipefail

CORDIS_VERSION="${CORDIS_VERSION:-4.0.1}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${PHASE4_ETTOOL_REVIEW_ADAPTER_WORK_DIR:-$(mktemp -d)}"
SMOKE_DIR="$WORK_DIR/cordis-smoke"
PACK_DIR="$WORK_DIR/packs"
RUNTIME_ROOT="$WORK_DIR/runtime"
source "$ROOT_DIR/agent_harness/validation/lib/common_runtime.sh"
trap 'rm -rf "$WORK_DIR"' EXIT
mkdir -p "$SMOKE_DIR" "$PACK_DIR" "$RUNTIME_ROOT"
export npm_config_registry="$NPM_REGISTRY"
export AGENT_HARNESS_STATE_ROOT="$RUNTIME_ROOT"

PROJECT_PLUGIN_ROOT="$ROOT_DIR/agent_harness/projects/et_tool"

echo '[0/5] ET-TOOL Code Review Adapter v0.1 static precheck'
grep -q "'change.analyze'" "$PROJECT_PLUGIN_ROOT/src/review-contracts.ts"
grep -q "'code.review'" "$PROJECT_PLUGIN_ROOT/src/review-contracts.ts"
grep -q "'architecture.review'" "$PROJECT_PLUGIN_ROOT/src/review-contracts.ts"
grep -q "'rule.review'" "$PROJECT_PLUGIN_ROOT/src/review-contracts.ts"
grep -q "'lifecycle.review'" "$PROJECT_PLUGIN_ROOT/src/review-contracts.ts"
grep -q "'contract.review'" "$PROJECT_PLUGIN_ROOT/src/review-contracts.ts"
grep -q "'validation.plan'" "$PROJECT_PLUGIN_ROOT/src/review-contracts.ts"
grep -q 'autoPass: false' "$PROJECT_PLUGIN_ROOT/src/review-adapter.ts"
grep -q "reviewer: 'agent' | 'human'" "$PROJECT_PLUGIN_ROOT/src/review-contracts.ts"
grep -q '存在 BLOCK finding 时禁止记录 PASS Evidence' "$PROJECT_PLUGIN_ROOT/src/review-service.ts"
[[ "$(grep -c '^[[:space:]]\{2\}[a-z_]*:$' "$PROJECT_PLUGIN_ROOT/project.yaml" | tr -d ' ')" -ge 7 ]]
echo '  governed explicit-review model = PASS'

echo '[1/5] Build Public Managers / ET-TOOL Project package'
for dir in project_contract governance_core public_plugins/project_manager public_plugins/architecture_navigator public_plugins/rule_manager public_plugins/knowledge_manager public_plugins/evidence_state_manager public_plugins/gate_manager projects/et_tool; do
  npm_install_if_needed "$ROOT_DIR/agent_harness/$dir" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
  (cd "$ROOT_DIR/agent_harness/$dir" && npm test && npm run build)
done
(cd "$PROJECT_PLUGIN_ROOT" && npm pack --pack-destination "$PACK_DIR" >/dev/null)
PROJECT_TGZ="$(find "$PACK_DIR" -maxdepth 1 -name 'agent-harness-project-et-tool-*.tgz' -print -quit)"
test -n "$PROJECT_TGZ"
PACK_LIST="$WORK_DIR/review-adapter-package.list"
tar -tzf "$PROJECT_TGZ" > "$PACK_LIST"
for entry in package/dist/review-adapter.js package/dist/review-service.js package/dist/review-contracts.js package/project.yaml package/cordis.patch.yml; do
  grep -Fxq "$entry" "$PACK_LIST"
done
echo '  review adapter subpath packaged = PASS'

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

echo '[3/5] Review Packet / Provider / Evidence smoke'
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
import * as reviewAdapterPlugin from '@agent-harness/project-et-tool/review-adapter'

const tick = () => new Promise(resolve => setTimeout(resolve, 0))
const assert = (condition, message) => { if (!condition) throw new Error(message) }
const ctx = new Context(); const fibers = []
fibers.push(ctx.plugin(GovernanceCatalogService)); await tick()
fibers.push(ctx.plugin(projectManagerPlugin)); await tick()
fibers.push(ctx.plugin(architecturePlugin)); await tick()
fibers.push(ctx.plugin(rulePlugin)); await tick()
fibers.push(ctx.plugin(knowledgePlugin)); await tick()
fibers.push(ctx.plugin(evidencePlugin)); await tick()
fibers.push(ctx.plugin(gatePlugin)); await tick()
const projectFiber = ctx.plugin(etToolProjectPlugin); await tick()
const reviewFiber = ctx.plugin(reviewAdapterPlugin); await tick()

const pm = ctx.get('projectManager')
const catalog = ctx.get('governanceCatalog')
const gates = ctx.get('gateManager')
const adapter = ctx.get('etToolCodeReviewAdapter')
assert(pm && catalog && gates && adapter, 'review adapter runtime services missing')
const project = pm.getProjectContext('et-tool')
assert(project, 'ET-TOOL Project missing')
assert(Object.keys(project.adapters).length === 7, `expected 7 project adapters, got ${Object.keys(project.adapters).length}`)

const capabilityGate = new Map([
  ['change.analyze', 'G010.010.010'],
  ['code.review', 'G010.010.010'],
  ['architecture.review', 'G020.010.010'],
  ['rule.review', 'G030.010.010'],
  ['lifecycle.review', 'G050.030.010'],
  ['contract.review', 'G070.010.010'],
  ['validation.plan', 'G060.020.010'],
])
for (const [capability, gateId] of capabilityGate) {
  const providers = catalog.listProviders(capability)
  assert(providers.some(item => item.providerId === `project.et-tool.code-review-adapter.${capability}`), `${capability} provider missing`)
  const packet = adapter.prepareReview({
    projectId: 'et-tool',
    taskId: `ADAPTER-${capability}`,
    gateId,
    capability,
    taskIntent: '修复 ET6003 UART GUI progress 生命周期与退出清理，不影响 CAN/CANFD',
    change: {
      files: ['source/apps/gui/chips/et6003/uart/et6003_uart_panel.cpp'],
      patch: 'diff --git a/source/apps/gui/chips/et6003/uart/et6003_uart_panel.cpp b/source/apps/gui/chips/et6003/uart/et6003_uart_panel.cpp\n@@ -10,1 +10,2 @@\n-old\n+new\n+cleanup();',
    },
  })
  assert(packet.capability === capability, `${capability} packet mismatch`)
  assert(packet.change.source === 'provided', 'synthetic change should use provided source')
  assert(packet.scopeHints.chips.includes('ET6003'), 'ET6003 scope missing')
  assert(packet.scopeHints.routes.includes('UART'), 'UART scope missing')
  assert(packet.scopeHints.layers.includes('GUI'), 'GUI layer missing')
  assert(packet.decisionPolicy.includes('never auto-promotes'), 'explicit reviewer policy missing')
  assert(packet.reviewGuidance.length > 0, `${capability} guidance missing`)
  assert(packet.validationPlanHints.some(item => item.kind === 'build'), 'post-Gate build hint missing')
}

const lifecyclePacket = adapter.prepareReview({
  projectId: 'et-tool',
  taskId: 'ADAPTER-LIFECYCLE-EVIDENCE',
  gateId: 'G050.030.010',
  capability: 'lifecycle.review',
  taskIntent: 'ET6003 UART GUI progress cleanup and exit resource lifecycle',
  change: {
    files: ['source/apps/gui/chips/et6003/uart/et6003_uart_panel.cpp'],
    patch: 'diff --git a/x b/x\n+cleanup();\n',
  },
})
assert(lifecyclePacket.architectureCandidates.length > 0, 'Architecture candidates missing')
assert(lifecyclePacket.ruleCandidates.length > 0, 'Rule candidates missing')
assert(lifecyclePacket.knowledgeCandidates.length > 0, 'Knowledge candidates missing')

const before = gates.checkGateSetEvidence('et-tool', lifecyclePacket.taskId, [lifecyclePacket.gateId])
assert(before.canComplete === false, 'MUST Gate must block before review evidence')
let blockedPass = false
try {
  adapter.recordReviewDecision({
    packetId: lifecyclePacket.packetId,
    result: 'PASS',
    summary: 'invalid pass',
    reviewer: 'agent',
    reviewerId: 'pilot-agent',
    findings: [{ severity: 'BLOCK', summary: 'cleanup missing on cancel' }],
  })
} catch {
  blockedPass = true
}
assert(blockedPass, 'PASS with BLOCK finding must be rejected')

const failEvidence = adapter.recordReviewDecision({
  packetId: lifecyclePacket.packetId,
  result: 'BLOCK',
  summary: 'Cancel cleanup path is incomplete.',
  reviewer: 'agent',
  reviewerId: 'pilot-agent',
  findings: [{ severity: 'BLOCK', summary: 'cancel path skips cleanup', refs: ['R300.600.020'] }],
})
assert(failEvidence.result === 'BLOCK', 'BLOCK decision result mismatch')
assert(gates.checkGateSetEvidence('et-tool', lifecyclePacket.taskId, [lifecyclePacket.gateId]).canComplete === false, 'FAIL evidence must not release MUST Gate')

const passEvidence = adapter.recordReviewDecision({
  packetId: lifecyclePacket.packetId,
  result: 'PASS',
  summary: 'Agent reviewed all async/progress exit paths; no blocking issue remains.',
  reviewer: 'agent',
  reviewerId: 'pilot-agent',
  findings: [{ severity: 'INFO', summary: 'cleanup paths reviewed' }],
})
assert(passEvidence.result === 'PASS', 'PASS decision result mismatch')
const after = gates.checkGateSetEvidence('et-tool', lifecyclePacket.taskId, [lifecyclePacket.gateId])
assert(after.canComplete === true, 'explicit PASS evidence should release MUST Gate')
assert(after.gates[0].evidenceRefs.includes(passEvidence.evidenceId), 'PASS Evidence not linked to Gate')

console.log('  7 capability providers + review packets = PASS')
console.log('  explicit Agent BLOCK/PASS decision + Gate Evidence guard = PASS')
await reviewFiber.dispose(); await tick()
for (const capability of capabilityGate.keys()) {
  assert(catalog.listProviders(capability).length === 0, `${capability} provider cleanup failed`)
}
await projectFiber.dispose(); await tick()
for (let i = fibers.length - 1; i >= 0; i -= 1) { await fibers[i].dispose(); await tick() }
EOF
ET_TOOL_PROJECT_ROOT="$ROOT_DIR" node "$SMOKE_DIR/smoke.mjs"

echo '[4/5] Adapter result'
printf '%s\n' \
  'PHASE4_ETTOOL_CODE_REVIEW_ADAPTER_V0_1_INTEGRATION=PASS' \
  'ETTOOL_REVIEW_CAPABILITIES=7' \
  'AUTO_PASS=false' \
  "CORDIS_VERSION=$CORDIS_VERSION"
echo '[5/5] DONE'
