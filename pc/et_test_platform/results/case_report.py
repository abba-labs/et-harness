# Formal Case 人工测试报告数据汇总层。
#
# 职责：把 ET_CASE_SPEC 与 canonical result.json 聚合成稳定 Case 级人工报告数据。
# 边界：不执行设备操作、不修改单次 pytest 状态，也不把软件异常伪装成 DUT FAIL。
# 依赖：仅依赖 Markdown/YAML 规格、canonical JSON 结果和标准库。

from __future__ import annotations

import json
import re
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from ..core.errors import EtPlatformError
from ..profiles.capabilities import load_packaged_chip_capabilities

REPORT_SCHEMA = "et.case-report.v1"
_SPEC_BEGIN = "<!-- ET_CASE_SPEC_BEGIN -->"
_SPEC_END = "<!-- ET_CASE_SPEC_END -->"
_REPORT_BEGIN = "<!-- ET_CASE_REPORT_BEGIN -->"
_REPORT_END = "<!-- ET_CASE_REPORT_END -->"
_SPEC_BLOCK = re.compile(
    rf"{re.escape(_SPEC_BEGIN)}\s*```yaml\s*(.*?)\s*```\s*{re.escape(_SPEC_END)}",
    re.DOTALL,
)
_REPORT_BLOCK = re.compile(
    rf"{re.escape(_REPORT_BEGIN)}\s*```yaml\s*(.*?)\s*```\s*{re.escape(_REPORT_END)}",
    re.DOTALL,
)
_REPORT_FORMATS = frozenset(
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
_HARDWARE_OBSERVATION_SOURCES = frozenset({"dut", "peer", "fpga", "instrument", "observer"})
_STATUS_PRIORITY = {
    "PASS": 0,
    "SKIP": 1,
    "EVIDENCE_MISSING": 2,
    "FAIL": 3,
}
_CANONICAL_RESULT_STATUSES = frozenset(_STATUS_PRIORITY)
_STATUS_LABELS = {
    "PASS": "通过",
    "FAIL": "失败",
    "SKIP": "未执行(SKIP)",
    "EVIDENCE_MISSING": "证据不完整",
    "NOT_EXECUTED": "未执行",
    "NOT_SELECTED": "未选择",
    "RUN_ERROR": "运行异常/报告不完整",
}


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _load_specs(document_path: Path) -> list[dict[str, Any]]:
    text = document_path.read_text(encoding="utf-8-sig")
    matches = list(_SPEC_BLOCK.finditer(text))
    if text.count(_SPEC_BEGIN) != text.count(_SPEC_END) or text.count(_SPEC_BEGIN) != len(matches):
        raise ValueError(f"unbalanced ET_CASE_SPEC blocks: {document_path}")
    specs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for match in matches:
        payload = yaml.safe_load(match.group(1))
        if not isinstance(payload, dict):
            raise ValueError(f"ET_CASE_SPEC must decode to a mapping: {document_path}")
        case_id = str(payload.get("case_id", "")).strip().lower()
        if not case_id:
            raise ValueError(f"ET_CASE_SPEC missing case_id: {document_path}")
        if case_id in seen:
            raise ValueError(f"duplicate ET_CASE_SPEC case_id: {case_id}")
        seen.add(case_id)
        specs.append(payload)
    notes = _load_report_notes(document_path, text)
    if notes and set(notes) != seen:
        missing = sorted(seen - set(notes))
        unknown = sorted(set(notes) - seen)
        raise ValueError(
            "ET_CASE_REPORT Case IDs must exactly match ET_CASE_SPEC Case IDs: "
            f"missing={missing!r}, unknown={unknown!r}"
        )
    for spec in specs:
        case_id = str(spec["case_id"]).strip().lower()
        if case_id in notes:
            spec["report_note"] = notes[case_id]
    return specs


def _load_report_notes(document_path: Path, text: str) -> dict[str, dict[str, Any]]:
    matches = list(_REPORT_BLOCK.finditer(text))
    if text.count(_REPORT_BEGIN) != text.count(_REPORT_END) or len(matches) > 1:
        raise ValueError(f"invalid ET_CASE_REPORT block: {document_path}")
    if not matches:
        return {}
    payload = yaml.safe_load(matches[0].group(1))
    if not isinstance(payload, dict) or payload.get("schema") != "et.case-report-note.v1":
        raise ValueError(f"invalid ET_CASE_REPORT schema: {document_path}")
    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, dict):
        raise ValueError(f"ET_CASE_REPORT cases must be a mapping: {document_path}")
    notes: dict[str, dict[str, Any]] = {}
    for raw_case_id, raw_note in raw_cases.items():
        case_id = _normalize_case_id(raw_case_id)
        if not case_id or case_id in notes or not isinstance(raw_note, dict):
            raise ValueError(f"invalid ET_CASE_REPORT entry {raw_case_id!r}: {document_path}")
        summary = str(raw_note.get("summary") or "").strip()
        fields = raw_note.get("fields")
        if not summary or not isinstance(fields, list) or not 1 <= len(fields) <= 4:
            raise ValueError(
                f"ET_CASE_REPORT {case_id} requires summary and 1..4 fields: {document_path}"
            )
        normalized_fields: list[dict[str, str]] = []
        for field in fields:
            if not isinstance(field, dict):
                raise ValueError(f"ET_CASE_REPORT {case_id} field must be a mapping")
            normalized = {
                "source": str(field.get("source") or "").strip(),
                "path": str(field.get("path") or "").strip(),
                "label": str(field.get("label") or "").strip(),
                "format": str(field.get("format") or "text").strip(),
                "aggregate": str(field.get("aggregate") or "same").strip(),
                "unit": str(field.get("unit") or "").strip(),
            }
            if (
                normalized["source"] not in {"artifact", "measurement", "observation"}
                or not normalized["path"]
                or not normalized["label"]
                or normalized["format"] not in _REPORT_FORMATS
                or normalized["aggregate"] not in {"same", "all", "range", "distinct"}
            ):
                raise ValueError(f"invalid ET_CASE_REPORT field for {case_id}: {field!r}")
            normalized_fields.append(normalized)
        notes[case_id] = {"summary": summary, "fields": normalized_fields}
    return notes


