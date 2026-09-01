# CRC 模拟 Canonical Result -> ET6801 寄存器名 -> Excel 报告闭环测试。
# 职责：不访问硬件，验证真实 CRC Contract、芯片 endpoint 映射、ET_CASE_REPORT 和 XLSX 导出链路。
# 边界：模拟结果只验证报告软件链，不能改变当前 SHA 的 FPGA/Silicon HIL 状态。
# 依赖：CRC公共契约、芯片映射和Canonical Result报告导出器。

from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path
from types import ModuleType

from et_test_platform.results.case_report import build_case_report_model


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _reporting_module() -> ModuleType:
    repository_root = Path(__file__).resolve().parents[5]
    script = repository_root / "tools" / "reporting" / "generate_case_report.py"
    spec = importlib.util.spec_from_file_location("_et_generate_case_report_crc", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _case_row(model: dict[str, object], case_id: str) -> dict[str, object]:
    rows = model["cases"]
    assert isinstance(rows, list)
    return next(row for row in rows if row["case_id"] == case_id)


def test_crc_simulated_et6801_report_uses_real_register_names_and_exports_xlsx(
    tmp_path: Path,
) -> None:
    repository_root = Path(__file__).resolve().parents[5]
    document = repository_root / "test_case_doc" / "crc" / "crc.md"
    results_root = tmp_path / "run"
    output = tmp_path / "ET6801_CRC_simulated.xlsx"

    _write_json(
        results_root / "session.json",
        {
            "schema_version": 1,
            "run_id": "run-crc-simulated-report",
            "chip_id": "ET6801",
            "finished_at": "2026-08-19T14:00:00Z",
            "exitstatus": 0,
            "selection": {
                "selected_case_ids": ["crc_p1_007", "crc_p1_014"],
                "selected_executions": [
                    {"case_id": "crc_p1_007", "parameter_id": None},
                    {"case_id": "crc_p1_014", "parameter_id": None},
                ],
            },
        },
    )

    # P1_007：验证 LENGTH 稳定 endpoint 和 RESULT.CRC 能解析到 ET6801 实际 Field。
    _write_json(
        results_root / "cases" / "crc-p1-007" / "result.json",
        {
            "schema_version": 1,
            "run_id": "run-crc-simulated-report",
            "chip_id": "ET6801",
            "case_run_id": "crc-p1-007-simulated",
            "case_id": "crc_p1_007",
            "parameter_id": None,
            "status": "PASS",
            "duration_s": 0.01,
            "measurements": {
                "mode": "CRC32",
                "length_bytes": 9,
                "expected_input_count": 3,
                "expected_crc": 0x12345678,
            },
            "observations": [
                {
                    "key": "programmed_input_count",
                    "value": 3,
                    "source": "dut",
                    "device_id": "dut",
                    "endpoint": "LENGTH.REMAINING_INPUT_COUNT",
                    "artifacts": [],
                },
                {
                    "key": "actual_crc",
                    "value": 0x12345678,
                    "source": "dut",
                    "device_id": "dut",
                    "endpoint": "RESULT.CRC",
                    "artifacts": [],
                },
                {
                    "key": "remaining_input_count",
                    "value": 0,
                    "source": "dut",
                    "device_id": "dut",
                    "endpoint": "LENGTH.REMAINING_INPUT_COUNT",
                    "artifacts": [],
                },
            ],
            "evidence_complete": True,
            "evidence_sources": ["dut"],
            "missing_evidence_sources": [],
            "artifacts": [],
            "error": None,
        },
    )

    # P1_014：验证 Raw/Status 原子 Observation 映射到不同 ET6801 中断 Field。
    _write_json(
        results_root / "cases" / "crc-p1-014" / "result.json",
        {
            "schema_version": 1,
            "run_id": "run-crc-simulated-report",
            "chip_id": "ET6801",
            "case_run_id": "crc-p1-014-simulated",
            "case_id": "crc_p1_014",
            "parameter_id": None,
            "status": "PASS",
            "duration_s": 0.01,
            "measurements": {
                "event_count_before": 7,
                "event_count_after": 7,
            },
            "observations": [
                {
                    "key": "raw_before_clear",
                    "value": True,
                    "source": "dut",
                    "device_id": "dut",
                    "endpoint": "IRQ_RAW.BUS_ERROR",
                    "artifacts": [],
                },
                {
                    "key": "status_before_clear",
                    "value": False,
                    "source": "dut",
                    "device_id": "dut",
                    "endpoint": "IRQ_STATUS.BUS_ERROR",
                    "artifacts": [],
                },
                {
                    "key": "raw_after_clear",
                    "value": False,
                    "source": "dut",
                    "device_id": "dut",
                    "endpoint": "IRQ_RAW.BUS_ERROR",
                    "artifacts": [],
                },
                {
                    "key": "status_after_clear",
                    "value": False,
                    "source": "dut",
                    "device_id": "dut",
                    "endpoint": "IRQ_STATUS.BUS_ERROR",
                    "artifacts": [],
                },
            ],
            "evidence_complete": True,
            "evidence_sources": ["dut"],
            "missing_evidence_sources": [],
            "artifacts": [],
            "error": None,
        },
    )

    model = build_case_report_model(document, results_root)
    length_row = _case_row(model, "CRC_P1_007")
    clear_row = _case_row(model, "CRC_P1_014")

    assert model["report_complete"] is True
    assert length_row["status"] == "PASS"
    assert length_row["coverage_complete"] is True
    assert "LENGTH.CRC_LENGTH（长度编程读回）" in length_row["remark"]
    assert "RES.POST_CRC_CAL（硬件CRC结果）" in length_row["remark"]

    assert clear_row["status"] == "PASS"
    assert clear_row["coverage_complete"] is True
    assert "INT_RAW_RPT.CRC_BEF_INT_RAW_RPT（Clear前IRQ_RAW.BUS_ERROR）" in clear_row["remark"]
    assert (
        "INT_STATUS_RPT.CRC_BEF_INT_STATUS_RPT（Clear后IRQ_STATUS.BUS_ERROR）"
        in clear_row["remark"]
    )

    reporting = _reporting_module()
    reporting._write_xlsx(model, output)
    assert output.is_file() and output.stat().st_size > 0

    with zipfile.ZipFile(output) as archive:
        xml_payload = b"\n".join(
            archive.read(name) for name in archive.namelist() if name.endswith(".xml")
        )
    assert b"LENGTH.CRC_LENGTH" in xml_payload
    assert b"RES.POST_CRC_CAL" in xml_payload
    assert b"INT_RAW_RPT.CRC_BEF_INT_RAW_RPT" in xml_payload
    assert b"INT_STATUS_RPT.CRC_BEF_INT_STATUS_RPT" in xml_payload
