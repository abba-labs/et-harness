# DMA P1 Formal Case。
#
# 职责：验证 DMA 并发、分类IRQ、Reload、Gather/Scatter、FIFO、LLI写回和M2M配置矩阵。
# 边界：只通过稳定 Driver API 操作设备，不直接访问寄存器、Codec或Transport。
# 依赖：仅依赖 DMA Case Fixture、本地纯数据Helper、Resource Driver和Canonical Evidence接口。

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction
from ...core.errors import CapabilityLookupError, TargetRejected, UnsupportedCapability
from ...drivers.crg import CrgPeripheral
from ...drivers.dma import (
    DmaAddressMode,
    DmaBurst,
    DmaConfig,
    DmaFeature,
    DmaFifoMode,
    DmaIrqEvent,
    DmaUpdateMode,
    DmaWidth,
)
from ...profiles.capabilities import ChipCapabilities
from ...results.recorder import write_json_result
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import (
    DmaSupportFactory,
    require_dma_control_writeback_capability,
    require_dma_m2m_capability,
    require_dma_transfer_done_capabilities,
    require_dma_transfer_done_firmware_capabilities,
)
from .dma_helpers import (
    DMA_CONFIG_DESTINATION_SCATTER,
    DMA_CONFIG_INITIAL_DONE,
    DMA_CONFIG_SOURCE_GATHER,
    DMA_DESTINATION_FILL,
    DMA_GUARD_SIZE,
    DMA_GUARD_VALUE,
    build_dma_m2m_vector,
    dma_m2m_measurement,
)

pytestmark = [pytest.mark.hardware, pytest.mark.ip("dma")]


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# =============================================================================
# 多通道并发
# =============================================================================


# 测试 Feature：
# DMA 全部可用 Channel 的一次原子并发启动和独立数据一致性。
#
# 测试方法：
# 1. 为运行时全部 Channel 准备独立 64 Byte Source/Destination 并逐通道配置。
# 2. 一次 CHANNELS_START 启动完整 Mask，逐通道等待 Free 后读取目标数据和终态。
# 3. 在最终断言前保存完整 Mask、逐通道实际数据和 Free 事实。
#
# 通过条件：
# 1. Runtime 全部 Channel 均进入同一原子启动 Mask。
# 2. 每个 Channel 的目标数据与各自源数据完全一致且无串扰。
# 3. 全部 Channel 最终 Free。
def test_dma_p1_001_all_channels_concurrent(
    dma_support_for: DmaSupportFactory,
    target_capabilities: ChipCapabilities,
    et_artifact_dir: Path,
    instance_id: int,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 按Contract顺序执行本Case，并在决定性断言前保存关键硬件事实。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=instance_id)
    resource_driver.reset()

    support = dma_support_for(instance_id)
    resource = support.resource
    dma = support.dma
    dynamic = dma.capabilities_get()
    resource_pool_owned = False
    controller_enabled = False
    configured_channels: list[int] = []

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        # 遍历本Case声明的参数或资源集合，逐项形成可追溯硬件证据。
        for configured_channel in reversed(configured_channels):
            actions.append(
                (
                    f"DMA channel {configured_channel} stop",
                    lambda configured_channel=configured_channel: dma.stop(configured_channel),
                )
            )
            actions.append(
                (
                    f"DMA channel {configured_channel} deconfigure",
                    lambda configured_channel=configured_channel: dma.deconfigure(
                        configured_channel
                    ),
                )
            )
        if controller_enabled:
            actions.append(("DMA controller disable", dma.controller_disable))
        if resource_pool_owned:
            actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        resource.reset()
        resource_pool_owned = True
        sources = []
        destinations = []
        expected = []
        # 遍历本Case声明的参数或资源集合，逐项形成可追溯硬件证据。
        for channel in range(dynamic.channel_count):
            require_dma_m2m_capability(
                target_capabilities,
                instance_id=instance_id,
                channel=channel,
                transfer_count=64,
            )
            data = bytes((channel * 37 + index * 11) & 0xFF for index in range(64))
            source = resource.create(64)
            destination = resource.create(64)
            resource.write(source, data)
            resource.fill(destination, 0xA5)
            sources.append(source)
            destinations.append(destination)
            expected.append(data)

        dma.controller_enable()
        controller_enabled = True
        # 遍历本Case声明的参数或资源集合，逐项形成可追溯硬件证据。
        for channel in range(dynamic.channel_count):
            dma.configure(
                DmaConfig(
                    channel=channel,
                    source_address=sources[channel].address,
                    destination_address=destinations[channel].address,
                    transfer_count=64,
                    priority=channel,
                )
            )
            configured_channels.append(channel)

        channel_mask = (1 << dynamic.channel_count) - 1
        dma.start_channels(channel_mask)
        # 遍历本Case声明的参数或资源集合，逐项形成可追溯硬件证据。
        for channel in range(dynamic.channel_count):
            dma.wait_channel_free(channel)
        actual = [resource.read(item) for item in destinations]
        statuses = [dma.channel_status(channel) for channel in range(dynamic.channel_count)]

        record_property("expected_channel_mask", channel_mask)
        record_property("actual_channel_mask", channel_mask)
        record_property("channel_mask", channel_mask)
        record_property("channel_count", dynamic.channel_count)
        all_data_match = actual == expected
        all_channels_free = all(status.is_free for status in statuses)
        record_property("all_data_match", all_data_match)
        record_property("all_channels_free", all_channels_free)
        # 遍历本Case声明的参数或资源集合，逐项形成可追溯硬件证据。
        for channel, value in enumerate(actual):
            record_observation(
                record_property,
                key="channel_actual_data",
                value=value,
                source="dut",
                endpoint=f"DMA_DESTINATION_DATA.CHANNEL_{channel}",
            )
            record_observation(
                record_property,
                key="channel_free",
                value=statuses[channel].is_free,
                source="dut",
                endpoint="DMA_CHANNEL_STATUS.FREE",
            )

        write_json_result(
            et_artifact_dir / f"dma_p1_001_all_channels_concurrent_dma{instance_id}.json",
            {
                "measurement_schema": "et.measurement.v1",
                "controller": instance_id,
                "channel_mask": channel_mask,
                "channels": dynamic.channel_count,
                "bytes_per_channel": 64,
                "expected_sha256": [_digest(item) for item in expected],
                "actual_sha256": [_digest(item) for item in actual],
                "all_data_match": all_data_match,
                "all_channels_free": all_channels_free,
            },
        )

        assert dynamic.channel_count > 0
        assert all_data_match
        assert all_channels_free


# =============================================================================
# 基础中断
# =============================================================================


