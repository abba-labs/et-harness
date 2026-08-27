# Framework Validation测试模块。
#
# 职责：验证test_dma_p1_memory_case 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import inspect
import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from et_test_platform.drivers.dma import (
    DmaChannelStatus,
    DmaConfig,
    DmaIrqEvent,
    DmaIrqResult,
)
from et_test_platform.drivers.resource import ResourceRef
from et_test_platform.profiles.capabilities import load_packaged_chip_capabilities
from et_test_platform.test_cases.dma import test_dma_p1 as p1_cases

_BASE_ADDRESS = 0x20400000


class _Resource:
    def __init__(self) -> None:
        self._next = 1
        self._data: dict[int, bytearray] = {}
        self.refs: list[ResourceRef] = []
        self.created_refs: list[ResourceRef] = []
        self.reset_count = 0

    def reset(self) -> None:
        self.reset_count += 1
        self._data.clear()
        self.refs.clear()

    @contextmanager
    def pool_mode(self) -> Iterator[None]:
        self.reset()
        try:
            yield
        finally:
            self.reset()

    def create(self, size: int, alignment: int = 4) -> ResourceRef:
        del alignment
        handle = self._next
        self._next += 1
        ref = ResourceRef(handle, size, _BASE_ADDRESS + handle * 0x1000)
        self._data[handle] = bytearray(size)
        self.refs.append(ref)
        self.created_refs.append(ref)
        return ref

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


class _Dma:
    def __init__(self, resource: _Resource) -> None:
        self.resource = resource
        self.instance_id = 0
        self.config: DmaConfig | None = None
        self.controller_enabled = False
        self.irq_enabled = False
        self.irq_events = DmaIrqEvent(0)
        self.irq_result = DmaIrqResult(DmaIrqEvent(0), 0, 0, 0)
        self.cleanup_calls: list[str] = []

    def controller_enable(self) -> None:
        self.controller_enabled = True

    def controller_disable(self) -> None:
        self.cleanup_calls.append("controller_disable")
        self.controller_enabled = False

    @contextmanager
    def controller_mode(self) -> Iterator[None]:
        self.controller_enable()
        try:
            yield
        finally:
            self.controller_disable()

    def configure(self, config: DmaConfig) -> None:
        self.config = config

    def deconfigure(self, channel: int) -> None:
        del channel
        self.cleanup_calls.append("deconfigure")
        self.config = None

    @contextmanager
    def configured_channel(self, config: DmaConfig) -> Iterator[None]:
        self.configure(config)
        try:
            yield
        finally:
            self.stop(config.channel)
            self.deconfigure(config.channel)

    def irq_enable(
        self,
        channel: int,
        events: DmaIrqEvent,
        priority: int,
    ) -> int:
        del channel, priority
        self.irq_events = events
        self.irq_enabled = True
        return 1

    def irq_disable(self, events: DmaIrqEvent) -> None:
        del events
        self.cleanup_calls.append("irq_disable")
        self.irq_enabled = False

    def irq_result_clear(self) -> None:
        self.irq_result = DmaIrqResult(DmaIrqEvent(0), 0, 0, 0)

    def wait_irq_count(
        self,
        *,
        minimum_count: int,
        timeout_s: float,
        poll_interval_s: float = 0.001,
    ) -> DmaIrqResult:
        del timeout_s, poll_interval_s
        if self.irq_result.irq_count < minimum_count:
            raise TimeoutError("fake DMA IRQ count did not reach minimum")
        return self.irq_result

    def start(self, channel: int) -> None:
        del channel
        assert self.config is not None
        source_handle = (self.config.source_address - _BASE_ADDRESS) // 0x1000
        destination_handle = (self.config.destination_address - _BASE_ADDRESS) // 0x1000
        source_ref = next(item for item in self.resource.refs if item.handle == source_handle)
        destination_ref = next(
            item for item in self.resource.refs if item.handle == destination_handle
        )
        source_offset = self.config.source_address - source_ref.address
        destination_offset = self.config.destination_address - destination_ref.address
        self.resource._data[destination_handle][
            destination_offset : destination_offset + self.config.transfer_count
        ] = self.resource._data[source_handle][
            source_offset : source_offset + self.config.transfer_count
        ]
        self.irq_result = DmaIrqResult(self.irq_events, 1, 0, 0)

    def stop(self, channel: int) -> None:
        del channel
        self.cleanup_calls.append("stop")

    def channel_status(self, channel: int) -> DmaChannelStatus:
        del channel
        return DmaChannelStatus(True, True, self.irq_result.latched_events)

    def wait_channel_free(
        self,
        channel: int,
        *,
        timeout_s: float = 1.0,
        poll_interval_s: float = 0.001,
    ) -> DmaChannelStatus:
        del timeout_s, poll_interval_s
        status = self.channel_status(channel)
        if status.interrupt_events & DmaIrqEvent.ERROR:
            raise RuntimeError(f"fake DMA channel {channel} terminated with ERROR")
        if not status.is_free:
            raise TimeoutError(f"fake DMA channel {channel} did not become free")
        return status


class _Crg:
    def __init__(self) -> None:
        self.reset_calls: list[tuple[object, int]] = []

    def reset(self, peripheral: object, *, instance: int) -> None:
        self.reset_calls.append((peripheral, instance))


def test_dma_p1_016_safe_sram_matrix_uses_managed_support(
    tmp_path: Path,
) -> None:
    resource = _Resource()
    dma = _Dma(resource)
    crg = _Crg()
    parameters = inspect.signature(p1_cases.test_dma_p1_016_memory_region_matrix).parameters
    assert {"dma_support_for", "target_capabilities", "et_artifact_dir", "instance_id"} <= set(
        parameters
    )

    def support_factory(instance_id: int) -> SimpleNamespace:
        return SimpleNamespace(
            controller=instance_id,
            resource=resource,
            dma=dma,
        )

    try:
        p1_cases.test_dma_p1_016_memory_region_matrix(
            dma_support_for=support_factory,
            target_capabilities=load_packaged_chip_capabilities("et6801"),
            et_artifact_dir=tmp_path,
            instance_id=0,
            record_property=lambda name, value: None,
            crg_driver=crg,
            resource_driver=resource,
        )
    except pytest.skip.Exception as exc:
        pytest.fail(f"P1-012 remains statically skipped: {exc}")

    assert resource.refs == []
    assert len(resource.created_refs) == 2
    assert resource.created_refs[0].address != resource.created_refs[1].address
    assert len(crg.reset_calls) == 1
    assert resource.reset_count == 3
    assert dma.irq_result.latched_events & DmaIrqEvent.TRANSFER_DONE
    assert dma.irq_result.unexpected_count == 0
    assert dma.irq_result.overflow_count == 0
    assert dma.cleanup_calls == [
        "irq_disable",
        "stop",
        "deconfigure",
        "controller_disable",
    ]

    artifacts = list(tmp_path.glob("dma_p1_016*.json"))
    assert len(artifacts) == 1
    payload = json.loads(artifacts[0].read_text(encoding="utf-8"))
    assert "status" not in payload
    assert payload["measurement_schema"] == "et.measurement.v1"
    assert payload["data_match"] is True
