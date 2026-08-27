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
const service = readFileSync('agent_harness/public_plugins/agent_governance_closure_adapters/src/service.ts', 'utf8')
const remaining = readFileSync('agent_harness/public_plugins/agent_governance_closure_adapters/src/remaining-modules.ts', 'utf8')
const readme = readFileSync('agent_harness/public_plugins/agent_governance_closure_adapters/README.md', 'utf8')

if (!registry.includes('public.agent-governance-closure-adapters')) throw new Error('Closure Adapter plugin missing from registry')
for (const dep of ['public.evidence-state-manager', 'public.gate-manager']) {
  if (!registry.includes(dep)) throw new Error(`Closure Adapter dependency missing: ${dep}`)
}
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
  if (!service.includes(`registerClosureModule`) || !service.includes(id.replaceAll('-', ''))) {
    // The service registers factory functions rather than string literals for every module.
    const token = id === 'context-closure' ? 'createContextLedgerClosureModule'
      : id === 'knowledge-closure' ? 'createKnowledgeClosureModule'
      : id === 'experience-memory-closure' ? 'createExperienceMemoryClosureModule'
      : id === 'architecture-closure' ? 'createArchitectureClosureModule'
      : id === 'rules-closure' ? 'createRulesClosureModule'
      : id === 'evidence-state-closure' ? 'createEvidenceStateClosureModule'
      : id === 'working-set-closure' ? 'createWorkingSetClosureModule'
      : 'createObligationGateReconcileModule'
    if (!service.includes(token)) throw new Error(`Missing mandatory Closure Module registration: ${id}`)
  }
}
if (!remaining.includes("result: 'INFO'")) throw new Error('Evidence Closure must record INFO rather than auto-PASS')
if (!remaining.includes('without PASS Evidence')) throw new Error('MUST Gate false-resolution guard missing')
if (!readme.includes('8/8')) throw new Error('README must state complete fixed mandatory set')
if (!readme.includes('never auto-promote')) throw new Error('Knowledge no-auto-promotion boundary missing')
NODE

printf '%s\n' \
  'KERNEL_ALL_MANDATORY_CLOSURE_MODULES_REGISTERED=PASS' \
  'KERNEL_ARCHITECTURE_CHANGE_CANDIDATE=PASS' \
  'KERNEL_RULE_CHANGE_CANDIDATE=PASS' \
  'KERNEL_EVIDENCE_INFO_ONLY=PASS' \
  'KERNEL_WORKING_SET_SEPARATE_CLOSURE=PASS' \
  'KERNEL_OBLIGATION_GATE_RECONCILE=PASS' \
  'KERNEL_MUST_GATE_FALSE_RESOLUTION_BLOCKED=PASS' \
  'KERNEL_REMAINING_MODULE_REPLAY=PASS' \
  'PHASE4A_PUBLIC_AGENT_GOVERNANCE_KERNEL_STEP5_V0_1=PASS'
