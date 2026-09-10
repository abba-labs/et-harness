# 固定运行目录的知识整理回执与安全复用。
# 职责：未发布或Hash损坏的现场拒绝清空；已seal且Hash完好的pending工作区允许覆盖；已review后校验Case知识Hash。
# 边界：不碰旧时间戳Run，不扫描设备，不根据PASS自动确认已无新知识。
# 依赖：标准库、文件事务及延迟加载的记录检查器。

from __future__ import annotations

import io
import os
import zipfile
from contextlib import AbstractContextManager
from pathlib import Path

from record_model import MAX_IP_BYTES, list_value, object_value, text_value
from record_transaction import (
    atomic_write,
    digest,
    file_lock,
    json_bytes,
    json_object,
    safe_name,
    safe_path,
)

RECEIPT = "publication.json"
WORKSPACE_SCHEMA = "et.run-workspace.v3"


class KnowledgeReviewPending(ValueError):
    pass


def environment_lock(repository: Path) -> AbstractContextManager[None]:
    return file_lock(repository.parent / "tmp/run_pipeline.lock")


def _validate_root(repository: Path, root: Path) -> None:
    try:
        relative = (
            root.absolute().relative_to((repository / "artifacts/records").absolute()).as_posix()
        )
    except ValueError as exc:
        raise ValueError("managed workspace must be records/<CHIP>/<IP>/current") from exc
    safe_path(repository / "artifacts/records", relative)
    parts = Path(relative).parts
    if len(parts) != 3 or parts[-1] != "current":
        raise ValueError("managed workspace must be records/<CHIP>/<IP>/current")
    for part in parts[:2]:
        if safe_name(part).upper() != part:
            raise ValueError("managed workspace chip/IP must use canonical uppercase names")


def workspace_files(root: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    total = 0
    for path in sorted(root.rglob("*")):
        name = path.relative_to(root).as_posix()
        safe_path(root, name)
        if path.is_dir() or name == RECEIPT:
            continue
        total += path.stat().st_size
        if total > MAX_IP_BYTES:
            raise ValueError("current workspace exceeds 256 MiB; preserve it before recovery")
        files[name] = path.read_bytes()
    return files


def _hashes(files: dict[str, bytes]) -> dict[str, str]:
    return {name: digest(data) for name, data in files.items()}


def _directories(root: Path) -> list[str]:
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_dir())


def _verify_record_proofs(repository: Path, proofs: dict[str, object]) -> None:
    from record_check import check_records

    for relative, value in proofs.items():
        if not relative.startswith("artifacts/records/"):
            raise ValueError("publication proof must reference fixed records")
        expected = object_value(value, "knowledge proof")
        cases = tuple(
            Path(name).stem
            for name in expected
            if name.startswith("cases/") and name.endswith(".md")
        )
        if not cases:
            raise ValueError(
                "publication requires reviewed Case Markdown, not legacy snapshot proofs"
            )
        check = check_records(safe_path(repository, relative), cases=cases)
        if check["files"] != expected:
            raise ValueError(
                "reviewed Case knowledge or attachment changed; review again before reuse"
            )


def _verify_archive(data: bytes) -> dict[str, object]:
    if len(data) > MAX_IP_BYTES + 1024 * 1024:
        raise ValueError("workspace archive exceeds capacity")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if (
            len(names) > 10000
            or len(names) != len(set(names))
            or sum(entry.file_size for entry in entries) > MAX_IP_BYTES + 1024 * 1024
        ):
            raise ValueError("duplicate or oversized workspace archive")
        manifest = json_object(archive.read("workspace-archive.json"))
        hashes = object_value(manifest.get("files"), "workspace archive files")
        if manifest.get("schema") != WORKSPACE_SCHEMA or set(names) != {
            "workspace-archive.json",
            *hashes,
        }:
            raise ValueError("workspace archive membership mismatch")
        for name, sha in hashes.items():
            if digest(archive.read(name)) != sha:
                raise ValueError(f"workspace archive hash mismatch: {name}")
    return manifest


