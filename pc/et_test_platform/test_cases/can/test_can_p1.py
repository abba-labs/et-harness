# pyright: reportMissingImports=false
# CAN P1帧格式与DLC边界。
# 职责：明确配置、双Pattern激励、实际帧观测和独立Expected比较。
# 边界：不把内部回环当作外部位速率测量，不在Case绑定芯片地址或实例。
# 依赖：CAN/CRG/Resource公共Driver及只读Support。

from dataclasses import asdict
from time import sleep

import pytest

from ...core.deadline import OperationDeadline
from ...drivers.can import (
    CanBusConfig,
    CanFilter,
    CanFilterAction,
    CanFilterType,
    CanFrameFlags,
    CanHighPriorityStorage,
    CanIrqSource,
    CanLoopback,
    CanOptions,
    CanRxSource,
    CanTimeoutSource,
    CanTimestampSource,
    CanTiming,
    CanTxEventType,
    CanTxFrame,
    CanUnmatchedPolicy,
)
from ...drivers.crg import CrgPeripheral
from ...instruments.can_boxes.models import CanBusConfig as PeerBusConfig
from ...instruments.can_boxes.models import CanFrame as PeerFrame
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import (
    FD_LENGTHS,
    PATTERN_A,
    PATTERN_B,
    TIMEOUT_S,
    dedicated_loopback_ram,
    fifo_loopback_ram,
    filter_loopback_ram,
    loopback_ram,
    pattern,
    phase_timing,
    rx_buffer_boundary_indices,
    tx_event_loopback_ram,
    tx_order_ram,
)

pytestmark = [pytest.mark.hardware, pytest.mark.ip("can")]


# =============================================================================
# Message RAM完整遍历
# =============================================================================
# Message RAM完整遍历
# =============================================================================


# 测试 Feature：
# CAN Message RAM固定模式、地址别名与March C-读写；重建后正常收发。
#
# 测试方法：
# 1. 显式调用 can_handle.reset()，进入 INIT 仅遍历芯片映射允许的 Message RAM 区域。
# 2. 依次写入 0x5A5A5A5A、0xA5A5A5A5 及地址异或模式并读回核对。
# 3. 执行 March C- 六阶段自测。
# 4. 保持 RAM 状态重建内部回环并发送单帧验证恢复。
#
# 通过条件：
# 1. 所有受测字的各阶段读回均匹配独立 Expected。
# 2. RAM 测试后 TX 完成、RX 数据完全一致。
def test_can_p1_016_message_ram_march(can0) -> None:
    # 1）复位
    can_handle = can0
    can_handle.reset()

    # 2）IP 配置与切片准备
    support = can_handle.support
    regions = support.mapping.CAN_RAM_TEST_REGIONS[support.handle]
    word_bytes, batch_words = 4, 64
    chunks = []
    for offset, length in regions:
        assert offset % word_bytes == length % word_bytes == 0 and length > 0
        chunks.extend(
            (address, min(batch_words, (offset + length - address) // word_bytes))
            for address in range(offset, offset + length, batch_words * word_bytes)
        )

    can_handle.initializing_set(True)
    can_handle.wait_initializing(True, timeout_s=TIMEOUT_S)

    # 3）获取并判断结果：固定模式与地址别名测试
    for constant in (0x5A5A5A5A, 0xA5A5A5A5, None):
        for offset, count in chunks:
            values = tuple(
                constant if constant is not None else ((offset // word_bytes + idx) ^ 0x5A5A5A5A)
                for idx in range(count)
            )
            can_handle.ram_words_write(offset, values, timeout_s=TIMEOUT_S)

        for offset, count in chunks:
            expected = tuple(
                constant if constant is not None else ((offset // word_bytes + idx) ^ 0x5A5A5A5A)
                for idx in range(count)
            )
            actual = can_handle.ram_words_read(offset, count, timeout_s=TIMEOUT_S)
            assert actual == expected

    # March C- 六阶段测试 (w0 -> up_r0w1 -> up_r1w0 -> down_r0w1 -> down_r1w0 -> r0)
    for before, after, descending in (
        (None, 0, False),
        (0, 0xFFFFFFFF, False),
        (0xFFFFFFFF, 0, False),
        (0, 0xFFFFFFFF, True),
        (0xFFFFFFFF, 0, True),
        (0, None, False),
    ):
        for offset, count in reversed(chunks) if descending else chunks:
            if before is None:
                can_handle.ram_words_write(offset, (after,) * count, timeout_s=TIMEOUT_S)
            else:
                actual = (
                    can_handle.ram_words_read(offset, count, timeout_s=TIMEOUT_S)
                    if after is None
                    else can_handle.ram_words_exchange(offset, (after,) * count, descending=descending, timeout_s=TIMEOUT_S)
                )
                assert actual == (before,) * count

    # 4）重建回环验证 RAM 可用性（保持当前 RAM 内容不复位）
    can_handle.timing_set(CanTiming(
        phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    ))
    can_handle.options_set(CanOptions(False, False, False, False, False, True, False, 0, 0, 0))
    can_handle.ram_layout_set(loopback_ram(support))
    can_handle.filter_set(0, CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x123, 0x123), extended=False)
    can_handle.loopback_set(CanLoopback.INTERNAL)
    can_handle.bus_config_set(CanBusConfig(
        monitor=True, restricted=False, timestamp_divisor=1, timestamp_source=CanTimestampSource.DISABLED,
        timeout_source=CanTimeoutSource.CONTINUOUS, timeout_period=0, timeout_enabled=False,
        reject_remote_ext=True, reject_remote_std=True,
        unmatched_ext=CanUnmatchedPolicy.REJECT, unmatched_std=CanUnmatchedPolicy.REJECT,
    ))
    can_handle.initializing_set(False)
    can_handle.wait_initializing(False, timeout_s=TIMEOUT_S)

    can_handle.tx_write(0, CanTxFrame(0x123, CanFrameFlags.NONE, 8, 0, PATTERN_A))
    can_handle.tx_request(1)
    tx = can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)
    can_handle.wait_rx_available(0, timeout_s=TIMEOUT_S)
    received = can_handle.rx_read(CanRxSource.FIFO0)
    assert tx.completed & 1
    assert received.identifier == 0x123 and received.dlc == 8 and received.data == PATTERN_A
    can_handle.rx_fifo_ack(0, received.index)

# =============================================================================


# 测试 Feature：
# RX New/TX Complete中断的Line0/Line1投递、屏蔽、独立W1C及再次置位。
#
# 测试方法：
# 1. 显式调用 can_handle.reset()，配置内部/外部回环或 Normal 模式。
# 2. 配置中断引脚选通与使能，分别在 Line0/Line1 触发 TX/RX 事件。
# 3. 校验对应线路捕获，逐源 W1C 清除并验证第二笔数据仍正常触发。
#
# 通过条件：
# 1. 两个源都从指定物理线路实际投递，无未知中断或捕获Fault。
# 2. W1C 只清目标源，第二笔数据仍正确投递。
@pytest.mark.parametrize("mode", ("internal", "external", "normal"))
@pytest.mark.parametrize("tx_line", (0, 1))
def test_can_p1_011_irq_lines_and_clear(
    can0, can_irq_peer, mode, tx_line
) -> None:
    # 1）复位
    can_handle = can0
    can_handle.reset()

    # 2）IP 配置与激励准备
    support = can_handle.support
    sources = CanIrqSource.RX_FIFO0_NEW | CanIrqSource.TX_COMPLETE
    box = can_irq_peer[3] if can_irq_peer else None

    if box:
        _, gpio, pins, _ = can_irq_peer
        for number, function in pins:
            gpio.configure_signal(number, function, can_handle.instance_id)
        box.open()
        box.configure(PeerBusConfig(listen_only=False))
        box.clear()

    can_handle.initializing_set(True)
    can_handle.wait_initializing(True, timeout_s=TIMEOUT_S)
    can_handle.timing_set(CanTiming(
        phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    ))
    can_handle.options_set(CanOptions(
        fd_enabled=False, brs_enabled=False, automatic_retry=True, tx_pause=False, edge_filter=False,
        protocol_exception=True, tdc_enabled=False, tdc_offset_cycles=0, tdc_filter_cycles=0, ram_watchdog_cycles=0,
    ))
    can_handle.ram_layout_set(loopback_ram(support))
    can_handle.filter_set(0, CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x123, 0x321), extended=False)
    can_handle.loopback_set({
        "internal": CanLoopback.INTERNAL,
        "external": CanLoopback.EXTERNAL,
        "normal": CanLoopback.DISABLED,
    }[mode])
    can_handle.bus_config_set(CanBusConfig(
        monitor=mode == "internal", restricted=False, timestamp_divisor=1, timestamp_source=CanTimestampSource.DISABLED,
        timeout_source=CanTimeoutSource.CONTINUOUS, timeout_period=0, timeout_enabled=False,
        reject_remote_ext=True, reject_remote_std=True,
        unmatched_ext=CanUnmatchedPolicy.REJECT, unmatched_std=CanUnmatchedPolicy.REJECT,
    ))
    can_handle.tx_buffer_irq_set(0, True)
    can_handle.irq_line_select_set(sources, tx_line)
    can_handle.irq_mask_set(sources, False)
    can_handle.irq_clear(sources)
    can_handle.initializing_set(False)
    can_handle.wait_initializing(False, timeout_s=TIMEOUT_S)

    # 3）获取并判断结果：两次真实收发激励
    for payload in (PATTERN_A, PATTERN_B):
        can_handle.irq_clear(sources)
        can_handle.tx_write(0, CanTxFrame(0x123, CanFrameFlags.NONE, 8, 0, payload))
        can_handle.tx_request(1)
        tx = can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)
        assert tx.completed & 1

        if mode != "internal" and box:
            box.send(PeerFrame(0x123, payload), single_shot=True)

        can_handle.wait_rx_available(0, timeout_s=TIMEOUT_S)
        rx = can_handle.rx_read(CanRxSource.FIFO0)
        can_handle.rx_fifo_ack(0, rx.index)
        assert rx.identifier == 0x123 and rx.data == payload

        # 检查线路事件与 W1C 清零
        line_events = can_handle.irq_line_events_get()
        assert line_events[tx_line] & CanIrqSource.TX_COMPLETE
        can_handle.irq_clear(CanIrqSource.TX_COMPLETE)
        assert not (can_handle.irq_snapshot_get().raw_status & CanIrqSource.TX_COMPLETE)

FORMAT_NODES = (
    ("classic_std", CanFrameFlags(0)),
    ("classic_ext", CanFrameFlags.EXTENDED),
    ("fd_std", CanFrameFlags.FD),
    ("fd_ext", CanFrameFlags.FD | CanFrameFlags.EXTENDED),
    ("fd_brs_std", CanFrameFlags.FD | CanFrameFlags.BRS),
    ("fd_brs_ext", CanFrameFlags.FD | CanFrameFlags.BRS | CanFrameFlags.EXTENDED),
)

# Filter刺激完成后留给内部回环和硬件Message RAM更新的固定观察窗口。
FILTER_OBSERVATION_S = 0.1

# 标准Filter节点依次声明：名称、Filter列表、未匹配策略、输入ID、目标FIFO、Filter索引、High Priority。
STANDARD_FILTER_NODES = (
    (
        "range_below",
        (CanFilter(CanFilterType.RANGE, CanFilterAction.FIFO0, 0x120, 0x180),),
        CanUnmatchedPolicy.REJECT,
        0x11F,
        None,
        None,
        False,
    ),
    (
        "range_lower",
        (CanFilter(CanFilterType.RANGE, CanFilterAction.FIFO0, 0x120, 0x180),),
        CanUnmatchedPolicy.REJECT,
        0x120,
        0,
        0,
        False,
    ),
    (
        "range_middle",
        (CanFilter(CanFilterType.RANGE, CanFilterAction.FIFO0, 0x120, 0x180),),
        CanUnmatchedPolicy.REJECT,
        0x150,
        0,
        0,
        False,
    ),
    (
        "range_upper",
        (CanFilter(CanFilterType.RANGE, CanFilterAction.FIFO0, 0x120, 0x180),),
        CanUnmatchedPolicy.REJECT,
        0x180,
        0,
        0,
        False,
    ),
    (
        "range_above",
        (CanFilter(CanFilterType.RANGE, CanFilterAction.FIFO0, 0x120, 0x180),),
        CanUnmatchedPolicy.REJECT,
        0x181,
        None,
        None,
        False,
    ),
    (
        "dual_first",
        (CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x101, 0x110),),
        CanUnmatchedPolicy.REJECT,
        0x101,
        0,
        0,
        False,
    ),
    (
        "dual_second",
        (CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x101, 0x110),),
        CanUnmatchedPolicy.REJECT,
        0x110,
        0,
        0,
        False,
    ),
    (
        "dual_miss",
        (CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x101, 0x110),),
        CanUnmatchedPolicy.REJECT,
        0x111,
        None,
        None,
        False,
    ),
    (
        "mask_first",
        (CanFilter(CanFilterType.MASK, CanFilterAction.FIFO0, 0x400, 0x700),),
        CanUnmatchedPolicy.REJECT,
        0x400,
        0,
        0,
        False,
    ),
    (
        "mask_last",
        (CanFilter(CanFilterType.MASK, CanFilterAction.FIFO0, 0x400, 0x700),),
        CanUnmatchedPolicy.REJECT,
        0x4FF,
        0,
        0,
        False,
    ),
    (
        "mask_miss",
        (CanFilter(CanFilterType.MASK, CanFilterAction.FIFO0, 0x400, 0x700),),
        CanUnmatchedPolicy.REJECT,
        0x500,
        None,
        None,
        False,
    ),
    (
        "matched_fifo1",
        (CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO1, 0x220, 0x220),),
        CanUnmatchedPolicy.REJECT,
        0x220,
        1,
        0,
        False,
    ),
    (
        "matched_reject",
        (CanFilter(CanFilterType.DUAL, CanFilterAction.REJECT, 0x221, 0x221),),
        CanUnmatchedPolicy.RX0,
        0x221,
        None,
        None,
        False,
    ),
    (
        "unmatched_fifo0",
        (CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO1, 0x100, 0x100),),
        CanUnmatchedPolicy.RX0,
        0x200,
        0,
        None,
        False,
    ),
    (
        "unmatched_fifo1",
        (CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x100, 0x100),),
        CanUnmatchedPolicy.RX1,
        0x200,
        1,
        None,
        False,
    ),
    (
        "unmatched_reject",
        (CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x100, 0x100),),
        CanUnmatchedPolicy.REJECT,
        0x200,
        None,
        None,
        False,
    ),
    (
        "overlap_fifo0_first",
        (
            CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x123, 0x123),
            CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO1, 0x123, 0x123),
        ),
        CanUnmatchedPolicy.REJECT,
        0x123,
        0,
        0,
        False,
    ),
    (
        "overlap_fifo1_first",
        (
            CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO1, 0x123, 0x123),
            CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x123, 0x123),
        ),
        CanUnmatchedPolicy.REJECT,
        0x123,
        1,
        0,
        False,
    ),
    (
        "overlap_first_disabled",
        (
            CanFilter(CanFilterType.DISABLED, CanFilterAction.DISABLED, 0, 0),
            CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO1, 0x123, 0x123),
        ),
        CanUnmatchedPolicy.REJECT,
        0x123,
        1,
        1,
        False,
    ),
    (
        "high_priority_fifo0",
        (CanFilter(CanFilterType.DUAL, CanFilterAction.PRIORITY_FIFO0, 0x321, 0x321),),
        CanUnmatchedPolicy.REJECT,
        0x321,
        0,
        0,
        True,
    ),
)

