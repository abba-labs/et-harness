# 显式现场归档的安全回归。
# 职责：验证人工指定新ZIP才归档、归档损坏拒绝复用、历史目录不收养。
# 边界：归档只作特殊恢复，不是默认Case知识贡献。
# 依赖：pytest和固定工作区模块。

from __future__ import annotations

import importlib
from pathlib import Path
from types import ModuleType

import pytest


@pytest.fixture
def workspace(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    root = Path(__file__).resolve().parents[5]
    monkeypatch.syspath_prepend(str(root / "tools/runner"))
    return importlib.import_module("record_workspace")


# 测试方法：显式归档失败阶段，破坏归档再校验；通过条件：只有完整外部归档允许复用。
def test_archive_is_explicit_and_verified(workspace: ModuleType, tmp_path: Path) -> None:
    root = tmp_path / "artifacts/records/ET6801/_PIPELINE/current"
    root.mkdir(parents=True)
    (root / "stage.log").write_bytes(b"failed stage")
    output = root.parent / "recovery.zip"
    workspace.archive_workspace(tmp_path, root, output)
    original = output.read_bytes()
    output.write_bytes(b"damaged")
    with pytest.raises(ValueError, match="damaged"):
        workspace.prepare_workspace(tmp_path, root)
    assert (root / "stage.log").read_bytes() == b"failed stage"
    output.write_bytes(original)
    workspace.prepare_workspace(tmp_path, root)
    assert list(root.iterdir()) == []


# 测试方法：已有归档、工作区内目标和非ZIP目标；通过条件：拒绝覆盖或自引用。
@pytest.mark.parametrize("kind", ["exists", "inside", "suffix", "other"])
def test_archive_rejects_unsafe_destination(
    workspace: ModuleType, tmp_path: Path, kind: str
) -> None:
    root = tmp_path / "artifacts/records/ET6801/_PIPELINE/current"
    root.mkdir(parents=True)
    (root / "stage.log").write_bytes(b"original")
    output = (
        root / "archive.zip"
        if kind == "inside"
        else root.parent / ("archive.txt" if kind == "suffix" else "recovery.zip")
    )
    if kind == "other":
        output = tmp_path / "outside.zip"
    if kind == "exists":
        output.write_bytes(b"keep existing archive")
    with pytest.raises(ValueError):
        workspace.archive_workspace(tmp_path, root, output)
    assert (root / "stage.log").read_bytes() == b"original"
    if kind == "exists":
        assert output.read_bytes() == b"keep existing archive"


# 测试方法：归档旧时间戳Run；通过条件：拒绝改变历史目录或生成复用回执。
def test_archive_refuses_legacy_workspace(workspace: ModuleType, tmp_path: Path) -> None:
    root = tmp_path / "artifacts/runs/20260908_old"
    root.mkdir(parents=True)
    (root / "keep.log").write_bytes(b"old")
    with pytest.raises(ValueError, match="managed workspace"):
        workspace.archive_workspace(tmp_path, root, tmp_path / "archive.zip")
    assert not (root / "publication.json").exists()