def verify_publication(
    repository: Path, root: Path, *, require_review: bool = True, verify_knowledge: bool = True
) -> dict[str, object]:
    _validate_root(repository, root)
    path = safe_path(root, RECEIPT)
    if not path.is_file():
        raise ValueError(
            "current workspace is unpublished; preserve/review/archive it before reuse"
        )
    receipt = json_object(path.read_bytes())
    if receipt.get("schema") != WORKSPACE_SCHEMA or receipt.get("root") != str(root.resolve()):
        raise ValueError("workspace receipt identity mismatch")
    if _hashes(workspace_files(root)) != receipt.get("files") or _directories(root) != receipt.get(
        "directories"
    ):
        raise ValueError("current workspace changed after publication; refusing to remove files")
    archived = receipt.get("archive")
    if archived is not None:
        proof = object_value(archived, "archive proof")
        archive = Path(text_value(proof.get("path"), "archive path"))
        safe_path(archive.parent, archive.name)
        if archive.stat().st_size > MAX_IP_BYTES + 1024 * 1024:
            raise ValueError("workspace archive exceeds capacity")
        data = archive.read_bytes()
        manifest = _verify_archive(data) if digest(data) == proof.get("sha256") else {}
        if (
            manifest.get("files") != receipt["files"]
            or manifest.get("directories") != receipt["directories"]
        ):
            raise ValueError("workspace archive proof is missing or damaged")
    else:
        proofs = object_value(receipt.get("records"), "record proofs")
        pending = receipt.get("pending_review")
        if not isinstance(pending, bool):
            raise ValueError("workspace receipt lacks an explicit knowledge review state")
        if pending and require_review:
            raise KnowledgeReviewPending(
                "Case knowledge review is pending; distill the findings or confirm no new knowledge "
                "with maintain_test_records.py review before reusing current"
            )
        if not proofs and not pending and receipt.get("routine_success") is not True:
            raise ValueError("workspace has no publication proof")
        if verify_knowledge:
            _verify_record_proofs(repository, proofs)
    return receipt


# 删除只针对验证过的固定工作目录成员；额外文件、链接或内容变化都会先失败。
def prepare_workspace(repository: Path, root: Path) -> Path:
    _validate_root(repository, root)
    if root.exists() and any(root.iterdir()):
        receipt = verify_publication(repository, root, require_review=False)
        parent = root.parent.parent / "_PIPELINE/current"
        if (
            root != parent
            and (root / "manifest.json").is_file()
            and (parent / "manifest.json").is_file()
        ):
            child = json_object(safe_path(root, "manifest.json").read_bytes())
            pipeline = json_object(safe_path(parent, "manifest.json").read_bytes())
            if child.get("pipeline_run_id") and child["pipeline_run_id"] == pipeline.get("run_id"):
                # 父Pipeline未完成或回执损坏时拒绝覆盖子现场；pending不再互锁。
                verify_publication(repository, parent, require_review=False)
        for name in object_value(receipt["files"], "workspace files"):
            safe_path(root, name).unlink()
        safe_path(root, RECEIPT).unlink()
        for name in sorted(
            list_value(receipt["directories"], "directories"),
            key=lambda name: len(str(name).split("/")),
            reverse=True,
        ):
            safe_path(root, str(name)).rmdir()
    root.mkdir(parents=True, exist_ok=True)
    return root


def seal_workspace(
    repository: Path,
    root: Path,
    *,
    proofs: dict[str, object],
    expected_files: dict[str, object] | None = None,
    routine_success: bool = False,
    pending_review: bool = False,
) -> None:
    _validate_root(repository, root)
    _verify_record_proofs(repository, proofs)
    hashes = _hashes(workspace_files(root))
    if expected_files is not None and hashes != expected_files:
        raise ValueError("unbound or modified files remain in the Case workspace")
    if not proofs and not routine_success and not pending_review:
        raise ValueError("cannot mark an unrecorded failure workspace reusable")
    atomic_write(
        root / RECEIPT,
        json_bytes(
            {
                "schema": WORKSPACE_SCHEMA,
                "root": str(root.resolve()),
                "files": hashes,
                "directories": _directories(root),
                "records": proofs,
                "routine_success": routine_success,
                "pending_review": pending_review,
            }
        ),
    )