def _load_case_results(results_root: Path) -> list[dict[str, Any]]:
    cases_root = results_root / "cases"
    if not cases_root.is_dir():
        return []
    results: list[dict[str, Any]] = []
    for path in sorted(cases_root.glob("*/result.json")):
        result = _read_json(path)
        result["_result_path"] = str(path.relative_to(results_root))
        result["_results_root"] = str(results_root.resolve())
        results.append(result)
    return results


def _load_session(results_root: Path) -> dict[str, Any]:
    path = results_root / "session.json"
    if not path.is_file():
        raise ValueError(f"canonical session.json is missing: {path}")
    session = _read_json(path)
    if session.get("schema_version") != 1:
        raise ValueError(f"unsupported session schema_version: {path}")
    if not str(session.get("run_id") or "").strip():
        raise ValueError(f"session run_id is missing: {path}")
    return session


def _normalize_case_id(value: object) -> str:
    return str(value or "").strip().lower()


def _result_parameter_id(result: dict[str, Any]) -> str | None:
    value = result.get("parameter_id")
    if value not in (None, ""):
        return str(value)
    parameters = result.get("parameters")
    if not isinstance(parameters, dict):
        return None
    value = parameters.get("parameter_id")
    return str(value) if value not in (None, "") else None


def _result_measurements(result: dict[str, Any]) -> dict[str, Any]:
    value = result.get("measurements")
    return value if isinstance(value, dict) else {}


def _result_observations(result: dict[str, Any]) -> list[dict[str, Any]]:
    value = result.get("observations")
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _measurement_gap(spec: dict[str, Any]) -> bool:
    gap = spec.get("gap")
    return isinstance(gap, list) and "case_measurement_gap" in gap


