# 固定IP记录目录的单机锁和可恢复文件事务。
# 职责：校验受控相对路径，发布完整文件集，异常或进程中断后回滚。
# 边界：不判断Case结果，不删除历史Run，不访问硬件。
# 依赖：仅标准库。

from __future__ import annotations

import hashlib
import json
import os
import re
import zipfile
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path, PurePosixPath


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def json_object(data: bytes) -> dict[str, object]:
    def reject(value: str) -> None:
        raise ValueError(f"non-finite JSON value: {value}")

    def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    value = json.loads(data.decode("utf-8-sig"), parse_constant=reject, object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ValueError("record must be a JSON object")
    return value


# Windows设备名、绝对路径、分隔符混用和目录穿越在任何平台都拒绝。
def safe_name(value: str) -> str:
    if value in {"_PIPELINE", "_TOOLING", "_DIAGNOSTICS", "_maintenance"}:
        return value
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value):
        raise ValueError(f"unsafe record name: {value!r}")
    if value.endswith(".") or value.split(".")[0].upper() in {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(10)),
        *(f"LPT{i}" for i in range(10)),
    }:
        raise ValueError(f"reserved record name: {value!r}")
    return value


def safe_path(root: Path, relative: str) -> Path:
    parts = PurePosixPath(relative).parts
    if not parts or relative != "/".join(parts):
        raise ValueError(f"unsafe relative record path: {relative!r}")
    for part in parts:
        safe_name(part)
    root = root.absolute()
    candidate = root.joinpath(*parts)
    for ancestor in (root, *root.parents, candidate, *candidate.parents):
        if ancestor.is_symlink() or (hasattr(ancestor, "is_junction") and ancestor.is_junction()):
            raise ValueError(f"linked record path is forbidden: {ancestor}")
    candidate.resolve().relative_to(root.resolve())
    return candidate


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = safe_path(path.parent, path.name + ".pending")
    with temporary.open("wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


# 锁文件留在固定工作目录；由操作系统释放锁，不靠文件是否存在判断占用。
@contextmanager
def file_lock(path: Path) -> Iterator[None]:
    safe_path(path.parent, path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        try:
            if os.fstat(stream.fileno()).st_size == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError(f"record operation is already running: {path}") from exc
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


# 未完成事务只恢复已声明的受控文件；发现外部修改时停止，绝不覆盖它。
def recover(root: Path, work: Path) -> bool:
    journal = safe_path(work, "transaction.json")
    if not journal.exists():
        return False
    manifest = json_object(journal.read_bytes())
    if manifest.get("root") != str(root.resolve()):
        raise ValueError("transaction belongs to a different record directory")
    entries = manifest.get("files")
    if not isinstance(entries, dict):
        raise ValueError("invalid transaction file list")
    backup = safe_path(work, "rollback.zip")
    if digest(backup.read_bytes()) != manifest.get("backup_sha256"):
        raise ValueError("transaction backup is damaged; current files were not changed")
    with zipfile.ZipFile(backup) as archive:
        restores: dict[Path, bytes | None] = {}
        for name, entry in entries.items():
            if not isinstance(entry, dict):
                raise ValueError("invalid transaction entry")
            destination = safe_path(root, name)
            present = digest(destination.read_bytes()) if destination.exists() else None
            if present not in {entry.get("before"), entry.get("after")}:
                raise ValueError(f"external change blocks transaction recovery: {destination}")
            data = archive.read(name) if entry.get("before") is not None else None
            if data is not None and digest(data) != entry["before"]:
                raise ValueError(f"invalid rollback member: {name}")
            restores[destination] = data
        for destination, data in restores.items():
            if data is None:
                destination.unlink(missing_ok=True)
            else:
                atomic_write(destination, data)
    journal.unlink()
    backup.unlink()
    return True


# 调用方必须持有file_lock；事务只修改显式提供的文件，不遍历或清空目标目录。
def publish(
    root: Path,
    work: Path,
    files: Mapping[str, bytes | None],
    *,
    validate: Callable[[], object] | None = None,
) -> int:
    recover(root, work)
    work.mkdir(parents=True, exist_ok=True)
    changes: dict[str, bytes | None] = {}
    before: dict[str, bytes | None] = {}
    for name, data in files.items():
        destination = safe_path(root, name)
        old = destination.read_bytes() if destination.exists() else None
        if old != data:
            changes[name], before[name] = data, old
    if not changes:
        return 0
    backup = safe_path(work, "rollback.zip")
    temporary = safe_path(work, "rollback.zip.pending")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in before.items():
            if data is not None:
                archive.writestr(name, data)
    os.replace(temporary, backup)
    journal = safe_path(work, "transaction.json")
    atomic_write(
        journal,
        json_bytes(
            {
                "root": str(root.resolve()),
                "backup_sha256": digest(backup.read_bytes()),
                "files": {
                    name: {
                        "before": digest(before[name]) if before[name] is not None else None,
                        "after": digest(data) if data is not None else None,
                    }
                    for name, data in changes.items()
                },
            }
        ),
    )
    try:
        for name, data in changes.items():
            destination = safe_path(root, name)
            if data is None:
                destination.unlink(missing_ok=True)
            else:
                atomic_write(destination, data)
        if validate is not None:
            validate()
    except Exception:
        recover(root, work)
        raise
    # journal移除是提交点；移除前进程终止会在下次调用恢复旧版本。
    journal.unlink()
    backup.unlink()
    return len(changes)
