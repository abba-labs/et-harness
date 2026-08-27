#!/usr/bin/env bash
set -euo pipefail

CORDIS_VERSION="${CORDIS_VERSION:-4.0.1}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${KNOWLEDGE_DUAL_SCOPE_WORK_DIR:-$(mktemp -d)}"
SMOKE_DIR="$WORK_DIR/cordis-smoke"
GLOBAL_ROOT="$WORK_DIR/global-knowledge"
PROJECT_ROOT="$WORK_DIR/project"

source "$ROOT_DIR/agent_harness/validation/lib/common_runtime.sh"
trap 'rm -rf "$WORK_DIR"' EXIT
mkdir -p "$SMOKE_DIR" "$GLOBAL_ROOT" "$PROJECT_ROOT/architecture" "$PROJECT_ROOT/rules" "$PROJECT_ROOT/knowledge" "$PROJECT_ROOT/gates"
printf 'synthetic\n' > "$PROJECT_ROOT/project.marker"

npm_install_if_needed "$ROOT_DIR/agent_harness/project_contract" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
(cd "$ROOT_DIR/agent_harness/project_contract" && npm test && npm run build)

npm_install_if_needed "$ROOT_DIR/agent_harness/governance_core" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
(cd "$ROOT_DIR/agent_harness/governance_core" && npm test && npm run build)

npm_install_if_needed "$ROOT_DIR/agent_harness/public_plugins/project_manager" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
(cd "$ROOT_DIR/agent_harness/public_plugins/project_manager" && npm test && npm run build)

npm_install_if_needed "$ROOT_DIR/agent_harness/public_plugins/knowledge_manager" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
(cd "$ROOT_DIR/agent_harness/public_plugins/knowledge_manager" && npm test && npm run build)

cat > "$GLOBAL_ROOT/TAXONOMY.yaml" <<'EOF'
standard: knowledge-library-v0.2
categories:
  - id: C010
    title: Technical Knowledge
    children:
      - id: C010.010
        title: Chips
EOF
cat > "$GLOBAL_ROOT/001_library.md" <<'EOF'
# [K001] Global Knowledge

## [K001.001] BootROM Flash Programming
Status: VALIDATED
Category: C010.010
Fact: BootROM flash programming behavior is reusable technical knowledge outside one application project.
Scope: flash programming bootrom chip
Provenance: GLOBAL-SRC-001
Tags: [flash, bootrom]
EOF

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
cat > "$PROJECT_ROOT/gates/00_INDEX.md" <<'EOF'
---
interface: project-resource-index-v0.1
resource: gates
standard: gate-v0.1
files: []
---
EOF
cat > "$PROJECT_ROOT/knowledge/TAXONOMY.yaml" <<'EOF'
standard: knowledge-library-v0.2
categories:
  - id: C010
    title: Project Implementation
EOF
cat > "$PROJECT_ROOT/knowledge/001_library.md" <<'EOF'
# [K001] Project Knowledge

## [K001.001] Project Flash Programming Backend
Status: VALIDATED
Category: C010
Fact: The synthetic project's flash programming backend routes jobs through its project-specific implementation pipeline.
Scope: flash programming backend project
Provenance: PROJECT-SRC-001
Tags: [flash, backend]
EOF

cd "$SMOKE_DIR"
npm init -y >/dev/null
npm pkg set type=module >/dev/null
npm_install_if_needed "$SMOKE_DIR" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS" \
  "@deepseek-ai/cordis@$CORDIS_VERSION" \
  "$ROOT_DIR/agent_harness/governance_core" \
  "$ROOT_DIR/agent_harness/project_contract" \
  "$ROOT_DIR/agent_harness/public_plugins/project_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/knowledge_manager"

cat > "$SMOKE_DIR/smoke.mjs" <<'EOF'
import { Context } from '@deepseek-ai/cordis'
import GovernanceCatalogService from '@agent-harness/governance-core'
import * as projectManagerPlugin from '@agent-harness/project-manager'
import * as knowledgePlugin from '@agent-harness/knowledge-manager'

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
fibers.push(ctx.plugin(knowledgePlugin)); await tick()

