# Framework Validation测试模块。
#
# 职责：验证test_interrupt_case 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

from dataclasses import astuple, dataclass
from pathlib import Path

import pytest
import yaml

from et_test_platform.communication.protocols.et_message import ServiceMessage
from et_test_platform.core.errors import (
    CapabilityLookupError,
    ProtocolError,
    UnsupportedCapability,
)
from et_test_platform.drivers.dma import (
    CAPABILITIES,
    CHANNEL_SNAPSHOT,
    COMPONENT_SNAPSHOT,
    DMA_CONFIG,
    DMA_SERVICE_ID,
    INTERRUPT_SNAPSHOT,
    LLI_DESCRIPTOR_LOCATION,
    DmaAccessView,
    DmaBurst,
    DmaCapabilities,
    DmaCommand,
    DmaConfig,
    DmaDriver,
    DmaFeature,
    DmaFifoMode,
    DmaIrqEvent,
    DmaIrqResult,
)
from et_test_platform.drivers.resource import ResourceRef
from et_test_platform.profiles.capabilities import (
    load_packaged_chip_capabilities,
)
from et_test_platform.test_cases.dma._support import (
    require_dma_control_writeback_capability,
    require_dma_transfer_done_capabilities,
    require_dma_transfer_done_firmware_capabilities,
)
from et_test_platform.test_cases.dma.dma_irq_helpers import DMA_P0_REQUIRED_CAPABILITIES

CODE_ROOT = Path(__file__).parents[6]
DMA_P0_REQUIREMENTS = CODE_ROOT / "tools" / "capabilities" / "requirements" / "dma_p0.yaml"


class _ControlWritebackCapabilities:
    def __init__(self, *, feature: bool, parameter: bool) -> None:
        self._feature = feature
        self._parameter = parameter

    def instances(self, ip_id: str) -> tuple[str, ...]:
        assert ip_id == "dma"
        return ("dma0",)

    def has_feature(self, ip_id: str, name: str, *, instance: str) -> bool:
        assert (ip_id, name, instance) == ("dma", "control_writeback", "dma0")
        return self._feature

    def parameter(
        self,
        ip_id: str,
        name: str,
        *,
        instance: str,
        member: str,
    ) -> bool:
        assert (ip_id, name, instance, member) == (
            "dma",
            "control_writeback",
            "dma0",
            "channel_0",
        )
        return self._parameter


# Catch a common Case relying on a chip name or assumed SVD bit value.
@pytest.mark.parametrize(
    ("feature", "parameter"),
    ((False, True), (True, False)),
)
def test_done_writeback_requires_semantic_profile_capability(
    feature: bool,
    parameter: bool,
) -> None:

    with pytest.raises(UnsupportedCapability, match="control_writeback"):
        require_dma_control_writeback_capability(
            _ControlWritebackCapabilities(  # type: ignore[arg-type]
                feature=feature,
                parameter=parameter,
            ),
            instance_id=0,
            channel=0,
        )


class _Resource:
    def __init__(self) -> None:
        self._next = 1
        self._data: dict[int, bytearray] = {}

    def reset(self) -> None:
        self._data.clear()

    def create(self, size: int, alignment: int = 4) -> ResourceRef:
        del alignment
        handle = self._next
        self._next += 1
        self._data[handle] = bytearray(size)
        return ResourceRef(handle, size, 0x20400000 + handle * 0x1000)

    def write(self, resource: ResourceRef, data: bytes, offset: int = 0) -> None:
        self._data[resource.handle][offset : offset + len(data)] = data

    def fill(
        self,
        resource: ResourceRef,
        value: int,
        size: int | None = None,
        offset: int = 0,
    ) -> None:
        count = resource.size - offset if size is None else size
        self._data[resource.handle][offset : offset + count] = bytes((value,)) * count

    def read(
        self,
        resource: ResourceRef,
        size: int | None = None,
        offset: int = 0,
    ) -> bytes:
        count = resource.size - offset if size is None else size
        return bytes(self._data[resource.handle][offset : offset + count])


