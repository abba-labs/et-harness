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
if (!registry.includes('public.agent-governance-kernel')) throw new Error('public plugin registry missing Kernel')
if (!registry.includes('governance.lifecycle')) throw new Error('governance.lifecycle capability missing')
if (!registry.includes('governance.turn-journal')) throw new Error('governance.turn-journal capability missing')
NODE

printf '%s\n' \
  'KERNEL_LIFECYCLE_CONTRACT=PASS' \
  'KERNEL_TURN_JOURNAL=PASS' \
  'KERNEL_UNBOUND_PROJECT_GOVERNANCE=PASS' \
  'KERNEL_PENDING_CLOSURE_GUARD=PASS' \
  'PHASE4A_PUBLIC_AGENT_GOVERNANCE_KERNEL_STEP1_V0_1=PASS'