def _structured_artifacts(result: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    # 只读取 canonical result 已绑定、且仍位于本次 run 目录内的 JSON 附件。
    # 这是旧 Case 向 Observation 契约迁移期间的受控兼容路径，不扫描目录。
    root_value = result.get("_results_root")
    artifacts = result.get("artifacts")
    if not isinstance(root_value, str) or not isinstance(artifacts, dict):
        return []
    root = Path(root_value).resolve()
    raw_paths: list[str] = []
    for value in artifacts.values():
        if isinstance(value, str):
            raw_paths.append(value)
        elif isinstance(value, list):
            raw_paths.extend(item for item in value if isinstance(item, str))
    payloads: list[tuple[str, dict[str, Any]]] = []
    for value in dict.fromkeys(raw_paths):
        path = Path(value)
        if not path.is_absolute():
            path = root / path
        path = path.resolve()
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            continue
        if path.suffix.lower() != ".json" or not path.is_file():
            continue
        try:
            payload = _read_json(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        payloads.append((relative, payload))
    return payloads


def _failure_observations(spec: dict[str, Any]) -> list[dict[str, str]]:
    raw = spec.get("failure_observations")
    if not isinstance(raw, list):
        return []
    observations: list[dict[str, str]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        key = str(entry.get("key", "")).strip()
        label = str(entry.get("label", "")).strip()
        source = str(entry.get("source", "")).strip()
        if key and label and source:
            default_role = (
                "expected"
                if source == "oracle"
                else "config"
                if source.endswith("config")
                else "actual"
            )
            observations.append(
                {
                    "key": key,
                    "label": label,
                    "source": source,
                    "role": str(entry.get("role", default_role)).strip(),
                    "format": str(entry.get("format", "text")).strip(),
                    "semantic_ref": str(entry.get("semantic_ref", "")).strip(),
                    "unit": str(entry.get("unit", "")).strip(),
                }
            )
    return observations


def _has_hardware_failure_observation(spec: dict[str, Any], result: dict[str, Any]) -> bool:
    measurements = _result_measurements(result)
    recorded = _result_observations(result)
    return any(
        observation["source"] in _HARDWARE_OBSERVATION_SOURCES
        and (
            observation["key"] in measurements
            or any(
                item.get("key") == observation["key"]
                and item.get("source") == observation["source"]
                for item in recorded
            )
        )
        for observation in _failure_observations(spec)
    )


def _observation_contract_issues(spec: dict[str, Any], result: dict[str, Any]) -> list[str]:
    # PASS/FAIL 使用同一证据契约：每个声明项必须有值；声明了 Capability
    # 语义路径时，还必须能解析到当前芯片实例的具体硬件路径。
    if _measurement_gap(spec) and _structured_artifacts(result):
        return []
    measurements = _result_measurements(result)
    recorded = _result_observations(result)
    chip_id = str(result.get("chip_id") or result.get("chip") or "")
    issues: list[str] = []
    for observation in _failure_observations(spec):
        values = [
            item
            for item in recorded
            if item.get("key") == observation["key"] and item.get("source") == observation["source"]
        ]
        if not values and observation["key"] not in measurements:
            issues.append(f"缺少Observation: {observation['key']}")
            continue
        semantic_ref = observation.get("semantic_ref", "")
        if not semantic_ref or not values:
            continue
        for item in values:
            endpoint = str(item.get("endpoint") or "")
            if (
                not chip_id
                or not endpoint
                or not _capability_paths(chip_id, semantic_ref, endpoint)
            ):
                issues.append(f"Capability路径未解析: {semantic_ref}@{endpoint or '?'}")
    return list(dict.fromkeys(issues))


def _aggregate_raw_status(results: list[dict[str, Any]]) -> str:
    if not results:
        return "NOT_EXECUTED"
    statuses = [str(result.get("status") or "").upper() for result in results]
    known = [status for status in statuses if status in _STATUS_PRIORITY]
    if len(known) != len(statuses):
        return "RUN_ERROR"
    return max(known, key=_STATUS_PRIORITY.__getitem__)


def _aggregate_report_status(spec: dict[str, Any], results: list[dict[str, Any]]) -> str:
    raw_status = _aggregate_raw_status(results)
    if raw_status not in {"PASS", "FAIL"}:
        return raw_status
    if raw_status == "FAIL":
        failing = [
            result for result in results if str(result.get("status") or "").upper() == "FAIL"
        ]
        if not any(_has_hardware_failure_observation(spec, result) for result in failing):
            return "RUN_ERROR"

    # Canonical Result 已经完成 pytest 状态和必需 Evidence 的最终判定。
    # 报告不得再使用 failure_observations 改写 PASS/FAIL；人工报告字段由
    # ET_CASE_REPORT 单独解析，缺失时由 _human_report_note 失败关闭。
    return raw_status


def _execution_key(case_id: object, parameter_id: object) -> tuple[str, str | None]:
    normalized_parameter = str(parameter_id) if parameter_id not in (None, "") else None
    return _normalize_case_id(case_id), normalized_parameter


def _selection_scope(
    session: dict[str, Any],
) -> tuple[set[str] | None, set[tuple[str, str | None]] | None]:
    selection = session.get("selection")
    if not isinstance(selection, dict):
        return None, None
    raw_case_ids = selection.get("selected_case_ids")
    raw_executions = selection.get("selected_executions")
    if not isinstance(raw_case_ids, list) or not isinstance(raw_executions, list):
        raise ValueError("session selection must contain selected_case_ids and selected_executions")
    selected_case_ids = {_normalize_case_id(value) for value in raw_case_ids}
    selected_case_ids.discard("")
    executions: set[tuple[str, str | None]] = set()
    for entry in raw_executions:
        if not isinstance(entry, dict):
            raise ValueError("session selected_executions entries must be objects")
        key = _execution_key(entry.get("case_id"), entry.get("parameter_id"))
        if not key[0]:
            raise ValueError("session selected execution is missing case_id")
        if key in executions:
            raise ValueError(f"duplicate selected execution in session: {key!r}")
        executions.add(key)
    if {case_id for case_id, _ in executions} != selected_case_ids:
        raise ValueError("session selected_case_ids disagree with selected_executions")
    return selected_case_ids, executions


def _validate_case_results(
    results: list[dict[str, Any]],
    *,
    session: dict[str, Any],
    known_case_ids: set[str],
    selected_executions: set[tuple[str, str | None]] | None,
) -> None:
    run_id = str(session["run_id"])
    seen_case_run_ids: set[str] = set()
    seen_executions: set[tuple[str, str | None]] = set()
    for result in results:
        path = str(result.get("_result_path") or "result.json")
        if result.get("schema_version") != 1:
            raise ValueError(f"unsupported result schema_version: {path}")
        if str(result.get("run_id") or "") != run_id:
            raise ValueError(f"result run_id does not match session: {path}")
        case_run_id = str(result.get("case_run_id") or "").strip()
        if not case_run_id or case_run_id in seen_case_run_ids:
            raise ValueError(f"missing or duplicate case_run_id: {path}")
        seen_case_run_ids.add(case_run_id)
        case_id = _normalize_case_id(result.get("case_id"))
        if case_id not in known_case_ids:
            raise ValueError(f"result references unknown Case ID {case_id!r}: {path}")
        status = str(result.get("status") or "").upper()
        if status not in _CANONICAL_RESULT_STATUSES:
            raise ValueError(f"unsupported canonical result status {status!r}: {path}")
        key = _execution_key(case_id, _result_parameter_id(result))
        if key in seen_executions:
            raise ValueError(f"duplicate Case execution result {key!r}: {path}")
        seen_executions.add(key)
        if selected_executions is not None and key not in selected_executions:
            raise ValueError(f"result was not part of the recorded selection {key!r}: {path}")


def _format_value(value: object) -> str:
    if isinstance(value, str):
        return value
    if value is None or isinstance(value, (bool, int, float)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, dict):
        return "；".join(f"{key}={_format_value(value[key])}" for key in sorted(value))
    if isinstance(value, (list, tuple)):
        return "、".join(_format_value(item) for item in value)
    return str(value)


def _format_count_value(value: object) -> str:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return str(value)
    if isinstance(value, (list, dict, tuple)):
        return str(len(value))
    raise ValueError(f"invalid count observation value: {value!r}")


def _format_observation_value(value: object, format_name: str, unit: str) -> str:
    if format_name.startswith("hex") and format_name[3:].isdigit():
        width_bits = int(format_name[3:])
        if (
            width_bits not in {8, 16, 32, 64}
            or not isinstance(value, int)
            or isinstance(value, bool)
            or value < 0
            or value >= 1 << width_bits
        ):
            raise ValueError(f"invalid {format_name} observation value: {value!r}")
        rendered = f"0x{value:0{width_bits // 4}X}"
    elif format_name == "bit_bool":
        if not isinstance(value, (bool, int)) or value not in {0, 1}:
            raise ValueError(f"invalid bit_bool observation value: {value!r}")
        rendered = f"0x{int(bool(value)):X} ({str(bool(value)).lower()})"
    elif format_name == "bool":
        if not isinstance(value, (bool, int)) or value not in {0, 1}:
            raise ValueError(f"invalid bool observation value: {value!r}")
        rendered = str(bool(value)).lower()
    elif format_name in {"decimal", "float"}:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"invalid {format_name} observation value: {value!r}")
        rendered = str(value)
    elif format_name == "count":
        rendered = _format_count_value(value)
    elif format_name == "bytes_hex":
        if isinstance(value, str):
            compact = "".join(value.split())
            if len(compact) % 2 or re.fullmatch(r"[0-9A-Fa-f]*", compact) is None:
                raise ValueError(f"invalid bytes_hex observation value: {value!r}")
            rendered = " ".join(
                compact[index : index + 2].upper() for index in range(0, len(compact), 2)
            )
        elif isinstance(value, list) and all(
            isinstance(item, int) and not isinstance(item, bool) and 0 <= item <= 0xFF
            for item in value
        ):
            rendered = " ".join(f"{item:02X}" for item in value)
        else:
            raise ValueError(f"invalid bytes_hex observation value: {value!r}")
    else:
        rendered = _format_value(value)
    return f"{rendered} {unit}" if unit else rendered


def _path_value(payload: object, path: str) -> object:
    current = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(path)
        current = current[part]
    return current


def _report_note_value(result: dict[str, Any], field: dict[str, str]) -> object:
    source = field["source"]
    path = field["path"]
    if source == "measurement":
        return _path_value(_result_measurements(result), path)
    if source == "observation":
        values = [
            item.get("value") for item in _result_observations(result) if item.get("key") == path
        ]
        if len(values) != 1:
            raise KeyError(path)
        return values[0]
    payloads = _structured_artifacts(result)
    values: list[object] = []
    for _, payload in payloads:
        try:
            values.append(_path_value(payload, path))
        except KeyError:
            continue
    if len(values) != 1:
        raise KeyError(path)
    return values[0]


def _aggregate_note_values(values: list[object], mode: str) -> object:
    if not values:
        raise ValueError("report note has no values")
    if any(value is None for value in values):
        raise ValueError("report note contains a missing required value")
    if mode == "same":
        first = values[0]
        if any(value != first for value in values[1:]):
            raise ValueError("report note values are not identical")
        return first
    if mode == "all":
        return values
    if mode == "distinct":
        unique: list[object] = []
        for value in values:
            if value not in unique:
                unique.append(value)
        if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in unique):
            return sorted(unique)
        if all(isinstance(value, str) for value in unique):
            return sorted(unique)
        return unique
    if not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values):
        raise ValueError("range aggregation requires numeric values")
    return min(values), max(values)


