# DMA Contract -> Formal Case -> Report 字段静态一致性测试。
#
# 职责：无硬件检查 dma.md 声明的失败证据/人工报告字段是否由对应 Formal Case 真正产生。
# 边界：不执行 DMA Driver、不伪造 HIL，只检查稳定 Case Registry、AST记录键和Artifact顶层键。
# 依赖：公共Report Contract Loader、DMA Registry和Python AST。

from __future__ import annotations

import ast
import re
from pathlib import Path

from et_test_platform.results.case_report import _load_specs
from et_test_platform.test_cases.dma.case_registry import DMA_CASE_REGISTRY

_REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
_DMA_DOCUMENT = _REPOSITORY_ROOT / "test_case_doc" / "dma" / "dma.md"
_DMA_CASE_ROOT = _REPOSITORY_ROOT / "pc" / "et_test_platform" / "test_cases" / "dma"
_CASE_NAME = re.compile(r"test_(dma_p[0-3]_\d{3})(?:_|$)")
_OBSERVATION_SOURCES = {"dut", "peer", "fpga", "instrument", "observer"}


def _call_name(call: ast.Call) -> str:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return ""


def _literal_string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _artifact_keys(call: ast.Call) -> set[str]:
    if len(call.args) < 2 or not isinstance(call.args[1], ast.Dict):
        return set()
    return {value for key in call.args[1].keys if (value := _literal_string(key)) is not None}


def _case_record_keys() -> dict[str, dict[str, set[str]]]:
    records: dict[str, dict[str, set[str]]] = {}
    for path in sorted(_DMA_CASE_ROOT.glob("test_dma_p*.py")):
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in module.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            match = _CASE_NAME.match(node.name)
            if match is None:
                continue
            case_id = match.group(1)
            entry = records.setdefault(
                case_id,
                {"measurement": set(), "observation": set(), "artifact": set()},
            )
            for child in ast.walk(node):
                if not isinstance(child, ast.Call):
                    continue
                name = _call_name(child)
                if name == "record_property" and child.args:
                    key = _literal_string(child.args[0])
                    if key is not None:
                        entry["measurement"].add(key)
                elif name == "record_observation":
                    key = next(
                        (
                            _literal_string(keyword.value)
                            for keyword in child.keywords
                            if keyword.arg == "key"
                        ),
                        None,
                    )
                    if key is not None:
                        entry["observation"].add(key)
                elif name == "write_json_result":
                    entry["artifact"].update(_artifact_keys(child))
    return records


def test_dma_contract_fields_are_produced_by_registered_formal_cases() -> None:
    specs = _load_specs(_DMA_DOCUMENT)
    by_id = {str(spec["case_id"]).lower(): spec for spec in specs}
    registry = set(DMA_CASE_REGISTRY)
    recorded = _case_record_keys()

    assert len(DMA_CASE_REGISTRY) == 28
    assert set(by_id) == registry
    assert set(recorded) == registry

    issues: list[str] = []
    for case_id in DMA_CASE_REGISTRY:
        spec = by_id[case_id]
        actual = recorded[case_id]

        for item in spec.get("failure_observations", []):
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or "")
            source = str(item.get("source") or "")
            bucket = "observation" if source in _OBSERVATION_SOURCES else "measurement"
            if key and key not in actual[bucket]:
                issues.append(f"{case_id}: failure {bucket} key not produced: {key}")

        note = spec.get("report_note")
        if not isinstance(note, dict):
            issues.append(f"{case_id}: ET_CASE_REPORT note missing")
            continue
        fields = note.get("fields")
        if not isinstance(fields, list) or not 1 <= len(fields) <= 4:
            issues.append(f"{case_id}: ET_CASE_REPORT must contain 1..4 fields")
            continue
        for field in fields:
            if not isinstance(field, dict):
                issues.append(f"{case_id}: invalid ET_CASE_REPORT field")
                continue
            source = str(field.get("source") or "")
            path = str(field.get("path") or "")
            root = path.split(".", 1)[0]
            if source in {"measurement", "observation"}:
                if path not in actual[source]:
                    issues.append(f"{case_id}: report {source} key not produced: {path}")
            elif source == "artifact" and root not in actual["artifact"]:
                issues.append(f"{case_id}: report artifact key not produced: {root}")

    assert not issues, "\n".join(issues)


def test_dma_decisive_evidence_keeps_raw_device_facts_atomic() -> None:
    recorded = _case_record_keys()

    p0_002 = recorded["dma_p0_002"]
    assert "second_actual_data" in p0_002["observation"]
    assert "second_data_match" in p0_002["measurement"]
    assert "second_data_match" not in p0_002["observation"]
    assert "final_fifo_empty" in p0_002["observation"]

    p2_015 = recorded["dma_p2_015"]
    assert "baseline_actual_data" in p2_015["observation"]
    assert "baseline_channel_free" in p2_015["observation"]
    assert "recovery_actual_data" in p2_015["observation"]
    assert "recovery_channel_free" in p2_015["observation"]
    assert "baseline_data_state" not in p2_015["observation"]
    assert "recovery_data_state" not in p2_015["observation"]
