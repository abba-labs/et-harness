#!/usr/bin/env bash
set -euo pipefail

CORDIS_VERSION="${CORDIS_VERSION:-4.0.1}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${CONTEXT_MANAGEMENT_WORK_DIR:-$(mktemp -d)}"
SMOKE_DIR="$WORK_DIR/cordis-smoke"
GLOBAL_ROOT="$WORK_DIR/global-knowledge"
PROJECT_ROOT="$WORK_DIR/project"
RUNTIME_ROOT="$WORK_DIR/runtime"

source "$ROOT_DIR/agent_harness/validation/lib/common_runtime.sh"
trap 'rm -rf "$WORK_DIR"' EXIT
mkdir -p "$SMOKE_DIR" "$GLOBAL_ROOT" "$PROJECT_ROOT/architecture" "$PROJECT_ROOT/rules" "$PROJECT_ROOT/knowledge" "$PROJECT_ROOT/gates" "$RUNTIME_ROOT"
printf 'synthetic\n' > "$PROJECT_ROOT/project.marker"
export AGENT_HARNESS_STATE_ROOT="$RUNTIME_ROOT"

for dir in \
  project_contract \
  governance_core \
  public_plugins/project_manager \
  public_plugins/architecture_navigator \
  public_plugins/rule_manager \
  public_plugins/evidence_state_manager \
  public_plugins/knowledge_manager \
  public_plugins/gate_manager \
  public_plugins/context_builder; do
  npm_install_if_needed "$ROOT_DIR/agent_harness/$dir" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
  (cd "$ROOT_DIR/agent_harness/$dir" && npm test && npm run build)
done

cat > "$GLOBAL_ROOT/TAXONOMY.yaml" <<'EOF'
standard: knowledge-library-v0.2
categories:
  - id: C010
    title: Shared Engineering
EOF
cat > "$GLOBAL_ROOT/001_library.md" <<'EOF'
# [K001] Shared Engineering

## [K001.001] Shared Theme Fact
Status: VALIDATED
Category: C010
Fact: Shared theme variables should be reused across compatible projects.
Provenance: GLOBAL-BASELINE
Tags: [theme]
EOF

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
  "$ROOT_DIR/agent_harness/public_plugins/context_builder"

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

const pm = ctx.get('projectManager')
const evidence = ctx.get('evidenceStateManager')
const manager = ctx.get('contextManager')
assert(pm && evidence && manager, 'required Context services missing')
const disposeProject = pm.registerProject(manifest, projectRoot)

let snapshot = manager.beginTask({
  projectId: 'synthetic-project',
  taskId: 'TASK-CONTEXT',
  goal: 'Safely update the UI theme.',
  maxChars: 12000,
  recentTailLimit: 3,
})
assert(snapshot.session.taskLedger.phase === 'bootstrap', 'Task must start in bootstrap')
assert(snapshot.session.workingSet.length === 0, 'Bootstrap must not preload deep content')

let frame = manager.buildFrame('synthetic-project', 'TASK-CONTEXT')
assert(frame.pack.text.includes('Project Compass'), 'Bootstrap Compass missing')
assert(frame.pack.text.includes('Task Ledger'), 'Bootstrap Task Ledger missing')
assert(frame.pack.text.includes('ARCH A010 Interface Architecture'), 'Compass route map missing')
assert(!frame.pack.text.includes('Shared theme variables should be reused'), 'Bootstrap loaded Global Knowledge body too early')

snapshot = manager.updateTaskLedger('synthetic-project', 'TASK-CONTEXT', {
  phase: 'analysis',
  scopeRefs: ['A010.010'],
  constraintRefs: ['R010.010', 'G010.010'],
  confirmed: [{ text: 'Theme runtime scope is A010.010.', refs: ['A010.010'] }],
  assumptions: [{ text: 'The visual issue may originate in the theme entry.', refs: [] }],
  openIssues: [{ text: 'Need to verify the shared theme constraint.', refs: ['knowledge://global/K001.001'] }],
  plan: ['Inspect current theme runtime', 'Apply minimal change', 'Run UI gate'],
})
assert(snapshot.session.taskLedger.confirmed.length === 1, 'Confirmed ledger missing')
assert(snapshot.session.taskLedger.assumptions.length === 1, 'Assumption ledger missing')

manager.addHandles('synthetic-project', 'TASK-CONTEXT', [
  { kind: 'knowledge', reference: 'knowledge://global/K001.001', title: 'Shared Theme Fact' },
  { kind: 'file', reference: 'file://source/ui/theme/index.ts', title: 'Theme Entry' },
])
manager.attach('synthetic-project', 'TASK-CONTEXT', [
  { kind: 'architecture', id: 'A010.010', priority: 'high' },
  { kind: 'rule', id: 'R010.010', priority: 'required' },
  { kind: 'knowledge', id: 'knowledge://global/K001.001', priority: 'normal' },
  { kind: 'knowledge', id: 'K001.001', priority: 'normal' },
  { kind: 'gate', id: 'G010.010', priority: 'required' },
])