@dataclass
class _Dma:
    resource: _Resource
    instance_id: int = 0
    enabled: bool = False
    config: DmaConfig | None = None
    irq_enabled: bool = False
    started: bool = False
    capability_queries: int = 0
    reported_capabilities: DmaCapabilities | None = None

    def capabilities_get(self) -> DmaCapabilities:
        self.capability_queries += 1
        if self.reported_capabilities is not None:
            return self.reported_capabilities
        return DmaCapabilities(
            features=DmaFeature.MEMORY_TO_MEMORY | DmaFeature.INTERRUPTS,
            channel_count=8,
            max_transfer_count=4095,
            max_gather_scatter_interval=0x0FFFFF,
            max_gather_scatter_count=0x0FFF,
            irq_events=DmaIrqEvent.TRANSFER_DONE,
        )

    def controller_enable(self) -> None:
        self.enabled = True

    def controller_disable(self) -> None:
        self.enabled = False

    def configure(self, config: DmaConfig) -> None:
        self.config = config

    def deconfigure(self, channel: int) -> None:
        del channel
        self.config = None

    def irq_enable(
        self,
        channel: int,
        events: DmaIrqEvent,
        priority: int,
    ) -> int:
        del channel, events, priority
        self.irq_enabled = True
        return 1

    def irq_disable(self, events: DmaIrqEvent) -> None:
        del events
        self.irq_enabled = False

    def start(self, channel: int) -> None:
        del channel
        assert self.config is not None
        source_handle = (self.config.source_address - 0x20400000) // 0x1000
        destination_handle = (self.config.destination_address - 0x20400000) // 0x1000
        self.resource._data[destination_handle][: self.config.transfer_count] = self.resource._data[
            source_handle
        ][: self.config.transfer_count]
        self.started = True

    def stop(self, channel: int) -> None:
        del channel
        self.started = False

    def irq_result_get(self) -> DmaIrqResult:
        return DmaIrqResult(
            DmaIrqEvent.TRANSFER_DONE if self.started else DmaIrqEvent(0),
            1 if self.started else 0,
            0,
            0,
        )


class _MissingDmaCapabilities:
    def instances(self, ip_id: str) -> tuple[str, ...]:
        assert ip_id == "dma"
        return ("dma0",)

    def options(
        self,
        ip_id: str,
        name: str,
        *,
        instance: str,
    ) -> tuple[str, ...]:
        del ip_id, name, instance
        raise CapabilityLookupError("transfer mode is not described")


class _DmaCapabilityTarget:
    def __init__(self, response: bytes) -> None:
        self.response = response
        self.calls: list[tuple[int, int, int, bytes]] = []

    def request(
        self,
        service_id: int,
        command_id: int,
        *,
        instance_id: int = 0,
        body: bytes = b"",
        retry_safe: bool = False,
    ):
        del retry_safe
        self.calls.append((service_id, command_id, instance_id, body))
        return (
            ServiceMessage(
                service_id=service_id,
                command_id=command_id,
                instance_id=instance_id,
                body=self.response,
            ),
            object(),
        )


def test_dma_config_wire_contract_is_fixed_to_64_bytes() -> None:
    encoded = DmaConfig(
        channel=2,
        source_address=0x20400000,
        destination_address=0x20401000,
        transfer_count=256,
    ).encode()

    assert DMA_CONFIG.size == 64
    assert len(encoded) == 64
    assert encoded[0] == 2
    assert int.from_bytes(encoded[16:24], "little") == 0x20400000
    assert int.from_bytes(encoded[24:32], "little") == 0x20401000
    assert int.from_bytes(encoded[32:36], "little") == 256


def test_dma_capabilities_get_decodes_the_firmware_wire_contract() -> None:
    target = _DmaCapabilityTarget(
        CAPABILITIES.pack(
            int(DmaFeature.MEMORY_TO_MEMORY | DmaFeature.INTERRUPTS),
            8,
            4095,
            0x0FFFFF,
            0x0FFF,
            int(DmaIrqEvent.TRANSFER_DONE | DmaIrqEvent.ERROR),
        )
    )

    driver = DmaDriver(target, instance_id=1)  # type: ignore[arg-type]
    capabilities = driver.capabilities_get()

    assert target.calls == [(DMA_SERVICE_ID, DmaCommand.CAPABILITIES_GET, 1, b"")]
    assert capabilities.channel_count == 8
    assert capabilities.max_transfer_count == 4095
    assert capabilities.features & DmaFeature.MEMORY_TO_MEMORY
    assert capabilities.irq_events == (DmaIrqEvent.TRANSFER_DONE | DmaIrqEvent.ERROR)


