# 当前事实提取与既有Excel消费者回归。
# 职责：验证精确字段读取、摘要边界、原始结果不变与报告输入一致。
# 边界：仅合成Canonical数据，不创建真实硬件结论。
# 依赖：pytest、合成Session和既有报表导出器。

from __future__ import annotations

import importlib
import io
import json
import zipfile
from pathlib import Path
from types import ModuleType

import pytest

from .test_record_source import make_session


@pytest.fixture
def reporting(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    root = Path(__file__).resolve().parents[5]
    monkeypatch.syspath_prepend(str(root / "tools/runner"))
    return importlib.import_module("record_report")


# 测试方法：先取摘要、再列字段、最后精确取值；通过条件：不重复方法全文，原值和来源保留。
def test_extract_is_bounded_and_on_demand(reporting: ModuleType, tmp_path: Path) -> None:
    source = importlib.import_module("record_source")
    run = make_session(source, tmp_path)
    incoming = source.load_input(tmp_path, run, ip="crc", lane="fpga", work=tmp_path / "work")
    original = {p.relative_to(run): p.read_bytes() for p in run.rglob("*") if p.is_file()}
    summary = reporting.render_facts(incoming).decode()
    assert "CRC_P1_001" in summary and "PASS" in summary
    assert "执行DUT刺激" not in summary and "observations" not in summary
    fields = reporting.render_facts(incoming, cases=("CRC_P1_001",)).decode()
    assert "measurement.actual_crc" in fields
    detail = reporting.render_facts(
        incoming, cases=("CRC_P1_001",), keys=("measurement.actual_crc",)
    ).decode()
    assert "measurement.actual_crc：" in detail and "\n1\n" in detail
    assert original == {p.relative_to(run): p.read_bytes() for p in run.rglob("*") if p.is_file()}


# 测试方法：请求未选Case、拼错字段、跨Case无选择取值或超限；通过条件：明确失败，不静默丢字段。
def test_extract_rejects_ambiguous_or_oversized_selection(
    reporting: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = importlib.import_module("record_source")
    run = make_session(source, tmp_path)
    incoming = source.load_input(tmp_path, run, ip="crc", lane="fpga", work=tmp_path / "work")
    for kwargs in (
        {"cases": ("CRC_P1_999",)},
        {"keys": ("measurement.actual_crc",)},
        {"cases": ("CRC_P1_001",), "keys": ("measurement.missing",)},
    ):
        with pytest.raises(ValueError):
            reporting.render_facts(incoming, **kwargs)
    monkeypatch.setattr(reporting, "MAX_FACTS_BYTES", 1)
    with pytest.raises(ValueError, match="256 KiB"):
        reporting.render_facts(incoming)


# 测试方法：选中但未执行的Case提取；通过条件：显示NOT_EXECUTED而不是继承其他PASS。
def test_extract_preserves_not_executed(reporting: ModuleType, tmp_path: Path) -> None:
    source = importlib.import_module("record_source")
    run = make_session(source, tmp_path, missing=True)
    incoming = source.load_input(tmp_path, run, ip="crc", lane="fpga", work=tmp_path / "work")
    text = reporting.render_facts(incoming).decode()
    assert "NOT_EXECUTED" in text and "| PASS |" not in text


# 测试方法：同一已校验Session生成两份内存报告；通过条件：字节确定，沿用原报告页和原始状态。
def test_report_uses_canonical_model_not_knowledge(reporting: ModuleType, tmp_path: Path) -> None:
    from tools.reporting.generate_case_report import xlsx_bytes

    source = importlib.import_module("record_source")
    run = make_session(source, tmp_path)
    incoming = source.load_input(tmp_path, run, ip="crc", lane="fpga", work=tmp_path / "work")
    data = xlsx_bytes(incoming.report_model)
    assert data == xlsx_bytes(incoming.report_model)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert archive.testzip() is None
        workbook = archive.read("xl/workbook.xml").decode()
        assert "测试报告" in workbook and "执行明细" in workbook
        assert "受保护证据" not in workbook
        assert "PASS" in archive.read("xl/sharedStrings.xml").decode()


# 测试方法：同一key包含多个端点及重复采样；通过条件：精确查询保留全部原始观测顺序与身份。
def test_extract_keeps_all_observations_for_one_key(reporting: ModuleType, tmp_path: Path) -> None:
    source = importlib.import_module("record_source")
    run = make_session(source, tmp_path)
    incoming = source.load_input(tmp_path, run, ip="crc", lane="fpga", work=tmp_path / "work")
    result = incoming.cases["CRC_P1_001"][0].result
    assert result is not None
    observations = [
        {
            "key": "protected_timings",
            "source": "dut",
            "device_id": "dut",
            "endpoint": endpoint,
            "value": value,
            "artifacts": [],
        }
        for endpoint, value in (("CAN0.NBTP", 500), ("CAN1.NBTP", 250), ("CAN0.NBTP", 500))
    ]
    result["observations"] = observations
    listing = reporting.render_facts(incoming, cases=("CRC_P1_001",)).decode()
    assert listing.count("- `observation.protected_timings`") == 1
    detail = reporting.render_facts(
        incoming, cases=("CRC_P1_001",), keys=("observation.protected_timings",)
    ).decode()
    extracted = json.loads(detail.split("````json\n")[1].split("\n````")[0])
    assert extracted == observations and len(extracted) == 3
    assert result["observations"] == observations
