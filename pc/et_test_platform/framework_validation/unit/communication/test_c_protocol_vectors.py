# Framework Validation测试模块。
#
# 职责：验证test_c_protocol_vectors 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parents[5]
FIRMWARE_FRAMEWORK = PROJECT_ROOT / "firmware" / "framework"
HARNESS = (
    PROJECT_ROOT
    / "pc"
    / "et_test_platform"
    / "framework_validation"
    / "native"
    / "et_protocol_vector_harness.c"
)
VECTORS = (
    PROJECT_ROOT
    / "pc"
    / "et_test_platform"
    / "framework_validation"
    / "test_data"
    / "protocol"
    / "et_frame_v1_golden.json"
)


def _compile_native(tmp_path: Path) -> list[str]:
    compiler = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    output = tmp_path / "et_protocol_vector_harness"
    sources = (
        HARNESS,
        FIRMWARE_FRAMEWORK / "src" / "et_frame.c",
        FIRMWARE_FRAMEWORK / "src" / "et_message.c",
        FIRMWARE_FRAMEWORK / "src" / "et_protocol.c",
        FIRMWARE_FRAMEWORK / "src" / "et_service_router.c",
    )
    include = FIRMWARE_FRAMEWORK / "include"
    if compiler is not None:
        subprocess.run(
            [
                compiler,
                "-std=c99",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-I",
                str(include),
                *(str(source) for source in sources),
                "-o",
                str(output),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return [str(output)]

    wsl = shutil.which("wsl.exe")
    if wsl is None:
        pytest.skip("a C compiler is required for the protocol vector contract")

    def wsl_path(path: Path) -> str:
        return subprocess.run(
            [wsl, "wslpath", "-a", str(path).replace("\\", "/")],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    wsl_output = wsl_path(output)
    subprocess.run(
        [
            wsl,
            "cc",
            "-std=c99",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I",
            wsl_path(include),
            *(wsl_path(source) for source in sources),
            "-o",
            wsl_output,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return [wsl, wsl_output]


def test_c_codec_matches_shared_golden_vectors(tmp_path: Path) -> None:
    command = _compile_native(tmp_path)
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    actual = dict(line.split("=", 1) for line in completed.stdout.splitlines() if line)
    expected = {
        item["name"]: item["hex"]
        for item in json.loads(VECTORS.read_text(encoding="utf-8"))["vectors"]
    }

    assert actual == expected
