#!/usr/bin/env bash
set -euo pipefail

CORDIS_VERSION="${CORDIS_VERSION:-4.0.1}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${GOVERNANCE_RUNTIME_WORK_DIR:-$(mktemp -d)}"
SMOKE_DIR="$WORK_DIR/cordis-smoke"
PROJECT_ROOT="$WORK_DIR/project"
RUNTIME_ROOT="$WORK_DIR/runtime"

source "$ROOT_DIR/agent_harness/validation/lib/common_runtime.sh"
trap 'rm -rf "$WORK_DIR"' EXIT
mkdir -p "$SMOKE_DIR" "$PROJECT_ROOT/architecture" "$PROJECT_ROOT/rules" "$PROJECT_ROOT/knowledge" "$PROJECT_ROOT/gates" "$RUNTIME_ROOT"
printf 'synthetic\n' > "$PROJECT_ROOT/project.marker"
export AGENT_HARNESS_STATE_ROOT="$RUNTIME_ROOT"
unset AGENT_HARNESS_GLOBAL_KNOWLEDGE_ROOT || true

for dir in \
  project_contract \
  governance_core \
  public_plugins/project_manager \
  public_plugins/architecture_navigator \
  public_plugins/rule_manager \
  public_plugins/evidence_state_manager \
  public_plugins/knowledge_manager \
  public_plugins/gate_manager \
  public_plugins/context_builder \
  public_plugins/experience_memory_manager \
  public_plugins/agent_governance_kernel \
  public_plugins/agent_governance_closure_adapters \
  public_plugins/auto_governance_engine \
  public_plugins/governance_runtime; do
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
    summary: UI architecture map
    aliases: [ui, theme]
---
EOF
cat > "$PROJECT_ROOT/architecture/010_interface.md" <<'EOF'
# [A010] Interface Architecture
Role: application interface layer

## [A010.010] Theme Runtime
Role: current theme runtime
Boundary: theme changes stay inside this module
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
    summary: UI constraints
    aliases: [ui, theme]
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

## [K001.001] Project Theme Entry
Status: VALIDATED
Category: C010
Fact: The synthetic project resolves its theme through source/ui/theme/index.ts.
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
    aliases: [ui, test]
---
EOF
cat > "$PROJECT_ROOT/gates/010_validation.yaml" <<'EOF'
standard: gate-v0.1
file_id: G010
title: Interface Validation
nodes:
  - id: G010.010
    title: UI Build
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
  "$ROOT_DIR/agent_harness/public_plugins/governance_runtime"

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
fibers.push(ctx.plugin(GovernanceCatalogService)); await tick()
fibers.push(ctx.plugin(projectManagerPlugin)); await tick()
fibers.push(ctx.plugin(architecturePlugin)); await tick()
fibers.push(ctx.plugin(rulePlugin)); await tick()
fibers.push(ctx.plugin(evidencePlugin)); await tick()
fibers.push(ctx.plugin(knowledgePlugin)); await tick()
fibers.push(ctx.plugin(gatePlugin)); await tick()
fibers.push(ctx.plugin(contextPlugin)); await tick()
fibers.push(ctx.plugin(experiencePlugin)); await tick()
fibers.push(ctx.plugin(kernelPlugin)); await tick()
fibers.push(ctx.plugin(closurePlugin)); await tick()
fibers.push(ctx.plugin(enginePlugin)); await tick()
fibers.push(ctx.plugin(runtimePlugin)); await tick()

const pm = ctx.get('projectManager')
const runtime = ctx.get('governanceRuntime')
const kernel = ctx.get('agentGovernanceKernel')
const knowledge = ctx.get('knowledgeManager')
assert(pm && runtime && kernel && knowledge, 'required governance services missing')
const disposeProject = pm.registerProject(manifest, projectRoot)

const none = () => ({ scopeDecision: 'NONE', rationale: 'No durable change in this domain.', candidates: [] })
const reflectionFor = (request, knowledgeCandidate) => {
  const keep = [
    ...request.context.route.architectureIds,
    ...request.context.route.ruleIds,
    ...request.context.route.knowledgeIds,
    ...request.context.route.gateIds,
  ]
  return {
    contractVersion: '0.1',
    taskId: request.taskId,
    turnId: request.turnId,
    context: {
      progress: `Closed ${request.turnId} through the host-independent Governance Runtime.`,
      decisions: [],
      confirmed: ['Runtime lifecycle and semantic reflection were automatic.'],
      assumptions: [],
      openIssues: [],
      next: [],
      touchedRefs: keep,
    },
    knowledge: knowledgeCandidate ? {
      scopeDecision: 'PROJECT',
      rationale: 'The fact is specific to this synthetic project.',
      candidates: [{
        domain: 'knowledge',
        title: 'Governed Runtime Observation',
        factOrProposal: 'The synthetic project governance runtime closes analysis Turns through the common runtime controller.',
        scopeDecision: 'PROJECT',
        rationale: 'Project-specific implementation fact.',
        provenanceRefs: [`runtime://${request.runtimeId}/${request.turnId}`],
        evidenceRefs: [],
        relatedRefs: ['knowledge-category://project/C010'],
        confidence: 0.95,
      }],
    } : none(),
    experience: none(),
    architecture: none(),
    rules: none(),
    evidence: none(),
    workingSet: { keep, add: [], remove: [] },
    obligations: { opened: [], resolved: [], unchanged: [] },
  }
}

