#!/usr/bin/env bash
set -euo pipefail

CORDIS_VERSION="${CORDIS_VERSION:-4.0.1}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${PHASE3_ARCH_VALIDATION_WORK_DIR:-$(mktemp -d)}"
SMOKE_DIR="$WORK_DIR/cordis-smoke"
SYNTHETIC_ROOT="$WORK_DIR/project-root"

# shellcheck source=lib/common_runtime.sh
source "$ROOT_DIR/agent_harness/validation/lib/common_runtime.sh"

cleanup() {
  if [[ "${PHASE3_ARCH_KEEP_VALIDATION_WORK_DIR:-0}" != "1" ]]; then
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

echo "[2/5] 构建并测试 Project Manager + Architecture Navigator"
npm_install_if_needed "$ROOT_DIR/agent_harness/public_plugins/project_manager" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
(
  cd "$ROOT_DIR/agent_harness/public_plugins/project_manager"
  npm test
  npm run build
)

npm_install_if_needed "$ROOT_DIR/agent_harness/public_plugins/architecture_navigator" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
(
  cd "$ROOT_DIR/agent_harness/public_plugins/architecture_navigator"
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
  "$ROOT_DIR/agent_harness/public_plugins/architecture_navigator"

echo "[4/5] 真实 Cordis：项目注册、Architecture 接入、路由、拒绝与卸载"
cat > smoke.mjs <<'EOF'
import { mkdirSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { Context } from '@deepseek-ai/cordis'
import GovernanceCatalogService from '@agent-harness/governance-core'
import * as projectManagerPlugin from '@agent-harness/project-manager'
import * as architectureNavigatorPlugin from '@agent-harness/architecture-navigator'

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
const repoRoot = process.env.ET_TOOL_REPO_ROOT
assert(root, 'SYNTHETIC_PROJECT_ROOT 未设置')
assert(repoRoot, 'ET_TOOL_REPO_ROOT 未设置')
const architectureRoot = join(root, 'architecture')
mkdirSync(architectureRoot, { recursive: true })

const validArchitecture = `# [A010] Interface Layer
Role: UI and interaction entry
Resources: source/apps/ui/

## [A010.010] Visual System
Role: UI visual style, theme and layout

### [A010.010.010] Theme
Role: theme tokens and appearance
Resources: source/apps/ui/theme/

### [A010.010.020] Layout
Role: page layout and spacing
Resources: source/apps/ui/layout/
`

writeFileSync(join(architectureRoot, '00_INDEX.md'), `---
interface: project-resource-index-v0.1
resource: architecture
standard: architecture-v0.1
files:
  - id: A010
    file: 010_interface.md
    title: Interface Layer
    summary: UI and interaction architecture
    aliases: [ui, interface, style, theme, layout]
---
`)
writeFileSync(join(architectureRoot, '010_interface.md'), validArchitecture)

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

const architectureFiber = ctx.plugin(architectureNavigatorPlugin)
await tick()
const navigator = ctx.get('architectureNavigator')
assert(navigator, 'ctx.architectureNavigator 未暴露')
assert(
  catalog.listProviders('architecture.navigate').some(item => item.providerId === 'public.architecture-navigator.default'),
  'architecture.navigate Provider 未注册',
)
console.log('  architecture.navigate provider = PASS')

const disposeProject = projectManager.registerProject(manifest, root)
const snapshot = navigator.refreshProject('synthetic-project')
assert(snapshot.state === 'ready', 'Architecture index 未进入 READY')
assert(snapshot.nodeCount === 4, `Architecture node count 错误: ${snapshot.nodeCount}`)
console.log('  admission / index build = PASS')

const route = navigator.searchArchitecture({
  projectId: 'synthetic-project',
  query: 'ui theme style',
  limit: 4,
})
assert(route.some(item => item.id === 'A010.010.010'), '自然语言路由未命中 Theme Node')
assert(route.every(item => item.projectId === 'synthetic-project'), 'Candidate project_id 丢失')
assert(route.every(item => item.provenance?.resource === 'project://synthetic-project/architecture'), 'Candidate provenance 错误')
console.log('  Index → File → Node route = PASS')

const exact = navigator.searchArchitecture({
  projectId: 'synthetic-project',
  query: 'A010.010.020',
})
assert(exact.length === 1 && exact[0].id === 'A010.010.020', '稳定 Node ID 精确寻址失败')
assert(exact[0].relevance === 1, '稳定 Node ID 应为最高优先级')
console.log('  stable Node ID route = PASS')

writeFileSync(
  join(architectureRoot, '010_interface.md'),
  '# [A010] Root\n### [A010.010] Wrong Depth\n',
)
expectThrow(() => navigator.refreshProject('synthetic-project'), '标题层级')
expectThrow(() => navigator.getIndex('synthetic-project'), '标题层级')
console.log('  invalid refresh rejects and clears stale cache = PASS')

writeFileSync(join(architectureRoot, '010_interface.md'), validArchitecture)
navigator.refreshProject('synthetic-project')
disposeProject()
expectThrow(
  () => navigator.searchArchitecture({ projectId: 'synthetic-project', query: 'ui' }),
  '找不到项目',
)
console.log('  project removal invalidates route = PASS')

const disposeEtTool = projectManager.registerProjectFromManifestFile(
  join(repoRoot, 'agent_harness/projects/et_tool/project.yaml'),
  repoRoot,
)
const etToolSnapshot = navigator.refreshProject('et-tool')
assert(etToolSnapshot.state === 'ready', 'ET-TOOL empty Architecture interface 未进入 READY')
assert(etToolSnapshot.nodeCount === 0, 'ET-TOOL 当前 Architecture 必须保持 CONTENT EMPTY')
assert(
  navigator.searchArchitecture({ projectId: 'et-tool', query: 'ui' }).length === 0,
  'ET-TOOL 空 Architecture 不应产生虚假候选',
)
disposeEtTool()
navigator.removeProject('et-tool')
console.log('  ET-TOOL empty standard interface = PASS')

await architectureFiber.dispose()
await tick()
assert(ctx.get('architectureNavigator') === undefined, 'Architecture Navigator Service 未清理')
assert(
  !catalog.listProviders('architecture.navigate').some(item => item.providerId === 'public.architecture-navigator.default'),
  'Architecture Navigator Provider 未清理',
)
assert(
  !catalog.listPlugins().some(item => item.manifest.pluginId === 'public.architecture-navigator'),
  'Architecture Navigator admission 未清理',
)
console.log('  architecture plugin unload cleanup = PASS')

await projectManagerFiber.dispose()
await tick()
assert(ctx.get('projectManager') === undefined, 'Project Manager Service 未清理')

await coreFiber.dispose()
await tick()
assert(ctx.get('governanceCatalog') === undefined, 'Governance Core Service 未清理')
console.log('  upstream unload cleanup = PASS')
EOF

SYNTHETIC_PROJECT_ROOT="$SYNTHETIC_ROOT" ET_TOOL_REPO_ROOT="$ROOT_DIR" node smoke.mjs

echo "[5/5] Phase 3 Architecture Navigator Gate"
printf '%s\n' \
  'PHASE3_ARCHITECTURE_NAVIGATOR_INTEGRATION=PASS' \
  "VALIDATION_MODE=$HARNESS_VALIDATION_MODE" \
  "CORDIS_VERSION=$CORDIS_VERSION"
