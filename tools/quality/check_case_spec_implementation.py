#!/usr/bin/env python3
# Verify implemented ET_CASE_SPEC evidence binding and snapshot artifact lifecycle.

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DOC_ROOT = ROOT / "test_case_doc"
CASE_ROOT = ROOT / "pc/et_test_platform/test_cases"
_SPEC_BEGIN = "<!-- ET_CASE_SPEC_BEGIN -->"
_SPEC_END = "<!-- ET_CASE_SPEC_END -->"
_SPEC_RE = re.compile(
    rf"{re.escape(_SPEC_BEGIN)}\s*```yaml\s*(.*?)\s*```\s*{re.escape(_SPEC_END)}",
    re.DOTALL,
)
_CASE_ID = re.compile(r"^(?P<ip>[A-Z][A-Z0-9_]*)_P[0-3]_[0-9]{3}$")
_FUNCTION_ID = re.compile(r"^test_(?P<case>[a-z][a-z0-9_]*_p[0-3]_[0-9]{3})(?:_|$)")


@dataclass(frozen=True, slots=True, order=True)
class Violation:
    path: Path
    line: int
    code: str
    message: str

    def render(self) -> str:
        return f"{self.path.relative_to(ROOT)}:{self.line}: {self.code} {self.message}"


@dataclass(frozen=True, slots=True)
class RecordedProperty:
    line: int
    tokens: frozenset[str]
    api: str


@dataclass(frozen=True, slots=True)
class AssertionFact:
    line: int
    tokens: frozenset[str]


def _public_documents() -> tuple[Path, ...]:
    documents: list[Path] = []
    for path in sorted(DOC_ROOT.rglob("*.md")):
        if path.parent == DOC_ROOT or path.stem != path.parent.name:
            continue
        text = path.read_text(encoding="utf-8-sig")
        if _SPEC_BEGIN in text:
            documents.append(path)
    return tuple(documents)