def _format_note_value(value: object, field: dict[str, str]) -> str:
    mode = field["aggregate"]
    if mode == "range":
        low, high = value
        if low == high:
            return _format_observation_value(low, field["format"], field["unit"])
        return (
            f"{_format_observation_value(low, field['format'], field['unit'])}"
            f" ～ {_format_observation_value(high, field['format'], field['unit'])}"
        )
    if field["format"] in {"count", "bytes_hex"}:
        return _format_observation_value(value, field["format"], field["unit"])
    if isinstance(value, list):
        return "、".join(
            _format_observation_value(item, field["format"], field["unit"]) for item in value
        )
    return _format_observation_value(value, field["format"], field["unit"])


def _clean_markdown_cell(value: str) -> str:
    return value.replace("`", "").strip()


@cache
def _chip_observation_aliases(document_path: str, chip_id: str) -> tuple[tuple[str, str], ...]:
    document = Path(document_path)
    normalized_chip = chip_id.strip().upper()
    if not normalized_chip:
        return ()
    chip_document = document.with_name(f"{normalized_chip}_{document.name}")
    if not chip_document.is_file():
        return ()

    aliases: list[tuple[str, str]] = []
    inside_mapping_table = False
    for raw_line in chip_document.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not inside_mapping_table:
            if line.startswith("| 公共稳定语义 |"):
                inside_mapping_table = True
            continue
        if not line.startswith("|"):
            if aliases:
                break
            continue
        cells = [_clean_markdown_cell(cell) for cell in line.split("|")[1:-1]]
        if len(cells) < 2:
            continue
        stable_name, chip_name = cells[0], cells[1]
        if stable_name == "公共稳定语义" or not stable_name or not chip_name:
            continue
        if set(stable_name) <= {"-", ":"}:
            continue
        aliases.append((stable_name, chip_name))
    return tuple(aliases)