# 扩展Filter节点依次声明：名称、Filter列表、XIDAM、未匹配策略、输入ID、目标FIFO、Filter索引、High Priority。
EXTENDED_FILTER_NODES = (
    (
        "range_below",
        (CanFilter(CanFilterType.RANGE, CanFilterAction.FIFO0, 0x120, 0x180),),
        0x1FFFFFFF,
        CanUnmatchedPolicy.REJECT,
        0x11F,
        None,
        None,
        False,
    ),
    (
        "range_lower",
        (CanFilter(CanFilterType.RANGE, CanFilterAction.FIFO0, 0x120, 0x180),),
        0x1FFFFFFF,
        CanUnmatchedPolicy.REJECT,
        0x120,
        0,
        0,
        False,
    ),
    (
        "range_middle",
        (CanFilter(CanFilterType.RANGE, CanFilterAction.FIFO0, 0x120, 0x180),),
        0x1FFFFFFF,
        CanUnmatchedPolicy.REJECT,
        0x150,
        0,
        0,
        False,
    ),
    (
        "range_upper",
        (CanFilter(CanFilterType.RANGE, CanFilterAction.FIFO0, 0x120, 0x180),),
        0x1FFFFFFF,
        CanUnmatchedPolicy.REJECT,
        0x180,
        0,
        0,
        False,
    ),
    (
        "range_above",
        (CanFilter(CanFilterType.RANGE, CanFilterAction.FIFO0, 0x120, 0x180),),
        0x1FFFFFFF,
        CanUnmatchedPolicy.REJECT,
        0x181,
        None,
        None,
        False,
    ),
    (
        "dual_first",
        (CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x101, 0x110),),
        0x1FFFFFFF,
        CanUnmatchedPolicy.REJECT,
        0x101,
        0,
        0,
        False,
    ),
    (
        "dual_second",
        (CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x101, 0x110),),
        0x1FFFFFFF,
        CanUnmatchedPolicy.REJECT,
        0x110,
        0,
        0,
        False,
    ),
    (
        "dual_miss",
        (CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x101, 0x110),),
        0x1FFFFFFF,
        CanUnmatchedPolicy.REJECT,
        0x111,
        None,
        None,
        False,
    ),
    (
        "mask_first",
        (CanFilter(CanFilterType.MASK, CanFilterAction.FIFO0, 0x400, 0x700),),
        0x1FFFFFFF,
        CanUnmatchedPolicy.REJECT,
        0x400,
        0,
        0,
        False,
    ),
    (
        "mask_last",
        (CanFilter(CanFilterType.MASK, CanFilterAction.FIFO0, 0x400, 0x700),),
        0x1FFFFFFF,
        CanUnmatchedPolicy.REJECT,
        0x4FF,
        0,
        0,
        False,
    ),
    (
        "mask_miss",
        (CanFilter(CanFilterType.MASK, CanFilterAction.FIFO0, 0x400, 0x700),),
        0x1FFFFFFF,
        CanUnmatchedPolicy.REJECT,
        0x500,
        None,
        None,
        False,
    ),
    *(
        (
            f"xidam_full_{identifier:03x}",
            (CanFilter(CanFilterType.RANGE, CanFilterAction.FIFO0, 0x120, 0x120),),
            0x1FFFFFFF,
            CanUnmatchedPolicy.REJECT,
            identifier,
            0 if identifier == 0x120 else None,
            0 if identifier == 0x120 else None,
            False,
        )
        for identifier in (0x120, 0x121, 0x12F, 0x130)
    ),
    *(
        (
            f"xidam_low_nibble_{identifier:03x}",
            (CanFilter(CanFilterType.RANGE, CanFilterAction.FIFO0, 0x120, 0x120),),
            0x1FFFFFF0,
            CanUnmatchedPolicy.REJECT,
            identifier,
            0 if identifier < 0x130 else None,
            0 if identifier < 0x130 else None,
            False,
        )
        for identifier in (0x120, 0x121, 0x12F, 0x130)
    ),
    *(
        (
            f"range_no_mask_{identifier:03x}",
            (CanFilter(CanFilterType.RANGE_NO_MASK, CanFilterAction.FIFO0, 0x120, 0x120),),
            0x1FFFFFF0,
            CanUnmatchedPolicy.REJECT,
            identifier,
            0 if identifier == 0x120 else None,
            0 if identifier == 0x120 else None,
            False,
        )
        for identifier in (0x120, 0x121, 0x12F, 0x130)
    ),
    (
        "high_id_first",
        (
            CanFilter(
                CanFilterType.DUAL,
                CanFilterAction.FIFO0,
                0x10000123,
                0x1FFFFFED,
            ),
        ),
        0x1FFFFFFF,
        CanUnmatchedPolicy.REJECT,
        0x10000123,
        0,
        0,
        False,
    ),
    (
        "high_id_second",
        (
            CanFilter(
                CanFilterType.DUAL,
                CanFilterAction.FIFO0,
                0x10000123,
                0x1FFFFFED,
            ),
        ),
        0x1FFFFFFF,
        CanUnmatchedPolicy.REJECT,
        0x1FFFFFED,
        0,
        0,
        False,
    ),
    (
        "high_id_low_alias_miss",
        (
            CanFilter(
                CanFilterType.DUAL,
                CanFilterAction.FIFO0,
                0x10000123,
                0x1FFFFFED,
            ),
        ),
        0x1FFFFFFF,
        CanUnmatchedPolicy.REJECT,
        0x123,
        None,
        None,
        False,
    ),
    (
        "matched_fifo1",
        (CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO1, 0x220, 0x220),),
        0x1FFFFFFF,
        CanUnmatchedPolicy.REJECT,
        0x220,
        1,
        0,
        False,
    ),
    (
        "matched_reject",
        (CanFilter(CanFilterType.DUAL, CanFilterAction.REJECT, 0x221, 0x221),),
        0x1FFFFFFF,
        CanUnmatchedPolicy.RX0,
        0x221,
        None,
        None,
        False,
    ),
    (
        "unmatched_fifo0",
        (CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO1, 0x100, 0x100),),
        0x1FFFFFFF,
        CanUnmatchedPolicy.RX0,
        0x200,
        0,
        None,
        False,
    ),
    (
        "unmatched_fifo1",
        (CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x100, 0x100),),
        0x1FFFFFFF,
        CanUnmatchedPolicy.RX1,
        0x200,
        1,
        None,
        False,
    ),
    (
        "unmatched_reject",
        (CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x100, 0x100),),
        0x1FFFFFFF,
        CanUnmatchedPolicy.REJECT,
        0x200,
        None,
        None,
        False,
    ),
    (
        "overlap_fifo0_first",
        (
            CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x123, 0x123),
            CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO1, 0x123, 0x123),
        ),
        0x1FFFFFFF,
        CanUnmatchedPolicy.REJECT,
        0x123,
        0,
        0,
        False,
    ),
    (
        "overlap_fifo1_first",
        (
            CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO1, 0x123, 0x123),
            CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x123, 0x123),
        ),
        0x1FFFFFFF,
        CanUnmatchedPolicy.REJECT,
        0x123,
        1,
        0,
        False,
    ),
    (
        "overlap_first_disabled",
        (
            CanFilter(CanFilterType.RANGE, CanFilterAction.DISABLED, 0, 0),
            CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO1, 0x123, 0x123),
        ),
        0x1FFFFFFF,
        CanUnmatchedPolicy.REJECT,
        0x123,
        1,
        1,
        False,
    ),
    (
        "high_priority_fifo0",
        (CanFilter(CanFilterType.DUAL, CanFilterAction.PRIORITY_FIFO0, 0x321, 0x321),),
        0x1FFFFFFF,
        CanUnmatchedPolicy.REJECT,
        0x321,
        0,
        0,
        True,
    ),
)

