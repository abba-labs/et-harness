# DMA 模拟 Canonical Result -> ET6801 寄存器名 -> Excel 报告闭环测试。
# 职责：不访问硬件，验证真实 DMA Contract、芯片 endpoint 映射、ET_CASE_REPORT 和 XLSX 导出链路。
# 边界：模拟结果只验证报告软件链，不能改变当前 SHA 的 FPGA/Silicon HIL 状态。
# 依赖：DMA公共契约、芯片映射和Canonical Result报告导出器。

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
    spec = importlib.util.spec_from_file_location("_et_generate_case_report_dma", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _case_row(model: dict[str, object], case_id: str) -> dict[str, object]:
    rows = model["cases"]
    assert isinstance(rows, list)
    return next(row for row in rows if row["case_id"] == case_id)


def test_dma_simulated_et6801_report_uses_real_register_names_and_exports_xlsx(
    tmp_path: Path,
) -> None:
    repository_root = Path(__file__).resolve().parents[5]
    document = repository_root / "test_case_doc" / "dma" / "dma.md"
    results_root = tmp_path / "run"
    output = tmp_path / "ET6801_DMA_simulated.xlsx"

    _write_json(
        results_root / "session.json",
        {
            "schema_version": 1,
            "run_id": "run-dma-simulated-report",
            "chip_id": "ET6801",
            "finished_at": "2026-08-19T15:00:00Z",
            "exitstatus": 0,
            "selection": {
                "selected_case_ids": ["dma_p1_010", "dma_p1_015"],
                "selected_executions": [
                    {"case_id": "dma_p1_010", "parameter_id": None},
                    {"case_id": "dma_p1_015", "parameter_id": None},
                ],
            },
        },
    )

    _write_json(
        results_root / "cases" / "dma-p1-010" / "result.json",
        {
            "schema_version": 1,
            "run_id": "run-dma-simulated-report",
            "chip_id": "ET6801",
            "case_run_id": "dma-p1-010-simulated",
            "case_id": "dma_p1_010",
            "parameter_id": None,
            "status": "PASS",
            "duration_s": 0.01,
            "measurements": {"expected_fifo_mode": "half_depth", "data_match": True},
            "observations": [
                {
                    "key": "actual_fifo_mode",
                    "value": "half_depth",
                    "source": "dut",
                    "device_id": "dut",
                    "endpoint": "DMA_CHANNEL_CFG.FIFO_MODE",
                    "artifacts": [],
                },
                {
                    "key": "channel_free",
                    "value": True,
                    "source": "dut",
                    "device_id": "dut",
                    "endpoint": "DMA_CHANNEL_STATUS.FREE",
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

    _write_json(
        results_root / "cases" / "dma-p1-015" / "result.json",
        {
            "schema_version": 1,
            "run_id": "run-dma-simulated-report",
            "chip_id": "ET6801",
            "case_run_id": "dma-p1-015-simulated",
            "case_id": "dma_p1_015",
            "parameter_id": None,
            "status": "PASS",
            "duration_s": 0.01,
            "measurements": {"expected_block_size": 257},
            "observations": [
                {
                    "key": "actual_block_size",
                    "value": 257,
                    "source": "dut",
                    "device_id": "dut",
                    "endpoint": "DMA_CHANNEL_CTL.BLOCK_SIZE",
                    "artifacts": [],
                },
                {
                    "key": "actual_source_burst",
                    "value": "items_64",
                    "source": "dut",
                    "device_id": "dut",
                    "endpoint": "DMA_CHANNEL_CTL.SOURCE_BURST",
                    "artifacts": [],
                },
                {
                    "key": "actual_destination_burst",
                    "value": "items_64",
                    "source": "dut",
                    "device_id": "dut",
                    "endpoint": "DMA_CHANNEL_CTL.DESTINATION_BURST",
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
    fifo_row = _case_row(model, "DMA_P1_010")
    burst_row = _case_row(model, "DMA_P1_015")

    assert model["report_complete"] is True
    assert fifo_row["status"] == "PASS"
    assert fifo_row["coverage_complete"] is True
    assert "CFGX_H32.FIFO_MODE" in fifo_row["remark"]

    assert burst_row["status"] == "PASS"
    assert burst_row["coverage_complete"] is True
    assert "CTLX_H32.BLOCK_TS" in burst_row["remark"]
    assert "CTLX_L32.SRC_MSIZE" in burst_row["remark"]
    assert "CTLX_L32.DEST_MSIZE" in burst_row["remark"]

    reporting = _reporting_module()
    reporting._write_xlsx(model, output)
    assert output.is_file() and output.stat().st_size > 0

    with zipfile.ZipFile(output) as archive:
        xml_payload = b"\n".join(
            archive.read(name) for name in archive.namelist() if name.endswith(".xml")
        )
    assert b"CFGX_H32.FIFO_MODE" in xml_payload
    assert b"CTLX_H32.BLOCK_TS" in xml_payload
    assert b"CTLX_L32.SRC_MSIZE" in xml_payload
    assert b"CTLX_L32.DEST_MSIZE" in xml_payload
