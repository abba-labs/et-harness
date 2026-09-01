# Framework Validation测试模块。
#
# 职责：验证test_uart_wrap_deinit_native 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[5]
UART_WRAP = ROOT / "firmware" / "wrap" / "src" / "et_uart_wrap.c"


def _extract_deinit() -> str:
    source = UART_WRAP.read_text(encoding="utf-8")
    start = source.index("et_wrap_status_t et_uart_wrap_deinit(")
    end = source.index("et_wrap_status_t et_uart_wrap_enable_interrupts(", start)
    return source[start:end]


def _harness() -> str:
    function = _extract_deinit()
    return f"""
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef enum {{
    ET_WRAP_STATUS_OK = 0,
    ET_WRAP_STATUS_INVALID_ARGUMENT = 1,
    ET_WRAP_STATUS_STATE_ERROR = 2,
    ET_WRAP_STATUS_IO_ERROR = 3
}} et_wrap_status_t;

typedef enum {{
    DRV_OK = 0,
    DRV_ERROR = 1
}} DRV_Status;

typedef struct {{ uint32_t marker; }} UART_Type;
typedef uint16_t et_uart_id_t;
typedef struct {{ uintptr_t opaque[8]; }} et_uart_wrap_handle_t;
typedef struct {{
    UART_Type *uart;
    et_uart_id_t uart_id;
    uint8_t initialized;
    uint8_t last_snapshot_valid;
    uint16_t reserved16;
    uint32_t last_interrupt_status;
}} et_uart_wrap_private_t;

#define UART_IT_RECV_DATA_AVAILABLE_FLAG (1u << 0)
#define UART_IT_TRANS_DATA_EMPTY_FLAG (1u << 1)
#define UART_IT_CHAR_TIMEOUT_FLAG (1u << 2)
#define UART_IT_ERROR_FLAG (1u << 3)
#define UART_IT_MODEM_STATUS_FLAG (1u << 4)
#define UART_IT_9BITS_ADDR_RESV_FLAG (1u << 5)
#define UART_IT_PROMGRAM_THRE_FLAG (1u << 6)
#define UART_IT_UART_NOFIFO_BUSY (1u << 7)

static DRV_Status reset_status;
static uint32_t reset_calls;
static uint32_t disable_calls;
static uint32_t clear_calls;

static et_uart_wrap_private_t *private_handle(
    et_uart_wrap_handle_t *handle)
{{
    return (et_uart_wrap_private_t *)handle;
}}

static et_wrap_status_t map_driver_status(DRV_Status status)
{{
    return (status == DRV_OK) ? ET_WRAP_STATUS_OK : ET_WRAP_STATUS_IO_ERROR;
}}

static void UART_disableInterrupt(UART_Type *uart, uint32_t flags)
{{
    (void)uart;
    (void)flags;
    ++disable_calls;
}}

static void UART_clearInterruptStatus(UART_Type *uart, uint32_t flags)
{{
    (void)uart;
    (void)flags;
    ++clear_calls;
}}

static DRV_Status UART_performSoftwareReset(UART_Type *uart)
{{
    (void)uart;
    ++reset_calls;
    return reset_status;
}}

{function}

int main(void)
{{
    et_uart_wrap_handle_t handle;
    et_uart_wrap_private_t *private;
    UART_Type uart = {{ 0x12345678u }};
    uint8_t before[sizeof(handle)];

    (void)memset(&handle, 0, sizeof(handle));
    private = private_handle(&handle);
    private->uart = &uart;
    private->uart_id = 2u;
    private->initialized = 1u;
    private->last_snapshot_valid = 1u;
    private->last_interrupt_status = 0xa5a5a5a5u;
    (void)memcpy(before, &handle, sizeof(handle));

    reset_status = DRV_ERROR;
    if (et_uart_wrap_deinit(&handle) != ET_WRAP_STATUS_IO_ERROR) return 10;
    if (memcmp(before, &handle, sizeof(handle)) != 0) return 11;
    if ((reset_calls != 1u) || (disable_calls != 1u) ||
        (clear_calls != 1u)) return 12;

    reset_status = DRV_OK;
    if (et_uart_wrap_deinit(&handle) != ET_WRAP_STATUS_OK) return 20;
    for (uint32_t index = 0u; index < sizeof(handle); ++index) {{
        if (((const uint8_t *)&handle)[index] != 0u) return 21;
    }}
    if ((reset_calls != 2u) || (disable_calls != 2u) ||
        (clear_calls != 2u)) return 22;

    if (et_uart_wrap_deinit(&handle) != ET_WRAP_STATUS_OK) return 30;
    if (reset_calls != 2u) return 31;
    (void)printf("uart_wrap_deinit_retry=PASS\\n");
    return 0;
}}
"""


def test_uart_wrap_deinit_failure_preserves_real_handle(tmp_path: Path) -> None:
    compiler = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if compiler is None:
        pytest.skip("a C compiler is required for the UART Wrap deinit harness")

    source = tmp_path / "uart_wrap_deinit_harness.c"
    executable = tmp_path / "uart_wrap_deinit_harness"
    source.write_text(_harness(), encoding="utf-8")
    compiled = subprocess.run(
        [
            compiler,
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            str(source),
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
    assert completed.stdout.strip() == "uart_wrap_deinit_retry=PASS"
