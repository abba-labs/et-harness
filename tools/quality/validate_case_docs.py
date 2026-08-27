#!/usr/bin/env python3
# Validate machine-readable Formal Case specifications against Registry and source code.

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

_SPEC_BEGIN = "<!-- ET_CASE_SPEC_BEGIN -->"
_SPEC_END = "<!-- ET_CASE_SPEC_END -->"
_REPORT_BEGIN = "<!-- ET_CASE_REPORT_BEGIN -->"
_REPORT_END = "<!-- ET_CASE_REPORT_END -->"
_SPEC_BLOCK = re.compile(
    rf"{re.escape(_SPEC_BEGIN)}\s*```yaml\s*(.*?)\s*```\s*{re.escape(_SPEC_END)}",
    re.DOTALL,
)
_FEATURE_TABLE_ROW = re.compile(r"^\|\s*([A-Z][A-Z0-9_]*_F_[0-9]{3})\s*\|", re.MULTILINE)
_CASE_ID = re.compile(r"^(?P<ip>[A-Z][A-Z0-9_]*)_P(?P<level>[0-3])_(?P<number>[0-9]{3})$")
_CASE_FUNCTION = re.compile(r"^test_(?P<case_id>[a-z][a-z0-9_]*?_p[0-3]_[0-9]{3})(?:_|$)")
_CJK = re.compile(r"[\u4e00-\u9fff]")
_REQUIRED_METHOD_LISTS = ("inputs", "steps", "observations", "pass_criteria")
_OBSERVATION_ROLES = frozenset({"config", "stimulus", "expected", "actual"})
_OBSERVATION_FORMATS = frozenset(
    {
        "text",
        "bool",
        "bit_bool",
        "decimal",
        "float",
        "count",
        "hex8",
        "hex16",
        "hex32",
        "hex64",
        "bytes_hex",
    }
)
_RESOURCE_LEVELS = {f"R{index}": index for index in range(6)}
_REPORT_BLOCK = re.compile(
    rf"{re.escape(_REPORT_BEGIN)}\s*```yaml\s*(.*?)\s*```\s*{re.escape(_REPORT_END)}",
    re.DOTALL,
)
_SEMANTIC_REF = re.compile(
    r"^[a-z][a-z0-9_]*\.(?:feature|limit|option|interrupt|identity|parameter)\.[a-z][a-z0-9_]*$"
)


@dataclass(frozen=True, slots=True, order=True)
class CaseDocViolation:
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


def _document_ip(path: Path) -> str:
    return path.stem.lower()


def _feature_ids(document: str) -> set[str]:
    return set(_FEATURE_TABLE_ROW.findall(document))


def _load_spec_blocks(path: Path) -> tuple[list[dict[str, Any]], list[CaseDocViolation]]:
    text = path.read_text(encoding="utf-8-sig")
    violations: list[CaseDocViolation] = []
    matches = list(_SPEC_BLOCK.finditer(text))
    if text.count(_SPEC_BEGIN) != text.count(_SPEC_END) or text.count(_SPEC_BEGIN) != len(matches):
        violations.append(
            CaseDocViolation(
                path,
                "ETCASE101",
                "ET_CASE_SPEC begin/end markers or fenced YAML blocks are not balanced",
            )
        )
        return [], violations

    specs: list[dict[str, Any]] = []
    for index, match in enumerate(matches, start=1):
        try:
            payload = yaml.safe_load(match.group(1))
        except yaml.YAMLError as exc:
            violations.append(
                CaseDocViolation(path, "ETCASE102", f"spec #{index} contains invalid YAML: {exc}")
            )
            continue
        if not isinstance(payload, dict):
            violations.append(
                CaseDocViolation(path, "ETCASE103", f"spec #{index} must decode to a mapping")
            )
            continue
        specs.append(payload)
    return specs, violations


