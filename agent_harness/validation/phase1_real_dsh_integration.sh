#!/usr/bin/env bash
set -euo pipefail

DSH_VERSION="${DSH_VERSION:-0.1.0-rc.8}"
CORDIS_VERSION="${CORDIS_VERSION:-4.0.1}"
PNPM_VERSION="${PNPM_VERSION:-11.7.0}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${PHASE1_VALIDATION_WORK_DIR:-$(mktemp -d)}"
PACK_DIR="$WORK_DIR/packs"
DSH_HOME="$WORK_DIR/dsh-home"
HOST_DIR="$WORK_DIR/dsh-host"
SMOKE_DIR="$WORK_DIR/cordis-smoke"

cleanup() {
  if [[ "${PHASE1_KEEP_VALIDATION_WORK_DIR:-0}" != "1" ]]; then
    rm -rf "$WORK_DIR"
  else
    echo "保留验证目录: $WORK_DIR"
  fi
}
trap cleanup EXIT

run_with_timeout() {
  local seconds="$1"
  shift
  if command -v timeout >/dev/null 2>&1; then
    timeout "${seconds}s" "$@"
  else
    "$@"
  fi
}

npm_install() {
  echo "  npm registry: $NPM_REGISTRY"
  echo "  npm install timeout: ${NPM_INSTALL_TIMEOUT_SECONDS}s"

  local cmd=(
    npm install
    --registry "$NPM_REGISTRY"
    --no-audit
    --no-fund
    --fetch-retries 1
    --fetch-retry-mintimeout 2000
    --fetch-retry-maxtimeout 10000
    --fetch-timeout 60000
    --loglevel info
  )

  local status=0
  run_with_timeout "$NPM_INSTALL_TIMEOUT_SECONDS" "${cmd[@]}" "$@" || status=$?
  if [[ "$status" -ne 0 ]]; then
    echo >&2
    echo "npm install 失败或超时（exit=$status）。先检查网络：" >&2
    echo "  npm ping --registry $NPM_REGISTRY" >&2
    echo "  npm view @deepseek-ai/cordis version --registry $NPM_REGISTRY" >&2
    echo >&2
    echo "如果官方 npm 在你的网络环境不可达，可临时重跑：" >&2
    echo "  NPM_REGISTRY=https://registry.npmmirror.com bash agent_harness/validation/phase1_real_dsh_integration.sh" >&2
    return "$status"
  fi
}

ensure_pnpm() {
  if command -v pnpm >/dev/null 2>&1; then
    echo "  pnpm: $(pnpm --version)"
    return
  fi

  echo "  安装 pnpm@$PNPM_VERSION"
  npm install --global "pnpm@$PNPM_VERSION" \
    --registry "$NPM_REGISTRY" \
    --no-audit \
    --no-fund
}

write_dsh_pnpm_policy() {
  cat > pnpm-workspace.yaml <<'EOF'
# Phase 1 integration-only build-script allowlist.
# These are the exact packages reported by pnpm 11.7.0 for
# @deepseek-ai/dsh 0.1.0-rc.8. Any newly introduced build-script dependency
# remains blocked and must be reviewed before this list is changed.
allowBuilds:
  '@deepseek-ai/dsh-subprocess-local': true
  '@google/genai': true
  koffi: true
  node-pty: true
  protobufjs: true
EOF
}

mkdir -p "$PACK_DIR" "$HOST_DIR" "$SMOKE_DIR"
export DSH_HOME
# npm, pnpm and dsh-plugin-spawned pnpm all use the same selected registry.
export npm_config_registry="$NPM_REGISTRY"

echo "[0/5] npm 网络预检"
npm --version
node --version
if ! run_with_timeout 30 npm ping --registry "$NPM_REGISTRY"; then
  echo >&2
  echo "npm registry 当前不可访问，先不要继续等待。" >&2
  echo "可以尝试：" >&2
  echo "  NPM_REGISTRY=https://registry.npmmirror.com bash agent_harness/validation/phase1_real_dsh_integration.sh" >&2
  exit 20
fi

echo "[1/5] 构建并测试治理核心"
cd "$ROOT_DIR/agent_harness/governance_core"
echo "  [1.1] 安装 governance_core 依赖"
npm_install
echo "  [1.2] 运行 governance_core 单测"
npm test
echo "  [1.3] 编译 governance_core"
npm run build
echo "  [1.4] 打包 governance_core"
npm pack --pack-destination "$PACK_DIR" >/dev/null

