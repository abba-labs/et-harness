#!/usr/bin/env python3
from pathlib import Path

path = Path(__file__).with_name('apply_project_context_contribution_v0_1.py')
text = path.read_text(encoding='utf-8')

old_helper = '''    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{relative}: expected one replacement, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
'''
new_helper = '''    count = text.count(old)
    repeated_contract_route = (
        relative.endswith("auto_governance_engine/src/contracts.ts")
        and old.startswith("  readonly route: AutoGovernanceRouteSnapshot")
        and count in {1, 2}
    )
    if count != 1 and not repeated_contract_route:
        raise SystemExit(f"{relative}: expected one replacement, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
'''
if text.count(old_helper) != 1:
    raise SystemExit('patch helper marker mismatch')
text = text.replace(old_helper, new_helper, 1)

old_route_call = '''replace_once(
    "agent_harness/public_plugins/auto_governance_engine/src/service.ts",
    """import {
  resolveGovernanceRouteGraph,
  type GovernanceRouteResourceKind,
} from './route-resolver.js'
""",
    """import {
  PROJECT_CONTEXT_CONTRIBUTION_CAPABILITY,
  PROJECT_CONTEXT_CONTRIBUTION_REQUEST_SCHEMA,
  contributionReceipt,
  mergeContributionInlineItems,
  mergeContributionReferences,
  resolveDeclaredProjectContextContributions,
  type NormalizedProjectContextContribution,
} from './context-contribution.js'
import {
  resolveGovernanceRouteGraph,
  type GovernanceRouteResourceKind,
} from './route-resolver.js'
""",
)
'''
new_route_call = '''replace_once(
    "agent_harness/public_plugins/auto_governance_engine/src/service.ts",
    """import {
  resolveGovernanceRouteGraph,
""",
    """import {
  PROJECT_CONTEXT_CONTRIBUTION_CAPABILITY,
  PROJECT_CONTEXT_CONTRIBUTION_REQUEST_SCHEMA,
  contributionReceipt,
  mergeContributionInlineItems,
  mergeContributionReferences,
  resolveDeclaredProjectContextContributions,
  type NormalizedProjectContextContribution,
} from './context-contribution.js'
import {
  resolveGovernanceRouteGraph,
""",
)
'''
if text.count(old_route_call) != 1:
    raise SystemExit('route import patch marker mismatch')
text = text.replace(old_route_call, new_route_call, 1)

path.write_text(text, encoding='utf-8')
print('Prepared project context contribution patch.')