def test_dma_lifecycle_commands_keep_the_atomic_wire_contract() -> None:
    target = _DmaCapabilityTarget(b"")
    driver = DmaDriver(target, instance_id=1)  # type: ignore[arg-type]

    driver.suspend(3)
    driver.resume(3)
    driver.start_channels(0xA5)
    driver.interrupt_mask_enable(3, DmaIrqEvent.TRANSFER_DONE)
    driver.interrupt_mask_disable(3, DmaIrqEvent.TRANSFER_DONE)
    driver.interrupt_pending_clear(3, DmaIrqEvent.TRANSFER_DONE)

    assert target.calls == [
        (
            DMA_SERVICE_ID,
            DmaCommand.CHANNEL_SUSPEND,
            1,
            b"\x03\x00\x00\x00",
        ),
        (
            DMA_SERVICE_ID,
            DmaCommand.CHANNEL_RESUME,
            1,
            b"\x03\x00\x00\x00",
        ),
        (
            DMA_SERVICE_ID,
            DmaCommand.CHANNELS_START,
            1,
            b"\xa5\x00\x00\x00",
        ),
        (
            DMA_SERVICE_ID,
            DmaCommand.INTERRUPT_MASK_ENABLE,
            1,
            b"\x01\x00\x00\x00\x03\x00\x00\x00",
        ),
        (
            DMA_SERVICE_ID,
            DmaCommand.INTERRUPT_MASK_DISABLE,
            1,
            b"\x01\x00\x00\x00\x03\x00\x00\x00",
        ),
        (
            DMA_SERVICE_ID,
            DmaCommand.INTERRUPT_PENDING_CLEAR,
            1,
            b"\x01\x00\x00\x00\x03\x00\x00\x00",
        ),
    ]

    with pytest.raises(ValueError, match="channel mask"):
        driver.start_channels(0)


def test_dma_find_free_channel_decodes_four_byte_response() -> None:
    target = _DmaCapabilityTarget(b"\x05\x00\x00\x00")

    channel = DmaDriver(  # type: ignore[arg-type]
        target,
        instance_id=1,
    ).find_free_channel()

    assert channel == 5
    assert target.calls == [(DMA_SERVICE_ID, DmaCommand.FREE_CHANNEL_FIND, 1, b"")]


def test_dma_find_free_channel_rejects_wrong_response_size() -> None:
    target = _DmaCapabilityTarget(b"\x05")

    with pytest.raises(ProtocolError, match="free-channel"):
        DmaDriver(target).find_free_channel()  # type: ignore[arg-type]


def test_dma_component_snapshot_decodes_fixed_wire_contract() -> None:
    values = tuple(range(0x10, 0x1C))
    target = _DmaCapabilityTarget(COMPONENT_SNAPSHOT.pack(*values))

    snapshot = DmaDriver(target, instance_id=1).component_snapshot_get(  # type: ignore[arg-type]
        DmaAccessView.ACC
    )

    assert snapshot.dma_id == values[0]
    assert snapshot.component_id == values[1]
    assert snapshot.channel_params == values[2:10]
    assert snapshot.multi_block_params == values[10]
    assert snapshot.max_block_size_params == values[11]
    assert target.calls == [
        (
            DMA_SERVICE_ID,
            DmaCommand.COMPONENT_SNAPSHOT_GET,
            1,
            b"\x01\x00\x00\x00",
        )
    ]


def test_dma_interrupt_and_channel_snapshots_decode_fixed_contracts() -> None:
    interrupt_values = tuple(range(16))
    target = _DmaCapabilityTarget(INTERRUPT_SNAPSHOT.pack(*interrupt_values))
    driver = DmaDriver(target)  # type: ignore[arg-type]

    interrupt = driver.interrupt_snapshot_get()

    assert interrupt.raw == interrupt_values[0:5]
    assert interrupt.status == interrupt_values[5:10]
    assert interrupt.mask == interrupt_values[10:15]
    assert interrupt.combined_status == interrupt_values[15]

    # 构造完整13字段响应；最后4项使用稳定业务枚举和边界Block Size。
    channel_values = (
        *range(0x20, 0x29),
        int(DmaBurst.ITEMS_64),
        int(DmaBurst.ITEMS_16),
        257,
        int(DmaFifoMode.HALF_DEPTH),
    )
    target.response = CHANNEL_SNAPSHOT.pack(*channel_values)
    channel = driver.channel_snapshot_get(7)

    assert astuple(channel) == (
        *channel_values[:9],
        DmaBurst.ITEMS_64,
        DmaBurst.ITEMS_16,
        257,
        DmaFifoMode.HALF_DEPTH,
    )
    assert target.calls[-1] == (
        DMA_SERVICE_ID,
        DmaCommand.CHANNEL_SNAPSHOT_GET,
        0,
        b"\x07\x00\x00\x00",
    )


