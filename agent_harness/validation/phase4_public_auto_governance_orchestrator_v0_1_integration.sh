#!/usr/bin/env bash
set -euo pipefail

CORDIS_VERSION="${CORDIS_VERSION:-4.0.1}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${AUTO_GOVERNANCE_WORK_DIR:-$(mktemp -d)}"
SMOKE_DIR="$WORK_DIR/cordis-smoke"
PROJECT_ROOT="$WORK_DIR/project"
GLOBAL_ROOT="$WORK_DIR/global-knowledge"
RUNTIME_ROOT="$WORK_DIR/runtime"

source "$ROOT_DIR/agent_harness/validation/lib/common_runtime.sh"
trap 'rm -rf "$WORK_DIR"' EXIT
mkdir -p "$SMOKE_DIR" "$PROJECT_ROOT/architecture" "$PROJECT_ROOT/rules" "$PROJECT_ROOT/knowledge" "$PROJECT_ROOT/gates" "$GLOBAL_ROOT" "$RUNTIME_ROOT"
printf 'synthetic\n' > "$PROJECT_ROOT/project.marker"
export AGENT_HARNESS_STATE_ROOT="$RUNTIME_ROOT"
export AGENT_HARNESS_GLOBAL_KNOWLEDGE_ROOT="$GLOBAL_ROOT"

cat > "$GLOBAL_ROOT/TAXONOMY.yaml" <<'EOF'
standard: knowledge-library-v0.2
categories:
  - id: C010
    title: Shared Engineering
EOF
cat > "$GLOBAL_ROOT/001_library.md" <<'EOF'
# [K001] Shared Engineering

## [K001.001] Shared Review Fact
Status: VALIDATED
Category: C010
Fact: Shared code changes require explicit review before build.
Provenance: GLOBAL-SYNTHETIC
Tags: [review]
EOF

cat > "$PROJECT_ROOT/architecture/00_INDEX.md" <<'EOF'
---
interface: project-resource-index-v0.1
resource: architecture
standard: architecture-v0.1
files:
  - id: A010
    file: 010_application.md
    title: Demo Application Architecture
    summary: Demo application layer and contract
    aliases: [demo, application, command]
---
EOF
cat > "$PROJECT_ROOT/architecture/010_application.md" <<'EOF'
# [A010] Demo Application Architecture
Role: demo application architecture

## [A010.010] Demo Command Layer
Role: owns demo command behavior
Boundary: changes stay in the application layer
Resources: source/application/demo/
Relations: R010.010
EOF

cat > "$PROJECT_ROOT/rules/00_INDEX.md" <<'EOF'
---
interface: project-resource-index-v0.1
resource: rules
standard: rule-v0.1
files:
  - id: R010
    file: 010_application.md
    title: Demo Application Rules
    summary: Demo application constraints
    aliases: [demo, application, command, review]
---
EOF
cat > "$PROJECT_ROOT/rules/010_application.md" <<'EOF'
# [R010] Demo Application Rules

## [R010.010] Demo Change Must Be Reviewed
Level: MUST
When: 修改 demo application code
Rule: Demo application code changes MUST complete Code Gate review before build or test.
Refs: [A010.010, G010.010.010]
EOF

cat > "$PROJECT_ROOT/knowledge/TAXONOMY.yaml" <<'EOF'
standard: knowledge-library-v0.2
categories:
  - id: C010
    title: Demo Application
EOF
cat > "$PROJECT_ROOT/knowledge/001_library.md" <<'EOF'
# [K001] Demo Application Knowledge

## [K001.001] Demo Source Location
Status: VALIDATED
Category: C010
Fact: Demo application implementation lives under source/application/demo/.
Provenance: PROJECT-SYNTHETIC
Tags: [demo, application]
EOF