def _validate_report_notes(
    path: Path,
    document: str,
    case_ids: set[str],
) -> list[CaseDocViolation]:
    violations: list[CaseDocViolation] = []
    matches = list(_REPORT_BLOCK.finditer(document))
    if document.count(_REPORT_BEGIN) != document.count(_REPORT_END) or len(matches) > 1:
        return [
            CaseDocViolation(
                path,
                "ETCASE601",
                "document may contain at most one balanced ET_CASE_REPORT YAML block",
            )
        ]
    if not matches:
        return [
            CaseDocViolation(
                path,
                "ETCASE600",
                "Formal Case document must define one complete ET_CASE_REPORT block",
            )
        ]
    try:
        payload = yaml.safe_load(matches[0].group(1))
    except yaml.YAMLError as exc:
        return [CaseDocViolation(path, "ETCASE602", f"ET_CASE_REPORT YAML is invalid: {exc}")]
    if not isinstance(payload, dict) or payload.get("schema") != "et.case-report-note.v1":
        return [
            CaseDocViolation(
                path, "ETCASE603", "ET_CASE_REPORT schema must be et.case-report-note.v1"
            )
        ]
    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, dict) or set(raw_cases) != case_ids:
        return [
            CaseDocViolation(
                path,
                "ETCASE604",
                "ET_CASE_REPORT Case IDs must exactly match ET_CASE_SPEC Case IDs",
            )
        ]
    for case_id, note in raw_cases.items():
        violations.extend(_validate_report_note(path, str(case_id), note))
    return violations


def _validate_report_note(
    path: Path,
    case_id: str,
    note: object,
) -> list[CaseDocViolation]:
    if not isinstance(note, dict) or not _non_empty_string(note.get("summary")):
        return [CaseDocViolation(path, "ETCASE605", f"{case_id} report summary is required")]
    violations: list[CaseDocViolation] = []
    summary = str(note["summary"])
    if not _readable_chinese(summary):
        violations.append(
            CaseDocViolation(
                path,
                "ETCASE606",
                f"{case_id} report summary must be readable Chinese text",
            )
        )
    fields = note.get("fields")
    if not isinstance(fields, list) or not 1 <= len(fields) <= 4:
        violations.append(
            CaseDocViolation(
                path, "ETCASE607", f"{case_id} report fields must contain 1..4 entries"
            )
        )
        return violations
    for field in fields:
        violations.extend(_validate_report_field(path, case_id, field))
    return violations


def _validate_report_field(
    path: Path,
    case_id: str,
    field: object,
) -> list[CaseDocViolation]:
    if not isinstance(field, dict):
        return [CaseDocViolation(path, "ETCASE608", f"{case_id} report field must be a mapping")]
    violations: list[CaseDocViolation] = []
    if field.get("source") not in {"artifact", "measurement", "observation"}:
        violations.append(
            CaseDocViolation(path, "ETCASE609", f"{case_id} report field source is invalid")
        )
    if not _non_empty_string(field.get("path")) or not _non_empty_string(field.get("label")):
        violations.append(
            CaseDocViolation(path, "ETCASE610", f"{case_id} report field path/label is required")
        )
    label = str(field.get("label") or "")
    if label and not _readable_chinese(label):
        violations.append(
            CaseDocViolation(
                path,
                "ETCASE611",
                f"{case_id} report field label must be readable Chinese text",
            )
        )
    if field.get("format", "text") not in _OBSERVATION_FORMATS:
        violations.append(
            CaseDocViolation(path, "ETCASE612", f"{case_id} report field format is invalid")
        )
    if field.get("aggregate", "same") not in {"same", "all", "range", "distinct"}:
        violations.append(
            CaseDocViolation(path, "ETCASE613", f"{case_id} report field aggregate is invalid")
        )
    return violations


def _readable_chinese(value: str) -> bool:
    return bool(_CJK.search(value)) and "?" not in value and "\ufffd" not in value


