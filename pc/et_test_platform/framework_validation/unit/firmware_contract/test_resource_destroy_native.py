# Framework Validation测试模块。
#
# 职责：验证test_resource_destroy_native 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[5]
WRAP = ROOT / "firmware/wrap"


def test_resource_destroy_rolls_back_only_latest_allocation(tmp_path: Path) -> None:
    compiler = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if compiler is None:
        pytest.skip("a C compiler is required for the Resource Wrap harness")
    source = tmp_path / "resource_destroy_harness.c"
    executable = tmp_path / "resource_destroy_harness"
    source.write_text(
        r"""
#include <stdint.h>
#include <stdio.h>
#include "et_resource_wrap.h"

int main(void)
{
    et_resource_handle_t first;
    et_resource_handle_t second;
    et_resource_handle_t reused;
    void *second_address;
    void *reused_address;
    uint32_t size;

    if (et_resource_wrap_init() != ET_WRAP_STATUS_OK) return 10;
    if (et_resource_wrap_create(16u, 4u, &first) != ET_WRAP_STATUS_OK) return 11;
    if (et_resource_wrap_create(32u, 4u, &second) != ET_WRAP_STATUS_OK) return 12;
    if (et_resource_wrap_resolve(second, &second_address, &size) != ET_WRAP_STATUS_OK) return 13;
    if (et_resource_wrap_destroy(first) != ET_WRAP_STATUS_STATE_ERROR) return 14;
    if (et_resource_wrap_destroy(second) != ET_WRAP_STATUS_OK) return 15;
    if (et_resource_wrap_resolve(second, &reused_address, &size) != ET_WRAP_STATUS_INVALID_ARGUMENT) return 16;
    if (et_resource_wrap_create(32u, 4u, &reused) != ET_WRAP_STATUS_OK) return 17;
    if (reused == second) return 18;
    if (et_resource_wrap_resolve(reused, &reused_address, &size) != ET_WRAP_STATUS_OK) return 19;
    if (reused_address != second_address) return 20;
    if (et_resource_wrap_destroy(reused) != ET_WRAP_STATUS_OK) return 21;
    if (et_resource_wrap_destroy(first) != ET_WRAP_STATUS_OK) return 22;
    (void)printf("resource_destroy=PASS\n");
    return 0;
}
""",
        encoding="utf-8",
    )
    compiled = subprocess.run(
        [
            compiler,
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I",
            str(WRAP / "include"),
            str(source),
            str(WRAP / "src" / "et_resource_wrap.c"),
            "-o",
            str(executable),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert compiled.returncode == 0, compiled.stderr
    completed = subprocess.run(
        [str(executable)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, f"stdout={completed.stdout!r}\nstderr={completed.stderr!r}"
    assert completed.stdout.strip() == "resource_destroy=PASS"