# =============================================================================


# 测试 Feature：
# Classic标准/扩展帧、FD/BRS、DLC到有效长度映射及ID上下边界。
#
# 测试方法：
# 1. 显式执行 can_handle.reset()，配置波特率、FD/BRS 选项与 64-byte 接收布局。
# 2. 内部回环遍历 16 种 DLC 及正反两组 Pattern 数据并发送。
# 3. 读取并 Ack 实际 RX 帧，校验元数据与有效字节。
#
# 通过条件：
# 1. 16 种 DLC、两种 Pattern 全部完成，元数据及有效字节完全一致。
# 2. 每帧 TX 完成，RX 恰有一帧，Ack 后为空且无 Lost。
@pytest.mark.parametrize("format_name,flags", FORMAT_NODES, ids=[node[0] for node in FORMAT_NODES])
@pytest.mark.parametrize("id_bound", ("minimum", "maximum"))
def test_can_p1_001_frame_formats(can0, format_name, flags, id_bound) -> None:
    # 1）复位
    can_handle = can0
    can_handle.reset()

    # 2）IP 配置
    support = can_handle.support
    extended = bool(flags & CanFrameFlags.EXTENDED)
    fd_enabled = bool(flags & CanFrameFlags.FD)
    identifier = (0x1FFFFFFF if extended else 0x7FF) if id_bound == "maximum" else 0

    can_handle.initializing_set(True)
    can_handle.wait_initializing(True, timeout_s=TIMEOUT_S)
    can_handle.timing_set(CanTiming(
        phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    ))
    can_handle.options_set(CanOptions(
        fd_enabled=fd_enabled,
        brs_enabled=bool(flags & CanFrameFlags.BRS),
        automatic_retry=True,
        tx_pause=False,
        edge_filter=False,
        protocol_exception=True,
        tdc_enabled=False,
        tdc_offset_cycles=0,
        tdc_filter_cycles=0,
        ram_watchdog_cycles=0,
    ))
    can_handle.ram_layout_set(loopback_ram(support, payload_bytes=64))
    can_handle.filter_set(0, CanFilter(CanFilterType.DISABLED, CanFilterAction.DISABLED, 0, 0), extended=False)
    can_handle.loopback_set(CanLoopback.INTERNAL)
    can_handle.bus_config_set(CanBusConfig(
        monitor=True, restricted=False, timestamp_divisor=1, timestamp_source=CanTimestampSource.INTERNAL,
        timeout_source=CanTimeoutSource.CONTINUOUS, timeout_period=0, timeout_enabled=False,
        reject_remote_ext=True, reject_remote_std=True,
        unmatched_ext=CanUnmatchedPolicy.RX0 if extended else CanUnmatchedPolicy.REJECT,
        unmatched_std=CanUnmatchedPolicy.REJECT if extended else CanUnmatchedPolicy.RX0,
    ))
    can_handle.initializing_set(False)
    can_handle.wait_initializing(False, timeout_s=TIMEOUT_S)

    # 3）获取并判断结果：遍历 16 种 DLC 规格及正反两组数据
    for dlc in range(16):
        length = FD_LENGTHS[dlc] if fd_enabled else min(dlc, 8)
        for inverse in (False, True):
            payload = pattern(length, inverse=inverse)
            can_handle.tx_write(0, CanTxFrame(identifier, flags, dlc, 0, payload))
            can_handle.tx_request(1)
            tx = can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)
            ready = can_handle.wait_rx_available(0, timeout_s=TIMEOUT_S)
            actual = can_handle.rx_read(CanRxSource.FIFO0)
            can_handle.rx_fifo_ack(0, actual.index)
            after = can_handle.rx_fifo_status_get(0)

            assert actual.identifier == identifier and actual.flags == flags
            assert actual.dlc == dlc and len(actual.data) == length
            assert actual.data == payload
            assert tx.completed & 1 and ready.fill == 1 and after.fill == 0
            assert not (ready.lost or after.lost)


