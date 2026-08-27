#!/usr/bin/env bash
set -euo pipefail

CORDIS_VERSION="${CORDIS_VERSION:-4.0.1}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${PHASE3_RULE_VALIDATION_WORK_DIR:-$(mktemp -d)}"
SMOKE_DIR="$WORK_DIR/cordis-smoke"
SYNTHETIC_ROOT="$WORK_DIR/project-root"

# shellcheck source=lib/common_runtime.sh
source "$ROOT_DIR/agent_harness/validation/lib/common_runtime.sh"

cleanup() {
  if [[ "${PHASE3_RULE_KEEP_VALIDATION_WORK_DIR:-0}" != "1" ]]; then
    rm -rf "$WORK_DIR"
  else
    echo "保留验证目录: $WORK_DIR"
  fi
}
trap cleanup EXIT

mkdir -p "$SMOKE_DIR" "$SYNTHETIC_ROOT"
export npm_config_registry="$NPM_REGISTRY"

echo "[0/5] 环境预检"
echo "  validation mode = $HARNESS_VALIDATION_MODE"
node --version
npm --version
npm ping --registry "$NPM_REGISTRY" >/dev/null

echo "[1/5] 构建并测试 Project Contract + Governance Core"
npm_install_if_needed "$ROOT_DIR/agent_harness/project_contract" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
(
  cd "$ROOT_DIR/agent_harness/project_contract"
  npm test
  npm run build
)

npm_install_if_needed "$ROOT_DIR/agent_harness/governance_core" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
(
  cd "$ROOT_DIR/agent_harness/governance_core"
  npm test
  npm run build
)

echo "[2/5] 构建并测试 Project Manager + Rule Manager"
npm_install_if_needed "$ROOT_DIR/agent_harness/public_plugins/project_manager" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
(
  cd "$ROOT_DIR/agent_harness/public_plugins/project_manager"
  npm test
  npm run build
)

npm_install_if_needed "$ROOT_DIR/agent_harness/public_plugins/rule_manager" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
(
  cd "$ROOT_DIR/agent_harness/public_plugins/rule_manager"
  npm test
  npm run build
)

echo "[3/5] 准备真实 Cordis Runtime"
cd "$SMOKE_DIR"
npm init -y >/dev/null
npm pkg set type=module >/dev/null
npm_install_if_needed "$SMOKE_DIR" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS" \
  "@deepseek-ai/cordis@$CORDIS_VERSION" \
  "$ROOT_DIR/agent_harness/governance_core" \
  "$ROOT_DIR/agent_harness/project_contract" \
  "$ROOT_DIR/agent_harness/public_plugins/project_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/rule_manager"

