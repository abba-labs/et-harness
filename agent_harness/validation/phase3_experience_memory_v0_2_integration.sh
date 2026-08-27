#!/usr/bin/env bash
set -euo pipefail

CORDIS_VERSION="${CORDIS_VERSION:-4.0.1}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${EXPERIENCE_MEMORY_V0_2_WORK_DIR:-$(mktemp -d)}"
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
  public_plugins/knowledge_manager \
  public_plugins/experience_memory_manager; do
  npm_install_if_needed "$ROOT_DIR/agent_harness/$dir" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS"
  (cd "$ROOT_DIR/agent_harness/$dir" && npm test && npm run build)
done

cat > "$GLOBAL_ROOT/TAXONOMY.yaml" <<'EOF'
standard: knowledge-library-v0.2
categories:
  - id: C010
    title: Shared Engineering Knowledge
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
    title: Project Engineering Knowledge
EOF

# A valid empty knowledge-library-v0.2 contains TAXONOMY.yaml and no numbered
# Knowledge shard yet. The first candidate must exercise managed shard creation.

cd "$SMOKE_DIR"
npm init -y >/dev/null
npm pkg set type=module >/dev/null
npm_install_if_needed "$SMOKE_DIR" "$NPM_REGISTRY" "$NPM_INSTALL_TIMEOUT_SECONDS" \
  "@deepseek-ai/cordis@$CORDIS_VERSION" \
  "$ROOT_DIR/agent_harness/governance_core" \
  "$ROOT_DIR/agent_harness/project_contract" \
  "$ROOT_DIR/agent_harness/public_plugins/project_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/evidence_state_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/knowledge_manager" \
  "$ROOT_DIR/agent_harness/public_plugins/experience_memory_manager"

cat > "$SMOKE_DIR/smoke.mjs" <<'EOF'
import { Context } from '@deepseek-ai/cordis'
import GovernanceCatalogService from '@agent-harness/governance-core'
import * as projectManagerPlugin from '@agent-harness/project-manager'
import * as evidencePlugin from '@agent-harness/evidence-state-manager'
import * as knowledgePlugin from '@agent-harness/knowledge-manager'
import * as experiencePlugin from '@agent-harness/experience-memory-manager'

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
fibers.push(ctx.plugin(experiencePlugin)); await tick()

const pm = ctx.get('projectManager')
const evidence = ctx.get('evidenceStateManager')
const knowledge = ctx.get('knowledgeManager')
const validation = ctx.get('knowledgeValidationPolicy')
const experience = ctx.get('experienceMemoryManager')
assert(pm && evidence && knowledge && validation && experience, 'required services missing')
const disposeProject = pm.registerProject(manifest, projectRoot)
knowledge.refreshProject('synthetic-project')

const projectSource = knowledge.registerProjectSource('synthetic-project', {
  kind: 'SPEC',
  title: 'Project Reset Specification',
  location: 'docs/project-reset-spec.pdf',
  revision: '1.0',
})
const globalSource1 = knowledge.registerGlobalSource({
  kind: 'SPEC',
  title: 'Shared Retry Specification',
  location: 'docs/shared-retry-spec.pdf',
  revision: '1.0',
})
const globalSource2 = knowledge.registerGlobalSource({
  kind: 'SVD',
  title: 'Shared Device Definition',
  location: 'spec/shared-device.svd',
  revision: '2.0',
})

// Project path: Experience evidence remains traceable REFERENCE; one trusted
// project document SUPPORT makes the candidate READY for explicit promotion.
const projectEvidence = evidence.recordEvidence({
  projectId: 'synthetic-project',
  taskId: 'TASK-PROJECT',
  kind: 'runtime-test',
  result: 'PASS',
  summary: 'Project behavior was reproduced and observed.',
  source: 'test.execute',
})
const projectExperience = experience.recordCandidate({
  projectId: 'synthetic-project',
  taskId: 'TASK-PROJECT',
  title: 'Project Reusable Experience',
  fact: 'Project reset sequence must complete before the first peripheral access.',
  scope: 'project-reset',
  evidenceRefs: [projectEvidence.evidenceId],
  refs: ['A010'],
})
assert(projectExperience.status === 'CANDIDATE', 'Experience must start as CANDIDATE')

