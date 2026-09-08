# 归档和保护释放的无硬件回归。
# 职责：验证冻结完整性、显式释放门槛和保留当前结果。
# 边界：只操作测试临时目录，不处理真实历史证据。
# 依赖：pytest和相邻记录测试数据工厂。

from __future__ import annotations

import importlib
import io
import zipfile
from pathlib import Path
from types import ModuleType

import pytest

from .test_record_store import incoming, update


@pytest.fixture
def modules(monkeypatch: pytest.MonkeyPatch) -> tuple[ModuleType, ModuleType]:
    repository = Path(__file__).resolve().parents[5]
    monkeypatch.syspath_prepend(str(repository / "tools/runner"))
    return importlib.import_module("record_store"), importlib.import_module("record_archive")


# 测试方法：失败后成功并归档，预览再发布释放事务；通过条件：预览不写，当前结果与次数不变。
def test_archive_then_release_preserves_current_results(
    modules: tuple[ModuleType, ModuleType], tmp_path: Path
) -> None:
    store, archive = modules
    update(store, tmp_path, incoming(store, 1, status="FAIL"))
    root, _ = update(store, tmp_path, incoming(store, 2))
    output, work = tmp_path / "milestone.zip", tmp_path / "work"
    archive.create_archive(root, output, work)
    before = (root / "evidence/TEST_P0_001.json").read_bytes()
    plan, files = archive.prepare_prune(root, output.read_bytes(), work, ["TEST_P0_001"])
    assert len(plan["released"]["TEST_P0_001"]) == 2
    assert (root / "evidence/TEST_P0_001.json").read_bytes() == before
    store.publish_update(root, work, files)
    record = store.load_records(root)[0]["TEST_P0_001"]
    assert record.payload["protected"] == []
    row = store.build_view({"TEST_P0_001": record})["executions"][0]
    assert row["status"] == "PASS" and row["attempts"] == 2
    assert row["status_counts"] == {"FAIL": 1, "PASS": 1}
    assert archive.verify_archive(output.read_bytes(), work)["check"]["case_count"] == 1
    with pytest.raises(ValueError, match="new explicitly named"):
        archive.create_archive(root, output, work)


# 测试方法：归档后产生新的失败保护快照；通过条件：旧归档不能授权释放新快照。
def test_old_archive_cannot_release_unarchived_failure(
    modules: tuple[ModuleType, ModuleType], tmp_path: Path
) -> None:
    store, archive = modules
    root, _ = update(store, tmp_path, incoming(store, 1))
    output, work = tmp_path / "milestone.zip", tmp_path / "work"
    archive.create_archive(root, output, work)
    update(store, tmp_path, incoming(store, 2, status="FAIL"))
    update(store, tmp_path, incoming(store, 3))
    with pytest.raises(ValueError, match="does not cover"):
        archive.prepare_prune(root, output.read_bytes(), work, ["TEST_P0_001"])
    assert len(store.load_records(root)[0]["TEST_P0_001"].payload["protected"]) == 2


# 测试方法：修改ZIP成员但保留原清单；通过条件：校验拒绝损坏归档。
def test_archive_hash_mismatch_is_rejected(
    modules: tuple[ModuleType, ModuleType], tmp_path: Path
) -> None:
    store, archive = modules
    root, _ = update(store, tmp_path, incoming(store, 1))
    output, work = tmp_path / "milestone.zip", tmp_path / "work"
    archive.create_archive(root, output, work)
    stream = io.BytesIO()
    with zipfile.ZipFile(output) as source, zipfile.ZipFile(stream, "w") as changed:
        for name in source.namelist():
            changed.writestr(name, b"damaged" if name == "results.json" else source.read(name))
    with pytest.raises(ValueError, match="hash mismatch"):
        archive.verify_archive(stream.getvalue(), work)


# 测试方法：归档写入当前目录或超过显式目标目录预算；通过条件：拒绝且不创建新归档。
def test_archive_location_and_budget_fail_closed(
    modules: tuple[ModuleType, ModuleType], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, archive = modules
    root, _ = update(store, tmp_path, incoming(store, 1))
    work = tmp_path / "work"
    with pytest.raises(ValueError, match="outside"):
        archive.create_archive(root, root / "milestone.zip", work)
    monkeypatch.setattr(archive, "MAX_ARCHIVES", 0)
    with pytest.raises(ValueError, match="budget exceeded"):
        archive.create_archive(root, tmp_path / "milestone.zip", work)
    assert not (tmp_path / "milestone.zip").exists()
