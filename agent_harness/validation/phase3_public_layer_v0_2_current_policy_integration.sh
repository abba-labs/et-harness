#!/usr/bin/env bash
set -euo pipefail

CORDIS_VERSION="${CORDIS_VERSION:-4.0.1}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${PUBLIC_LAYER_V0_2_WORK_DIR:-$(mktemp -d)}"
SMOKE_DIR="$WORK_DIR/cordis-smoke"
GLOBAL_ROOT="$WORK_DIR/global-knowledge"
PROJECT_ROOT="$WORK_DIR/project"
RUNTIME_ROOT="$WORK_DIR/runtime"

source "$ROOT_DIR/agent_harness/validation/lib/common_runtime.sh"
trap 'rm -rf "$WORK_DIR"' EXIT
mkdir -p \
  "$SMOKE_DIR" \
  "$GLOBAL_ROOT" \
  "$PROJECT_ROOT/architecture" \
  "$PROJECT_ROOT/rules" \
  "$PROJECT_ROOT/knowledge" \
  "$PROJECT_ROOT/gates" \
  "$RUNTIME_ROOT"
printf 'synthetic\n' > "$PROJECT_ROOT/project.marker"
export AGENT_HARNESS_STATE_ROOT="$RUNTIME_ROOT"

echo "[1/5] Build public layer packages"
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
  public_plugins/experience_memory_manager; do
  npm_install_if_needed "$ROOT_DIR/agent_harness/$dir" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
  (cd "$ROOT_DIR/agent_harness/$dir" && npm test && npm run build)
done

echo "[2/5] Create synthetic Global + Project resources"
cat > "$GLOBAL_ROOT/TAXONOMY.yaml" <<'EOF'
standard: knowledge-library-v0.2
categories:
  - id: C010
    title: Shared Engineering Knowledge
EOF
cat > "$GLOBAL_ROOT/001_library.md" <<'EOF'
# [K001] Shared Engineering Knowledge

## [K001.001] Shared Theme Principle
Status: VALIDATED
Category: C010
Fact: Shared theme variables should be reused instead of duplicated.
Scope: ui-theme
Provenance: GLOBAL-BASELINE
EOF

cat > "$PROJECT_ROOT/architecture/00_INDEX.md" <<'EOF'
---
interface: project-resource-index-v0.1
resource: architecture
standard: architecture-v0.1
files:
  - id: A010
    file: 010_ui.md
    title: UI Architecture
    summary: Theme runtime architecture
    aliases: [ui, theme, runtime]
---
EOF
cat > "$PROJECT_ROOT/architecture/010_ui.md" <<'EOF'
# [A010] UI Architecture
Role: UI layer
Resources: source/ui/

## [A010.010] Theme Runtime
Role: Owns runtime theme variables and refresh flow
Boundary: Does not define mandatory validation policy
Resources: source/ui/theme/
Relations: R010.010, G010.010
EOF

cat > "$PROJECT_ROOT/rules/00_INDEX.md" <<'EOF'
---
interface: project-resource-index-v0.1
resource: rules
standard: rule-v0.1
files:
  - id: R010
    file: 010_ui.md
    title: UI Rules
    summary: Theme change constraints
    aliases: [ui, theme, rule]
---
EOF
cat > "$PROJECT_ROOT/rules/010_ui.md" <<'EOF'
# [R010] UI Rules

## [R010.010] Reuse Theme Variables
Level: MUST
When: 修改 UI 主题变量或主题入口
Rule: 必须复用统一主题变量。
Refs: [A010.010, G010.010]
EOF

cat > "$PROJECT_ROOT/gates/00_INDEX.md" <<'EOF'
---
interface: project-resource-index-v0.1
resource: gates
standard: gate-v0.1
files:
  - id: G010
    file: 010_ui.yaml
    title: UI Validation
    summary: UI build and test gate
    aliases: [ui, theme, build, test]
---
EOF
cat > "$PROJECT_ROOT/gates/010_ui.yaml" <<'EOF'
standard: gate-v0.1
file_id: G010
title: UI Validation
nodes:
  - id: G010.010
    title: UI Build And Test
    gate:
      level: MUST
      when: 修改 UI 主题变量或主题入口
      steps:
        - id: build
          tool: build.execute
        - id: test
          tool: test.execute
      pass:
        mode: all_steps_pass
      refs: [R010.010]
EOF

