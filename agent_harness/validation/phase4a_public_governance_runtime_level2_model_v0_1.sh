#!/usr/bin/env bash
set -euo pipefail

CORDIS_VERSION="${CORDIS_VERSION:-4.0.1}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${GOVERNANCE_LEVEL2_MODEL_WORK_DIR:-$(mktemp -d)}"
SMOKE_DIR="$WORK_DIR/cordis-smoke"
PROJECT_ROOT="$WORK_DIR/project"
RUNTIME_ROOT="$WORK_DIR/runtime"
FAKE_MODEL_LOG="$WORK_DIR/fake-model.log"
MODEL_PILOT_MODE="${MODEL_PILOT_MODE:-contract}"

source "$ROOT_DIR/agent_harness/validation/lib/common_runtime.sh"
trap 'rm -rf "$WORK_DIR"' EXIT
mkdir -p "$SMOKE_DIR" "$PROJECT_ROOT/architecture" "$PROJECT_ROOT/rules" "$PROJECT_ROOT/knowledge" "$PROJECT_ROOT/gates" "$RUNTIME_ROOT"
printf 'synthetic\n' > "$PROJECT_ROOT/project.marker"
export AGENT_HARNESS_STATE_ROOT="$RUNTIME_ROOT"
unset AGENT_HARNESS_GLOBAL_KNOWLEDGE_ROOT || true

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
  model_adapters/generic_model
  model_adapters/json_process_client
  pilots/generic_model
)
for dir in "${PACKAGES[@]}"; do
  npm_install_if_needed "$ROOT_DIR/agent_harness/$dir" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
  (cd "$ROOT_DIR/agent_harness/$dir" && npm test && npm run build)
done

cat > "$PROJECT_ROOT/architecture/00_INDEX.md" <<'EOF'
---
interface: project-resource-index-v0.1
resource: architecture
standard: architecture-v0.1
files:
  - id: A010
    file: 010_interface.md
    title: Interface Architecture
    summary: UI theme architecture
    aliases: [ui, theme, interface]
---
EOF
cat > "$PROJECT_ROOT/architecture/010_interface.md" <<'EOF'
# [A010] Interface Architecture
Role: application interface layer

## [A010.010] Theme Runtime
Role: current theme runtime
Boundary: theme changes remain inside the theme module
Resources: source/ui/theme/
Relations: R010.010
EOF

cat > "$PROJECT_ROOT/rules/00_INDEX.md" <<'EOF'
---
interface: project-resource-index-v0.1
resource: rules
standard: rule-v0.1
files:
  - id: R010
    file: 010_interface.md
    title: Interface Rules
    summary: UI theme constraints
    aliases: [ui, theme, style]
---
EOF
cat > "$PROJECT_ROOT/rules/010_interface.md" <<'EOF'
# [R010] Interface Rules

## [R010.010] Theme Variables
Level: MUST
When: 修改 UI theme
Rule: 必须复用统一主题变量。
Refs: [A010.010, G010.010]
EOF

cat > "$PROJECT_ROOT/knowledge/TAXONOMY.yaml" <<'EOF'
standard: knowledge-library-v0.2
categories:
  - id: C010
    title: Project Runtime
    summary: Project-specific runtime implementation knowledge.
EOF
cat > "$PROJECT_ROOT/knowledge/001_library.md" <<'EOF'
# [K001] Project Runtime

## [K001.001] Theme Source
Status: VALIDATED
Category: C010
Fact: The synthetic project theme entry is source/ui/theme/index.ts.
Provenance: PROJECT-BASELINE
Tags: [theme]
EOF

cat > "$PROJECT_ROOT/gates/00_INDEX.md" <<'EOF'
---
interface: project-resource-index-v0.1
resource: gates
standard: gate-v0.1
files:
  - id: G010
    file: 010_validation.yaml
    title: Interface Validation
    summary: UI validation gate
    aliases: [ui, theme, validation]
---
EOF
cat > "$PROJECT_ROOT/gates/010_validation.yaml" <<'EOF'
standard: gate-v0.1
file_id: G010
title: Interface Validation
nodes:
  - id: G010.010
    title: UI Theme Validation
    gate:
      level: MUST
      when: 修改 UI theme
      steps:
        - id: build
          tool: build.execute
      pass:
        mode: all_steps_pass
      refs: [R010.010]
EOF

if [[ "$MODEL_PILOT_MODE" == "contract" ]]; then
  cat > "$WORK_DIR/fake-model.mjs" <<'EOF'
import { appendFileSync } from 'node:fs'

let input = ''
for await (const chunk of process.stdin) input += chunk
const request = JSON.parse(input)
appendFileSync(process.env.FAKE_MODEL_LOG, `${request.purpose}|${request.requestId}\n`, 'utf8')