# 测试 Feature：
# DMA 代表 Channel 的 TRANSFER_DONE 中断、数据完成和终态一致性。
#
# 测试方法：
# 1. 配置 32 Byte M2M 和 TRANSFER_DONE，清除旧 IRQ Result 后启动。
# 2. 等待真实 IRQ 与 Channel Free，读取目标数据和 Service ISR 事实。
# 3. 在断言前记录 ISR Latch、Event Count、实际数据和 Free 状态。
#
# 通过条件：
# 1. 目标数据逐字节等于源数据。
# 2. TRANSFER_DONE 被锁存、Event Count>=1，Unexpected/Overflow=0。
# 3. Channel 最终 Free。
def test_dma_p1_004_transfer_complete_irq(
    dma_support_for: DmaSupportFactory,
    target_capabilities: ChipCapabilities,
    et_artifact_dir: Path,
    instance_id: int,
    channel: int,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 按Contract顺序执行本Case，并在决定性断言前保存关键硬件事实。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=instance_id)
    resource_driver.reset()

    support = dma_support_for(instance_id)
    resource = support.resource
    dma = support.dma
    size = 32
    events = DmaIrqEvent.TRANSFER_DONE
    try:
        require_dma_transfer_done_capabilities(
            target_capabilities,
            instance_id=instance_id,
            channel=channel,
            transfer_count=size,
        )
        firmware_capabilities = dma.capabilities_get()
        require_dma_transfer_done_firmware_capabilities(
            firmware_capabilities,
            channel=channel,
            transfer_count=size,
        )
    except UnsupportedCapability as exc:
        pytest.skip(str(exc))
    source_data = bytes((index * 29 + 7) & 0xFF for index in range(size))
    controller_enabled = False
    configured = False
    irq_enabled = False
    irq = None

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if irq_enabled:
            actions.append(("DMA IRQ disable", lambda: dma.irq_disable(events)))
        if configured:
            actions.append(("DMA channel stop", lambda: dma.stop(channel)))
            actions.append(("DMA channel deconfigure", lambda: dma.deconfigure(channel)))
        if controller_enabled:
            actions.append(("DMA controller disable", dma.controller_disable))
        actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        resource.reset()
        source = resource.create(size, alignment=4)
        destination = resource.create(size, alignment=4)
        resource.write(source, source_data)
        resource.fill(destination, 0xA5)
        dma.controller_enable()
        controller_enabled = True
        dma.configure(
            DmaConfig(
                channel=channel,
                source_address=source.address,
                destination_address=destination.address,
                transfer_count=size,
            )
        )
        configured = True
        route_count = dma.irq_enable(channel, events, priority=3)
        irq_enabled = True
        dma.irq_result_clear()
        dma.start(channel)
        irq = dma.wait_irq_count(minimum_count=1, timeout_s=1.0)
        dma.wait_channel_free(channel, timeout_s=2.0)
        destination_data = resource.read(destination)
        status = dma.channel_status(channel)

        record_property("expected_irq_event", int(events))
        record_property("irq_event_count", irq.irq_count)
        record_property("data_match", destination_data == source_data)
        record_observation(
            record_property,
            key="isr_latched_transfer_done",
            value=bool(irq.latched_events & events),
            source="dut",
            endpoint="ISR.LATCHED.TRANSFER_DONE",
        )
        record_observation(
            record_property,
            key="actual_data",
            value=destination_data,
            source="dut",
            endpoint="DMA_DESTINATION_DATA",
        )
        record_observation(
            record_property,
            key="channel_free",
            value=status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FREE",
        )

        write_json_result(
            et_artifact_dir / f"dma_p1_004_transfer_complete_irq_dma{instance_id}_ch{channel}.json",
            {
                "measurement_schema": "et.measurement.v1",
                "controller": instance_id,
                "channel": channel,
                "transfer_bytes": size,
                "route_count": route_count,
                "irq_event_count": irq.irq_count,
                "latched_events": int(irq.latched_events),
                "unexpected_count": irq.unexpected_count,
                "overflow_count": irq.overflow_count,
                "expected_sha256": _digest(source_data),
                "actual_sha256": _digest(destination_data),
                "data_match": destination_data == source_data,
                "channel_free": status.is_free,
            },
        )

        assert destination_data == source_data
        assert irq.latched_events & events == events
        assert irq.irq_count >= 1
        assert irq.unexpected_count == 0
        assert irq.overflow_count == 0
        assert status.is_free

    assert irq is not None


# 测试 Feature：
# 单节点 LLI 传输完成时的 BLOCK_DONE 中断和边界 Channel 行为。
#
# 测试方法：
# 1. 在运行时首/末 Channel 上建立单节点 Descriptor 并启用 BLOCK_DONE。
# 2. 启动 LLI，等待 Free 后读取目标数据、IRQ Result 和终态。
# 3. 在强断言前保存边界 Channel、ISR Latch、Event Count、数据和 Free。
#
# 通过条件：
# 1. 首/末两个边界 Channel 均执行且目标数据正确。
# 2. BLOCK_DONE 精确锁存、Event Count=1，Unexpected/Overflow=0。
# 3. Channel 最终 Free。
def test_dma_p1_005_block_complete_irq(
    dma_support_for: DmaSupportFactory,
    et_artifact_dir: Path,
    instance_id: int,
    dma_boundary_channel: int,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 按Contract顺序执行本Case，并在决定性断言前保存关键硬件事实。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=instance_id)
    resource_driver.reset()

    channel = dma_boundary_channel
    support = dma_support_for(instance_id)
    resource = support.resource
    dma = support.dma
    source_data = bytes((index * 19 + 11) & 0xFF for index in range(64))
    events = DmaIrqEvent.BLOCK_DONE
    controller_enabled = False
    configured = False
    irq_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if irq_enabled:
            actions.append(("DMA IRQ disable", lambda: dma.irq_disable(events)))
        if configured:
            actions.append(("DMA channel stop", lambda: dma.stop(channel)))
            actions.append(("DMA channel deconfigure", lambda: dma.deconfigure(channel)))
        if controller_enabled:
            actions.append(("DMA controller disable", dma.controller_disable))
        actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        resource.reset()
        source = resource.create(len(source_data))
        destination = resource.create(len(source_data))
        descriptor = resource.create(28, alignment=4)
        resource.write(source, source_data)
        resource.fill(destination, 0xA5)
        descriptor_config = DmaConfig(
            channel=channel,
            source_address=source.address,
            destination_address=destination.address,
            transfer_count=len(source_data),
            source_update_mode=DmaUpdateMode.LINKED_LIST,
            destination_update_mode=DmaUpdateMode.LINKED_LIST,
        )
        dma.lli_descriptor_init_v2(descriptor.address, descriptor_config, is_last=True)
        dma.controller_enable()
        controller_enabled = True
        dma.configure(
            DmaConfig(
                channel=channel,
                source_address=source.address,
                destination_address=destination.address,
                transfer_count=len(source_data),
                source_update_mode=DmaUpdateMode.LINKED_LIST,
                destination_update_mode=DmaUpdateMode.LINKED_LIST,
                linked_list_address=descriptor.address,
            )
        )
        configured = True
        route_count = dma.irq_enable(channel, events, priority=4)
        irq_enabled = True
        dma.irq_result_clear()
        dma.start(channel)
        dma.wait_channel_free(channel)
        result = dma.irq_result_get()
        actual = resource.read(destination)
        status = dma.channel_status(channel)

        record_property("expected_irq_event", int(events))
        record_property("boundary_channel", channel)
        record_property("irq_event_count", result.irq_count)
        record_property("data_match", actual == source_data)
        record_observation(
            record_property,
            key="isr_latched_block_done",
            value=bool(result.latched_events & events),
            source="dut",
            endpoint="ISR.LATCHED.BLOCK_DONE",
        )
        record_observation(
            record_property,
            key="actual_data",
            value=actual,
            source="dut",
            endpoint="DMA_DESTINATION_DATA",
        )
        record_observation(
            record_property,
            key="channel_free",
            value=status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FREE",
        )

        write_json_result(
            et_artifact_dir / f"dma_p1_005_block_irq_dma{instance_id}_ch{channel}.json",
            {
                "measurement_schema": "et.measurement.v1",
                "controller": instance_id,
                "channel": channel,
                "route_count": route_count,
                "irq_event_count": result.irq_count,
                "latched_events": int(result.latched_events),
                "data_match": actual == source_data,
                "channel_free": status.is_free,
            },
        )

        assert actual == source_data
        assert result.latched_events == events
        assert result.irq_count == 1
        assert result.unexpected_count == 0
        assert result.overflow_count == 0
        assert status.is_free