def _specs(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8-sig")
    values = []
    for match in _SPEC_RE.finditer(text):
        payload = yaml.safe_load(match.group(1))
        if isinstance(payload, dict):
            values.append(payload)
    return values


def _case_functions(ip: str) -> dict[str, tuple[Path, ast.FunctionDef | ast.AsyncFunctionDef]]:
    package = CASE_ROOT / ip
    values: dict[str, tuple[Path, ast.FunctionDef | ast.AsyncFunctionDef]] = {}
    for path in sorted(package.glob("test_*_p*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            match = _FUNCTION_ID.match(node.name)
            if match is not None:
                values[match.group("case")] = (path, node)
    return values


def _call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def _name_ids(node: ast.AST) -> frozenset[str]:
    return frozenset(item.id for item in ast.walk(node) if isinstance(item, ast.Name))


def _calls_in_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.Call]:
    calls: list[ast.Call] = []

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, item: ast.FunctionDef) -> None:
            if item is node:
                self.generic_visit(item)

        def visit_AsyncFunctionDef(self, item: ast.AsyncFunctionDef) -> None:
            if item is node:
                self.generic_visit(item)

        def visit_Call(self, item: ast.Call) -> None:
            calls.append(item)
            self.generic_visit(item)

    Visitor().visit(node)
    return calls


def _snapshot_target(call: ast.Call) -> tuple[str, frozenset[str]] | None:
    name = _call_name(call)
    if name == "write_json_result" and call.args:
        expression = call.args[0]
    elif name == "record_result" and len(call.args) >= 2:
        expression = ast.Tuple(elts=[call.args[0], call.args[1]], ctx=ast.Load())
    else:
        return None
    return ast.dump(expression, include_attributes=False), _name_ids(expression)


def _parent_map(node: ast.AST) -> dict[ast.AST, ast.AST]:
    return {child: parent for parent in ast.walk(node) for child in ast.iter_child_nodes(parent)}


def _ancestor_chain(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> tuple[ast.AST, ...]:
    values: list[ast.AST] = []
    current = parents.get(node)
    while current is not None:
        values.append(current)
        current = parents.get(current)
    return tuple(values)


def _if_branch(
    node: ast.AST,
    branch: ast.If,
    parents: dict[ast.AST, ast.AST],
) -> str | None:
    current = node
    while parents.get(current) is not branch:
        current = parents.get(current)
        if current is None:
            return None
    if current in branch.body:
        return "body"
    if current in branch.orelse:
        return "orelse"
    return None


def _mutually_exclusive(
    left: ast.AST,
    right: ast.AST,
    parents: dict[ast.AST, ast.AST],
) -> bool:
    right_ancestors = set(_ancestor_chain(right, parents))
    for ancestor in _ancestor_chain(left, parents):
        if not isinstance(ancestor, ast.If) or ancestor not in right_ancestors:
            continue
        if {
            _if_branch(left, ancestor, parents),
            _if_branch(right, ancestor, parents),
        } == {"body", "orelse"}:
            return True
    return False


def _assigned_names(node: ast.AST) -> frozenset[str]:
    return frozenset(
        item.id
        for item in ast.walk(node)
        if isinstance(item, ast.Name) and isinstance(item.ctx, ast.Store)
    )


def _snapshot_write_violations(
    path: Path,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[Violation]:
    parents = _parent_map(node)
    writes: list[tuple[ast.Call, str]] = []
    violations: list[Violation] = []
    for call in _calls_in_function(node):
        target = _snapshot_target(call)
        if target is None:
            continue
        target_key, target_names = target
        writes.append((call, target_key))
        loops = [
            ancestor
            for ancestor in _ancestor_chain(call, parents)
            if isinstance(ancestor, (ast.For, ast.AsyncFor, ast.While))
        ]
        if loops and all(not (target_names & _assigned_names(loop)) for loop in loops):
            violations.append(
                Violation(
                    path,
                    call.lineno,
                    "ETSPEC206",
                    f"{node.name} writes a loop-invariant snapshot target; "
                    "use Canonical Measurement/Observation or a loop-unique artifact path",
                )
            )

    by_target: dict[str, list[ast.Call]] = {}
    for call, target_key in writes:
        by_target.setdefault(target_key, []).append(call)
    for calls in by_target.values():
        if len(calls) < 2:
            continue
        conflicting = [
            (left, right)
            for index, left in enumerate(calls)
            for right in calls[index + 1 :]
            if not _mutually_exclusive(left, right, parents)
        ]
        if not conflicting:
            continue
        violations.append(
            Violation(
                path,
                min(call.lineno for pair in conflicting for call in pair),
                "ETSPEC205",
                f"{node.name} has multiple reachable publish sites for the same snapshot target; "
                "build one final snapshot and publish it once",
            )
        )
    return violations


def check_snapshot_writes(path: Path) -> list[Violation]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    violations: list[Violation] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
            "test_"
        ):
            violations.extend(_snapshot_write_violations(path, node))
    return sorted(set(violations))


def _observation_keys(spec: dict[str, Any]) -> tuple[str, ...]:
    observations = spec.get("failure_observations")
    if not isinstance(observations, list):
        return ()
    return tuple(
        str(item.get("key"))
        for item in observations
        if isinstance(item, dict) and isinstance(item.get("key"), str)
    )


def _semantic_observation_keys(spec: dict[str, Any]) -> frozenset[str]:
    observations = spec.get("failure_observations")
    if not isinstance(observations, list):
        return frozenset()
    return frozenset(
        str(item.get("key"))
        for item in observations
        if isinstance(item, dict)
        and isinstance(item.get("key"), str)
        and isinstance(item.get("semantic_ref"), str)
        and str(item.get("semantic_ref")).strip()
    )


def _expression_tokens(node: ast.AST) -> frozenset[str]:
    values: set[str] = set()

    class Visitor(ast.NodeVisitor):
        def visit_Attribute(self, item: ast.Attribute) -> None:
            values.add(ast.unparse(item))

        def visit_Name(self, item: ast.Name) -> None:
            values.add(item.id)

    Visitor().visit(node)
    return frozenset(values)


def _recorded_properties(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> dict[str, list[RecordedProperty]]:
    values: dict[str, list[RecordedProperty]] = {}
    for item in _calls_in_function(node):
        if not isinstance(item.func, ast.Name):
            continue
        if item.func.id == "record_property" and len(item.args) >= 2:
            key = item.args[0]
            value = item.args[1]
        elif item.func.id == "record_observation":
            keywords = {keyword.arg: keyword.value for keyword in item.keywords if keyword.arg}
            key = keywords.get("key")
            value = keywords.get("value")
            if key is None or value is None:
                continue
        else:
            continue
        if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
            continue
        values.setdefault(key.value, []).append(
            RecordedProperty(item.lineno, _expression_tokens(value), item.func.id)
        )
    return values


def _assertions(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[AssertionFact]:
    return [
        AssertionFact(item.lineno, _expression_tokens(item.test))
        for item in ast.walk(node)
        if isinstance(item, ast.Assert)
    ]


def _matching_assert_lines(
    records: list[RecordedProperty], assertions: list[AssertionFact]
) -> list[int]:
    record_tokens = set().union(*(record.tokens for record in records))
    if not record_tokens:
        return []
    scored = [
        (len(record_tokens & assertion.tokens), assertion.line)
        for assertion in assertions
        if record_tokens & assertion.tokens
    ]
    if not scored:
        return []
    best_score = max(score for score, _ in scored)
    return [line for score, line in scored if score == best_score]


def _check_spec(
    *,
    spec: dict[str, Any],
    functions: dict[str, tuple[Path, ast.FunctionDef | ast.AsyncFunctionDef]],
) -> list[Violation]:
    case_id = spec.get("case_id")
    if not isinstance(case_id, str):
        return []
    function = functions.get(case_id.lower())
    if function is None:
        return []
    gap = spec.get("gap")
    if isinstance(gap, list) and "case_measurement_gap" in gap:
        return []

    path, node = function
    keys = _observation_keys(spec)
    semantic_keys = _semantic_observation_keys(spec)
    recorded = _recorded_properties(node)
    assertions = _assertions(node)
    violations = _snapshot_write_violations(path, node)
    if not assertions:
        violations.append(
            Violation(path, node.lineno, "ETSPEC201", f"{case_id} has no final hardware assertion")
        )
        return violations

    last_assert = max(assertion.line for assertion in assertions)
    for key in keys:
        records = recorded.get(key, [])
        if not records:
            violations.append(
                Violation(
                    path,
                    node.lineno,
                    "ETSPEC202",
                    f"{case_id} does not record failure_observations key {key!r}",
                )
            )
            continue

        if key in semantic_keys and not any(
            record.api == "record_observation" for record in records
        ):
            violations.append(
                Violation(
                    path,
                    min(record.line for record in records),
                    "ETSPEC204",
                    f"{case_id} semantic observation {key!r} must use record_observation",
                )
            )

        matching_asserts = _matching_assert_lines(records, assertions)
        boundary = min(matching_asserts) if matching_asserts else last_assert
        if min(record.line for record in records) >= boundary:
            violations.append(
                Violation(
                    path,
                    min(record.line for record in records),
                    "ETSPEC203",
                    f"{case_id} records {key!r} only after its matching assertion boundary",
                )
            )
    return violations


def check_documents() -> list[Violation]:
    violations: list[Violation] = []
    cache: dict[str, dict[str, tuple[Path, ast.FunctionDef | ast.AsyncFunctionDef]]] = {}
    for document in _public_documents():
        for spec in _specs(document):
            case_id = spec.get("case_id")
            if not isinstance(case_id, str):
                continue
            match = _CASE_ID.fullmatch(case_id)
            if match is None:
                continue
            ip = match.group("ip").lower()
            functions = cache.setdefault(ip, _case_functions(ip))
            violations.extend(_check_spec(spec=spec, functions=functions))
    return sorted(set(violations))


def _parse_args() -> argparse.Namespace:
    return argparse.ArgumentParser(
        description="Check ET_CASE_SPEC observations, assertions and artifact snapshot lifecycle."
    ).parse_args()


def main() -> int:
    _parse_args()
    violations = check_documents()
    for violation in violations:
        print(violation.render(), file=sys.stderr)
    if violations:
        print(
            f"Case spec implementation check failed: {len(violations)} violation(s).",
            file=sys.stderr,
        )
        return 1
    print("Case spec implementation check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
