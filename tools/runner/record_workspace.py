# 固定运行工作目录的证据发布回执与安全复用。
# 职责：只复用已有发布证明且内容未变的current目录，保存失败现场的显式归档。
# 边界：不碰旧时间戳Run，不扫描设备，不根据PASS文字推断Case证据已保存。
# 依赖：标准库、文件事务及延迟加载的记录检查器。

from __future__ import annotations

import io
import os
import zipfile
from contextlib import AbstractContextManager
from pathlib import Path

from record_model import MAX_IP_BYTES, list_value, object_value, text_value
from record_transaction import atomic_write, digest, file_lock, json_bytes, json_object, safe_path

RECEIPT = "publication.json"
WORKSPACE_SCHEMA = "et.run-workspace.v1"


def environment_lock(repository: Path) -> AbstractContextManager[None]:
    return file_lock(repository.parent / "tmp/run_pipeline.lock")


def _validate_root(repository: Path, root: Path) -> None:
    relative = root.absolute().relative_to((repository / "artifacts/runs").absolute()).as_posix()
    safe_path(repository / "artifacts/runs", relative)
    parts = Path(relative).parts
    if parts != ("current",) and not (len(parts) == 3 and parts[:2] == ("current", "tests")):
        raise ValueError("managed workspace must be artifacts/runs/current[/tests/IP]")


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
        check = check_records(safe_path(repository, relative))
        actual = object_value(check["snapshots"], "current snapshots")
        for case, identities in object_value(value, "record proof").items():
            if not set(list_value(identities, "snapshot identities")) <= set(
                list_value(actual.get(case, []), "current identities")
            ):
                raise ValueError(f"published snapshot is no longer available: {case}")


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


def verify_publication(repository: Path, root: Path) -> dict[str, object]:
    _validate_root(repository, root)
    path = safe_path(root, RECEIPT)
    if not path.is_file():
        raise ValueError("current workspace is unpublished; preserve/archive it before reuse")
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
        if not proofs and receipt.get("routine_success") is not True:
            raise ValueError("workspace has no publication proof")
        _verify_record_proofs(repository, proofs)
    return receipt


# 删除只针对验证过的固定工作目录成员；额外文件、链接或内容变化都会先失败。
def prepare_workspace(repository: Path, root: Path) -> Path:
    _validate_root(repository, root)
    if root.exists() and any(root.iterdir()):
        receipt = verify_publication(repository, root)
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
) -> None:
    _validate_root(repository, root)
    _verify_record_proofs(repository, proofs)
    hashes = _hashes(workspace_files(root))
    if expected_files is not None and hashes != expected_files:
        raise ValueError("unbound or modified files remain in the Case workspace")
    if not proofs and not routine_success:
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
            }
        ),
    )


def seal_pipeline(repository: Path, root: Path, *, successful: bool) -> None:
    proofs: dict[str, object] = {}
    for path in sorted((root / "tests").glob("*")):
        if not path.is_dir():
            raise ValueError("unexpected entry in pipeline tests directory")
        receipt = verify_publication(repository, path)
        proofs.update(object_value(receipt.get("records"), "Case publication proofs"))
    seal_workspace(repository, root, proofs=proofs, routine_success=successful)


def archive_workspace(repository: Path, root: Path, output: Path) -> dict[str, object]:
    from record_archive import MAX_ARCHIVE_DIRECTORY_BYTES, MAX_ARCHIVES

    _validate_root(repository, root)
    safe_path(output.parent, output.name)
    if (
        output.suffix.lower() != ".zip"
        or output.exists()
        or output.resolve().is_relative_to(root.resolve())
    ):
        raise ValueError("workspace archive requires a new .zip outside current workspace")
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
    siblings = list(output.parent.glob("*.zip"))
    if (
        len(siblings) >= MAX_ARCHIVES
        or sum(path.stat().st_size for path in siblings) + len(data) > MAX_ARCHIVE_DIRECTORY_BYTES
    ):
        raise ValueError("archive destination budget exceeded")
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
