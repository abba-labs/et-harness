#!/usr/bin/env bash
set -euo pipefail

NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${EXTERNAL_CHAT_AGENT_PILOT_WORK_DIR:-$(mktemp -d)}"
STATE_ROOT="$WORK_DIR/state"
REPORT_FILE="$WORK_DIR/closed-loop-report.json"

source "$ROOT_DIR/agent_harness/validation/lib/common_runtime.sh"

cleanup() {
  if [[ "${EXTERNAL_CHAT_AGENT_PILOT_KEEP_WORK_DIR:-0}" != "1" ]]; then rm -rf "$WORK_DIR"; fi
}
trap cleanup EXIT
mkdir -p "$STATE_ROOT"

: "${EXTERNAL_AGENT_GITHUB_TOKEN:?EXTERNAL_AGENT_GITHUB_TOKEN is required}"
: "${EXTERNAL_AGENT_REPOSITORY:?EXTERNAL_AGENT_REPOSITORY is required}"
: "${EXTERNAL_AGENT_ISSUE_NUMBER:?EXTERNAL_AGENT_ISSUE_NUMBER is required}"

PACKAGES=(
  project_contract
  governance_core
  public_plugins/project_manager
  public_plugins/architecture_navigator
  public_plugins/rule_manager
  public_plugins/evidence_state_manager
  public_plugins/knowledge_manager
  public_plugins/gate_manager
  public_plugins/context_builder
  public_plugins/experience_memory_manager
  public_plugins/agent_governance_kernel
  public_plugins/agent_governance_closure_adapters
  public_plugins/auto_governance_engine
  public_plugins/governance_runtime
  projects/et_tool
  model_adapters/generic_model
  pilots/generic_model
  pilots/external_chat_agent
)

for dir in "${PACKAGES[@]}"; do
  npm_install_if_needed "$ROOT_DIR/agent_harness/$dir" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
  (cd "$ROOT_DIR/agent_harness/$dir" && npm run build)
done

if grep -Eq "@agent-harness/(project-manager|architecture-navigator|rule-manager|knowledge-manager|gate-manager|agent-governance-kernel|governance-runtime)" \
  "$ROOT_DIR/agent_harness/pilots/external_chat_agent/src/github-issue-client.ts"; then
  echo "External Agent bridge contains forbidden governance imports" >&2
  exit 1
fi

export AGENT_HARNESS_STATE_ROOT="$STATE_ROOT"
export EXTERNAL_AGENT_PROJECT_ROOT="$ROOT_DIR"
export EXTERNAL_CHAT_AGENT_CLOSED_LOOP_REPORT="$REPORT_FILE"
export EXTERNAL_AGENT_RESPONSE_TIMEOUT_MS="${EXTERNAL_AGENT_RESPONSE_TIMEOUT_MS:-900000}"
export EXTERNAL_AGENT_POLL_INTERVAL_MS="${EXTERNAL_AGENT_POLL_INTERVAL_MS:-2000}"

set +e
node "$ROOT_DIR/agent_harness/pilots/external_chat_agent/dist/closed-loop.js"
rc=$?
set -e

if [[ -f "$REPORT_FILE" ]]; then
  python3 - "$REPORT_FILE" <<'PY'
import json
import sys

with open(sys.argv[1], encoding='utf-8') as f:
    report = json.load(f)

a = report.get('assertions') or {}
for key in (
    'fourModelCalls',
    'turn1Closed',
    'knowledgeClosureApplied',
    'knowledgeCandidateCreated',
    'knowledgeCategoryForcedActive',
    'knowledgeIndexRefreshed',
    'contextAutomaticallyAdvanced',
    'turn2Closed',
):
    print(f"CLOSED_LOOP_{key.upper()}={'PASS' if a.get(key) else 'FAIL'}")
print(f"CLOSED_LOOP_KNOWLEDGE_AUTOMATICALLY_REUSED={'PASS' if a.get('knowledgeAutomaticallyReusedByDefaultRoute') else 'FAIL'}")
print('CLOSED_LOOP_DIAGNOSTIC=' + json.dumps({
    'candidateId': (report.get('knowledgeMutation') or {}).get('candidateId'),
    'candidateStatus': (report.get('knowledgeMutation') or {}).get('candidateStatus'),
    'candidateCategory': (report.get('knowledgeMutation') or {}).get('candidateCategory'),
    'turn2KnowledgeIds': ((report.get('turn2') or {}).get('route') or {}).get('knowledgeIds'),
}, ensure_ascii=False))
PY
fi

if [[ "$rc" -eq 0 ]]; then
  echo "PHASE4A_EXTERNAL_CHAT_AGENT_POSITIVE_CLOSED_LOOP_V0_2=PASS"
  exit 0
fi
if [[ "$rc" -eq 3 ]]; then
  echo "PHASE4A_EXTERNAL_CHAT_AGENT_FOUNDATIONAL_CLOSED_LOOP_V0_2=PASS"
  echo "PHASE4A_EXTERNAL_CHAT_AGENT_VALIDATED_KNOWLEDGE_REUSE_V0_2=FAIL"
  exit 3
fi

echo "PHASE4A_EXTERNAL_CHAT_AGENT_POSITIVE_CLOSED_LOOP_V0_2=FAIL rc=$rc" >&2
exit "$rc"
