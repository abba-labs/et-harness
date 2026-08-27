#!/usr/bin/env bash
set -euo pipefail

# Re-run unchanged adversarial assertions after Framework hardening.
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
agent_root="$repo_root/agent_harness"
install_timeout="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"

packages=(
  "project_contract"
  "governance_core"
  "public_plugins/project_manager"
  "public_plugins/architecture_navigator"
  "public_plugins/rule_manager"
  "public_plugins/evidence_state_manager"
  "public_plugins/knowledge_manager"
  "public_plugins/gate_manager"
  "public_plugins/context_builder"
  "public_plugins/experience_memory_manager"
  "public_plugins/agent_governance_kernel"
  "public_plugins/agent_governance_closure_adapters"
  "public_plugins/auto_governance_engine"
  "public_plugins/governance_runtime"
  "projects/et_tool"
  "model_adapters/generic_model"
  "pilots/generic_model"
  "pilots/external_chat_agent"
)

for package in "${packages[@]}"; do
  echo "ADVERSARIAL_BUILD_PACKAGE=$package"
  cd "$agent_root/$package"
  timeout "$install_timeout" npm install --ignore-scripts --loglevel=warn
  npm run build
done

for package in \
  public_plugins/rule_manager \
  public_plugins/auto_governance_engine \
  public_plugins/governance_runtime
do
  cd "$agent_root/$package"
  npm test
done

cd "$repo_root"
set +e
node "$agent_root/pilots/external_chat_agent/dist/adversarial-baseline.js"
status=$?
set -e

if [[ "$status" -ne 0 ]]; then
  echo "PHASE4B_ADVERSARIAL_GOVERNANCE_NEGATIVE_V0_1=FAIL"
  exit "$status"
fi

echo "PHASE4B_ADVERSARIAL_GOVERNANCE_NEGATIVE_V0_1=PASS"