def test_dma_lli_descriptor_init_appends_only_location_metadata() -> None:
    target = _DmaCapabilityTarget(b"")
    driver = DmaDriver(target, instance_id=1)  # type: ignore[arg-type]
    config = DmaConfig(
        channel=3,
        source_address=0x20401000,
        destination_address=0x20402000,
        transfer_count=64,
        linked_list_address=0x20403000,
        source_update_mode=2,
        destination_update_mode=2,
    )

    driver.lli_descriptor_init(0x00010001, config, is_last=False)

    body = target.calls[0][3]
    assert len(body) == DMA_CONFIG.size + LLI_DESCRIPTOR_LOCATION.size == 76
    assert body[: DMA_CONFIG.size] == config.encode()
    assert LLI_DESCRIPTOR_LOCATION.unpack(body[DMA_CONFIG.size :]) == (
        0x00010001,
        0,
        0,
    )


@pytest.mark.parametrize(
    "response",
    [
        b"\x00" * (CAPABILITIES.size - 1),
        CAPABILITIES.pack(0, 0, 4095, 0, 0, 0),
        CAPABILITIES.pack(0, 8, 0, 0, 0, 0),
    ],
)
def test_dma_capabilities_get_rejects_invalid_responses(response: bytes) -> None:
    target = _DmaCapabilityTarget(response)

    with pytest.raises(ProtocolError, match="CAPABILITIES_GET"):
        DmaDriver(target).capabilities_get()  # type: ignore[arg-type]


def test_dma_p0_case_queries_exactly_the_frozen_requirement_list() -> None:
    raw = yaml.safe_load(DMA_P0_REQUIREMENTS.read_text(encoding="utf-8"))

    assert tuple(raw["required_capabilities"]) == (DMA_P0_REQUIRED_CAPABILITIES)


def test_dma_transfer_done_contract_rejects_unsupported_size_before_driver() -> None:
    capabilities = load_packaged_chip_capabilities("et6801")

    with pytest.raises(UnsupportedCapability, match="exceeds"):
        require_dma_transfer_done_capabilities(
            capabilities,
            instance_id=0,
            channel=0,
            transfer_count=4096,
        )


def test_dma_transfer_done_contract_rejects_missing_profile_before_driver() -> None:
    with pytest.raises(UnsupportedCapability, match="not described"):
        require_dma_transfer_done_capabilities(
            _MissingDmaCapabilities(),  # type: ignore[arg-type]
            instance_id=0,
            channel=0,
            transfer_count=64,
        )


@pytest.mark.parametrize(
    ("capabilities", "message"),
    [
        (
            DmaCapabilities(DmaFeature.INTERRUPTS, 8, 4095, 0, 0, DmaIrqEvent.TRANSFER_DONE),
            "memory_to_memory",
        ),
        (
            DmaCapabilities(DmaFeature.MEMORY_TO_MEMORY, 8, 4095, 0, 0, DmaIrqEvent.TRANSFER_DONE),
            "does not support interrupts",
        ),
        (
            DmaCapabilities(
                DmaFeature.MEMORY_TO_MEMORY | DmaFeature.INTERRUPTS,
                0,
                4095,
                0,
                0,
                DmaIrqEvent.TRANSFER_DONE,
            ),
            "channel 0",
        ),
        (
            DmaCapabilities(
                DmaFeature.MEMORY_TO_MEMORY | DmaFeature.INTERRUPTS,
                8,
                32,
                0,
                0,
                DmaIrqEvent.TRANSFER_DONE,
            ),
            "limit 32",
        ),
        (
            DmaCapabilities(
                DmaFeature.MEMORY_TO_MEMORY | DmaFeature.INTERRUPTS,
                8,
                4095,
                0,
                0,
                DmaIrqEvent.ERROR,
            ),
            "TRANSFER_DONE",
        ),
    ],
)
def test_dma_runtime_transfer_done_contract_rejects_missing_capability(
    capabilities: DmaCapabilities,
    message: str,
) -> None:
    with pytest.raises(UnsupportedCapability, match=message):
        require_dma_transfer_done_firmware_capabilities(
            capabilities,
            channel=0,
            transfer_count=64,
        )