echo "[2/5] 构建示例治理插件"
cd "$ROOT_DIR/agent_harness/examples/governance_demo_plugin"
echo "  [2.1] 安装 demo plugin 依赖"
npm_install
echo "  [2.2] 编译 demo plugin"
npm run build
echo "  [2.3] 打包 demo plugin"
npm pack --pack-destination "$PACK_DIR" >/dev/null

CORE_TGZ="$(find "$PACK_DIR" -maxdepth 1 -name 'agent-harness-governance-core-*.tgz' -print -quit)"
DEMO_TGZ="$(find "$PACK_DIR" -maxdepth 1 -name 'agent-harness-governance-demo-plugin-*.tgz' -print -quit)"
test -n "$CORE_TGZ"
test -n "$DEMO_TGZ"

echo "[3/5] 安装真实 DeepSeek Harness $DSH_VERSION"
cd "$HOST_DIR"
npm init -y >/dev/null
ensure_pnpm
write_dsh_pnpm_policy
echo "  [3.1] 使用 pnpm 安装 @deepseek-ai/dsh@$DSH_VERSION"
echo "  [3.1] build-script allowlist 已启用（新增脚本仍默认拒绝）"
pnpm add \
  --registry "$NPM_REGISTRY" \
  --reporter append-only \
  "@deepseek-ai/dsh@$DSH_VERSION"
DSH_BIN="$HOST_DIR/node_modules/.bin/dsh"
test -x "$DSH_BIN"
echo "  DeepSeek Harness install = PASS"

echo "[4/5] 通过 dsh plugin 安装两个 Bundle 并验证组合树"
"$DSH_BIN" plugin --profile phase1 add "$CORE_TGZ" "$DEMO_TGZ"
"$DSH_BIN" --profile phase1 --dump-config > "$WORK_DIR/dsh-dump-config.txt"
grep -q 'id: agent-governance-core' "$WORK_DIR/dsh-dump-config.txt"
grep -q 'id: agent-harness-governance-demo-plugin' "$WORK_DIR/dsh-dump-config.txt"
echo "  DSH Bundle install/composition = PASS"

echo "[5/5] 使用真实 Cordis Runtime 验证 Service / Provider / 卸载清理"
cd "$SMOKE_DIR"
npm init -y >/dev/null
npm pkg set type=module >/dev/null
echo "  [5.1] 安装真实 Cordis Runtime 与两个本地 Bundle"
npm_install "@deepseek-ai/cordis@$CORDIS_VERSION" "$CORE_TGZ" "$DEMO_TGZ"
cat > smoke.mjs <<'EOF'
import { Context } from '@deepseek-ai/cordis'
import GovernanceCatalogService from '@agent-harness/governance-core'
import * as demoPlugin from '@agent-harness/governance-demo-plugin'

const tick = () => new Promise(resolve => setTimeout(resolve, 0))
const assert = (condition, message) => {
  if (!condition) throw new Error(message)
}

const ctx = new Context()
const coreFiber = ctx.plugin(GovernanceCatalogService)
await tick()

const catalog = ctx.get('governanceCatalog')
assert(catalog, 'ctx.governanceCatalog 未暴露')
console.log('  ctx.governanceCatalog = PASS')

const demoFiber = ctx.plugin(demoPlugin)
await tick()
assert(
  catalog.listPlugins().some(item => item.manifest.pluginId === 'example.rule-provider'),
  '示例治理插件未准入',
)
assert(
  catalog.listProviders('rule.resolve').some(item => item.providerId === 'example.rule-provider.default'),
  '示例 Provider 未注册',
)
console.log('  demo admission/provider = PASS')

await demoFiber.dispose()
await tick()
assert(
  !catalog.listProviders('rule.resolve').some(item => item.providerId === 'example.rule-provider.default'),
  '插件卸载后 Provider 未清理',
)
assert(
  !catalog.listPlugins().some(item => item.manifest.pluginId === 'example.rule-provider'),
  '插件卸载后治理记录未清理',
)
console.log('  demo unload cleanup = PASS')

await coreFiber.dispose()
await tick()
assert(ctx.get('governanceCatalog') === undefined, '治理核心卸载后 Service 未移除')
console.log('  core service unload cleanup = PASS')
EOF
node smoke.mjs

echo
printf '%s\n' \
  'PHASE1_REAL_DSH_INTEGRATION=PASS' \
  "DSH_VERSION=$DSH_VERSION" \
  "CORDIS_VERSION=$CORDIS_VERSION"
