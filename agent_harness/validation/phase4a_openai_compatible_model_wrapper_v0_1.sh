#!/usr/bin/env bash
set -euo pipefail

NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${OPENAI_COMPAT_WRAPPER_WORK_DIR:-$(mktemp -d)}"
PORT_FILE="$WORK_DIR/provider-port.txt"
PROVIDER_LOG="$WORK_DIR/provider.log"
PROVIDER_ERR="$WORK_DIR/provider.err"
WRAPPER_DIR="$ROOT_DIR/agent_harness/model_adapters/openai_compatible_wrapper"
WRAPPER_ENTRY="$WRAPPER_DIR/dist/cli.js"
LEVEL2_SCRIPT="$ROOT_DIR/agent_harness/validation/phase4a_public_governance_runtime_level2_model_v0_1.sh"
PROVIDER_PID=""

source "$ROOT_DIR/agent_harness/validation/lib/common_runtime.sh"

cleanup() {
  if [[ -n "$PROVIDER_PID" ]]; then kill "$PROVIDER_PID" >/dev/null 2>&1 || true; fi
  if [[ "${OPENAI_COMPAT_WRAPPER_KEEP_WORK_DIR:-0}" != "1" ]]; then rm -rf "$WORK_DIR"; fi
}
trap cleanup EXIT
mkdir -p "$WORK_DIR"

npm_install_if_needed "$ROOT_DIR/agent_harness/model_adapters/generic_model" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
(cd "$ROOT_DIR/agent_harness/model_adapters/generic_model" && npm test && npm run build)
npm_install_if_needed "$WRAPPER_DIR" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
(cd "$WRAPPER_DIR" && npm test && npm run build)
[[ -f "$WRAPPER_ENTRY" ]] || { echo "Wrapper entry missing: $WRAPPER_ENTRY" >&2; exit 1; }

cat > "$WORK_DIR/mock-openai-compatible-provider.mjs" <<'EOF'
import http from 'node:http'
import { appendFileSync, writeFileSync } from 'node:fs'

const portFile = process.env.MOCK_PROVIDER_PORT_FILE
const logFile = process.env.MOCK_PROVIDER_LOG
if (!portFile || !logFile) throw new Error('mock provider paths missing')

const json = (res, status, value) => {
  const body = JSON.stringify(value)
  res.writeHead(status, {
    'content-type': 'application/json',
    'content-length': Buffer.byteLength(body),
  })
  res.end(body)
}

const reflectionText = runtimeRequest => {
  const keep = [
    ...runtimeRequest.context.route.architectureIds,
    ...runtimeRequest.context.route.ruleIds,
    ...runtimeRequest.context.route.knowledgeIds,
    ...runtimeRequest.context.route.gateIds,
  ]
  const answer = (runtimeRequest.turnObservations ?? []).find(item => item.kind === 'ASSISTANT_MESSAGE')
  if (!answer?.text?.includes('A010.010')) throw new Error('governed assistant observation missing')
  return JSON.stringify({
    contractVersion: '0.1',
    taskId: runtimeRequest.taskId,
    turnId: runtimeRequest.turnId,
    context: {
      progress: 'OpenAI-compatible wrapper completed the governed synthetic analysis.',
      decisions: [],
      confirmed: ['Visible model output and routed context were observed before automatic Reflection.'],
      assumptions: [],
      openIssues: [],
      next: [],
      touchedRefs: keep,
    },
    knowledge: { scopeDecision: 'NONE', rationale: 'No additional durable knowledge beyond the existing synthetic baseline.', candidates: [] },
    experience: { scopeDecision: 'NONE', rationale: 'No cross-task experience candidate.', candidates: [] },
    architecture: { scopeDecision: 'NONE', rationale: 'No architecture change proposal.', candidates: [] },
    rules: { scopeDecision: 'NONE', rationale: 'No rule change proposal.', candidates: [] },
    evidence: { scopeDecision: 'NONE', rationale: 'No new validation evidence.', candidates: [] },
    workingSet: { keep, add: [], remove: [] },
    obligations: { opened: [], resolved: [], unchanged: [] },
  })
}

const server = http.createServer(async (req, res) => {
  try {
    if (req.method !== 'POST') return json(res, 405, { error: { message: 'POST required' } })
    if (req.headers.authorization !== 'Bearer mock-key') return json(res, 401, { error: { message: 'bad auth' } })
    let raw = ''
    for await (const chunk of req) raw += chunk
    const body = JSON.parse(raw)
    const path = req.url ?? ''
    let style
    let userText
    if (path === '/v1/responses') {
      style = 'responses'
      userText = body.input
    } else if (path === '/v1/chat/completions') {
      style = 'chat_completions'
      userText = body.messages?.find(item => item.role === 'user')?.content
    } else {
      return json(res, 404, { error: { message: `unknown path ${path}` } })
    }
    if (typeof userText !== 'string') throw new Error('provider user input missing')

    let purpose = 'WORK'
    let outputText = 'A010.010 Theme Runtime 是当前 UI theme 的架构入口；R010.010 要求复用统一主题变量，现有知识 K001.001 指向 source/ui/theme/index.ts。'
    try {
      const payload = JSON.parse(userText)
      if (payload?.runtimeRequest) {
        purpose = 'GOVERNANCE_REFLECTION'
        outputText = reflectionText(payload.runtimeRequest)
      }
    } catch {
      // WORK prompt is plain text.
    }

    if (purpose === 'GOVERNANCE_REFLECTION') {
      if (style === 'responses' && body.text?.format?.type !== 'json_schema') {
        throw new Error('Responses Reflection did not request json_schema')
      }
      if (style === 'chat_completions' && body.response_format?.type !== 'json_object') {
        throw new Error('Chat Reflection did not request json_object')
      }
    }
    appendFileSync(logFile, `${style}|${purpose}\n`, 'utf8')

    if (style === 'responses') {
      return json(res, 200, {
        id: `resp_${purpose}`,
        output: [{ type: 'message', content: [{ type: 'output_text', text: outputText }] }],
      })
    }
    return json(res, 200, {
      id: `chat_${purpose}`,
      choices: [{ index: 0, finish_reason: 'stop', message: { role: 'assistant', content: outputText } }],
    })
  } catch (error) {
    return json(res, 500, { error: { message: error instanceof Error ? error.message : String(error) } })
  }
})

