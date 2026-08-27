#!/usr/bin/env bash
set -euo pipefail

CORDIS_VERSION="${CORDIS_VERSION:-4.0.1}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${PHASE4_ETTOOL_ARCH_WORK_DIR:-$(mktemp -d)}"
SMOKE_DIR="$WORK_DIR/cordis-smoke"
PACK_DIR="$WORK_DIR/packs"
RUNTIME_ROOT="$WORK_DIR/runtime"

source "$ROOT_DIR/agent_harness/validation/lib/common_runtime.sh"

cleanup() {
  if [[ "${PHASE4_ETTOOL_ARCH_KEEP_WORK_DIR:-0}" != "1" ]]; then
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
ARCH_ROOT="$PROJECT_PLUGIN_ROOT/architecture"

printf '%s\n' '[0/6] ET-TOOL Architecture v0.1 静态预检'
ARCH_FILES=(
  00_INDEX.md
  010_chip_map.md
  020_cli_map.md
  030_gui_map.md
  040_upgrade_route_map.md
  050_shared_system_map.md
  060_product_control_validation_map.md
)
for file in "${ARCH_FILES[@]}"; do
  test -f "$ARCH_ROOT/$file"
done

grep -q 'id: A060' "$ARCH_ROOT/00_INDEX.md"
grep -q '# \[A010\] Product Capability Map' "$ARCH_ROOT/010_chip_map.md"
grep -q 'A050.020.100.010.*ET3101 UART ROM Implementation' "$ARCH_ROOT/050_shared_system_map.md"
grep -q 'A050.020.200.020.*ET6002 Classic CAN ROM Implementation' "$ARCH_ROOT/050_shared_system_map.md"
grep -q 'A050.020.300.020.*ET6003 CAN Family Shared Implementation' "$ARCH_ROOT/050_shared_system_map.md"
grep -q 'A050.030.020.010.020.*ET3101 J-Link Executors' "$ARCH_ROOT/050_shared_system_map.md"
grep -q 'A050.030.020.020.010.*ET6002 CMSIS-DAP Executors' "$ARCH_ROOT/050_shared_system_map.md"
grep -q 'A060.030.030.200.030.*ET6002 CANFD Unsupported Validation Boundary' "$ARCH_ROOT/060_product_control_validation_map.md"
grep -q 'A060.040.010.300.050.*ET6003 J-Link Automation' "$ARCH_ROOT/060_product_control_validation_map.md"
printf '%s\n' '  six-map architecture + full resource-precision nodes = PASS'

printf '%s\n' '[1/6] 全 Architecture Resource 路径漂移校验'
mapfile -t ARCH_RESOURCES < <(
  grep -h '^Resources:' "$ARCH_ROOT"/[0-9][0-9][0-9]_*.md \
    | sed 's/^Resources:[[:space:]]*//' \
    | tr ',' '\n' \
    | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' \
    | grep -E '^(source|doc|agent_harness)/' \
    | sort -u
)
if [[ "${#ARCH_RESOURCES[@]}" -lt 80 ]]; then
  printf 'Architecture precision resource set unexpectedly small: %s\n' "${#ARCH_RESOURCES[@]}" >&2
  exit 1
fi
for resource in "${ARCH_RESOURCES[@]}"; do
  if [[ ! -e "$ROOT_DIR/$resource" ]]; then
    printf 'missing ET-TOOL Architecture Resource: %s\n' "$resource" >&2
    exit 1
  fi
done
printf '  architecture resource paths=%s = PASS\n' "${#ARCH_RESOURCES[@]}"

printf '%s\n' '[2/6] 关键能力边界静态断言'
# ET6002 CANFD 必须只存在产品事实/验证边界，不能被 Resource Precision 偷偷造出 implementation。
if grep -q 'ET6002 CANFD.*Implementation' "$ARCH_ROOT/050_shared_system_map.md"; then
  printf '%s\n' 'ET6002 CANFD must not gain a fake implementation node' >&2
  exit 1
fi
grep -q 'ET6002 CANFD Unsupported' "$ARCH_ROOT/010_chip_map.md"
grep -q 'ET6002 CANFD Unsupported' "$ARCH_ROOT/040_upgrade_route_map.md"
# ET6003 CANFD 必须显式表达共享 CAN-family 主干，而不是复制独立 implementation。
grep -q 'ET6003 CAN Family Shared Implementation' "$ARCH_ROOT/050_shared_system_map.md"
grep -q 'ET6003 CANFD Route Specific Implementation' "$ARCH_ROOT/050_shared_system_map.md"
printf '%s\n' '  unsupported/shared-implementation boundaries = PASS'

printf '%s\n' '[3/6] 构建 Project Contract / Project Manager / Architecture Navigator / ET-TOOL Project'
PACKAGES=(
  project_contract
  governance_core
  public_plugins/project_manager
  public_plugins/architecture_navigator
  projects/et_tool
)
for dir in "${PACKAGES[@]}"; do
  npm_install_if_needed "$ROOT_DIR/agent_harness/$dir" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
  (cd "$ROOT_DIR/agent_harness/$dir" && npm test && npm run build)
done

(cd "$PROJECT_PLUGIN_ROOT" && npm pack --pack-destination "$PACK_DIR" >/dev/null)
PROJECT_TGZ="$(find "$PACK_DIR" -maxdepth 1 -name 'agent-harness-project-et-tool-*.tgz' -print -quit)"
test -n "$PROJECT_TGZ"

printf '%s\n' '[4/6] 真实 Cordis Runtime + Architecture Navigator 全项目路由/资源测试'
cd "$SMOKE_DIR"
npm init -y >/dev/null
npm pkg set type=module >/dev/null
npm_install_if_needed "$SMOKE_DIR" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS" \
  "@deepseek-ai/cordis@$CORDIS_VERSION" \
  "$ROOT_DIR/agent_harness/governance_core" \
  "$ROOT_DIR/agent_harness/project_contract" \
  "$ROOT_DIR/agent_harness/public_plugins/project_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/architecture_navigator" \
  "$PROJECT_TGZ"

cat > "$SMOKE_DIR/smoke.mjs" <<'EOF'
import { Context } from '@deepseek-ai/cordis'
import GovernanceCatalogService from '@agent-harness/governance-core'
import * as projectManagerPlugin from '@agent-harness/project-manager'
import * as architecturePlugin from '@agent-harness/architecture-navigator'
import * as etToolProjectPlugin from '@agent-harness/project-et-tool'

const tick = () => new Promise(resolve => setTimeout(resolve, 0))
const assert = (condition, message) => { if (!condition) throw new Error(message) }
const hasId = (items, id) => items.some(item => item.id === id)
const hasResource = (nodeResult, resource) => nodeResult?.node.resources.includes(resource)

const ctx = new Context()
const fibers = []
fibers.push(ctx.plugin(GovernanceCatalogService)); await tick()
fibers.push(ctx.plugin(projectManagerPlugin)); await tick()
fibers.push(ctx.plugin(architecturePlugin)); await tick()
const projectFiber = ctx.plugin(etToolProjectPlugin); await tick()

const arch = ctx.get('architectureNavigator')
assert(arch, 'architectureNavigator missing')

const snapshot = arch.refreshProject('et-tool')
assert(snapshot.state === 'ready', `architecture state is ${snapshot.state}`)
assert(snapshot.files.length === 6, `expected 6 architecture files, got ${snapshot.files.length}`)
assert(snapshot.nodeCount >= 260, `architecture node tree unexpectedly small: ${snapshot.nodeCount}`)

const node = id => {
  const result = arch.getNode('et-tool', id)
  assert(result, `missing Architecture node ${id}`)
  return result
}
const assertResource = (id, resource) => {
  const result = node(id)
  assert(hasResource(result, resource), `${id} missing Resource ${resource}`)
}
const assertRelation = (id, relation) => {
  const result = node(id)
  assert(result.node.relations.includes(relation), `${id} missing Relation ${relation}`)
}
const assertQuery = (query, expectedId) => {
  const results = arch.searchArchitecture({ projectId: 'et-tool', query, limit: 50 })
  assert(hasId(results, expectedId), `${query} did not hit ${expectedId}; got ${results.map(item => item.id).join(', ')}`)
}

// ROM implementation precision.
assertResource('A050.020.100.010', 'source/apps/cli/chips/et3101/et3101_uart_cli_module.cpp')
assertResource('A050.020.100.020', 'source/apps/cli/chips/et3101/et3101_can_cli_module.cpp')
assertResource('A050.020.100.030', 'source/transport/can/zlg_canfd_driver.h')
assertResource('A050.020.200.010', 'source/backend/chips/et6002/et6002_uart_memory_backend.h')
assertResource('A050.020.200.020', 'source/backend/chips/et6002/et6002_can_memory_backend.h')
assertResource('A050.020.300.010', 'source/apps/cli/chips/et6003/et6003_uart_memory_runner.h')
assertResource('A050.020.300.020', 'source/backend/chips/et6003/et6003_can_family_rom_backend.h')
assertResource('A050.020.300.030', 'source/apps/cli/chips/et6003/et6003_canfd_identify_runner.h')
assertRelation('A050.020.300.030', 'A050.020.300.020')

// Probe executor / driver / algorithm precision.
assertResource('A050.030.020.010.010', 'source/apps/cli/chips/et3101/et3101_debug_probe_cmsis_dap_pflash_hw_executor.h')
assertResource('A050.030.020.010.020', 'source/apps/cli/chips/et3101/et3101_debug_probe_jlink_hw_executor.h')
assertResource('A050.030.020.020.010', 'source/apps/cli/chips/et6002/et6002_debug_probe_cmsis_dap_pflash_hw_executor.h')
assertResource('A050.030.020.020.020', 'source/probe/algorithms/chips/et6002/et6002_debug_probe_jlink_pflash_hw_executor.h')
assertResource('A050.030.020.030.010', 'source/apps/cli/chips/et6003/et6003_debug_probe_cmsis_dap_pflash_hw_executor.h')
assertResource('A050.030.020.030.020', 'source/apps/cli/chips/et6003/et6003_debug_probe_jlink_hw_executor.h')
assertResource('A050.030.030.010', 'source/probe/drivers/cmsis_dap/cmsis_dap_swd_session.h')
assertResource('A050.030.030.020', 'source/probe/drivers/jlink/jlink_swd_session.h')
assertResource('A050.030.040.010', 'source/probe/algorithms/chips/et3101/et3101_debug_probe_pflash_algorithm.h')
assertResource('A050.030.040.020', 'source/probe/algorithms/chips/et6002/et6002_debug_probe_pflash_algorithm.h')
assertResource('A050.030.040.030', 'source/probe/algorithms/chips/et6003/et6003_debug_probe_pflash_algorithm.h')

// Profiles / validation / automation precision.
assertResource('A060.010.010.010', 'source/profiles/chips/et3101/evidence.yaml')
assertResource('A060.010.010.020', 'source/profiles/chips/et6002/evidence.yaml')
assertResource('A060.010.010.030', 'source/profiles/chips/et6003/evidence.yaml')
assertResource('A060.040.010.100.010', 'source/automation/scripts/chips/et3101/uart_rom/')
assertResource('A060.040.010.200.020', 'source/automation/scripts/chips/et6002/can_rom/')
assertResource('A060.040.010.200.050', 'source/automation/scripts/chips/et6002/debug_probe/jlink/')
assertResource('A060.040.010.300.030', 'source/automation/scripts/chips/et6003/canfd_rom/')
assertResource('A060.040.010.300.040', 'source/automation/scripts/chips/et6003/debug_probe/dap/')
assertResource('A060.040.010.300.050', 'source/automation/scripts/chips/et6003/debug_probe/jlink/')

// User-language routing across chips/routes/operations.
assertQuery('ET3101 UART program', 'A010.010.010.030')
assertQuery('ET3101 CANFD', 'A010.010.030')
assertQuery('ET3101 J-Link CLI', 'A020.060.010')
assertQuery('ET6002 CAN program', 'A010.020.020.030')
assertQuery('ET6002 J-Link CLI', 'A020.060.020')
assertQuery('ET6002 CANFD', 'A010.020.030')
assertQuery('ET6003 UART security', 'A010.030.010.040')
assertQuery('ET6003 CAN program', 'A010.030.020.030')
assertQuery('ET6003 CANFD verify', 'A010.030.030.030')
assertQuery('ET6003 CMSIS-DAP CLI', 'A020.050.030')
assertQuery('ET6003 J-Link program', 'A010.030.050.030')

// Projection/downlink graph must remain connected.
assertRelation('A020.030.020', 'A050.020.200.020')
assertRelation('A030.060.030', 'A050.020.300.030')
assertRelation('A040.040.020', 'A050.030.020.020.010')
assertRelation('A040.050.010', 'A050.030.020.010.020')
assertRelation('A040.030.020', 'A060.030.030.200.030')

console.log(`  Architecture files=${snapshot.files.length} nodes=${snapshot.nodeCount}`)
console.log('  full-project precise Resource routing = PASS')
console.log('  ROM shared/route-specific implementation semantics = PASS')
console.log('  Probe executor/driver/algorithm separation = PASS')
console.log('  Profiles/validation/automation precision = PASS')
console.log('  user-language cross-chip routing = PASS')
console.log('  ET6002 CANFD negative boundary = PASS')

await projectFiber.dispose(); await tick()
for (let index = fibers.length - 1; index >= 0; index -= 1) {
  await fibers[index].dispose(); await tick()
}
EOF

ET_TOOL_PROJECT_ROOT="$ROOT_DIR" node "$SMOKE_DIR/smoke.mjs"

printf '%s\n' '[5/6] Architecture v0.1 Contract result'
printf '%s\n' \
  'PHASE4_ETTOOL_ARCHITECTURE_V0_1_INTEGRATION=PASS' \
  'ETTOOL_FULL_RESOURCE_PRECISION=PASS' \
  "CORDIS_VERSION=$CORDIS_VERSION"
printf '%s\n' '[6/6] DONE'
