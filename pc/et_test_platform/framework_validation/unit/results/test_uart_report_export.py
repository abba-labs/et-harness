# UART 模拟 Canonical Result -> ET6801 寄存器名 -> Excel 报告闭环测试。
# 职责：验证UART稳定endpoint、芯片映射、ET_CASE_REPORT和XLSX导出链路。
# 边界：模拟结果只验证报告软件链，不改变或替代任何HIL结果。
# 依赖：UART公共契约、芯片映射和Canonical Result报告导出器。

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
    spec = importlib.util.spec_from_file_location("_et_generate_case_report_uart", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _case_row(model: dict[str, object], case_id: str) -> dict[str, object]:
    rows = model["cases"]
    assert isinstance(rows, list)
    return next(row for row in rows if row["case_id"] == case_id)


def test_uart_simulated_et6801_report_uses_real_register_names_and_exports_xlsx(
    tmp_path: Path,
) -> None:
    repository_root = Path(__file__).resolve().parents[5]
    document = repository_root / "test_case_doc" / "uart" / "uart.md"
    results_root = tmp_path / "run"
    output = tmp_path / "ET6801_UART_simulated.xlsx"

    _write_json(
        results_root / "session.json",
        {
            "schema_version": 1,
            "run_id": "run-uart-simulated-report",
            "chip_id": "ET6801",
            "finished_at": "2026-08-20T01:00:00Z",
            "exitstatus": 0,
            "selection": {
                "selected_case_ids": ["uart_p3_009"],
                "selected_executions": [{"case_id": "uart_p3_009", "parameter_id": None}],
            },
        },
    )

    _write_json(
        results_root / "cases" / "uart-p3-009" / "result.json",
        {
            "schema_version": 1,
            "run_id": "run-uart-simulated-report",
            "chip_id": "ET6801",
            "case_run_id": "uart-p3-009-simulated",
            "case_id": "uart_p3_009",
            "parameter_id": None,
            "status": "PASS",
            "duration_s": 0.01,
            "measurements": {},
            "observations": [
                {
                    "key": "fifo_access_enabled",
                    "value": True,
                    "source": "dut",
                    "device_id": "dut",
                    "endpoint": "UART_FIFO_ACCESS.ENABLED",
                    "artifacts": [],
                },
                {
                    "key": "tx_fifo_value",
                    "value": 90,
                    "source": "dut",
                    "device_id": "dut",
                    "endpoint": "UART_FIFO_ACCESS.TX_VALUE",
                    "artifacts": [],
                },
                {
                    "key": "rx_fifo_value",
                    "value": 165,
                    "source": "dut",
                    "device_id": "dut",
                    "endpoint": "UART_FIFO_ACCESS.RX_VALUE",
                    "artifacts": [],
                },
                {
                    "key": "recovery_actual_data",
                    "value": [1, 2, 3, 4],
                    "source": "dut",
                    "device_id": "dut",
                    "endpoint": "UART_CAPTURE.DATA",
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
    row = _case_row(model, "UART_P3_009")

    assert model["report_complete"] is True
    assert row["status"] == "PASS"
    assert row["coverage_complete"] is True
    assert "FAR" in row["remark"]
    assert "TFR" in row["remark"]
    assert "RFW" in row["remark"]

    reporting = _reporting_module()
    reporting._write_xlsx(model, output)
    assert output.is_file() and output.stat().st_size > 0

    with zipfile.ZipFile(output) as archive:
        xml_payload = b"\n".join(
            archive.read(name) for name in archive.namelist() if name.endswith(".xml")
        )
    assert b"FAR" in xml_payload
    assert b"TFR" in xml_payload
    assert b"RFW" in xml_payload
