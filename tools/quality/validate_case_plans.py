#!/usr/bin/env python3
# Validate planning-only ET_CASE_PLAN blocks without pretending they are implemented Formal Cases.

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_PLAN_BEGIN = "<!-- ET_CASE_PLAN_BEGIN -->"
_PLAN_END = "<!-- ET_CASE_PLAN_END -->"
_SPEC_BEGIN = "<!-- ET_CASE_SPEC_BEGIN -->"
_PLAN_BLOCK = re.compile(
    rf"{re.escape(_PLAN_BEGIN)}\s*```yaml\s*(.*?)\s*```\s*{re.escape(_PLAN_END)}",
    re.DOTALL,
)
_SPEC_CASE_ID = re.compile(
    rf"{re.escape(_SPEC_BEGIN)}.*?case_id:\s*([A-Z][A-Z0-9_]*_P[0-3]_[0-9]{{3}})",
    re.DOTALL,
)
_FEATURE_TABLE_ROW = re.compile(
    r"^\|\s*([A-Z][A-Z0-9_]*_F_[0-9]{3})\s*\|",
    re.MULTILINE,
)
_CASE_ID = re.compile(r"^(?P<ip>[A-Z][A-Z0-9_]*)_P(?P<level>[0-3])_(?P<number>[0-9]{3})$")
_CJK = re.compile(r"[\u4e00-\u9fff]")
_REQUIRED_METHOD_LISTS = ("inputs", "steps", "observations", "pass_criteria")
_OBSERVATION_ROLES = frozenset({"config", "stimulus", "expected", "actual"})
_OBSERVATION_FORMATS = frozenset(
    {"text", "bool", "bit_bool", "decimal", "float", "hex8", "hex16", "hex32", "hex64", "bytes_hex"}
)
_RESOURCE_LEVELS = {f"R{index}": index for index in range(6)}
_SEMANTIC_REF = re.compile(
    r"^[a-z][a-z0-9_]*\.(?:feature|limit|option|interrupt|identity|parameter)\.[a-z][a-z0-9_]*$"
)


@dataclass(frozen=True, slots=True, order=True)
class PlanViolation:
    path: Path
    code: str
    message: str

    def render(self, root: Path) -> str:
        try:
            display = self.path.resolve().relative_to(root.resolve())
        except ValueError:
            display = self.path
        return f"{display}: {self.code} {self.message}"


def _non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _non_empty_string_list(value: object) -> bool:
    return (
        isinstance(value, list) and bool(value) and all(_non_empty_string(item) for item in value)
    )


def _load_plans(
    path: Path,
) -> tuple[list[dict[str, Any]], list[PlanViolation]]:
    text = path.read_text(encoding="utf-8-sig")
    matches = list(_PLAN_BLOCK.finditer(text))
    violations: list[PlanViolation] = []
    if text.count(_PLAN_BEGIN) != text.count(_PLAN_END) or text.count(_PLAN_BEGIN) != len(matches):
        return [], [
            PlanViolation(
                path,
                "ETPLAN101",
                "ET_CASE_PLAN markers or fenced YAML blocks are unbalanced",
            )
        ]

    plans: list[dict[str, Any]] = []
    for index, match in enumerate(matches, start=1):
        try:
            payload = yaml.safe_load(match.group(1))
        except yaml.YAMLError as exc:
            violations.append(
                PlanViolation(
                    path,
                    "ETPLAN102",
                    f"plan #{index} has invalid YAML: {exc}",
                )
            )
            continue
        if not isinstance(payload, dict):
            violations.append(
                PlanViolation(
                    path,
                    "ETPLAN103",
                    f"plan #{index} must decode to a mapping",
                )
            )
            continue
        plans.append(payload)
    return plans, violations


