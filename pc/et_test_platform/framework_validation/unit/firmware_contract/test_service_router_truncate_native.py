# Framework Validation测试模块。
#
# 职责：验证test_service_router_truncate_native 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[5]
FRAMEWORK = ROOT / "firmware/framework"


def test_service_router_truncate_restores_checkpoint(tmp_path: Path) -> None:
    compiler = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if compiler is None:
        pytest.skip("a C compiler is required for the Service Router harness")
    source = tmp_path / "service_router_truncate_harness.c"
    executable = tmp_path / "service_router_truncate_harness"
    source.write_text(
        r"""
#include <stdint.h>
#include <stdio.h>
#include "et_service_router.h"

static uint16_t handle(
    void *context, uint16_t command_id, const uint8_t *request_body,
    uint16_t request_length, uint8_t *response_body,
    uint16_t response_capacity, uint16_t *response_length)
{
    (void)context;
    (void)command_id;
    (void)request_body;
    (void)request_length;
    (void)response_body;
    (void)response_capacity;
    *response_length = 0u;
    return ET_STATUS_OK;
}

int main(void)
{
    et_service_router_t router;
    et_service_descriptor_t item = {0};
    uint16_t checkpoint;

    et_service_router_init(&router);
    item.handle = handle;
    item.service_id = 1u;
    if (et_service_register(&router, &item) != 0) return 10;
    checkpoint = et_service_count(&router);
    item.service_id = 2u;
    if (et_service_register(&router, &item) != 0) return 11;
    item.service_id = 3u;
    if (et_service_register(&router, &item) != 0) return 12;
    if (et_service_router_truncate(&router, checkpoint) != 0) return 13;
    if (et_service_count(&router) != 1u) return 14;
    if ((et_service_at(&router, 0u) == NULL) ||
        (et_service_at(&router, 0u)->service_id != 1u)) return 15;
    if (et_service_at(&router, 1u) != NULL) return 16;
    if (et_service_router_truncate(&router, 2u) == 0) return 17;
    (void)printf("service_router_truncate=PASS\n");
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
            str(FRAMEWORK / "include"),
            str(source),
            str(FRAMEWORK / "src" / "et_service_router.c"),
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
    assert completed.stdout.strip() == "service_router_truncate=PASS"