# 测试 Feature：
# DMA TRANSFER_DONE 的 RAW/STATUS/MASK/CLEAR 状态机。
#
# 测试方法：
# 1. 关闭 Mask、清 Pending 后读取 before；在 Mask 关闭时完成传输并读取 masked。
# 2. Clear Pending 后读取 cleared，再 Enable Mask 读取 enabled。
# 3. 四阶段硬件位与数据在断言前全部进入 Canonical Evidence。
#
# 通过条件：
# 1. before RAW/STATUS/MASK 均为0。
# 2. masked RAW=1、STATUS=0、MASK=0；Clear 后 RAW/STATUS=0。
# 3. Enable 后 MASK=1，数据正确且 Channel Free。
def test_dma_p1_006_interrupt_mask_raw_clear(
    dma_support_for: DmaSupportFactory,
    et_artifact_dir: Path,
    instance_id: int,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 按Contract顺序执行本Case，并在决定性断言前保存关键硬件事实。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=instance_id)
    resource_driver.reset()

    support = dma_support_for(instance_id)
    resource = support.resource
    dma = support.dma
    channel = 0
    channel_bit = 1 << channel
    events = DmaIrqEvent.TRANSFER_DONE
    source_data = bytes((index * 29 + 7) & 0xFF for index in range(64))
    controller_enabled = False
    configured = False
    irq_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if irq_enabled:
            actions.append(
                ("DMA interrupt mask disable", lambda: dma.interrupt_mask_disable(channel, events))
            )
            actions.append(("DMA IRQ disable", lambda: dma.irq_disable(events)))
        if configured:
            actions.append(("DMA channel stop", lambda: dma.stop(channel)))
            actions.append(("DMA channel deconfigure", lambda: dma.deconfigure(channel)))
        if controller_enabled:
            actions.append(("DMA controller disable", dma.controller_disable))
        actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        resource.reset()
        source = resource.create(len(source_data))
        destination = resource.create(len(source_data))
        resource.write(source, source_data)
        resource.fill(destination, 0xA5)
        dma.controller_enable()
        controller_enabled = True
        dma.configure(
            DmaConfig(
                channel=channel,
                source_address=source.address,
                destination_address=destination.address,
                transfer_count=len(source_data),
            )
        )
        configured = True
        route_count = dma.irq_enable(channel, events, priority=4)
        irq_enabled = True
        dma.interrupt_mask_disable(channel, events)
        dma.interrupt_pending_clear(channel, events)
        before = dma.interrupt_snapshot_get()

        dma.start(channel)
        dma.wait_channel_free(channel)
        masked = dma.interrupt_snapshot_get()
        actual = resource.read(destination)

        dma.interrupt_pending_clear(channel, events)
        cleared = dma.interrupt_snapshot_get()
        dma.interrupt_mask_enable(channel, events)
        enabled = dma.interrupt_snapshot_get()
        status = dma.channel_status(channel)

        record_observation(
            record_property,
            key="masked_raw",
            value=masked.raw[0],
            source="dut",
            endpoint="IRQ_RAW.TRANSFER_DONE",
        )
        record_observation(
            record_property,
            key="masked_status",
            value=masked.status[0],
            source="dut",
            endpoint="IRQ_STATUS.TRANSFER_DONE",
        )
        record_observation(
            record_property,
            key="cleared_raw",
            value=cleared.raw[0],
            source="dut",
            endpoint="IRQ_RAW.TRANSFER_DONE",
        )
        record_observation(
            record_property,
            key="enabled_mask",
            value=enabled.mask[0],
            source="dut",
            endpoint="IRQ_MASK.TRANSFER_DONE",
        )
        record_property("data_match", actual == source_data)
        record_observation(
            record_property,
            key="channel_free",
            value=status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FREE",
        )

        write_json_result(
            et_artifact_dir / f"dma_p1_006_interrupt_mask_raw_clear_dma{instance_id}.json",
            {
                "measurement_schema": "et.measurement.v1",
                "controller": instance_id,
                "channel": channel,
                "route_count": route_count,
                "data_match": actual == source_data,
                "before": {
                    "raw": list(before.raw),
                    "status": list(before.status),
                    "mask": list(before.mask),
                    "combined_status": before.combined_status,
                },
                "masked": {
                    "raw": list(masked.raw),
                    "status": list(masked.status),
                    "mask": list(masked.mask),
                    "combined_status": masked.combined_status,
                },
                "cleared": {
                    "raw": list(cleared.raw),
                    "status": list(cleared.status),
                    "mask": list(cleared.mask),
                    "combined_status": cleared.combined_status,
                },
                "enabled": {
                    "raw": list(enabled.raw),
                    "status": list(enabled.status),
                    "mask": list(enabled.mask),
                    "combined_status": enabled.combined_status,
                },
            },
        )

        assert before.raw[0] & channel_bit == 0
        assert before.status[0] & channel_bit == 0
        assert before.mask[0] & channel_bit == 0
        assert actual == source_data
        assert masked.raw[0] & channel_bit
        assert masked.status[0] & channel_bit == 0
        assert masked.mask[0] & channel_bit == 0
        assert cleared.raw[0] & channel_bit == 0
        assert cleared.status[0] & channel_bit == 0
        assert enabled.mask[0] & channel_bit
        assert status.is_free


# =============================================================================
# 地址 Reload 与 BLOCK_DONE
# =============================================================================


# 测试 Feature：
# Source、Destination 和双端 Reload 的连续 Block 行为及 BLOCK_DONE。
#
# 测试方法：
# 1. 参数化 source/destination/both，使用 Runtime Max Transfer Count 建立持续 Reload。
# 2. 等待至少两次 BLOCK_DONE 后 Stop，读取地址 Snapshot、数据和 IRQ Result。
# 3. 记录实际 Source/Destination 地址和 Event Count 后按模式进行强断言。
#
# 通过条件：
# 1. 三种 Reload 模式的地址约束和数据均符合定义。
# 2. BLOCK_DONE Event Count>=2，Unexpected/Overflow=0。
@pytest.mark.parametrize("reload_mode", ["source", "destination", "both"])
def test_dma_p1_007_reload_modes(
    dma_support_for: DmaSupportFactory,
    target_capabilities: ChipCapabilities,
    et_artifact_dir: Path,
    instance_id: int,
    reload_mode: str,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 按Contract顺序执行本Case，并在决定性断言前保存关键硬件事实。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=instance_id)
    resource_driver.reset()

    support = dma_support_for(instance_id)
    resource = support.resource
    dma = support.dma
    instance = target_capabilities.instances("dma")[instance_id]
    try:
        source_options = target_capabilities.options("dma", "reload_source", instance=instance)
        destination_options = target_capabilities.options(
            "dma", "reload_destination", instance=instance
        )
    except CapabilityLookupError as exc:
        pytest.skip(f"skip_by_capability: {exc}")
    if "enable" not in source_options or "enable" not in destination_options:
        pytest.skip(f"skip_by_capability: {instance} reload")
    dynamic = dma.capabilities_get()
    events = DmaIrqEvent.BLOCK_DONE
    if not dynamic.features & DmaFeature.RELOAD:
        pytest.skip("skip_by_runtime_feature: DMA reload unavailable")
    if not dynamic.irq_events & events:
        pytest.skip("skip_by_runtime_feature: DMA BLOCK_DONE unavailable")

    size = dynamic.max_transfer_count
    source_reload = reload_mode in {"source", "both"}
    destination_reload = reload_mode in {"destination", "both"}
    if reload_mode == "source":
        source_data, source_size, destination_size = b"\x3c" * size, size, 1
    elif reload_mode == "destination":
        source_data, source_size, destination_size = b"\x3c", 1, size
    else:
        source_data = bytes((index * 17 + 9) & 0xFF for index in range(size))
        source_size = destination_size = size

    controller_enabled = False
    configured = False
    irq_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if irq_enabled:
            actions.append(("DMA BLOCK_DONE IRQ disable", lambda: dma.irq_disable(events)))
        if configured:
            actions.append(("DMA channel stop", lambda: dma.stop(0)))
            actions.append(("DMA channel deconfigure", lambda: dma.deconfigure(0)))
        if controller_enabled:
            actions.append(("DMA controller disable", dma.controller_disable))
        actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        require_dma_m2m_capability(
            target_capabilities,
            instance_id=instance_id,
            channel=0,
            transfer_count=size,
        )
        resource.reset()
        source = resource.create(source_size, alignment=4)
        destination = resource.create(destination_size, alignment=4)
        resource.write(source, source_data)
        resource.fill(destination, 0xA5)
        dma.controller_enable()
        controller_enabled = True
        dma.configure(
            DmaConfig(
                channel=0,
                source_address=source.address,
                destination_address=destination.address,
                transfer_count=size,
                source_address_mode=(
                    DmaAddressMode.FIXED
                    if reload_mode == "destination"
                    else DmaAddressMode.INCREMENT
                ),
                destination_address_mode=(
                    DmaAddressMode.FIXED if reload_mode == "source" else DmaAddressMode.INCREMENT
                ),
                source_update_mode=(
                    DmaUpdateMode.RELOAD if source_reload else DmaUpdateMode.CONTIGUOUS
                ),
                destination_update_mode=(
                    DmaUpdateMode.RELOAD if destination_reload else DmaUpdateMode.CONTIGUOUS
                ),
            )
        )
        configured = True
        route_count = dma.irq_enable(0, events, priority=4)
        irq_enabled = True
        dma.irq_result_clear()
        dma.start(0)
        result = dma.wait_irq_count(minimum_count=2, timeout_s=2.0)
        dma.stop(0)
        snapshot = dma.channel_snapshot_get(0)

        if reload_mode == "source":
            data_match = resource.read(destination, 1) == b"\x3c"
            address_match = (
                source.address <= snapshot.source_address <= source.address + size
                and snapshot.destination_address == destination.address
            )
        elif reload_mode == "destination":
            data_match = resource.read(destination) == b"\x3c" * size
            address_match = (
                snapshot.source_address == source.address
                and destination.address
                <= snapshot.destination_address
                <= destination.address + size
            )
        else:
            data_match = resource.read(destination) == source_data
            address_match = (
                source.address <= snapshot.source_address <= source.address + size
                and destination.address
                <= snapshot.destination_address
                <= destination.address + size
            )

        record_property("reload_mode", reload_mode)
        record_property("block_event_count", result.irq_count)
        record_property("data_match", data_match)
        record_observation(
            record_property,
            key="source_address",
            value=snapshot.source_address,
            source="dut",
            endpoint="DMA_CHANNEL.SOURCE_ADDRESS",
        )
        record_observation(
            record_property,
            key="destination_address",
            value=snapshot.destination_address,
            source="dut",
            endpoint="DMA_CHANNEL.DESTINATION_ADDRESS",
        )
        record_observation(
            record_property,
            key="isr_latched_block_done",
            value=bool(result.latched_events & events),
            source="dut",
            endpoint="ISR.LATCHED.BLOCK_DONE",
        )

        write_json_result(
            et_artifact_dir / f"dma_p1_007_reload_{reload_mode}_dma{instance_id}.json",
            {
                "measurement_schema": "et.measurement.v1",
                "controller": instance_id,
                "reload_mode": reload_mode,
                "transfer_count": size,
                "route_count": route_count,
                "block_event_count": result.irq_count,
                "latched_events": int(result.latched_events),
                "unexpected_count": result.unexpected_count,
                "overflow_count": result.overflow_count,
                "source_address": snapshot.source_address,
                "destination_address": snapshot.destination_address,
                "data_match": data_match,
                "address_match": address_match,
            },
        )

        assert size > 0
        assert address_match
        assert data_match
        assert result.latched_events & events
        assert result.irq_count >= 2
        assert result.unexpected_count == 0
        assert result.overflow_count == 0


