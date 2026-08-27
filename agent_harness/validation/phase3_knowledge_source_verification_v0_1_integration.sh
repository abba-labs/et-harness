#!/usr/bin/env bash
set -euo pipefail

CORDIS_VERSION="${CORDIS_VERSION:-4.0.1}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${KNOWLEDGE_SOURCE_VERIFICATION_WORK_DIR:-$(mktemp -d)}"
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
  public_plugins/evidence_state_manager \
  public_plugins/knowledge_manager; do
  npm_install_if_needed "$ROOT_DIR/agent_harness/$dir" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
  (cd "$ROOT_DIR/agent_harness/$dir" && npm test && npm run build)
done

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

## [K001.001] BootROM Entry
Status: CANDIDATE
Category: C010.010
Fact: A reusable BootROM entry behavior is being verified across projects.
Provenance: SOURCE-READING
Tags: [bootrom]
EOF

for resource in architecture rules gates; do
  case "$resource" in
    architecture) standard='architecture-v0.1' ;;
    rules) standard='rule-v0.1' ;;
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

cat > "$PROJECT_ROOT/knowledge/TAXONOMY.yaml" <<'EOF'
standard: knowledge-library-v0.2
categories:
  - id: C010
    title: Project Implementation
EOF
cat > "$PROJECT_ROOT/knowledge/001_library.md" <<'EOF'
# [K001] Project Knowledge

## [K001.001] Project Backend Path
Status: CANDIDATE
Category: C010
Fact: The synthetic project uses its own backend path.
Provenance: PROJECT-READING
Tags: [backend]
EOF

cd "$SMOKE_DIR"
npm init -y >/dev/null
npm pkg set type=module >/dev/null
npm_install_if_needed "$SMOKE_DIR" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS" \
  "@deepseek-ai/cordis@$CORDIS_VERSION" \
  "$ROOT_DIR/agent_harness/governance_core" \
  "$ROOT_DIR/agent_harness/project_contract" \
  "$ROOT_DIR/agent_harness/public_plugins/project_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/evidence_state_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/knowledge_manager"

cat > "$SMOKE_DIR/smoke.mjs" <<'EOF'
import { Context } from '@deepseek-ai/cordis'
import GovernanceCatalogService from '@agent-harness/governance-core'
import * as projectManagerPlugin from '@agent-harness/project-manager'
import * as evidencePlugin from '@agent-harness/evidence-state-manager'
import * as knowledgePlugin from '@agent-harness/knowledge-manager'

const tick = () => new Promise(resolve => setTimeout(resolve, 0))
const assert = (condition, message) => { if (!condition) throw new Error(message) }
const projectRoot = process.env.SYNTHETIC_PROJECT_ROOT
assert(projectRoot, 'SYNTHETIC_PROJECT_ROOT missing')

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
fibers.push(ctx.plugin(evidencePlugin)); await tick()
fibers.push(ctx.plugin(knowledgePlugin)); await tick()

const pm = ctx.get('projectManager')
const evidence = ctx.get('evidenceStateManager')
const knowledge = ctx.get('knowledgeManager')
assert(pm && evidence && knowledge, 'required services missing')
const disposeProject = pm.registerProject(manifest, projectRoot)
knowledge.refreshProject('synthetic-project')

const globalSource = knowledge.registerGlobalSource({
  kind: 'SPEC',
  title: 'BootROM Specification',
  location: 'docs/bootrom-spec.pdf',
  revision: '1.0',
})
assert(globalSource.sourceUri === 'source://global/SRC000001', 'Global Source URI wrong')

const projectSource = knowledge.registerProjectSource('synthetic-project', {
  kind: 'CODE',
  title: 'Project Backend Source',
  location: 'source/backend.ts',
})
assert(projectSource.sourceUri === 'source://project/synthetic-project/SRC000001', 'Project Source URI wrong')

knowledge.recordVerification({
  knowledgeUri: 'knowledge://global/K001.001',
  basisRef: globalSource.sourceUri,
  relation: 'SUPPORT',
})

let rejectedProjectSourceForGlobal = false
try {
  knowledge.recordVerification({
    knowledgeUri: 'knowledge://global/K001.001',
    basisRef: projectSource.sourceUri,
    relation: 'SUPPORT',
  })
} catch {
  rejectedProjectSourceForGlobal = true
}
assert(rejectedProjectSourceForGlobal, 'Global Knowledge must reject Project-private Source')

const runtimeEvidence = evidence.recordEvidence({
  projectId: 'synthetic-project',
  taskId: 'TASK-ROM-VERIFY',
  kind: 'runtime-test',
  result: 'PASS',
  summary: 'BootROM behavior reproduced on target.',
  source: 'test.execute',
})
const evidenceUri = knowledgePlugin.qualifyEvidenceId('synthetic-project', runtimeEvidence.evidenceId)
knowledge.recordVerification({
  knowledgeUri: 'knowledge://global/K001.001',
  basisRef: evidenceUri,
  relation: 'SUPPORT',
})
knowledge.recordVerification({
  knowledgeUri: 'knowledge://project/synthetic-project/K001.001',
  basisRef: evidenceUri,
  relation: 'SUPPORT',
})
knowledge.recordVerification({
  knowledgeUri: 'knowledge://project/synthetic-project/K001.001',
  basisRef: globalSource.sourceUri,
  relation: 'SUPPORT',
})

const globalSummary = knowledge.getVerificationSummary('knowledge://global/K001.001')
assert(globalSummary.supportCount === 2, 'Global Verification support count wrong')
assert(globalSummary.contradictCount === 0, 'Global Verification contradict count wrong')
const projectSummary = knowledge.getVerificationSummary('knowledge://project/synthetic-project/K001.001')
assert(projectSummary.supportCount === 2, 'Project Verification support count wrong')

// Verification persists as URI relation; project unload must not delete Global verification history.
disposeProject()
knowledge.removeProject('synthetic-project')
const afterUnload = knowledge.getVerificationSummary('knowledge://global/K001.001')
assert(afterUnload.supportCount === 2, 'Project unload damaged Global Verification history')
assert(afterUnload.records.some(record => record.basisRef === evidenceUri), 'Evidence URI was not preserved')

for (let index = fibers.length - 1; index >= 1; index -= 1) {
  await fibers[index].dispose(); await tick()
}
await fibers[0].dispose(); await tick()
console.log('KNOWLEDGE_SOURCE_VERIFICATION_V0_1=PASS')
EOF

AGENT_HARNESS_GLOBAL_KNOWLEDGE_ROOT="$GLOBAL_ROOT" \
SYNTHETIC_PROJECT_ROOT="$PROJECT_ROOT" \
node "$SMOKE_DIR/smoke.mjs"

grep -q 'knowledge-source-registry-v0.1' "$GLOBAL_ROOT/SOURCES.yaml"
grep -q 'source://global/SRC000001' "$GLOBAL_ROOT/VERIFICATIONS.jsonl"
grep -q 'evidence://project/synthetic-project/EV-' "$GLOBAL_ROOT/VERIFICATIONS.jsonl"

printf '%s\n' \
  'PHASE3_KNOWLEDGE_SOURCE_VERIFICATION_V0_1_INTEGRATION=PASS' \
  "GLOBAL_ROOT=$GLOBAL_ROOT" \
  "PROJECT_ROOT=$PROJECT_ROOT"
