# CAN P2多实例组合测试。
# 职责：显式编排各实例配置、交错收发和隔离比较。
# 边界：只用公共Driver；实例和RAM区域从Capability及Mapping读取。
# 依赖：CAN/CRG/Resource、只读Support及Canonical Observation。

from dataclasses import asdict, replace

import pytest

from ...core.errors import ConfigurationError
from ...drivers.can import (
    CanFilter,
    CanFilterAction,
    CanFilterType,
    CanFrameFlags,
    CanLoopback,
    CanRxSource,
    CanTiming,
    CanTxFrame,
)
from ...drivers.crg import CrgPeripheral
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import PATTERN_A, TIMEOUT_S, loopback_ram, phase_timing

pytestmark = [pytest.mark.hardware, pytest.mark.ip("can")]


# =============================================================================
# 多实例存储隔离
# =============================================================================


# 测试 Feature：
# CAN多实例配置、Message RAM及内部回环数据隔离。
#
# 测试方法：
# 1. 枚举全部实例，逐一复位后清空资源池；为各实例配置独立ID和首尾Guard。
# 2. 所有实例先发送并达到RX就绪，再逆序读取，逐字段比较完整帧。
# 3. 只改变最后实例Filter并再收发，复核全部实例配置及RAM首尾Guard。
#
# 通过条件：
# 1. 每个实例只收到自己的ID和数据，发送完成且RX无Lost。
# 2. 重配最后实例不改变其他实例的Filter、布局和Guard。
def test_can_p2_004_instance_ram_isolation(
    can_instance_supports, resource_driver, record_property
) -> None:

    # 准备：并存切片由Mapping显式声明，不从单实例容量推断物理独占。
    supports = can_instance_supports
    layouts, filters, guards = {}, {}, {}
    regions = supports[0].mapping.CAN_CONCURRENT_RAM_REGIONS
    frame_text, guard_text = [], []
    hardware_trace = []
    record_property("expected", "每实例ID及数据独立；全部TX完成；首尾Guard和其他实例配置保持")

    # 每个实例保留开头两个word给Guard，所有CAN元素整体平移以免覆盖。
    for index, support in enumerate(supports):
        start, size = regions[support.handle]
        if start < 0 or start % 4 or size % 4 or start + size > support.ram_limits.ram_bytes:
            raise ConfigurationError(f"CAN concurrent RAM slice is invalid: {support.handle}")
        layout = loopback_ram(support)
        offsets = {
            name: getattr(layout, name) + start + 8
            for name in (
                "std_offset",
                "ext_offset",
                "tx_offset",
                "event_offset",
                "rx0_offset",
                "rx1_offset",
                "rx_buffer_offset",
            )
        }
        layouts[support.handle] = replace(layout, **offsets)
        end = offsets["rx_buffer_offset"] + support.ram_limits.rx_buffer_count * (
            support.mapping.CAN_RAM_HEADER_BYTES + layout.rx_buffer_payload_bytes
        )
        if end > start + size - 4:
            raise ConfigurationError(f"CAN layout overlaps final guard: {support.handle}")
        filters[support.handle] = CanFilter(
            CanFilterType.DUAL, CanFilterAction.FIFO0, 0x100 + index, 0x100 + index
        )
        guards[support.handle] = (0x5A5A0000 | index, 0xA5A50000 | index)

    # 清理：全部参与实例分别复位，最后复位资源池；单项错误不阻断其余恢复。
    with case_cleanup_scope(
        lambda: (
            tuple(
                (
                    f"{s.handle} reset",
                    lambda s=s: s.crg.reset(CrgPeripheral.CAN, instance=s.can.instance_id),
                )
                for s in supports
            )
            + (("Resource pool reset", resource_driver.reset),)
        )
    ):
        # 隔离：先复位所有参与CAN，再清空资源；不复位控制UART或无关IP。
        for support in supports:
            support.crg.reset(CrgPeripheral.CAN, instance=support.can.instance_id)
        resource_driver.reset()

        # 配置：各实例同时保持不同ID；Guard覆盖窗口首尾，不参与收发元素布局。
        for support in supports:
            can, handle = support.can, support.handle
            start, size = regions[handle]
            can.initializing_set(True)
            can.wait_initializing(True, timeout_s=TIMEOUT_S)
            can.timing_set(
                CanTiming(
                    phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
                    phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
                )
            )
            can.ram_layout_set(layouts[handle])
            can.filter_set(0, filters[handle], extended=False)
            can.loopback_set(CanLoopback.INTERNAL)
            can.ram_words_write(start, (guards[handle][0],))
            can.ram_words_write(start + size - 4, (guards[handle][1],))

        # 配置观测：全部写完才统一读回，才能发现后一个配置覆盖前一个实例。
        for support in supports:
            actual_layout = support.can.ram_layout_get()
            actual_filter = support.can.filter_get(0, extended=False)
            # 配置阶段已可失败；报告先保存实际Filter，不能等收到帧才有硬件备注。
            hardware_trace.append(
                f"{support.handle} Filter: ID1=0x{actual_filter.id1:X}, ID2=0x{actual_filter.id2:X}"
            )
            record_property("hardware_trace", hardware_trace)
            record_observation(
                record_property,
                key="layout_before",
                value=asdict(actual_layout),
                source="dut",
                endpoint="CONFIG.RAM_LAYOUT",
                device_id=support.handle,
            )
            record_observation(
                record_property,
                key="filter_before",
                value=asdict(actual_filter),
                source="dut",
                endpoint="FILTER.STANDARD",
                device_id=support.handle,
            )
            assert actual_layout == layouts[support.handle]
            assert actual_filter == filters[support.handle]
            support.can.initializing_set(False)
            support.can.wait_initializing(False, timeout_s=TIMEOUT_S)

        # 激励：全部实例先挂帧，不能一发一收而失去并存覆盖。
        for index, support in enumerate(supports):
            frame = CanTxFrame(
                0x100 + index, CanFrameFlags(0), 8, 0, index.to_bytes(4, "little") + PATTERN_A[4:]
            )
            support.can.tx_write(0, frame)
            support.can.tx_request(1)

        # 等待：在任何读取前确认所有RX可读，并保存各实例真实完成和Lost状态。
        for support in supports:
            tx = support.can.wait_tx_complete(1, timeout_s=TIMEOUT_S)
            rx = support.can.wait_rx_available(0, timeout_s=TIMEOUT_S)
            record_observation(
                record_property,
                key="tx",
                value=tx.completed,
                source="dut",
                endpoint="TX.COMPLETED",
                device_id=support.handle,
            )
            record_observation(
                record_property,
                key="lost",
                value=rx.lost,
                source="dut",
                endpoint="RX0.LOST",
                device_id=support.handle,
            )
            assert tx.completed & 1 and not rx.lost

        # 读取：逆序逐帧核对，不从发送缓存生成实际帧。
        for index in reversed(range(len(supports))):
            support = supports[index]
            actual = support.can.rx_read(CanRxSource.FIFO0)
            frame_text.append(
                f"{support.handle}: ID=0x{actual.identifier:X}, DATA={actual.data.hex(' ').upper()}"
            )
            record_property("frames", frame_text)
            hardware_trace.append(frame_text[-1])
            record_property("hardware_trace", hardware_trace)
            record_observation(
                record_property,
                key="frame",
                value=asdict(actual),
                source="dut",
                endpoint="RX.FRAME",
                device_id=support.handle,
            )
            assert actual.identifier == 0x100 + index and actual.dlc == 8
            assert actual.flags == CanFrameFlags(0) and not actual.nonmatching
            assert actual.data == index.to_bytes(4, "little") + PATTERN_A[4:]
            support.can.rx_fifo_ack(0, actual.index)

        # 隔离刺激：仅最后实例进入INIT改变Filter，其他实例保持运行。
        last = supports[-1]
        last.can.initializing_set(True)
        last.can.wait_initializing(True, timeout_s=TIMEOUT_S)
        filters[last.handle] = CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x500, 0x500)
        last.can.filter_set(0, filters[last.handle], extended=False)
        last.can.initializing_set(False)
        last.can.wait_initializing(False, timeout_s=TIMEOUT_S)
        last.can.tx_write(0, CanTxFrame(0x500, CanFrameFlags(0), 8, 0, PATTERN_A))
        last.can.tx_request(1)
        tx = last.can.wait_tx_complete(1, timeout_s=TIMEOUT_S)
        rx = last.can.wait_rx_available(0, timeout_s=TIMEOUT_S)
        actual = last.can.rx_read(CanRxSource.FIFO0)
        record_observation(
            record_property,
            key="changed_frame",
            value=asdict(actual),
            source="dut",
            endpoint="RX.FRAME",
            device_id=last.handle,
        )
        record_observation(
            record_property,
            key="changed_tx",
            value=tx.completed,
            source="dut",
            endpoint="TX.COMPLETED",
            device_id=last.handle,
        )
        record_observation(
            record_property,
            key="changed_lost",
            value=rx.lost,
            source="dut",
            endpoint="RX0.LOST",
            device_id=last.handle,
        )
        assert actual.identifier == 0x500 and actual.data == PATTERN_A
        assert actual.dlc == 8 and actual.flags == CanFrameFlags(0) and not actual.nonmatching
        assert tx.completed & 1 and not rx.lost
        last.can.rx_fifo_ack(0, actual.index)

        # 终态：无额外RX，进入INIT后读实际布局、Filter和Guard，不复位后再验证。
        for support in supports:
            can, handle = support.can, support.handle
            start, size = regions[handle]
            empty = can.rx_fifo_status_get(0)
            record_observation(
                record_property,
                key="empty",
                value=empty.fill,
                source="dut",
                endpoint="RX0.FILL",
                device_id=handle,
            )
            assert empty.fill == 0 and not empty.lost
            can.initializing_set(True)
            can.wait_initializing(True, timeout_s=TIMEOUT_S)
            actual_layout = can.ram_layout_get()
            actual_filter = can.filter_get(0, extended=False)
            actual_guards = (
                can.ram_words_read(start, 1)[0],
                can.ram_words_read(start + size - 4, 1)[0],
            )
            guard_text.append(f"{handle}: 0x{actual_guards[0]:08X}/0x{actual_guards[1]:08X}")
            record_property("guards", guard_text)
            hardware_trace.append(guard_text[-1])
            record_property("hardware_trace", hardware_trace)
            record_observation(
                record_property,
                key="layout_after",
                value=asdict(actual_layout),
                source="dut",
                endpoint="CONFIG.RAM_LAYOUT",
                device_id=handle,
            )
            record_observation(
                record_property,
                key="filter_after",
                value=asdict(actual_filter),
                source="dut",
                endpoint="FILTER.STANDARD",
                device_id=handle,
            )
            record_observation(
                record_property,
                key="guard",
                value=actual_guards,
                source="dut",
                endpoint="RAM.GUARD",
                device_id=handle,
            )
            assert actual_layout == layouts[handle] and actual_filter == filters[handle]
            assert actual_guards == guards[handle]
