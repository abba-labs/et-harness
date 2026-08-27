# Framework Validation测试模块。
#
# 职责：验证test_frame_buffered_drain_native 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parents[5]
HARNESS = (
    PROJECT_ROOT
    / "pc"
    / "et_test_platform"
    / "framework_validation"
    / "native"
    / "et_frame_buffered_drain_harness.c"
)
FRAMEWORK = PROJECT_ROOT / "firmware" / "framework"


def _compile_native(tmp_path: Path) -> Path:
    compiler = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if compiler is None:
        pytest.skip("a C compiler is required for the frame drain harness")

    output = tmp_path / "et_frame_buffered_drain_harness"
    subprocess.run(
        [
            compiler,
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I",
            str(FRAMEWORK / "include"),
            str(HARNESS),
            str(FRAMEWORK / "src" / "et_frame.c"),
            "-o",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return output


def test_frame_parser_drains_complete_cached_frames_without_new_bytes(
    tmp_path: Path,
) -> None:
    completed = subprocess.run(
        [str(_compile_native(tmp_path))],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.strip() == "frame_buffered_drain=PASS"
