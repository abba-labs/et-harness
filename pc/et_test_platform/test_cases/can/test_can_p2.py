# pyright: reportMissingImports=none
# CAN P2多实例组合测试。
# 职责：显式编排各实例配置、交错收发和隔离比较。
# 边界：只用公共Driver；实例和RAM区域从Capability及Mapping读取。
# 依赖：CAN Driver、pytest与多实例Support。

from dataclasses import replace

import pytest  # pyright: ignore[reportMissingImports] # type: ignore

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
from ._support import PATTERN_A, TIMEOUT_S, loopback_ram, phase_timing

pytestmark = [pytest.mark.hardware, pytest.mark.ip("can")]


# =============================================================================
# 多实例存储隔离（范围调整项：保持多实例跨芯片映射验证）
# =============================================================================


# 测试 Feature：
# CAN多实例配置、Message RAM及内部回环数据隔离。
#
# 测试方法：
# 1. 枚举全部实例并复位，为各实例配置独立ID和首尾Guard。
# 2. 所有实例先发送并达到RX就绪，再逆序读取比对。
# 3. 改变最后实例Filter并再收发，复核全部实例配置及RAM首尾Guard。
#
# 通过条件：
# 1. 每个实例只收到自己的ID和数据，发送完成且RX无Lost。
# 2. 重配最后实例不改变其他实例的Filter、布局和Guard。
def test_can_p2_004_instance_ram_isolation(can_instance_supports) -> None:
    # 1）准备与复位
    supports = can_instance_supports
    layouts, filters, guards = {}, {}, {}
    regions = supports[0].mapping.CAN_CONCURRENT_RAM_REGIONS

    for support in supports:
        support.can.reset()

    # 2）IP 配置与Guard准备
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
        filters[support.handle] = CanFilter(
            CanFilterType.DUAL, CanFilterAction.FIFO0, 0x100 + index, 0x100 + index
        )
        guards[support.handle] = (0x5A5A0000 | index, 0xA5A50000 | index)

        can, handle = support.can, support.handle
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
        can.initializing_set(False)
        can.wait_initializing(False, timeout_s=TIMEOUT_S)

    # 3）获取并判断结果：交错发送与逆序读取
    for index, support in enumerate(supports):
        frame = CanTxFrame(
            0x100 + index, CanFrameFlags(0), 8, 0, index.to_bytes(4, "little") + PATTERN_A[4:]
        )
        support.can.tx_write(0, frame)
        support.can.tx_request(1)

    for support in supports:
        assert support.can.wait_tx_complete(1, timeout_s=TIMEOUT_S).completed & 1
        assert support.can.wait_rx_available(0, timeout_s=TIMEOUT_S).fill >= 1

    for index in reversed(range(len(supports))):
        support = supports[index]
        actual = support.can.rx_read(CanRxSource.FIFO0)
        assert actual.identifier == 0x100 + index and actual.dlc == 8
        assert actual.data == index.to_bytes(4, "little") + PATTERN_A[4:]
        support.can.rx_fifo_ack(0, actual.index)

    # 隔离验证：改变最后实例Filter
    last = supports[-1]
    last.can.initializing_set(True)
    last.can.wait_initializing(True, timeout_s=TIMEOUT_S)
    filters[last.handle] = CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x500, 0x500)
    last.can.filter_set(0, filters[last.handle], extended=False)
    last.can.initializing_set(False)
    last.can.wait_initializing(False, timeout_s=TIMEOUT_S)

    last.can.tx_write(0, CanTxFrame(0x500, CanFrameFlags(0), 8, 0, PATTERN_A))
    last.can.tx_request(1)
    assert last.can.wait_tx_complete(1, timeout_s=TIMEOUT_S).completed & 1
    last_rx = last.can.rx_read(CanRxSource.FIFO0)
    assert last_rx.identifier == 0x500 and last_rx.data == PATTERN_A
    last.can.rx_fifo_ack(0, last_rx.index)

    # 最终 Guard 核验
    for support in supports:
        start, size = regions[support.handle]
        can = support.can
        assert can.rx_fifo_status_get(0).fill == 0
        actual_guards = (
            can.ram_words_read(start, 1)[0],
            can.ram_words_read(start + size - 4, 1)[0],
        )
        assert actual_guards == guards[support.handle]
