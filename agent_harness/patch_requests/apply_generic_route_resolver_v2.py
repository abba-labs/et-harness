#!/usr/bin/env python3
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "agent_harness/public_plugins/auto_governance_engine/src/service.ts"

text = SERVICE.read_text(encoding="utf-8")

old_import = "import type { ProjectCandidateResult, ProjectContext } from '@agent-harness/project-contract'\n"
new_import = "import type { ProjectContext } from '@agent-harness/project-contract'\n"
if old_import in text:
    text = text.replace(old_import, new_import, 1)
elif new_import not in text:
    raise SystemExit("expected ProjectContext import not found")

resolver_import = (
    "import {\n"
    "  resolveGovernanceRouteGraph,\n"
    "  type GovernanceRouteResourceKind,\n"
    "} from './route-resolver.js'\n"
)
if resolver_import not in text:
    contracts_import = "} from './contracts.js'\n"
    if contracts_import not in text:
        raise SystemExit("contracts import terminator not found")
    text = text.replace(contracts_import, contracts_import + resolver_import, 1)

helper_pattern = re.compile(
    r"const candidateIds = .*?\n\nconst normalizedPath =",
    re.DOTALL,
)
text, helper_count = helper_pattern.subn("const normalizedPath =", text, count=1)
if helper_count == 0 and "candidateRelatedResourceIds" in text:
    raise SystemExit("legacy one-hop route helper block could not be removed")

route_pattern = re.compile(
    r"    const architecture = this\.runtimeContext\.architectureNavigator\.searchArchitecture\(\{ \.\.\.request, limit: 6 \}\)\n"
    r".*?"
    r"    const route: AutoGovernanceRouteSnapshot = \{\n"
    r"      architectureIds: candidateIds\(architecture\),\n"
    r"      ruleIds: candidateIds\(rules\),\n"
    r"      knowledgeIds: candidateIds\(knowledge\),\n"
    r"      gateIds: candidateIds\(gates\),\n"
    r"    \}\n",
    re.DOTALL,
)
new_route = """    const seeds = {
      architecture: this.runtimeContext.architectureNavigator.searchArchitecture({ ...request, limit: 6 }),
      rule: this.runtimeContext.ruleManager.searchRules({ ...request, limit: 10 }),
      knowledge: this.runtimeContext.knowledgeManager.searchKnowledge({ ...request, limit: 8 }),
      gate: this.runtimeContext.gateManager.searchGates({
        ...request,
        limit: phase === 'implementation' ? 24 : 8,
      }),
    }
    const exactLookup = (kind: GovernanceRouteResourceKind, id: string) => {
      if (kind === 'architecture') {
        return this.runtimeContext.architectureNavigator.searchArchitecture({ ...request, query: id, limit: 1 })[0]
      }
      if (kind === 'rule') {
        return this.runtimeContext.ruleManager.searchRules({ ...request, query: id, limit: 1 })[0]
      }
      if (kind === 'knowledge') {
        return this.runtimeContext.knowledgeManager.searchKnowledge({ ...request, query: id, limit: 1 })[0]
      }
      return this.runtimeContext.gateManager.searchGates({ ...request, query: id, limit: 1 })[0]
    }
    const resolution = resolveGovernanceRouteGraph({
      projectId: runtime.projectId,
      seeds,
      maxDepth: 2,
      limits: {
        architecture: 12,
        rule: 24,
        knowledge: 20,
        gate: phase === 'implementation' ? 32 : 16,
      },
      exactLookup,
    })
    const route: AutoGovernanceRouteSnapshot = {
      architectureIds: resolution.candidates.architecture.map(candidate => candidate.id),
      ruleIds: resolution.candidates.rule.map(candidate => candidate.id),
      knowledgeIds: resolution.candidates.knowledge.map(candidate => candidate.id),
      gateIds: resolution.candidates.gate.map(candidate => candidate.id),
    }
"""
text, route_count = route_pattern.subn(new_route, text, count=1)
if route_count == 0 and "const resolution = resolveGovernanceRouteGraph" not in text:
    raise SystemExit("legacy routeTask block could not be replaced")

SERVICE.write_text(text, encoding="utf-8")
print(f"updated {SERVICE.relative_to(ROOT)}")
