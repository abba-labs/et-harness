# Framework Validation测试模块。
#
# 职责：验证test_dma_reliability_contract 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[5]
DMA_SERVICE = ROOT / "firmware/services/src/et_dma_service.c"
DMA_HEADER = ROOT / "firmware/services/include/et_dma_service.h"
DMA_WRAP = ROOT / "firmware/wrap/src/et_dma_wrap.c"
DMA_DRIVER = ROOT / "pc/et_test_platform/drivers/dma/driver.py"
DMA_CONTRACT = ROOT / "pc/et_test_platform/drivers/dma/contract.py"
SYSCTRL_SERVICE = ROOT / "firmware/services/src/et_sysctrl_service.c"
SYSCTRL_WRAP = ROOT / "firmware/wrap/src/et_sysctrl_wrap.c"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _case_block(source: str, label: str, next_label: str) -> str:
    start = source.index(f"case {label}:")
    end = source.index(f"case {next_label}:", start)
    return source[start:end]


def test_dma_service_state_owns_only_dma_lifecycle_and_irq_session() -> None:
    header = _source(DMA_HEADER)

    for required in (
        "controller_id",
        "controller_enabled",
        "channel_count",
        "configured_channels",
        "active_channels",
        "irq_enabled",
        "irq_hardware_enabled",
        "route_bound_mask",
        "irq_result",
    ):
        assert required in header

    for forbidden in (
        "resource_pool_owned_channels",
        "route_ownership",
        "source_route_interface",
        "destination_route_interface",
        "source_route_address",
        "destination_route_address",
        "ET_DMA_ROUTE_OWN_SOURCE",
        "ET_DMA_ROUTE_OWN_DESTINATION",
    ):
        assert forbidden not in header


def test_dma_service_has_no_cross_ip_resource_or_route_registry() -> None:
    service = _source(DMA_SERVICE)

    for forbidden in (
        "et_resource_wrap",
        "acquire_config_ownership",
        "release_channel_ownership",
        "memory_range_is_valid",
        "peripheral_endpoint_is_valid",
        "validate_dma_route",
        "resolve_range",
        "route_lease",
        "pool_lease",
        "endpoint_registry",
    ):
        assert forbidden not in service

    assert "et_dma_wrap_configure_channel(&config)" in service
    assert "et_dma_wrap_deconfigure_channel(" in service


def test_sysctrl_service_and_wrap_execute_direct_request_id_only() -> None:
    service = _source(SYSCTRL_SERVICE)
    wrap = _source(SYSCTRL_WRAP)

    assert "ET_SYSCTRL_COMMAND_DMA_REQUEST_CONFIGURE_V2" in service
    assert "request_body[ET_SYSCTRL_DMA_REQUEST_ID_OFFSET]" in service
    assert "et_sysctrl_wrap_configure_dma_request(" in service
    assert "et_resource_wrap" not in service
    assert "read_u64" not in service

    assert "(SYSCTRL_DMAReqIdx)request_id" in wrap
    assert "ET_CHIP_UART_DMA_REQUEST_TABLE" not in wrap
    assert "uart_dma_requests" not in wrap
    assert "map_request" not in wrap
    assert "endpoint" not in wrap
    assert "instance_id" not in wrap


def test_deprecated_sysctrl_v1_is_not_silently_reinterpreted() -> None:
    service = _source(SYSCTRL_SERVICE)
    start = service.index("if (command_id == ET_SYSCTRL_COMMAND_DMA_REQUEST_CONFIGURE)")
    end = service.index(
        "if (command_id == ET_SYSCTRL_COMMAND_DMA_REQUEST_RELEASE)",
        start,
    )
    block = service[start:end]

    assert "ET_SYSCTRL_DMA_REQUEST_V1_SIZE" in block
    assert "ET_STATUS_NOT_SUPPORTED" in block
    assert "et_sysctrl_wrap_configure_dma_request" not in block


