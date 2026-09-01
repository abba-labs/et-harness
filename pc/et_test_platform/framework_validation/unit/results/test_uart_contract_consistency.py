# UART Contract -> Formal Case -> Report 字段静态一致性测试。
# 职责：检查UART报告字段是否由对应Formal Case真实记录。
# 边界：仅执行静态契约检查，不访问Driver、Firmware或硬件。
# 依赖：UART公共契约、Formal Case源码和报告契约解析器。

from __future__ import annotations

import ast
import re
from pathlib import Path

from et_test_platform.results.case_report import _load_specs
from et_test_platform.test_cases.uart.case_registry import UART_CASE_REGISTRY

_REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
_UART_DOCUMENT = _REPOSITORY_ROOT / "test_case_doc" / "uart" / "uart.md"
_UART_CASE_ROOT = _REPOSITORY_ROOT / "pc" / "et_test_platform" / "test_cases" / "uart"
_CASE_NAME = re.compile(r"test_(uart_p[0-3]_\d{3})(?:_|$)")
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


def _case_record_keys() -> dict[str, dict[str, set[str]]]:
    records: dict[str, dict[str, set[str]]] = {}
    for path in sorted(_UART_CASE_ROOT.glob("test_uart_p*.py")):
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
                elif name == "record_result":
                    entry["artifact"].update(
                        keyword.arg for keyword in child.keywords if keyword.arg is not None
                    )
    return records


def test_uart_contract_fields_are_produced_by_registered_formal_cases() -> None:
    specs = _load_specs(_UART_DOCUMENT)
    by_id = {str(spec["case_id"]).lower(): spec for spec in specs}
    registry = set(UART_CASE_REGISTRY)
    recorded = _case_record_keys()

    assert len(UART_CASE_REGISTRY) == 33
    assert set(by_id) == registry
    assert set(recorded) == registry

    issues: list[str] = []
    for case_id in UART_CASE_REGISTRY:
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
            if source in {"measurement", "observation"} and path not in actual[source]:
                issues.append(f"{case_id}: report {source} key not produced: {path}")
            elif source == "artifact" and root not in actual["artifact"]:
                issues.append(f"{case_id}: report artifact key not produced: {root}")

    assert not issues, "\n".join(issues)


def test_uart_decisive_evidence_keeps_device_facts_atomic() -> None:
    recorded = _case_record_keys()
    p0_004 = recorded["uart_p0_004"]
    assert "peer_rx_data" in p0_004["observation"]
    assert "dut_rx_data" in p0_004["observation"]
    assert "dut_to_peer_match" in p0_004["measurement"]
    assert "peer_to_dut_match" in p0_004["measurement"]
    assert "dut_to_peer_match" not in p0_004["observation"]

    p3_010 = recorded["uart_p3_010"]
    assert "peer_actual_data" in p3_010["observation"]
    assert "dut_actual_data" in p3_010["observation"]
    assert "all_data_match" in p3_010["measurement"]
    assert "all_data_match" not in p3_010["observation"]


def test_uart_service_and_measurement_facts_do_not_masquerade_as_register_observations() -> None:
    recorded = _case_record_keys()

    p0_001 = recorded["uart_p0_001"]
    assert "capabilities_features" in p0_001["measurement"]
    assert "capabilities_features" not in p0_001["observation"]

    for case_id in (
        "uart_p1_002",
        "uart_p1_003",
        "uart_p1_006",
        "uart_p1_007",
        "uart_p1_011",
        "uart_p2_010",
    ):
        facts = recorded[case_id]
        assert "irq_pending_mask" not in facts["observation"]

    assert "enabled_mask" in recorded["uart_p1_011"]["measurement"]
    assert "disabled_mask" in recorded["uart_p1_011"]["measurement"]
    assert "paused_received" in recorded["uart_p1_013"]["measurement"]
    assert "paused_received" in recorded["uart_p2_006"]["measurement"]
    assert "mismatch_peak_rx_fifo_level" in recorded["uart_p2_005"]["measurement"]
    assert "mismatch_window_stable" in recorded["uart_p2_005"]["measurement"]