cat > "$PROJECT_ROOT/knowledge/TAXONOMY.yaml" <<'EOF'
standard: knowledge-library-v0.2
categories:
  - id: C010
    title: Project Engineering Knowledge
EOF

echo "[3/5] Prepare Cordis runtime"
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
  "$ROOT_DIR/agent_harness/public_plugins/experience_memory_manager"

echo "[4/5] Run Public Layer v0.2 end-to-end flow"
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

const tick = () => new Promise(resolve => setTimeout(resolve, 0))
const assert = (condition, message) => { if (!condition) throw new Error(message) }
const projectRoot = process.env.SYNTHETIC_PROJECT_ROOT
assert(projectRoot, 'SYNTHETIC_PROJECT_ROOT missing')

const manifest = {
  contract_version: '0.1',
  project: { id: 'synthetic-project', name: 'Synthetic Project', aliases: ['synthetic'] },
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

const catalog = ctx.get('governanceCatalog')
const pm = ctx.get('projectManager')
const arch = ctx.get('architectureNavigator')
const rules = ctx.get('ruleManager')
const evidence = ctx.get('evidenceStateManager')
const knowledge = ctx.get('knowledgeManager')
const gates = ctx.get('gateManager')
const contextManager = ctx.get('contextManager')
const experience = ctx.get('experienceMemoryManager')
assert(catalog && pm && arch && rules && evidence && knowledge && gates && contextManager && experience, 'public services missing')

for (const capability of [
  'governance.project', 'architecture.navigate', 'rule.navigate', 'knowledge.navigate',
  'knowledge.library', 'gate.navigate', 'context.build', 'context.manage',
  'evidence.record', 'state.update', 'experience.manage', 'memory.context',
]) {
  assert(catalog.listProviders(capability).length > 0, `missing provider: ${capability}`)
}

const disposeProject = pm.registerProject(manifest, projectRoot)
knowledge.refreshProject('synthetic-project')
const projectSource = knowledge.registerProjectSource('synthetic-project', {
  kind: 'SPEC',
  title: 'Theme Runtime Verification Specification',
  location: 'docs/theme-runtime-verification.pdf',
  revision: '1.0',
})

const taskId = 'TASK-PUBLIC-V02'
let session = contextManager.beginTask({
  projectId: 'synthetic-project',
  taskId,
  goal: 'Update UI theme safely.',
  maxChars: 12000,
  recentTailLimit: 3,
})
assert(session.session.taskLedger.phase === 'bootstrap', 'Context must start in bootstrap')
assert(session.session.workingSet.length === 0, 'Bootstrap must not preload deep content')
let frame = contextManager.buildFrame('synthetic-project', taskId)
assert(frame.pack.text.includes('Project Compass'), 'Bootstrap Compass missing')
assert(!frame.pack.text.includes('必须复用统一主题变量'), 'Bootstrap loaded Rule body before Agent selection')

const archHit = arch.searchArchitecture({ projectId: 'synthetic-project', query: 'ui theme runtime' })
  .find(item => item.id === 'A010.010')
const ruleHit = rules.searchRules({ projectId: 'synthetic-project', query: 'ui theme variable' })
  .find(item => item.id === 'R010.010')
const gateHit = gates.searchGates({ projectId: 'synthetic-project', query: 'ui theme build test' })
  .find(item => item.id === 'G010.010')
const globalKnowledgeHit = knowledge.searchGlobalKnowledge({ query: 'shared theme variables' })
  .find(item => item.knowledgeUri === 'knowledge://global/K001.001')
assert(archHit && ruleHit && gateHit && globalKnowledgeHit, 'progressive discovery failed')

contextManager.updateTaskLedger('synthetic-project', taskId, {
  phase: 'analysis',
  scopeRefs: [archHit.id],
  constraintRefs: [ruleHit.id, gateHit.id],
  confirmed: [{ text: 'Theme runtime scope is A010.010.', refs: [archHit.id] }],
  assumptions: [{ text: 'Theme entry may require a small runtime refresh change.', refs: [] }],
  openIssues: [{ text: 'Need to verify current theme behavior.', refs: [gateHit.id] }],
  plan: ['Inspect selected resources', 'Apply minimal change', 'Run required gate'],
})
contextManager.addHandles('synthetic-project', taskId, [
  { kind: 'file', reference: 'file://source/ui/theme/index.ts', title: 'Theme Entry' },
  { kind: 'knowledge', reference: globalKnowledgeHit.knowledgeUri, title: 'Shared Theme Principle' },
])
contextManager.attach('synthetic-project', taskId, [
  { kind: 'architecture', id: archHit.id, priority: 'high' },
  { kind: 'rule', id: ruleHit.id, priority: 'required' },
  { kind: 'knowledge', id: globalKnowledgeHit.knowledgeUri, priority: 'normal' },
  { kind: 'gate', id: gateHit.id, priority: 'required' },
])
frame = contextManager.buildFrame('synthetic-project', taskId)
assert(frame.pack.text.includes('Theme Runtime'), 'Architecture body missing')
assert(frame.pack.text.includes('必须复用统一主题变量'), 'MUST Rule missing')
assert(frame.pack.text.includes('Shared theme variables should be reused'), 'Global Knowledge missing')
assert(frame.pack.text.includes('UI Build And Test'), 'MUST Gate missing')

const beforeInvalid = contextManager.getTask('synthetic-project', taskId)
let invalidBlocked = false
try {
  contextManager.updateTaskLedger('synthetic-project', taskId, {
    confirmed: [{ text: 'This is probably correct.', refs: [] }],
  })
} catch { invalidBlocked = true }
assert(invalidBlocked, 'Invalid Confirmed entry must be rejected')
assert(contextManager.getTask('synthetic-project', taskId).stateVersion === beforeInvalid.stateVersion, 'Rejected Context write changed State')

const failEvidence = evidence.recordEvidence({
  projectId: 'synthetic-project', taskId, kind: 'test', result: 'FAIL',
  summary: 'First UI build failed.', source: 'test.execute', gateId: gateHit.id,
})
contextManager.updateProgressLedger('synthetic-project', taskId, {
  lastAction: 'Applied minimal theme change.',
  lastResult: 'First UI build failed.',
  touchedRefs: ['file://source/ui/theme/index.ts'],
  currentProblem: 'Build failure remains.',
  blockers: ['Need build output details.'],
  next: ['Inspect build output.'],
  evidenceRefs: [failEvidence.evidenceId],
})
const generationBefore = contextManager.getTask('synthetic-project', taskId).session.generation
contextManager.rebuild({
  projectId: 'synthetic-project', taskId, phase: 'implementation',
  workingSet: [
    { kind: 'rule', id: ruleHit.id, priority: 'required' },
    { kind: 'gate', id: gateHit.id, priority: 'required' },
  ],
  clearRecentTail: true,
  evidenceRefs: [failEvidence.evidenceId],
})
assert(contextManager.getTask('synthetic-project', taskId).session.generation === generationBefore + 1, 'Context rebuild generation mismatch')

assert(gates.checkGateSetEvidence('synthetic-project', taskId, [gateHit.id]).canComplete === false, 'MUST Gate should block before PASS')
const passEvidence = evidence.recordEvidence({
  projectId: 'synthetic-project', taskId, kind: 'gate', result: 'PASS',
  summary: 'UI build and tests passed after correction.', source: 'agent-tool-execution', gateId: gateHit.id,
})
assert(gates.checkGateSetEvidence('synthetic-project', taskId, [gateHit.id]).canComplete === true, 'MUST Gate should pass after PASS Evidence')
evidence.updateState({
  projectId: 'synthetic-project', scope: `task:${taskId}`, key: 'validation',
  value: { result: 'PASS', gateId: gateHit.id }, reason: 'Required gate has PASS evidence.',
  evidenceRefs: [passEvidence.evidenceId], expectedVersion: 0,
})

const exp = experience.recordCandidate({
  projectId: 'synthetic-project', taskId,
  title: 'Theme Runtime Verification',
  fact: 'Theme changes require a runtime verification after the build succeeds.',
  scope: 'ui-theme-runtime',
  evidenceRefs: [passEvidence.evidenceId],
  refs: [archHit.id, ruleHit.id, gateHit.id],
})
const submitted = experience.submitToKnowledge('synthetic-project', {
  candidateId: exp.candidateId, targetScope: 'project', categoryId: 'C010',
})
assert(submitted.evaluation.decision === 'INSUFFICIENT', 'Ordinary gate Evidence must not validate Knowledge')
assert(submitted.verificationRecords[0].validationClass === 'REFERENCE', 'Ordinary gate Evidence must remain REFERENCE')
assert(experience.getCandidate('synthetic-project', exp.candidateId)?.status === 'KNOWLEDGE_CANDIDATE', 'Experience linked state missing')
knowledge.recordVerification({
  knowledgeUri: submitted.knowledgeUri,
  basisRef: projectSource.sourceUri,
  relation: 'SUPPORT',
})
assert(experience.evaluateKnowledgeCandidate('synthetic-project', exp.candidateId).decision === 'READY', 'Trusted Project Source should make Knowledge READY')
const promoted = experience.promoteKnowledgeCandidate('synthetic-project', exp.candidateId)
assert(promoted.status === 'PROMOTED', 'Experience promotion failed')
assert(knowledge.resolveKnowledgeReference(submitted.knowledgeUri)?.result.node.status === 'VALIDATED', 'Knowledge did not become VALIDATED')

contextManager.updateTaskLedger('synthetic-project', taskId, {
  phase: 'handoff', openIssues: [], plan: ['Hand off validated result.'],
})
contextManager.updateProgressLedger('synthetic-project', taskId, {
  lastAction: 'Validated theme change.', lastResult: 'Required gate passed.',
  currentProblem: '', blockers: [], next: ['Hand off validated result.'],
  evidenceRefs: [passEvidence.evidenceId],
})
contextManager.rebuild({
  projectId: 'synthetic-project', taskId, phase: 'handoff',
  workingSet: [
    { kind: 'knowledge', id: submitted.knowledgeUri, priority: 'high' },
    { kind: 'rule', id: ruleHit.id, priority: 'required' },
  ],
  clearRecentTail: true,
  evidenceRefs: [passEvidence.evidenceId],
})
frame = contextManager.buildFrame('synthetic-project', taskId)
assert(frame.pack.text.includes('Theme changes require a runtime verification after the build succeeds.'), 'Rebuilt Context did not resolve VALIDATED Knowledge')
const handoff = contextManager.createHandoff('synthetic-project', taskId)
assert(handoff.workingSet.some(item => item.id === submitted.knowledgeUri), 'Handoff missing Knowledge URI')
contextManager.pause('synthetic-project', taskId)
assert(contextManager.resume('synthetic-project', taskId).pack.text.includes('Required gate passed.'), 'Resume lost Progress Ledger')
assert(contextManager.complete('synthetic-project', taskId).session.status === 'COMPLETED', 'Context task did not complete')

const bypassEvidence = evidence.recordEvidence({
  projectId: 'synthetic-project', taskId: 'TASK-BYPASS', kind: 'test', result: 'PASS',
  summary: 'Bypass guard evidence.', source: 'test.execute',
})
const bypassExp = experience.recordCandidate({
  projectId: 'synthetic-project', taskId: 'TASK-BYPASS', title: 'Bypass Guard',
  fact: 'Direct validated knowledge writes must remain blocked.', evidenceRefs: [bypassEvidence.evidenceId],
})
let bypassBlocked = false
try {
  experience.promoteToKnowledge('synthetic-project', {
    candidateId: bypassExp.candidateId, fileId: 'K001', parentNodeId: 'K001',
    nodeId: 'K001.999', title: 'Bypass Guard',
  })
} catch (error) {
  bypassBlocked = String(error).includes('禁止 Experience Manager 直接写入 VALIDATED Knowledge')
}
assert(bypassBlocked, 'Legacy direct VALIDATED bypass is open')

disposeProject()
knowledge.removeProject('synthetic-project')
for (let index = fibers.length - 1; index >= 1; index -= 1) {
  await fibers[index].dispose(); await tick()
}
await fibers[0].dispose(); await tick()
assert(ctx.get('contextManager') === undefined, 'Context Manager lifecycle cleanup failed')
assert(ctx.get('experienceMemoryManager') === undefined, 'Experience Manager lifecycle cleanup failed')
console.log('PUBLIC_LAYER_V0_2_CURRENT_POLICY=PASS')
EOF

AGENT_HARNESS_GLOBAL_KNOWLEDGE_ROOT="$GLOBAL_ROOT" \
SYNTHETIC_PROJECT_ROOT="$PROJECT_ROOT" \
node "$SMOKE_DIR/smoke.mjs"

echo "[5/5] Verify durable outputs"
grep -q 'Status: VALIDATED' "$PROJECT_ROOT/knowledge/001_library.md"
grep -q 'knowledgeFingerprint' "$PROJECT_ROOT/knowledge/VERIFICATIONS.jsonl"

echo 'PHASE3_PUBLIC_LAYER_V0_2_CURRENT_POLICY_INTEGRATION=PASS'
