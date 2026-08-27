#!/usr/bin/env bash
set -euo pipefail

NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${EXTERNAL_CHAT_AGENT_PILOT_WORK_DIR:-$(mktemp -d)}"
AUDIT_ROOT="$WORK_DIR/audits"
STATE_ROOT="$WORK_DIR/state"

source "$ROOT_DIR/agent_harness/validation/lib/common_runtime.sh"

cleanup() {
  if [[ "${EXTERNAL_CHAT_AGENT_PILOT_KEEP_WORK_DIR:-0}" != "1" ]]; then rm -rf "$WORK_DIR"; fi
}
trap cleanup EXIT
mkdir -p "$AUDIT_ROOT" "$STATE_ROOT"

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

# The bridge must remain transport-only. These imports would mean governance logic leaked into it.
if grep -Eq "@agent-harness/(project-manager|architecture-navigator|rule-manager|knowledge-manager|gate-manager|agent-governance-kernel|governance-runtime)" \
  "$ROOT_DIR/agent_harness/pilots/external_chat_agent/src/github-issue-client.ts"; then
  echo "External Agent bridge contains forbidden governance imports" >&2
  exit 1
fi

export AGENT_HARNESS_EXTERNAL_CHAT_AUDIT_ROOT="$AUDIT_ROOT"
export AGENT_HARNESS_STATE_ROOT="$STATE_ROOT"
export EXTERNAL_AGENT_PROJECT_ROOT="$ROOT_DIR"
export EXTERNAL_AGENT_RESPONSE_TIMEOUT_MS="${EXTERNAL_AGENT_RESPONSE_TIMEOUT_MS:-900000}"
export EXTERNAL_AGENT_POLL_INTERVAL_MS="${EXTERNAL_AGENT_POLL_INTERVAL_MS:-2000}"

node "$ROOT_DIR/agent_harness/pilots/external_chat_agent/dist/index.js"

python3 - "$AUDIT_ROOT/latest.json" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, encoding='utf-8') as f:
    receipt = json.load(f)

if receipt.get('pass') is not True:
    raise SystemExit(f"external chat audit not PASS: {receipt.get('blockingReasons')}")

calls = receipt.get('externalAgentCalls') or []
if [item.get('purpose') for item in calls] != ['WORK', 'GOVERNANCE_REFLECTION']:
    raise SystemExit(f"unexpected external Agent call order: {calls}")

route = receipt.get('route') or {}
for key in ('architectureIds', 'ruleIds', 'knowledgeIds', 'gateIds'):
    if not route.get(key):
        raise SystemExit(f"automatic route missing {key}")

closure = receipt.get('closure') or {}
if closure.get('status') != 'COMPLETE':
    raise SystemExit(f"closure is not COMPLETE: {closure}")
receipts = closure.get('moduleReceipts') or []
if len(receipts) != 8 or any(item.get('status') not in ('APPLIED', 'NO_CHANGE') for item in receipts):
    raise SystemExit(f"8/8 Closure failed: {receipts}")

journal = receipt.get('journal') or {}
if journal.get('status') != 'CLOSED':
    raise SystemExit(f"journal not CLOSED: {journal}")

print('EXTERNAL_CHAT_AGENT_WORK_PATH=PASS')
print('EXTERNAL_CHAT_AGENT_A_R_K_G_AUTO_ROUTE=PASS')
print('EXTERNAL_CHAT_AGENT_AUTOMATIC_REFLECTION=PASS')
print('EXTERNAL_CHAT_AGENT_8_OF_8_CLOSURE=PASS')
print('EXTERNAL_CHAT_AGENT_TURN_CLOSED=PASS')
print('EXTERNAL_CHAT_AGENT_BRIDGE_TRANSPORT_ONLY=PASS')
print('PHASE4A_EXTERNAL_CHAT_AGENT_GOVERNANCE_PILOT_V0_1=PASS')
PY