# =============================================================================
# Gather / Scatter
# =============================================================================


# 测试 Feature：
# DMA Source Gather 的 Interval/Count 及 Gather 后目标布局。
#
# 测试方法：
# 1. 构造三组“10 Byte有效数据+5 Byte间隔”的 Source 和带 Guard Destination。
# 2. 配置 Gather Count=10/Interval=5，Start/Wait 后读取完整 Destination。
# 3. 记录实际目标数据、Guard 和 Channel Free 后再比较 Expected。
#
# 通过条件：
# 1. 三组有效数据连续拼接且逐字节匹配。
# 2. Guard 完整且 Channel Free。
def test_dma_p1_008_source_gather(
    dma_support_for: DmaSupportFactory,
    target_capabilities: ChipCapabilities,
    et_artifact_dir: Path,
    instance_id: int,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 按Contract顺序执行本Case，并在决定性断言前保存关键硬件事实。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=instance_id)
    resource_driver.reset()

    support = dma_support_for(instance_id)
    resource = support.resource
    dma = support.dma
    instance = target_capabilities.instances("dma")[instance_id]
    if not target_capabilities.has_feature("dma", "source_gather", instance=instance):
        pytest.skip(f"skip_by_capability: {instance} source_gather")
    if not dma.capabilities_get().features & DmaFeature.SOURCE_GATHER:
        pytest.skip("skip_by_runtime_feature: source_gather unavailable")
    source_data = b"1234567890xxxxx" * 3
    expected = b"1234567890" * 3
    resource_pool_owned = False
    controller_enabled = False
    channel_configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if channel_configured:
            actions.append(("DMA channel stop", lambda: dma.stop(0)))
            actions.append(("DMA channel deconfigure", lambda: dma.deconfigure(0)))
        if controller_enabled:
            actions.append(("DMA controller disable", dma.controller_disable))
        if resource_pool_owned:
            actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        resource.reset()
        resource_pool_owned = True
        source = resource.create(len(source_data))
        destination = resource.create(len(expected) + 16)
        resource.write(source, source_data)
        resource.fill(destination, 0xA5)
        dma.controller_enable()
        controller_enabled = True
        dma.configure(
            DmaConfig(
                channel=0,
                source_address=source.address,
                destination_address=destination.address + 8,
                transfer_count=len(expected),
                flags=DMA_CONFIG_SOURCE_GATHER,
                source_gather_interval=5,
                source_gather_count=10,
            )
        )
        channel_configured = True
        dma.start(0)
        dma.wait_channel_free(0)
        actual = resource.read(destination)
        status = dma.channel_status(0)
        actual_data = actual[8 : 8 + len(expected)]
        guards_intact = actual[:8] == b"\xa5" * 8 and actual[-8:] == b"\xa5" * 8

        record_property("gather_count", 10)
        record_property("gather_interval", 5)
        record_property("expected_data", expected)
        record_property("guards_intact", guards_intact)
        record_observation(
            record_property,
            key="actual_data",
            value=actual_data,
            source="dut",
            endpoint="DMA_DESTINATION_DATA",
        )
        record_observation(
            record_property,
            key="channel_free",
            value=status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FREE",
        )

        write_json_result(
            et_artifact_dir / f"dma_p1_008_source_gather_dma{instance_id}.json",
            {
                "measurement_schema": "et.measurement.v1",
                "controller": instance_id,
                "gather_count": 10,
                "gather_interval": 5,
                "groups": 3,
                "expected_sha256": _digest(expected),
                "actual_sha256": _digest(actual_data),
                "data_match": actual_data == expected,
                "guards_intact": guards_intact,
                "channel_free": status.is_free,
            },
        )

        assert actual_data == expected
        assert guards_intact
        assert status.is_free


# 测试 Feature：
# DMA Destination Scatter 的 Interval/Count 及 Scatter 后目标布局。
#
# 测试方法：
# 1. 构造连续30 Byte Source和带Guard/间隔哨兵Destination。
# 2. 配置 Scatter Count=10/Interval=1，Start/Wait后读取完整Destination。
# 3. 保存实际布局、Guard和Free后比较Expected。
#
# 通过条件：
# 1. 目标形成三组10 Byte数据与预期间隔。
# 2. Guard/间隔完整且Channel Free。
def test_dma_p1_009_destination_scatter(
    dma_support_for: DmaSupportFactory,
    target_capabilities: ChipCapabilities,
    et_artifact_dir: Path,
    instance_id: int,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 按Contract顺序执行本Case，并在决定性断言前保存关键硬件事实。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=instance_id)
    resource_driver.reset()

    support = dma_support_for(instance_id)
    resource = support.resource
    dma = support.dma
    instance = target_capabilities.instances("dma")[instance_id]
    if not target_capabilities.has_feature("dma", "destination_scatter", instance=instance):
        pytest.skip(f"skip_by_capability: {instance} destination_scatter")
    if not dma.capabilities_get().features & DmaFeature.DESTINATION_SCATTER:
        pytest.skip("skip_by_runtime_feature: destination_scatter unavailable")
    source_data = b"1234567890" * 3
    expected = b"1234567890\xa5" * 2 + b"1234567890"
    resource_pool_owned = False
    controller_enabled = False
    channel_configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if channel_configured:
            actions.append(("DMA channel stop", lambda: dma.stop(0)))
            actions.append(("DMA channel deconfigure", lambda: dma.deconfigure(0)))
        if controller_enabled:
            actions.append(("DMA controller disable", dma.controller_disable))
        if resource_pool_owned:
            actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        resource.reset()
        resource_pool_owned = True
        source = resource.create(len(source_data))
        destination = resource.create(len(expected) + 16)
        resource.write(source, source_data)
        resource.fill(destination, 0xA5)
        dma.controller_enable()
        controller_enabled = True
        dma.configure(
            DmaConfig(
                channel=0,
                source_address=source.address,
                destination_address=destination.address + 8,
                transfer_count=len(source_data),
                flags=DMA_CONFIG_DESTINATION_SCATTER,
                destination_scatter_interval=1,
                destination_scatter_count=10,
            )
        )
        channel_configured = True
        dma.start(0)
        dma.wait_channel_free(0)
        actual = resource.read(destination)
        status = dma.channel_status(0)
        actual_layout = actual[8 : 8 + len(expected)]
        guards_intact = actual[:8] == b"\xa5" * 8 and actual[-8:] == b"\xa5" * 8

        record_property("scatter_count", 10)
        record_property("scatter_interval", 1)
        record_property("expected_layout", expected)
        record_property("guards_intact", guards_intact)
        record_observation(
            record_property,
            key="actual_layout",
            value=actual_layout,
            source="dut",
            endpoint="DMA_DESTINATION_DATA",
        )
        record_observation(
            record_property,
            key="channel_free",
            value=status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FREE",
        )

        write_json_result(
            et_artifact_dir / f"dma_p1_009_destination_scatter_dma{instance_id}.json",
            {
                "measurement_schema": "et.measurement.v1",
                "controller": instance_id,
                "scatter_count": 10,
                "scatter_interval": 1,
                "groups": 3,
                "expected_sha256": _digest(expected),
                "actual_sha256": _digest(actual_layout),
                "data_match": actual_layout == expected,
                "guards_intact": guards_intact,
                "channel_free": status.is_free,
            },
        )

        assert actual_layout == expected
        assert guards_intact
        assert status.is_free