def _registry_case_ids(path: Path) -> tuple[set[str], list[CaseDocViolation]]:
    violations: list[CaseDocViolation] = []
    if not path.is_file():
        return set(), [CaseDocViolation(path, "ETCASE201", "case_registry.py is missing")]
    source = path.read_text(encoding="utf-8-sig")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return set(), [CaseDocViolation(path, "ETCASE202", f"registry syntax error: {exc}")]

    assignments: list[tuple[str, ...]] = []
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        target = node.target if isinstance(node, ast.AnnAssign) else node.targets[0]
        if not isinstance(target, ast.Name) or not target.id.endswith("_CASE_REGISTRY"):
            continue
        try:
            value = ast.literal_eval(node.value)
        except (ValueError, TypeError):
            violations.append(
                CaseDocViolation(path, "ETCASE203", f"{target.id} must be a literal tuple/list")
            )
            continue
        if not isinstance(value, (tuple, list)) or not all(isinstance(item, str) for item in value):
            violations.append(
                CaseDocViolation(
                    path, "ETCASE204", f"{target.id} must contain only stable Case IDs"
                )
            )
            continue
        assignments.append(tuple(value))

    if len(assignments) != 1:
        violations.append(
            CaseDocViolation(
                path,
                "ETCASE205",
                f"expected exactly one *_CASE_REGISTRY assignment, found {len(assignments)}",
            )
        )
        return set(), violations
    values = assignments[0]
    if len(set(values)) != len(values):
        violations.append(
            CaseDocViolation(path, "ETCASE206", "registry contains duplicate Case IDs")
        )
    return set(values), violations


def _implemented_case_ids(package: Path) -> tuple[set[str], list[CaseDocViolation]]:
    locations: dict[str, list[str]] = {}
    violations: list[CaseDocViolation] = []
    for path in sorted(package.glob("test_*_p*.py")):
        source = path.read_text(encoding="utf-8-sig")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            violations.append(CaseDocViolation(path, "ETCASE301", f"Case syntax error: {exc}"))
            continue
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not node.name.startswith("test_"):
                continue
            match = _CASE_FUNCTION.match(node.name)
            if match is None:
                continue
            case_id = match.group("case_id")
            locations.setdefault(case_id, []).append(f"{path.name}:{node.lineno}")

    for case_id, definitions in sorted(locations.items()):
        if len(definitions) > 1:
            violations.append(
                CaseDocViolation(
                    package,
                    "ETCASE302",
                    f"{case_id} has multiple source implementations: {', '.join(definitions)}",
                )
            )
    return set(locations), violations


# 提取字面量字典字段；只校验稳定字段名，不解释任何 IP 语义。
def _literal_dict_paths(node: ast.Dict) -> set[str]:
    paths: set[str] = set()
    for key, value in zip(node.keys, node.values, strict=True):
        if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
            continue
        key_name = key.value
        paths.add(key_name)
        if not isinstance(value, ast.Dict):
            paths.add(f"{key_name}.*")
            continue
        child_paths = _literal_dict_paths(value)
        if child_paths:
            for child in child_paths:
                paths.add(f"{key_name}.{child}")
        else:
            paths.add(f"{key_name}.*")
    return paths


# to_measurements() 的来源若为本函数内的轻量结果对象，则提取其构造参数名。
def _measurement_object_paths(function: ast.FunctionDef, variable_name: str) -> set[str]:
    for node in ast.walk(function):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == variable_name for target in node.targets
        ):
            continue
        return {keyword.arg for keyword in node.value.keywords if keyword.arg is not None}
    return set()


def _parameter_names(function: ast.FunctionDef) -> frozenset[str]:
    names: set[str] = set()
    for decorator in function.decorator_list:
        if not isinstance(decorator, ast.Call) or not decorator.args:
            continue
        if not isinstance(decorator.func, ast.Attribute) or decorator.func.attr != "parametrize":
            continue
        argument_names = decorator.args[0]
        if isinstance(argument_names, ast.Constant) and isinstance(argument_names.value, str):
            names.update(item.strip() for item in argument_names.value.split(",") if item.strip())
    return frozenset(names)


