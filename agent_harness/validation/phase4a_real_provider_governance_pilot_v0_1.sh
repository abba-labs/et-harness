#!/usr/bin/env bash
set -euo pipefail

CORDIS_VERSION="${CORDIS_VERSION:-4.0.1}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${REAL_PROVIDER_PILOT_WORK_DIR:-$(mktemp -d)}"
SMOKE_DIR="$WORK_DIR/smoke"
PORT_FILE="$WORK_DIR/provider.port"
PROVIDER_LOG="$WORK_DIR/provider.log"
AUDIT_ROOT="$WORK_DIR/audits"
STATE_ROOT="$WORK_DIR/state"

source "$ROOT_DIR/agent_harness/validation/lib/common_runtime.sh"

PROVIDER_PID=""
cleanup() {
  if [[ -n "$PROVIDER_PID" ]]; then kill "$PROVIDER_PID" >/dev/null 2>&1 || true; fi
  if [[ "${REAL_PROVIDER_PILOT_KEEP_WORK_DIR:-0}" != "1" ]]; then rm -rf "$WORK_DIR"; fi
}
trap cleanup EXIT
mkdir -p "$SMOKE_DIR" "$AUDIT_ROOT" "$STATE_ROOT"

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
  model_adapters/json_process_client
  model_adapters/openai_compatible_wrapper
  pilots/generic_model
  pilots/real_provider
)
for dir in "${PACKAGES[@]}"; do
  npm_install_if_needed "$ROOT_DIR/agent_harness/$dir" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
  (cd "$ROOT_DIR/agent_harness/$dir" && npm test && npm run build)
done

cd "$SMOKE_DIR"
npm init -y >/dev/null
npm pkg set type=module >/dev/null
npm_install_if_needed "$SMOKE_DIR" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS" \
  "@deepseek-ai/cordis@$CORDIS_VERSION" \
  "$ROOT_DIR/agent_harness/governance_core" \
  "$ROOT_DIR/agent_harness/project_contract" \
  "$ROOT_DIR/agent_harness/public_plugins/project_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/architecture_navigator" \
  "$ROOT_DIR/agent_harness/public_plugins/rule_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/evidence_state_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/knowledge_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/gate_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/context_builder" \
  "$ROOT_DIR/agent_harness/public_plugins/experience_memory_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/agent_governance_kernel" \
  "$ROOT_DIR/agent_harness/public_plugins/agent_governance_closure_adapters" \
  "$ROOT_DIR/agent_harness/public_plugins/auto_governance_engine" \
  "$ROOT_DIR/agent_harness/public_plugins/governance_runtime" \
  "$ROOT_DIR/agent_harness/projects/et_tool" \
  "$ROOT_DIR/agent_harness/model_adapters/generic_model" \
  "$ROOT_DIR/agent_harness/model_adapters/json_process_client" \
  "$ROOT_DIR/agent_harness/model_adapters/openai_compatible_wrapper" \
  "$ROOT_DIR/agent_harness/pilots/generic_model" \
  "$ROOT_DIR/agent_harness/pilots/real_provider"

cat > "$WORK_DIR/mock-provider.mjs" <<'EOF'
import http from 'node:http'
import { appendFileSync, writeFileSync } from 'node:fs'

const portFile = process.env.PORT_FILE
const providerLog = process.env.PROVIDER_LOG
if (!portFile || !providerLog) throw new Error('mock provider paths missing')

const readBody = request => new Promise((resolve, reject) => {
  let body = ''
  request.setEncoding('utf8')
  request.on('data', chunk => {
    body += chunk
    if (body.length > 8 * 1024 * 1024) reject(new Error('request too large'))
  })
  request.on('end', () => resolve(body))
  request.on('error', reject)
})

const reflectionResult = runtimeRequest => {
  const route = runtimeRequest.context?.route ?? {}
  const keep = [
    ...(route.architectureIds ?? []),
    ...(route.ruleIds ?? []),
    ...(route.knowledgeIds ?? []),
    ...(route.gateIds ?? []),
  ]
  return {
    contractVersion: '0.1',
    taskId: runtimeRequest.taskId,
    turnId: runtimeRequest.turnId,
    context: {
      progress: 'Completed Level 2C governed provider analysis.',
      decisions: [],
      confirmed: ['The model used automatically routed project governance context.'],
      assumptions: [],
      openIssues: [],
      next: [],
      touchedRefs: keep,
    },
    knowledge: {
      scopeDecision: 'NONE',
      rationale: 'This validation run does not need to create a new durable knowledge candidate.',
      candidates: [],
    },
    experience: { scopeDecision: 'NONE', rationale: 'No new cross-task experience.', candidates: [] },
    architecture: { scopeDecision: 'NONE', rationale: 'No architecture change proposal.', candidates: [] },
    rules: { scopeDecision: 'NONE', rationale: 'No rule change proposal.', candidates: [] },
    evidence: { scopeDecision: 'NONE', rationale: 'No new validation evidence.', candidates: [] },
    workingSet: { keep, add: [], remove: [] },
    obligations: { opened: [], resolved: [], unchanged: [] },
  }
}

