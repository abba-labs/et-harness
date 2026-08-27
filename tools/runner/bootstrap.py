#!/usr/bin/env python3
# Windows one-click bootstrap. It prepares Python only; pipeline policy lives in run_pipeline.py.

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import venv
from collections.abc import Sequence
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPOSITORY_ROOT / "run_config.yaml"
CONFIG_TEMPLATE = REPOSITORY_ROOT / "run_config.example.yaml"
VENV_ROOT = REPOSITORY_ROOT / ".venv"
DEPENDENCY_MARKER = VENV_ROOT / ".et_dependencies.sha256"
PIPELINE_RUNNER = REPOSITORY_ROOT / "tools/runner/run_pipeline.py"
CONFIG_GUI = REPOSITORY_ROOT / "tools/runner/run_config_gui.py"
_DEPENDENCY_FILES = (REPOSITORY_ROOT / "pyproject.toml", REPOSITORY_ROOT / "uv.lock")
_DEPENDENCY_IMPORT_CHECK = (
    "import pytest, yaml, serial, pyvisa, xlsxwriter, et_test_platform; "
    "import shutil, sys; from pathlib import Path; "
    "assert shutil.which('clang-format', path=str(Path(sys.executable).parent))"
)


# 解析启动器参数。配置语义由虚拟环境内的统一 Pipeline Runner 负责。
def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare the local Python environment and run the configured pipeline."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="operator YAML configuration")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="validate configuration and local environment without executing the pipeline",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="open the lightweight run configuration GUI after preparing dependencies",
    )
    return parser.parse_args(argv)


# 首次运行只创建本地配置并停止，避免空路径或模板值触发任何硬件动作。
def _ensure_operator_config(path: Path, *, continue_after_create: bool = False) -> None:
    if path.is_file():
        return
    if path != DEFAULT_CONFIG or not CONFIG_TEMPLATE.is_file():
        raise RuntimeError(f"operator configuration does not exist: {path}")
    shutil.copyfile(CONFIG_TEMPLATE, DEFAULT_CONFIG)
    if continue_after_create:
        return
    raise RuntimeError(
        f"created {DEFAULT_CONFIG.name}; fill in the local environment values and "
        "run run_test.bat again."
    )


def _venv_python() -> Path:
    if os.name == "nt":
        return VENV_ROOT / "Scripts/python.exe"
    return VENV_ROOT / "bin/python"


def _dependency_fingerprint() -> str:
    digest = hashlib.sha256()
    for path in _DEPENDENCY_FILES:
        if path.is_file():
            digest.update(path.name.encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _dependencies_importable(python: Path) -> bool:
    if not python.is_file():
        return False
    completed = subprocess.run(
        [str(python), "-c", _DEPENDENCY_IMPORT_CHECK],
        cwd=REPOSITORY_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def _ensure_virtual_environment() -> Path:
    python = _venv_python()
    if not python.is_file():
        print("Creating local .venv ...")
        venv.EnvBuilder(with_pip=True).create(VENV_ROOT)
    if not python.is_file():
        raise RuntimeError(f"virtual environment Python was not created: {python}")
    return python


def _pip_available(python: Path) -> bool:
    completed = subprocess.run(
        [str(python), "-m", "pip", "--version"],
        cwd=REPOSITORY_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def _ensure_pip(python: Path) -> None:
    if _pip_available(python):
        return
    print("Installing pip into the local .venv ...")
    subprocess.run(
        [str(python), "-m", "ensurepip", "--upgrade"],
        cwd=REPOSITORY_ROOT,
        check=True,
    )
    if not _pip_available(python):
        raise RuntimeError("pip is unavailable after ensurepip recovery")


def _ensure_dependencies(python: Path) -> None:
    fingerprint = _dependency_fingerprint()
    marker = (
        DEPENDENCY_MARKER.read_text(encoding="utf-8").strip() if DEPENDENCY_MARKER.is_file() else ""
    )
    if marker == fingerprint and _dependencies_importable(python):
        print("Python dependencies: ready")
        return

    print("Installing/updating Python dependencies ...")
    _ensure_pip(python)
    subprocess.run(
        [str(python), "-m", "pip", "install", "-e", ".[test]"],
        cwd=REPOSITORY_ROOT,
        check=True,
    )
    if not _dependencies_importable(python):
        raise RuntimeError("dependency verification failed after installation")
    DEPENDENCY_MARKER.write_text(fingerprint + "\n", encoding="utf-8")
    print("Python dependencies: ready")


def _pipeline_command(python: Path, config: Path, *, check_only: bool = False) -> list[str]:
    command = [str(python), str(PIPELINE_RUNNER), "--config", str(config)]
    if check_only:
        command.append("--check-only")
    return command


def _gui_command(python: Path, config: Path) -> list[str]:
    return [str(python), str(CONFIG_GUI), "--config", str(config)]


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    config = Path(args.config).resolve()
    try:
        if args.gui and args.check_only:
            raise RuntimeError("--gui and --check-only cannot be used together")
        _ensure_operator_config(config, continue_after_create=bool(args.gui))
        python = _ensure_virtual_environment()
        _ensure_dependencies(python)
        command = (
            _gui_command(python, config)
            if args.gui
            else _pipeline_command(python, config, check_only=bool(args.check_only))
        )
        completed = subprocess.run(
            command,
            cwd=REPOSITORY_ROOT,
            check=False,
        )
        return int(completed.returncode)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