# =============================================================================
# ID过滤与Remote策略
# =============================================================================


# 测试 Feature：
# CAN标准ID Range、Dual、Mask、首匹配、路由、未匹配策略及High Priority状态。
#
# 测试方法：
# 1. 显式执行 can_handle.reset()，配置两个深度4的RX FIFO及内部回环。
# 2. 下发Filter列表和未匹配策略，发送Classic标准帧。
# 3. 读取FIFO与RX帧，校验路由判定；High Priority节点另检验状态和IRQ。
#
# 通过条件：
# 1. 预期FIFO收到一帧，拒绝节点两个FIFO均为空，ID、数据及Filter索引正确。
# 2. 重叠规则只命中首个启用项；High Priority状态和IRQ指向同一Filter。
@pytest.mark.parametrize(
    "node_name,filters,unmatched_policy,identifier,expected_fifo,expected_filter,high_priority",
    STANDARD_FILTER_NODES,
    ids=[node[0] for node in STANDARD_FILTER_NODES],
)
def test_can_p1_002_standard_id_filter_and_routing(
    can0,
    node_name,
    filters,
    unmatched_policy,
    identifier,
    expected_fifo,
    expected_filter,
    high_priority,
) -> None:
    # 1）复位
    can_handle = can0
    can_handle.reset()

    # 2）IP 配置与激励准备
    support = can_handle.support
    payload_bytes = 8
    sequence = identifier & 0xFF
    payload = bytes((sequence,)) + pattern(payload_bytes - 1)

    can_handle.initializing_set(True)
    can_handle.wait_initializing(True, timeout_s=TIMEOUT_S)
    can_handle.timing_set(CanTiming(
        phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    ))
    can_handle.options_set(CanOptions(
        fd_enabled=False, brs_enabled=False, automatic_retry=True, tx_pause=False, edge_filter=False,
        protocol_exception=True, tdc_enabled=False, tdc_offset_cycles=0, tdc_filter_cycles=0, ram_watchdog_cycles=0,
    ))
    can_handle.ram_layout_set(filter_loopback_ram(support, standard_count=len(filters), extended_count=0))
    for filter_index, filter_config in enumerate(filters):
        can_handle.filter_set(filter_index, filter_config, extended=False)
    can_handle.loopback_set(CanLoopback.INTERNAL)
    can_handle.bus_config_set(CanBusConfig(
        monitor=True, restricted=False, timestamp_divisor=1, timestamp_source=CanTimestampSource.INTERNAL,
        timeout_source=CanTimeoutSource.CONTINUOUS, timeout_period=0, timeout_enabled=False,
        reject_remote_ext=True, reject_remote_std=True,
        unmatched_ext=CanUnmatchedPolicy.REJECT, unmatched_std=unmatched_policy,
    ))
    if high_priority:
        can_handle.irq_mask_set(CanIrqSource.HIGH_PRIORITY, False)
        can_handle.irq_clear(CanIrqSource.HIGH_PRIORITY)
    can_handle.initializing_set(False)
    can_handle.wait_initializing(False, timeout_s=TIMEOUT_S)

    # 3）获取并判断结果
    can_handle.tx_write(0, CanTxFrame(identifier, CanFrameFlags.NONE, payload_bytes, sequence, payload))
    can_handle.tx_request(1)
    can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)
    sleep(FILTER_OBSERVATION_S)

    fifo0 = can_handle.rx_fifo_status_get(0)
    fifo1 = can_handle.rx_fifo_status_get(1)
    if expected_fifo is None:
        assert fifo0.fill == 0 and fifo1.fill == 0
    else:
        assert fifo0.fill == (1 if expected_fifo == 0 else 0)
        assert fifo1.fill == (1 if expected_fifo == 1 else 0)
        actual_frame = can_handle.rx_read(CanRxSource.FIFO0 if expected_fifo == 0 else CanRxSource.FIFO1)
        can_handle.rx_fifo_ack(expected_fifo, actual_frame.index)
        assert actual_frame.identifier == identifier and actual_frame.data == payload
        assert actual_frame.nonmatching == (expected_filter is None and expected_fifo is not None)
        if expected_filter is not None:
            assert actual_frame.filter_index == expected_filter

    if high_priority:
        high_priority_status = can_handle.high_priority_status_get()
        assert high_priority_status.storage == CanHighPriorityStorage.FIFO0
        assert high_priority_status.filter_index == expected_filter
        assert not high_priority_status.filter_extended
        assert can_handle.irq_snapshot_get().raw_status & CanIrqSource.HIGH_PRIORITY


# 测试 Feature：
# CAN扩展ID Range、Dual、Mask、XIDAM、29-bit比较、首匹配、路由及High Priority状态。
#
# 测试方法：
# 1. 显式调用 can_handle.reset()，配置扩展Filter、XIDAM及两个RX FIFO。
# 2. 发送29-bit Classic扩展帧，等待TX完成。
# 3. 校验对应FIFO接收、首匹配索引及High Priority状态。
#
# 通过条件：
# 1. 路由、Filter索引与独立Expected一致，29-bit高位不混淆。
# 2. 目标FIFO恰收到一帧，非目标FIFO为空；High Priority索引正确。
@pytest.mark.parametrize(
    "node_name,filters,extended_mask,unmatched_policy,identifier,expected_fifo,expected_filter,high_priority",
    EXTENDED_FILTER_NODES,
    ids=[node[0] for node in EXTENDED_FILTER_NODES],
)
def test_can_p1_003_extended_id_filter_and_mask(
    can0,
    node_name,
    filters,
    extended_mask,
    unmatched_policy,
    identifier,
    expected_fifo,
    expected_filter,
    high_priority,
) -> None:
    # 1）复位
    can_handle = can0
    can_handle.reset()

    # 2）IP 配置与激励准备
    support = can_handle.support
    payload_bytes = 8
    sequence = identifier & 0xFF
    payload = bytes((sequence,)) + pattern(payload_bytes - 1)

    can_handle.initializing_set(True)
    can_handle.wait_initializing(True, timeout_s=TIMEOUT_S)
    can_handle.timing_set(CanTiming(
        phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    ))
    can_handle.options_set(CanOptions(
        fd_enabled=False, brs_enabled=False, automatic_retry=True, tx_pause=False, edge_filter=False,
        protocol_exception=True, tdc_enabled=False, tdc_offset_cycles=0, tdc_filter_cycles=0, ram_watchdog_cycles=0,
    ))
    can_handle.ram_layout_set(filter_loopback_ram(support, standard_count=0, extended_count=len(filters)))
    for filter_index, filter_config in enumerate(filters):
        can_handle.filter_set(filter_index, filter_config, extended=True)
    can_handle.extended_mask_set(extended_mask)
    can_handle.loopback_set(CanLoopback.INTERNAL)
    can_handle.bus_config_set(CanBusConfig(
        monitor=True, restricted=False, timestamp_divisor=1, timestamp_source=CanTimestampSource.INTERNAL,
        timeout_source=CanTimeoutSource.CONTINUOUS, timeout_period=0, timeout_enabled=False,
        reject_remote_ext=True, reject_remote_std=True,
        unmatched_ext=unmatched_policy, unmatched_std=CanUnmatchedPolicy.REJECT,
    ))
    if high_priority:
        can_handle.irq_mask_set(CanIrqSource.HIGH_PRIORITY, False)
        can_handle.irq_clear(CanIrqSource.HIGH_PRIORITY)
    can_handle.initializing_set(False)
    can_handle.wait_initializing(False, timeout_s=TIMEOUT_S)

    # 3）获取并判断结果
    can_handle.tx_write(0, CanTxFrame(identifier, CanFrameFlags.EXTENDED, payload_bytes, sequence, payload))
    can_handle.tx_request(1)
    can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)
    sleep(FILTER_OBSERVATION_S)

    fifo0 = can_handle.rx_fifo_status_get(0)
    fifo1 = can_handle.rx_fifo_status_get(1)
    if expected_fifo is None:
        assert fifo0.fill == 0 and fifo1.fill == 0
    else:
        assert fifo0.fill == (1 if expected_fifo == 0 else 0)
        assert fifo1.fill == (1 if expected_fifo == 1 else 0)
        actual_frame = can_handle.rx_read(CanRxSource.FIFO0 if expected_fifo == 0 else CanRxSource.FIFO1)
        can_handle.rx_fifo_ack(expected_fifo, actual_frame.index)
        assert actual_frame.identifier == identifier and actual_frame.data == payload
        assert actual_frame.flags == CanFrameFlags.EXTENDED
        assert actual_frame.nonmatching == (expected_filter is None and expected_fifo is not None)
        if expected_filter is not None:
            assert actual_frame.filter_index == expected_filter

    if high_priority:
        high_priority_status = can_handle.high_priority_status_get()
        assert high_priority_status.storage == CanHighPriorityStorage.FIFO0
        assert high_priority_status.filter_index == expected_filter
        assert high_priority_status.filter_extended
        assert can_handle.irq_snapshot_get().raw_status & CanIrqSource.HIGH_PRIORITY