const projectSubmitted = experience.submitToKnowledge('synthetic-project', {
  candidateId: projectExperience.candidateId,
  targetScope: 'project',
  categoryId: 'C010',
})
assert(projectSubmitted.evaluation.decision === 'INSUFFICIENT', 'Ordinary Experience Evidence must not validate Knowledge')
assert(projectSubmitted.verificationRecords.length === 1, 'Project Evidence must become one Verification')
assert(projectSubmitted.verificationRecords[0].basisRef === knowledgePlugin.qualifyEvidenceId('synthetic-project', projectEvidence.evidenceId), 'Verification basis mismatch')
assert(projectSubmitted.verificationRecords[0].validationClass === 'REFERENCE', 'Ordinary Evidence must remain REFERENCE')
let projectState = experience.getCandidate('synthetic-project', projectExperience.candidateId)
assert(projectState?.status === 'KNOWLEDGE_CANDIDATE', 'Experience must enter KNOWLEDGE_CANDIDATE state')
assert(projectState?.knowledgeCandidateUri === projectSubmitted.knowledgeUri, 'Experience must link Knowledge Candidate URI')
assert(knowledge.resolveKnowledgeReference(projectSubmitted.knowledgeUri)?.result.node.status === 'CANDIDATE', 'Knowledge must remain CANDIDATE before explicit promotion')

knowledge.recordVerification({
  knowledgeUri: projectSubmitted.knowledgeUri,
  basisRef: projectSource.sourceUri,
  relation: 'SUPPORT',
})
assert(experience.evaluateKnowledgeCandidate('synthetic-project', projectExperience.candidateId).decision === 'READY', 'One project document SUPPORT should make Project Knowledge READY')
const projectPromoted = experience.promoteKnowledgeCandidate('synthetic-project', projectExperience.candidateId)
assert(projectPromoted.status === 'PROMOTED', 'Project Experience promotion failed')
assert(knowledge.resolveKnowledgeReference(projectSubmitted.knowledgeUri)?.result.node.status === 'VALIDATED', 'Project Knowledge must become VALIDATED')
projectState = experience.getCandidate('synthetic-project', projectExperience.candidateId)
assert(projectState?.status === 'PROMOTED', 'Experience must become PROMOTED only after Knowledge VALIDATED')
assert(projectState?.promotedKnowledgeUri === projectSubmitted.knowledgeUri, 'Promoted Knowledge URI missing')

// Global path: Experience Evidence remains REFERENCE. Two independent trusted
// document SUPPORT bases are required before explicit Global promotion.
const globalEvidence = evidence.recordEvidence({
  projectId: 'synthetic-project',
  taskId: 'TASK-GLOBAL',
  kind: 'runtime-test',
  result: 'PASS',
  summary: 'A project observation supports the shared claim but is not global validation.',
  source: 'test.execute',
})
const globalExperience = experience.recordCandidate({
  projectId: 'synthetic-project',
  taskId: 'TASK-GLOBAL',
  title: 'Shared Reusable Experience',
  fact: 'A shared retry rule is required after this class of transient initialization failure.',
  scope: 'shared-initialization',
  evidenceRefs: [globalEvidence.evidenceId],
})
const globalSubmitted = experience.submitToKnowledge('synthetic-project', {
  candidateId: globalExperience.candidateId,
  targetScope: 'global',
  categoryId: 'C010',
})
assert(globalSubmitted.evaluation.decision === 'INSUFFICIENT', 'Global Knowledge must reject ordinary Experience Evidence as validation')
assert(globalSubmitted.verificationRecords[0].validationClass === 'REFERENCE', 'Global Experience Evidence must remain REFERENCE')
assert(experience.getCandidate('synthetic-project', globalExperience.candidateId)?.status === 'KNOWLEDGE_CANDIDATE', 'Global Experience link state missing')
let blocked = false
try { experience.promoteKnowledgeCandidate('synthetic-project', globalExperience.candidateId) } catch { blocked = true }
assert(blocked, 'INSUFFICIENT Global Knowledge must not promote')
assert(experience.getCandidate('synthetic-project', globalExperience.candidateId)?.status === 'KNOWLEDGE_CANDIDATE', 'Failed promotion must not corrupt Experience state')