def _call_report_paths(
    call: ast.Call,
    *,
    function: ast.FunctionDef,
    measurement_paths: set[str],
) -> dict[str, set[str]]:
    values: dict[str, set[str]] = {
        "artifact": set(),
        "measurement": set(),
        "observation": set(),
    }
    if not isinstance(call.func, ast.Name):
        return values

    if call.func.id == "record_property" and len(call.args) >= 2:
        key = call.args[0]
        if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
            return values
        values["measurement"].add(key.value)
        if isinstance(call.args[1], ast.Dict):
            values["measurement"].update(
                f"{key.value}.{path}" for path in _literal_dict_paths(call.args[1])
            )
        else:
            values["measurement"].add(f"{key.value}.*")
        return values

    if call.func.id == "record_observation":
        keywords = {keyword.arg: keyword.value for keyword in call.keywords if keyword.arg}
        key = keywords.get("key")
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            values["observation"].add(key.value)
        return values

    if call.func.id == "record_result":
        for keyword in call.keywords:
            if keyword.arg is None:
                continue
            values["artifact"].add(keyword.arg)
            if isinstance(keyword.value, ast.Dict):
                values["artifact"].update(
                    f"{keyword.arg}.{path}" for path in _literal_dict_paths(keyword.value)
                )
            else:
                values["artifact"].add(f"{keyword.arg}.*")
        return values

    if call.func.id != "write_json_result" or len(call.args) < 2:
        return values
    payload = call.args[1]
    if isinstance(payload, ast.Dict):
        values["artifact"].update(_literal_dict_paths(payload))
    elif (
        isinstance(payload, ast.Call)
        and isinstance(payload.func, ast.Attribute)
        and payload.func.attr == "to_measurements"
    ):
        values["artifact"].update(measurement_paths)
        if isinstance(payload.func.value, ast.Name):
            values["artifact"].update(_measurement_object_paths(function, payload.func.value.id))
    return values


def _path_is_available(field_path: str, available: set[str]) -> bool:
    if field_path in available:
        return True
    segments = field_path.split(".")
    return any(f"{'.'.join(segments[:index])}.*" in available for index in range(1, len(segments)))


def _branch_records_path(
    statements: list[ast.stmt],
    *,
    function: ast.FunctionDef,
    source: str,
    field_path: str,
    measurement_paths: set[str],
) -> bool:
    return any(
        _path_is_available(
            field_path,
            _call_report_paths(
                call,
                function=function,
                measurement_paths=measurement_paths,
            )[source],
        )
        for statement in statements
        for call in (node for node in ast.walk(statement) if isinstance(node, ast.Call))
    )


def _parameter_branch_incomplete(
    function: ast.FunctionDef,
    *,
    source: str,
    field_path: str,
    measurement_paths: set[str],
) -> bool:
    parameter_names = _parameter_names(function)
    if not parameter_names:
        return False
    parents = {
        child: parent for parent in ast.walk(function) for child in ast.iter_child_nodes(parent)
    }
    matching_calls = [
        call
        for call in ast.walk(function)
        if isinstance(call, ast.Call)
        and _path_is_available(
            field_path,
            _call_report_paths(
                call,
                function=function,
                measurement_paths=measurement_paths,
            )[source],
        )
    ]
    if not matching_calls:
        return False

    parameter_branches: set[ast.If] = set()
    for call in matching_calls:
        current = parents.get(call)
        conditional = False
        while current is not None and current is not function:
            if isinstance(current, ast.If) and parameter_names & {
                node.id for node in ast.walk(current.test) if isinstance(node, ast.Name)
            }:
                parameter_branches.add(current)
                conditional = True
            current = parents.get(current)
        if not conditional:
            return False

    return any(
        not branch.orelse
        or not _branch_records_path(
            branch.body,
            function=function,
            source=source,
            field_path=field_path,
            measurement_paths=measurement_paths,
        )
        or not _branch_records_path(
            branch.orelse,
            function=function,
            source=source,
            field_path=field_path,
            measurement_paths=measurement_paths,
        )
        for branch in parameter_branches
    )


