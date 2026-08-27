# Framework Validation测试模块。
#
# 职责：验证test_uart_cleanup_native 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parents[5]
UART_SERVICE = PROJECT_ROOT / "firmware" / "services" / "src" / "et_uart_service.c"


def _extract_cleanup_function() -> str:
    source = UART_SERVICE.read_text(encoding="utf-8")
    start = source.index("static et_wrap_status_t uart_reset_to_idle(")
    end = source.index(
        "static et_wrap_status_t uart_write_fifo_dma_hardware(",
        start,
    )
    return source[start:end]


def _harness_source() -> str:
    cleanup = _extract_cleanup_function()
    return f"""
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define ET_UART_WRAP_TXFIFO_THRESHOLD_8 8u
#define ET_UART_WRAP_RXFIFO_THRESHOLD_1 1u
#define ET_UART_WRAP_DMA_DISABLED 0u

typedef enum {{
    ET_WRAP_STATUS_OK = 0,
    ET_WRAP_STATUS_INVALID_ARGUMENT = 1,
    ET_WRAP_STATUS_IO_ERROR = 2
}} et_wrap_status_t;

typedef struct {{ uint32_t irq_line; }} et_irq_route_t;
typedef struct {{ uint32_t marker; }} et_uart_wrap_handle_t;
typedef struct {{ uint32_t unused; }} et_irq_manager_t;

typedef struct {{
    uint8_t initialized;
    uint8_t irq_bound;
    uint8_t irq_priority;
    uint8_t default_irq_priority;
    uint8_t capture_active;
    uint16_t capture_expected;
    uint16_t capture_received;
    uint8_t fifo_enabled;
    uint8_t fifo_tx_threshold;
    uint8_t fifo_rx_threshold;
    uint8_t dma_mode;
    uint32_t irq_enabled_mask;
    uint32_t irq_applied_wrap_mask;
    uint32_t irq_suppressed_wrap_mask;
    uint32_t irq_fault_count;
    et_irq_manager_t *irq_manager;
    et_irq_route_t irq_route;
    et_uart_wrap_handle_t handle;
}} et_uart_service_t;

static uint8_t fail_disable_once;
static uint8_t fail_unbind_once;
static uint8_t fail_deinit_once;
static uint32_t disable_calls;
static uint32_t unbind_calls;
static uint32_t deinit_calls;

static void uart_irq_callback(void *context, uint32_t line, uint32_t events)
{{
    (void)context; (void)line; (void)events;
}}

static void uart_note_irq_fault(et_uart_service_t *service)
{{
    if (service->irq_fault_count != UINT32_MAX) {{
        ++service->irq_fault_count;
    }}
}}

static void uart_store_capture_state(
    et_uart_service_t *service,
    uint8_t active,
    uint16_t expected,
    uint16_t received)
{{
    service->capture_active = active;
    service->capture_expected = expected;
    service->capture_received = received;
}}

static void uart_clear_irq_evidence(et_uart_service_t *service)
{{
    service->irq_fault_count = 0u;
}}

static et_wrap_status_t et_uart_wrap_disable_interrupts(
    et_uart_wrap_handle_t *handle,
    uint32_t mask)
{{
    (void)handle; (void)mask;
    ++disable_calls;
    if (fail_disable_once != 0u) {{
        fail_disable_once = 0u;
        return ET_WRAP_STATUS_IO_ERROR;
    }}
    return ET_WRAP_STATUS_OK;
}}

static int et_irq_manager_unbind(
    et_irq_manager_t *manager,
    uint32_t line,
    void (*callback)(void *, uint32_t, uint32_t),
    void *context)
{{
    (void)manager; (void)line; (void)callback; (void)context;
    ++unbind_calls;
    if (fail_unbind_once != 0u) {{
        fail_unbind_once = 0u;
        return -1;
    }}
    return 0;
}}

static et_wrap_status_t et_uart_wrap_deinit(et_uart_wrap_handle_t *handle)
{{
    ++deinit_calls;
    if (fail_deinit_once != 0u) {{
        fail_deinit_once = 0u;
        return ET_WRAP_STATUS_IO_ERROR;
    }}
    handle->marker = 0u;
    return ET_WRAP_STATUS_OK;
}}

{cleanup}

static void initialize_service(et_uart_service_t *service)
{{
    static et_irq_manager_t manager;
    (void)memset(service, 0, sizeof(*service));
    service->initialized = 1u;
    service->irq_bound = 1u;
    service->irq_priority = 9u;
    service->default_irq_priority = 3u;
    service->irq_applied_wrap_mask = 0x55u;
    service->irq_manager = &manager;
    service->irq_route.irq_line = 7u;
    service->handle.marker = 0x12345678u;
}}

static int test_disable_retry(void)
{{
    et_uart_service_t service;
    initialize_service(&service);
    fail_disable_once = 1u;
    if (uart_reset_to_idle(&service) != ET_WRAP_STATUS_IO_ERROR) return 10;
    if ((service.initialized == 0u) || (service.irq_bound == 0u) ||
        (service.irq_applied_wrap_mask != 0x55u) ||
        (service.handle.marker != 0x12345678u) ||
        (disable_calls != 1u) || (unbind_calls != 0u) ||
        (deinit_calls != 0u) || (service.irq_fault_count != 1u)) return 11;
    if (uart_reset_to_idle(&service) != ET_WRAP_STATUS_OK) return 12;
    if ((disable_calls != 2u) || (unbind_calls != 1u) ||
        (deinit_calls != 1u) || (service.initialized != 0u) ||
        (service.irq_bound != 0u) || (service.handle.marker != 0u)) return 13;
    return 0;
}}

static int test_unbind_retry(void)
{{
    et_uart_service_t service;
    disable_calls = unbind_calls = deinit_calls = 0u;
    initialize_service(&service);
    fail_unbind_once = 1u;
    if (uart_reset_to_idle(&service) != ET_WRAP_STATUS_IO_ERROR) return 20;
    if ((service.irq_applied_wrap_mask != 0u) ||
        (service.irq_bound == 0u) || (service.initialized == 0u) ||
        (disable_calls != 1u) || (unbind_calls != 1u) ||
        (deinit_calls != 0u)) return 21;
    if (uart_reset_to_idle(&service) != ET_WRAP_STATUS_OK) return 22;
    if ((disable_calls != 1u) || (unbind_calls != 2u) ||
        (deinit_calls != 1u)) return 23;
    return 0;
}}

static int test_deinit_retry(void)
{{
    et_uart_service_t service;
    disable_calls = unbind_calls = deinit_calls = 0u;
    initialize_service(&service);
    fail_deinit_once = 1u;
    if (uart_reset_to_idle(&service) != ET_WRAP_STATUS_IO_ERROR) return 30;
    if ((service.irq_applied_wrap_mask != 0u) ||
        (service.irq_bound != 0u) || (service.initialized == 0u) ||
        (service.handle.marker != 0x12345678u) ||
        (disable_calls != 1u) || (unbind_calls != 1u) ||
        (deinit_calls != 1u)) return 31;
    if (uart_reset_to_idle(&service) != ET_WRAP_STATUS_OK) return 32;
    if ((disable_calls != 1u) || (unbind_calls != 1u) ||
        (deinit_calls != 2u) || (service.initialized != 0u) ||
        (service.handle.marker != 0u)) return 33;
    return 0;
}}

int main(void)
{{
    int result;
    result = test_disable_retry();
    if (result != 0) return result;
    result = test_unbind_retry();
    if (result != 0) return result;
    result = test_deinit_retry();
    if (result != 0) return result;
    (void)printf("uart_cleanup_retry=PASS\\n");
    return 0;
}}
"""


def test_uart_cleanup_retries_only_unfinished_physical_steps(
    tmp_path: Path,
) -> None:
    compiler = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if compiler is None:
        pytest.skip("a C compiler is required for the UART cleanup harness")

    source = tmp_path / "uart_cleanup_harness.c"
    executable = tmp_path / "uart_cleanup_harness"
    source.write_text(_harness_source(), encoding="utf-8")
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
    assert completed.stdout.strip() == "uart_cleanup_retry=PASS"
