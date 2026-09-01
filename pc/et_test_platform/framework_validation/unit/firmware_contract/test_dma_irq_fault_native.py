# Framework Validation测试模块。
#
# 职责：验证test_dma_irq_fault_native 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[5]
DMA_SERVICE = ROOT / "firmware/services/src/et_dma_service.c"


def _extract_helper() -> str:
    source = DMA_SERVICE.read_text(encoding="utf-8")
    start = source.index("static void record_irq_observation_fault(")
    end = source.index("static void dma_irq_callback(", start)
    return source[start:end]


def _harness() -> str:
    helper = _extract_helper()
    return f"""
#include <stdint.h>
#include <stdio.h>

typedef enum {{
    ET_WRAP_STATUS_OK = 0,
    ET_WRAP_STATUS_IO_ERROR = 1
}} et_wrap_status_t;

typedef uint8_t et_dma_wrap_controller_id_t;
typedef uint8_t et_dma_wrap_channel_id_t;

typedef struct {{
    volatile uint32_t latched_events;
    volatile uint32_t irq_count;
    volatile uint32_t unexpected_count;
    volatile uint32_t overflow_count;
}} et_dma_irq_result_t;

typedef struct {{
    et_dma_wrap_controller_id_t controller_id;
    et_dma_wrap_channel_id_t irq_channel;
    uint8_t irq_priority;
    uint8_t irq_enabled;
    uint8_t irq_combined;
    uint8_t irq_hardware_enabled;
    uint32_t enabled_events;
    volatile uint32_t result_generation;
    et_dma_irq_result_t irq_result;
}} et_dma_service_t;

static et_wrap_status_t disable_status;
static et_wrap_status_t clear_status;
static uint32_t disable_calls;
static uint32_t clear_calls;

static et_wrap_status_t et_dma_wrap_disable_interrupts(
    et_dma_wrap_controller_id_t controller,
    et_dma_wrap_channel_id_t channel,
    uint32_t events)
{{
    (void)controller;
    (void)channel;
    (void)events;
    ++disable_calls;
    return disable_status;
}}

static et_wrap_status_t et_dma_wrap_clear_interrupts(
    et_dma_wrap_controller_id_t controller,
    et_dma_wrap_channel_id_t channel,
    uint32_t events)
{{
    (void)controller;
    (void)channel;
    (void)events;
    ++clear_calls;
    return clear_status;
}}

static void increment_saturating(volatile uint32_t *value)
{{
    if ((value != NULL) && (*value != UINT32_MAX)) {{
        ++(*value);
    }}
}}

static void result_write_begin(et_dma_service_t *service)
{{
    ++service->result_generation;
}}

static void result_write_end(et_dma_service_t *service)
{{
    ++service->result_generation;
}}

{helper}

static void init_service(et_dma_service_t *service)
{{
    *service = (et_dma_service_t){{0}};
    service->controller_id = 1u;
    service->irq_channel = 3u;
    service->irq_hardware_enabled = 1u;
    service->enabled_events = 0x1fu;
}}

int main(void)
{{
    et_dma_service_t service;

    init_service(&service);
    disable_status = ET_WRAP_STATUS_OK;
    clear_status = ET_WRAP_STATUS_OK;
    record_irq_observation_fault(&service);
    if ((service.irq_result.unexpected_count != 1u) ||
        (service.irq_result.overflow_count != 0u) ||
        (service.irq_hardware_enabled != 0u) ||
        (service.result_generation != 2u) ||
        (disable_calls != 1u) || (clear_calls != 1u)) return 10;

    init_service(&service);
    disable_calls = clear_calls = 0u;
    disable_status = ET_WRAP_STATUS_IO_ERROR;
    clear_status = ET_WRAP_STATUS_IO_ERROR;
    record_irq_observation_fault(&service);
    if ((service.irq_result.unexpected_count != 1u) ||
        (service.irq_result.overflow_count != 1u) ||
        (service.irq_hardware_enabled != 1u) ||
        (service.result_generation != 2u) ||
        (disable_calls != 1u) || (clear_calls != 1u)) return 20;

    (void)printf("dma_irq_observation_fault=PASS\\n");
    return 0;
}}
"""


def test_dma_irq_observation_failure_is_visible_and_bounded(
    tmp_path: Path,
) -> None:
    compiler = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if compiler is None:
        pytest.skip("a C compiler is required for the DMA IRQ fault harness")

    source = tmp_path / "dma_irq_fault_harness.c"
    executable = tmp_path / "dma_irq_fault_harness"
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
    assert completed.stdout.strip() == "dma_irq_observation_fault=PASS"
