#!/usr/bin/env bash
set -euo pipefail

CORDIS_VERSION="${CORDIS_VERSION:-4.0.1}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${FRAMEWORK_OBSERVER_V0_1_WORK_DIR:-$(mktemp -d)}"
SMOKE_DIR="$WORK_DIR/cordis-smoke"
PROJECT_ROOT="$WORK_DIR/project"
METRICS_ROOT="$WORK_DIR/metrics"

source "$ROOT_DIR/agent_harness/validation/lib/common_runtime.sh"
trap 'rm -rf "$WORK_DIR"' EXIT
mkdir -p "$SMOKE_DIR" "$PROJECT_ROOT/architecture" "$PROJECT_ROOT/rules" "$PROJECT_ROOT/knowledge" "$PROJECT_ROOT/gates" "$METRICS_ROOT"
printf 'synthetic\n' > "$PROJECT_ROOT/project.marker"
export AGENT_HARNESS_METRICS_ROOT="$METRICS_ROOT"

for dir in \
  project_contract \
  governance_core \
  public_plugins/project_manager \
  public_plugins/architecture_navigator \
  public_plugins/rule_manager \
  public_plugins/framework_efficiency_observer; do
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
    file: 010_ui.md
    title: UI Architecture
    summary: UI theme architecture
    aliases: [ui, theme]
---
EOF
cat > "$PROJECT_ROOT/architecture/010_ui.md" <<'EOF'
# [A010] UI Architecture
Role: UI root
Resources: source/ui/

## [A010.010] Theme
Role: Theme runtime
Resources: source/ui/theme/
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
    summary: UI theme rules
    aliases: [ui, theme]
---
EOF
cat > "$PROJECT_ROOT/rules/010_ui.md" <<'EOF'
# [R010] UI Rules

## [R010.010] Theme Rule
Level: MUST
When: 修改主题
Rule: 必须复用统一主题变量。
Refs: [A010.010]
EOF

for resource in knowledge gates; do
  case "$resource" in
    knowledge) standard='knowledge-v0.1' ;;
    gates) standard='gate-v0.1' ;;
  esac
  cat > "$PROJECT_ROOT/$resource/00_INDEX.md" <<EOF
---
interface: project-resource-index-v0.1
resource: $resource
standard: $standard
files: []
---
EOF
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
  "$ROOT_DIR/agent_harness/public_plugins/framework_efficiency_observer"

cat > "$SMOKE_DIR/smoke.mjs" <<'EOF'
import { Context } from '@deepseek-ai/cordis'
import GovernanceCatalogService, { frameworkMetricsActive } from '@agent-harness/governance-core'
import * as projectManagerPlugin from '@agent-harness/project-manager'
import * as architecturePlugin from '@agent-harness/architecture-navigator'
import * as rulePlugin from '@agent-harness/rule-manager'
import * as observerPlugin from '@agent-harness/framework-efficiency-observer'

const tick = () => new Promise(resolve => setTimeout(resolve, 0))
const assert = (condition, message) => { if (!condition) throw new Error(message) }
const root = process.env.SYNTHETIC_PROJECT_ROOT
assert(root, 'SYNTHETIC_PROJECT_ROOT missing')

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
const governanceFiber = ctx.plugin(GovernanceCatalogService); await tick()
const projectFiber = ctx.plugin(projectManagerPlugin); await tick()
const architectureFiber = ctx.plugin(architecturePlugin); await tick()
const ruleFiber = ctx.plugin(rulePlugin); await tick()
assert(frameworkMetricsActive() === false, 'metrics must be inactive before observer install')
const observerFiber = ctx.plugin(observerPlugin); await tick()

const catalog = ctx.get('governanceCatalog')
const pm = ctx.get('projectManager')
const arch = ctx.get('architectureNavigator')
const rules = ctx.get('ruleManager')
const observer = ctx.get('frameworkEfficiencyObserver')
assert(catalog && pm && arch && rules && observer, 'required services missing')
assert(frameworkMetricsActive() === true, 'observer must activate metrics')
assert(catalog.listProviders('observability.framework').length === 1, 'observer provider missing')

const disposeProject = pm.registerProject(manifest, root)
arch.refreshProject('synthetic-project')
rules.refreshProject('synthetic-project')

// Broken listener while metrics are active: execution must still succeed.
const disposeBroken = ctx.on('framework/metric', () => { throw new Error('BROKEN_OBSERVER') })
const failOpenResult = arch.searchArchitecture({
  projectId: 'synthetic-project',
  query: 'ui theme',
  scope: { taskId: 'TASK-FAIL-OPEN' },
})
assert(failOpenResult.some(item => item.id === 'A010.010'), 'broken observer affected execution plane')
disposeBroken()

const beforeArch = arch.searchArchitecture({
  projectId: 'synthetic-project',
  query: 'ui theme',
  scope: { taskId: 'TASK-OBS' },
})
const beforeRule = rules.searchRules({
  projectId: 'synthetic-project',
  query: 'ui theme',
  scope: { taskId: 'TASK-OBS' },
})
rules.searchRules({
  projectId: 'synthetic-project',
  query: 'definitely-not-found',
  scope: { taskId: 'TASK-OBS' },
})
assert(beforeArch.some(item => item.id === 'A010.010'), 'architecture result missing with observer')
assert(beforeRule.some(item => item.id === 'R010.010'), 'rule result missing with observer')