def _resolve_chip_observation(
    endpoint: str,
    aliases: tuple[tuple[str, str], ...],
) -> str:
    if not endpoint:
        return ""
    for stable_name, chip_name in aliases:
        if endpoint == stable_name:
            return chip_name
    for stable_name, chip_name in aliases:
        placeholder = "<Source>"
        if placeholder not in stable_name:
            continue
        prefix, suffix = stable_name.split(placeholder, 1)
        if not endpoint.startswith(prefix) or (suffix and not endpoint.endswith(suffix)):
            continue
        end = len(endpoint) - len(suffix) if suffix else len(endpoint)
        source_name = endpoint[len(prefix) : end]
        if source_name:
            return chip_name.replace("<Source bit>", source_name).replace(placeholder, source_name)
    for stable_name, chip_name in sorted(aliases, key=lambda item: len(item[0]), reverse=True):
        if stable_name in endpoint:
            return endpoint.replace(stable_name, chip_name)
    return ""


def _compact_chip_locations(locations: list[str]) -> str:
    unique = list(dict.fromkeys(location for location in locations if location))
    if not unique:
        return ""
    if len(unique) == 1:
        return unique[0]
    split_locations = [location.rsplit(".", 1) for location in unique]
    if all(len(parts) == 2 for parts in split_locations):
        prefixes = {parts[0] for parts in split_locations}
        if len(prefixes) == 1:
            return f"{next(iter(prefixes))}.<Source>"
    if len(unique) <= 3:
        return " / ".join(unique)
    return f"{unique[0]} 等{len(unique)}项"