server.listen(0, '127.0.0.1', () => {
  const address = server.address()
  if (!address || typeof address === 'string') throw new Error('mock provider address unavailable')
  writeFileSync(portFile, String(address.port), 'utf8')
})
EOF

MOCK_PROVIDER_PORT_FILE="$PORT_FILE" MOCK_PROVIDER_LOG="$PROVIDER_LOG" \
  node "$WORK_DIR/mock-openai-compatible-provider.mjs" 2>"$PROVIDER_ERR" &
PROVIDER_PID=$!
for _ in $(seq 1 100); do
  [[ -s "$PORT_FILE" ]] && break
  kill -0 "$PROVIDER_PID" >/dev/null 2>&1 || { cat "$PROVIDER_ERR" >&2; exit 1; }
  sleep 0.05
done
[[ -s "$PORT_FILE" ]] || { echo "mock provider did not start" >&2; cat "$PROVIDER_ERR" >&2; exit 1; }
BASE_URL="http://127.0.0.1:$(cat "$PORT_FILE")/v1"
WRAPPER_ARGS_JSON="$(python3 -c 'import json,sys; print(json.dumps([sys.argv[1]]))' "$WRAPPER_ENTRY")"
NODE_EXE="$(command -v node)"

run_level2b() {
  local style="$1"
  local chat_mode="$2"
  export MODEL_PILOT_MODE=real
  export GOVERNANCE_MODEL_BRIDGE_COMMAND="$NODE_EXE"
  export GOVERNANCE_MODEL_BRIDGE_ARGS_JSON="$WRAPPER_ARGS_JSON"
  export GOVERNANCE_MODEL_BRIDGE_CLIENT_ID="openai-compatible-${style}"
  export GOVERNANCE_MODEL_BRIDGE_ENV_NAMES="OPENAI_COMPAT_BASE_URL,OPENAI_COMPAT_API_KEY,OPENAI_COMPAT_MODEL,OPENAI_COMPAT_API_STYLE,OPENAI_COMPAT_CHAT_JSON_MODE,OPENAI_COMPAT_PROVIDER_ID"
  export OPENAI_COMPAT_BASE_URL="$BASE_URL"
  export OPENAI_COMPAT_API_KEY="mock-key"
  export OPENAI_COMPAT_MODEL="mock-model"
  export OPENAI_COMPAT_API_STYLE="$style"
  export OPENAI_COMPAT_CHAT_JSON_MODE="$chat_mode"
  export OPENAI_COMPAT_PROVIDER_ID="mock-openai-compatible"
  export GOVERNANCE_LEVEL2_MODEL_WORK_DIR="$WORK_DIR/level2-${style}"
  bash "$LEVEL2_SCRIPT"
}

run_level2b responses json_schema
run_level2b chat_completions json_object

python3 - "$PROVIDER_LOG" <<'PY'
from pathlib import Path
import sys
lines = [line.strip() for line in Path(sys.argv[1]).read_text(encoding='utf-8').splitlines() if line.strip()]
expected = [
    'responses|WORK',
    'responses|GOVERNANCE_REFLECTION',
    'chat_completions|WORK',
    'chat_completions|GOVERNANCE_REFLECTION',
]
if lines != expected:
    raise SystemExit(f'Unexpected provider call sequence: {lines!r}')
print('LEVEL2B_OPENAI_COMPAT_RESPONSES=PASS')
print('LEVEL2B_OPENAI_COMPAT_CHAT_COMPLETIONS=PASS')
print('LEVEL2B_OPENAI_COMPAT_AUTOMATIC_REFLECTION=PASS')
PY

python3 - "$ROOT_DIR" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
wrapper = '\n'.join(p.read_text(encoding='utf-8') for p in (root / 'agent_harness/model_adapters/openai_compatible_wrapper/src').rglob('*.ts'))
for forbidden in [
    'contextManager', 'knowledgeManager', 'agentGovernanceKernel', 'agent/pre-step',
    'agent/turn-stopping', 'mcp__', 'Google Drive',
]:
    if forbidden in wrapper:
        raise SystemExit(f'Governance/Host/Tool coupling leaked into model wrapper: {forbidden}')
for required in ['OPENAI_COMPAT_API_STYLE', "'/responses'", "'/chat/completions'", "type: 'json_schema'", "type: 'json_object'"]:
    if required not in wrapper:
        raise SystemExit(f'OpenAI-compatible wrapper contract missing: {required}')
print('LEVEL2B_OPENAI_COMPAT_MODEL_LAYER_ONLY=PASS')
PY

printf '%s\n' 'PHASE4A_OPENAI_COMPATIBLE_MODEL_WRAPPER_V0_1=PASS'