const server = http.createServer(async (request, response) => {
  try {
    if (request.method !== 'POST') {
      response.writeHead(405).end()
      return
    }
    if (request.headers.authorization !== 'Bearer fixture-secret-key') {
      response.writeHead(401, { 'content-type': 'application/json' })
      response.end(JSON.stringify({ error: { message: 'bad auth' } }))
      return
    }
    const body = JSON.parse(await readBody(request))
    const style = request.url?.endsWith('/responses')
      ? 'responses'
      : request.url?.endsWith('/chat/completions')
        ? 'chat_completions'
        : 'unknown'
    if (style === 'unknown') {
      response.writeHead(404).end()
      return
    }
    const systemText = style === 'responses'
      ? String(body.instructions ?? '')
      : String(body.messages?.find(item => item.role === 'system')?.content ?? '')
    const userText = style === 'responses'
      ? String(body.input ?? '')
      : String([...body.messages ?? []].reverse().find(item => item.role === 'user')?.content ?? '')
    const purpose = systemText.includes('semantic Reflection executor')
      ? 'GOVERNANCE_REFLECTION'
      : 'WORK'
    appendFileSync(providerLog, `${style}|${purpose}\n`, 'utf8')

    let output
    if (purpose === 'WORK') {
      if (!userText.includes('BUSINESS TASK (verbatim):')) throw new Error('work prompt lost business task boundary')
      if (!userText.includes('AUTOMATIC GOVERNANCE CONTEXT:')) throw new Error('work prompt missing automatic context')
      output = 'Code Gate 负责构建前审查；通过后进入正式 Release 构建，再执行所需验证并沉淀 Evidence。三者职责连续但不互相替代。'
    } else {
      const payload = JSON.parse(userText)
      const runtimeRequest = payload.runtimeRequest
      if (!runtimeRequest?.turnObservations?.some(item => item.kind === 'TASK_INPUT')) {
        throw new Error('reflection missing TASK_INPUT observation')
      }
      if (!runtimeRequest?.turnObservations?.some(item => item.kind === 'ASSISTANT_MESSAGE')) {
        throw new Error('reflection missing ASSISTANT_MESSAGE observation')
      }
      output = JSON.stringify(reflectionResult(runtimeRequest))
    }

    response.writeHead(200, { 'content-type': 'application/json' })
    if (style === 'responses') {
      response.end(JSON.stringify({ id: 'resp_fixture', model: body.model, output_text: output }))
    } else {
      response.end(JSON.stringify({
        id: 'chat_fixture',
        model: body.model,
        choices: [{ message: { role: 'assistant', content: output } }],
      }))
    }
  } catch (error) {
    response.writeHead(500, { 'content-type': 'application/json' })
    response.end(JSON.stringify({ error: { message: error instanceof Error ? error.message : String(error) } }))
  }
})

server.listen(0, '127.0.0.1', () => {
  const address = server.address()
  if (!address || typeof address === 'string') throw new Error('mock provider address unavailable')
  writeFileSync(portFile, String(address.port), 'utf8')
})
EOF

PORT_FILE="$PORT_FILE" PROVIDER_LOG="$PROVIDER_LOG" node "$WORK_DIR/mock-provider.mjs" &
PROVIDER_PID=$!
for _ in $(seq 1 100); do
  [[ -s "$PORT_FILE" ]] && break
  sleep 0.05
done
[[ -s "$PORT_FILE" ]] || { echo 'mock provider did not start' >&2; exit 1; }
PORT="$(cat "$PORT_FILE")"

PILOT_ENTRY="$SMOKE_DIR/node_modules/@agent-harness/real-provider-governance-pilot/dist/index.js"
[[ -f "$PILOT_ENTRY" ]] || { echo "pilot entry missing: $PILOT_ENTRY" >&2; exit 1; }