def _bind_chip_report_labels(
    document: Path,
    chip_id: str,
    specs: list[dict[str, Any]],
    results: list[dict[str, Any]],
) -> None:
    aliases = _chip_observation_aliases(str(document), chip_id)
    if not aliases:
        return
    by_case: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        by_case.setdefault(_normalize_case_id(result.get("case_id")), []).append(result)
    for spec in specs:
        note = spec.get("report_note")
        if not isinstance(note, dict):
            continue
        case_results = by_case.get(_normalize_case_id(spec.get("case_id")), [])
        for field in note.get("fields", []):
            if not isinstance(field, dict) or field.get("source") != "observation":
                continue
            locations: list[str] = []
            for result in case_results:
                for item in _result_observations(result):
                    if item.get("key") != field.get("path"):
                        continue
                    resolved = _resolve_chip_observation(str(item.get("endpoint") or ""), aliases)
                    if resolved:
                        locations.append(resolved)
            chip_location = _compact_chip_locations(locations)
            if chip_location:
                field["label"] = f"{chip_location}（{field['label']}）"


def _human_report_note(spec: dict[str, Any], results: list[dict[str, Any]]) -> str:
    note = spec.get("report_note")
    if not isinstance(note, dict):
        return ""
    completed = [
        result for result in results if str(result.get("status") or "").upper() in {"PASS", "FAIL"}
    ]
    lines = [str(note["summary"])]
    for field in note["fields"]:
        try:
            values = [_report_note_value(result, field) for result in completed]
            value = _aggregate_note_values(values, field["aggregate"])
            rendered = _format_note_value(value, field)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"report note field cannot be resolved for {spec.get('case_id')}: "
                f"{field['source']}:{field['path']} ({exc})"
            ) from exc
        lines.append(f"{field['label']}：{rendered}")
    return "\n".join(lines)


@cache
def _capability_paths(chip_id: str, semantic_ref: str, instance: str) -> tuple[str, ...]:
    parts = semantic_ref.split(".", 2)
    if len(parts) != 3:
        return ()
    ip_id, kind, name = parts
    try:
        capabilities = load_packaged_chip_capabilities(chip_id.strip().lower())
        evidence = capabilities.evidence(ip_id, kind, name, instance=instance)
    except (EtPlatformError, OSError, ValueError):
        return ()
    return tuple(dict.fromkeys(item.path for item in evidence if item.path))


def _hardware_location(
    result: dict[str, Any], item: dict[str, Any], observation: dict[str, str]
) -> str:
    source = str(item.get("source") or observation["source"])
    device_id = str(item.get("device_id") or source)
    endpoint = str(item.get("endpoint") or "")
    chip_id = str(result.get("chip_id") or result.get("chip") or "")
    if source == "dut" and device_id == "dut" and chip_id:
        device_id = chip_id
    parts = [source.upper(), device_id]
    if endpoint and endpoint != device_id:
        parts.append(endpoint)
    semantic_ref = observation.get("semantic_ref", "")
    if semantic_ref and chip_id and endpoint:
        paths = _capability_paths(chip_id, semantic_ref, endpoint)
        parts.append(" / ".join(paths) if paths else f"Capability路径未解析({semantic_ref})")
    return " / ".join(parts)


def _observation_lines(spec: dict[str, Any], result: dict[str, Any]) -> list[str]:
    measurements = _result_measurements(result)
    recorded = _result_observations(result)
    groups: dict[str, list[str]] = {
        role: [] for role in ("config", "stimulus", "expected", "actual")
    }
    titles = {
        "config": "测试配置",
        "stimulus": "测试激励",
        "expected": "预期结果",
        "actual": "硬件观测",
    }
    parameter_id = _result_parameter_id(result)
    if parameter_id:
        groups["config"].append(f"参数实例: {parameter_id}")
    for observation in _failure_observations(spec):
        role = observation.get("role", "actual")
        values = [
            item
            for item in recorded
            if item.get("key") == observation["key"] and item.get("source") == observation["source"]
        ]
        if values:
            for item in values:
                rendered = _format_observation_value(
                    item.get("value"),
                    observation.get("format", "text"),
                    observation.get("unit", ""),
                )
                location = _hardware_location(result, item, observation)
                groups.setdefault(role, []).append(
                    f"{location}\n  {observation['label']}: {rendered}"
                )
        elif observation["key"] in measurements:
            rendered = _format_observation_value(
                measurements[observation["key"]],
                observation.get("format", "text"),
                observation.get("unit", ""),
            )
            groups.setdefault(role, []).append(f"{observation['label']}: {rendered}")
    # 原始 JSON 只承担机器证据职责。没有报告模板时只提示证据已经保留，
    # 绝不把任意嵌套对象直接展开到面向人的 Excel 备注中。
    if _measurement_gap(spec) and _structured_artifacts(result):
        groups["actual"].append("详细硬件数据已保存为结构化原始证据。")
    lines: list[str] = []
    for role in ("config", "stimulus", "expected", "actual"):
        values = groups.get(role, [])
        if values:
            lines.append(f"{titles[role]}:\n- " + "\n- ".join(values))
    artifacts = [
        str(path)
        for item in recorded
        for path in item.get("artifacts", [])
        if isinstance(path, str) and path
    ]
    if artifacts:
        lines.append("证据文件:\n- " + "\n- ".join(dict.fromkeys(artifacts)))
    return lines


