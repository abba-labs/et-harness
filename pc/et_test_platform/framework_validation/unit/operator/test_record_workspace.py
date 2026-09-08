# 固定运行缓冲区的安全复用回归。
# 职责：验证发布证明、外部变化、历史路径隔离和显式现场归档。
# 边界：只使用临时软件样本，不操作硬件。
# 依赖：pytest和记录工具。

from __future__ import annotations

import importlib
from pathlib import Path
from types import ModuleType

import pytest

from .test_record_store import incoming, update


@pytest.fixture
def workspace(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    repository = Path(__file__).resolve().parents[5]
    monkeypatch.syspath_prepend(str(repository / "tools/runner"))
    return importlib.import_module("record_workspace")


# 测试方法：连续复用已完成的普通阶段工作区；通过条件：路径固定且每次复用后为空。
def test_workspace_reuses_only_fixed_directory(workspace: ModuleType, tmp_path: Path) -> None:
    root = tmp_path / "artifacts/runs/current"
    for iteration in range(20):
        assert workspace.prepare_workspace(tmp_path, root) == root
        assert list(root.iterdir()) == []
        (root / "stage.log").write_text(str(iteration), encoding="utf-8")
        workspace.seal_workspace(tmp_path, root, proofs={}, routine_success=True)
        assert len(list(root.iterdir())) == 2
    assert [path.name for path in root.parent.iterdir()] == ["current"]


# 测试方法：未发布、修改内容或添加外部文件；通过条件：均拒绝复用并保留现有字节。
@pytest.mark.parametrize("kind", ["unpublished", "changed", "extra", "extra_directory"])
def test_workspace_preserves_unpublished_or_changed_data(
    workspace: ModuleType, tmp_path: Path, kind: str
) -> None:
    root = workspace.prepare_workspace(tmp_path, tmp_path / "artifacts/runs/current")
    (root / "stage.log").write_bytes(b"initial")
    if kind != "unpublished":
        workspace.seal_workspace(tmp_path, root, proofs={}, routine_success=True)
    if kind == "changed":
        (root / "stage.log").write_bytes(b"external edit")
    elif kind == "extra":
        (root / "user.txt").write_bytes(b"keep me")
    elif kind == "extra_directory":
        (root / "user-directory").mkdir()
    before = {path.name: path.read_bytes() if path.is_file() else None for path in root.iterdir()}
    with pytest.raises(ValueError, match="unpublished|changed after publication"):
        workspace.prepare_workspace(tmp_path, root)
    assert before == {
        path.name: path.read_bytes() if path.is_file() else None for path in root.iterdir()
    }


# 测试方法：建立真实记录回执后破坏证据包；通过条件：在删除当前工作文件前拒绝复用。
def test_workspace_checks_durable_record_proof(workspace: ModuleType, tmp_path: Path) -> None:
    store = importlib.import_module("record_store")
    checker = importlib.import_module("record_check")
    record, _ = update(store, tmp_path, incoming(store, 1))
    root = workspace.prepare_workspace(tmp_path, tmp_path / "artifacts/runs/current/tests/test")
    (root / "session.json").write_bytes(b"sample")
    proofs = {record.relative_to(tmp_path).as_posix(): checker.check_records(record)["snapshots"]}
    workspace.seal_workspace(
        tmp_path, root, proofs=proofs, expected_files={"session.json": workspace.digest(b"sample")}
    )
    (record / "evidence/TEST_P0_001.zip").write_bytes(b"broken")
    with pytest.raises((ValueError, workspace.zipfile.BadZipFile)):
        workspace.prepare_workspace(tmp_path, root)
    assert (root / "session.json").read_bytes() == b"sample"


# 测试方法：显式归档未完成现场，破坏归档再恢复；通过条件：仅完整归档可授权下一次复用。
def test_workspace_archive_enables_verified_recovery(workspace: ModuleType, tmp_path: Path) -> None:
    root = workspace.prepare_workspace(tmp_path, tmp_path / "artifacts/runs/current")
    (root / "stage.log").write_bytes(b"failed stage evidence")
    output = tmp_path / "failed-stage.zip"
    workspace.archive_workspace(tmp_path, root, output)
    original = output.read_bytes()
    output.write_bytes(b"damaged")
    with pytest.raises(ValueError, match="damaged"):
        workspace.prepare_workspace(tmp_path, root)
    assert (root / "stage.log").read_bytes() == b"failed stage evidence"
    output.write_bytes(original)
    workspace.prepare_workspace(tmp_path, root)
    assert list(root.iterdir()) == []
    assert output.read_bytes() == original


# 测试方法：请求旧时间戳目录；通过条件：即使内容为空也不收养为可复用工作区。
def test_workspace_refuses_legacy_paths(workspace: ModuleType, tmp_path: Path) -> None:
    root = tmp_path / "artifacts/runs/20260908_old"
    root.mkdir(parents=True)
    with pytest.raises(ValueError, match="managed workspace"):
        workspace.prepare_workspace(tmp_path, root)
