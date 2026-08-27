#!/usr/bin/env bash
set -euo pipefail

CORDIS_VERSION="${CORDIS_VERSION:-4.0.1}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${PHASE3_PUBLIC_VALIDATION_WORK_DIR:-$(mktemp -d)}"
SMOKE_DIR="$WORK_DIR/cordis-smoke"
PROJECT_ROOT="$WORK_DIR/synthetic-project"
RUNTIME_ROOT="$WORK_DIR/runtime"
source "$ROOT_DIR/agent_harness/validation/lib/common_runtime.sh"

cleanup() {
  if [[ "${PHASE3_PUBLIC_KEEP_VALIDATION_WORK_DIR:-0}" != "1" ]]; then rm -rf "$WORK_DIR"; fi
}
trap cleanup EXIT
mkdir -p "$SMOKE_DIR" "$PROJECT_ROOT" "$RUNTIME_ROOT"
export npm_config_registry="$NPM_REGISTRY"
export AGENT_HARNESS_STATE_ROOT="$RUNTIME_ROOT"

echo "[0/6] 环境预检"
node --version
npm --version
npm ping --registry "$NPM_REGISTRY" >/dev/null

echo "[1/6] 构建公共基础与全部公共插件"
PACKAGES=(
  project_contract
  governance_core
  public_plugins/project_manager
  public_plugins/architecture_navigator
  public_plugins/rule_manager
  public_plugins/knowledge_manager
  public_plugins/evidence_state_manager
  public_plugins/gate_manager
  public_plugins/context_builder
  public_plugins/experience_memory_manager
)
for dir in "${PACKAGES[@]}"; do
  npm_install_if_needed "$ROOT_DIR/agent_harness/$dir" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
  (cd "$ROOT_DIR/agent_harness/$dir" && npm test && npm run build)
done

echo "[2/6] 准备真实 Cordis Runtime"
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
  "$ROOT_DIR/agent_harness/public_plugins/context_builder" \
  "$ROOT_DIR/agent_harness/public_plugins/experience_memory_manager"

echo "[3/6] 创建完全虚拟 Project Plugin 数据"
mkdir -p "$PROJECT_ROOT/architecture" "$PROJECT_ROOT/rules" "$PROJECT_ROOT/knowledge" "$PROJECT_ROOT/gates"
printf 'synthetic\n' > "$PROJECT_ROOT/project.marker"

cat > "$PROJECT_ROOT/architecture/00_INDEX.md" <<'EOF'
---
interface: project-resource-index-v0.1
resource: architecture
standard: architecture-v0.1
files:
  - id: A010
    file: 010_interface.md
    title: Interface Architecture
    summary: UI theme and layout architecture
    aliases: [ui, interface, theme, style, layout]
---
EOF
cat > "$PROJECT_ROOT/architecture/010_interface.md" <<'EOF'
# [A010] Interface Architecture
Role: application interface layer
Resources: source/ui/

## [A010.010] Visual System
Role: UI visual system

### [A010.010.010] Theme
Role: theme variables and runtime appearance
Boundary: does not define mandatory coding rules
Resources: source/ui/theme/
Relations: R010.010.010
EOF

cat > "$PROJECT_ROOT/rules/00_INDEX.md" <<'EOF'
---
interface: project-resource-index-v0.1
resource: rules
standard: rule-v0.1
files:
  - id: R010
    file: 010_interface.md
    title: Interface Rules
    summary: UI theme and style constraints
    aliases: [ui, theme, style, visual]
---
EOF
cat > "$PROJECT_ROOT/rules/010_interface.md" <<'EOF'
# [R010] Interface Rules

## [R010.010] Visual Rules

### [R010.010.010] Theme Variables
Level: MUST
When: 修改 UI 主题、颜色或视觉样式
Rule: 必须复用项目统一主题变量。
Refs: [A010.010.010, G010.010.010]
EOF

