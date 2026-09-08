#!/usr/bin/env python3
# 仓库本地生成产物清理工具。
# 职责：预览或删除明确登记的运行产物、报告与工具缓存。
# 边界：不删除源码、配置、虚拟环境、第三方依赖或artifacts根目录。
# 依赖：仅使用Python标准库。

from __future__ import annotations

import argparse
import os
import shutil
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCOPES = ("runs", "reports", "caches", "tmp")
CACHE_DIRECTORY_NAMES = frozenset({"__pycache__", ".pytest_cache", ".ruff_cache"})
CACHE_SCAN_EXCLUSIONS = frozenset({".git", ".venv", "artifacts", "third_part"})
PRESERVED_DIRECTORY_ENTRIES = frozenset({".gitkeep"})
PROTECTED_RECORD_PATHS = frozenset(
    {"artifacts/runs/current", "artifacts/records", "artifacts/runs/record-maintenance"}
)


@dataclass(frozen=True, slots=True)
class CleanupEntry:
    path: Path
    file_count: int
    byte_count: int


# 验证目标确实是正式代码根，避免路径推导异常时误删其他目录。
def validate_repository_root(repository_root: Path) -> Path:
    resolved = repository_root.resolve()
    required = (resolved / "artifacts" / "README.md", resolved / "tools" / "runner")
    if not all(path.exists() for path in required):
        raise ValueError(f"invalid repository root for cleanup: {resolved}")
    return resolved


# 统计一个待删项；符号链接只计自身，不遍历链接目标。
def _measure_entry(path: Path) -> tuple[int, int]:
    if path.is_symlink():
        return 1, 0
    if path.is_file():
        return 1, path.stat().st_size

    file_count = 0
    byte_count = 0
    for directory, directory_names, file_names in os.walk(path, followlinks=False):
        directory_path = Path(directory)
        directory_names[:] = [
            name for name in directory_names if not (directory_path / name).is_symlink()
        ]
        for file_name in file_names:
            file_path = directory_path / file_name
            file_count += 1
            if not file_path.is_symlink():
                byte_count += file_path.stat().st_size
    return file_count, byte_count


# 返回指定目录的直接子项，保留runs/reports/tmp目录本身。
def _directory_contents(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(
        (path for path in directory.iterdir() if path.name not in PRESERVED_DIRECTORY_ENTRIES),
        key=lambda path: path.name.lower(),
    )


# 统一识别Python解释器缓存、质量工具缓存和安装元数据目录。
def _is_cache_directory_name(name: str) -> bool:
    return name in CACHE_DIRECTORY_NAMES or name.endswith(".egg-info")


# 查找Python工具缓存；跳过虚拟环境、第三方运行时和正式Artifact。
def _cache_directories(repository_root: Path) -> list[Path]:
    matches: list[Path] = []
    for directory, directory_names, _ in os.walk(repository_root, followlinks=False):
        directory_path = Path(directory)
        directory_names[:] = [
            name
            for name in directory_names
            if name not in CACHE_SCAN_EXCLUSIONS
            and not (directory_path / name).is_symlink()
            and (directory_path / name).relative_to(repository_root).as_posix()
            not in PROTECTED_RECORD_PATHS
        ]
        for name in tuple(directory_names):
            if _is_cache_directory_name(name):
                matches.append(directory_path / name)
                directory_names.remove(name)
    return sorted(matches, key=lambda path: (len(path.parts), str(path).lower()), reverse=True)


# 生成确定性的清理计划；本函数不修改文件系统。
def build_cleanup_plan(
    repository_root: Path,
    scopes: Iterable[str],
) -> list[CleanupEntry]:
    root = validate_repository_root(repository_root)
    requested = tuple(dict.fromkeys(scopes))
    unknown = sorted(set(requested) - set(SCOPES))
    if unknown:
        raise ValueError(f"unknown cleanup scopes: {', '.join(unknown)}")

    paths: list[Path] = []
    for scope in requested:
        if scope == "runs":
            paths.extend(_directory_contents(root / "artifacts" / "runs"))
        elif scope == "reports":
            paths.extend(_directory_contents(root / "artifacts" / "reports"))
        elif scope == "tmp":
            paths.extend(_directory_contents(root / "tmp"))
        elif scope == "caches":
            paths.extend(_cache_directories(root))

    plan: list[CleanupEntry] = []
    for path in dict.fromkeys(paths):
        if path.relative_to(root).as_posix() in PROTECTED_RECORD_PATHS:
            continue
        resolved_parent = path.parent.resolve()
        try:
            resolved_parent.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"cleanup target escaped repository root: {path}") from exc
        file_count, byte_count = _measure_entry(path)
        plan.append(CleanupEntry(path=path, file_count=file_count, byte_count=byte_count))
    return plan


# 执行已经审阅的计划；符号链接只解除链接，不删除链接目标。
def execute_cleanup(plan: Iterable[CleanupEntry]) -> None:
    for entry in plan:
        path = entry.path
        if path.is_symlink() or path.is_file():
            path.unlink(missing_ok=True)
        elif path.exists():
            shutil.rmtree(path)


# 将字节数转换为便于人工确认的显示值。
def _display_size(byte_count: int) -> str:
    value = float(byte_count)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024.0 or unit == "GiB":
            return f"{value:.1f} {unit}"
        value /= 1024.0
    raise AssertionError("unreachable size unit")


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preview or remove repository-local generated outputs safely."
    )
    parser.add_argument(
        "--scope",
        action="append",
        choices=SCOPES,
        help="cleanup scope; repeat as needed (default: runs)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="perform deletion; without this flag the command only previews",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="list every planned entry instead of printing only the summary",
    )
    return parser


# 默认仅预览runs；任何真实删除都要求显式--execute。
def main() -> int:
    args = _argument_parser().parse_args()
    scopes = tuple(args.scope or ("runs",))
    plan = build_cleanup_plan(REPOSITORY_ROOT, scopes)
    total_files = sum(entry.file_count for entry in plan)
    total_bytes = sum(entry.byte_count for entry in plan)

    mode = "EXECUTE" if args.execute else "PREVIEW"
    print(f"cleanup mode: {mode}")
    print(f"repository: {REPOSITORY_ROOT}")
    print(f"scopes: {', '.join(scopes)}")
    if args.verbose:
        for entry in plan:
            print(
                f"- {entry.path.relative_to(REPOSITORY_ROOT)} "
                f"({entry.file_count} files, {_display_size(entry.byte_count)})"
            )
    print(f"total: {len(plan)} entries, {total_files} files, {_display_size(total_bytes)}")

    if args.execute:
        execute_cleanup(plan)
        print("cleanup completed")
    else:
        print("preview only; add --execute to delete the listed entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
