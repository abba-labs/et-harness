#!/usr/bin/env python3
# Own the repository-local artifact run layout used by operator runners.

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = REPOSITORY_ROOT / "artifacts"
DEFAULT_RUNS_ROOT = ARTIFACT_ROOT / "runs"
DEFAULT_REPORTS_ROOT = ARTIFACT_ROOT / "reports"


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


# Create one immutable run directory directly below the canonical runs root.
def create_run_directory(runs_root: Path, *, run_name: str) -> Path:
    now = datetime.now()
    run_id = f"{now:%Y%m%d_%H%M%S_%f}_{safe_component(run_name, field='run name')}"
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


# Reserve one flat, timestamped Excel report path under the dedicated reports directory.
def create_report_output(
    reports_root: Path,
    *,
    chip: str,
    ip: str,
    now: datetime | None = None,
) -> Path:
    timestamp = now or datetime.now()
    chip_name = safe_component(chip, field="chip").upper()
    ip_name = safe_component(ip, field="IP").upper()
    reports_root.mkdir(parents=True, exist_ok=True)
    output = reports_root / f"{timestamp:%Y%m%d_%H%M%S_%f}_{chip_name}_{ip_name}测试报告.xlsx"
    if output.exists():
        raise FileExistsError(f"timestamped report already exists: {output}")
    return output


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