def _case_report_paths(
    package: Path,
) -> tuple[dict[str, dict[str, set[str]]], dict[str, dict[str, set[str]]]]:
    available: dict[str, dict[str, set[str]]] = {}
    parameter_incomplete: dict[str, dict[str, set[str]]] = {}
    for path in sorted(package.glob("test_*_p*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except SyntaxError:
            continue
        measurement_paths: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
                measurement_paths.update(_literal_dict_paths(node.value))
        for function in (node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)):
            match = _CASE_FUNCTION.match(function.name)
            if match is None:
                continue
            case_id = match.group("case_id").upper()
            sources = available.setdefault(
                case_id,
                {"artifact": set(), "measurement": set(), "observation": set()},
            )
            incomplete = parameter_incomplete.setdefault(
                case_id,
                {"artifact": set(), "measurement": set(), "observation": set()},
            )
            for call in (node for node in ast.walk(function) if isinstance(node, ast.Call)):
                for source, paths in _call_report_paths(
                    call,
                    function=function,
                    measurement_paths=measurement_paths,
                ).items():
                    sources[source].update(paths)
            for source, paths in sources.items():
                for field_path in paths:
                    if _parameter_branch_incomplete(
                        function,
                        source=source,
                        field_path=field_path,
                        measurement_paths=measurement_paths,
                    ):
                        incomplete[source].add(field_path)
    return available, parameter_incomplete


# 把三类报告字段绑定到Case真实记录点，并拒绝仅由部分参数分支产生的公共字段。
def _validate_report_implementation_bindings(
    path: Path,
    document: str,
    available: dict[str, dict[str, set[str]]],
    parameter_incomplete: dict[str, dict[str, set[str]]],
) -> list[CaseDocViolation]:
    match = _REPORT_BLOCK.search(document)
    if match is None:
        return []
    try:
        payload = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return []
    raw_cases = payload.get("cases") if isinstance(payload, dict) else None
    if not isinstance(raw_cases, dict):
        return []
    violations: list[CaseDocViolation] = []
    for case_id, note in raw_cases.items():
        fields = note.get("fields") if isinstance(note, dict) else None
        if not isinstance(fields, list):
            continue
        case_sources = available.get(str(case_id), {})
        incomplete_sources = parameter_incomplete.get(str(case_id), {})
        for field in fields:
            if not isinstance(field, dict):
                continue
            source = str(field.get("source") or "")
            field_path = str(field.get("path") or "")
            if not _path_is_available(field_path, case_sources.get(source, set())):
                code = "ETCASE614" if source == "artifact" else "ETCASE615"
                violations.append(
                    CaseDocViolation(
                        path,
                        code,
                        f"{case_id} {source} report path is not written by the Case: {field_path}",
                    )
                )
                continue
            if _path_is_available(field_path, incomplete_sources.get(source, set())):
                violations.append(
                    CaseDocViolation(
                        path,
                        "ETCASE616",
                        f"{case_id} {source} report path is not produced by every parameter branch: "
                        f"{field_path}",
                    )
                )
    return violations


def _validate_failure_observations(
    path: Path,
    case_id: str,
    value: object,
) -> list[CaseDocViolation]:
    violations: list[CaseDocViolation] = []
    if not isinstance(value, list) or not value:
        return [
            CaseDocViolation(
                path,
                "ETCASE421",
                f"{case_id} failure_observations must be a non-empty list",
            )
        ]

    keys: set[str] = set()
    has_hardware_fact = False
    for entry in value:
        if not isinstance(entry, dict):
            violations.append(
                CaseDocViolation(
                    path, "ETCASE422", f"{case_id} has non-mapping failure observation"
                )
            )
            continue
        key = entry.get("key")
        label = entry.get("label")
        source = entry.get("source")
        if (
            not _non_empty_string(key)
            or not _non_empty_string(label)
            or not _non_empty_string(source)
        ):
            violations.append(
                CaseDocViolation(
                    path,
                    "ETCASE423",
                    f"{case_id} failure observation requires non-empty key/label/source",
                )
            )
            continue
        key_string = str(key)
        if key_string in keys:
            violations.append(
                CaseDocViolation(
                    path,
                    "ETCASE424",
                    f"{case_id} duplicates failure observation key {key_string!r}",
                )
            )
        keys.add(key_string)
        if source in {"dut", "peer", "fpga", "instrument", "observer"}:
            has_hardware_fact = True

        role = entry.get("role")
        format_name = entry.get("format")
        semantic_ref = entry.get("semantic_ref")
        unit = entry.get("unit")
        if role is None:
            violations.append(
                CaseDocViolation(path, "ETCASE426", f"{case_id} observation role is required")
            )
        elif role not in _OBSERVATION_ROLES:
            violations.append(
                CaseDocViolation(
                    path, "ETCASE426", f"{case_id} observation role is invalid: {role!r}"
                )
            )
        if format_name is None:
            violations.append(
                CaseDocViolation(path, "ETCASE427", f"{case_id} observation format is required")
            )
        elif format_name not in _OBSERVATION_FORMATS:
            violations.append(
                CaseDocViolation(
                    path, "ETCASE427", f"{case_id} observation format is invalid: {format_name!r}"
                )
            )
        if semantic_ref is not None and (
            not _non_empty_string(semantic_ref)
            or _SEMANTIC_REF.fullmatch(str(semantic_ref)) is None
        ):
            violations.append(
                CaseDocViolation(
                    path,
                    "ETCASE428",
                    f"{case_id} observation semantic_ref is invalid: {semantic_ref!r}",
                )
            )
        if unit is not None and not _non_empty_string(unit):
            violations.append(
                CaseDocViolation(path, "ETCASE429", f"{case_id} observation unit must be non-empty")
            )

    if not has_hardware_fact:
        violations.append(
            CaseDocViolation(
                path,
                "ETCASE425",
                f"{case_id} failure_observations must include at least one DUT/observer hardware fact",
            )
        )
    return violations


def _validate_identity(
    path: Path,
    spec: dict[str, Any],
    *,
    case_id: str,
    document_ip: str,
    feature_ids: set[str],
) -> list[CaseDocViolation]:
    violations: list[CaseDocViolation] = []
    if spec.get("schema") != "et.case.v1":
        violations.append(
            CaseDocViolation(path, "ETCASE401", f"{case_id} schema must be et.case.v1")
        )

    match = _CASE_ID.fullmatch(case_id)
    if match is None:
        violations.append(
            CaseDocViolation(path, "ETCASE402", f"invalid or missing Case ID {case_id!r}")
        )
    else:
        if match.group("ip").lower() != document_ip:
            violations.append(
                CaseDocViolation(
                    path,
                    "ETCASE403",
                    f"{case_id} does not belong to document IP {document_ip}",
                )
            )
        expected_level = f"P{match.group('level')}"
        if spec.get("p_level") != expected_level:
            violations.append(
                CaseDocViolation(path, "ETCASE404", f"{case_id} p_level must be {expected_level}")
            )

    case_name = spec.get("case_name")
    report_feature = spec.get("report_feature")
    if not _non_empty_string(case_name) or not _CJK.search(str(case_name)):
        violations.append(
            CaseDocViolation(
                path, "ETCASE405", f"{case_id} case_name must be a concrete Chinese name"
            )
        )
    if not _non_empty_string(report_feature) or not _CJK.search(str(report_feature)):
        violations.append(
            CaseDocViolation(
                path,
                "ETCASE406",
                f"{case_id} report_feature must be a concrete Chinese capability description",
            )
        )
    elif "_F_" in str(report_feature) or re.search(r"\bF[0-9]{3}\b", str(report_feature)):
        violations.append(
            CaseDocViolation(
                path,
                "ETCASE407",
                f"{case_id} report_feature must not expose internal Feature IDs",
            )
        )

    feature_refs = spec.get("feature_refs")
    if not isinstance(feature_refs, list) or not all(
        _non_empty_string(item) for item in feature_refs
    ):
        violations.append(
            CaseDocViolation(
                path, "ETCASE408", f"{case_id} feature_refs must be a list of Feature IDs"
            )
        )
    else:
        unknown = sorted(set(feature_refs) - feature_ids)
        if unknown:
            violations.append(
                CaseDocViolation(
                    path,
                    "ETCASE409",
                    f"{case_id} references undefined Feature IDs: {', '.join(unknown)}",
                )
            )
    return violations


def _validate_method(
    path: Path,
    spec: dict[str, Any],
    *,
    case_id: str,
) -> list[CaseDocViolation]:
    method = spec.get("method")
    if not isinstance(method, dict):
        return [CaseDocViolation(path, "ETCASE410", f"{case_id} method must be a mapping")]

    violations: list[CaseDocViolation] = []
    for field in _REQUIRED_METHOD_LISTS:
        if not _non_empty_string_list(method.get(field)):
            violations.append(
                CaseDocViolation(
                    path,
                    "ETCASE411",
                    f"{case_id} method.{field} must be a non-empty list of steps/facts",
                )
            )
    return violations


def _validate_execution_contract(
    path: Path,
    spec: dict[str, Any],
    *,
    case_id: str,
) -> list[CaseDocViolation]:
    violations: list[CaseDocViolation] = []
    if not _non_empty_string(spec.get("timeout")):
        violations.append(
            CaseDocViolation(path, "ETCASE412", f"{case_id} timeout must be explicit")
        )

    cleanup = spec.get("cleanup")
    if not isinstance(cleanup, list) or not all(_non_empty_string(item) for item in cleanup):
        violations.append(
            CaseDocViolation(
                path, "ETCASE413", f"{case_id} cleanup must be a list of explicit actions"
            )
        )

    resources = spec.get("resources")
    resource_fields = ("minimum_level", "full_coverage_level", "board", "bench")
    if not isinstance(resources, dict) or not all(
        _non_empty_string(resources.get(field)) for field in resource_fields
    ):
        violations.append(
            CaseDocViolation(
                path, "ETCASE414", f"{case_id} resources must define level/board/bench facts"
            )
        )
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
                CaseDocViolation(
                    path,
                    "ETCASE418",
                    f"{case_id} resource levels must be R0..R5 with minimum <= full coverage",
                )
            )
    if not _non_empty_string_list(spec.get("backend")):
        violations.append(
            CaseDocViolation(path, "ETCASE415", f"{case_id} backend must be non-empty")
        )
    if not _non_empty_string_list(spec.get("evidence")):
        violations.append(
            CaseDocViolation(path, "ETCASE416", f"{case_id} evidence must be non-empty")
        )
    if not isinstance(spec.get("gap"), list):
        violations.append(CaseDocViolation(path, "ETCASE417", f"{case_id} gap must be a list"))
    return violations


