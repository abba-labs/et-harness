# Framework Validation测试模块。
#
# 职责：验证test_irq_manager_reliability_native 对应的软件合同和回归行为。
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
    / "et_irq_manager_reliability_harness.c"
)
FRAMEWORK = PROJECT_ROOT / "firmware" / "framework"
WRAP = PROJECT_ROOT / "firmware" / "wrap"


def _compile_native(tmp_path: Path) -> Path:
    compiler = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if compiler is None:
        pytest.skip("a C compiler is required for the IRQ manager harness")

    output = tmp_path / "et_irq_manager_reliability_harness"
    subprocess.run(
        [
            compiler,
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I",
            str(FRAMEWORK / "include"),
            "-I",
            str(WRAP / "include"),
            str(HARNESS),
            str(FRAMEWORK / "src" / "et_irq_manager.c"),
            "-o",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return output


def test_irq_manager_cleanup_progress_is_retryable(tmp_path: Path) -> None:
    completed = subprocess.run(
        [str(_compile_native(tmp_path))],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.strip() == "irq_manager_reliability=PASS"
