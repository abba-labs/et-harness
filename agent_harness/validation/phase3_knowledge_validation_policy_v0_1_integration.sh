#!/usr/bin/env bash
set -euo pipefail

CORDIS_VERSION="${CORDIS_VERSION:-4.0.1}"
NPM_REGISTRY="${NPM_REGISTRY:-https://registry.npmjs.org}"
NPM_INSTALL_TIMEOUT_SECONDS="${NPM_INSTALL_TIMEOUT_SECONDS:-1200}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${KNOWLEDGE_VALIDATION_POLICY_WORK_DIR:-$(mktemp -d)}"
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
EOF
cat > "$GLOBAL_ROOT/001_library.md" <<'EOF'
# [K001] Global Knowledge

## [K001.001] Global Candidate Ready Path
Status: CANDIDATE
Category: C010
Fact: Global candidate requires two independent supporting bases.
Scope: validation-policy
Provenance: POLICY-TEST

## [K001.002] Global Candidate Contradiction Path
Status: CANDIDATE
Category: C010
Fact: Contradiction blocks global promotion.
Scope: validation-policy
Provenance: POLICY-TEST
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
    title: Project Knowledge
EOF
cat > "$PROJECT_ROOT/knowledge/001_library.md" <<'EOF'
# [K001] Project Knowledge

## [K001.001] Project Candidate
Status: CANDIDATE
Category: C010
Fact: Project candidate requires one supporting basis.
Scope: validation-policy
Provenance: POLICY-TEST
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
const validation = ctx.get('knowledgeValidationPolicy')
assert(pm && evidence && knowledge && validation, 'required services missing')
const disposeProject = pm.registerProject(manifest, projectRoot)
knowledge.refreshProject('synthetic-project')

const source1 = knowledge.registerGlobalSource({
  kind: 'SPEC', title: 'Spec One', location: 'docs/spec-one.pdf', revision: '1.0',
})
const source2 = knowledge.registerGlobalSource({
  kind: 'CODE', title: 'Canonical Code', location: 'source/reference.c', revision: 'abc123',
})
const source3 = knowledge.registerGlobalSource({
  kind: 'SVD', title: 'Register Definition', location: 'spec/device.svd', revision: '2.0',
})

// Project: one document-level SUPPORT is enough.
knowledge.recordVerification({
  knowledgeUri: 'knowledge://project/synthetic-project/K001.001',
  basisRef: source1.sourceUri,
  relation: 'SUPPORT',
})
let projectDecision = validation.evaluate('knowledge://project/synthetic-project/K001.001')
assert(projectDecision.decision === 'READY', 'Project candidate should be READY after one document SUPPORT')
const projectPromotion = validation.promote('knowledge://project/synthetic-project/K001.001')
assert(projectPromotion.mutation.status === 'VALIDATED', 'Project explicit promotion failed')

// Global: one document SUPPORT is insufficient. A CODE reference remains REFERENCE;
// a second independent document-level SUPPORT makes the candidate READY.
knowledge.recordVerification({
  knowledgeUri: 'knowledge://global/K001.001',
  basisRef: source1.sourceUri,
  relation: 'SUPPORT',
})
let globalDecision = validation.evaluate('knowledge://global/K001.001')
assert(globalDecision.decision === 'INSUFFICIENT', 'Global candidate should need two document SUPPORT bases')
knowledge.recordVerification({
  knowledgeUri: 'knowledge://global/K001.001',
  basisRef: source2.sourceUri,
  relation: 'SUPPORT',
})
globalDecision = validation.evaluate('knowledge://global/K001.001')
assert(globalDecision.decision === 'INSUFFICIENT', 'CODE reference must not satisfy document validation quorum')
assert(globalDecision.distinctSupportCount === 2, 'Both SUPPORT records should remain observable')
assert(globalDecision.documentSupportCount === 1, 'Only the SPEC should count as document validation')
knowledge.recordVerification({
  knowledgeUri: 'knowledge://global/K001.001',
  basisRef: source3.sourceUri,
  relation: 'SUPPORT',
})
globalDecision = validation.evaluate('knowledge://global/K001.001')
assert(globalDecision.decision === 'READY', 'Global candidate should be READY after two document SUPPORT bases')
assert(globalDecision.documentSupportCount === 2, 'Global document validation quorum should be two')
const globalPromotion = validation.promote('knowledge://global/K001.001')
assert(globalPromotion.mutation.status === 'VALIDATED', 'Global explicit promotion failed')