cat > "$PROJECT_ROOT/knowledge/00_INDEX.md" <<'EOF'
---
interface: project-resource-index-v0.1
resource: knowledge
standard: knowledge-v0.1
files:
  - id: K010
    file: 010_interface.md
    title: Interface Knowledge
    summary: UI theme runtime knowledge and lessons
    aliases: [ui, theme, runtime, refresh, visual]
---
EOF
cat > "$PROJECT_ROOT/knowledge/010_interface.md" <<'EOF'
# [K010] Interface Knowledge

## [K010.010] Theme Knowledge

### [K010.010.010] Theme Source
Status: VALIDATED
Fact: UI 主题变量由统一主题入口提供。
Scope: ui theme
Provenance: DESIGN-BASELINE
Refs: [A010.010.010]
EOF

cat > "$PROJECT_ROOT/gates/00_INDEX.md" <<'EOF'
---
interface: project-resource-index-v0.1
resource: gates
standard: gate-v0.1
files:
  - id: G010
    file: 010_validation.yaml
    title: Interface Validation
    summary: UI build and validation gates
    aliases: [ui, build, test, validation, theme]
---
EOF
cat > "$PROJECT_ROOT/gates/010_validation.yaml" <<'EOF'
standard: gate-v0.1
file_id: G010
title: Interface Validation
nodes:
  - id: G010.010
    title: UI Validation
    children:
      - id: G010.010.010
        title: UI Build And Test
        gate:
          level: MUST
          when: 修改 UI 主题、颜色、布局或相关实现
          steps:
            - id: build
              tool: build.execute
            - id: test
              tool: test.execute
          pass:
            mode: all_steps_pass
          refs: [R010.010.010]
EOF

echo "[4/6] 模拟 Agent 完整公共插件工作流"
cat > "$SMOKE_DIR/smoke.mjs" <<'EOF'
import { Context } from '@deepseek-ai/cordis'
import GovernanceCatalogService from '@agent-harness/governance-core'
import * as projectManagerPlugin from '@agent-harness/project-manager'
import * as architecturePlugin from '@agent-harness/architecture-navigator'
import * as rulePlugin from '@agent-harness/rule-manager'
import * as knowledgePlugin from '@agent-harness/knowledge-manager'
import * as evidencePlugin from '@agent-harness/evidence-state-manager'
import * as gatePlugin from '@agent-harness/gate-manager'
import * as contextPlugin from '@agent-harness/context-builder'
import * as experiencePlugin from '@agent-harness/experience-memory-manager'

const tick = () => new Promise(resolve => setTimeout(resolve, 0))
const assert = (condition, message) => { if (!condition) throw new Error(message) }
const root = process.env.SYNTHETIC_PROJECT_ROOT
assert(root, 'SYNTHETIC_PROJECT_ROOT 未设置')

const manifest = {
  contract_version: '0.1',
  project: {
    id: 'synthetic-project',
    name: 'Synthetic Project',
    aliases: ['synthetic'],
  },
  root: { markers: ['project.marker'] },
  resources: {
    architecture: { path: 'architecture/', standard: 'architecture-v0.1' },
    rules: { path: 'rules/', standard: 'rule-v0.1' },
    knowledge: { path: 'knowledge/', standard: 'knowledge-v0.1' },
    gates: { path: 'gates/', standard: 'gate-v0.1' },
  },
  adapters: {},
}

const ctx = new Context()
const fibers = []
fibers.push(ctx.plugin(GovernanceCatalogService)); await tick()
fibers.push(ctx.plugin(projectManagerPlugin)); await tick()
fibers.push(ctx.plugin(architecturePlugin)); await tick()
fibers.push(ctx.plugin(rulePlugin)); await tick()
fibers.push(ctx.plugin(knowledgePlugin)); await tick()
fibers.push(ctx.plugin(evidencePlugin)); await tick()
fibers.push(ctx.plugin(gatePlugin)); await tick()
fibers.push(ctx.plugin(contextPlugin)); await tick()
fibers.push(ctx.plugin(experiencePlugin)); await tick()

