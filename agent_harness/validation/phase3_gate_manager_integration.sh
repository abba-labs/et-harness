#!/usr/bin/env bash
set -euo pipefail

CORDIS_VERSION="${CORDIS_VERSION:-4.0.1}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${PHASE3_GATE_VALIDATION_WORK_DIR:-$(mktemp -d)}"
SMOKE_DIR="$WORK_DIR/cordis-smoke"
SYNTHETIC_ROOT="$WORK_DIR/project-root"
source "$ROOT_DIR/agent_harness/validation/lib/common_runtime.sh"
trap 'rm -rf "$WORK_DIR"' EXIT
mkdir -p "$SMOKE_DIR" "$SYNTHETIC_ROOT"
export npm_config_registry="$NPM_REGISTRY"
export AGENT_HARNESS_STATE_ROOT="$WORK_DIR/runtime"

for dir in project_contract governance_core public_plugins/project_manager public_plugins/evidence_state_manager public_plugins/gate_manager; do
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
  "$ROOT_DIR/agent_harness/public_plugins/evidence_state_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/gate_manager"

cat > smoke.mjs <<'EOF'
import { mkdirSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { Context } from '@deepseek-ai/cordis'
import GovernanceCatalogService from '@agent-harness/governance-core'
import * as projectManagerPlugin from '@agent-harness/project-manager'
import * as evidenceStatePlugin from '@agent-harness/evidence-state-manager'
import * as gateManagerPlugin from '@agent-harness/gate-manager'

const tick = () => new Promise(resolve => setTimeout(resolve, 0))
const assert = (c, m) => { if (!c) throw new Error(m) }
const root = process.env.SYNTHETIC_PROJECT_ROOT
const gates = join(root, 'gates')
mkdirSync(gates, { recursive: true })
writeFileSync(join(gates, '00_INDEX.md'), `---
interface: project-resource-index-v0.1
resource: gates
standard: gate-v0.1
files:
  - id: G010
    file: 010_validation.yaml
    title: Validation Gates
    summary: build and validation gates
    aliases: [build, test, validation, ui]
---
`)
writeFileSync(join(gates, '010_validation.yaml'), `standard: gate-v0.1
file_id: G010
title: Validation Gates
nodes:
  - id: G010.010
    title: UI Validation
    children:
      - id: G010.010.010
        title: UI Build
        gate:
          level: MUST
          when: 修改 UI 相关代码
          steps:
            - id: build
              tool: build.execute
            - id: test
              tool: test.execute
          pass:
            mode: all_steps_pass
`)
const manifest = {
  contract_version: '0.1',
  project: { id: 'synthetic-project', name: 'Synthetic Project' },
  root: { markers: ['marker'] },
  resources: {
    architecture: { path: 'architecture/', standard: 'architecture-v0.1' },
    rules: { path: 'rules/', standard: 'rule-v0.1' },
    knowledge: { path: 'knowledge/', standard: 'knowledge-v0.1' },
    gates: { path: 'gates/', standard: 'gate-v0.1' },
  },
  adapters: {},
}

const ctx = new Context()
const core = ctx.plugin(GovernanceCatalogService); await tick()
const pmFiber = ctx.plugin(projectManagerPlugin); await tick()
const evidenceFiber = ctx.plugin(evidenceStatePlugin); await tick()
const gateFiber = ctx.plugin(gateManagerPlugin); await tick()
const pm = ctx.get('projectManager')
const es = ctx.get('evidenceStateManager')
const gm = ctx.get('gateManager')
assert(pm && es && gm, '公共 Service 未完整暴露')
const disposeProject = pm.registerProject(manifest, root)
gm.refreshProject('synthetic-project')

const before = gm.checkGateSetEvidence('synthetic-project', 'TASK-1', ['G010.010.010'])
assert(before.canComplete === false, 'MUST Gate 无 Evidence 时不应允许完成')
const evidence = es.recordEvidence({
  projectId: 'synthetic-project',
  taskId: 'TASK-1',
  kind: 'gate',
  result: 'PASS',
  summary: 'UI build and tests passed',
  source: 'agent-tool-run',
  gateId: 'G010.010.010',
})
const after = gm.checkGateSetEvidence('synthetic-project', 'TASK-1', ['G010.010.010'])
assert(after.canComplete === true, 'MUST Gate PASS Evidence 后应允许完成')
assert(after.gates[0].evidenceRefs.includes(evidence.evidenceId), 'Gate 未关联 PASS Evidence')
console.log('  MUST Gate Evidence guard = PASS')

disposeProject()
await gateFiber.dispose(); await tick()
await evidenceFiber.dispose(); await tick()
await pmFiber.dispose(); await tick()
await core.dispose(); await tick()
console.log('  lifecycle cleanup = PASS')
EOF

SYNTHETIC_PROJECT_ROOT="$SYNTHETIC_ROOT" node smoke.mjs
printf '%s\n' 'PHASE3_GATE_MANAGER_INTEGRATION=PASS' "CORDIS_VERSION=$CORDIS_VERSION"