# =============================================================================
# FIFO Mode
# =============================================================================


# 测试 Feature：
# DMA M2M 的 Single 与 Half-Depth FIFO Mode 配置和数据行为。
#
# 测试方法：
# 1. 参数化 FIFO Mode，配置 257 Byte M2M 与 16-item Burst。
# 2. Configure 后读取 Channel Snapshot 的 FIFO Mode，随后执行传输。
# 3. 保存 Expected/Actual FIFO Mode、实际数据和 Free 后统一断言。
#
# 通过条件：
# 1. SINGLE/HALF_DEPTH 两个参数实例硬件读回均与 Expected 一致。
# 2. 目标数据、Source和Guard正确。
# 3. Channel最终Free。
@pytest.mark.parametrize("fifo_mode", list(DmaFifoMode))
def test_dma_p1_010_fifo_mode(
    dma_support_for: DmaSupportFactory,
    target_capabilities: ChipCapabilities,
    et_artifact_dir: Path,
    instance_id: int,
    fifo_mode: DmaFifoMode,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=instance_id)
    resource_driver.reset()

    support = dma_support_for(instance_id)
    resource = support.resource
    dma = support.dma
    transfer_count = 257
    vector = build_dma_m2m_vector(
        transfer_count,
        DmaWidth.BITS_8,
        DmaAddressMode.INCREMENT,
        DmaAddressMode.INCREMENT,
    )
    require_dma_m2m_capability(
        target_capabilities,
        instance_id=instance_id,
        channel=0,
        transfer_count=transfer_count,
    )
    resource_pool_owned = False
    controller_enabled = False
    channel_configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if channel_configured:
            actions.append(("DMA channel stop", lambda: dma.stop(0)))
            actions.append(("DMA channel deconfigure", lambda: dma.deconfigure(0)))
        if controller_enabled:
            actions.append(("DMA controller disable", dma.controller_disable))
        if resource_pool_owned:
            actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        resource.reset()
        resource_pool_owned = True
        allocation_size = transfer_count + 2 * DMA_GUARD_SIZE
        source = resource.create(allocation_size, alignment=4)
        destination = resource.create(allocation_size, alignment=4)
        resource.fill(source, DMA_GUARD_VALUE)
        resource.fill(destination, DMA_GUARD_VALUE)
        resource.write(source, vector.source_data, offset=DMA_GUARD_SIZE)
        resource.fill(destination, DMA_DESTINATION_FILL, size=transfer_count, offset=DMA_GUARD_SIZE)
        dma.controller_enable()
        controller_enabled = True
        dma.configure(
            DmaConfig(
                channel=0,
                source_address=source.address + DMA_GUARD_SIZE,
                destination_address=destination.address + DMA_GUARD_SIZE,
                transfer_count=transfer_count,
                source_burst=DmaBurst.ITEMS_16,
                destination_burst=DmaBurst.ITEMS_16,
                fifo_mode=fifo_mode,
            )
        )
        channel_configured = True

        # CASE_CHANGE：复用已有 Snapshot，增加配置读回，不增加新的寄存器访问层。
        config_snapshot = dma.channel_snapshot_get(0)
        actual_fifo_mode = config_snapshot.fifo_mode
        record_property("expected_fifo_mode", fifo_mode.name.lower())
        record_observation(
            record_property,
            key="actual_fifo_mode",
            value=actual_fifo_mode.name.lower(),
            source="dut",
            endpoint="DMA_CHANNEL_CFG.FIFO_MODE",
        )

        dma.start(0)
        dma.wait_channel_free(0)
        source_raw = resource.read(source)
        destination_raw = resource.read(destination)
        guard = bytes([DMA_GUARD_VALUE]) * DMA_GUARD_SIZE
        actual = destination_raw[DMA_GUARD_SIZE:-DMA_GUARD_SIZE]
        status = dma.channel_status(0)
        guards_intact = (
            source_raw[:DMA_GUARD_SIZE] == guard
            and source_raw[-DMA_GUARD_SIZE:] == guard
            and destination_raw[:DMA_GUARD_SIZE] == guard
            and destination_raw[-DMA_GUARD_SIZE:] == guard
        )
        data_match = actual == vector.expected_destination
        record_property("data_match", data_match)
        record_property("guards_intact", guards_intact)
        record_observation(
            record_property,
            key="actual_data",
            value=actual,
            source="dut",
            endpoint="DMA_DESTINATION_DATA",
        )
        record_observation(
            record_property,
            key="channel_free",
            value=status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FREE",
        )

        write_json_result(
            et_artifact_dir / f"dma_p1_010_fifo_dma{instance_id}_mode{int(fifo_mode)}.json",
            {
                "measurement_schema": "et.measurement.v1",
                "expected_fifo_mode": fifo_mode.name.lower(),
                "actual_fifo_mode": actual_fifo_mode.name.lower(),
                "subcase": dma_m2m_measurement(
                    instance_id=instance_id,
                    channel=0,
                    transfer_count=transfer_count,
                    width=DmaWidth.BITS_8,
                    source_mode=DmaAddressMode.INCREMENT,
                    destination_mode=DmaAddressMode.INCREMENT,
                    source_burst=DmaBurst.ITEMS_16,
                    destination_burst=DmaBurst.ITEMS_16,
                    fifo_mode=fifo_mode,
                    vector=vector,
                    actual=actual,
                ),
                "guards_intact": guards_intact,
                "channel_free": status.is_free,
            },
        )

        assert actual_fifo_mode is fifo_mode
        assert source_raw[DMA_GUARD_SIZE:-DMA_GUARD_SIZE] == vector.source_data
        assert data_match
        assert guards_intact
        assert status.is_free


# =============================================================================
# LLI Control Writeback
# =============================================================================


