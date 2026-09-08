# 固定记录完整性检查的无硬件回归。
# 职责：验证派生视图、文件集合和人工区域的检查边界。
# 边界：合成证据不代表芯片验证。
# 依赖：pytest和相邻记录测试数据工厂。

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from .test_record_store import incoming, update


@pytest.fixture
def records(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repository = Path(__file__).resolve().parents[5]
    monkeypatch.syspath_prepend(str(repository / "tools/runner"))
    store = importlib.import_module("record_store")
    root, _ = update(store, tmp_path, incoming(store, 1))
    return root


# 测试方法：验证完整记录后追加人工结论；通过条件：两次检查均通过，Hash反映修改。
def test_check_accepts_manual_analysis_and_hashes_all_files(records: Path) -> None:
    checker = importlib.import_module("record_check")
    first = checker.check_records(records)
    path = records / "cases/TEST_P0_001.md"
    path.write_text(path.read_text(encoding="utf-8") + "\n人工分析。\n", encoding="utf-8")
    second = checker.check_records(records)
    assert first["status"] == second["status"] == "PASS"
    assert first["files"]["cases/TEST_P0_001.md"] != second["files"]["cases/TEST_P0_001.md"]
    assert first["snapshots"] == second["snapshots"]


# 测试方法：分别破坏机器JSON或自动文档；通过条件：拒绝陈旧派生数据。
@pytest.mark.parametrize("name", ["results.json", "README.md", "cases/TEST_P0_001.md"])
def test_check_rejects_modified_generated_views(records: Path, name: str) -> None:
    checker = importlib.import_module("record_check")
    path = records / name
    text = path.read_text(encoding="utf-8")
    if name == "results.json":
        text = text.replace('"PASS"', '"FAIL"')
    else:
        text = text.replace(
            "<!-- ET_RECORD_AUTO_BEGIN -->", "<!-- ET_RECORD_AUTO_BEGIN -->\n破坏内容"
        )
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="stale or modified"):
        checker.check_records(records)


# 测试方法：额外文件、Run子目录或缺失文档；通过条件：拒绝且不自动删除或修复。
@pytest.mark.parametrize("kind", ["extra", "directory", "missing"])
def test_check_rejects_unexpected_layout(records: Path, kind: str) -> None:
    checker = importlib.import_module("record_check")
    if kind == "extra":
        (records / "notes.txt").write_text("keep", encoding="utf-8")
    elif kind == "directory":
        (records / "run-20260908").mkdir()
    else:
        (records / "README.md").unlink()
    with pytest.raises(ValueError, match="membership mismatch|unexpected record directory"):
        checker.check_records(records)
    if kind == "extra":
        assert (records / "notes.txt").read_text(encoding="utf-8") == "keep"