def _evidence_remark(spec: dict[str, Any], results: list[dict[str, Any]]) -> str:
    human_note = _human_report_note(spec, results)
    if human_note:
        return human_note
    sections: list[str] = []
    for result in results:
        if str(result.get("status") or "").upper() not in {"PASS", "FAIL"}:
            continue
        lines = _observation_lines(spec, result)
        if lines:
            sections.append("\n".join(lines))
    return "\n\n".join(sections)


def _evidence_missing_remark(spec: dict[str, Any], results: list[dict[str, Any]]) -> str:
    missing: list[str] = []
    for result in results:
        if str(result.get("status") or "").upper() != "EVIDENCE_MISSING":
            continue
        values = result.get("missing_evidence_sources")
        if isinstance(values, list):
            missing.extend(str(value) for value in values if value)
    unique = list(dict.fromkeys(missing))
    issues = [
        issue
        for result in results
        if str(result.get("status") or "").upper() in {"PASS", "FAIL"}
        for issue in _observation_contract_issues(spec, result)
    ]
    details = list(dict.fromkeys([*unique, *issues]))
    suffix = "；".join(details) if details else "未记录具体来源"
    return f"所需结构化Observation不完整：{suffix}。"


def _report_remark(spec: dict[str, Any], results: list[dict[str, Any]], status: str) -> str:
    if status in {"PASS", "FAIL"}:
        return _evidence_remark(spec, results)
    if status == "RUN_ERROR":
        return "运行异常/报告不完整：未取得足够的结构化 DUT/Observer Observation，未作为芯片 FAIL 展示。"
    if status == "EVIDENCE_MISSING":
        return _evidence_missing_remark(spec, results)
    if status == "SKIP":
        return "本次运行存在未执行参数，未形成该稳定 Case 的完整 PASS 证据。"
    if status == "NOT_EXECUTED":
        return "本次结果目录未发现该稳定 Case 的执行记录。"
    if status == "NOT_SELECTED":
        return "该稳定 Case 不在本次运行的选择范围内。"
    return ""


def _list_of_strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _method_text(spec: dict[str, Any]) -> str:
    method = spec.get("method")
    if not isinstance(method, dict):
        return ""
    inputs = _list_of_strings(method.get("inputs"))
    steps = _list_of_strings(method.get("steps"))
    parts: list[str] = []
    if inputs:
        parts.append("输入：" + "；".join(inputs))
    if steps:
        parts.append(
            "步骤：\n" + "\n".join(f"{index}. {step}" for index, step in enumerate(steps, 1))
        )
    return "\n".join(parts)


def _pass_criteria_text(spec: dict[str, Any]) -> str:
    method = spec.get("method")
    if not isinstance(method, dict):
        return ""
    criteria = _list_of_strings(method.get("pass_criteria"))
    return "\n".join(f"{index}. {criterion}" for index, criterion in enumerate(criteria, 1))


def _case_row(
    spec: dict[str, Any],
    results: list[dict[str, Any]],
    *,
    selected: bool,
    expected_execution_count: int | None,
) -> dict[str, Any]:
    status = _aggregate_report_status(spec, results) if selected else "NOT_SELECTED"
    execution_complete = (
        expected_execution_count is None or len(results) == expected_execution_count
    )
    coverage_complete = (
        selected
        and execution_complete
        and status in {"PASS", "FAIL"}
        and all(str(result.get("status") or "").upper() in {"PASS", "FAIL"} for result in results)
    )
    return {
        "case_id": str(spec.get("case_id") or ""),
        "p_level": str(spec.get("p_level") or ""),
        "report_feature": str(spec.get("report_feature") or ""),
        "case_name": str(spec.get("case_name") or ""),
        "method": _method_text(spec),
        "pass_criteria": _pass_criteria_text(spec),
        "status": status,
        "status_label": _STATUS_LABELS.get(status, status),
        "remark": _report_remark(spec, results, status),
        "execution_count": len(results),
        "expected_execution_count": expected_execution_count,
        "coverage_complete": coverage_complete,
        "feature_refs": _list_of_strings(spec.get("feature_refs")),
    }


