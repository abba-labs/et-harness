# Formal Case 人工报告模型单元测试。
#
# 职责：验证参数化聚合、结构化失败备注和运行异常降级规则。
# 边界：只使用临时 Markdown/JSON，不执行真实硬件、不验证 Excel 渲染。
# 依赖：仅依赖 case_report 纯报告汇总逻辑和 pytest 临时目录。

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from et_test_platform.results.case_report import (
    _aggregate_note_values,
    _format_observation_value,
    _format_value,
    build_case_report_model,
)


def _reporting_module() -> ModuleType:
    repository_root = Path(__file__).resolve().parents[5]
    script = repository_root / "tools" / "reporting" / "generate_case_report.py"
    spec = importlib.util.spec_from_file_location("_et_generate_case_report_status", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_format_value_renders_nested_evidence_as_human_text() -> None:
    value = [
        {"actual": "A1B2", "finish": True},
        {"actual": "C3D4", "finish": True},
    ]

    rendered = _format_value(value)

    assert rendered == "actual=A1B2；finish=true、actual=C3D4；finish=true"
    assert "{" not in rendered
    assert "}" not in rendered


# 公共报告字段不能用None伪装参数分支缺失；缺值必须让报告门禁失败。
def test_report_note_rejects_missing_required_value() -> None:
    with pytest.raises(ValueError, match="missing required value"):
        _aggregate_note_values([1, None], "all")


# Excel结果列必须展示每一种稳定报告状态，不能用空单元格隐藏SKIP或报告异常。
@pytest.mark.parametrize(
    "status",
    [
        "PASS",
        "FAIL",
        "SKIP",
        "EVIDENCE_MISSING",
        "NOT_EXECUTED",
        "NOT_SELECTED",
        "RUN_ERROR",
    ],
)
def test_excel_report_result_never_hides_known_status(status: str) -> None:
    assert _reporting_module()._report_result(status) == status


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _spec(
    case_id: str,
    report_feature: str,
    failure_observations: str,
) -> str:
    return f"""
<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: {case_id}
case_name: {report_feature}测试
report_feature: {report_feature}
p_level: P1
feature_refs:
  - CRC_F_001
legacy_trace:
  - synthetic
current_spec_evidence:
  - synthetic
method:
  inputs:
    - 确定性输入
  steps:
    - 执行DUT刺激
    - 读取硬件结果
  observations:
    - 硬件结果
  pass_criteria:
    - 硬件结果满足期望
timeout: 有界deadline
cleanup:
  - 恢复DUT
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 无额外要求
  bench: 无额外要求
backend:
  - FPGA
evidence:
  - actual
failure_observations:
{failure_observations}
gap: []
```
<!-- ET_CASE_SPEC_END -->
"""


def _write_document(path: Path) -> None:
    failure = """  - key: expected_crc
    label: 期望CRC值
    source: oracle
  - key: actual_crc
    label: 硬件实际CRC值
    source: dut"""
    document = """# CRC

| Feature ID | 报告名称 |
|---|---|
| CRC_F_001 | CRC测试能力 |
"""
    document += _spec("CRC_P1_001", "参数化CRC结果正确", failure)
    document += _spec("CRC_P1_002", "DUT失败结构化展示", failure)
    document += _spec("CRC_P1_003", "运行异常不伪装硬件失败", failure)
    document += _spec("CRC_P1_004", "证据完整性检查", failure)
    document += _spec("CRC_P1_005", "Capability条件执行", failure)
    document += _spec("CRC_P1_006", "未执行Case展示", failure)
    path.write_text(document, encoding="utf-8")


def _result(
    case_id: str,
    status: str,
    *,
    parameter_id: str | None = None,
    measurements: dict[str, object] | None = None,
    observations: list[dict[str, object]] | None = None,
    missing_evidence: list[str] | None = None,
    error: str | None = None,
    run_id: str = "run-1",
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "run_id": run_id,
        "chip_id": "ET6801",
        "case_run_id": f"{case_id.lower()}-{parameter_id or 'default'}",
        "case_id": case_id.lower(),
        "parameter_id": parameter_id,
        "status": status,
        "duration_s": 0.01,
        "parameters": {"parameter_id": parameter_id} if parameter_id else {},
        "measurements": measurements or {},
        "observations": observations or [],
        "evidence_complete": status != "EVIDENCE_MISSING",
        "evidence_sources": ["dut"] if measurements else [],
        "missing_evidence_sources": missing_evidence or [],
        "error": error,
    }


def test_case_report_aggregates_stable_cases_without_replacing_canonical_status(
    tmp_path: Path,
) -> None:
    document = tmp_path / "CRC.md"
    results_root = tmp_path / "run"
    _write_document(document)
    _write_json(
        results_root / "session.json",
        {
            "schema_version": 1,
            "run_id": "run-1",
            "chip_id": "ET6801",
            "finished_at": "2026-08-12T12:00:00Z",
            "exitstatus": 1,
        },
    )

    cases = [
        _result(
            "CRC_P1_001",
            "PASS",
            parameter_id="poly-a",
            measurements={"expected_crc": 0x1234, "actual_crc": 0x1234},
        ),
        _result(
            "CRC_P1_001",
            "PASS",
            parameter_id="poly-b",
            measurements={"expected_crc": 0x5678, "actual_crc": 0x5678},
        ),
        _result(
            "CRC_P1_002",
            "FAIL",
            parameter_id="bad-vector",
            measurements={"expected_crc": 4660, "actual_crc": 22136},
            error="AssertionError: should never appear in human FAIL remark",
        ),
        _result(
            "CRC_P1_003",
            "FAIL",
            parameter_id="fixture-crash",
            error="Traceback: serial fixture failed",
        ),
        _result(
            "CRC_P1_004",
            "EVIDENCE_MISSING",
            missing_evidence=["dut", "fpga"],
        ),
        _result("CRC_P1_005", "SKIP", error="capability missing"),
    ]
    for index, result in enumerate(cases, start=1):
        _write_json(results_root / "cases" / f"case-{index}" / "result.json", result)

    model = build_case_report_model(document, results_root)
    by_id = {row["case_id"]: row for row in model["cases"]}

    assert model["schema"] == "et.case-report.v1"
    assert model["chip_name"] == "ET6801"
    assert model["summary"]["stable_case_count"] == 6
    assert model["summary"]["execution_count"] == 6

    assert by_id["CRC_P1_001"]["status"] == "PASS"
    assert by_id["CRC_P1_001"]["execution_count"] == 2

    hardware_fail = by_id["CRC_P1_002"]
    assert hardware_fail["status"] == "FAIL"
    assert "参数实例: bad-vector" in hardware_fail["remark"]
    assert "期望CRC值: 4660" in hardware_fail["remark"]
    assert "硬件实际CRC值: 22136" in hardware_fail["remark"]
    assert "AssertionError" not in hardware_fail["remark"]

    run_error = by_id["CRC_P1_003"]
    assert run_error["status"] == "RUN_ERROR"
    assert run_error["status_label"] == "运行异常/报告不完整"
    assert "Traceback" not in run_error["remark"]

    evidence_missing = by_id["CRC_P1_004"]
    assert evidence_missing["status"] == "EVIDENCE_MISSING"
    assert "dut；fpga" in evidence_missing["remark"]

    skipped = by_id["CRC_P1_005"]
    assert skipped["status"] == "SKIP"
    assert "完整 PASS 证据" in skipped["remark"]

    not_executed = by_id["CRC_P1_006"]
    assert not_executed["status"] == "NOT_EXECUTED"
    assert "未发现" in not_executed["remark"]


def test_case_report_mixed_pass_and_skip_is_not_reported_as_pass(tmp_path: Path) -> None:
    document = tmp_path / "CRC.md"
    results_root = tmp_path / "run"
    _write_document(document)
    _write_json(
        results_root / "session.json",
        {
            "schema_version": 1,
            "run_id": "run-2",
            "finished_at": "2026-08-12T12:00:00Z",
            "exitstatus": 0,
        },
    )
    _write_json(
        results_root / "cases" / "pass" / "result.json",
        _result("CRC_P1_001", "PASS", parameter_id="supported", run_id="run-2"),
    )
    _write_json(
        results_root / "cases" / "skip" / "result.json",
        _result("CRC_P1_001", "SKIP", parameter_id="unsupported", run_id="run-2"),
    )

    model = build_case_report_model(document, results_root)
    row = next(item for item in model["cases"] if item["case_id"] == "CRC_P1_001")

    assert row["status"] == "SKIP"
    assert row["status_label"] == "未执行(SKIP)"
    assert model["session_complete"] is True
    assert model["report_complete"] is False


def test_case_report_distinguishes_not_selected_from_missing_execution(tmp_path: Path) -> None:
    document = tmp_path / "CRC.md"
    results_root = tmp_path / "run"
    _write_document(document)
    _write_json(
        results_root / "session.json",
        {
            "schema_version": 1,
            "run_id": "run-selection",
            "finished_at": "2026-08-12T12:00:00Z",
            "exitstatus": 0,
            "selection": {
                "collected_count": 2,
                "selected_count": 1,
                "deselected_count": 1,
                "selected_case_ids": ["crc_p1_001"],
                "selected_executions": [
                    {
                        "case_id": "crc_p1_001",
                        "parameter_id": "only",
                        "node_id": "test_crc.py::test_crc[only]",
                    }
                ],
            },
        },
    )
    _write_json(
        results_root / "cases" / "selected" / "result.json",
        _result(
            "CRC_P1_001",
            "PASS",
            parameter_id="only",
            measurements={"expected_crc": 0x1234, "actual_crc": 0x1234},
            run_id="run-selection",
        ),
    )

    model = build_case_report_model(document, results_root)
    by_id = {row["case_id"]: row for row in model["cases"]}

    assert by_id["CRC_P1_001"]["status"] == "PASS"
    assert by_id["CRC_P1_002"]["status"] == "NOT_SELECTED"
    assert model["report_complete"] is True


@pytest.mark.parametrize(
    ("case_id", "run_id", "message"),
    [
        ("CRC_P1_999", "run-integrity", "unknown Case ID"),
        ("CRC_P1_001", "another-run", "does not match session"),
    ],
)
def test_case_report_rejects_foreign_or_unknown_results(
    tmp_path: Path,
    case_id: str,
    run_id: str,
    message: str,
) -> None:
    document = tmp_path / "CRC.md"
    results_root = tmp_path / "run"
    _write_document(document)
    _write_json(
        results_root / "session.json",
        {"schema_version": 1, "run_id": "run-integrity"},
    )
    _write_json(
        results_root / "cases" / "foreign" / "result.json",
        _result(case_id, "PASS", run_id=run_id),
    )

    with pytest.raises(ValueError, match=message):
        build_case_report_model(document, results_root)


def test_case_report_requires_canonical_session(tmp_path: Path) -> None:
    document = tmp_path / "CRC.md"
    _write_document(document)

    with pytest.raises(ValueError, match="session.json is missing"):
        build_case_report_model(document, tmp_path / "run")


# PASS 与 FAIL 共用同一 Observation 备注；状态只影响结果列，不改变硬件证据展示。
@pytest.mark.parametrize("status", ["PASS", "FAIL"])
def test_case_report_renders_same_hardware_observation_for_pass_and_fail(
    tmp_path: Path,
    status: str,
) -> None:
    document = tmp_path / "CRC.md"
    results_root = tmp_path / "run"
    detailed = """  - key: expected_crc
    label: 期望CRC值
    source: oracle
    role: expected
    format: hex32
  - key: actual_crc
    label: CRC结果寄存器值
    source: dut
    role: actual
    format: hex32
    semantic_ref: crc.feature.result"""
    text = "# CRC\n\n| Feature ID | 报告名称 |\n|---|---|\n| CRC_F_001 | CRC测试能力 |\n"
    text += _spec("CRC_P1_001", "CRC结果", detailed)
    document.write_text(text, encoding="utf-8")
    _write_json(
        results_root / "session.json",
        {
            "schema_version": 1,
            "run_id": "run-observation",
            "chip_id": "ET6801",
            "finished_at": "2026-08-13T12:00:00Z",
            "exitstatus": 0 if status == "PASS" else 1,
        },
    )
    _write_json(
        results_root / "cases" / "observation" / "result.json",
        _result(
            "CRC_P1_001",
            status,
            run_id="run-observation",
            measurements={"expected_crc": 0xAD37D056},
            observations=[
                {
                    "key": "actual_crc",
                    "value": 0xAD37D056,
                    "source": "dut",
                    "device_id": "dut",
                    "endpoint": "crc0",
                    "artifacts": [],
                }
            ],
        ),
    )

    model = build_case_report_model(document, results_root)
    remark = model["cases"][0]["remark"]
    assert "期望CRC值: 0xAD37D056" in remark
    assert "DUT / ET6801 / crc0 / CRC.RES" in remark
    assert "CRC结果寄存器值: 0xAD37D056" in remark


# 报告不得使用 failure_observations 二次改写 Canonical PASS；
# 人工展示字段应只按 ET_CASE_REPORT 从真实 Observation 解析。
def test_case_report_keeps_canonical_pass_when_report_observation_is_resolvable(
    tmp_path: Path,
) -> None:
    document = tmp_path / "CRC.md"
    results_root = tmp_path / "run"
    spec = _spec(
        "CRC_P1_001",
        "CRC结果",
        """  - key: actual_crc
    label: CRC结果
    source: measurement
    role: actual
    format: hex32""",
    )
    note = """
<!-- ET_CASE_REPORT_BEGIN -->
```yaml
schema: et.case-report-note.v1
cases:
  CRC_P1_001:
    summary: CRC硬件结果正确。
    fields:
      - {source: observation, path: actual_crc, label: CRC结果, format: hex32, aggregate: same}
```
<!-- ET_CASE_REPORT_END -->
"""
    document.write_text(
        "# CRC\n\n| Feature ID | 报告名称 |\n|---|---|\n| CRC_F_001 | CRC测试能力 |\n"
        + spec
        + note,
        encoding="utf-8",
    )
    _write_json(
        results_root / "session.json",
        {
            "schema_version": 1,
            "run_id": "run-observation-source",
            "chip_id": "ET6801",
            "finished_at": "2026-08-27T12:00:00Z",
            "exitstatus": 0,
        },
    )
    _write_json(
        results_root / "cases" / "observation" / "result.json",
        _result(
            "CRC_P1_001",
            "PASS",
            run_id="run-observation-source",
            observations=[
                {
                    "key": "actual_crc",
                    "value": 0xAD37D056,
                    "source": "dut",
                    "device_id": "dut",
                    "endpoint": "RESULT.VALUE",
                    "artifacts": [],
                }
            ],
        ),
    )

    model = build_case_report_model(document, results_root)
    row = model["cases"][0]
    assert row["status"] == "PASS"
    assert row["coverage_complete"] is True
    assert "CRC结果：0xAD37D056" in row["remark"]


# Canonical PASS 已形成但 ET_CASE_REPORT 必选字段不存在时，报告必须失败关闭，
# 不能静默生成一个测试结果为空白的“不完整”Excel。
def test_case_report_rejects_unresolvable_required_report_field(tmp_path: Path) -> None:
    document = tmp_path / "CRC.md"
    results_root = tmp_path / "run"
    spec = _spec(
        "CRC_P1_001",
        "CRC结果",
        """  - key: actual_crc
    label: CRC结果
    source: dut
    role: actual
    format: hex32""",
    )
    note = """
<!-- ET_CASE_REPORT_BEGIN -->
```yaml
schema: et.case-report-note.v1
cases:
  CRC_P1_001:
    summary: CRC硬件结果正确。
    fields:
      - {source: observation, path: actual_crc, label: CRC结果, format: hex32, aggregate: same}
```
<!-- ET_CASE_REPORT_END -->
"""
    document.write_text(
        "# CRC\n\n| Feature ID | 报告名称 |\n|---|---|\n| CRC_F_001 | CRC测试能力 |\n"
        + spec
        + note,
        encoding="utf-8",
    )
    _write_json(
        results_root / "session.json",
        {
            "schema_version": 1,
            "run_id": "run-missing-report-field",
            "finished_at": "2026-08-27T12:00:00Z",
            "exitstatus": 0,
        },
    )
    _write_json(
        results_root / "cases" / "missing" / "result.json",
        _result("CRC_P1_001", "PASS", run_id="run-missing-report-field"),
    )

    with pytest.raises(ValueError, match="report note field cannot be resolved"):
        build_case_report_model(document, results_root)


# Observation 格式化必须拒绝越界或歧义输入，不能静默截断成看似合法的硬件值。
@pytest.mark.parametrize(
    ("value", "format_name"),
    [
        (True, "hex32"),
        (-1, "hex8"),
        (0x100, "hex8"),
        (2, "bit_bool"),
        (7, "bool"),
        ([-1, 0x100], "bytes_hex"),
        ("0G", "bytes_hex"),
    ],
)
def test_observation_formatter_rejects_ambiguous_or_out_of_range_values(
    value: object,
    format_name: str,
) -> None:
    with pytest.raises(ValueError, match="invalid"):
        _format_observation_value(value, format_name, "")


# Count既可表示已完成事务的非负计数，也可表示集合的元素数量；两种形式均不得依赖自由文本转换。
def test_observation_formatter_accepts_scalar_and_collection_counts() -> None:
    assert _format_observation_value(7, "count", "") == "7"
    assert _format_observation_value([1, 2, 3], "count", "") == "3"

    with pytest.raises(ValueError, match="invalid count"):
        _format_observation_value(-1, "count", "")


# 标记迁移缺口的旧 Case 只能通过 canonical result 已绑定的结构化 JSON 补充备注，
# 报告层不得扫描目录或解析自由文本。
def test_case_report_uses_bound_structured_artifact_for_measurement_gap(tmp_path: Path) -> None:
    document = tmp_path / "DMA.md"
    results_root = tmp_path / "run"
    spec = _spec(
        "CRC_P1_001",
        "兼容结构化附件",
        """  - key: expected_state
    label: 期望状态
    source: oracle
    role: expected
    format: text
  - key: actual_state
    label: 硬件状态
    source: dut
    role: actual
    format: text""",
    ).replace("gap: []", "gap:\n  - case_measurement_gap")
    document.write_text(
        "# DMA\n\n| Feature ID | 报告名称 |\n|---|---|\n| CRC_F_001 | 兼容 |\n" + spec,
        encoding="utf-8",
    )
    evidence = results_root / "dma_p1_001.json"
    _write_json(evidence, {"measurement_schema": "et.measurement.v1", "data_match": True})
    _write_json(results_root / "session.json", {"schema_version": 1, "run_id": "run-gap"})
    result = _result("CRC_P1_001", "PASS", run_id="run-gap")
    result["artifacts"] = {"measurement_artifact_result": str(evidence)}
    _write_json(results_root / "cases" / "gap" / "result.json", result)

    model = build_case_report_model(document, results_root)
    row = model["cases"][0]
    assert row["status"] == "PASS"
    assert row["coverage_complete"] is True
    assert "详细硬件数据已保存为结构化原始证据" in row["remark"]
    assert "data_match" not in row["remark"]


# 人读备注只消费 IP 文档白名单字段；完整 JSON 继续作为原始证据保留，不能直接铺进 Excel。
def test_case_report_note_template_summarizes_bound_artifact(tmp_path: Path) -> None:
    document = tmp_path / "DMA.md"
    results_root = tmp_path / "run"
    spec = _spec(
        "CRC_P1_001",
        "DMA数据传输",
        """  - key: expected_state
    label: 期望状态
    source: oracle
    role: expected
    format: text
  - key: actual_state
    label: 硬件状态
    source: dut
    role: actual
    format: text""",
    ).replace("gap: []", "gap:\n  - case_measurement_gap")
    note = """
<!-- ET_CASE_REPORT_BEGIN -->
```yaml
schema: et.case-report-note.v1
cases:
  CRC_P1_001:
    summary: DMA数据传输验证完成。
    fields:
    - source: artifact
      path: bytes
      label: 传输字节数
      format: decimal
      aggregate: range
      unit: 字节
    - source: artifact
      path: data_match
      label: 数据一致
      format: bool
      aggregate: same
```
<!-- ET_CASE_REPORT_END -->
"""
    document.write_text(
        "# DMA\n\n| Feature ID | 报告名称 |\n|---|---|\n| CRC_F_001 | 兼容 |\n" + spec + note,
        encoding="utf-8",
    )
    _write_json(results_root / "session.json", {"schema_version": 1, "run_id": "run-note"})
    for index, size in enumerate((1, 64), start=1):
        evidence = results_root / f"dma-{index}.json"
        _write_json(
            evidence,
            {
                "measurement_schema": "et.measurement.v1",
                "bytes": size,
                "data_match": True,
                "large_nested_payload": {"must_not_appear": list(range(100))},
            },
        )
        result = _result(
            "CRC_P1_001",
            "PASS",
            parameter_id=str(index),
            run_id="run-note",
        )
        result["artifacts"] = {"measurement_artifact_result": str(evidence)}
        _write_json(results_root / "cases" / str(index) / "result.json", result)

    row = build_case_report_model(document, results_root)["cases"][0]
    assert row["remark"] == ("DMA数据传输验证完成。\n传输字节数：1 字节 ～ 64 字节\n数据一致：true")
    assert "large_nested_payload" not in row["remark"]


# 模板路径与 Case 产物不一致时必须失败，防止文档与代码悄悄漂移。
def test_case_report_note_template_rejects_unresolved_field(tmp_path: Path) -> None:
    document = tmp_path / "DMA.md"
    results_root = tmp_path / "run"
    spec = _spec(
        "CRC_P1_001",
        "DMA数据传输",
        """  - key: expected_state
    label: 期望状态
    source: oracle
    role: expected
    format: text
  - key: actual_state
    label: 硬件状态
    source: dut
    role: actual
    format: text""",
    ).replace("gap: []", "gap:\n  - case_measurement_gap")
    document.write_text(
        "# DMA\n\n| Feature ID | 报告名称 |\n|---|---|\n| CRC_F_001 | 兼容 |\n"
        + spec
        + """
<!-- ET_CASE_REPORT_BEGIN -->
```yaml
schema: et.case-report-note.v1
cases:
  CRC_P1_001:
    summary: DMA数据传输验证完成。
    fields:
    - source: artifact
      path: missing_field
      label: 不存在字段
      format: text
      aggregate: same
```
<!-- ET_CASE_REPORT_END -->
""",
        encoding="utf-8",
    )
    evidence = results_root / "dma.json"
    _write_json(evidence, {"measurement_schema": "et.measurement.v1", "bytes": 8})
    _write_json(results_root / "session.json", {"schema_version": 1, "run_id": "run-drift"})
    result = _result("CRC_P1_001", "PASS", run_id="run-drift")
    result["artifacts"] = {"measurement_artifact_result": str(evidence)}
    _write_json(results_root / "cases" / "drift" / "result.json", result)

    with pytest.raises(ValueError, match="report note field cannot be resolved"):
        build_case_report_model(document, results_root)


# ET_CASE_REPORT 一旦启用就必须覆盖文档内全部稳定 Case，不能依赖外部门禁补齐运行时契约。
def test_case_report_note_template_requires_complete_case_coverage(tmp_path: Path) -> None:
    document = tmp_path / "DMA.md"
    failure = """  - key: expected_state
    label: 期望状态
    source: oracle
  - key: actual_state
    label: 硬件状态
    source: dut"""
    document.write_text(
        "# DMA\n\n| Feature ID | 报告名称 |\n|---|---|\n| CRC_F_001 | 兼容 |\n"
        + _spec("CRC_P1_001", "第一项", failure)
        + _spec("CRC_P1_002", "第二项", failure)
        + """
<!-- ET_CASE_REPORT_BEGIN -->
```yaml
schema: et.case-report-note.v1
cases:
  CRC_P1_001:
    summary: 第一项验证完成。
    fields:
    - source: measurement
      path: value
      label: 硬件值
      format: decimal
      aggregate: same
```
<!-- ET_CASE_REPORT_END -->
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must exactly match"):
        build_case_report_model(document, tmp_path / "run")


# 报告解析器必须独立拒绝非法格式，避免关闭软件门禁时把拼写错误静默当作普通文本。
def test_case_report_note_template_rejects_invalid_format_at_runtime(tmp_path: Path) -> None:
    document = tmp_path / "DMA.md"
    document.write_text(
        "# DMA\n\n| Feature ID | 报告名称 |\n|---|---|\n| CRC_F_001 | 兼容 |\n"
        + _spec(
            "CRC_P1_001",
            "DMA数据传输",
            """  - key: expected_state
    label: 期望状态
    source: oracle
  - key: actual_state
    label: 硬件状态
    source: dut""",
        )
        + """
<!-- ET_CASE_REPORT_BEGIN -->
```yaml
schema: et.case-report-note.v1
cases:
  CRC_P1_001:
    summary: DMA数据传输验证完成。
    fields:
    - source: measurement
      path: value
      label: 硬件值
      format: hexadecimal
      aggregate: same
```
<!-- ET_CASE_REPORT_END -->
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid ET_CASE_REPORT field"):
        build_case_report_model(document, tmp_path / "run")


# AES 报告通过 chip_id 选择同目录芯片文档，将稳定端点解析为 ET6801 实际寄存器名。
def test_case_report_note_resolves_et6801_register_names_from_chip_document(tmp_path: Path) -> None:
    document = tmp_path / "aes.md"
    chip_document = tmp_path / "ET6801_aes.md"
    results_root = tmp_path / "run"
    failure = """  - key: finish_status
    label: STATUS.FINISH实际值
    source: dut
    role: actual
    format: bit_bool
  - key: actual_output
    label: RESULT_DOUT[0..3]实际输出
    source: dut
    role: actual
    format: bytes_hex
  - key: actual_irq_status
    label: IRQ_STATUS.COMPLETE实际值
    source: dut
    role: actual
    format: hex32"""
    note = """
<!-- ET_CASE_REPORT_BEGIN -->
```yaml
schema: et.case-report-note.v1
cases:
  AES_P1_001:
    summary: AES模拟Evidence的芯片寄存器名解析。
    fields:
    - {source: observation, path: finish_status, label: "STATUS.FINISH实际值", format: bit_bool, aggregate: same}
    - {source: observation, path: actual_output, label: "RESULT_DOUT[0..3]实际输出", format: bytes_hex, aggregate: same}
    - {source: observation, path: actual_irq_status, label: "IRQ_STATUS.COMPLETE实际值", format: hex32, aggregate: same}
```
<!-- ET_CASE_REPORT_END -->
"""
    document.write_text(
        "# AES\n\n| Feature ID | 报告名称 |\n|---|---|\n| AES_F_001 | AES模拟能力 |\n"
        + _spec("AES_P1_001", "AES芯片寄存器解析", failure)
        + note,
        encoding="utf-8",
    )
    chip_document.write_text(
        """# ET6801 AES Chip Adaptation

| 公共稳定语义 | ET6801 实际寄存器 / Field | 用途 |
|---|---|---|
| `STATUS.FINISH` | `RPT_AES_STS.FINISH` | 完成状态 |
| `RESULT_DOUT[0..3]` | `RESULT_DOUT0~RESULT_DOUT3` | 128-bit输出 |
| `IRQ_STATUS.<Source>` | `RPT_AES_INT_STATUS.<Source bit>` | IRQ状态 |
""",
        encoding="utf-8",
    )
    _write_json(
        results_root / "session.json",
        {
            "schema_version": 1,
            "run_id": "run-aes-register-map",
            "chip_id": "ET6801",
            "finished_at": "2026-08-19T12:00:00Z",
            "exitstatus": 0,
        },
    )
    _write_json(
        results_root / "cases" / "aes" / "result.json",
        _result(
            "AES_P1_001",
            "PASS",
            run_id="run-aes-register-map",
            observations=[
                {
                    "key": "finish_status",
                    "value": True,
                    "source": "dut",
                    "device_id": "dut",
                    "endpoint": "STATUS.FINISH",
                    "artifacts": [],
                },
                {
                    "key": "actual_output",
                    "value": "69c4e0d86a7b0430d8cdb78070b4c55a",
                    "source": "dut",
                    "device_id": "dut",
                    "endpoint": "RESULT_DOUT[0..3]",
                    "artifacts": [],
                },
                {
                    "key": "actual_irq_status",
                    "value": 0,
                    "source": "dut",
                    "device_id": "dut",
                    "endpoint": "IRQ_STATUS.COMPLETE",
                    "artifacts": [],
                },
            ],
        ),
    )

    row = build_case_report_model(document, results_root)["cases"][0]
    assert row["status"] == "PASS"
    assert "RPT_AES_STS.FINISH（STATUS.FINISH实际值）" in row["remark"]
    assert "RESULT_DOUT0~RESULT_DOUT3（RESULT_DOUT[0..3]实际输出）" in row["remark"]
    assert "RPT_AES_INT_STATUS.COMPLETE（IRQ_STATUS.COMPLETE实际值）" in row["remark"]