const response = {
  contractVersion: '0.1',
  requestId: request.requestId,
  providerId: 'synthetic-provider',
  modelId: 'synthetic-model-v0.1',
}

if (request.purpose === 'WORK') {
  if (!request.userText.includes('分析当前项目 UI theme 的架构和约束，并给出简洁结论。')) {
    throw new Error('Original business task was not preserved in work request')
  }
  if (!request.userText.includes('AUTOMATIC GOVERNANCE CONTEXT')) {
    throw new Error('Automatic Governance Context was not supplied to work model')
  }
  response.outputText = '当前 UI theme 由 A010.010 Theme Runtime 约束，修改时必须遵守 R010.010 统一主题变量规则；现有主题入口知识指向 source/ui/theme/index.ts。'
} else if (request.purpose === 'GOVERNANCE_REFLECTION') {
  const payload = JSON.parse(request.userText)
  const runtimeRequest = payload.runtimeRequest
  const observations = runtimeRequest.turnObservations ?? []
  const task = observations.find(item => item.kind === 'TASK_INPUT')
  const answer = observations.find(item => item.kind === 'ASSISTANT_MESSAGE')
  if (!task?.text?.includes('UI theme')) throw new Error('TASK_INPUT observation missing from semantic request')
  if (!answer?.text?.includes('A010.010')) throw new Error('ASSISTANT_MESSAGE observation missing from semantic request')
  if (!runtimeRequest.knowledgeClassification.projectCategories.some(item => item.categoryId === 'C010')) {
    throw new Error('Project Knowledge categories missing from semantic request')
  }
  const keep = [
    ...runtimeRequest.context.route.architectureIds,
    ...runtimeRequest.context.route.ruleIds,
    ...runtimeRequest.context.route.knowledgeIds,
    ...runtimeRequest.context.route.gateIds,
  ]
  response.outputJson = {
    contractVersion: '0.1',
    taskId: runtimeRequest.taskId,
    turnId: runtimeRequest.turnId,
    context: {
      progress: 'Completed governed model analysis of the synthetic UI theme.',
      decisions: [],
      confirmed: ['The routed project context was sufficient for this analysis.'],
      assumptions: [],
      openIssues: [],
      next: [],
      touchedRefs: keep,
    },
    knowledge: {
      scopeDecision: 'PROJECT',
      rationale: 'The work produced a project-specific durable observation.',
      candidates: [{
        domain: 'knowledge',
        title: 'Governed Theme Analysis Path',
        factOrProposal: 'The synthetic project UI theme can be analyzed from routed A010.010, R010.010 and K001.001 context without host-specific governance logic.',
        scopeDecision: 'PROJECT',
        rationale: 'This is specific to the synthetic project runtime and routing.',
        provenanceRefs: [answer.observationRef],
        evidenceRefs: [],
        relatedRefs: ['knowledge-category://project/C010', ...keep],
        confidence: 0.94,
      }],
    },
    experience: { scopeDecision: 'NONE', rationale: 'No cross-task experience candidate.', candidates: [] },
    architecture: { scopeDecision: 'NONE', rationale: 'No architecture change proposal.', candidates: [] },
    rules: { scopeDecision: 'NONE', rationale: 'No rule change proposal.', candidates: [] },
    evidence: { scopeDecision: 'NONE', rationale: 'No new validation evidence.', candidates: [] },
    workingSet: { keep, add: [], remove: [] },
    obligations: { opened: [], resolved: [], unchanged: [] },
  }
} else {
  throw new Error(`Unknown model purpose ${request.purpose}`)
}
process.stdout.write(JSON.stringify(response))
EOF
  export GOVERNANCE_MODEL_BRIDGE_COMMAND="$(command -v node)"
  export GOVERNANCE_MODEL_BRIDGE_ARGS_JSON="[\"$WORK_DIR/fake-model.mjs\"]"
  export GOVERNANCE_MODEL_BRIDGE_CLIENT_ID="contract-model"
  export FAKE_MODEL_LOG
elif [[ "$MODEL_PILOT_MODE" == "real" ]]; then
  : "${GOVERNANCE_MODEL_BRIDGE_COMMAND:?real mode requires GOVERNANCE_MODEL_BRIDGE_COMMAND}"
  export GOVERNANCE_MODEL_BRIDGE_ARGS_JSON="${GOVERNANCE_MODEL_BRIDGE_ARGS_JSON:-[]}"
  export GOVERNANCE_MODEL_BRIDGE_CLIENT_ID="${GOVERNANCE_MODEL_BRIDGE_CLIENT_ID:-real-model}"
  export GOVERNANCE_MODEL_BRIDGE_ENV_NAMES="${GOVERNANCE_MODEL_BRIDGE_ENV_NAMES:-}"