def _execution_row(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": str(result.get("case_id") or ""),
        "parameter_id": _result_parameter_id(result),
        "status": str(result.get("status") or ""),
        "duration_s": result.get("duration_s"),
        "evidence_complete": result.get("evidence_complete"),
        "evidence_sources": result.get("evidence_sources") or [],
        "missing_evidence_sources": result.get("missing_evidence_sources") or [],
        "target_id": result.get("target_id"),
        "chip_id": result.get("chip_id"),
        "firmware_build_id": result.get("firmware_build_id"),
        "measurements": _result_measurements(result),
        "observations": _result_observations(result),
        "error": result.get("error"),
        "result_path": result.get("_result_path"),
    }


def _spec_trace_row(spec: dict[str, Any]) -> dict[str, Any]:
    method = spec.get("method") if isinstance(spec.get("method"), dict) else {}
    resources = spec.get("resources") if isinstance(spec.get("resources"), dict) else {}
    observations = _failure_observations(spec)
    return {
        "case_id": str(spec.get("case_id") or ""),
        "p_level": str(spec.get("p_level") or ""),
        "report_feature": str(spec.get("report_feature") or ""),
        "case_name": str(spec.get("case_name") or ""),
        "feature_refs": _list_of_strings(spec.get("feature_refs")),
        "inputs": _list_of_strings(method.get("inputs")),
        "steps": _list_of_strings(method.get("steps")),
        "observations": _list_of_strings(method.get("observations")),
        "pass_criteria": _list_of_strings(method.get("pass_criteria")),
        "failure_observations": observations,
        "resources": resources,
        "backend": _list_of_strings(spec.get("backend")),
    }


def _summary(
    case_rows: list[dict[str, Any]], execution_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for row in case_rows:
        status = str(row["status"])
        counts[status] = counts.get(status, 0) + 1
    return {
        "stable_case_count": len(case_rows),
        "execution_count": len(execution_rows),
        "status_counts": counts,
        "coverage_complete_count": sum(bool(row["coverage_complete"]) for row in case_rows),
    }


def _session_complete(session: dict[str, Any]) -> bool:
    exitstatus = session.get("exitstatus")
    return bool(session.get("finished_at")) and isinstance(exitstatus, int) and exitstatus in {0, 1}


# 读取第六章 ET_CASE_SPEC 和一次 pytest 结果目录，生成不改变 canonical 状态的人工报告模型。
def build_case_report_model(
    document_path: str | Path,
    results_root: str | Path,
    *,
    chip_name: str | None = None,
) -> dict[str, Any]:

    document = Path(document_path).resolve()
    root = Path(results_root).resolve()
    specs = _load_specs(document)
    results = _load_case_results(root)
    session = _load_session(root)
    chip_id = str(session.get("chip_id") or session.get("chip") or "")
    _bind_chip_report_labels(document, chip_id, specs, results)
    selected_case_ids, selected_executions = _selection_scope(session)
    known_case_ids = {_normalize_case_id(spec.get("case_id")) for spec in specs}
    if selected_case_ids is not None and not selected_case_ids.issubset(known_case_ids):
        unknown = sorted(selected_case_ids - known_case_ids)
        raise ValueError(f"session selection references unknown Case IDs: {unknown!r}")
    _validate_case_results(
        results,
        session=session,
        known_case_ids=known_case_ids,
        selected_executions=selected_executions,
    )
    by_case: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        by_case.setdefault(_normalize_case_id(result.get("case_id")), []).append(result)

    case_rows: list[dict[str, Any]] = []
    for spec in specs:
        case_id = _normalize_case_id(spec.get("case_id"))
        selected = selected_case_ids is None or case_id in selected_case_ids
        expected_count = (
            None
            if selected_executions is None
            else sum(
                1 for expected_case_id, _ in selected_executions if expected_case_id == case_id
            )
        )
        case_rows.append(
            _case_row(
                spec,
                by_case.get(case_id, []),
                selected=selected,
                expected_execution_count=expected_count,
            )
        )
    execution_rows = [_execution_row(result) for result in results]
    session_complete = _session_complete(session)
    report_complete = session_complete and all(
        bool(row["coverage_complete"]) or row["status"] == "NOT_SELECTED" for row in case_rows
    )
    return {
        "schema": REPORT_SCHEMA,
        "chip_name": chip_name or session.get("chip_id") or session.get("chip") or "",
        "ip_name": document.stem.upper(),
        "document_path": str(document),
        "results_root": str(root),
        "session": session,
        "session_complete": session_complete,
        "report_complete": report_complete,
        "summary": _summary(case_rows, execution_rows),
        "cases": case_rows,
        "executions": execution_rows,
        "spec_trace": [_spec_trace_row(spec) for spec in specs],
    }
