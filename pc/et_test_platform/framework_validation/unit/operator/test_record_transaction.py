# 固定目录记录事务的无硬件回归。
# 职责：验证原子发布、幂等、故障恢复和路径隔离。
# 边界：仅操作pytest临时目录，不接触用户测试证据。
# 依赖：标准库、pytest与记录事务工具。

from __future__ import annotations

import importlib
from pathlib import Path
from types import ModuleType

import pytest


@pytest.fixture
def transaction(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    root = Path(__file__).resolve().parents[5]
    monkeypatch.syspath_prepend(str(root / "tools/runner"))
    return importlib.import_module("record_transaction")


# 测试方法：重复发布同一文件集；通过条件：第二次不写文件，不增加目录。
def test_publish_is_idempotent(transaction: ModuleType, tmp_path: Path) -> None:
    root, work = tmp_path / "records", tmp_path / "work"
    files = {"cases/CAN_P0_001.md": b"case", "evidence/CAN_P0_001.json": b"{}"}
    with transaction.file_lock(work / "record.lock"):
        assert transaction.publish(root, work, files) == 2
        assert transaction.publish(root, work, files) == 0
    assert sorted(path.name for path in work.iterdir()) == ["record.lock"]
    assert (root / "cases/CAN_P0_001.md").read_bytes() == b"case"


# 测试方法：发布第二个文件时注入失败；通过条件：两个文件均恢复旧内容。
def test_publish_rolls_back_all_files(
    transaction: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, work = tmp_path / "records", tmp_path / "work"
    transaction.publish(root, work, {"a.json": b"old a", "b.json": b"old b"})
    original = transaction.atomic_write

    def fail(path: Path, data: bytes) -> None:
        if path.name == "b.json" and data == b"new b":
            raise OSError("injected disk failure")
        original(path, data)

    monkeypatch.setattr(transaction, "atomic_write", fail)
    with pytest.raises(OSError, match="injected"):
        transaction.publish(root, work, {"a.json": b"new a", "b.json": b"new b"})
    assert (root / "a.json").read_bytes() == b"old a"
    assert (root / "b.json").read_bytes() == b"old b"
    assert not (work / "transaction.json").exists()


# 测试方法：模拟进程中断，随后恢复；通过条件：旧数据恢复且外部修改阻止覆盖。
def test_interrupted_transaction_recovers_and_protects_external_edit(
    transaction: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, work = tmp_path / "records", tmp_path / "work"
    transaction.publish(root, work, {"a.json": b"old"})
    original = transaction.atomic_write

    def interrupt(path: Path, data: bytes) -> None:
        original(path, data)
        if path.name == "a.json":
            raise KeyboardInterrupt

    monkeypatch.setattr(transaction, "atomic_write", interrupt)
    with pytest.raises(KeyboardInterrupt):
        transaction.publish(root, work, {"a.json": b"new"})
    monkeypatch.setattr(transaction, "atomic_write", original)
    (root / "a.json").write_bytes(b"external")
    with pytest.raises(ValueError, match="external change"):
        transaction.recover(root, work)
    assert (root / "a.json").read_bytes() == b"external"
    (root / "a.json").write_bytes(b"new")
    assert transaction.recover(root, work)
    assert (root / "a.json").read_bytes() == b"old"


# 测试方法：提交跨平台非法路径；通过条件：任何目标写入前拒绝。
@pytest.mark.parametrize("name", ["../x", "/x", "C:/x", "a\\b", "a//b", "CON.json", "x/../y"])
def test_transaction_rejects_unsafe_paths(
    transaction: ModuleType, tmp_path: Path, name: str
) -> None:
    with pytest.raises(ValueError):
        transaction.safe_path(tmp_path, name)


# 测试方法：重复取得同一锁；通过条件：立即报占用而非阻塞或并行写。
def test_lock_rejects_concurrent_writer(transaction: ModuleType, tmp_path: Path) -> None:
    with (
        transaction.file_lock(tmp_path / "record.lock"),
        pytest.raises(RuntimeError, match="already running"),
        transaction.file_lock(tmp_path / "record.lock"),
    ):
        pytest.fail("a second writer acquired the record lock")


# 测试方法：写入后完整性验证失败；通过条件：提交点之前回滚所有文件。
def test_publish_validation_failure_rolls_back(transaction: ModuleType, tmp_path: Path) -> None:
    root, work = tmp_path / "records", tmp_path / "work"
    transaction.publish(root, work, {"a.json": b"original"})

    def invalid() -> None:
        assert (root / "a.json").read_bytes() == b"new"
        raise ValueError("derived view mismatch")

    with pytest.raises(ValueError, match="derived view mismatch"):
        transaction.publish(root, work, {"a.json": b"new", "b.md": b"new"}, validate=invalid)
    assert (root / "a.json").read_bytes() == b"original"
    assert not (root / "b.md").exists()
    assert not (work / "transaction.json").exists()
