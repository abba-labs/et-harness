#!/usr/bin/env bash
set -euo pipefail

CORDIS_VERSION="${CORDIS_VERSION:-4.0.1}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${PHASE3_KNOWLEDGE_VALIDATION_WORK_DIR:-$(mktemp -d)}"
SMOKE_DIR="$WORK_DIR/cordis-smoke"
SYNTHETIC_ROOT="$WORK_DIR/project-root"

source "$ROOT_DIR/agent_harness/validation/lib/common_runtime.sh"

cleanup() {
  if [[ "${PHASE3_KNOWLEDGE_KEEP_VALIDATION_WORK_DIR:-0}" != "1" ]]; then rm -rf "$WORK_DIR"; fi
}
trap cleanup EXIT
mkdir -p "$SMOKE_DIR" "$SYNTHETIC_ROOT"
export npm_config_registry="$NPM_REGISTRY"

echo "[0/5] 环境预检"
node --version
npm --version
npm ping --registry "$NPM_REGISTRY" >/dev/null

echo "[1/5] 构建公共基础包"
for dir in project_contract governance_core public_plugins/project_manager; do
  npm_install_if_needed "$ROOT_DIR/agent_harness/$dir" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
  (cd "$ROOT_DIR/agent_harness/$dir" && npm test && npm run build)
done

echo "[2/5] 构建 Knowledge Manager"
npm_install_if_needed "$ROOT_DIR/agent_harness/public_plugins/knowledge_manager" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
(cd "$ROOT_DIR/agent_harness/public_plugins/knowledge_manager" && npm test && npm run build)

echo "[3/5] 准备真实 Cordis Runtime"
cd "$SMOKE_DIR"
npm init -y >/dev/null
npm pkg set type=module >/dev/null
npm_install_if_needed "$SMOKE_DIR" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS" \
  "@deepseek-ai/cordis@$CORDIS_VERSION" \
  "$ROOT_DIR/agent_harness/governance_core" \
  "$ROOT_DIR/agent_harness/project_contract" \
  "$ROOT_DIR/agent_harness/public_plugins/project_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/knowledge_manager"

echo "[4/5] 真实 Cordis smoke"
cat > smoke.mjs <<'EOF'
import { mkdirSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { Context } from '@deepseek-ai/cordis'
import GovernanceCatalogService from '@agent-harness/governance-core'
import * as projectManagerPlugin from '@agent-harness/project-manager'
import * as knowledgeManagerPlugin from '@agent-harness/knowledge-manager'

const tick = () => new Promise(resolve => setTimeout(resolve, 0))
const assert = (condition, message) => { if (!condition) throw new Error(message) }
const expectThrow = (fn, expected) => {
  try { fn() } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    assert(message.includes(expected), `异常不包含 ${expected}: ${message}`)
    return
  }
  throw new Error(`期望抛出异常: ${expected}`)
}

const root = process.env.SYNTHETIC_PROJECT_ROOT
const knowledgeRoot = join(root, 'knowledge')
mkdirSync(knowledgeRoot, { recursive: true })
writeFileSync(join(knowledgeRoot, '00_INDEX.md'), `---
interface: project-resource-index-v0.1
resource: knowledge
standard: knowledge-v0.1
files:
  - id: K010
    file: 010_interface.md
    title: Interface Knowledge
    summary: UI theme knowledge
    aliases: [ui, theme, visual, legacy]
---
`)
writeFileSync(join(knowledgeRoot, '010_interface.md'), `# [K010] Interface Knowledge

## [K010.010] Visual

### [K010.010.010] Theme Source
Status: VALIDATED
Fact: UI 主题变量来自统一主题入口。
Scope: ui theme
Provenance: TASK-100

### [K010.010.020] Legacy Finding
Status: CANDIDATE
Fact: 某旧页面可能直接保存颜色常量。
Scope: ui theme legacy
Provenance: TASK-101
`)

const manifest = {
  contract_version: '0.1',
  project: { id: 'synthetic-project', name: 'Synthetic Project' },
  root: { markers: ['marker'] },
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
const projectFiber = ctx.plugin(projectManagerPlugin)
await tick()
const projectManager = ctx.get('projectManager')
const knowledgeFiber = ctx.plugin(knowledgeManagerPlugin)
await tick()
const knowledgeManager = ctx.get('knowledgeManager')
assert(catalog && projectManager && knowledgeManager, '公共 Service 未完整暴露')
assert(catalog.listProviders('knowledge.navigate').some(item => item.providerId === 'public.knowledge-manager.default'), 'knowledge.navigate Provider 缺失')

const disposeProject = projectManager.registerProject(manifest, root)
const snapshot = knowledgeManager.refreshProject('synthetic-project')
assert(snapshot.knowledgeCount === 2, 'knowledge count 错误')
assert(snapshot.statusCounts.VALIDATED === 1 && snapshot.statusCounts.CANDIDATE === 1, 'status count 错误')
console.log('  admission / index build = PASS')

const normal = knowledgeManager.searchKnowledge({ projectId: 'synthetic-project', query: 'ui theme' })
assert(normal.some(item => item.id === 'K010.010.010'), 'VALIDATED knowledge 未命中')
assert(normal.some(item => item.id === 'K010.010.020'), '默认查询未召回 CANDIDATE')
assert(normal.find(item => item.id === 'K010.010.020')?.metadata?.trustTier === 'EXPLORATORY', 'CANDIDATE trust tier 缺失')
assert(normal.find(item => item.id === 'K010.010.020')?.warnings?.length > 0, 'CANDIDATE 使用警告缺失')
console.log('  tiered all-status route = PASS')

const candidate = knowledgeManager.searchKnowledge({
  projectId: 'synthetic-project',
  query: 'legacy theme',
  filters: { status: 'CANDIDATE' },
})
assert(candidate.some(item => item.id === 'K010.010.020'), '显式 CANDIDATE 查询失败')
console.log('  explicit candidate route = PASS')

const exact = knowledgeManager.searchKnowledge({ projectId: 'synthetic-project', query: 'K010.010.020' })
assert(exact.length === 1 && exact[0].metadata.status === 'CANDIDATE', '稳定 K ID 精确寻址失败')
assert(exact[0].warnings?.length > 0, '非 VALIDATED 精确访问缺少警告')
console.log('  stable K ID route = PASS')

writeFileSync(join(knowledgeRoot, '010_interface.md'), '# [K010] Root\n## [K010.010] Leaf\nStatus: VALIDATED\nFact: X\n')
expectThrow(() => knowledgeManager.refreshProject('synthetic-project'), '缺少 Provenance')
expectThrow(() => knowledgeManager.getIndex('synthetic-project'), '缺少 Provenance')
console.log('  invalid refresh clears stale cache = PASS')

disposeProject()
await knowledgeFiber.dispose(); await tick()
assert(ctx.get('knowledgeManager') === undefined, 'Knowledge Manager Service 未清理')
assert(!catalog.listProviders('knowledge.navigate').some(item => item.providerId === 'public.knowledge-manager.default'), 'Knowledge Provider 未清理')
await projectFiber.dispose(); await tick()
await coreFiber.dispose(); await tick()
console.log('  lifecycle cleanup = PASS')
EOF

SYNTHETIC_PROJECT_ROOT="$SYNTHETIC_ROOT" node smoke.mjs

echo "[5/5] Phase 3 Knowledge Manager Gate"
printf '%s\n' \
  'PHASE3_KNOWLEDGE_MANAGER_INTEGRATION=PASS' \
  "VALIDATION_MODE=$HARNESS_VALIDATION_MODE" \
  "CORDIS_VERSION=$CORDIS_VERSION"