def test_dma_lli_v2_uses_direct_address_and_old_command_is_deprecated() -> None:
    service = _source(DMA_SERVICE)
    header = _source(DMA_HEADER)
    contract = _source(DMA_CONTRACT)

    assert "ET_DMA_COMMAND_LLI_DESCRIPTOR_INIT_V2 = 0x001cu" in header
    assert "LLI_DESCRIPTOR_INIT_V2 = 0x001C" in contract
    assert "ET_DMA_SERVICE_LLI_V2_REQUEST_SIZE 80u" in header
    assert (
        "descriptor_wire = read_u64(&request_body[ET_DMA_SERVICE_LLI_DESCRIPTOR_OFFSET])" in service
    )
    assert "(uint64_t)descriptor_address != descriptor_wire" in service
    assert "et_dma_wrap_init_lli_descriptor(" in service

    old_block = _case_block(
        service,
        "ET_DMA_COMMAND_LLI_DESCRIPTOR_INIT",
        "ET_DMA_COMMAND_LLI_DESCRIPTOR_INIT_V2",
    )
    assert "ET_DMA_SERVICE_LLI_V1_REQUEST_SIZE" in old_block
    assert "ET_STATUS_NOT_SUPPORTED" in old_block
    assert "et_dma_wrap_init_lli_descriptor" not in old_block


def test_dma_config_decode_keeps_wire_and_pointer_safety_checks() -> None:
    service = _source(DMA_SERVICE)
    decode = service[service.index("static int decode_config(") :]
    decode = decode[: decode.index("static void result_write_begin(")]

    assert "length != ET_DMA_SERVICE_CONFIG_REQUEST_SIZE" in decode
    assert "ET_DMA_SERVICE_HANDSHAKE_CONFIG_MASK" in decode
    assert "channel_is_valid" in decode
    assert "(uint64_t)source_address != source" in decode
    assert "(uint64_t)destination_address != destination" in decode
    assert "(uint64_t)linked_list_address != linked_list" in decode
    assert "et_dma_wrap_get_default_config" in decode
    assert "et_resource_wrap" not in decode


def test_dma_read_only_commands_still_request_exact_duplicate_retry() -> None:
    source = _source(DMA_DRIVER)

    assert "_READ_ONLY_COMMANDS" in source
    assert "_IDEMPOTENT_COMMANDS" in source
    assert "_RETRY_SAFE_COMMANDS" in source
    assert '"retry_safe": DmaCommand(command) in self._RETRY_SAFE_COMMANDS' in source


def test_dma_channel_status_uses_raw_terminal_events() -> None:
    wrap = _source(DMA_WRAP)
    service = _source(DMA_SERVICE)

    assert "get_channel_raw_interrupt_flags" in wrap
    status = wrap[wrap.index("et_wrap_status_t et_dma_wrap_get_channel_status(") :]
    status = status[: status.index("et_wrap_status_t et_dma_wrap_enable_interrupts(")]
    assert "get_channel_raw_interrupt_flags" in status
    start = service[service.index("ET_DMA_COMMAND_CHANNEL_START") :]
    assert "ET_DMA_SERVICE_ALL_IRQ_EVENTS" in start


def test_dma_managed_irq_enable_requires_configured_idle_channel() -> None:
    source = _source(DMA_SERVICE)
    block = source[source.index("static uint16_t irq_enable(") :]
    block = block[: block.index("static uint16_t irq_disable(")]

    assert "service->controller_enabled == 0u" in block
    assert "service->configured_channels" in block
    assert "service->active_channels != 0u" in block


def test_dma_managed_irq_mask_sequence_preserves_same_route_only() -> None:
    source = _source(DMA_SERVICE)
    start = source.index("case ET_DMA_COMMAND_INTERRUPT_MASK_ENABLE:")
    end = source.index("case ET_DMA_COMMAND_IRQ_ENABLE:", start)
    block = source[start:end]

    assert "if (service->controller_enabled == 0u)" in block
    assert "channel != service->irq_channel" in block
    assert "ET_DMA_SERVICE_IRQ_EVENTS_OFFSET" in block
    assert "service->enabled_events" in block
    assert "if ((service->controller_enabled == 0u) ||" not in block
    assert "command_id != ET_DMA_COMMAND_INTERRUPT_PENDING_CLEAR" in block
    assert "service->irq_hardware_enabled =" in block
    assert "(command_id == ET_DMA_COMMAND_INTERRUPT_MASK_ENABLE) ? 1u : 0u" in block