# 测试 Feature：
# Classic标准/扩展Remote帧的允许、拒绝及同ID数据帧恢复。
#
# 测试方法：
# 1. 显式执行 can_handle.reset()，允许Remote并核对接收元数据。
# 2. 切换为拒绝同类型Remote，等待TX完成及固定观察窗口并确认FIFO无接收。
# 3. 保持拒绝Remote策略，发送同ID 8-byte数据帧验证正常接收。
#
# 通过条件：
# 1. 允许阶段收到RTR=1、原始DLC正确且payload为空的Remote帧。
# 2. 拒绝阶段FIFO无新增，而随后同ID数据帧完整接收。
@pytest.mark.parametrize("extended", (False, True), ids=("standard", "extended"))
@pytest.mark.parametrize("dlc", (0, 8), ids=("dlc0", "dlc8"))
def test_can_p1_004_remote_frame_policy(can0, extended, dlc) -> None:
    # 1）复位
    can_handle = can0
    can_handle.reset()

    # 2）IP 配置与激励（阶段一：允许 Remote 接收）
    support = can_handle.support
    identifier = 0x123
    frame_flags = CanFrameFlags.REMOTE | (CanFrameFlags.EXTENDED if extended else CanFrameFlags.NONE)
    recovery_flags = CanFrameFlags.EXTENDED if extended else CanFrameFlags.NONE
    recovery_payload = pattern(8)
    timing = CanTiming(
        phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    )
    can_handle.initializing_set(True)
    can_handle.wait_initializing(True, timeout_s=TIMEOUT_S)
    can_handle.timing_set(timing)
    can_handle.options_set(CanOptions(
        fd_enabled=False, brs_enabled=False, automatic_retry=True, tx_pause=False, edge_filter=False,
        protocol_exception=True, tdc_enabled=False, tdc_offset_cycles=0, tdc_filter_cycles=0, ram_watchdog_cycles=0,
    ))
    can_handle.ram_layout_set(filter_loopback_ram(support, standard_count=0 if extended else 1, extended_count=1 if extended else 0))
    can_handle.filter_set(0, CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, identifier, identifier), extended=extended)
    if extended:
        can_handle.extended_mask_set(0x1FFFFFFF)
    can_handle.loopback_set(CanLoopback.INTERNAL)
    can_handle.bus_config_set(CanBusConfig(
        monitor=True, restricted=False, timestamp_divisor=1, timestamp_source=CanTimestampSource.INTERNAL,
        timeout_source=CanTimeoutSource.CONTINUOUS, timeout_period=0, timeout_enabled=False,
        reject_remote_ext=False, reject_remote_std=False, unmatched_ext=CanUnmatchedPolicy.REJECT, unmatched_std=CanUnmatchedPolicy.REJECT,
    ))
    can_handle.initializing_set(False)
    can_handle.wait_initializing(False, timeout_s=TIMEOUT_S)

    # 允许刺激：Remote保留原始DLC，无payload
    can_handle.tx_write(0, CanTxFrame(identifier, frame_flags, dlc, 1, b""))
    can_handle.tx_request(1)
    can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)
    can_handle.wait_rx_available(0, timeout_s=TIMEOUT_S)
    remote_frame = can_handle.rx_read(CanRxSource.FIFO0)
    can_handle.rx_fifo_ack(0, remote_frame.index)
    assert remote_frame.identifier == identifier and remote_frame.flags == frame_flags
    assert remote_frame.dlc == dlc and remote_frame.data == b""

    # 3）阶段二：切换为拒绝 Remote 并验证同 ID 数据帧恢复
    can_handle.initializing_set(True)
    can_handle.wait_initializing(True, timeout_s=TIMEOUT_S)
    can_handle.bus_config_set(CanBusConfig(
        monitor=True, restricted=False, timestamp_divisor=1, timestamp_source=CanTimestampSource.INTERNAL,
        timeout_source=CanTimeoutSource.CONTINUOUS, timeout_period=0, timeout_enabled=False,
        reject_remote_ext=extended, reject_remote_std=not extended, unmatched_ext=CanUnmatchedPolicy.REJECT, unmatched_std=CanUnmatchedPolicy.REJECT,
    ))
    can_handle.initializing_set(False)
    can_handle.wait_initializing(False, timeout_s=TIMEOUT_S)

    # 拒绝验证：发送 Remote 确认被拒
    can_handle.tx_write(0, CanTxFrame(identifier, frame_flags, dlc, 2, b""))
    can_handle.tx_request(1)
    can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)
    sleep(FILTER_OBSERVATION_S)
    rejected_status = can_handle.rx_fifo_status_get(0)
    assert rejected_status.fill == 0 and not rejected_status.lost

    # 恢复验证：发送同 ID 数据帧确认正常接收
    can_handle.tx_write(0, CanTxFrame(identifier, recovery_flags, 8, 3, recovery_payload))
    can_handle.tx_request(1)
    can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)
    can_handle.wait_rx_available(0, timeout_s=TIMEOUT_S)
    recovery_frame = can_handle.rx_read(CanRxSource.FIFO0)
    can_handle.rx_fifo_ack(0, recovery_frame.index)
    assert recovery_frame.identifier == identifier and recovery_frame.flags == recovery_flags
    assert recovery_frame.dlc == 8 and recovery_frame.data == recovery_payload

# =============================================================================
# RX FIFO与Dedicated Buffer
# =============================================================================


