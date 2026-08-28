#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "agent_harness/public_plugins/auto_governance_engine/src/service.ts"

text = SERVICE.read_text(encoding="utf-8")

old_import = "import type { ProjectCandidateResult, ProjectContext } from '@agent-harness/project-contract'\n"
new_import = "import type { ProjectContext } from '@agent-harness/project-contract'\n"
if old_import not in text:
    raise SystemExit("expected ProjectCandidateResult import not found")
text = text.replace(old_import, new_import, 1)

contracts_import = "} from './contracts.js'\n"
resolver_import = (
    "} from './contracts.js'\n"
    "import {\n"
    "  resolveGovernanceRouteGraph,\n"
    "  type GovernanceRouteResourceKind,\n"
    "} from './route-resolver.js'\n"
)
if contracts_import not in text:
    raise SystemExit("contracts import terminator not found")
text = text.replace(contracts_import, resolver_import, 1)

old_helpers = """const candidateIds = (candidates: readonly ProjectCandidateResult[]): string[] =>
  unique(candidates.map(candidate => candidate.id))

export const candidateRelatedResourceIds = (
  candidates: readonly ProjectCandidateResult[],
  prefix: 'A' | 'R' | 'K' | 'G',
): string[] => {
  const pattern = new RegExp(`^${prefix}\\d{3}(?:\\.\\d{3})*$`)
  return unique(candidates.flatMap(candidate => {
    const metadata = recordOf(candidate.metadata)
    return [metadata?.refs, metadata?.relations].flatMap(value =>
      Array.isArray(value)
        ? value.filter((item): item is string => typeof item === 'string')
        : [],
    )
  })).filter(id => pattern.test(id))
}

const mergeCandidateResults = (
  direct: readonly ProjectCandidateResult[],
  related: readonly ProjectCandidateResult[],
  limit: number,
): ProjectCandidateResult[] => {
  const merged = new Map<string, ProjectCandidateResult>()
  for (const candidate of [...direct, ...related]) {
    if (!merged.has(candidate.id)) merged.set(candidate.id, candidate)
  }
  return [...merged.values()].slice(0, Math.max(1, limit))
}

"""
if old_helpers not in text:
    raise SystemExit("legacy one-hop route helper block not found")
text = text.replace(old_helpers, "", 1)

old_route = """    const architecture = this.runtimeContext.architectureNavigator.searchArchitecture({ ...request, limit: 6 })
    const rules = this.runtimeContext.ruleManager.searchRules({ ...request, limit: 10 })
    const directKnowledge = this.runtimeContext.knowledgeManager.searchKnowledge({ ...request, limit: 8 })
    const directGates = this.runtimeContext.gateManager.searchGates({ ...request, limit: phase === 'implementation' ? 24 : 8 })
    const relationSources = [...architecture, ...rules]
    const relatedKnowledge = candidateRelatedResourceIds(relationSources, 'K').flatMap(id =>
      this.runtimeContext.knowledgeManager.searchKnowledge({ ...request, query: id, limit: 1 }),
    )
    const relatedGates = candidateRelatedResourceIds(relationSources, 'G').flatMap(id =>
      this.runtimeContext.gateManager.searchGates({ ...request, query: id, limit: 1 }),
    )
    const knowledge = mergeCandidateResults(directKnowledge, relatedKnowledge, 8)
    const gates = mergeCandidateResults(directGates, relatedGates, phase === 'implementation' ? 24 : 8)
    const route: AutoGovernanceRouteSnapshot = {
      architectureIds: candidateIds(architecture),
      ruleIds: candidateIds(rules),
      knowledgeIds: candidateIds(knowledge),
      gateIds: candidateIds(gates),
    }
"""
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
if old_route not in text:
    raise SystemExit("legacy routeTask block not found")
text = text.replace(old_route, new_route, 1)

SERVICE.write_text(text, encoding="utf-8")
print(f"updated {SERVICE.relative_to(ROOT)}")