def _validate_spec(
    path: Path,
    spec: dict[str, Any],
    *,
    document_ip: str,
    feature_ids: set[str],
) -> list[CaseDocViolation]:
    raw_case_id = spec.get("case_id")
    case_id = str(raw_case_id) if raw_case_id is not None else "<missing>"
    violations = _validate_identity(
        path,
        spec,
        case_id=case_id,
        document_ip=document_ip,
        feature_ids=feature_ids,
    )
    violations.extend(_validate_method(path, spec, case_id=case_id))
    violations.extend(_validate_execution_contract(path, spec, case_id=case_id))
    violations.extend(
        _validate_failure_observations(path, case_id, spec.get("failure_observations"))
    )
    return violations


def validate_document(path: Path, *, root: Path) -> list[CaseDocViolation]:
    if not path.is_file():
        return [
            CaseDocViolation(
                path,
                "ETCASE001",
                "registered Formal IP package is missing its public Case document",
            )
        ]
    text = path.read_text(encoding="utf-8-sig")
    specs, violations = _load_spec_blocks(path)
    if not specs and _SPEC_BEGIN not in text:
        return violations

    document_ip = _document_ip(path)
    package = root / "pc/et_test_platform/test_cases" / document_ip
    registry_ids, registry_violations = _registry_case_ids(package / "case_registry.py")
    implemented_ids, implementation_violations = _implemented_case_ids(package)
    violations.extend(registry_violations)
    violations.extend(implementation_violations)

    feature_ids = _feature_ids(text)
    if not feature_ids:
        violations.append(
            CaseDocViolation(path, "ETCASE501", "no Feature IDs were found in Markdown table rows")
        )

    spec_ids: list[str] = []
    for spec in specs:
        violations.extend(
            _validate_spec(path, spec, document_ip=document_ip, feature_ids=feature_ids)
        )
        raw_case_id = spec.get("case_id")
        if isinstance(raw_case_id, str) and _CASE_ID.fullmatch(raw_case_id):
            spec_ids.append(raw_case_id.lower())

    if len(set(spec_ids)) != len(spec_ids):
        violations.append(CaseDocViolation(path, "ETCASE502", "duplicate ET_CASE_SPEC Case IDs"))
    spec_set = set(spec_ids)
    violations.extend(
        _validate_report_notes(
            path,
            text,
            {str(spec.get("case_id")) for spec in specs if isinstance(spec.get("case_id"), str)},
        )
    )
    report_paths, parameter_incomplete = _case_report_paths(package)
    violations.extend(
        _validate_report_implementation_bindings(
            path,
            text,
            report_paths,
            parameter_incomplete,
        )
    )
    if spec_set != registry_ids:
        missing_specs = sorted(registry_ids - spec_set)
        unregistered_specs = sorted(spec_set - registry_ids)
        details: list[str] = []
        if missing_specs:
            details.append("registered without spec=" + ",".join(missing_specs))
        if unregistered_specs:
            details.append("spec not registered=" + ",".join(unregistered_specs))
        violations.append(CaseDocViolation(path, "ETCASE503", "; ".join(details)))

    if registry_ids != implemented_ids:
        missing_functions = sorted(registry_ids - implemented_ids)
        unregistered_functions = sorted(implemented_ids - registry_ids)
        details = []
        if missing_functions:
            details.append("registered without function=" + ",".join(missing_functions))
        if unregistered_functions:
            details.append("function not registered=" + ",".join(unregistered_functions))
        violations.append(CaseDocViolation(path, "ETCASE504", "; ".join(details)))
    return violations