# 测试 Feature：
# LLI Descriptor DONE 初始值和完成后的 Control Writeback。
#
# 测试方法：
# 1. 参数化 initial_done=False/True，读取传输前 Descriptor。
# 2. 执行单节点 LLI 后再次读取 Descriptor、目标数据和 Channel 状态。
# 3. DONE前后、非控制字段和数据在断言前进入Evidence。
#
# 通过条件：
# 1. 初始DONE等于参数，完成后DONE=1。
# 2. 非控制字段保持不变，目标数据正确。
# 3. Channel Free。
@pytest.mark.parametrize("initial_done", [False, True])
def test_dma_p1_011_done_writeback(
    dma_support_for: DmaSupportFactory,
    target_capabilities: ChipCapabilities,
    et_artifact_dir: Path,
    instance_id: int,
    initial_done: bool,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 按Contract顺序执行本Case，并在决定性断言前保存关键硬件事实。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=instance_id)
    resource_driver.reset()

    require_dma_control_writeback_capability(
        target_capabilities,
        instance_id=instance_id,
        channel=0,
    )
    support = dma_support_for(instance_id)
    resource = support.resource
    dma = support.dma
    source_data = bytes((index * 23 + 9) & 0xFF for index in range(64))
    flags = DMA_CONFIG_INITIAL_DONE if initial_done else 0
    resource_pool_owned = False
    controller_enabled = False
    channel_configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if channel_configured:
            actions.append(("DMA channel stop", lambda: dma.stop(0)))
            actions.append(("DMA channel deconfigure", lambda: dma.deconfigure(0)))
        if controller_enabled:
            actions.append(("DMA controller disable", dma.controller_disable))
        if resource_pool_owned:
            actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        resource.reset()
        resource_pool_owned = True
        source = resource.create(len(source_data), alignment=4)
        destination = resource.create(len(source_data), alignment=4)
        descriptor = resource.create(28, alignment=4)
        resource.write(source, source_data)
        resource.fill(destination, 0xA5)
        descriptor_config = DmaConfig(
            channel=0,
            source_address=source.address,
            destination_address=destination.address,
            transfer_count=len(source_data),
            source_update_mode=DmaUpdateMode.LINKED_LIST,
            destination_update_mode=DmaUpdateMode.LINKED_LIST,
            flags=flags,
        )
        dma.lli_descriptor_init_v2(descriptor.address, descriptor_config, is_last=True)
        before = resource.read(descriptor)
        done_mask = 1 << 12
        before_control_high = int.from_bytes(before[16:20], "little")
        initial_done_actual = bool(before_control_high & done_mask)

        dma.controller_enable()
        controller_enabled = True
        dma.configure(
            DmaConfig(
                channel=0,
                source_address=source.address,
                destination_address=destination.address,
                transfer_count=len(source_data),
                source_update_mode=DmaUpdateMode.LINKED_LIST,
                destination_update_mode=DmaUpdateMode.LINKED_LIST,
                linked_list_address=descriptor.address,
                flags=flags,
            )
        )
        channel_configured = True
        dma.start(0)
        dma.wait_channel_free(0)
        after = resource.read(descriptor)
        after_control_high = int.from_bytes(after[16:20], "little")
        actual_data = resource.read(destination)
        final_done = bool(after_control_high & done_mask)
        non_control_unchanged = before[:16] == after[:16] and before[20:] == after[20:]
        status = dma.channel_status(0)

        record_observation(
            record_property,
            key="initial_done",
            value=initial_done_actual,
            source="dut",
            endpoint="LLI_DESCRIPTOR.DONE",
        )
        record_observation(
            record_property,
            key="final_done",
            value=final_done,
            source="dut",
            endpoint="LLI_DESCRIPTOR.DONE",
        )
        record_property("non_control_unchanged", non_control_unchanged)
        record_property("data_match", actual_data == source_data)
        record_observation(
            record_property,
            key="actual_data",
            value=actual_data,
            source="dut",
            endpoint="DMA_DESTINATION_DATA",
        )
        record_observation(
            record_property,
            key="channel_free",
            value=status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FREE",
        )

        write_json_result(
            et_artifact_dir
            / f"dma_p1_011_done_writeback_dma{instance_id}_{int(initial_done)}.json",
            {
                "measurement_schema": "et.measurement.v1",
                "controller": instance_id,
                "initial_done": initial_done_actual,
                "descriptor_address": descriptor.address,
                "before_control_high": before_control_high,
                "after_control_high": after_control_high,
                "final_done": final_done,
                "done_mask": done_mask,
                "non_control_unchanged": non_control_unchanged,
                "data_match": actual_data == source_data,
                "channel_free": status.is_free,
            },
        )

        assert initial_done_actual == initial_done
        assert actual_data == source_data
        assert non_control_unchanged
        assert final_done
        assert status.is_free


# =============================================================================
# M2M 宽度与地址模式
# =============================================================================


# 测试 Feature：
# DMA M2M 的 8/16/32-bit 宽度与源/目标递增、递减、固定地址组合。
#
# 测试方法：
# 1. 参数化 3种Width × 3种Source Mode × 3种Destination Mode。
# 2. 纯软件生成17 Item Source/Expected，执行带Guard M2M。
# 3. 保存参数、Expected/Actual摘要和Free后执行强断言。
#
# 通过条件：
# 1. 27个参数实例全部执行。
# 2. 每轮Destination与Expected一致、Source不变、Guard完整。
# 3. Channel Free。
@pytest.mark.parametrize("width", list(DmaWidth))
@pytest.mark.parametrize("source_mode", list(DmaAddressMode))
@pytest.mark.parametrize("destination_mode", list(DmaAddressMode))
def test_dma_p1_014_m2m_width_address_matrix(
    dma_support_for: DmaSupportFactory,
    target_capabilities: ChipCapabilities,
    et_artifact_dir: Path,
    instance_id: int,
    width: DmaWidth,
    source_mode: DmaAddressMode,
    destination_mode: DmaAddressMode,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 按Contract顺序执行本Case，并在决定性断言前保存关键硬件事实。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=instance_id)
    resource_driver.reset()

    transfer_count = 17
    support = dma_support_for(instance_id)
    resource = support.resource
    dma = support.dma
    vector = build_dma_m2m_vector(transfer_count, width, source_mode, destination_mode)
    require_dma_m2m_capability(
        target_capabilities,
        instance_id=instance_id,
        channel=0,
        transfer_count=transfer_count,
    )
    resource_pool_owned = False
    controller_enabled = False
    channel_configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if channel_configured:
            actions.append(("DMA channel stop", lambda: dma.stop(0)))
            actions.append(("DMA channel deconfigure", lambda: dma.deconfigure(0)))
        if controller_enabled:
            actions.append(("DMA controller disable", dma.controller_disable))
        if resource_pool_owned:
            actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        resource.reset()
        resource_pool_owned = True
        allocation_size = len(vector.source_data) + 2 * DMA_GUARD_SIZE
        source = resource.create(allocation_size, alignment=4)
        destination = resource.create(allocation_size, alignment=4)
        resource.fill(source, DMA_GUARD_VALUE)
        resource.fill(destination, DMA_GUARD_VALUE)
        resource.write(source, vector.source_data, offset=DMA_GUARD_SIZE)
        resource.fill(
            destination,
            DMA_DESTINATION_FILL,
            size=len(vector.expected_destination),
            offset=DMA_GUARD_SIZE,
        )
        dma.controller_enable()
        controller_enabled = True
        dma.configure(
            DmaConfig(
                channel=0,
                source_address=source.address + vector.source_start_offset,
                destination_address=destination.address + vector.destination_start_offset,
                transfer_count=transfer_count,
                source_width=width,
                destination_width=width,
                source_address_mode=source_mode,
                destination_address_mode=destination_mode,
            )
        )
        channel_configured = True
        dma.start(0)
        dma.wait_channel_free(0)
        source_raw = resource.read(source)
        destination_raw = resource.read(destination)
        guard = bytes([DMA_GUARD_VALUE]) * DMA_GUARD_SIZE
        actual = destination_raw[DMA_GUARD_SIZE:-DMA_GUARD_SIZE]
        status = dma.channel_status(0)
        parameter_id = f"w{int(width)}-s{int(source_mode)}-d{int(destination_mode)}"
        guards_intact = (
            source_raw[:DMA_GUARD_SIZE] == guard
            and source_raw[-DMA_GUARD_SIZE:] == guard
            and destination_raw[:DMA_GUARD_SIZE] == guard
            and destination_raw[-DMA_GUARD_SIZE:] == guard
        )

        record_property("parameter_id", parameter_id)
        record_property("expected_data", vector.expected_destination)
        record_property("expected_data_digest", _digest(vector.expected_destination))
        record_property(
            "source_unchanged", source_raw[DMA_GUARD_SIZE:-DMA_GUARD_SIZE] == vector.source_data
        )
        record_property("guards_intact", guards_intact)
        record_observation(
            record_property,
            key="actual_data",
            value=actual,
            source="dut",
            endpoint="DMA_DESTINATION_DATA",
        )
        record_property("actual_data_digest", _digest(actual))
        record_observation(
            record_property,
            key="channel_free",
            value=status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FREE",
        )

        result = dma_m2m_measurement(
            instance_id=instance_id,
            channel=0,
            transfer_count=transfer_count,
            width=width,
            source_mode=source_mode,
            destination_mode=destination_mode,
            source_burst=DmaBurst.ITEMS_1,
            destination_burst=DmaBurst.ITEMS_1,
            fifo_mode=DmaFifoMode.SINGLE,
            vector=vector,
            actual=actual,
        )
        write_json_result(
            et_artifact_dir
            / f"dma_p1_014_dma{instance_id}_w{int(width)}_s{int(source_mode)}_d{int(destination_mode)}.json",
            {"measurement_schema": "et.measurement.v1", "measurement": result},
        )

        assert source_raw[DMA_GUARD_SIZE:-DMA_GUARD_SIZE] == vector.source_data
        assert actual == vector.expected_destination
        assert guards_intact
        assert status.is_free


# =============================================================================
# Block Count 与 Burst 边界
# =============================================================================