// CONTRADICT blocks even when enough document SUPPORT exists.
knowledge.recordVerification({
  knowledgeUri: 'knowledge://global/K001.002',
  basisRef: source1.sourceUri,
  relation: 'SUPPORT',
})
knowledge.recordVerification({
  knowledgeUri: 'knowledge://global/K001.002',
  basisRef: source3.sourceUri,
  relation: 'SUPPORT',
})
const runtimeEvidence = evidence.recordEvidence({
  projectId: 'synthetic-project',
  taskId: 'TASK-CONTRADICT',
  kind: 'runtime-test',
  result: 'FAIL',
  summary: 'Runtime behavior contradicts the candidate claim.',
  source: 'test.execute',
})
knowledge.recordVerification({
  knowledgeUri: 'knowledge://global/K001.002',
  basisRef: knowledgePlugin.qualifyEvidenceId('synthetic-project', runtimeEvidence.evidenceId),
  relation: 'CONTRADICT',
})
const blocked = validation.evaluate('knowledge://global/K001.002')
assert(blocked.decision === 'BLOCKED', 'CONTRADICT must block promotion')
let blockedPromotion = false
try { validation.promote('knowledge://global/K001.002') } catch { blockedPromotion = true }
assert(blockedPromotion, 'BLOCKED candidate must not promote')

// Candidate Fact change makes old SUPPORT stale.
const managed = knowledge.submitKnowledgeCandidate('synthetic-project', {
  categoryId: 'C010',
  title: 'Mutable Candidate',
  fact: 'Initial claim for fingerprint test.',
  scope: 'fingerprint-test',
  provenance: 'POLICY-TEST',
})
const managedUri = `knowledge://project/synthetic-project/${managed.knowledgeId}`
knowledge.recordVerification({ knowledgeUri: managedUri, basisRef: source1.sourceUri, relation: 'SUPPORT' })
assert(validation.evaluate(managedUri).decision === 'READY', 'Initial managed claim should be READY')
knowledge.updateKnowledgeCandidate('synthetic-project', managed.knowledgeId, {
  fact: 'Changed claim invalidates old verification.',
})
const changed = validation.evaluate(managedUri)
assert(changed.decision === 'INSUFFICIENT', 'Changed Claim must not reuse old SUPPORT')
assert(changed.records.length === 0, 'Old Claim Verification should be excluded')

// Promotion only changes Status; K-ID remains stable.
assert(knowledge.getNode('synthetic-project', 'K001.001')?.node.status === 'VALIDATED', 'Project promoted status missing')
assert(knowledge.getGlobalNode('K001.001')?.node.status === 'VALIDATED', 'Global promoted status missing')

disposeProject()
knowledge.removeProject('synthetic-project')
for (let index = fibers.length - 1; index >= 1; index -= 1) {
  await fibers[index].dispose(); await tick()
}
await fibers[0].dispose(); await tick()
console.log('KNOWLEDGE_VALIDATION_POLICY_V0_1=PASS')
EOF

AGENT_HARNESS_GLOBAL_KNOWLEDGE_ROOT="$GLOBAL_ROOT" \
SYNTHETIC_PROJECT_ROOT="$PROJECT_ROOT" \
node "$SMOKE_DIR/smoke.mjs"

grep -q 'Status: VALIDATED' "$GLOBAL_ROOT/001_library.md"
grep -q 'knowledgeFingerprint' "$GLOBAL_ROOT/VERIFICATIONS.jsonl"

printf '%s\n' \
  'PHASE3_KNOWLEDGE_VALIDATION_POLICY_V0_1_INTEGRATION=PASS' \
  "GLOBAL_ROOT=$GLOBAL_ROOT" \
  "PROJECT_ROOT=$PROJECT_ROOT"
