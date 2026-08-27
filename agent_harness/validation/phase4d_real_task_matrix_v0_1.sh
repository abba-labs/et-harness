#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
agent_root="$repo_root/agent_harness"
install_timeout="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
matrix_iterations="${REAL_TASK_MATRIX_ITERATIONS:-1}"

if ! [[ "$matrix_iterations" =~ ^[1-9][0-9]*$ ]]; then
  echo "REAL_TASK_MATRIX_INVALID_ITERATIONS=$matrix_iterations"
  exit 2
fi

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
  echo "REAL_TASK_MATRIX_BUILD_PACKAGE=$package"
  cd "$agent_root/$package"
  timeout "$install_timeout" npm install --ignore-scripts --loglevel=warn
  npm run build
done

for package in \
  "public_plugins/rule_manager" \
  "public_plugins/knowledge_manager" \
  "public_plugins/auto_governance_engine" \
  "public_plugins/governance_runtime" \
  "projects/et_tool"
do
  echo "REAL_TASK_MATRIX_TEST_PACKAGE=$package"
  cd "$agent_root/$package"
  npm test
done

cd "$repo_root"
report_dir="${REAL_TASK_MATRIX_REPORT_DIR:-${RUNNER_TEMP:-/tmp}/real-task-matrix-reports}"
mkdir -p "$report_dir"
matrix_failed=0

for ((iteration = 1; iteration <= matrix_iterations; iteration++)); do
  echo "REAL_TASK_MATRIX_ITERATION=$iteration/$matrix_iterations"
  if ! REAL_TASK_MATRIX_ITERATION="$iteration" \
    REAL_TASK_MATRIX_REPORT_DIR="$report_dir" \
    node "$agent_root/pilots/external_chat_agent/dist/real-task-matrix.js"; then
    matrix_failed=1
  fi
done

git diff --check -- '*.ts' '*.json' '*.yaml' '*.yml' '*.sh'

if [[ "$matrix_failed" -ne 0 ]]; then
  echo "PHASE4D_REAL_TASK_MATRIX_V0_1=FAIL"
  exit 4
fi

echo "REAL_TASK_MATRIX_COMPLETED_ITERATIONS=$matrix_iterations"
echo "PHASE4D_REAL_TASK_MATRIX_V0_1=PASS"
