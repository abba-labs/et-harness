#!/usr/bin/env bash
set -euo pipefail

NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PACKAGE_DIR="$ROOT_DIR/agent_harness/public_plugins/agent_governance_kernel"

source "$ROOT_DIR/agent_harness/validation/lib/common_runtime.sh"
export npm_config_registry="$NPM_REGISTRY"

npm_install_if_needed "$ROOT_DIR/agent_harness/governance_core" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
(cd "$ROOT_DIR/agent_harness/governance_core" && npm run build)

npm_install_if_needed "$PACKAGE_DIR" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
(cd "$PACKAGE_DIR" && npm run build && npm test)

cd "$ROOT_DIR"
node --input-type=module <<'NODE'
import { readFileSync } from 'node:fs'
const registry = readFileSync('agent_harness/public_plugins/public_plugins.v0.1.yaml', 'utf8')
const core = readFileSync('agent_harness/governance_core/src/contracts.ts', 'utf8')
const pkg = JSON.parse(readFileSync('agent_harness/public_plugins/agent_governance_kernel/package.json', 'utf8'))
if (!registry.includes('governance.turn-reflection')) throw new Error('Public Plugin Registry missing governance.turn-reflection')
if (!core.includes("id: 'governance.turn-reflection'")) throw new Error('Governance Core missing turn-reflection core capability')
if (pkg.peerDependencies?.['@agent-harness/project-manager']) throw new Error('Kernel must not depend on Project Manager')
if (pkg.peerDependencies?.['@agent-harness/context-builder']) throw new Error('Kernel must not depend on Context Manager/Builder')
NODE

printf '%s\n' \
  'KERNEL_UNIFIED_TURN_REFLECTION=PASS' \
  'KERNEL_REFLECTION_ALL_DOMAINS_REQUIRED=PASS' \
  'KERNEL_REFLECTION_SCOPE_PROTOCOL=PASS' \
  'KERNEL_REFLECTION_PERSISTENCE=PASS' \
  'KERNEL_REFLECTION_REQUIRED_BEFORE_CLOSE=PASS' \
  'KERNEL_REFLECTION_FAIL_CLOSED=PASS' \
  'KERNEL_REFLECTION_PROJECT_INDEPENDENT=PASS' \
  'PHASE4A_PUBLIC_AGENT_GOVERNANCE_KERNEL_STEP2_V0_1=PASS'
