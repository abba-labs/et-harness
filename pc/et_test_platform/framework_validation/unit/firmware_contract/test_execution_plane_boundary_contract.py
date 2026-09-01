# Framework Validation测试模块。
#
# 职责：验证test_execution_plane_boundary_contract 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[5]
SERVICES = ROOT / "firmware" / "services" / "src"
RESOURCE_HEADER = ROOT / "firmware" / "wrap" / "include" / "et_resource_wrap.h"
RESOURCE_SOURCE = ROOT / "firmware" / "wrap" / "src" / "et_resource_wrap.c"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_uart_service_calls_uart_wrap_and_common_irq_only() -> None:
    source = _source(SERVICES / "et_uart_service.c")
    for forbidden in (
        "et_resource_wrap",
        "et_sysctrl_wrap",
        "et_dma_wrap",
        "publish_dma_endpoint",
        "endpoint_registry",
        "route_registry",
        "route_lease",
    ):
        assert forbidden not in source
    assert "et_uart_wrap_" in source
    assert "et_irq_manager_" in source


def test_resource_wrap_is_buffer_pool_only() -> None:
    source = _source(RESOURCE_HEADER) + "\n" + _source(RESOURCE_SOURCE)
    for forbidden in (
        "dma_endpoint",
        "dma_route",
        "provider",
        "endpoint_id",
        "route_events",
        "lease_count",
        "acquire_pool",
        "release_pool",
        "publish_dma_endpoint",
        "bind_dma_route",
        "validate_dma_route",
    ):
        assert forbidden not in source
    for required in (
        "et_resource_wrap_create",
        "et_resource_wrap_write",
        "et_resource_wrap_read",
        "et_resource_wrap_fill",
        "et_resource_wrap_resolve",
        "et_resource_wrap_get_info",
    ):
        assert required in source