const pm = ctx.get('projectManager')
const knowledge = ctx.get('knowledgeManager')
assert(pm && knowledge, 'required public services missing')
assert(knowledge.isGlobalLibraryMounted(), 'Global Knowledge should mount from Harness env')

const disposeProject = pm.registerProject(manifest, projectRoot)
knowledge.refreshProject('synthetic-project')

const global = knowledge.searchGlobalKnowledge({ query: 'flash programming' })
assert(global.some(item => item.knowledgeUri === 'knowledge://global/K001.001'), 'Global search failed')

const project = knowledge.searchKnowledge({ projectId: 'synthetic-project', query: 'flash programming' })
assert(project.some(item => item.id === 'K001.001'), 'Project search failed')

const combined = knowledge.searchKnowledgeCombined({
  projectId: 'synthetic-project',
  query: 'flash programming',
  limit: 8,
})
assert(combined.length >= 2, 'Combined search should include Global and Project')
assert(combined[0]?.libraryScope.kind === 'global', 'Combined search must return Global first')
assert(combined.some(item => item.knowledgeUri === 'knowledge://global/K001.001'), 'Combined Global URI missing')
assert(combined.some(item => item.knowledgeUri === 'knowledge://project/synthetic-project/K001.001'), 'Combined Project URI missing')

const globalRef = knowledge.resolveKnowledgeReference('knowledge://global/K001.001')
const projectRef = knowledge.resolveKnowledgeReference('knowledge://project/synthetic-project/K001.001')
assert(globalRef?.result.node.title === 'BootROM Flash Programming', 'Global URI resolve failed')
assert(projectRef?.result.node.title === 'Project Flash Programming Backend', 'Project URI resolve failed')

const globalCandidate = knowledge.submitGlobalKnowledgeCandidate({
  categoryId: 'C010.010',
  title: 'ROM Reset Observation',
  fact: 'A reusable ROM reset observation can be contributed by any project as Global Knowledge.',
  provenance: 'TASK-GLOBAL-001',
  tags: ['rom', 'reset'],
})
assert(globalCandidate.status === 'CANDIDATE', 'Global contribution must start as CANDIDATE')

const projectCandidate = knowledge.submitKnowledgeCandidate('synthetic-project', {
  categoryId: 'C010',
  title: 'Project Worker Layout',
  fact: 'The synthetic project stores its worker implementation under a project-specific layout.',
  provenance: 'TASK-PROJECT-001',
  tags: ['worker'],
})
assert(projectCandidate.status === 'CANDIDATE', 'Project contribution must start as CANDIDATE')

// Unload Project. Global library must survive unchanged.
disposeProject()
knowledge.removeProject('synthetic-project')
const globalAfterUnload = knowledge.searchGlobalKnowledge({ query: 'rom reset', filters: { status: 'CANDIDATE' } })
assert(globalAfterUnload.some(item => item.candidate.id === globalCandidate.knowledgeId), 'Project unload damaged Global Knowledge')
assert(knowledge.resolveKnowledgeReference(`knowledge://global/${globalCandidate.knowledgeId}`), 'Global URI unavailable after project unload')

for (let index = fibers.length - 1; index >= 1; index -= 1) {
  await fibers[index].dispose(); await tick()
}
await fibers[0].dispose(); await tick()
console.log('KNOWLEDGE_DUAL_SCOPE_V0_2=PASS')
EOF

AGENT_HARNESS_GLOBAL_KNOWLEDGE_ROOT="$GLOBAL_ROOT" \
SYNTHETIC_PROJECT_ROOT="$PROJECT_ROOT" \
node "$SMOKE_DIR/smoke.mjs"

printf '%s\n' \
  'PHASE3_KNOWLEDGE_DUAL_SCOPE_V0_2_INTEGRATION=PASS' \
  "GLOBAL_ROOT=$GLOBAL_ROOT" \
  "PROJECT_ROOT=$PROJECT_ROOT"
