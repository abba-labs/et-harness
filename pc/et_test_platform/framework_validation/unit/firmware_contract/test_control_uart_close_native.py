# Framework Validation测试模块。
#
# 职责：验证test_control_uart_close_native 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[5]
CONTROL_UART = ROOT / "firmware/application/src/et_control_uart.c"


def _extract_close() -> str:
    source = CONTROL_UART.read_text(encoding="utf-8")
    start = source.index("int et_control_uart_close(")
    end = source.index("void et_control_uart_poll(", start)
    return source[start:end]


def _harness() -> str:
    close_function = _extract_close()
    return f"""
#include <stdint.h>
#include <stdio.h>

typedef enum {{
    ET_WRAP_STATUS_OK = 0,
    ET_WRAP_STATUS_IO_ERROR = 1
}} et_wrap_status_t;

typedef struct {{ uint32_t unused; }} et_uart_wrap_handle_t;
typedef struct {{ uint32_t unused; }} et_irq_manager_t;
typedef struct {{ uint32_t irq_line; }} et_irq_route_t;
typedef struct {{
    uint8_t rx_mode;
    et_irq_manager_t *irq_manager;
}} et_control_uart_config_t;
typedef struct {{ uint32_t port_errors; }} et_control_uart_stats_t;
typedef struct {{
    et_control_uart_config_t config;
    et_uart_wrap_handle_t uart;
    et_irq_route_t irq_route;
    et_control_uart_stats_t stats;
    uint8_t opened;
    uint8_t uart_initialized;
    uint8_t irq_bound;
    uint8_t irq_enabled;
}} et_control_uart_t;

#define ET_UART_WRAP_IRQ_ERROR (1u << 0)
#define ET_CONTROL_UART_MODE_IRQ 1u
#define ET_UART_WRAP_IRQ_RX_READY (1u << 1)
#define ET_UART_WRAP_IRQ_RX_IDLE (1u << 2)

static uint8_t fail_disable_once;
static uint8_t fail_unbind_once;
static uint8_t fail_deinit_once;
static uint32_t disable_calls;
static uint32_t unbind_calls;
static uint32_t deinit_calls;

static uint32_t control_uart_interrupt_mask(
    const et_control_uart_t *transport)
{{
    return (transport->config.rx_mode == ET_CONTROL_UART_MODE_IRQ)
        ? (ET_UART_WRAP_IRQ_ERROR | ET_UART_WRAP_IRQ_RX_READY |
           ET_UART_WRAP_IRQ_RX_IDLE)
        : ET_UART_WRAP_IRQ_ERROR;
}}

static et_wrap_status_t et_uart_wrap_disable_interrupts(
    et_uart_wrap_handle_t *uart,
    uint32_t mask)
{{
    (void)uart;
    (void)mask;
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
    (void)manager;
    (void)line;
    (void)callback;
    (void)context;
    ++unbind_calls;
    if (fail_unbind_once != 0u) {{
        fail_unbind_once = 0u;
        return -1;
    }}
    return 0;
}}

static et_wrap_status_t et_uart_wrap_deinit(et_uart_wrap_handle_t *uart)
{{
    (void)uart;
    ++deinit_calls;
    if (fail_deinit_once != 0u) {{
        fail_deinit_once = 0u;
        return ET_WRAP_STATUS_IO_ERROR;
    }}
    return ET_WRAP_STATUS_OK;
}}

static void control_uart_irq_handler(
    void *context,
    uint32_t line,
    uint32_t events)
{{
    (void)context;
    (void)line;
    (void)events;
}}

{close_function}

static void initialize(et_control_uart_t *transport)
{{
    static et_irq_manager_t manager;
    *transport = (et_control_uart_t){{0}};
    transport->config.rx_mode = ET_CONTROL_UART_MODE_IRQ;
    transport->config.irq_manager = &manager;
    transport->opened = 1u;
    transport->uart_initialized = 1u;
    transport->irq_bound = 1u;
    transport->irq_enabled = 1u;
}}

int main(void)
{{
    et_control_uart_t transport;

    initialize(&transport);
    fail_disable_once = 1u;
    if (et_control_uart_close(&transport) == 0) return 10;
    if ((transport.opened != 0u) || (transport.irq_enabled == 0u) ||
        (transport.irq_bound == 0u) || (transport.uart_initialized == 0u) ||
        (disable_calls != 1u) || (unbind_calls != 0u) ||
        (deinit_calls != 0u) || (transport.stats.port_errors != 1u)) return 11;
    if (et_control_uart_close(&transport) != 0) return 12;
    if ((disable_calls != 2u) || (unbind_calls != 1u) ||
        (deinit_calls != 1u)) return 13;

    disable_calls = unbind_calls = deinit_calls = 0u;
    initialize(&transport);
    fail_unbind_once = 1u;
    if (et_control_uart_close(&transport) == 0) return 20;
    if ((transport.irq_enabled != 0u) || (transport.irq_bound == 0u) ||
        (transport.uart_initialized == 0u) || (disable_calls != 1u) ||
        (unbind_calls != 1u) || (deinit_calls != 0u)) return 21;
    if (et_control_uart_close(&transport) != 0) return 22;
    if ((disable_calls != 1u) || (unbind_calls != 2u) ||
        (deinit_calls != 1u)) return 23;

    disable_calls = unbind_calls = deinit_calls = 0u;
    initialize(&transport);
    fail_deinit_once = 1u;
    if (et_control_uart_close(&transport) == 0) return 30;
    if ((transport.irq_enabled != 0u) || (transport.irq_bound != 0u) ||
        (transport.uart_initialized == 0u) || (disable_calls != 1u) ||
        (unbind_calls != 1u) || (deinit_calls != 1u)) return 31;
    if (et_control_uart_close(&transport) != 0) return 32;
    if ((disable_calls != 1u) || (unbind_calls != 1u) ||
        (deinit_calls != 2u)) return 33;

    if (et_control_uart_close(&transport) != 0) return 40;
    if (deinit_calls != 2u) return 41;
    (void)printf("control_uart_close_retry=PASS\\n");
    return 0;
}}
"""


def test_control_uart_close_retries_only_unfinished_steps(tmp_path: Path) -> None:
    compiler = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if compiler is None:
        pytest.skip("a C compiler is required for the control UART close harness")
    source = tmp_path / "control_uart_close_harness.c"
    executable = tmp_path / "control_uart_close_harness"
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
    assert completed.stdout.strip() == "control_uart_close_retry=PASS"
