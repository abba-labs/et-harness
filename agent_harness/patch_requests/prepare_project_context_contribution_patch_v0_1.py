#!/usr/bin/env python3
from pathlib import Path

path = Path(__file__).with_name('apply_project_context_contribution_v0_1.py')
text = path.read_text(encoding='utf-8')
old = '''    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{relative}: expected one replacement, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
'''
new = '''    count = text.count(old)
    repeated_contract_route = (
        relative.endswith("auto_governance_engine/src/contracts.ts")
        and old.startswith("  readonly route: AutoGovernanceRouteSnapshot")
        and count in {1, 2}
    )
    if count != 1 and not repeated_contract_route:
        raise SystemExit(f"{relative}: expected one replacement, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
'''
if text.count(old) != 1:
    raise SystemExit('patch helper marker mismatch')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
print('Prepared project context contribution patch.')
