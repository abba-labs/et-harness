# Framework Validation测试模块。
#
# 职责：验证test_dma_helpers 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import inspect

from et_test_platform.drivers.dma import DmaTransferType
from et_test_platform.test_cases.dma import dma_helpers, dma_irq_helpers
from et_test_platform.test_cases.dma._support import require_dma_transfer_capability
from et_test_platform.test_cases.dma.dma_helpers import (
    DMA_ADDRESS_DECREMENT,
    DMA_ADDRESS_FIXED,
    DMA_ADDRESS_INCREMENT,
    build_dma_m2m_vector,
)


class _TransferCapabilitiesFake:
    def instances(self, ip_name: str) -> tuple[str, ...]:
        assert ip_name == "dma"
        return ("dma0",)

    def options(self, ip_name: str, feature_name: str, *, instance: str) -> tuple[str, ...]:
        assert ip_name == "dma"
        assert feature_name == "transfer_type_and_flow_control"
        assert instance == "dma0"
        return ("peripheral_to_peripheral",)


def test_dma_address_vector_covers_increment_decrement_and_fixed() -> None:
    increment = build_dma_m2m_vector(3, 0, DMA_ADDRESS_INCREMENT, DMA_ADDRESS_INCREMENT)
    source_decrement = build_dma_m2m_vector(3, 0, DMA_ADDRESS_DECREMENT, DMA_ADDRESS_INCREMENT)
    destination_decrement = build_dma_m2m_vector(3, 0, DMA_ADDRESS_INCREMENT, DMA_ADDRESS_DECREMENT)
    source_fixed = build_dma_m2m_vector(3, 0, DMA_ADDRESS_FIXED, DMA_ADDRESS_INCREMENT)
    destination_fixed = build_dma_m2m_vector(3, 0, DMA_ADDRESS_INCREMENT, DMA_ADDRESS_FIXED)

    assert increment.expected_destination == increment.source_data
    assert source_decrement.expected_destination == bytes(reversed(source_decrement.source_data))
    assert destination_decrement.expected_destination == bytes(
        reversed(destination_decrement.source_data)
    )
    assert source_fixed.expected_destination == source_fixed.source_data[:1] * 3
    assert destination_fixed.expected_destination[0:1] == destination_fixed.source_data[-1:]
    assert destination_fixed.expected_destination[1:] == b"\xa5\xa5"


def test_dma_transfer_capability_gate_is_static_only() -> None:
    instance = require_dma_transfer_capability(
        _TransferCapabilitiesFake(),
        instance_id=0,
        transfer_type=DmaTransferType.PERIPHERAL_TO_PERIPHERAL,
    )

    assert instance == "dma0"
    source = inspect.getsource(require_dma_transfer_capability)
    assert "capabilities_get" not in source
    assert "DmaDriver" not in source


def test_dma_case_helpers_do_not_export_capability_gates() -> None:
    assert not any(name.startswith("require_dma_") for name in dir(dma_helpers))

    helper_source = inspect.getsource(dma_helpers)
    assert "ChipCapabilities" not in helper_source
    assert "CapabilityLookupError" not in helper_source


def test_dma_irq_helpers_do_not_export_capability_gates() -> None:
    assert dma_irq_helpers.__all__ == ["DMA_P0_REQUIRED_CAPABILITIES"]
    assert not any(name.startswith("require_dma_") for name in dir(dma_irq_helpers))

    irq_helper_source = inspect.getsource(dma_irq_helpers)
    assert "ChipCapabilities" not in irq_helper_source
    assert "CapabilityLookupError" not in irq_helper_source
    assert "scheduling.dma_support" not in irq_helper_source


def test_dma_case_helpers_do_not_own_runtime_waits() -> None:
    source = inspect.getsource(dma_helpers)

    assert "def wait_for_irq_count(" not in source
    assert "def wait_channel_free(" not in source