# 测试 Feature：
# 1. test_dma_p1_015_block_and_burst_boundaries对应的DMA稳定硬件Feature。
#
# 测试方法：
# 1. 按Contract准备输入，通过稳定Driver执行配置、刺激和硬件观测。
#
# 通过条件：
# 1. 决定性Observation与Expected一致，且本Case获得的资源最终可恢复。
@pytest.mark.parametrize(
    "transfer_count_spec,source_burst,destination_burst",
    [("burst_sample", burst, burst) for burst in DmaBurst]
    + [
        (count, DmaBurst.ITEMS_1, DmaBurst.ITEMS_1)
        for count in (1, 2, 3, 4, 7, 8, 15, 16, 255, 256)
    ]
    + [
        ("max_minus_one", DmaBurst.ITEMS_1, DmaBurst.ITEMS_1),
        ("max", DmaBurst.ITEMS_1, DmaBurst.ITEMS_1),
    ],
)
def test_dma_p1_015_block_and_burst_boundaries(
    dma_support_for: DmaSupportFactory,
    target_capabilities: ChipCapabilities,
    et_artifact_dir: Path,
    instance_id: int,
    transfer_count_spec: int | str,
    source_burst: DmaBurst,
    destination_burst: DmaBurst,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=instance_id)
    resource_driver.reset()

    support = dma_support_for(instance_id)
    resource = support.resource
    dma = support.dma
    maximum = dma.capabilities_get().max_transfer_count
    if transfer_count_spec == "burst_sample":
        transfer_count = min(512, maximum)
    elif transfer_count_spec == "max_minus_one":
        transfer_count = max(1, maximum - 1)
    elif transfer_count_spec == "max":
        transfer_count = maximum
    else:
        transfer_count = transfer_count_spec
    vector = build_dma_m2m_vector(
        transfer_count,
        DmaWidth.BITS_8,
        DmaAddressMode.INCREMENT,
        DmaAddressMode.INCREMENT,
    )
    require_dma_m2m_capability(
        target_capabilities,
        instance_id=instance_id,
        channel=0,
        transfer_count=transfer_count,
    )
    resource_pool_owned = False
    controller_enabled = False
    channel_configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if channel_configured:
            actions.append(("DMA channel stop", lambda: dma.stop(0)))
            actions.append(("DMA channel deconfigure", lambda: dma.deconfigure(0)))
        if controller_enabled:
            actions.append(("DMA controller disable", dma.controller_disable))
        if resource_pool_owned:
            actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        resource.reset()
        resource_pool_owned = True
        allocation_size = len(vector.source_data) + 2 * DMA_GUARD_SIZE
        source = resource.create(allocation_size, alignment=4)
        destination = resource.create(allocation_size, alignment=4)
        resource.fill(source, DMA_GUARD_VALUE)
        resource.fill(destination, DMA_GUARD_VALUE)
        resource.write(source, vector.source_data, offset=DMA_GUARD_SIZE)
        resource.fill(
            destination,
            DMA_DESTINATION_FILL,
            size=len(vector.expected_destination),
            offset=DMA_GUARD_SIZE,
        )
        dma.controller_enable()
        controller_enabled = True
        dma.configure(
            DmaConfig(
                channel=0,
                source_address=source.address + DMA_GUARD_SIZE,
                destination_address=destination.address + DMA_GUARD_SIZE,
                transfer_count=transfer_count,
                source_burst=source_burst,
                destination_burst=destination_burst,
            )
        )
        channel_configured = True

        # CASE_CHANGE：用现有 Channel Snapshot 读取真实 Block/Burst 配置。
        config_snapshot = dma.channel_snapshot_get(0)
        actual_block_size = config_snapshot.block_size
        actual_source_burst = config_snapshot.source_burst
        actual_destination_burst = config_snapshot.destination_burst
        record_property("expected_block_size", transfer_count)
        record_property("expected_source_burst", source_burst.name.lower())
        record_property("expected_destination_burst", destination_burst.name.lower())
        record_observation(
            record_property,
            key="actual_block_size",
            value=actual_block_size,
            source="dut",
            endpoint="DMA_CHANNEL_CTL.BLOCK_SIZE",
        )
        record_observation(
            record_property,
            key="actual_source_burst",
            value=actual_source_burst.name.lower(),
            source="dut",
            endpoint="DMA_CHANNEL_CTL.SOURCE_BURST",
        )
        record_observation(
            record_property,
            key="actual_destination_burst",
            value=actual_destination_burst.name.lower(),
            source="dut",
            endpoint="DMA_CHANNEL_CTL.DESTINATION_BURST",
        )

        dma.start(0)
        dma.wait_channel_free(0)
        source_raw = resource.read(source)
        destination_raw = resource.read(destination)
        guard = bytes([DMA_GUARD_VALUE]) * DMA_GUARD_SIZE
        actual = destination_raw[DMA_GUARD_SIZE:-DMA_GUARD_SIZE]
        status = dma.channel_status(0)
        guards_intact = (
            source_raw[:DMA_GUARD_SIZE] == guard
            and source_raw[-DMA_GUARD_SIZE:] == guard
            and destination_raw[:DMA_GUARD_SIZE] == guard
            and destination_raw[-DMA_GUARD_SIZE:] == guard
        )
        data_match = actual == vector.expected_destination
        record_property("data_match", data_match)
        record_property("guards_intact", guards_intact)
        record_observation(
            record_property,
            key="actual_data",
            value=actual,
            source="dut",
            endpoint="DMA_DESTINATION_DATA",
        )
        record_observation(
            record_property,
            key="channel_free",
            value=status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FREE",
        )

        result = dma_m2m_measurement(
            instance_id=instance_id,
            channel=0,
            transfer_count=transfer_count,
            width=DmaWidth.BITS_8,
            source_mode=DmaAddressMode.INCREMENT,
            destination_mode=DmaAddressMode.INCREMENT,
            source_burst=source_burst,
            destination_burst=destination_burst,
            fifo_mode=DmaFifoMode.SINGLE,
            vector=vector,
            actual=actual,
        )
        write_json_result(
            et_artifact_dir
            / f"dma_p1_015_dma{instance_id}_n{transfer_count}_b{int(source_burst)}_{int(destination_burst)}.json",
            {
                "measurement_schema": "et.measurement.v1",
                "expected_block_size": transfer_count,
                "actual_block_size": actual_block_size,
                "expected_source_burst": source_burst.name.lower(),
                "actual_source_burst": actual_source_burst.name.lower(),
                "expected_destination_burst": destination_burst.name.lower(),
                "actual_destination_burst": actual_destination_burst.name.lower(),
                "measurement": result,
            },
        )

        assert maximum > 0
        assert actual_block_size == transfer_count
        assert actual_source_burst is source_burst
        assert actual_destination_burst is destination_burst
        assert source_raw[DMA_GUARD_SIZE:-DMA_GUARD_SIZE] == vector.source_data
        assert data_match
        assert guards_intact
        assert status.is_free


# =============================================================================
# Resource SRAM 与完成中断
# =============================================================================