let semanticCalls = 0
const semantic = {
  executorId: 'mock-model-agnostic-semantic-executor',
  reflect(request) {
    semanticCalls += 1
    assert(request.runtimeId === 'GENERIC-1', 'Semantic request runtimeId mismatch')
    assert(request.knowledgeClassification.projectCategories.some(item => item.categoryId === 'C010'), 'Project Knowledge categories were not supplied')
    assert(request.knowledgeClassification.publicLibraryMounted === false, 'Public Knowledge should be unavailable in this smoke')
    return reflectionFor(request, request.turnId === 'TURN-1')
  },
}

const opened = await runtime.openTurn({
  runtimeId: 'GENERIC-1',
  turnId: 'TURN-1',
  taskText: 'Analyze the project UI theme architecture and constraints.',
  projectId: 'synthetic-project',
  workspacePath: projectRoot,
  semanticExecutor: semantic,
  userMessageRefs: ['message://user/1'],
})
assert(opened.journal.status === 'OPEN', 'TURN-1 Journal did not open')
assert(opened.context.route.architectureIds.length > 0, 'Architecture routing did not trigger')
assert(opened.context.route.ruleIds.length > 0, 'Rule routing did not trigger')
assert(opened.context.route.knowledgeIds.length > 0, 'Knowledge routing did not trigger')
assert(opened.context.route.gateIds.length > 0, 'Gate routing did not trigger')
assert(opened.context.text.includes('GOVERNANCE CONTEXT'), 'Context envelope was not built')
assert(runtime.preflightAction({ runtimeId: 'GENERIC-1', turnId: 'TURN-1', name: 'read_file' }).allowed, 'Read-only action should be allowed')

runtime.observeWork({
  kind: 'resource-touch',
  runtimeId: 'GENERIC-1',
  turnId: 'TURN-1',
  resourceRefs: ['source://ui/theme/index.ts'],
})
const closed = await runtime.closeTurn({
  runtimeId: 'GENERIC-1',
  turnId: 'TURN-1',
  assistantMessageRefs: ['message://assistant/1'],
})
assert(closed.closure.status === 'COMPLETE', 'TURN-1 Closure did not complete')
assert(kernel.getTurn(opened.taskId, 'TURN-1')?.status === 'CLOSED', 'TURN-1 Journal did not close')
assert(closed.closure.moduleReceipts.length >= 8, 'All mandatory Closure receipts were not produced')
assert(semanticCalls === 1, 'SemanticExecutor was not triggered exactly once for TURN-1')
assert(knowledge.getIndex('synthetic-project').statusCounts.CANDIDATE >= 1, 'Knowledge Candidate was not persisted')
assert(runtime.getStatus('GENERIC-1')?.activeTurnId === undefined, 'Runtime still reports TURN-1 active')

const opened2 = await runtime.openTurn({
  runtimeId: 'GENERIC-1',
  turnId: 'TURN-2',
  taskText: 'Continue the same analysis without any durable new finding.',
  projectId: 'synthetic-project',
  workspacePath: projectRoot,
})
assert(opened2.context.stateVersion >= closed.context.stateVersion, 'Context was not reused across Turns')
const closed2 = await runtime.closeTurn({ runtimeId: 'GENERIC-1', turnId: 'TURN-2' })
assert(closed2.closure.status === 'COMPLETE', 'TURN-2 Closure did not complete')
assert(semanticCalls === 2, 'Stored SemanticExecutor was not reused for TURN-2')

