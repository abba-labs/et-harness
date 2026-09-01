# AES 模拟 Canonical Result -> ET6801 寄存器名 -> Excel 报告闭环测试。
# 职责：不访问硬件，仅验证 AES 稳定 endpoint、芯片映射、ET_CASE_REPORT 和 XLSX 导出链路。
# 边界：模拟结果不能改变任何 HIL 状态，也不替代真实 AES Case。
# 依赖：AES公共契约、芯片映射和Canonical Result报告导出器。

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
    spec = importlib.util.spec_from_file_location("_et_generate_case_report", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_aes_p1_008_simulated_et6801_report_reaches_xlsx_with_real_register_names(
    tmp_path: Path,
) -> None:
    document = tmp_path / "aes.md"
    chip_document = tmp_path / "ET6801_aes.md"
    results_root = tmp_path / "run"
    output = tmp_path / "ET6801_AES_simulated.xlsx"

    document.write_text(
        """# AES Stable IP Contract

| Feature ID | 报告名称 |
|---|---|
| AES_F_013 | 运算完成状态 |
| AES_F_014 | 状态W1C清除语义 |

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: AES_P1_008
case_name: AES FINISH状态置位与W1C清除测试
report_feature: AES 完整 PROCESS 后的 FINISH 置位、输出正确性与 W1C 清除
p_level: P1
feature_refs: [AES_F_013, AES_F_014]
legacy_trace: [synthetic]
current_spec_evidence: [synthetic]
method:
  inputs:
  - 测试条件：AES-128/ECB/Encrypt+固定Key和16-byte block。
  steps:
  - 单块运算：执行PROCESS并读取Actual。
  - 清除前状态：读取STATUS.FINISH。
  - W1C清除：对FINISH执行Clear。
  - 清除后状态：再次读取STATUS.FINISH。
  observations:
  - 硬件输出结果：RESULT_DOUT[0..3] Actual与Golden一致。
  - FINISH清除前：STATUS.FINISH=1。
  - FINISH清除后：STATUS.FINISH=0。
  pass_criteria:
  - 数据正确：Actual与Golden一致。
  - FINISH置位：Clear前STATUS.FINISH=1。
  - FINISH清除：Clear后STATUS.FINISH=0。
timeout: 有界deadline
cleanup: [恢复AES状态]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外要求, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation]
failure_observations:
- {key: expected_output, label: PC Golden, source: oracle, role: expected, format: bytes_hex}
- {key: actual_output, label: "RESULT_DOUT[0..3]实际输出", source: dut, role: actual, format: bytes_hex}
- {key: actual_state, label: STATUS.FINISH清除前实际值, source: dut, role: actual, format: bit_bool}
- {key: finish_after_clear, label: STATUS.FINISH清除后实际值, source: dut, role: actual, format: bit_bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_REPORT_BEGIN -->
```yaml
schema: et.case-report-note.v1
cases:
  AES_P1_008:
    summary: AES FINISH置位、RESULT_DOUT与W1C清除的原子硬件证据。
    fields:
    - {source: measurement, path: expected_output, label: PC Golden, format: bytes_hex, aggregate: same}
    - {source: observation, path: actual_output, label: "RESULT_DOUT[0..3]实际输出", format: bytes_hex, aggregate: same}
    - {source: observation, path: actual_state, label: STATUS.FINISH清除前实际值, format: bit_bool, aggregate: same}
    - {source: observation, path: finish_after_clear, label: STATUS.FINISH清除后实际值, format: bit_bool, aggregate: same}
```
<!-- ET_CASE_REPORT_END -->
""",
        encoding="utf-8",
    )
    chip_document.write_text(
        """# ET6801 AES Chip Adaptation

| 公共稳定语义 | ET6801 实际寄存器 / Field | 用途 |
|---|---|---|
| `STATUS.FINISH` | `RPT_AES_STS.FINISH` | 完成状态 |
| `RESULT_DOUT[0..3]` | `RESULT_DOUT0~RESULT_DOUT3` | 128-bit输出 |
""",
        encoding="utf-8",
    )

    _write_json(
        results_root / "session.json",
        {
            "schema_version": 1,
            "run_id": "run-aes-simulated-report",
            "chip_id": "ET6801",
            "finished_at": "2026-08-19T13:00:00Z",
            "exitstatus": 0,
        },
    )
    _write_json(
        results_root / "cases" / "aes-p1-008" / "result.json",
        {
            "schema_version": 1,
            "run_id": "run-aes-simulated-report",
            "chip_id": "ET6801",
            "case_run_id": "aes-p1-008-simulated",
            "case_id": "aes_p1_008",
            "parameter_id": None,
            "status": "PASS",
            "duration_s": 0.01,
            "parameters": {},
            "measurements": {
                "expected_output": "69c4e0d86a7b0430d8cdb78070b4c55a",
            },
            "observations": [
                {
                    "key": "actual_output",
                    "value": "69c4e0d86a7b0430d8cdb78070b4c55a",
                    "source": "dut",
                    "device_id": "dut",
                    "endpoint": "RESULT_DOUT[0..3]",
                    "artifacts": [],
                },
                {
                    "key": "actual_state",
                    "value": True,
                    "source": "dut",
                    "device_id": "dut",
                    "endpoint": "STATUS.FINISH",
                    "artifacts": [],
                },
                {
                    "key": "finish_after_clear",
                    "value": False,
                    "source": "dut",
                    "device_id": "dut",
                    "endpoint": "STATUS.FINISH",
                    "artifacts": [],
                },
            ],
            "evidence_complete": True,
            "evidence_sources": ["dut"],
            "missing_evidence_sources": [],
            "error": None,
        },
    )

    model = build_case_report_model(document, results_root)
    row = model["cases"][0]
    assert row["status"] == "PASS"
    assert row["coverage_complete"] is True
    assert model["report_complete"] is True
    assert "RESULT_DOUT0~RESULT_DOUT3（RESULT_DOUT[0..3]实际输出）" in row["remark"]
    assert "RPT_AES_STS.FINISH（STATUS.FINISH清除前实际值）" in row["remark"]
    assert "RPT_AES_STS.FINISH（STATUS.FINISH清除后实际值）" in row["remark"]
    assert "STATUS.FINISH与RESULT_DOUT实际现场" not in row["remark"]

    reporting = _reporting_module()
    reporting._write_xlsx(model, output)
    assert output.is_file() and output.stat().st_size > 0

    with zipfile.ZipFile(output) as archive:
        xml_payload = b"\n".join(
            archive.read(name) for name in archive.namelist() if name.endswith(".xml")
        )
    assert b"RESULT_DOUT0~RESULT_DOUT3" in xml_payload
    assert b"RPT_AES_STS.FINISH" in xml_payload
