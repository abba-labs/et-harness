#!/usr/bin/env bash
set -euo pipefail

CORDIS_VERSION="${CORDIS_VERSION:-4.0.1}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${CONTEXT_LINT_WORK_DIR:-$(mktemp -d)}"
SMOKE_DIR="$WORK_DIR/cordis-smoke"
PROJECT_ROOT="$WORK_DIR/project"
RUNTIME_ROOT="$WORK_DIR/runtime"

source "$ROOT_DIR/agent_harness/validation/lib/common_runtime.sh"
trap 'rm -rf "$WORK_DIR"' EXIT
mkdir -p "$SMOKE_DIR" "$PROJECT_ROOT/architecture" "$PROJECT_ROOT/rules" "$PROJECT_ROOT/knowledge" "$PROJECT_ROOT/gates" "$RUNTIME_ROOT"
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

cat > "$PROJECT_ROOT/architecture/00_INDEX.md" <<'EOF'
---
interface: project-resource-index-v0.1
resource: architecture
standard: architecture-v0.1
files: []
---
EOF
cat > "$PROJECT_ROOT/rules/00_INDEX.md" <<'EOF'
---
interface: project-resource-index-v0.1
resource: rules
standard: rule-v0.1
files: []
---
EOF
cat > "$PROJECT_ROOT/knowledge/00_INDEX.md" <<'EOF'
---
interface: project-resource-index-v0.1
resource: knowledge
standard: knowledge-v0.1
files: []
---
EOF
cat > "$PROJECT_ROOT/gates/00_INDEX.md" <<'EOF'
---
interface: project-resource-index-v0.1
resource: gates
standard: gate-v0.1
files: []
---
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
const root = process.env.SYNTHETIC_PROJECT_ROOT
assert(root, 'SYNTHETIC_PROJECT_ROOT missing')

const manifest = {
  contract_version: '0.1',
  project: { id: 'synthetic-project', name: 'Synthetic Project' },
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
const context = ctx.get('contextManager')
assert(pm && context, 'required services missing')
const disposeProject = pm.registerProject(manifest, root)

context.beginTask({
  projectId: 'synthetic-project',
  taskId: 'TASK-LINT',
  goal: '验证 Context Lint 写入门禁',
})
const initial = context.getTask('synthetic-project', 'TASK-LINT')

let missingRefRejected = false
try {
  context.updateTaskLedger('synthetic-project', 'TASK-LINT', {
    confirmed: [{ text: '这是一个没有来源的确认事实。', refs: [] }],
  })
} catch (error) {
  missingRefRejected = String(error).includes('CONFIRMED_WITHOUT_REF')
}
assert(missingRefRejected, 'Confirmed without Ref must be rejected')
let after = context.getTask('synthetic-project', 'TASK-LINT')
assert(after.stateVersion === initial.stateVersion, 'Rejected Context write changed State version')
assert(after.session.taskLedger.confirmed.length === 0, 'Rejected Confirmed leaked into State')

let uncertainRejected = false
try {
  context.updateTaskLedger('synthetic-project', 'TASK-LINT', {
    confirmed: [{ text: 'timeout 可能来自 ready bit。', refs: ['A010'] }],
  })
} catch (error) {
  uncertainRejected = String(error).includes('CONFIRMED_UNCERTAIN')
}
assert(uncertainRejected, 'Uncertain Confirmed must be rejected')

let multilineRejected = false
try {
  context.updateProgressLedger('synthetic-project', 'TASK-LINT', {
    lastAction: '修改 reset\n继续测试',
  })
} catch (error) {
  multilineRejected = String(error).includes('MULTILINE_TEXT')
}
assert(multilineRejected, 'Multiline Progress must be rejected')

context.updateTaskLedger('synthetic-project', 'TASK-LINT', {
  confirmed: [{ text: '当前分析范围为 A010。', refs: ['A010'] }],
  assumptions: [{ text: 'ready bit 可能未置位。', refs: [] }],
  plan: ['检查 ready bit'],
})
after = context.getTask('synthetic-project', 'TASK-LINT')
assert(after.stateVersion === initial.stateVersion + 1, 'Valid Context write did not update State exactly once')
assert(after.session.taskLedger.confirmed.length === 1, 'Valid Confirmed missing')

const lint = context.lintTask('synthetic-project', 'TASK-LINT')
assert(lint.valid, 'Valid task should pass Context Lint')

context.updateTaskLedger('synthetic-project', 'TASK-LINT', { scopeRefs: ['custom-ref'] })
const warningLint = context.lintTask('synthetic-project', 'TASK-LINT')
assert(warningLint.valid, 'Unknown reference format should not block Agent')
assert(warningLint.warnings.some(item => item.code === 'NON_STANDARD_REFERENCE'), 'Expected reference warning missing')

const frame = context.buildFrame('synthetic-project', 'TASK-LINT')
assert(frame.pack.warnings.some(item => item.includes('NON_STANDARD_REFERENCE')), 'Lint warning not surfaced in Context Frame')

disposeProject()
for (let index = fibers.length - 1; index >= 0; index -= 1) {
  await fibers[index].dispose(); await tick()
}
console.log('CONTEXT_LINT_V0_1=PASS')
EOF

SYNTHETIC_PROJECT_ROOT="$PROJECT_ROOT" node "$SMOKE_DIR/smoke.mjs"

printf '%s\n' 'PHASE3_CONTEXT_LINT_V0_1_INTEGRATION=PASS'