# 测试 Feature：
# CAN RX FIFO0/1的新消息、水位、满状态、Get/Put索引环回及顺序保持。
#
# 测试方法：
# 1. 显式调用 can_handle.reset()，配置深度4、水位2及内部回环。
# 2. 分别发送1、2、4帧，检查New、Watermark与Full边界及对应IRQ。
# 3. 先读取Ack两帧，再发送两帧触发索引环回，排空后验证顺序与空状态。
#
# 通过条件：
# 1. FILL依次达到1、2、4，Watermark在2时触发，Full在4时置位。
# 2. 6帧数据顺序与环绕索引完全符合预期，无Lost且最终清空。
@pytest.mark.parametrize("fifo", (0, 1), ids=("fifo0", "fifo1"))
def test_can_p1_005_rx_fifo_watermark_full_and_wrap(can0, fifo) -> None:
    # 1）复位
    can_handle = can0
    can_handle.reset()

    # 2）IP 配置与激励准备
    support = can_handle.support
    fifo_depth = 4
    fifo_watermark = 2
    payload_bytes = 8
    identifier = 0x245 + fifo
    source = CanRxSource.FIFO0 if fifo == 0 else CanRxSource.FIFO1
    action = CanFilterAction.FIFO0 if fifo == 0 else CanFilterAction.FIFO1
    irq_new = CanIrqSource.RX_FIFO0_NEW if fifo == 0 else CanIrqSource.RX_FIFO1_NEW
    irq_watermark = CanIrqSource.RX_FIFO0_WATERMARK if fifo == 0 else CanIrqSource.RX_FIFO1_WATERMARK
    irq_full = CanIrqSource.RX_FIFO0_FULL if fifo == 0 else CanIrqSource.RX_FIFO1_FULL
    tracked_irq = irq_new | irq_watermark | irq_full

    can_handle.initializing_set(True)
    can_handle.wait_initializing(True, timeout_s=TIMEOUT_S)
    can_handle.timing_set(CanTiming(
        phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    ))
    can_handle.options_set(CanOptions(
        fd_enabled=False, brs_enabled=False, automatic_retry=True, tx_pause=False, edge_filter=False,
        protocol_exception=True, tdc_enabled=False, tdc_offset_cycles=0, tdc_filter_cycles=0, ram_watchdog_cycles=0,
    ))
    can_handle.ram_layout_set(fifo_loopback_ram(support, fifo=fifo, watermark=fifo_watermark, overwrite=False))
    can_handle.filter_set(0, CanFilter(CanFilterType.DUAL, action, identifier, identifier), extended=False)
    can_handle.loopback_set(CanLoopback.INTERNAL)
    can_handle.bus_config_set(CanBusConfig(
        monitor=True, restricted=False, timestamp_divisor=1, timestamp_source=CanTimestampSource.INTERNAL,
        timeout_source=CanTimeoutSource.CONTINUOUS, timeout_period=0, timeout_enabled=False,
        reject_remote_ext=True, reject_remote_std=True,
        unmatched_ext=CanUnmatchedPolicy.REJECT, unmatched_std=CanUnmatchedPolicy.REJECT,
    ))
    can_handle.irq_mask_set(tracked_irq, False)
    can_handle.irq_clear(tracked_irq)
    can_handle.initializing_set(False)
    can_handle.wait_initializing(False, timeout_s=TIMEOUT_S)

    # 3）获取并判断结果：阶段激励与环回验证
    # 帧 0：到达 New
    can_handle.tx_write(0, CanTxFrame(identifier, CanFrameFlags.NONE, payload_bytes, 0, bytes((0,)) + pattern(payload_bytes - 1)))
    can_handle.tx_request(1)
    can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)
    first = can_handle.wait_rx_available(fifo, minimum=1, timeout_s=TIMEOUT_S)
    first_irq = can_handle.irq_snapshot_get().raw_status
    assert first.fill == 1 and not first.full and not first.lost
    assert first_irq & tracked_irq == irq_new
    can_handle.irq_clear(tracked_irq)

    # 帧 1：跨过水位线 2
    can_handle.tx_write(0, CanTxFrame(identifier, CanFrameFlags.NONE, payload_bytes, 1, bytes((1,)) + pattern(payload_bytes - 1, inverse=True)))
    can_handle.tx_request(1)
    can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)
    second = can_handle.wait_rx_available(fifo, minimum=2, timeout_s=TIMEOUT_S)
    second_irq = can_handle.irq_snapshot_get().raw_status
    assert second.fill == 2 and not second.full and not second.lost
    assert second_irq & tracked_irq == irq_new | irq_watermark
    can_handle.irq_clear(tracked_irq)

    # 帧 2、3：写满深度 4
    for seq in (2, 3):
        can_handle.tx_write(0, CanTxFrame(identifier, CanFrameFlags.NONE, payload_bytes, seq, bytes((seq,)) + pattern(payload_bytes - 1, inverse=bool(seq & 1))))
        can_handle.tx_request(1)
        can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)
    full = can_handle.wait_rx_available(fifo, minimum=4, timeout_s=TIMEOUT_S)
    full_irq = can_handle.irq_snapshot_get().raw_status
    assert full.fill == fifo_depth and full.full and not full.lost
    assert full_irq & tracked_irq & irq_full
    can_handle.irq_clear(tracked_irq)

    # 读出前两帧以释放槽位
    actual_sequences = []
    actual_indices = []
    for expected_seq in (0, 1):
        rec = can_handle.rx_read(source)
        actual_sequences.append(rec.data[0])
        actual_indices.append(rec.index)
        can_handle.rx_fifo_ack(fifo, rec.index)
        assert rec.identifier == identifier and rec.data[0] == expected_seq

    # 写入帧 4、5 触发 Put 索引环绕
    for seq in (4, 5):
        can_handle.tx_write(0, CanTxFrame(identifier, CanFrameFlags.NONE, payload_bytes, seq, bytes((seq,)) + pattern(payload_bytes - 1, inverse=bool(seq & 1))))
        can_handle.tx_request(1)
        can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)

    # 排空读出剩余四帧
    for expected_seq in (2, 3, 4, 5):
        rec = can_handle.rx_read(source)
        actual_sequences.append(rec.data[0])
        actual_indices.append(rec.index)
        can_handle.rx_fifo_ack(fifo, rec.index)
        assert rec.identifier == identifier and rec.data[0] == expected_seq

    final = can_handle.rx_fifo_status_get(fifo)
    assert actual_sequences == list(range(6))
    assert actual_indices == [0, 1, 2, 3, 0, 1]
    assert final.fill == 0 and not final.full and not final.lost


# 测试 Feature：
# CAN RX FIFO0/1满后的Blocking与Overwrite数据保留策略及恢复能力。
#
# 测试方法：
# 1. 显式调用 can_handle.reset()，配置深度4并顺序发送5帧。
# 2. 满后读取4个实际帧；Blocking保留0～3，Overwrite保留1～4。
# 3. 排空后发送第6帧（序号5），验证FIFO恢复正常接收。
#
# 通过条件：
# 1. 保留序列准确，Blocking报告Lost且中断触发，Overwrite覆盖旧帧。
# 2. 恢复帧数据正确，最终FIFO清空。
@pytest.mark.parametrize("fifo", (0, 1), ids=("fifo0", "fifo1"))
@pytest.mark.parametrize("overwrite", (False, True), ids=("blocking", "overwrite"))
def test_can_p1_006_rx_fifo_blocking_and_overwrite(can0, fifo, overwrite) -> None:
    # 1）复位
    can_handle = can0
    can_handle.reset()

    # 2）IP 配置与激励
    support = can_handle.support
    fifo_depth = 4
    payload_bytes = 8
    identifier = 0x255 + fifo
    source = CanRxSource.FIFO0 if fifo == 0 else CanRxSource.FIFO1
    action = CanFilterAction.FIFO0 if fifo == 0 else CanFilterAction.FIFO1
    irq_lost = CanIrqSource.RX_FIFO0_LOST if fifo == 0 else CanIrqSource.RX_FIFO1_LOST
    expected_sequences = [1, 2, 3, 4] if overwrite else [0, 1, 2, 3]

    can_handle.initializing_set(True)
    can_handle.wait_initializing(True, timeout_s=TIMEOUT_S)
    can_handle.timing_set(CanTiming(
        phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    ))
    can_handle.options_set(CanOptions(
        fd_enabled=False, brs_enabled=False, automatic_retry=True, tx_pause=False, edge_filter=False,
        protocol_exception=True, tdc_enabled=False, tdc_offset_cycles=0, tdc_filter_cycles=0, ram_watchdog_cycles=0,
    ))
    can_handle.ram_layout_set(fifo_loopback_ram(support, fifo=fifo, watermark=0, overwrite=overwrite))
    can_handle.filter_set(0, CanFilter(CanFilterType.DUAL, action, identifier, identifier), extended=False)
    can_handle.loopback_set(CanLoopback.INTERNAL)
    can_handle.bus_config_set(CanBusConfig(
        monitor=True, restricted=False, timestamp_divisor=1, timestamp_source=CanTimestampSource.INTERNAL,
        timeout_source=CanTimeoutSource.CONTINUOUS, timeout_period=0, timeout_enabled=False,
        reject_remote_ext=True, reject_remote_std=True,
        unmatched_ext=CanUnmatchedPolicy.REJECT, unmatched_std=CanUnmatchedPolicy.REJECT,
    ))
    can_handle.irq_mask_set(irq_lost, False)
    can_handle.irq_clear(irq_lost)
    can_handle.initializing_set(False)
    can_handle.wait_initializing(False, timeout_s=TIMEOUT_S)

    # 连续发送 5 帧填满并溢出
    for seq in range(5):
        can_handle.tx_write(0, CanTxFrame(identifier, CanFrameFlags.NONE, payload_bytes, seq, bytes((seq,)) + pattern(payload_bytes - 1, inverse=bool(seq & 1))))
        can_handle.tx_request(1)
        can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)

    # 3）获取并判断结果
    overflow = can_handle.rx_fifo_status_get(fifo)
    overflow_irq = can_handle.irq_snapshot_get().raw_status
    assert overflow.fill == fifo_depth and overflow.full
    if not overwrite:
        assert overflow.lost and overflow_irq & irq_lost

    actual_sequences = []
    for expected_seq in expected_sequences:
        rec = can_handle.rx_read(source)
        actual_sequences.append(rec.data[0])
        can_handle.rx_fifo_ack(fifo, rec.index)
        assert rec.identifier == identifier and rec.data[0] == expected_seq
    assert actual_sequences == expected_sequences

    # 恢复验证：清空后发送恢复帧 5
    can_handle.irq_clear(irq_lost)
    recovery_payload = bytes((5,)) + pattern(payload_bytes - 1, inverse=True)
    can_handle.tx_write(0, CanTxFrame(identifier, CanFrameFlags.NONE, payload_bytes, 5, recovery_payload))
    can_handle.tx_request(1)
    can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)
    can_handle.wait_rx_available(fifo, timeout_s=TIMEOUT_S)
    recovered = can_handle.rx_read(source)
    can_handle.rx_fifo_ack(fifo, recovered.index)
    assert recovered.identifier == identifier and recovered.data == recovery_payload

    final = can_handle.rx_fifo_status_get(fifo)
    assert final.fill == 0 and not final.full and not final.lost


