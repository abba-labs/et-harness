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
const contracts = readFileSync('agent_harness/public_plugins/agent_governance_kernel/src/contracts.ts', 'utf8')
const service = readFileSync('agent_harness/public_plugins/agent_governance_kernel/src/service.ts', 'utf8')
const pkg = JSON.parse(readFileSync('agent_harness/public_plugins/agent_governance_kernel/package.json', 'utf8'))

if (!registry.includes('governance.turn-closure')) throw new Error('Public Plugin Registry missing governance.turn-closure')
if (!core.includes("id: 'governance.turn-closure'")) throw new Error('Governance Core missing turn-closure core capability')
for (const id of [
  'context-closure',
  'knowledge-closure',
  'experience-memory-closure',
  'architecture-closure',
  'rules-closure',
  'evidence-state-closure',
  'working-set-closure',
  'obligation-gate-reconcile',
]) {
  if (!contracts.includes(`'${id}'`)) throw new Error(`Missing fixed Mandatory Closure Module ID: ${id}`)
}
if (!service.includes('return this.closure.closeTurn(taskId, turnId)')) {
  throw new Error('Kernel Service closeTurn must route through Closure Coordinator')
}
if (pkg.peerDependencies?.['@agent-harness/project-manager']) throw new Error('Kernel must remain project-independent')
if (pkg.peerDependencies?.['@agent-harness/context-builder']) throw new Error('Kernel must not depend directly on Context Manager/Builder in Step 3')
if (pkg.peerDependencies?.['@agent-harness/knowledge-manager']) throw new Error('Kernel must not depend directly on Knowledge Manager in Step 3')
NODE

printf '%s\n' \
  'KERNEL_CLOSURE_COORDINATOR=PASS' \
  'KERNEL_MANDATORY_CLOSURE_SET=PASS' \
  'KERNEL_CLOSURE_IDEMPOTENCY=PASS' \
  'KERNEL_CLOSURE_RECEIPT_PERSISTENCE=PASS' \
  'KERNEL_CLOSURE_FAILURE_REPLAY=PASS' \
  'KERNEL_CLOSURE_REQUIRED_BEFORE_CLOSE=PASS' \
  'KERNEL_CLOSURE_PROJECT_INDEPENDENT=PASS' \
  'PHASE4A_PUBLIC_AGENT_GOVERNANCE_KERNEL_STEP3_V0_1=PASS'