await observer.flush()
const report = await observer.analyze({ projectId: 'synthetic-project', taskId: 'TASK-OBS' })
assert(report.eventCount >= 3, 'observer did not capture framework metrics')
assert(report.components.some(item => item.component === 'architecture'), 'architecture metrics missing')
assert(report.components.some(item => item.component === 'rule'), 'rule metrics missing')
assert(report.components.find(item => item.component === 'rule')?.missCount === 1, 'rule MISS metric missing')

// Agent/session cost analysis is OFFLINE. Runtime observer must not subscribe to token-level session events.
const receivedBeforeSessionProbe = observer.getRuntimeStats().received
ctx.emit('session/event', { header: { id: 'SESSION-PROBE' } }, {
  type: 'assistant/chunk',
  time: 1020,
  data: { turn: 1, step: 1, chunk: { type: 'usage', usage: { inputTokens: 999 } } },
})
assert(observer.getRuntimeStats().received === receivedBeforeSessionProbe, 'observer must not live-listen to high-frequency session events')

const sessionEvents = [
  { type: 'turn/start', time: 1000, data: { turn: 1 } },
  { type: 'step/start', time: 1010, data: { turn: 1, step: 1 } },
  {
    type: 'assistant/chunk',
    time: 1020,
    data: {
      turn: 1,
      step: 1,
      chunk: { type: 'usage', usage: { inputTokens: 100, outputTokens: 20, cacheReadTokens: 50 } },
    },
  },
  {
    type: 'tool/call',
    time: 1030,
    data: { turn: 1, step: 1, callId: 'CALL-1', name: 'test.execute', arguments: '{}' },
  },
  {
    type: 'tool/result',
    time: 1080,
    data: {
      turn: 1,
      step: 1,
      message: {
        source: { kind: 'tool', callId: 'CALL-1' },
        content: [{ type: 'tool-result', toolCallId: 'CALL-1', content: [], isError: false }],
      },
    },
  },
  { type: 'step/end', time: 1100, data: { turn: 1, step: 1 } },
  { type: 'turn/end', time: 1110, data: { turn: 1, reason: { kind: 'stop' } } },
]
const sessionReport = observer.analyzeSessionEvents('SESSION-OBS', sessionEvents)
assert(sessionReport.components.some(item => item.component === 'runtime'), 'agent runtime metrics missing')
assert(sessionReport.components.some(item => item.component === 'tool'), 'tool metrics missing')
assert(sessionReport.components.find(item => item.component === 'runtime')?.values.inputTokens === 100, 'input token metric missing')
assert(sessionReport.components.find(item => item.component === 'runtime')?.values.outputTokens === 20, 'output token metric missing')
assert(sessionReport.components.find(item => item.component === 'tool')?.observedDurationMs === 50, 'tool duration metric mismatch')
assert(observer.getRuntimeStats().dropped === 0, 'metrics unexpectedly dropped')

// Unload observer. Core framework must remain behaviorally identical and metrics fast-path must disable.
await observerFiber.dispose(); await tick()
assert(ctx.get('frameworkEfficiencyObserver') === undefined, 'observer service did not unload')
assert(catalog.listProviders('observability.framework').length === 0, 'observer provider did not unload')
assert(frameworkMetricsActive() === false, 'metrics fast-path remained active after observer unload')

const afterArch = arch.searchArchitecture({
  projectId: 'synthetic-project',
  query: 'ui theme',
  scope: { taskId: 'TASK-OBS-AFTER' },
})
const afterRule = rules.searchRules({
  projectId: 'synthetic-project',
  query: 'ui theme',
  scope: { taskId: 'TASK-OBS-AFTER' },
})
assert(JSON.stringify(afterArch.map(item => item.id)) === JSON.stringify(beforeArch.map(item => item.id)), 'architecture behavior changed after observer unload')
assert(JSON.stringify(afterRule.map(item => item.id)) === JSON.stringify(beforeRule.map(item => item.id)), 'rule behavior changed after observer unload')

assert(catalog.listProviders('architecture.navigate').length > 0, 'architecture provider affected by observer unload')
assert(catalog.listProviders('rule.navigate').length > 0, 'rule provider affected by observer unload')

disposeProject()
await ruleFiber.dispose(); await tick()
await architectureFiber.dispose(); await tick()
await projectFiber.dispose(); await tick()
await governanceFiber.dispose(); await tick()
console.log('FRAMEWORK_EFFICIENCY_OBSERVER_V0_1=PASS')
EOF

SYNTHETIC_PROJECT_ROOT="$PROJECT_ROOT" node "$SMOKE_DIR/smoke.mjs"

test -s "$METRICS_ROOT/framework-events.jsonl"
grep -q '"component":"architecture"' "$METRICS_ROOT/framework-events.jsonl"
grep -q '"component":"rule"' "$METRICS_ROOT/framework-events.jsonl"

printf '%s\n' \
  'PHASE3_FRAMEWORK_EFFICIENCY_OBSERVER_V0_1_INTEGRATION=PASS' \
  "METRICS_ROOT=$METRICS_ROOT"