# 测试 Feature：
# CAN Dedicated RX Buffer定向接收、64-bit New Data位图边界、独立清除与再次置位。
#
# 测试方法：
# 1. 显式调用 can_handle.reset()，选择有效边界 Buffer 0、31、32、63 配置唯一标准ID过滤器。
# 2. 发送并读取各 Buffer，确认 New Data 位图置位且 FIFO 保持为空。
# 3. 独立清除位图后向 Buffer 0 重发新数据，验证位图与内容再次更新。
#
# 通过条件：
# 1. 每个目标 Buffer 数据准确，相邻 Buffer 无误接收。
# 2. 低/高 32-bit 位图均能独立置位、清除并再次置位。
def test_can_p1_007_dedicated_rx_buffer_boundaries(can0) -> None:
    # 1）复位
    can_handle = can0
    can_handle.reset()

    # 2）IP 配置与激励准备
    support = can_handle.support
    payload_bytes = 8
    indices = rx_buffer_boundary_indices(support.ram_limits)
    identifiers = {index: 0x300 + position for position, index in enumerate(indices)}
    expected_low = sum(1 << index for index in indices if index < 32)
    expected_high = sum(1 << (index - 32) for index in indices if index >= 32)

    can_handle.initializing_set(True)
    can_handle.wait_initializing(True, timeout_s=TIMEOUT_S)
    can_handle.timing_set(CanTiming(
        phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    ))
    can_handle.options_set(CanOptions(
        fd_enabled=False, brs_enabled=False, automatic_retry=True, tx_pause=False, edge_filter=False,
        protocol_exception=True, tdc_enabled=False, tdc_offset_cycles=0, tdc_filter_cycles=0, ram_watchdog_cycles=0,
    ))
    can_handle.ram_layout_set(dedicated_loopback_ram(support, filter_count=len(indices)))
    for filter_index, buffer_index in enumerate(indices):
        can_handle.filter_set(filter_index, CanFilter(CanFilterType.RANGE, CanFilterAction.BUFFER, identifiers[buffer_index], 0, buffer_index), extended=False)
    can_handle.loopback_set(CanLoopback.INTERNAL)
    can_handle.bus_config_set(CanBusConfig(
        monitor=True, restricted=False, timestamp_divisor=1, timestamp_source=CanTimestampSource.INTERNAL,
        timeout_source=CanTimeoutSource.CONTINUOUS, timeout_period=0, timeout_enabled=False,
        reject_remote_ext=True, reject_remote_std=True,
        unmatched_ext=CanUnmatchedPolicy.REJECT, unmatched_std=CanUnmatchedPolicy.REJECT,
    ))
    can_handle.initializing_set(False)
    can_handle.wait_initializing(False, timeout_s=TIMEOUT_S)

    # 3）获取并判断结果：逐个发送并校验 New Data 边界
    for seq, buf_idx in enumerate(indices):
        payload = bytes((buf_idx, seq)) + pattern(payload_bytes - 2, inverse=bool(seq & 1))
        can_handle.tx_write(0, CanTxFrame(identifiers[buf_idx], CanFrameFlags.NONE, payload_bytes, seq, payload))
        can_handle.tx_request(1)
        can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)

    all_set = can_handle.rx_buffer_status_get()
    assert all_set.low == expected_low and all_set.high == expected_high
    assert can_handle.rx_fifo_status_get(0).fill == 0

    # 读出各 Buffer 帧内容验证
    for seq, buf_idx in enumerate(indices):
        actual = can_handle.rx_read(CanRxSource.BUFFER, buf_idx)
        expected = bytes((buf_idx, seq)) + pattern(payload_bytes - 2, inverse=bool(seq & 1))
        assert actual.index == buf_idx and actual.identifier == identifiers[buf_idx]
        assert actual.data == expected

    # 独立清除某一项，确认其余项保持
    iso_idx = indices[1] if len(indices) > 1 else indices[0]
    iso_low = 1 << iso_idx if iso_idx < 32 else 0
    iso_high = 1 << (iso_idx - 32) if iso_idx >= 32 else 0
    can_handle.rx_buffer_ack(iso_low, iso_high)
    after_one = can_handle.rx_buffer_status_get()
    assert after_one.low == expected_low & ~iso_low and after_one.high == expected_high & ~iso_high

    # 全量清空
    can_handle.rx_buffer_ack(expected_low, expected_high)
    cleared = can_handle.rx_buffer_status_get()
    assert cleared.low == 0 and cleared.high == 0

    # 再次置位验证
    first_idx = indices[0]
    rec_payload = bytes((first_idx, 0xA5)) + pattern(payload_bytes - 2, inverse=True)
    can_handle.tx_write(0, CanTxFrame(identifiers[first_idx], CanFrameFlags.NONE, payload_bytes, 0xA5, rec_payload))
    can_handle.tx_request(1)
    can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)
    rep_status = can_handle.rx_buffer_status_get()
    rep_frame = can_handle.rx_read(CanRxSource.BUFFER, first_idx)
    assert rep_status.low == (1 << first_idx if first_idx < 32 else 0)
    assert rep_frame.identifier == identifiers[first_idx] and rep_frame.data == rec_payload


# =============================================================================
# TX Event FIFO
# =============================================================================


# 测试 Feature：
# CAN TX Event FIFO的新事件、水位、满、丢失、事件内容及Ack后恢复。
#
# 测试方法：
# 1. 显式调用 can_handle.reset()，配置深度4、水位2的TX Event FIFO。
# 2. 依次发送5帧，在第1、2、4、5帧后读取事件状态与IRQ Raw。
# 3. 读出并Ack前4项事件并比对元数据；排空后再发第6帧验证恢复。
#
# 通过条件：
# 1. 水位、满、丢失标志在对应帧边界正确触发。
# 2. 前4项事件数据准确，排空后新帧能继续生成并读取TX Event。
def test_can_p1_009_tx_event_fifo_watermark_full_and_recovery(can0) -> None:
    # 1）复位
    can_handle = can0
    can_handle.reset()

    # 2）IP 配置与激励准备
    support = can_handle.support
    identifier = 0x369
    payload_bytes = 8
    event_depth = 4
    event_watermark = 2
    markers = (0x10, 0x11, 0x12, 0x13, 0x14)
    recovery_marker = 0x20
    tracked_irq = CanIrqSource.TX_EVENT_NEW | CanIrqSource.TX_EVENT_WATERMARK | CanIrqSource.TX_EVENT_FULL | CanIrqSource.TX_EVENT_LOST

    can_handle.initializing_set(True)
    can_handle.wait_initializing(True, timeout_s=TIMEOUT_S)
    can_handle.timing_set(CanTiming(
        phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    ))
    can_handle.options_set(CanOptions(
        fd_enabled=False, brs_enabled=False, automatic_retry=True, tx_pause=False, edge_filter=False,
        protocol_exception=True, tdc_enabled=False, tdc_offset_cycles=0, tdc_filter_cycles=0, ram_watchdog_cycles=0,
    ))
    can_handle.ram_layout_set(tx_event_loopback_ram(support, watermark=event_watermark))
    can_handle.filter_set(0, CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, identifier, identifier), extended=False)
    can_handle.loopback_set(CanLoopback.INTERNAL)
    can_handle.bus_config_set(CanBusConfig(
        monitor=True, restricted=False, timestamp_divisor=1, timestamp_source=CanTimestampSource.INTERNAL,
        timeout_source=CanTimeoutSource.CONTINUOUS, timeout_period=0, timeout_enabled=False,
        reject_remote_ext=True, reject_remote_std=True,
        unmatched_ext=CanUnmatchedPolicy.REJECT, unmatched_std=CanUnmatchedPolicy.REJECT,
    ))
    can_handle.irq_mask_set(tracked_irq, False)
    can_handle.irq_clear(tracked_irq)
    can_handle.initializing_set(False)
    can_handle.wait_initializing(False, timeout_s=TIMEOUT_S)

    # 3）获取并判断结果：分阶段发送 5 帧
    for seq, marker in enumerate(markers):
        can_handle.tx_write(0, CanTxFrame(identifier, CanFrameFlags.STORE_EVENT, payload_bytes, marker, bytes((seq,)) + pattern(payload_bytes - 1)))
        can_handle.tx_request(1)
        can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)
        status = can_handle.tx_event_status_get()
        irq_raw = can_handle.irq_snapshot_get().raw_status
        if seq == 0:
            assert status.fill == 1 and not status.watermark and not status.full and not status.lost
            assert irq_raw & tracked_irq == CanIrqSource.TX_EVENT_NEW
        elif seq == 1:
            assert status.fill == 2 and status.watermark and not status.full and not status.lost
            assert irq_raw & tracked_irq == CanIrqSource.TX_EVENT_NEW | CanIrqSource.TX_EVENT_WATERMARK
        elif seq == 3:
            assert status.fill == 4 and status.watermark and status.full and not status.lost
            assert irq_raw & tracked_irq & CanIrqSource.TX_EVENT_FULL
        elif seq == 4:
            assert status.fill == 4 and status.full and status.lost
            assert irq_raw & tracked_irq & CanIrqSource.TX_EVENT_LOST

    # 读取并 Ack 前 4 项事件
    for idx in range(event_depth):
        ev = can_handle.tx_event_read()
        assert ev.index == idx and ev.identifier == identifier and ev.marker == markers[idx]
        assert ev.event_type is CanTxEventType.TRANSMITTED
        can_handle.tx_event_ack(ev.index)

    assert can_handle.tx_event_status_get().fill == 0

    # 恢复验证：发送第 6 帧并读取新事件
    can_handle.tx_write(0, CanTxFrame(identifier, CanFrameFlags.STORE_EVENT, payload_bytes, recovery_marker, pattern(payload_bytes, inverse=True)))
    can_handle.tx_request(1)
    can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)
    rec_ev = can_handle.tx_event_read()
    assert rec_ev.identifier == identifier and rec_ev.marker == recovery_marker
    can_handle.tx_event_ack(rec_ev.index)