frame = manager.buildFrame('synthetic-project', 'TASK-CONTEXT')
assert(frame.pack.text.includes('Shared theme variables should be reused'), 'Global Knowledge did not enter Working Set')
assert(frame.pack.text.includes('source/ui/theme/index.ts'), 'Project Knowledge did not enter Working Set')
assert(frame.pack.text.includes('必须复用统一主题变量'), 'MUST Rule missing')
assert(frame.pack.text.includes('UI Build'), 'Gate missing')

const ev = evidence.recordEvidence({
  projectId: 'synthetic-project',
  taskId: 'TASK-CONTEXT',
  kind: 'test',
  result: 'FAIL',
  summary: 'UI build failed after first edit.',
  source: 'test.execute',
})
manager.updateProgressLedger('synthetic-project', 'TASK-CONTEXT', {
  lastAction: 'Edited theme entry.',
  lastResult: 'UI build failed.',
  touchedRefs: ['file://source/ui/theme/index.ts'],
  currentProblem: 'Build failure remains unresolved.',
  blockers: ['Need build error details.'],
  next: ['Inspect build output.'],
  evidenceRefs: [ev.evidenceId],
})
manager.recordRecent('synthetic-project', 'TASK-CONTEXT', { kind: 'ACTION', summary: 'Opened theme entry.' })
manager.recordRecent('synthetic-project', 'TASK-CONTEXT', { kind: 'ACTION', summary: 'Edited theme entry.' })
manager.recordRecent('synthetic-project', 'TASK-CONTEXT', { kind: 'OBSERVATION', summary: 'Build failed.', evidenceRefs: [ev.evidenceId] })
manager.recordRecent('synthetic-project', 'TASK-CONTEXT', { kind: 'ACTION', summary: 'Inspected build output.' })

snapshot = manager.getTask('synthetic-project', 'TASK-CONTEXT')
assert(snapshot.session.recentTail.length === 3, 'Recent Tail ring limit failed')
assert(!snapshot.session.recentTail.some(item => item.summary === 'Opened theme entry.'), 'Old Recent Tail event was not removed')
assert(!JSON.stringify(snapshot.session).includes('Shared theme variables should be reused'), 'Expanded Knowledge body leaked into persistent Context State')

const handoff = manager.createHandoff('synthetic-project', 'TASK-CONTEXT')
assert(handoff.progressLedger.lastResult === 'UI build failed.', 'Handoff lost Progress Ledger')
assert(handoff.handles.some(item => item.reference === 'knowledge://global/K001.001'), 'Handoff lost Handles')

manager.pause('synthetic-project', 'TASK-CONTEXT')
frame = manager.resume('synthetic-project', 'TASK-CONTEXT')
assert(frame.sessionStatus === 'ACTIVE', 'Resume did not reactivate task')

snapshot = manager.rebuild({
  projectId: 'synthetic-project',
  taskId: 'TASK-CONTEXT',
  phase: 'validation',
  workingSet: [
    { kind: 'rule', id: 'R010.010', priority: 'required' },
    { kind: 'gate', id: 'G010.010', priority: 'required' },
  ],
})
assert(snapshot.session.generation === 2, 'Rebuild generation did not advance')
assert(snapshot.session.recentTail.length === 0, 'Rebuild did not clear Recent Tail')
frame = manager.buildFrame('synthetic-project', 'TASK-CONTEXT')
assert(!frame.pack.text.includes('Shared theme variables should be reused'), 'Detached Global Knowledge body survived rebuild')
assert(frame.pack.text.includes('必须复用统一主题变量'), 'Required Rule was lost after rebuild')

snapshot = manager.complete('synthetic-project', 'TASK-CONTEXT')
assert(snapshot.session.status === 'COMPLETED', 'Complete status missing')
assert(snapshot.session.taskLedger.phase === 'complete', 'Complete phase missing')

disposeProject()
for (let index = fibers.length - 1; index >= 1; index -= 1) {
  await fibers[index].dispose(); await tick()
}
await fibers[0].dispose(); await tick()
console.log('CONTEXT_MANAGEMENT_V0_2=PASS')
EOF

AGENT_HARNESS_GLOBAL_KNOWLEDGE_ROOT="$GLOBAL_ROOT" \
SYNTHETIC_PROJECT_ROOT="$PROJECT_ROOT" \
node "$SMOKE_DIR/smoke.mjs"

printf '%s\n' \
  'PHASE3_CONTEXT_MANAGEMENT_V0_2_INTEGRATION=PASS' \
  "PROJECT_ROOT=$PROJECT_ROOT" \
  "GLOBAL_ROOT=$GLOBAL_ROOT"