# 测试 Feature：
# 两个 Resource Driver 管理的 SRAM Buffer 之间的 M2M 数据完整性和 TRANSFER_DONE。
#
# 测试方法：
# 1. 创建带 Guard 的 256 Byte Source/Destination 并配置 TRANSFER_DONE。
# 2. Start 后等待 IRQ 与 Free，读取完整 Buffer 和 ISR Result。
# 3. 保存实际数据、Guard、ISR Latch和Free后断言。
#
# 通过条件：
# 1. Destination等于Source，Source与全部Guard保持不变。
# 2. TRANSFER_DONE交付且Unexpected/Overflow=0。
# 3. Channel Free；本Case不声明TCM地址转换覆盖。
def test_dma_p1_016_memory_region_matrix(
    dma_support_for: DmaSupportFactory,
    target_capabilities: ChipCapabilities,
    et_artifact_dir: Path,
    instance_id: int,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 按Contract顺序执行本Case，并在决定性断言前保存关键硬件事实。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=instance_id)
    resource_driver.reset()

    support = dma_support_for(instance_id)
    resource = support.resource
    dma = support.dma
    transfer_count = 256
    source_data = bytes((index * 17 + 9) & 0xFF for index in range(transfer_count))
    require_dma_m2m_capability(
        target_capabilities,
        instance_id=instance_id,
        channel=0,
        transfer_count=transfer_count,
    )
    events = DmaIrqEvent.TRANSFER_DONE
    resource_pool_owned = False
    controller_enabled = False
    channel_configured = False
    irq_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if irq_enabled:
            actions.append(("DMA IRQ disable", lambda: dma.irq_disable(events)))
        if channel_configured:
            actions.append(("DMA channel stop", lambda: dma.stop(0)))
            actions.append(("DMA channel deconfigure", lambda: dma.deconfigure(0)))
        if controller_enabled:
            actions.append(("DMA controller disable", dma.controller_disable))
        if resource_pool_owned:
            actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        resource.reset()
        resource_pool_owned = True
        allocation_size = transfer_count + 2 * DMA_GUARD_SIZE
        source = resource.create(allocation_size, alignment=4)
        destination = resource.create(allocation_size, alignment=4)
        resource.fill(source, DMA_GUARD_VALUE)
        resource.fill(destination, DMA_GUARD_VALUE)
        resource.write(source, source_data, offset=DMA_GUARD_SIZE)
        resource.fill(destination, DMA_DESTINATION_FILL, size=transfer_count, offset=DMA_GUARD_SIZE)
        dma.controller_enable()
        controller_enabled = True
        dma.configure(
            DmaConfig(
                channel=0,
                source_address=source.address + DMA_GUARD_SIZE,
                destination_address=destination.address + DMA_GUARD_SIZE,
                transfer_count=transfer_count,
            )
        )
        channel_configured = True
        route_count = dma.irq_enable(0, events, priority=4)
        irq_enabled = True
        dma.irq_result_clear()
        dma.start(0)
        result = dma.wait_irq_count(minimum_count=1, timeout_s=2.0)
        dma.wait_channel_free(0, timeout_s=2.0)
        source_raw = resource.read(source)
        destination_raw = resource.read(destination)
        channel_status = dma.channel_status(0)
        guard = bytes([DMA_GUARD_VALUE]) * DMA_GUARD_SIZE
        actual_data = destination_raw[DMA_GUARD_SIZE:-DMA_GUARD_SIZE]
        data_match = actual_data == source_data
        guards_intact = (
            source_raw[:DMA_GUARD_SIZE] == guard
            and source_raw[-DMA_GUARD_SIZE:] == guard
            and destination_raw[:DMA_GUARD_SIZE] == guard
            and destination_raw[-DMA_GUARD_SIZE:] == guard
        )

        record_property("expected_data", source_data)
        record_property("data_match", data_match)
        record_property("guards_intact", guards_intact)
        record_observation(
            record_property,
            key="actual_data",
            value=actual_data,
            source="dut",
            endpoint="DMA_DESTINATION_DATA",
        )
        record_observation(
            record_property,
            key="isr_latched_transfer_done",
            value=bool(result.latched_events & events),
            source="dut",
            endpoint="ISR.LATCHED.TRANSFER_DONE",
        )
        record_observation(
            record_property,
            key="channel_free",
            value=channel_status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FREE",
        )

        write_json_result(
            et_artifact_dir / f"dma_p1_016_memory_region_matrix_dma{instance_id}.json",
            {
                "measurement_schema": "et.measurement.v1",
                "controller": instance_id,
                "channel": 0,
                "transfer_count": transfer_count,
                "route_count": route_count,
                "irq_count": result.irq_count,
                "latched_events": int(result.latched_events),
                "unexpected_count": result.unexpected_count,
                "overflow_count": result.overflow_count,
                "expected_sha256": _digest(source_data),
                "actual_sha256": _digest(actual_data),
                "data_match": data_match,
                "guards_intact": guards_intact,
                "channel_free": channel_status.is_free,
            },
        )

        assert source_raw[DMA_GUARD_SIZE:-DMA_GUARD_SIZE] == source_data
        assert data_match
        assert guards_intact
        assert result.latched_events & events == events
        assert result.irq_count >= 1
        assert result.unexpected_count == 0
        assert result.overflow_count == 0
        assert channel_status.is_free


# =============================================================================
# 非法参数拒绝与恢复
# =============================================================================


# 测试 Feature：
# DMA 非法配置的 PC/Firmware 拒绝边界，以及拒绝后的同 Controller 恢复能力。
#
# 测试方法：
# 1. 在同一已使能Controller上依次提交7组非法参数，记录实际拒绝层级。
# 2. 随后配置32 Byte合法M2M并执行恢复传输。
# 3. 拒绝数量、层级、实际恢复数据和Free在最终断言前保存。
#
# 通过条件：
# 1. 7/7非法配置均由预期PC Contract或Firmware层拒绝。
# 2. 合法恢复传输数据完全匹配。
# 3. Channel 0最终Free。
def test_dma_p1_017_invalid_parameter_rejection(
    dma_support_for: DmaSupportFactory,
    target_capabilities: ChipCapabilities,
    et_artifact_dir: Path,
    instance_id: int,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 按Contract顺序执行本Case，并在决定性断言前保存关键硬件事实。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=instance_id)
    resource_driver.reset()

    support = dma_support_for(instance_id)
    resource = support.resource
    dma = support.dma
    payload = bytes((index * 19 + 7) & 0xFF for index in range(32))
    require_dma_m2m_capability(
        target_capabilities,
        instance_id=instance_id,
        channel=0,
        transfer_count=len(payload),
    )
    resource_pool_owned = False
    controller_enabled = False
    recovery_channel_configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if recovery_channel_configured:
            actions.append(("DMA channel stop", lambda: dma.stop(0)))
            actions.append(("DMA channel deconfigure", lambda: dma.deconfigure(0)))
        if controller_enabled:
            actions.append(("DMA controller disable", dma.controller_disable))
        if resource_pool_owned:
            actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        resource.reset()
        resource_pool_owned = True
        source = resource.create(len(payload), alignment=4)
        destination = resource.create(len(payload), alignment=4)
        resource.write(source, payload)
        resource.fill(destination, 0xA5)
        base = {
            "channel": 0,
            "source_address": source.address,
            "destination_address": destination.address,
            "transfer_count": 1,
        }
        dynamic = dma.capabilities_get()
        invalid = [
            ("transfer_count_zero", {"transfer_count": 0}, "firmware"),
            (
                "transfer_count_overflow",
                {"transfer_count": dynamic.max_transfer_count + 1},
                "firmware",
            ),
            ("source_width_unknown", {"source_width": 3}, "pc_contract"),
            ("source_burst_unknown", {"source_burst": 8}, "pc_contract"),
            ("channel_out_of_range", {"channel": dynamic.channel_count}, "firmware"),
            (
                "source_gather_count_overflow",
                {"flags": 1, "source_gather_count": dynamic.max_gather_scatter_count + 1},
                "firmware",
            ),
            (
                "source_gather_interval_overflow",
                {"flags": 1, "source_gather_interval": dynamic.max_gather_scatter_interval + 1},
                "firmware",
            ),
        ]
        dma.controller_enable()
        controller_enabled = True
        rejected: list[dict[str, int | str]] = []
        # 遍历本Case声明的参数或资源集合，逐项形成可追溯硬件证据。
        for name, overrides, rejection_layer in invalid:
            config = DmaConfig(**{**base, **overrides})
            if rejection_layer == "pc_contract":
                with pytest.raises(ValueError):
                    dma.configure(config)
                rejected.append({"vector": name, "layer": rejection_layer})
            else:
                with pytest.raises(TargetRejected) as exc_info:
                    dma.configure(config)
                rejected.append(
                    {
                        "vector": name,
                        "layer": rejection_layer,
                        "status": exc_info.value.status,
                    }
                )

        recovery_config = DmaConfig(
            channel=0,
            source_address=source.address,
            destination_address=destination.address,
            transfer_count=len(payload),
        )
        dma.configure(recovery_config)
        recovery_channel_configured = True
        dma.start(0)
        dma.wait_channel_free(0)
        actual = resource.read(destination)
        status = dma.channel_status(0)
        recovery_data_match = actual == payload

        record_property("expected_rejected_count", len(invalid))
        record_property("actual_rejected_count", len(rejected))
        record_property("rejection_layers", [item["layer"] for item in rejected])
        record_property("recovery_data_match", recovery_data_match)
        record_observation(
            record_property,
            key="recovery_actual_data",
            value=actual,
            source="dut",
            endpoint="DMA_DESTINATION_DATA",
        )
        record_property("recovery_channel_free", status.is_free)
        record_observation(
            record_property,
            key="recovery_free_state",
            value=status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FREE",
        )

        write_json_result(
            et_artifact_dir / f"dma_p1_017_invalid_parameter_rejection_dma{instance_id}.json",
            {
                "measurement_schema": "et.measurement.v1",
                "controller": instance_id,
                "expected_rejected_count": len(invalid),
                "actual_rejected_count": len(rejected),
                "rejections": rejected,
                "recovery_bytes": len(payload),
                "recovery_data_match": recovery_data_match,
                "recovery_channel_free": status.is_free,
            },
        )

        assert len(rejected) == len(invalid)
        assert recovery_data_match
        assert status.is_free