def _validate_identity(
    path: Path,
    plan: dict[str, Any],
    *,
    case_id: str,
    feature_ids: set[str],
) -> list[PlanViolation]:
    violations: list[PlanViolation] = []
    if plan.get("schema") != "et.case-plan.v1":
        violations.append(
            PlanViolation(path, "ETPLAN201", f"{case_id} schema must be et.case-plan.v1")
        )
    if plan.get("implementation_status") != "PLANNED":
        violations.append(
            PlanViolation(
                path,
                "ETPLAN202",
                f"{case_id} implementation_status must be PLANNED",
            )
        )

    match = _CASE_ID.fullmatch(case_id)
    if match is None:
        violations.append(
            PlanViolation(path, "ETPLAN203", f"invalid or missing Case ID {case_id!r}")
        )
    else:
        if match.group("ip").lower() != path.stem.lower():
            violations.append(
                PlanViolation(
                    path,
                    "ETPLAN204",
                    f"{case_id} does not belong to {path.stem}",
                )
            )
        if plan.get("p_level") != f"P{match.group('level')}":
            violations.append(
                PlanViolation(
                    path,
                    "ETPLAN205",
                    f"{case_id} p_level does not match Case ID",
                )
            )

    for field, code in (("case_name", "ETPLAN206"), ("report_feature", "ETPLAN207")):
        value = plan.get(field)
        if not _non_empty_string(value) or not _CJK.search(str(value)):
            violations.append(
                PlanViolation(
                    path,
                    code,
                    f"{case_id} {field} must be concrete Chinese text",
                )
            )

    feature_refs = plan.get("feature_refs")
    if not isinstance(feature_refs, list) or not all(
        _non_empty_string(item) for item in feature_refs
    ):
        violations.append(
            PlanViolation(path, "ETPLAN208", f"{case_id} feature_refs must be a list")
        )
    else:
        unknown = sorted(set(feature_refs) - feature_ids)
        if unknown:
            violations.append(
                PlanViolation(
                    path,
                    "ETPLAN209",
                    f"{case_id} references undefined Feature IDs: {', '.join(unknown)}",
                )
            )
    return violations


def _validate_method_contract(
    path: Path,
    plan: dict[str, Any],
    *,
    case_id: str,
) -> list[PlanViolation]:
    violations: list[PlanViolation] = []
    method = plan.get("method")
    if not isinstance(method, dict):
        violations.append(PlanViolation(path, "ETPLAN210", f"{case_id} method must be a mapping"))
    else:
        for field in _REQUIRED_METHOD_LISTS:
            if not _non_empty_string_list(method.get(field)):
                violations.append(
                    PlanViolation(
                        path,
                        "ETPLAN211",
                        f"{case_id} method.{field} must be a non-empty list",
                    )
                )

    if not _non_empty_string(plan.get("timeout")):
        violations.append(PlanViolation(path, "ETPLAN212", f"{case_id} timeout must be explicit"))
    cleanup = plan.get("cleanup")
    if not isinstance(cleanup, list) or not all(_non_empty_string(item) for item in cleanup):
        violations.append(
            PlanViolation(
                path,
                "ETPLAN213",
                f"{case_id} cleanup must be a string list",
            )
        )
    return violations


def _validate_resource_contract(
    path: Path,
    plan: dict[str, Any],
    *,
    case_id: str,
) -> list[PlanViolation]:
    violations: list[PlanViolation] = []
    resources = plan.get("resources")
    if not isinstance(resources, dict) or not all(
        _non_empty_string(resources.get(field))
        for field in ("minimum_level", "full_coverage_level", "board", "bench")
    ):
        violations.append(PlanViolation(path, "ETPLAN214", f"{case_id} resources are incomplete"))
    else:
        minimum_level = str(resources["minimum_level"])
        full_coverage_level = str(resources["full_coverage_level"])
        if (
            minimum_level not in _RESOURCE_LEVELS
            or full_coverage_level not in _RESOURCE_LEVELS
            or _RESOURCE_LEVELS.get(minimum_level, 99)
            > _RESOURCE_LEVELS.get(full_coverage_level, -1)
        ):
            violations.append(
                PlanViolation(
                    path,
                    "ETPLAN222",
                    f"{case_id} resource levels must be R0..R5 with minimum <= full coverage",
                )
            )
    if not _non_empty_string_list(plan.get("backend")):
        violations.append(PlanViolation(path, "ETPLAN215", f"{case_id} backend must be non-empty"))
    if not _non_empty_string_list(plan.get("evidence")):
        violations.append(PlanViolation(path, "ETPLAN216", f"{case_id} evidence must be non-empty"))
    failure_observations = plan.get("failure_observations")
    if not isinstance(failure_observations, list) or not failure_observations:
        violations.append(
            PlanViolation(
                path,
                "ETPLAN217",
                f"{case_id} failure_observations must be non-empty",
            )
        )
    else:
        for entry in failure_observations:
            if not isinstance(entry, dict):
                continue
            role = entry.get("role")
            format_name = entry.get("format")
            semantic_ref = entry.get("semantic_ref")
            if role is None:
                violations.append(
                    PlanViolation(path, "ETPLAN219", f"{case_id} observation role is required")
                )
            elif role not in _OBSERVATION_ROLES:
                violations.append(
                    PlanViolation(path, "ETPLAN219", f"{case_id} observation role is invalid")
                )
            if format_name is None:
                violations.append(
                    PlanViolation(path, "ETPLAN220", f"{case_id} observation format is required")
                )
            elif format_name not in _OBSERVATION_FORMATS:
                violations.append(
                    PlanViolation(path, "ETPLAN220", f"{case_id} observation format is invalid")
                )
            if semantic_ref is not None and (
                not _non_empty_string(semantic_ref)
                or _SEMANTIC_REF.fullmatch(str(semantic_ref)) is None
            ):
                violations.append(
                    PlanViolation(path, "ETPLAN221", f"{case_id} semantic_ref is invalid")
                )
    if not isinstance(plan.get("gap"), list):
        violations.append(PlanViolation(path, "ETPLAN218", f"{case_id} gap must be a list"))
    return violations