let failOnce = true
const flaky = {
  executorId: 'mock-flaky-semantic-executor',
  reflect(request) {
    if (failOnce) {
      failOnce = false
      throw new Error('synthetic semantic interruption')
    }
    return reflectionFor(request, false)
  },
}
const recovery1 = await runtime.openTurn({
  runtimeId: 'GENERIC-RECOVERY',
  turnId: 'TURN-A',
  taskText: 'Analyze the UI theme architecture for recovery testing.',
  projectId: 'synthetic-project',
  workspacePath: projectRoot,
  semanticExecutor: flaky,
})
let failed = false
try {
  await runtime.closeTurn({ runtimeId: 'GENERIC-RECOVERY', turnId: 'TURN-A' })
} catch (error) {
  failed = String(error).includes('synthetic semantic interruption')
}
assert(failed, 'Synthetic Reflection failure did not surface')
assert(kernel.getTurn(recovery1.taskId, 'TURN-A')?.status === 'CLOSURE_PENDING', 'Failed Reflection did not leave CLOSURE_PENDING')

const recoveredSemantic = {
  executorId: 'mock-recovered-semantic-executor',
  reflect(request) { return reflectionFor(request, false) },
}
const recovery2 = await runtime.openTurn({
  runtimeId: 'GENERIC-RECOVERY',
  turnId: 'TURN-B',
  taskText: 'Continue after the interrupted prior Turn.',
  projectId: 'synthetic-project',
  workspacePath: projectRoot,
  semanticExecutor: recoveredSemantic,
})
assert(kernel.getTurn(recovery1.taskId, 'TURN-A')?.status === 'CLOSED', 'New Turn did not auto-recover prior CLOSURE_PENDING Turn')
assert(recovery2.journal.status === 'OPEN', 'TURN-B did not open after automatic recovery')
const recoveryClosed = await runtime.closeTurn({ runtimeId: 'GENERIC-RECOVERY', turnId: 'TURN-B' })
assert(recoveryClosed.closure.status === 'COMPLETE', 'TURN-B Closure did not complete')

const completed = runtime.completeTask('GENERIC-1')
assert(completed.status === 'COMPLETED', 'Governance Runtime could not complete clean task')

const registry = await import('node:fs').then(fs => fs.readFileSync(process.env.PUBLIC_PLUGIN_REGISTRY, 'utf8'))
assert(registry.includes('public.governance-runtime'), 'Public Registry missing Governance Runtime')
assert(registry.includes('public.auto-governance-engine'), 'Public Registry missing Auto Governance Engine')
assert(!registry.includes('public.auto-governance-orchestrator'), 'Legacy Host-coupled Orchestrator must not remain canonical')

for (const fiber of fibers.reverse()) await fiber.dispose()
disposeProject()
console.log('GENERIC_RUNTIME_PROJECT_CONTEXT_ROUTING=PASS')
console.log('GENERIC_RUNTIME_SEMANTIC_EXECUTOR=PASS')
console.log('GENERIC_RUNTIME_KNOWLEDGE_CLASSIFICATION=PASS')
console.log('GENERIC_RUNTIME_8_OF_8_CLOSURE=PASS')
console.log('GENERIC_RUNTIME_MULTI_TURN_CONTEXT=PASS')
console.log('GENERIC_RUNTIME_AUTOMATIC_RECOVERY=PASS')
console.log('GENERIC_RUNTIME_HOST_INDEPENDENT=PASS')
EOF

export SYNTHETIC_PROJECT_ROOT="$PROJECT_ROOT"
export PUBLIC_PLUGIN_REGISTRY="$ROOT_DIR/agent_harness/public_plugins/public_plugins.v0.1.yaml"
node "$SMOKE_DIR/smoke.mjs"

python3 - "$ROOT_DIR" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
paths = [
    root / 'agent_harness/public_plugins/auto_governance_engine/src',
    root / 'agent_harness/public_plugins/governance_runtime/src',
]
for path in paths:
    text = '\n'.join(file.read_text(encoding='utf-8') for file in path.rglob('*.ts'))
    for forbidden in [
        'agent/pre-step', 'agent/turn-stopping', 'session/event', 'tools.register',
        'mcp__', 'Google Drive', 'GDRIVE_', 'DEEPSEEK_API_KEY',
    ]:
        if forbidden in text:
            raise SystemExit(f'Host/tool coupling leaked into {path}: {forbidden}')
runtime = (root / 'agent_harness/public_plugins/governance_runtime/src/service.ts').read_text(encoding='utf-8')
for required in ['openTurn(', 'observeWork(', 'preflightAction(', 'closeTurn(', 'SemanticExecutor', 'recoverUnresolvedTurns']:
    if required not in runtime:
        raise SystemExit(f'Governance Runtime missing contract: {required}')
print('GOVERNANCE_RUNTIME_NO_HOST_EVENTS=PASS')
print('GOVERNANCE_RUNTIME_NO_TOOL_PLUGIN_COUPLING=PASS')
PY

printf '%s\n' \
  'PHASE4A_PUBLIC_GOVERNANCE_RUNTIME_V0_1=PASS'