cat > "$PROJECT_ROOT/gates/00_INDEX.md" <<'EOF'
---
interface: project-resource-index-v0.1
resource: gates
standard: gate-v0.1
files:
  - id: G010
    file: 010_code_review.yaml
    title: Demo Code Review
    summary: Review changed demo application code before build
    aliases: [demo, code, review, change, application, logic]
---
EOF
cat > "$PROJECT_ROOT/gates/010_code_review.yaml" <<'EOF'
standard: gate-v0.1
file_id: G010
title: Demo Code Review
nodes:
  - id: G010.010
    title: Demo Change Review
    children:
      - id: G010.010.010
        title: Demo Code Review Must Pass
        gate:
          level: MUST
          when: demo application code changes
          steps:
            - id: review
              tool: code.review
              args:
                focus: demo application logic and contract
          pass:
            mode: all_steps_pass
          refs: [A010.010, R010.010]
EOF

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
  public_plugins/auto_governance_orchestrator; do
  npm_install_if_needed "$ROOT_DIR/agent_harness/$dir" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
  (cd "$ROOT_DIR/agent_harness/$dir" && npm run build)
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
  "$ROOT_DIR/agent_harness/public_plugins/auto_governance_orchestrator"

cat > "$SMOKE_DIR/smoke.mjs" <<'EOF'
import { Context, Service } from '@deepseek-ai/cordis'
import GovernanceCatalogService from '@agent-harness/governance-core'
import * as projectManagerPlugin from '@agent-harness/project-manager'
import * as architecturePlugin from '@agent-harness/architecture-navigator'
import * as rulePlugin from '@agent-harness/rule-manager'
import * as evidencePlugin from '@agent-harness/evidence-state-manager'
import * as knowledgePlugin from '@agent-harness/knowledge-manager'
import * as gatePlugin from '@agent-harness/gate-manager'
import * as contextPlugin from '@agent-harness/context-builder'
import * as autoPlugin from '@agent-harness/auto-governance-orchestrator'

const tick = () => new Promise(resolve => setTimeout(resolve, 0))
const assert = (condition, message) => { if (!condition) throw new Error(message) }
const projectRoot = process.env.SYNTHETIC_PROJECT_ROOT
assert(projectRoot, 'SYNTHETIC_PROJECT_ROOT missing')

const manifest = {
  contract_version: '0.1',
  project: {
    id: 'synthetic-project',
    name: 'Synthetic Project',
    type: 'test',
    aliases: ['synthetic', 'demo'],
    description: 'Synthetic project for automatic governance integration.',
  },
  root: { markers: ['project.marker'] },
  resources: {
    architecture: { path: 'architecture/', standard: 'architecture-v0.1' },
    rules: { path: 'rules/', standard: 'rule-v0.1' },
    knowledge: { path: 'knowledge/', standard: 'knowledge-v0.1' },
    gates: { path: 'gates/', standard: 'gate-v0.1' },
  },
  adapters: {
    code_review: { provider: 'synthetic.code-review', capability: 'code.review' },
  },
}

class FakeReviewService extends Service {
  static inject = ['evidenceStateManager']

  constructor(ctx) {
    super(ctx, 'fakeReview')
    this.runtimeContext = ctx
    this.packets = new Map()
  }

  prepareReview(input) {
    const packetId = `FAKE-${input.taskId}-${input.gateId}-${input.capability}`
    const packet = {
      packetId,
      projectId: input.projectId,
      taskId: input.taskId,
      gateId: input.gateId,
      capability: input.capability,
      focus: input.focus ?? 'demo review',
      taskIntent: input.taskIntent,
      change: {
        source: 'provided',
        files: ['source/application/demo/demo.cpp'],
        patch: '+ demo change',
        truncated: false,
        fingerprint: 'synthetic-fingerprint',
      },
      scopeHints: { chips: [], routes: [], layers: ['APPLICATION'], sharedLayerChange: true, unknownPaths: [] },
      architectureCandidates: [{ id: 'A010.010', title: 'Demo Command Layer', location: '010_application.md#A010.010' }],
      ruleCandidates: [{ id: 'R010.010', title: 'Demo Change Must Be Reviewed', location: '010_application.md#R010.010' }],
      knowledgeCandidates: [{ id: 'K001.001', title: 'Demo Source Location', location: '001_library.md#K001.001' }],
      gateRefs: ['A010.010', 'R010.010'],
      reviewGuidance: ['Review the synthetic demo change.'],
      validationPlanHints: [{ kind: 'build', scope: 'demo', reason: 'after gate pass' }],
      decisionPolicy: 'explicit agent decision required',
    }
    this.packets.set(packetId, packet)
    return packet
  }

