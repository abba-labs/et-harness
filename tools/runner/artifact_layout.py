#!/usr/bin/env python3
# Own the repository-local artifact run layout used by operator runners.

from __future__ import annotations

import io
import json
import os
import re
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = REPOSITORY_ROOT / "artifacts"
DEFAULT_RUNS_ROOT = ARTIFACT_ROOT / "runs"
DEFAULT_REPORTS_ROOT = ARTIFACT_ROOT / "reports"
DEFAULT_RECORDS_ROOT = ARTIFACT_ROOT / "records"


# Return one UTC timestamp in the stable format used by run manifests.
def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# Capture source identity without treating repository-owned evidence as a source change.
def capture_source_identity(repository_root: Path = REPOSITORY_ROOT) -> tuple[str, bool]:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        check=False,
        text=True,
        capture_output=True,
    )
    status = subprocess.run(
        [
            "git",
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            ".",
            ":(exclude)artifacts/runs/**",
            ":(exclude)artifacts/reports/**",
            ":(exclude)artifacts/records/**",
            ":(exclude)tmp/**",
        ],
        cwd=repository_root,
        check=False,
        text=True,
        capture_output=True,
    )
    source_revision = revision.stdout.strip() if revision.returncode == 0 else "unavailable"
    source_dirty = status.returncode != 0 or bool(status.stdout.strip())
    return source_revision, source_dirty


# Convert an operator label to one stable directory component.
def safe_component(value: str, *, field: str) -> str:
    normalized = re.sub(r"[^a-z0-9_]+", "_", value.strip().lower()).strip("_")
    if not normalized:
        raise ValueError(f"{field} must contain at least one letter or digit")
    return normalized


# Resolve output.root and reject paths outside the repository-owned artifacts tree.
def resolve_runs_root(value: str, *, config_directory: Path) -> Path:
    if value == "auto":
        return DEFAULT_RUNS_ROOT.resolve()
    supplied = Path(value)
    resolved = (supplied if supplied.is_absolute() else config_directory / supplied).resolve()
    runs_root = DEFAULT_RUNS_ROOT.resolve()
    try:
        resolved.relative_to(runs_root)
    except ValueError as exc:
        raise ValueError(
            f"output.root must stay inside repository artifacts/runs/: {runs_root}"
        ) from exc
    return resolved


# 保留历史独立诊断入口；正式Case入口使用create_current_directory。
def create_run_directory(runs_root: Path, *, run_name: str) -> Path:
    now = datetime.now()
    run_id = f"{now:%Y%m%d_%H%M%S_%f}_{safe_component(run_name, field='run name')}"
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


# 调用方必须持有环境锁；只有发布证明完整的固定工作区可以被复用。
def create_current_directory(repository: Path, runs_root: Path) -> Path:
    from record_workspace import prepare_workspace

    if runs_root.resolve() != (repository / "artifacts/runs").resolve():
        raise ValueError("Formal runs require canonical artifacts/runs root (output.root: auto)")
    return prepare_workspace(repository, runs_root / "current")


# 返回固定最新报告路径；只允许受控芯片/IP标识，不改写非法输入或创建目录。
def create_report_output(
    reports_root: Path,
    *,
    chip: str,
    ip: str,
) -> Path:
    from record_transaction import safe_name, safe_path

    chip_name = safe_name(chip).upper()
    ip_name = safe_name(ip).upper()
    directory = safe_path(reports_root, chip_name)
    output = directory / f"{chip_name}_{ip_name}测试报告.xlsx"
    if output.is_symlink() or (hasattr(output, "is_junction") and output.is_junction()):
        raise ValueError(f"linked report path is forbidden: {output}")
    if output.exists() and not output.is_file():
        raise ValueError(f"report destination is not a file: {output}")
    return output


# 调用方持有IP操作锁；先校验完整容器，再原子替换，任何失败均保留旧报告。
def publish_latest_report(
    reports_root: Path, *, chip: str, ip: str, data: bytes
) -> tuple[Path, int]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        required = {"[Content_Types].xml", "xl/workbook.xml"}
        if archive.testzip() is not None or not required <= set(archive.namelist()):
            raise ValueError("latest report is not a valid XLSX container")
    output = create_report_output(reports_root, chip=chip, ip=ip)
    if output.is_file() and output.read_bytes() == data:
        return output, 0
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=".report-", suffix=".pending", dir=output.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        create_report_output(reports_root, chip=chip, ip=ip)
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return output, 1


# Write a small run manifest atomically so interrupted runs remain identifiable.
def write_manifest(run_dir: Path, payload: dict[str, Any]) -> Path:
    output = run_dir / "manifest.json"
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)
    return output