def _validate_plan(
    path: Path,
    plan: dict[str, Any],
    feature_ids: set[str],
) -> list[PlanViolation]:
    raw_case_id = plan.get("case_id")
    case_id = str(raw_case_id) if raw_case_id is not None else "<missing>"
    violations = _validate_identity(
        path,
        plan,
        case_id=case_id,
        feature_ids=feature_ids,
    )
    violations.extend(_validate_method_contract(path, plan, case_id=case_id))
    violations.extend(_validate_resource_contract(path, plan, case_id=case_id))
    return violations


def validate_document(path: Path, *, root: Path) -> list[PlanViolation]:
    text = path.read_text(encoding="utf-8-sig")
    plans, violations = _load_plans(path)
    if not plans and _PLAN_BEGIN not in text:
        return violations

    feature_ids = set(_FEATURE_TABLE_ROW.findall(text))
    if not feature_ids:
        violations.append(
            PlanViolation(
                path,
                "ETPLAN301",
                "no Feature IDs were found in Markdown tables",
            )
        )
    spec_ids = {value.lower() for value in _SPEC_CASE_ID.findall(text)}
    seen: set[str] = set()
    for plan in plans:
        violations.extend(_validate_plan(path, plan, feature_ids))
        case_id = str(plan.get("case_id") or "").lower()
        if case_id in seen:
            violations.append(PlanViolation(path, "ETPLAN302", f"duplicate plan Case ID {case_id}"))
        seen.add(case_id)
        if case_id in spec_ids:
            violations.append(
                PlanViolation(
                    path,
                    "ETPLAN303",
                    f"{case_id} exists as both PLAN and SPEC",
                )
            )

    registry = root / "pc/et_test_platform/test_cases" / path.stem.lower() / "case_registry.py"
    if registry.is_file():
        registry_text = registry.read_text(encoding="utf-8-sig")
        registered = set(re.findall(r'"([a-z][a-z0-9_]*_p[0-3]_[0-9]{3})"', registry_text))
        overlap = sorted(registered & seen)
        if overlap:
            violations.append(
                PlanViolation(
                    path,
                    "ETPLAN304",
                    "registered Case IDs must be SPEC, not PLAN: " + ", ".join(overlap),
                )
            )
    return sorted(set(violations))


def discover_plan_documents(root: Path) -> tuple[Path, ...]:
    documents = []
    document_root = root / "test_case_doc"
    for path in sorted(document_root.rglob("*.md")):
        is_public_contract = path.parent != document_root and path.stem == path.parent.name
        if not is_public_contract:
            continue
        text = path.read_text(encoding="utf-8-sig")
        if _PLAN_BEGIN in text and _FEATURE_TABLE_ROW.search(text):
            documents.append(path)
    return tuple(documents)


def validate_paths(paths: Iterable[Path], *, root: Path) -> list[PlanViolation]:
    violations: list[PlanViolation] = []
    for path in paths:
        resolved = path if path.is_absolute() else root / path
        violations.extend(validate_document(resolved, root=root))
    return sorted(set(violations))


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate planning-only ET_CASE_PLAN Markdown blocks."
    )
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--root", type=Path, default=REPOSITORY_ROOT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    root = args.root.resolve()
    paths = tuple(args.paths) if args.paths else discover_plan_documents(root)
    if not paths:
        print("No ET_CASE_PLAN documents found.")
        return 0
    violations = validate_paths(paths, root=root)
    if violations:
        for violation in violations:
            print(violation.render(root), file=sys.stderr)
        print(
            f"Case plan validation failed: {len(violations)} violation(s).",
            file=sys.stderr,
        )
        return 1
    print(f"Case plan validation passed: {len(paths)} document(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