  recordReviewDecision(input) {
    const packet = this.packets.get(input.packetId)
    if (!packet) throw new Error(`fake packet missing: ${input.packetId}`)
    const evidence = this.runtimeContext.evidenceStateManager.recordEvidence({
      projectId: packet.projectId,
      taskId: packet.taskId,
      kind: 'gate',
      result: input.result === 'PASS' ? 'PASS' : 'FAIL',
      summary: input.summary,
      source: 'synthetic-review-provider',
      gateId: packet.gateId,
      metadata: { reviewer: input.reviewer, reviewerId: input.reviewerId },
    })
    return {
      packetId: packet.packetId,
      gateId: packet.gateId,
      taskId: packet.taskId,
      result: input.result,
      evidenceId: evidence.evidenceId,
    }
  }
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
fibers.push(ctx.plugin(autoPlugin)); await tick()

const pm = ctx.get('projectManager')
const manager = ctx.get('contextManager')
const auto = ctx.get('autoGovernanceOrchestrator')
assert(pm && manager && auto, 'required services missing')
const disposeProject = pm.registerProject(manifest, projectRoot)

const reviewManifest = {
  manifestVersion: '0.1',
  pluginId: 'project.synthetic.review',
  pluginVersion: '0.1.0',
  displayName: 'Synthetic Review Provider',
  scope: { kind: 'project', id: 'synthetic-project' },
  trust: 'reviewed',
  permissions: ['project.read', 'evidence.write'],
  provides: [{
    capability: 'code.review',
    contract: {
      id: 'code.review',
      version: '0.1',
      summary: 'Synthetic semantic code review',
      criticality: 'important',
    },
  }],
}
const admission = ctx.governanceCatalog.admit(reviewManifest)
assert(admission.status === 'admitted', `review plugin admission failed: ${admission.reasons?.join('; ')}`)
const reviewFiber = ctx.plugin(FakeReviewService); await tick()
const disposeProvider = ctx.governanceCatalog.registerProvider({
  providerId: 'synthetic.code-review',
  pluginId: reviewManifest.pluginId,
  capability: 'code.review',
  priority: 1000,
  metadata: {
    projectId: 'synthetic-project',
    service: 'fakeReview',
    prepareMethod: 'prepareReview',
    decisionMethod: 'recordReviewDecision',
    semanticReviewer: 'agent',
    autoPass: false,
  },
})

const agent = {
  id: 'SYNTHETIC-AGENT',
  session: { header: { cwd: projectRoot } },
}
const human = {
  id: 'MSG-1',
  role: 'user',
  content: [{ type: 'text', text: 'Update the demo application command logic safely.' }],
  source: { kind: 'user' },
}
const signal = new AbortController().signal
const firstStep = await ctx.waterfall(
  'agent/pre-step',
  { agent, messages: [human], turn: 1, step: 1, signal },
  async () => ({ kind: 'enter', messages: [human] }),
)
assert(firstStep.kind === 'enter', 'auto bootstrap rejected first step')
const injected = firstStep.messages.find(message => message?.source?.plugin === autoPlugin.name)
assert(injected, 'Auto Governance context was not injected')
assert(injected.content?.[0]?.text?.includes('AUTO GOVERNANCE CONTEXT'), 'injected governance marker missing')

let status = auto.getTaskStatus(agent.id)
assert(status, 'Auto Governance task was not created')
assert(status.projectId === 'synthetic-project', 'project was not resolved automatically')
assert(status.route.architectureIds.includes('A010.010'), 'Architecture was not auto-routed')
assert(status.route.ruleIds.includes('R010.010'), 'Rule was not auto-routed')
assert(status.route.knowledgeIds.includes('K001.001'), 'Knowledge was not auto-routed')
const session = manager.getTask(status.projectId, status.taskId).session
assert(session.workingSet.some(item => item.kind === 'architecture' && item.id === 'A010.010'), 'Architecture not attached to Context')
assert(session.workingSet.some(item => item.kind === 'rule' && item.id === 'R010.010'), 'Rule not attached to Context')

ctx.emit('tools/result', {
  name: 'apply_patch',
  arguments: { patch: '*** Update File: source/application/demo/demo.cpp' },
  agent,
}, { isError: false, content: [{ type: 'text', text: 'Done!' }] })
await tick()

status = auto.getTaskStatus(agent.id)
assert(status?.codeChangeSeen === true, 'code change was not detected automatically')
assert(status.applicableGateIds.includes('G010.010.010'), 'executable Gate was not selected automatically')
assert(status.pendingReviews.length === 1, 'review packet was not prepared automatically')
assert(status.pendingReviews[0].decision === 'PENDING', 'review packet must start PENDING')

const buildExec = {
  name: 'bash',
  arguments: { command: 'cmake --build build' },
  agent,
}
const blocked = await ctx.waterfall(
  'tools/pre-execute',
  buildExec,
  async () => ({ kind: 'allow' }),
)
assert(blocked.kind === 'deny', 'build/test was not blocked before Gate PASS')

const packetId = status.pendingReviews[0].packetId
const decision = auto.recordReviewDecision({
  packetId,
  result: 'PASS',
  summary: 'Synthetic Agent reviewed the current diff and found no blocking issue.',
  reviewerId: agent.id,
})
assert(decision.allCurrentReviewsPass, 'current review epoch did not become PASS')
assert(decision.gateSetSatisfied, 'Gate PASS Evidence was not recognized')

const allowed = await ctx.waterfall(
  'tools/pre-execute',
  buildExec,
  async () => ({ kind: 'allow' }),
)
assert(allowed.kind === 'allow', 'build/test was not released after Gate PASS')

const completed = auto.completeTaskForAgent(agent)
assert(completed.status === 'COMPLETED', `task completion blocked unexpectedly: ${completed.reason ?? ''}`)
const completedSession = manager.getTask(status.projectId, status.taskId).session
assert(completedSession.status === 'COMPLETED', 'Context did not complete automatically through governance completion')

console.log('AUTO_GOVERNANCE_TASK_START=PASS')
console.log('AUTO_GOVERNANCE_ROUTE_CONTEXT=PASS')
console.log('AUTO_GOVERNANCE_CODE_CHANGE_REVIEW=PASS')
console.log('AUTO_GOVERNANCE_PRE_BUILD_GUARD=PASS')
console.log('AUTO_GOVERNANCE_AGENT_DECISION=PASS')
console.log('AUTO_GOVERNANCE_COMPLETION=PASS')
console.log('PUBLIC_AUTO_GOVERNANCE_ORCHESTRATOR_V0_1=PASS')

disposeProvider()
await reviewFiber.dispose(); await tick()
ctx.governanceCatalog.removePlugin(reviewManifest.pluginId)
disposeProject()
for (let index = fibers.length - 1; index >= 0; index -= 1) {
  await fibers[index].dispose(); await tick()
}
EOF

SYNTHETIC_PROJECT_ROOT="$PROJECT_ROOT" node "$SMOKE_DIR/smoke.mjs"
