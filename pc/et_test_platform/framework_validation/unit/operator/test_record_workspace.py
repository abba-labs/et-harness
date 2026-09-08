# 固定运行缓冲区的安全复用回归。
# 职责：验证发布证明、外部变化、历史路径隔离和显式现场归档。
# 边界：只使用临时软件样本，不操作硬件。
# 依赖：pytest和记录工具。

from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import ModuleType

import pytest

from .test_record_store import make_knowledge


@pytest.fixture
def workspace(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    repository = Path(__file__).resolve().parents[5]
    monkeypatch.syspath_prepend(str(repository / "tools/runner"))
    return importlib.import_module("record_workspace")


def pipeline_for(repository: Path, current: Path) -> Path:
    parent = current.parent.parent / "_PIPELINE/current"
    parent.mkdir(parents=True, exist_ok=True)
    (parent / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": "pipeline-1",
                "test_workspaces": [current.relative_to(repository).as_posix()],
            }
        ),
        encoding="utf-8",
    )
    (current / "manifest.json").write_text(
        json.dumps({"pipeline_run_id": "pipeline-1"}), encoding="utf-8"
    )
    return parent


# 测试方法：连续复用已完成的普通阶段工作区；通过条件：路径固定且每次复用后为空。
def test_workspace_reuses_only_fixed_directory(workspace: ModuleType, tmp_path: Path) -> None:
    root = tmp_path / "artifacts/records/ET6801/_PIPELINE/current"
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
    root = workspace.prepare_workspace(
        tmp_path, tmp_path / "artifacts/records/ET6801/_PIPELINE/current"
    )
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


# 测试方法：建立整理回执后修改知识；通过条件：复用前要求重新确认，不依赖任何证据ZIP。
def test_workspace_checks_durable_record_proof(workspace: ModuleType, tmp_path: Path) -> None:
    checker = importlib.import_module("record_check")
    document = make_knowledge(tmp_path)
    record = document.parent.parent
    root = workspace.prepare_workspace(tmp_path, tmp_path / "artifacts/records/ET6801/CRC/current")
    (root / "session.json").write_bytes(b"sample")
    proofs = {record.relative_to(tmp_path).as_posix(): checker.check_records(record)["files"]}
    workspace.seal_workspace(
        tmp_path, root, proofs=proofs, expected_files={"session.json": workspace.digest(b"sample")}
    )
    document.write_text(
        document.read_text(encoding="utf-8") + "\n新的判断，需复核。\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="reviewed Case knowledge"):
        workspace.prepare_workspace(tmp_path, root)
    assert (root / "session.json").read_bytes() == b"sample"


# 测试方法：测试PASS但整理未完成；通过条件：封存不改测试状态，下一轮复用在删除前阻止。
def test_pending_review_blocks_overwrite_even_after_pass(
    workspace: ModuleType, tmp_path: Path
) -> None:
    root = workspace.prepare_workspace(tmp_path, tmp_path / "artifacts/records/ET6801/CRC/current")
    (root / "session.json").write_bytes(b"PASS raw")
    parent = pipeline_for(tmp_path, root)
    workspace.seal_workspace(tmp_path, root, proofs={}, pending_review=True)
    workspace.seal_pipeline(tmp_path, parent, successful=True)
    assert workspace.verify_publication(tmp_path, root, require_review=False)["pending_review"]
    for target in (root, parent):
        with pytest.raises(workspace.KnowledgeReviewPending):
            workspace.prepare_workspace(tmp_path, target)
    assert (root / "session.json").read_bytes() == b"PASS raw"


# 测试方法：完成Case知识后显式确认子工作区；通过条件：父回执同步，整个current可安全复用。
def test_review_refreshes_parent_receipt(workspace: ModuleType, tmp_path: Path) -> None:
    checker = importlib.import_module("record_check")
    document = make_knowledge(tmp_path)
    root = workspace.prepare_workspace(tmp_path, tmp_path / "artifacts/records/ET6801/CRC/current")
    (root / "session.json").write_bytes(b"source")
    parent = pipeline_for(tmp_path, root)
    workspace.seal_workspace(tmp_path, root, proofs={}, pending_review=True)
    workspace.seal_pipeline(tmp_path, parent, successful=True)
    record = document.parent.parent
    proofs = {record.relative_to(tmp_path).as_posix(): checker.check_records(record)["files"]}
    workspace.review_workspace(tmp_path, root, proofs=proofs)
    workspace.verify_publication(tmp_path, parent)
    workspace.prepare_workspace(tmp_path, parent)
    assert list(parent.iterdir()) == []
    assert document.exists()


# 测试方法：显式归档未完成现场，破坏归档再恢复；通过条件：仅完整归档可授权下一次复用。
def test_workspace_archive_enables_verified_recovery(workspace: ModuleType, tmp_path: Path) -> None:
    root = workspace.prepare_workspace(
        tmp_path, tmp_path / "artifacts/records/ET6801/_PIPELINE/current"
    )
    (root / "stage.log").write_bytes(b"failed stage evidence")
    output = root.parent / "recovery.zip"
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


# 测试方法：一IP已整理、同Pipeline另一IP待整理；通过条件：已整理IP也不能提前覆盖。
def test_pipeline_pending_sibling_blocks_child_reuse(workspace: ModuleType, tmp_path: Path) -> None:
    checker = importlib.import_module("record_check")
    document = make_knowledge(tmp_path)
    root = workspace.prepare_workspace(tmp_path, tmp_path / "artifacts/records/ET6801/CRC/current")
    parent = pipeline_for(tmp_path, root)
    sibling = workspace.prepare_workspace(
        tmp_path, tmp_path / "artifacts/records/ET6801/UART/current"
    )
    (sibling / "manifest.json").write_text('{"pipeline_run_id":"pipeline-1"}', encoding="utf-8")
    manifest = json.loads((parent / "manifest.json").read_bytes())
    manifest["test_workspaces"].append(sibling.relative_to(tmp_path).as_posix())
    (parent / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    workspace.seal_workspace(tmp_path, root, proofs={}, pending_review=True)
    workspace.seal_workspace(tmp_path, sibling, proofs={}, pending_review=True)
    workspace.seal_pipeline(tmp_path, parent, successful=True)
    record = document.parent.parent
    proofs = {record.relative_to(tmp_path).as_posix(): checker.check_records(record)["files"]}
    workspace.review_workspace(tmp_path, root, proofs=proofs)
    with pytest.raises(workspace.KnowledgeReviewPending):
        workspace.prepare_workspace(tmp_path, root)
    assert (root / "manifest.json").is_file() and (sibling / "manifest.json").is_file()