echo "[4/5] 真实 Cordis：项目注册、Rule 接入、路由、拒绝与卸载"
cat > smoke.mjs <<'EOF'
import { mkdirSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { Context } from '@deepseek-ai/cordis'
import GovernanceCatalogService from '@agent-harness/governance-core'
import * as projectManagerPlugin from '@agent-harness/project-manager'
import * as ruleManagerPlugin from '@agent-harness/rule-manager'

const tick = () => new Promise(resolve => setTimeout(resolve, 0))
const assert = (condition, message) => {
  if (!condition) throw new Error(message)
}
const expectThrow = (fn, expected) => {
  try {
    fn()
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    assert(message.includes(expected), `异常不包含 ${expected}: ${message}`)
    return
  }
  throw new Error(`期望抛出异常: ${expected}`)
}

const root = process.env.SYNTHETIC_PROJECT_ROOT
assert(root, 'SYNTHETIC_PROJECT_ROOT 未设置')
const rulesRoot = join(root, 'rules')
mkdirSync(rulesRoot, { recursive: true })

const validRules = `# [R010] Interface Rules

## [R010.010] Visual Style

### [R010.010.010] Theme

#### [R010.010.010.010] Theme Token
Level: MUST
When: 修改 UI 主题、颜色或视觉样式
Rule: 必须使用项目统一主题变量。
Refs: [A010.010.010]

#### [R010.010.010.020] Theme Literal
Level: MUST_NOT
When: 新增或修改 UI 颜色值
Rule: 禁止在业务组件中新增未登记的独立颜色常量。
`

writeFileSync(join(rulesRoot, '00_INDEX.md'), `---
interface: project-resource-index-v0.1
resource: rules
standard: rule-v0.1
files:
  - id: R010
    file: 010_interface.md
    title: Interface Rules
    summary: UI visual style constraints
    aliases: [ui, interface, style, theme]
---
`)
writeFileSync(join(rulesRoot, '010_interface.md'), validRules)

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
const coreFiber = ctx.plugin(GovernanceCatalogService)
await tick()
const catalog = ctx.get('governanceCatalog')
assert(catalog, 'ctx.governanceCatalog 未暴露')

const projectManagerFiber = ctx.plugin(projectManagerPlugin)
await tick()
const projectManager = ctx.get('projectManager')
assert(projectManager, 'ctx.projectManager 未暴露')
console.log('  ctx.projectManager = PASS')

const ruleFiber = ctx.plugin(ruleManagerPlugin)
await tick()
const ruleManager = ctx.get('ruleManager')
assert(ruleManager, 'ctx.ruleManager 未暴露')
assert(
  catalog.listProviders('rule.navigate').some(item => item.providerId === 'public.rule-manager.default'),
  'rule.navigate Provider 未注册',
)
console.log('  rule.navigate provider = PASS')

const disposeProject = projectManager.registerProject(manifest, root)
const snapshot = ruleManager.refreshProject('synthetic-project')
assert(snapshot.state === 'ready', 'Rule index 未进入 READY')
assert(snapshot.ruleCount === 2, `Rule count 错误: ${snapshot.ruleCount}`)
console.log('  admission / index build = PASS')

const route = ruleManager.searchRules({
  projectId: 'synthetic-project',
  query: 'ui theme 主题',
  limit: 4,
})
assert(route.some(item => item.id === 'R010.010.010.010'), '自然语言路由未命中 Theme Token')
assert(route.every(item => item.projectId === 'synthetic-project'), 'Candidate project_id 丢失')
assert(route.every(item => item.provenance?.resource === 'project://synthetic-project/rules'), 'Candidate provenance 错误')
console.log('  Index → File → Rule Tree route = PASS')

const exact = ruleManager.searchRules({
  projectId: 'synthetic-project',
  query: 'R010.010.010.020',
})
assert(exact.length === 1 && exact[0].id === 'R010.010.010.020', '稳定 Rule ID 精确寻址失败')
assert(exact[0].relevance === 1, '稳定 Rule ID 应为最高优先级')
console.log('  stable Rule ID route = PASS')

writeFileSync(
  join(rulesRoot, '010_interface.md'),
  '# [R010] Root\n## [R010.010] Leaf\nWhen: 任意\nRule: 必须执行。\n',
)
expectThrow(() => ruleManager.refreshProject('synthetic-project'), '缺少合法 Level')
expectThrow(() => ruleManager.getIndex('synthetic-project'), '缺少合法 Level')
console.log('  invalid refresh rejects and clears stale cache = PASS')

writeFileSync(join(rulesRoot, '010_interface.md'), validRules)
ruleManager.refreshProject('synthetic-project')
disposeProject()
expectThrow(
  () => ruleManager.searchRules({ projectId: 'synthetic-project', query: 'ui' }),
  '找不到项目',
)
console.log('  project removal invalidates route = PASS')

await ruleFiber.dispose()
await tick()
assert(ctx.get('ruleManager') === undefined, 'Rule Manager Service 未清理')
assert(
  !catalog.listProviders('rule.navigate').some(item => item.providerId === 'public.rule-manager.default'),
  'Rule Manager Provider 未清理',
)
assert(
  !catalog.listPlugins().some(item => item.manifest.pluginId === 'public.rule-manager'),
  'Rule Manager admission 未清理',
)
console.log('  rule plugin unload cleanup = PASS')

await projectManagerFiber.dispose()
await tick()
assert(ctx.get('projectManager') === undefined, 'Project Manager Service 未清理')

await coreFiber.dispose()
await tick()
assert(ctx.get('governanceCatalog') === undefined, 'Governance Core Service 未清理')
console.log('  upstream unload cleanup = PASS')
EOF

SYNTHETIC_PROJECT_ROOT="$SYNTHETIC_ROOT" node smoke.mjs

echo "[5/5] Phase 3 Rule Manager Gate"
printf '%s\n' \
  'PHASE3_RULE_MANAGER_INTEGRATION=PASS' \
  "VALIDATION_MODE=$HARNESS_VALIDATION_MODE" \
  "CORDIS_VERSION=$CORDIS_VERSION"