const catalog = ctx.get('governanceCatalog')
const pm = ctx.get('projectManager')
const arch = ctx.get('architectureNavigator')
const rules = ctx.get('ruleManager')
const knowledge = ctx.get('knowledgeManager')
const evidence = ctx.get('evidenceStateManager')
const gates = ctx.get('gateManager')
const context = ctx.get('contextBuilder')
const memory = ctx.get('experienceMemoryManager')
assert(catalog && pm && arch && rules && knowledge && evidence && gates && context && memory, '公共 Service 未全部暴露')

const requiredCapabilities = [
  'governance.project',
  'architecture.navigate',
  'rule.navigate',
  'knowledge.navigate',
  'gate.navigate',
  'context.build',
  'evidence.record',
  'evidence.read',
  'state.read',
  'state.update',
  'experience.manage',
  'memory.context',
]
for (const capability of requiredCapabilities) {
  assert(catalog.listProviders(capability).length > 0, `缺少公共 Provider: ${capability}`)
}
console.log('  public capability providers = PASS')

const disposeProject = pm.registerProject(manifest, root)
arch.refreshProject('synthetic-project')
rules.refreshProject('synthetic-project')
knowledge.refreshProject('synthetic-project')
gates.refreshProject('synthetic-project')
console.log('  four project resource interfaces READY = PASS')

const archHit = arch.searchArchitecture({ projectId: 'synthetic-project', query: 'ui theme style' })
  .find(item => item.id === 'A010.010.010')
const ruleHit = rules.searchRules({ projectId: 'synthetic-project', query: 'ui theme style' })
  .find(item => item.id === 'R010.010.010')
const knowledgeHit = knowledge.searchKnowledge({ projectId: 'synthetic-project', query: 'ui theme runtime' })
  .find(item => item.id === 'K010.010.010')
const gateHit = gates.searchGates({ projectId: 'synthetic-project', query: 'ui theme build validation' })
  .find(item => item.id === 'G010.010.010')
assert(archHit && ruleHit && knowledgeHit && gateHit, 'Router 未返回完整任务候选')
console.log('  project routers = PASS')

const pack = context.buildContext({
  projectId: 'synthetic-project',
  taskSummary: '修改 UI 设计风格',
  references: [
    { kind: 'architecture', id: archHit.id, priority: 'high' },
    { kind: 'rule', id: ruleHit.id },
    { kind: 'knowledge', id: knowledgeHit.id },
    { kind: 'gate', id: gateHit.id },
  ],
  maxChars: 12000,
})
assert(pack.items.some(item => item.id === ruleHit.id && item.required), 'MUST Rule 未强制保留')
assert(pack.items.some(item => item.id === gateHit.id && item.required), 'MUST Gate 未强制保留')
console.log('  selected minimal Context Pack = PASS')

const taskId = 'TASK-UI-STYLE'
const before = gates.checkGateSetEvidence('synthetic-project', taskId, [gateHit.id])
assert(before.canComplete === false, 'MUST Gate 无 PASS Evidence 时不应允许完成')

// 模拟 Agent 调用 Tool Capability 后把结果记录为 Evidence。
const passEvidence = evidence.recordEvidence({
  projectId: 'synthetic-project',
  taskId,
  kind: 'gate',
  result: 'PASS',
  summary: 'build.execute + test.execute passed',
  source: 'agent-tool-execution',
  gateId: gateHit.id,
})
const after = gates.checkGateSetEvidence('synthetic-project', taskId, [gateHit.id])
assert(after.canComplete === true, 'MUST Gate PASS Evidence 后仍阻塞')
console.log('  MUST Gate Evidence guard = PASS')

const state = evidence.updateState({
  projectId: 'synthetic-project',
  scope: `task:${taskId}`,
  key: 'validation',
  value: 'PASS',
  reason: 'all applicable MUST gates have PASS evidence',
  evidenceRefs: [passEvidence.evidenceId],
  expectedVersion: 0,
})
assert(state.version === 1, 'State version 错误')
console.log('  Evidence-backed State = PASS')