else
  echo "Unsupported MODEL_PILOT_MODE=$MODEL_PILOT_MODE" >&2
  exit 2
fi

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
  "$ROOT_DIR/agent_harness/model_adapters/generic_model" \
  "$ROOT_DIR/agent_harness/model_adapters/json_process_client" \
  "$ROOT_DIR/agent_harness/pilots/generic_model"

cat > "$SMOKE_DIR/smoke.mjs" <<'EOF'
import { Context } from '@deepseek-ai/cordis'
import GovernanceCatalogService from '@agent-harness/governance-core'
import * as projectManagerPlugin from '@agent-harness/project-manager'
import * as architecturePlugin from '@agent-harness/architecture-navigator'
import * as rulePlugin from '@agent-harness/rule-manager'
import * as evidencePlugin from '@agent-harness/evidence-state-manager'
import * as knowledgePlugin from '@agent-harness/knowledge-manager'
import * as gatePlugin from '@agent-harness/gate-manager'
import * as contextPlugin from '@agent-harness/context-builder'
import * as experiencePlugin from '@agent-harness/experience-memory-manager'
import * as kernelPlugin from '@agent-harness/agent-governance-kernel'
import * as closurePlugin from '@agent-harness/agent-governance-closure-adapters'
import * as enginePlugin from '@agent-harness/auto-governance-engine'
import * as runtimePlugin from '@agent-harness/governance-runtime'
import { JsonProcessModelClient } from '@agent-harness/json-process-model-client'
import { GenericModelPilotDriver } from '@agent-harness/generic-model-pilot'
import { readFileSync } from 'node:fs'

const tick = () => new Promise(resolve => setTimeout(resolve, 0))
const assert = (condition, message) => { if (!condition) throw new Error(message) }
const projectRoot = process.env.SYNTHETIC_PROJECT_ROOT
assert(projectRoot, 'SYNTHETIC_PROJECT_ROOT missing')

const manifest = {
  contract_version: '0.1',
  project: { id: 'synthetic-project', name: 'Synthetic Project', type: 'test' },
  root: { markers: ['project.marker'] },
  resources: {
    architecture: { path: 'architecture/', standard: 'architecture-v0.1' },
    rules: { path: 'rules/', standard: 'rule-v0.1' },
    knowledge: { path: 'knowledge/', standard: 'knowledge-v0.1' },
    gates: { path: 'gates/', standard: 'gate-v0.1' },
  },
  adapters: {},
}

const ctx = new Context()
const fibers = []
for (const plugin of [
  GovernanceCatalogService,
  projectManagerPlugin,
  architecturePlugin,
  rulePlugin,
  evidencePlugin,
  knowledgePlugin,
  gatePlugin,
  contextPlugin,
  experiencePlugin,
  kernelPlugin,
  closurePlugin,
  enginePlugin,
  runtimePlugin,
]) {
  fibers.push(ctx.plugin(plugin)); await tick()
}
const pm = ctx.get('projectManager')
const runtime = ctx.get('governanceRuntime')
const kernel = ctx.get('agentGovernanceKernel')
const knowledge = ctx.get('knowledgeManager')
assert(pm && runtime && kernel && knowledge, 'required governance services missing')
const disposeProject = pm.registerProject(manifest, projectRoot)

const args = JSON.parse(process.env.GOVERNANCE_MODEL_BRIDGE_ARGS_JSON || '[]')
assert(Array.isArray(args) && args.every(item => typeof item === 'string'), 'GOVERNANCE_MODEL_BRIDGE_ARGS_JSON must be string[]')
const explicitEnv = {}
if (process.env.MODEL_PILOT_MODE === 'contract') explicitEnv.FAKE_MODEL_LOG = process.env.FAKE_MODEL_LOG
for (const name of (process.env.GOVERNANCE_MODEL_BRIDGE_ENV_NAMES || '').split(',').map(item => item.trim()).filter(Boolean)) {
  const value = process.env[name]
  if (value !== undefined) explicitEnv[name] = value
}
const command = process.env.GOVERNANCE_MODEL_BRIDGE_COMMAND
assert(command, 'GOVERNANCE_MODEL_BRIDGE_COMMAND missing')
const client = new JsonProcessModelClient({
  clientId: process.env.GOVERNANCE_MODEL_BRIDGE_CLIENT_ID || 'model',
  command,
  args,
  env: explicitEnv,
  ...(process.env.GOVERNANCE_MODEL_BRIDGE_CWD ? { cwd: process.env.GOVERNANCE_MODEL_BRIDGE_CWD } : {}),
  timeoutMs: Number(process.env.GOVERNANCE_MODEL_TIMEOUT_MS || 120000),
})
const driver = new GenericModelPilotDriver(runtime, client)
const taskText = '分析当前项目 UI theme 的架构和约束，并给出简洁结论。'
for (const forbidden of ['Context Manager', 'Knowledge Manager', 'PROJECT / PUBLIC', 'Reflection', 'Closure']) {
  assert(!taskText.includes(forbidden), `Business task contains governance hint: ${forbidden}`)
}
const result = await driver.runTurn({
  runtimeId: 'LEVEL2-MODEL',
  turnId: 'TURN-1',
  taskText,
  projectId: 'synthetic-project',
  workspacePath: projectRoot,
})
assert(result.work.visibleOutput.length > 0, 'Model produced no user-visible work output')
assert(result.open.taskObservation.text === taskText, 'Business task was modified before governance runtime')
const observations = runtime.getTurnObservations('LEVEL2-MODEL', 'TURN-1')
assert(observations.some(item => item.kind === 'TASK_INPUT'), 'TASK_INPUT observation missing')
assert(observations.some(item => item.kind === 'ASSISTANT_MESSAGE' && item.text === result.work.visibleOutput), 'Visible model output was not governed')
assert(result.close.closure.status === 'COMPLETE', 'Model Turn Closure did not complete')
assert(kernel.getTurn(result.open.taskId, 'TURN-1')?.status === 'CLOSED', 'Model Turn Journal did not close')
assert(result.close.closure.moduleReceipts.length >= 8, '8/8 Closure receipts missing')
const scope = result.close.reflection.result.knowledge.scopeDecision
assert(['NONE', 'PROJECT', 'PUBLIC', 'BOTH'].includes(scope), 'Knowledge scope was not explicitly classified')