# =============================================================================
# 时钟停止与恢复
# =============================================================================


# 测试 Feature：
# CAN时钟停止请求、硬件ACK握手及恢复后收发能力。
#
# 测试方法：
# 1. 显式调用 can_handle.reset()，配置内部回环。
# 2. 发送第一帧并读取确认；请求 Clock Stop 并等待 ACK。
# 3. 撤销停止请求，清 INIT，发送第二帧验证恢复。
#
# 通过条件：
# 1. 请求后 ACK 和 INIT 均为 1，撤销后 ACK 解除，清 INIT 后恢复运行。
# 2. 恢复后发送第二帧数据完全匹配，状态无挂起。
def test_can_p1_015_clock_stop_and_recovery(can0) -> None:
    # 1）复位
    can_handle = can0
    can_handle.reset()

    # 2）IP 配置与激励准备
    support = can_handle.support
    timing = CanTiming(
        phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    )
    layout = loopback_ram(support)

    can_handle.initializing_set(True)
    can_handle.wait_initializing(True, timeout_s=TIMEOUT_S)
    can_handle.timing_set(timing)
    can_handle.options_set(CanOptions(False, False, False, False, False, True, False, 0, 0, 0))
    can_handle.ram_layout_set(layout)
    can_handle.filter_set(0, CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x123, 0x123), extended=False)
    can_handle.loopback_set(CanLoopback.INTERNAL)
    can_handle.bus_config_set(CanBusConfig(
        monitor=True, restricted=False, timestamp_divisor=1, timestamp_source=CanTimestampSource.DISABLED,
        timeout_source=CanTimeoutSource.CONTINUOUS, timeout_period=0, timeout_enabled=False,
        reject_remote_ext=True, reject_remote_std=True,
        unmatched_ext=CanUnmatchedPolicy.REJECT, unmatched_std=CanUnmatchedPolicy.REJECT,
    ))
    can_handle.initializing_set(False)
    can_handle.wait_initializing(False, timeout_s=TIMEOUT_S)

    # 验证第一帧通信
    can_handle.tx_write(0, CanTxFrame(0x123, CanFrameFlags.NONE, 8, 0, PATTERN_A))
    can_handle.tx_request(1)
    can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)
    can_handle.wait_rx_available(0, timeout_s=TIMEOUT_S)
    first = can_handle.rx_read(CanRxSource.FIFO0)
    can_handle.rx_fifo_ack(0, first.index)
    assert first.identifier == 0x123 and first.data == PATTERN_A

    # 请求 Clock Stop 并等待 ACK
    can_handle.clock_stop_set(True)
    assert can_handle.wait_clock_stop_ack(True, timeout_s=TIMEOUT_S)
    assert can_handle.initializing_get()

    # 撤销 Clock Stop 并清 INIT
    can_handle.clock_stop_set(False)
    assert can_handle.wait_clock_stop_ack(False, timeout_s=TIMEOUT_S)
    can_handle.initializing_set(False)
    can_handle.wait_initializing(False, timeout_s=TIMEOUT_S)

    # 3）获取并判断结果：恢复后发送第二帧
    can_handle.tx_write(0, CanTxFrame(0x123, CanFrameFlags.NONE, 8, 1, PATTERN_B))
    can_handle.tx_request(1)
    can_handle.wait_tx_complete(1, timeout_s=TIMEOUT_S)
    can_handle.wait_rx_available(0, timeout_s=TIMEOUT_S)
    second = can_handle.rx_read(CanRxSource.FIFO0)
    can_handle.rx_fifo_ack(0, second.index)
    assert second.identifier == 0x123 and second.data == PATTERN_B
    assert can_handle.tx_status_get().pending == 0
    assert can_handle.rx_fifo_status_get(0).fill == 0


# =============================================================================
# TX队列与FIFO次序
# =============================================================================


# 测试 Feature：
# CAN发送缓冲在Dedicated Buffer、TX FIFO与Priority Queue三种模式下的调度顺序。
#
# 测试方法：
# 1. 显式调用 can_handle.reset()，配置三项TX与内部回环。
# 2. 写入乱序ID报文（0x300, 0x100, 0x200），一次性批量请求发送。
# 3. 按接收端到达顺序依次读取并比对出队优先级。
#
# 通过条件：
# 1. FIFO按0x300/0x100/0x200出队；Queue和Buffer按0x100/0x200/0x300出队。
# 2. 帧头与数据完全一致，发送完成后状态恢复空闲。
@pytest.mark.parametrize("mode", ("buffer", "fifo", "queue"))
def test_can_p1_008_tx_fifo_queue_order(can0, mode) -> None:
    # 1）复位
    can_handle = can0
    can_handle.reset()

    # 2）IP 配置与激励准备
    support = can_handle.support
    layout = tx_order_ram(support, mode=mode)
    frames = tuple(
        CanTxFrame(identifier, CanFrameFlags.NONE, 8, idx, idx.to_bytes(4, "little") + PATTERN_A[4:])
        for idx, identifier in enumerate((0x300, 0x100, 0x200))
    )
    expected = frames if mode == "fifo" else (frames[1], frames[2], frames[0])

    can_handle.initializing_set(True)
    can_handle.wait_initializing(True, timeout_s=TIMEOUT_S)
    can_handle.timing_set(CanTiming(
        phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    ))
    can_handle.options_set(CanOptions(
        fd_enabled=False, brs_enabled=False, automatic_retry=True, tx_pause=False, edge_filter=False,
        protocol_exception=True, tdc_enabled=False, tdc_offset_cycles=0, tdc_filter_cycles=0, ram_watchdog_cycles=0,
    ))
    can_handle.ram_layout_set(layout)
    can_handle.filter_set(0, CanFilter(CanFilterType.RANGE, CanFilterAction.FIFO0, 0x100, 0x300), extended=False)
    can_handle.loopback_set(CanLoopback.INTERNAL)
    can_handle.bus_config_set(CanBusConfig(
        monitor=True, restricted=False, timestamp_divisor=1, timestamp_source=CanTimestampSource.DISABLED,
        timeout_source=CanTimeoutSource.CONTINUOUS, timeout_period=0, timeout_enabled=False,
        reject_remote_ext=True, reject_remote_std=True,
        unmatched_ext=CanUnmatchedPolicy.REJECT, unmatched_std=CanUnmatchedPolicy.REJECT,
    ))
    can_handle.initializing_set(False)
    can_handle.wait_initializing(False, timeout_s=TIMEOUT_S)

    # 预装三槽并批量请求
    for idx, frame in enumerate(frames):
        can_handle.tx_write(idx, frame)
        assert can_handle.tx_read(idx) == frame

    can_handle.tx_request(0b111)
    completed = can_handle.wait_tx_complete(0b111, timeout_s=TIMEOUT_S)
    assert completed.completed & 0b111 == 0b111

    # 3）获取并判断结果：依次读取并校验接收顺序
    for frame in expected:
        can_handle.wait_rx_available(0, timeout_s=TIMEOUT_S)
        actual = can_handle.rx_read(CanRxSource.FIFO0)
        assert actual.identifier == frame.identifier and actual.flags == frame.flags
        assert actual.dlc == frame.dlc and actual.data == frame.data
        can_handle.rx_fifo_ack(0, actual.index)

    final = can_handle.tx_status_get()
    rx = can_handle.rx_fifo_status_get(0)
    assert final.pending == 0 and not final.full
    assert rx.fill == 0 and not rx.lost