// Agent 自己总结经验语义，公共插件只管理候选。
const experience = memory.recordCandidate({
  projectId: 'synthetic-project',
  taskId,
  title: 'Theme Runtime Refresh',
  fact: '修改主题后需要重新读取运行时状态以确认最终生效值。',
  scope: 'ui theme runtime',
  evidenceRefs: [passEvidence.evidenceId],
  refs: [archHit.id, ruleHit.id, gateHit.id],
})
const memoryHit = memory.searchMemory({ projectId: 'synthetic-project', query: '主题 运行时 状态' })
  .find(item => item.id === experience.candidateId)
assert(memoryHit, 'Experience Candidate 未进入跨任务 Memory')
assert(memoryHit.warnings?.length > 0, '未晋级经验必须有警告')
console.log('  experience candidate memory = PASS')

// Agent 明确决定知识分类与稳定 K 地址。
const promotion = memory.promoteToKnowledge('synthetic-project', {
  candidateId: experience.candidateId,
  fileId: 'K010',
  parentNodeId: 'K010.010',
  nodeId: 'K010.010.020',
  title: 'Theme Runtime Refresh',
})
assert(promotion.knowledgeId === 'K010.010.020', 'Knowledge promotion ID 错误')
const promotedKnowledge = knowledge.getNode('synthetic-project', 'K010.010.020')?.node
assert(promotedKnowledge?.status === 'VALIDATED', 'Experience 晋级后不是 VALIDATED Knowledge')
assert(memory.getCandidate('synthetic-project', experience.candidateId)?.status === 'PROMOTED', 'Experience 状态未更新 PROMOTED')
console.log('  evidence-backed Knowledge promotion = PASS')

const promotedRoute = knowledge.searchKnowledge({
  projectId: 'synthetic-project',
  query: 'theme runtime refresh 状态',
})
assert(promotedRoute.some(item => item.id === 'K010.010.020'), '晋级后的 Knowledge 无法路由')
console.log('  promoted Knowledge route = PASS')

disposeProject()
for (let index = fibers.length - 1; index >= 1; index -= 1) {
  await fibers[index].dispose()
  await tick()
}
await fibers[0].dispose(); await tick()
assert(ctx.get('projectManager') === undefined, 'Project Manager 未清理')
assert(ctx.get('architectureNavigator') === undefined, 'Architecture Navigator 未清理')
assert(ctx.get('ruleManager') === undefined, 'Rule Manager 未清理')
assert(ctx.get('knowledgeManager') === undefined, 'Knowledge Manager 未清理')
assert(ctx.get('gateManager') === undefined, 'Gate Manager 未清理')
assert(ctx.get('contextBuilder') === undefined, 'Context Builder 未清理')
assert(ctx.get('evidenceStateManager') === undefined, 'Evidence State Manager 未清理')
assert(ctx.get('experienceMemoryManager') === undefined, 'Experience Memory Manager 未清理')
console.log('  public plugin lifecycle cleanup = PASS')
EOF

SYNTHETIC_PROJECT_ROOT="$PROJECT_ROOT" node "$SMOKE_DIR/smoke.mjs"

echo "[5/6] 公共插件与真实项目内容解耦"
PROJECTS_PATH_TOKEN='agent_harness'"/projects/"
if grep -q "$PROJECTS_PATH_TOKEN" "$0"; then
  echo "Public Plugin Gate 不得直接读取真实 Project Plugin 内容" >&2
  exit 1
fi
echo "  Public Plugin Gate uses synthetic Project only = PASS"

echo "[6/6] Public Plugins v0.1 Gate"
printf '%s\n' \
  'PHASE3_PUBLIC_PLUGINS_V0_1_INTEGRATION=PASS' \
  "VALIDATION_MODE=$HARNESS_VALIDATION_MODE" \
  "CORDIS_VERSION=$CORDIS_VERSION"