if (process.env.MODEL_PILOT_MODE === 'contract') {
  assert(scope === 'PROJECT', 'Contract model did not exercise PROJECT Knowledge classification')
  assert(knowledge.getIndex('synthetic-project').statusCounts.CANDIDATE >= 1, 'Contract model Knowledge Candidate not persisted')
  const log = readFileSync(process.env.FAKE_MODEL_LOG, 'utf8').trim().split(/\r?\n/).filter(Boolean)
  assert(log.length === 2, `Expected exactly two model calls, got ${log.length}`)
  assert(log[0]?.startsWith('WORK|'), 'First model call was not business WORK')
  assert(log[1]?.startsWith('GOVERNANCE_REFLECTION|'), 'Second model call was not automatic Reflection')
}

disposeProject()
for (const fiber of fibers.reverse()) await fiber.dispose()
console.log('LEVEL2_MODEL_BUSINESS_TASK_UNCHANGED=PASS')
console.log('LEVEL2_MODEL_AUTOMATIC_CONTEXT=PASS')
console.log('LEVEL2_MODEL_VISIBLE_OUTPUT_OBSERVED=PASS')
console.log('LEVEL2_MODEL_AUTOMATIC_REFLECTION=PASS')
console.log('LEVEL2_MODEL_KNOWLEDGE_CLASSIFIED=PASS')
console.log('LEVEL2_MODEL_8_OF_8_CLOSURE=PASS')
console.log('LEVEL2_MODEL_TURN_CLOSED=PASS')
EOF

export SYNTHETIC_PROJECT_ROOT="$PROJECT_ROOT"
export MODEL_PILOT_MODE
node "$SMOKE_DIR/smoke.mjs"

python3 - "$ROOT_DIR" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
runtime = '\n'.join(p.read_text(encoding='utf-8') for p in (root / 'agent_harness/public_plugins/governance_runtime/src').rglob('*.ts'))
model = '\n'.join(p.read_text(encoding='utf-8') for p in (root / 'agent_harness/model_adapters').rglob('*.ts'))
pilot = '\n'.join(p.read_text(encoding='utf-8') for p in (root / 'agent_harness/pilots/generic_model').rglob('*.ts'))
for forbidden in ['DEEPSEEK_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'mcp__', 'agent/pre-step', 'agent/turn-stopping']:
    if forbidden in runtime:
        raise SystemExit(f'Provider/Host coupling leaked into Governance Runtime: {forbidden}')
for text, label in [(model, 'model adapter'), (pilot, 'generic pilot')]:
    for forbidden in ['ContextManager', 'knowledgeManager.submit', 'agentGovernanceKernel.closeTurn', 'mcp__', 'agent/pre-step']:
        if forbidden in text:
            raise SystemExit(f'Governance/Host logic leaked into {label}: {forbidden}')
print('LEVEL2_MODEL_RUNTIME_PROVIDER_INDEPENDENT=PASS')
print('LEVEL2_MODEL_ADAPTER_GOVERNANCE_THIN=PASS')
print('LEVEL2_MODEL_PILOT_HOST_INDEPENDENT=PASS')
PY

printf '%s\n' 'PHASE4A_PUBLIC_GOVERNANCE_RUNTIME_LEVEL2_MODEL_V0_1=PASS'