run_lane() {
  local lane="$1"
  local style="$2"
  local audit="$AUDIT_ROOT/$lane"
  local state="$STATE_ROOT/$lane"
  mkdir -p "$audit" "$state"
  OPENAI_COMPAT_BASE_URL="http://127.0.0.1:$PORT/v1" \
  OPENAI_COMPAT_API_KEY="fixture-secret-key" \
  OPENAI_COMPAT_MODEL="fixture-model" \
  OPENAI_COMPAT_API_STYLE="$style" \
  OPENAI_COMPAT_CHAT_JSON_MODE="json_object" \
  OPENAI_COMPAT_PROVIDER_ID="fixture-provider" \
  REAL_PROVIDER_LANE="$lane" \
  REAL_PROVIDER_PROJECT_ROOT="$ROOT_DIR" \
  REAL_PROVIDER_RUN_ID="fixture-$lane" \
  AGENT_HARNESS_STATE_ROOT="$state" \
  AGENT_HARNESS_REAL_PROVIDER_AUDIT_ROOT="$audit" \
  node "$PILOT_ENTRY" >"$WORK_DIR/$lane.stdout" 2>"$WORK_DIR/$lane.stderr"
}

run_lane synthetic responses
run_lane et-tool chat_completions

node --input-type=module - "$AUDIT_ROOT" <<'EOF'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
const root = process.argv[2]
const assert = (condition, message) => { if (!condition) throw new Error(message) }
for (const lane of ['synthetic', 'et-tool']) {
  const file = join(root, lane, 'latest.json')
  const text = readFileSync(file, 'utf8')
  assert(!text.includes('fixture-secret-key'), `${lane} audit leaked provider API key`)
  const audit = JSON.parse(text)
  assert(audit.pass === true, `${lane} audit is not PASS: ${(audit.blockingReasons ?? []).join('; ')}`)
  assert(audit.modelCalls?.length === 2, `${lane} did not record exactly two model calls`)
  assert(audit.modelCalls[0]?.purpose === 'WORK', `${lane} first call was not WORK`)
  assert(audit.modelCalls[1]?.purpose === 'GOVERNANCE_REFLECTION', `${lane} second call was not Reflection`)
  for (const kind of ['architectureIds', 'ruleIds', 'knowledgeIds', 'gateIds']) {
    assert((audit.route?.[kind] ?? []).length > 0, `${lane} route ${kind} is empty`)
  }
  assert(audit.closure?.status === 'COMPLETE', `${lane} Closure not COMPLETE`)
  assert(audit.closure?.moduleReceipts?.length >= 8, `${lane} missing Closure receipts`)
  assert(audit.journal?.status === 'CLOSED', `${lane} Journal not CLOSED`)
}
EOF

node --input-type=module - "$PROVIDER_LOG" <<'EOF'
import { readFileSync } from 'node:fs'
const lines = readFileSync(process.argv[2], 'utf8').trim().split(/\r?\n/).filter(Boolean)
const expected = [
  'responses|WORK',
  'responses|GOVERNANCE_REFLECTION',
  'chat_completions|WORK',
  'chat_completions|GOVERNANCE_REFLECTION',
]
if (JSON.stringify(lines) !== JSON.stringify(expected)) {
  throw new Error(`provider call order mismatch: ${JSON.stringify(lines)}`)
}
EOF

if grep -R -F 'OPENAI_COMPAT_' "$ROOT_DIR/agent_harness/public_plugins/governance_runtime/src" >/dev/null; then
  echo 'Provider configuration leaked into Governance Runtime' >&2
  exit 1
fi
if grep -R -F 'fixture-secret-key' "$AUDIT_ROOT" >/dev/null; then
  echo 'Provider secret leaked into audit artifacts' >&2
  exit 1
fi

printf '%s\n' \
  'LEVEL2C_SYNTHETIC_REAL_PROVIDER_PATH=PASS' \
  'LEVEL2C_REAL_ETTOOL_PROJECT_PLUGIN_PATH=PASS' \
  'LEVEL2C_WORK_THEN_AUTOMATIC_REFLECTION=PASS' \
  'LEVEL2C_A_R_K_G_ROUTE=PASS' \
  'LEVEL2C_8_OF_8_CLOSURE=PASS' \
  'LEVEL2C_AUDIT_SECRET_REDACTION=PASS' \
  'LEVEL2C_GOVERNANCE_RUNTIME_PROVIDER_INDEPENDENT=PASS' \
  'PHASE4A_REAL_PROVIDER_GOVERNANCE_PILOT_V0_1=PASS'