def discover_case_documents(*, root: Path) -> tuple[Path, ...]:
    case_root = root / "pc/et_test_platform/test_cases"
    documents: list[Path] = []
    for package in sorted(path for path in case_root.iterdir() if path.is_dir()):
        if not (package / "case_registry.py").is_file():
            continue
        document = root / "test_case_doc" / package.name / f"{package.name}.md"
        documents.append(document)
    return tuple(documents)


def validate_paths(paths: Iterable[Path], *, root: Path) -> list[CaseDocViolation]:
    violations: list[CaseDocViolation] = []
    for path in paths:
        resolved = path if path.is_absolute() else root / path
        violations.extend(validate_document(resolved, root=root))
    return sorted(set(violations))


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate ET_CASE_SPEC Markdown against Formal Case Registry and source code."
    )
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--root", type=Path, default=REPOSITORY_ROOT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    root = args.root.resolve()
    paths = tuple(args.paths) if args.paths else discover_case_documents(root=root)
    if not paths:
        print("No machine-readable Formal Case documents found.")
        return 0
    violations = validate_paths(paths, root=root)
    if violations:
        for violation in violations:
            print(violation.render(root), file=sys.stderr)
        print(
            f"Formal Case document validation failed: {len(violations)} violation(s).",
            file=sys.stderr,
        )
        return 1
    print(f"Formal Case document validation passed: {len(paths)} document(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
