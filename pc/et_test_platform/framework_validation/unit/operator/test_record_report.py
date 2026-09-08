# 当前档案Excel的结构和来源回归。
# 职责：检查确定性生成、数据类型、公式注入防护和损坏报告拒绝。
# 边界：合成输入，仅检查输出文件，不形成硬件结论。
# 依赖：标准库、pytest和记录测试数据工厂。

from __future__ import annotations

import importlib
import io
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from types import ModuleType

import pytest

from .test_record_store import incoming, update


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    repository = Path(__file__).resolve().parents[5]
    monkeypatch.syspath_prepend(str(repository / "tools/runner"))
    return importlib.import_module("record_store")


# 测试方法：重复生成相同记录并读取OpenXML；通过条件：字节一致，来源Hash可见，时间和次数为数值。
def test_record_report_is_deterministic_and_typed(store: ModuleType, tmp_path: Path) -> None:
    root, _ = update(store, tmp_path, incoming(store, 1))
    records = store.load_records(root)[0]
    view = store.build_view(records)
    data = store.report_bytes(view, records)
    assert data == (root / "test_report.xlsx").read_bytes()
    namespace = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(io.BytesIO(data)) as package:
        strings = package.read("xl/sharedStrings.xml").decode()
        assert view["inputs_sha256"] in strings
        assert "不代表同一版本的完整回归" in strings
        cells = ET.fromstring(package.read("xl/worksheets/sheet1.xml"))
        assert cells.find(".//s:c[@r='E6']", namespace).get("t") is None
        assert cells.find(".//s:c[@r='M6']", namespace).get("t") is None
        assert cells.find(".//s:sheetViews/s:sheetView/s:pane", namespace) is not None


# 测试方法：方法文本以等号开头并保留失败；通过条件：文本不是公式，受保护快照单独展示。
def test_report_keeps_literal_text_and_protected_evidence(
    store: ModuleType, tmp_path: Path
) -> None:
    value = incoming(store, 1, status="FAIL")
    value.cases["TEST_P0_001"][0].selection["method"] = "=1+1"
    update(store, tmp_path, value)
    latest = incoming(store, 2)
    latest.cases["TEST_P0_001"][0].selection["method"] = "=1+1"
    root, _ = update(store, tmp_path, latest)
    with zipfile.ZipFile(root / "test_report.xlsx") as package:
        strings = package.read("xl/sharedStrings.xml").decode()
        assert "=1+1" in strings and "FAIL" in strings and "PASS" in strings
        assert "受保护证据" in package.read("xl/workbook.xml").decode()
        for name in package.namelist():
            if name.startswith("xl/worksheets/") and name.endswith(".xml"):
                assert b"<f>" not in package.read(name)


# 测试方法：损坏当前报告；通过条件：完整性检查拒绝，不能当作可归档的完整记录。
def test_check_rejects_damaged_excel(store: ModuleType, tmp_path: Path) -> None:
    root, _ = update(store, tmp_path, incoming(store, 1))
    (root / "test_report.xlsx").write_bytes(b"broken")
    checker = importlib.import_module("record_check")
    with pytest.raises(ValueError, match="stale or modified.*test_report"):
        checker.check_records(root)