def seal_pipeline(repository: Path, root: Path, *, successful: bool) -> None:
    _validate_root(repository, root)
    if root.parent.name != "_PIPELINE":
        raise ValueError("pipeline evidence requires a _PIPELINE/current workspace")
    manifest = json_object(safe_path(root, "manifest.json").read_bytes())
    references = list_value(manifest.get("test_workspaces", []), "pipeline test workspaces")
    proofs: dict[str, object] = {}
    pending = False
    for relative in references:
        path = safe_path(repository, text_value(relative, "test workspace"))
        _validate_root(repository, path)
        if path.parent.parent != root.parent.parent or path.parent.name.startswith("_"):
            raise ValueError("pipeline test workspace must belong to the same chip")
        child = json_object(safe_path(path, "manifest.json").read_bytes())
        if child.get("pipeline_run_id") != manifest.get("run_id"):
            raise ValueError("IP workspace belongs to a different pipeline; preserve current")
        receipt = verify_publication(repository, path, require_review=False)
        proofs.update(object_value(receipt.get("records"), "Case publication proofs"))
        pending = pending or receipt.get("pending_review") is True
    seal_workspace(
        repository, root, proofs=proofs, routine_success=successful, pending_review=pending
    )


# 显式review后仅刷新同一逻辑Pipeline的回执，不改写其阶段日志或其他IP。
def review_workspace(repository: Path, root: Path, *, proofs: dict[str, object]) -> None:
    receipt = verify_publication(repository, root, require_review=False, verify_knowledge=False)
    parent = root.parent.parent / "_PIPELINE/current"
    parent_receipt = None
    if (parent / RECEIPT).exists() and (root / "manifest.json").exists():
        manifest = json_object(safe_path(parent, "manifest.json").read_bytes())
        child = json_object(safe_path(root, "manifest.json").read_bytes())
        if child.get("pipeline_run_id") == manifest.get("run_id") and root.relative_to(
            repository
        ).as_posix() in manifest.get("test_workspaces", []):
            parent_receipt = verify_publication(
                repository, parent, require_review=False, verify_knowledge=False
            )
    if not proofs:
        raise ValueError("review requires the selected Case knowledge files")
    seal_workspace(
        repository,
        root,
        proofs=proofs,
        expected_files=object_value(receipt["files"], "reviewed source files"),
    )
    if parent_receipt is not None:
        seal_pipeline(repository, parent, successful=parent_receipt.get("routine_success") is True)


def archive_workspace(repository: Path, root: Path, output: Path) -> dict[str, object]:
    _validate_root(repository, root)
    safe_path(output.parent, output.name)
    if output.absolute() != (root.parent / "recovery.zip").absolute() or output.exists():
        raise ValueError("workspace archive requires the unused fixed sibling recovery.zip")
    files = workspace_files(root)
    if not files:
        raise ValueError("workspace has no files to archive")
    manifest = {
        "schema": WORKSPACE_SCHEMA,
        "files": _hashes(files),
        "directories": _directories(root),
    }
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted({**files, "workspace-archive.json": json_bytes(manifest)}.items()):
            entry = zipfile.ZipInfo(name)
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, data)
    data = stream.getvalue()
    _verify_archive(data)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as destination:
        destination.write(data)
        destination.flush()
        os.fsync(destination.fileno())
    if _verify_archive(output.read_bytes()) != manifest:
        raise ValueError("workspace archive verification failed")
    proof = {"path": str(output.resolve()), "sha256": digest(data)}
    atomic_write(
        root / RECEIPT,
        json_bytes(
            {
                "schema": WORKSPACE_SCHEMA,
                "root": str(root.resolve()),
                "files": manifest["files"],
                "directories": manifest["directories"],
                "archive": proof,
            }
        ),
    )
    return {"operation": "archive_workspace", **proof}