knowledge.recordVerification({
  knowledgeUri: globalSubmitted.knowledgeUri,
  basisRef: globalSource1.sourceUri,
  relation: 'SUPPORT',
})
assert(experience.evaluateKnowledgeCandidate('synthetic-project', globalExperience.candidateId).decision === 'INSUFFICIENT', 'One Global document SUPPORT must remain insufficient')
knowledge.recordVerification({
  knowledgeUri: globalSubmitted.knowledgeUri,
  basisRef: globalSource2.sourceUri,
  relation: 'SUPPORT',
})
const globalReady = experience.evaluateKnowledgeCandidate('synthetic-project', globalExperience.candidateId)
assert(globalReady.decision === 'READY', 'Two Global document SUPPORT bases should make Knowledge READY')
assert(globalReady.documentSupportCount === 2, 'Global document quorum should equal two')
const globalPromoted = experience.promoteKnowledgeCandidate('synthetic-project', globalExperience.candidateId)
assert(globalPromoted.status === 'PROMOTED', 'Global Experience promotion failed')
assert(knowledge.resolveKnowledgeReference(globalSubmitted.knowledgeUri)?.result.node.status === 'VALIDATED', 'Global Knowledge must become VALIDATED')

// Memory search keeps unpromoted linked candidates visible.
const pendingEvidence = evidence.recordEvidence({
  projectId: 'synthetic-project',
  taskId: 'TASK-PENDING',
  kind: 'runtime-test',
  result: 'PASS',
  summary: 'Pending global candidate has no trusted validation basis.',
  source: 'test.execute',
})
const pendingExperience = experience.recordCandidate({
  projectId: 'synthetic-project',
  taskId: 'TASK-PENDING',
  title: 'Pending Shared Memory',
  fact: 'Pending shared memory remains searchable while validation is incomplete.',
  evidenceRefs: [pendingEvidence.evidenceId],
})
experience.submitToKnowledge('synthetic-project', {
  candidateId: pendingExperience.candidateId,
  targetScope: 'global',
  categoryId: 'C010',
})
const memory = experience.searchMemory({ projectId: 'synthetic-project', query: 'Pending Shared Memory' })
assert(memory.some(item => item.id === pendingExperience.candidateId), 'KNOWLEDGE_CANDIDATE must remain searchable memory')

// Legacy direct writer must remain blocked for library-v0.2.
const legacyEvidence = evidence.recordEvidence({
  projectId: 'synthetic-project',
  taskId: 'TASK-LEGACY',
  kind: 'runtime-test',
  result: 'PASS',
  summary: 'Legacy bypass guard evidence.',
  source: 'test.execute',
})
const legacyExperience = experience.recordCandidate({
  projectId: 'synthetic-project',
  taskId: 'TASK-LEGACY',
  title: 'Legacy Guard',
  fact: 'Legacy direct promotion must stay blocked.',
  evidenceRefs: [legacyEvidence.evidenceId],
})
let legacyBlocked = false
try {
  experience.promoteToKnowledge('synthetic-project', {
    candidateId: legacyExperience.candidateId,
    fileId: 'K001',
    parentNodeId: 'K001',
    nodeId: 'K001.999',
    title: 'Legacy Guard',
  })
} catch (error) {
  legacyBlocked = String(error).includes('禁止 Experience Manager 直接写入 VALIDATED Knowledge')
}
assert(legacyBlocked, 'Legacy direct VALIDATED writer must stay blocked')

disposeProject()
knowledge.removeProject('synthetic-project')
for (let index = fibers.length - 1; index >= 1; index -= 1) {
  await fibers[index].dispose(); await tick()
}
await fibers[0].dispose(); await tick()
console.log('EXPERIENCE_MEMORY_V0_2=PASS')
EOF

AGENT_HARNESS_GLOBAL_KNOWLEDGE_ROOT="$GLOBAL_ROOT" \
SYNTHETIC_PROJECT_ROOT="$PROJECT_ROOT" \
node "$SMOKE_DIR/smoke.mjs"

grep -q 'Status: VALIDATED' "$PROJECT_ROOT/knowledge/001_library.md"
grep -q 'Status: VALIDATED' "$GLOBAL_ROOT/001_library.md"
grep -q 'knowledgeFingerprint' "$PROJECT_ROOT/knowledge/VERIFICATIONS.jsonl"
grep -q 'knowledgeFingerprint' "$GLOBAL_ROOT/VERIFICATIONS.jsonl"

printf '%s\n' \
  'PHASE3_EXPERIENCE_MEMORY_V0_2_INTEGRATION=PASS' \
  "GLOBAL_ROOT=$GLOBAL_ROOT" \
  "PROJECT_ROOT=$PROJECT_ROOT"
