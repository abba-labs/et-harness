#!/usr/bin/env bash
set -euo pipefail

NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ADAPTER_DIR="$ROOT_DIR/agent_harness/public_plugins/agent_governance_closure_adapters"

source "$ROOT_DIR/agent_harness/validation/lib/common_runtime.sh"
export npm_config_registry="$NPM_REGISTRY"

for package_dir in \
  "$ROOT_DIR/agent_harness/governance_core" \
  "$ROOT_DIR/agent_harness/project_contract" \
  "$ROOT_DIR/agent_harness/public_plugins/project_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/evidence_state_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/knowledge_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/architecture_navigator" \
  "$ROOT_DIR/agent_harness/public_plugins/rule_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/gate_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/context_builder" \
  "$ROOT_DIR/agent_harness/public_plugins/experience_memory_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/agent_governance_kernel"
do
  npm_install_if_needed "$package_dir" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
  (cd "$package_dir" && npm run build)
done

npm_install_if_needed "$ADAPTER_DIR" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
(cd "$ADAPTER_DIR" && npm run build && npm test)

cd "$ROOT_DIR"
node --input-type=module <<'NODE'
import { readFileSync } from 'node:fs'
const registry = readFileSync('agent_harness/public_plugins/public_plugins.v0.1.yaml', 'utf8')
const modules = readFileSync('agent_harness/public_plugins/agent_governance_closure_adapters/src/modules.ts', 'utf8')
const readme = readFileSync('agent_harness/public_plugins/agent_governance_closure_adapters/README.md', 'utf8')
if (!registry.includes('public.agent-governance-closure-adapters')) throw new Error('Closure Adapter plugin missing from Public Plugin Registry')
for (const id of ['context-closure', 'knowledge-closure', 'experience-memory-closure']) {
  if (!modules.includes(`id: '${id}'`)) throw new Error(`Missing mandatory manager adapter: ${id}`)
}
if (!modules.includes('knowledge-category://project/') || !modules.includes('knowledge-category://public/')) {
  throw new Error('Knowledge explicit category protocol is missing')
}
if (!readme.includes('never auto-promote') && !readme.includes('never auto-promote to `VALIDATED`')) {
  throw new Error('README must preserve no-auto-promotion boundary')
}
NODE

printf '%s\n' \
  'KERNEL_CONTEXT_CLOSURE_ADAPTER=PASS' \
  'KERNEL_KNOWLEDGE_CLOSURE_ADAPTER=PASS' \
  'KERNEL_KNOWLEDGE_EXPLICIT_CATEGORY=PASS' \
  'KERNEL_EXPERIENCE_CLOSURE_ADAPTER=PASS' \
  'KERNEL_MANAGER_ADAPTER_REPLAY=PASS' \
  'KERNEL_PUBLIC_SCOPE_GAPS_FAIL_CLOSED=PASS' \
  'PHASE4A_PUBLIC_AGENT_GOVERNANCE_KERNEL_STEP4_V0_1=PASS'
