# Framework Validation测试模块。
#
# 职责：验证test_common_reliability_native 对应的软件合同和回归行为。
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
    / "et_common_reliability_harness.c"
)
FRAMEWORK = PROJECT_ROOT / "firmware" / "framework"
WRAP = PROJECT_ROOT / "firmware" / "wrap"


def _compile_native(tmp_path: Path) -> list[str]:
    compiler = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if compiler is None:
        pytest.skip("a C compiler is required for the common reliability harness")

    output = tmp_path / "et_common_reliability_harness"
    sources = (
        HARNESS,
        FRAMEWORK / "src" / "et_frame.c",
        FRAMEWORK / "src" / "et_message.c",
        FRAMEWORK / "src" / "et_protocol.c",
        FRAMEWORK / "src" / "et_service_router.c",
        WRAP / "src" / "et_resource_wrap.c",
    )
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
            *(str(source) for source in sources),
            "-o",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return [str(output)]


def test_native_common_protocol_and_endpoint_reliability(tmp_path: Path) -> None:
    completed = subprocess.run(
        _compile_native(tmp_path),
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip() == "common_reliability=PASS"
