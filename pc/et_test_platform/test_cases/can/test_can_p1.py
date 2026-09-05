# CAN P1帧格式与DLC边界。
# 职责：明确配置、双Pattern激励、实际帧观测和独立Expected比较。
# 边界：不把内部回环当作外部位速率测量，不在Case绑定芯片地址或实例。
# 依赖：CAN/CRG/Resource公共Driver及只读Support。

from dataclasses import asdict
from time import sleep

import pytest

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

# 每种线格式分别覆盖两个ID边界；每个执行节点内部遍历16种DLC及两种数据。
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


# ------------------------------ 帧格式 ------------------------------


# 测试 Feature：
# Classic标准/扩展帧、FD/BRS、DLC到有效长度映射及ID上下边界。
#
# 测试方法：
# 1. 每个DLC节点复位CAN和资源池，配置500 kbit/s、FD数据2 Mbit/s及64-byte RX槽。
# 2. 内部回环分别发送原Pattern和反相Pattern；Classic DLC9～15只装载8-byte。
# 3. 读取并Ack实际RX帧，逐字段与独立Expected比较，不用发出的Wire数据充当接收值。
#
# 通过条件：
# 1. 每个格式/ID节点的16种DLC、两种Pattern全部完成，元数据及有效字节完全一致。
# 2. 每帧TX完成，RX恰有一帧，Ack后为空且无Lost；该结果不替代外部BRS波形测试。
@pytest.mark.parametrize("format_name,flags", FORMAT_NODES, ids=[node[0] for node in FORMAT_NODES])
@pytest.mark.parametrize("id_bound", ("minimum", "maximum"))
def test_can_p1_001_frame_formats(
    can_support, resource_driver, record_property, format_name, flags, id_bound
) -> None:

    # 准备：标准/扩展ID上限是CAN协议定义，不是芯片实例或寄存器事实。
    support = can_support
    can = support.can
    extended = bool(flags & CanFrameFlags.EXTENDED)
    fd_enabled = bool(flags & CanFrameFlags.FD)
    identifier = (0x1FFFFFFF if extended else 0x7FF) if id_bound == "maximum" else 0
    timing = CanTiming(
        phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    )
    layout = loopback_ram(support, payload_bytes=64)
    completed_nodes = []

    # 清理：异常也复位当前CAN和整池资源，不能留下未完成TX污染下一节点。
    with case_cleanup_scope(
        lambda: (
            ("CAN reset", lambda: support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)),
            ("Resource pool reset", resource_driver.reset),
        )
    ):
        # 隔离：每种DLC重新复位；两帧只有在上一帧完成并Ack后才顺序发送。
        for dlc in range(16):
            support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
            resource_driver.reset()
            length = FD_LENGTHS[dlc] if fd_enabled else min(dlc, 8)

            # 配置：进入INIT设置本节点格式与真实位时序，不使用默认FD/BRS状态。
            can.initializing_set(True)
            can.wait_initializing(True, timeout_s=TIMEOUT_S)
            can.timing_set(timing)
            can.options_set(
                CanOptions(
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
                )
            )

            # 接收路由：关闭Filter槽，当前ID类型的未匹配帧进入RX0，另一类型拒绝。
            can.ram_layout_set(layout)
            can.filter_set(
                0,
                CanFilter(CanFilterType.DISABLED, CanFilterAction.DISABLED, 0, 0),
                extended=False,
            )
            can.loopback_set(CanLoopback.INTERNAL)
            can.bus_config_set(
                CanBusConfig(
                    monitor=True,
                    restricted=False,
                    timestamp_divisor=1,
                    timestamp_source=CanTimestampSource.INTERNAL,
                    timeout_source=CanTimeoutSource.CONTINUOUS,
                    timeout_period=0,
                    timeout_enabled=False,
                    reject_remote_ext=True,
                    reject_remote_std=True,
                    unmatched_ext=CanUnmatchedPolicy.RX0 if extended else CanUnmatchedPolicy.REJECT,
                    unmatched_std=CanUnmatchedPolicy.REJECT if extended else CanUnmatchedPolicy.RX0,
                )
            )

            # 启动：退出INIT后独立读回模式，防止意外依赖外部总线完成回环。
            can.initializing_set(False)
            can.wait_initializing(False, timeout_s=TIMEOUT_S)
            mode = can.loopback_get()
            record_property("mode", mode.name)
            assert mode is CanLoopback.INTERNAL

            # 激励：每种长度均用两组数据，零长度帧也保留真实DLC/元数据验证。
            for inverse in (False, True):
                payload = pattern(length, inverse=inverse)
                outgoing = CanTxFrame(identifier, flags, dlc, 0, payload)
                can.tx_write(0, outgoing)
                can.tx_request(1)
                tx = can.wait_tx_complete(1, timeout_s=TIMEOUT_S)
                ready = can.wait_rx_available(0, timeout_s=TIMEOUT_S)

                # 观测：读取真实接收帧后Ack；先保存观测及Expected，再执行强断言。
                actual = can.rx_read(CanRxSource.FIFO0)
                can.rx_fifo_ack(0, actual.index)
                after = can.rx_fifo_status_get(0)
                record_property(
                    "current_node", f"{format_name}/{id_bound}/DLC{dlc}/{'B' if inverse else 'A'}"
                )
                record_property(
                    "expected",
                    f"ID=0x{identifier:X}, flags=0x{int(flags):02X}, DLC={dlc}, bytes={payload.hex(' ').upper()}",
                )
                record_property(
                    "format_text",
                    f"ID=0x{actual.identifier:X}, flags=0x{int(actual.flags):02X}, DLC={actual.dlc}, length={len(actual.data)}",
                )
                record_property(
                    "payload_text", actual.data.hex(" ").upper() if actual.data else "零长度帧"
                )
                record_observation(
                    record_property,
                    key="format",
                    value={
                        "identifier": actual.identifier,
                        "flags": int(actual.flags),
                        "dlc": actual.dlc,
                        "length": len(actual.data),
                    },
                    source="dut",
                    endpoint="RX.FRAME_HEADER",
                )
                record_observation(
                    record_property,
                    key="payload",
                    value=list(actual.data),
                    source="dut",
                    endpoint="RX.FRAME_PAYLOAD",
                )

                # 判定：Classic高DLC仍保留原DLC但长度为8；FD依独立表比较全部字节。
                assert actual.identifier == identifier and actual.flags == flags
                assert actual.dlc == dlc and len(actual.data) == length
                assert actual.data == payload
                assert tx.completed & 1
                assert ready.fill == 1 and after.fill == 0
                assert not (ready.lost or after.lost)
                completed_nodes.append((dlc, inverse))

    # 完整性：执行数是过程补充证据，不代替每帧前面的元数据和数据断言。
    record_property("completed_nodes", len(completed_nodes))
    assert len(completed_nodes) == 32


# =============================================================================
# ID过滤与Remote策略
# =============================================================================


# 测试 Feature：
# CAN标准ID Range、Dual、Mask、首匹配、路由、未匹配策略及High Priority状态。
#
# 测试方法：
# 1. 每个参数节点复位CAN和资源池，配置两个深度4的RX FIFO及内部回环。
# 2. 下发明确Filter列表和未匹配策略，发送一个带唯一序号的Classic标准帧。
# 3. 读取两个FIFO、实际RX帧；High Priority节点另读取状态和IRQ Raw。
#
# 通过条件：
# 1. 只在预期FIFO收到一帧，拒绝节点两个FIFO均为空，ID、数据及Filter索引正确。
# 2. 重叠规则只命中首个启用项；High Priority状态和IRQ指向同一Filter。
@pytest.mark.parametrize(
    "node_name,filters,unmatched_policy,identifier,expected_fifo,expected_filter,high_priority",
    STANDARD_FILTER_NODES,
    ids=[node[0] for node in STANDARD_FILTER_NODES],
)
def test_can_p1_002_standard_id_filter_and_routing(
    can_support,
    resource_driver,
    record_property,
    node_name,
    filters,
    unmatched_policy,
    identifier,
    expected_fifo,
    expected_filter,
    high_priority,
) -> None:

    # 准备：每个节点的Filter、输入和Expected均来自上方独立常量表。
    support = can_support
    can = support.can
    payload_bytes = 8
    sequence = identifier & 0xFF
    payload = bytes((sequence,)) + pattern(payload_bytes - 1)
    layout = filter_loopback_ram(
        support,
        standard_count=len(filters),
        extended_count=0,
    )
    timing = CanTiming(
        phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    )
    expected = {
        "node": node_name,
        "identifier": identifier,
        "fifo": expected_fifo,
        "filter_index": expected_filter,
        "nonmatching": expected_filter is None and expected_fifo is not None,
        "high_priority": high_priority,
    }
    actual_frame = None
    high_priority_status = None
    high_priority_irq = None

    # Expected：在任何设备操作前登记，不能从FIFO状态或RX帧反推。
    record_property("expected", expected)

    # 清理：任何节点失败都整体复位当前CAN和资源池，不逐项恢复Filter RAM。
    with case_cleanup_scope(
        lambda: (
            ("CAN reset", lambda: support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)),
            ("Resource pool reset", resource_driver.reset),
        )
    ):
        # 基线：清除上一个参数节点留下的FIFO、IRQ和Message RAM状态。
        support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
        resource_driver.reset()

        # 配置：显式建立时序、Filter RAM、内部回环和标准未匹配策略。
        can.initializing_set(True)
        can.wait_initializing(True, timeout_s=TIMEOUT_S)
        can.timing_set(timing)
        can.options_set(
            CanOptions(
                fd_enabled=False,
                brs_enabled=False,
                automatic_retry=True,
                tx_pause=False,
                edge_filter=False,
                protocol_exception=True,
                tdc_enabled=False,
                tdc_offset_cycles=0,
                tdc_filter_cycles=0,
                ram_watchdog_cycles=0,
            )
        )
        can.ram_layout_set(layout)

        # Filter索引顺序就是硬件首匹配顺序，禁止排序或合并相同ID项。
        for filter_index, filter_config in enumerate(filters):
            can.filter_set(
                filter_index,
                filter_config,
                extended=False,
            )

        can.loopback_set(CanLoopback.INTERNAL)
        can.bus_config_set(
            CanBusConfig(
                monitor=True,
                restricted=False,
                timestamp_divisor=1,
                timestamp_source=CanTimestampSource.INTERNAL,
                timeout_source=CanTimeoutSource.CONTINUOUS,
                timeout_period=0,
                timeout_enabled=False,
                reject_remote_ext=True,
                reject_remote_std=True,
                unmatched_ext=CanUnmatchedPolicy.REJECT,
                unmatched_std=unmatched_policy,
            )
        )

        # High Priority只解除对应Raw事件屏蔽；本Case不启用NVIC回调路径。
        if high_priority:
            can.irq_mask_set(CanIrqSource.HIGH_PRIORITY, False)
            can.irq_clear(CanIrqSource.HIGH_PRIORITY)

        can.initializing_set(False)
        can.wait_initializing(False, timeout_s=TIMEOUT_S)

        # 激励：一个帧只允许形成一个接收副本，TX完成后进入固定观察窗口。
        can.tx_write(
            0,
            CanTxFrame(identifier, CanFrameFlags.NONE, payload_bytes, sequence, payload),
        )
        can.tx_request(1)
        can.wait_tx_complete(1, timeout_s=TIMEOUT_S)
        sleep(FILTER_OBSERVATION_S)

        # 观测：两个FIFO状态都读取，防止同一帧被错误复制到非目标FIFO。
        fifo0 = can.rx_fifo_status_get(0)
        fifo1 = can.rx_fifo_status_get(1)
        record_observation(
            record_property,
            key="fifo0_status",
            value={"fill": fifo0.fill, "full": fifo0.full, "lost": fifo0.lost},
            source="dut",
            endpoint="RX_FIFO[0].STATUS",
        )
        record_observation(
            record_property,
            key="fifo1_status",
            value={"fill": fifo1.fill, "full": fifo1.full, "lost": fifo1.lost},
            source="dut",
            endpoint="RX_FIFO[1].STATUS",
        )

        # 接收节点按硬件实际有数据的FIFO读取，不能按Expected选择后隐藏错误路由。
        actual_fifo = None
        if bool(fifo0.fill) != bool(fifo1.fill):
            actual_fifo = 0 if fifo0.fill else 1
            source = CanRxSource.FIFO0 if actual_fifo == 0 else CanRxSource.FIFO1
            actual_frame = can.rx_read(source)
            can.rx_fifo_ack(actual_fifo, actual_frame.index)
            record_observation(
                record_property,
                key="rx_frame",
                value={
                    "identifier": actual_frame.identifier,
                    "filter_index": actual_frame.filter_index,
                    "nonmatching": actual_frame.nonmatching,
                    "data": actual_frame.data.hex(" ").upper(),
                },
                source="dut",
                endpoint=f"RX_FIFO[{actual_fifo}].FRAME",
            )

        # High Priority节点独立读取状态和IRQ Raw，不用普通RX帧字段替代。
        if high_priority:
            high_priority_status = can.high_priority_status_get()
            high_priority_irq = can.irq_snapshot_get().raw_status
            record_observation(
                record_property,
                key="high_priority_status",
                value={
                    "storage": int(high_priority_status.storage),
                    "filter_index": high_priority_status.filter_index,
                    "extended_filter": high_priority_status.filter_extended,
                },
                source="dut",
                endpoint="HIGH_PRIORITY.STATUS",
            )
            record_observation(
                record_property,
                key="high_priority_irq",
                value=int(high_priority_irq & CanIrqSource.HIGH_PRIORITY),
                source="dut",
                endpoint="IRQ.RAW",
            )

        # 判定：Expected路由、实际帧和High Priority三组事实分别强断言。
        if fifo0.fill and fifo1.fill:
            actual_route = "fifo0+fifo1"
        elif actual_fifo is None:
            actual_route = "rejected"
        else:
            actual_route = f"fifo{actual_fifo}"
        record_property("node", node_name)
        record_property("actual_route", actual_route)
        if expected_fifo is None:
            assert fifo0.fill == 0 and fifo1.fill == 0
        else:
            assert fifo0.fill == (1 if expected_fifo == 0 else 0)
            assert fifo1.fill == (1 if expected_fifo == 1 else 0)
            assert actual_fifo == expected_fifo and actual_frame is not None
            assert actual_frame.identifier == identifier and actual_frame.data == payload
            assert actual_frame.nonmatching == expected["nonmatching"]
            if expected_filter is not None:
                assert actual_frame.filter_index == expected_filter

        if high_priority:
            assert high_priority_status.storage == CanHighPriorityStorage.FIFO0
            assert high_priority_status.filter_index == expected_filter
            assert not high_priority_status.filter_extended
            assert high_priority_irq & CanIrqSource.HIGH_PRIORITY


# 测试 Feature：
# CAN扩展ID Range、Dual、Mask、XIDAM、29-bit比较、首匹配、路由及High Priority状态。
#
# 测试方法：
# 1. 每个参数节点复位CAN和资源池，配置扩展Filter、XIDAM及两个RX FIFO。
# 2. 用内部回环发送一个带唯一序号的Classic扩展帧，等待TX完成后观察两个FIFO。
# 3. 按硬件实际路由读取帧；High Priority节点另读取状态和IRQ Raw。
#
# 通过条件：
# 1. Range/Dual/Mask、XIDAM及RANGE_NO_MASK结果与独立Expected一致，29-bit高位不混淆。
# 2. 只在预期FIFO收到一帧；首匹配索引、High Priority列表/索引及IRQ均正确。
@pytest.mark.parametrize(
    "node_name,filters,extended_mask,unmatched_policy,identifier,expected_fifo,expected_filter,high_priority",
    EXTENDED_FILTER_NODES,
    ids=[node[0] for node in EXTENDED_FILTER_NODES],
)
def test_can_p1_003_extended_id_filter_and_mask(
    can_support,
    resource_driver,
    record_property,
    node_name,
    filters,
    extended_mask,
    unmatched_policy,
    identifier,
    expected_fifo,
    expected_filter,
    high_priority,
) -> None:

    # 准备：每个节点显式给出Filter、XIDAM、输入ID和独立Expected。
    support = can_support
    can = support.can
    payload_bytes = 8
    sequence = identifier & 0xFF
    payload = bytes((sequence,)) + pattern(payload_bytes - 1)
    layout = filter_loopback_ram(
        support,
        standard_count=0,
        extended_count=len(filters),
    )
    timing = CanTiming(
        phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    )
    expected = {
        "node": node_name,
        "identifier": identifier,
        "extended_mask": extended_mask,
        "fifo": expected_fifo,
        "filter_index": expected_filter,
        "nonmatching": expected_filter is None and expected_fifo is not None,
        "high_priority": high_priority,
    }
    actual_frame = None
    high_priority_status = None
    high_priority_irq = None

    # Expected：在任何设备操作前登记，不能根据RX结果修正Mask判据。
    record_property("expected", expected)

    # 清理：任何节点失败都整体复位当前CAN和资源池，不逐项恢复Message RAM。
    with case_cleanup_scope(
        lambda: (
            ("CAN reset", lambda: support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)),
            ("Resource pool reset", resource_driver.reset),
        )
    ):
        # 基线：清除上一个参数节点留下的Filter、XIDAM、FIFO和IRQ状态。
        support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
        resource_driver.reset()

        # 配置：进入INIT后建立时序、扩展Filter RAM和当前XIDAM。
        can.initializing_set(True)
        can.wait_initializing(True, timeout_s=TIMEOUT_S)
        can.timing_set(timing)
        can.options_set(
            CanOptions(
                fd_enabled=False,
                brs_enabled=False,
                automatic_retry=True,
                tx_pause=False,
                edge_filter=False,
                protocol_exception=True,
                tdc_enabled=False,
                tdc_offset_cycles=0,
                tdc_filter_cycles=0,
                ram_watchdog_cycles=0,
            )
        )
        can.ram_layout_set(layout)

        # Filter索引顺序就是硬件首匹配顺序，RANGE_NO_MASK节点仍写入同一扩展列表。
        for filter_index, filter_config in enumerate(filters):
            can.filter_set(
                filter_index,
                filter_config,
                extended=True,
            )

        can.extended_mask_set(extended_mask)
        can.loopback_set(CanLoopback.INTERNAL)
        can.bus_config_set(
            CanBusConfig(
                monitor=True,
                restricted=False,
                timestamp_divisor=1,
                timestamp_source=CanTimestampSource.INTERNAL,
                timeout_source=CanTimeoutSource.CONTINUOUS,
                timeout_period=0,
                timeout_enabled=False,
                reject_remote_ext=True,
                reject_remote_std=True,
                unmatched_ext=unmatched_policy,
                unmatched_std=CanUnmatchedPolicy.REJECT,
            )
        )

        # High Priority只解除对应Raw事件屏蔽；本Case不启用NVIC回调路径。
        if high_priority:
            can.irq_mask_set(CanIrqSource.HIGH_PRIORITY, False)
            can.irq_clear(CanIrqSource.HIGH_PRIORITY)

        can.initializing_set(False)
        can.wait_initializing(False, timeout_s=TIMEOUT_S)

        # 激励：发送完整29-bit ID，TX完成后进入固定观察窗口。
        can.tx_write(
            0,
            CanTxFrame(
                identifier,
                CanFrameFlags.EXTENDED,
                payload_bytes,
                sequence,
                payload,
            ),
        )
        can.tx_request(1)
        can.wait_tx_complete(1, timeout_s=TIMEOUT_S)
        sleep(FILTER_OBSERVATION_S)

        # 观测：两个FIFO状态都读取，防止错误路由或同一帧产生两个副本。
        fifo0 = can.rx_fifo_status_get(0)
        fifo1 = can.rx_fifo_status_get(1)
        record_observation(
            record_property,
            key="fifo0_status",
            value={"fill": fifo0.fill, "full": fifo0.full, "lost": fifo0.lost},
            source="dut",
            endpoint="RX_FIFO[0].STATUS",
        )
        record_observation(
            record_property,
            key="fifo1_status",
            value={"fill": fifo1.fill, "full": fifo1.full, "lost": fifo1.lost},
            source="dut",
            endpoint="RX_FIFO[1].STATUS",
        )

        # 按硬件实际有数据的FIFO读取，不能按Expected选择后隐藏错误路由。
        actual_fifo = None
        if bool(fifo0.fill) != bool(fifo1.fill):
            actual_fifo = 0 if fifo0.fill else 1
            source = CanRxSource.FIFO0 if actual_fifo == 0 else CanRxSource.FIFO1
            actual_frame = can.rx_read(source)
            can.rx_fifo_ack(actual_fifo, actual_frame.index)
            record_observation(
                record_property,
                key="rx_frame",
                value={
                    "identifier": actual_frame.identifier,
                    "filter_index": actual_frame.filter_index,
                    "nonmatching": actual_frame.nonmatching,
                    "data": actual_frame.data.hex(" ").upper(),
                },
                source="dut",
                endpoint=f"RX_FIFO[{actual_fifo}].FRAME",
            )

        # High Priority节点读取扩展Filter列表标志、索引、存储位置及IRQ Raw。
        if high_priority:
            high_priority_status = can.high_priority_status_get()
            high_priority_irq = can.irq_snapshot_get().raw_status
            record_observation(
                record_property,
                key="high_priority_status",
                value={
                    "storage": int(high_priority_status.storage),
                    "filter_index": high_priority_status.filter_index,
                    "extended_filter": high_priority_status.filter_extended,
                },
                source="dut",
                endpoint="HIGH_PRIORITY.STATUS",
            )
            record_observation(
                record_property,
                key="high_priority_irq",
                value=int(high_priority_irq & CanIrqSource.HIGH_PRIORITY),
                source="dut",
                endpoint="IRQ.RAW",
            )

        # 判定：路由、原始29-bit ID、Filter索引和High Priority分别强断言。
        if fifo0.fill and fifo1.fill:
            actual_route = "fifo0+fifo1"
        elif actual_fifo is None:
            actual_route = "rejected"
        else:
            actual_route = f"fifo{actual_fifo}"
        record_property("node", node_name)
        record_property("actual_route", actual_route)
        if expected_fifo is None:
            assert fifo0.fill == 0 and fifo1.fill == 0
        else:
            assert fifo0.fill == (1 if expected_fifo == 0 else 0)
            assert fifo1.fill == (1 if expected_fifo == 1 else 0)
            assert actual_fifo == expected_fifo and actual_frame is not None
            assert actual_frame.identifier == identifier and actual_frame.data == payload
            assert actual_frame.flags == CanFrameFlags.EXTENDED
            assert actual_frame.nonmatching == expected["nonmatching"]
            if expected_filter is not None:
                assert actual_frame.filter_index == expected_filter

        if high_priority:
            assert high_priority_status.storage == CanHighPriorityStorage.FIFO0
            assert high_priority_status.filter_index == expected_filter
            assert high_priority_status.filter_extended
            assert high_priority_irq & CanIrqSource.HIGH_PRIORITY


# 测试 Feature：
# Classic标准/扩展Remote帧的允许、拒绝及同ID数据帧恢复。
#
# 测试方法：
# 1. 分别用标准/扩展ID和DLC0/8构造Remote帧，先允许Remote并核对接收元数据。
# 2. 重新复位后拒绝同类型Remote，等待TX完成及固定观察窗口并读取FIFO状态。
# 3. 保持拒绝Remote策略，发送同ID 8-byte数据帧作为过滤和数据路径正对照。
#
# 通过条件：
# 1. 允许阶段收到RTR=1、原始DLC正确且payload为空的Remote帧。
# 2. 拒绝阶段FIFO无新增，而随后同ID数据帧完整接收，证明只拒绝Remote。
@pytest.mark.parametrize("extended", (False, True), ids=("standard", "extended"))
@pytest.mark.parametrize("dlc", (0, 8), ids=("dlc0", "dlc8"))
def test_can_p1_004_remote_frame_policy(
    can_support,
    resource_driver,
    record_property,
    extended,
    dlc,
) -> None:

    # 准备：Remote没有payload；恢复对照使用同ID且固定8-byte数据。
    support = can_support
    can = support.can
    identifier = 0x123
    frame_flags = CanFrameFlags.REMOTE
    if extended:
        frame_flags |= CanFrameFlags.EXTENDED
    recovery_flags = CanFrameFlags.EXTENDED if extended else CanFrameFlags.NONE
    recovery_payload = pattern(8)
    filter_config = CanFilter(
        CanFilterType.DUAL,
        CanFilterAction.FIFO0,
        identifier,
        identifier,
    )
    layout = filter_loopback_ram(
        support,
        standard_count=0 if extended else 1,
        extended_count=1 if extended else 0,
    )
    timing = CanTiming(
        phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    )
    expected = {
        "extended": extended,
        "identifier": identifier,
        "remote_dlc": dlc,
        "remote_payload_length": 0,
        "recovery_payload": recovery_payload.hex(" ").upper(),
    }

    # Expected：在任何设备操作前登记，不从Remote接收结果生成。
    record_property("expected", expected)

    # 清理：任何阶段失败都整体复位当前CAN和资源池。
    with case_cleanup_scope(
        lambda: (
            ("CAN reset", lambda: support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)),
            ("Resource pool reset", resource_driver.reset),
        )
    ):
        # 允许阶段基线：清除历史FIFO和Remote策略，重新建立完整配置。
        support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
        resource_driver.reset()

        can.initializing_set(True)
        can.wait_initializing(True, timeout_s=TIMEOUT_S)
        can.timing_set(timing)
        can.options_set(
            CanOptions(
                fd_enabled=False,
                brs_enabled=False,
                automatic_retry=True,
                tx_pause=False,
                edge_filter=False,
                protocol_exception=True,
                tdc_enabled=False,
                tdc_offset_cycles=0,
                tdc_filter_cycles=0,
                ram_watchdog_cycles=0,
            )
        )
        can.ram_layout_set(layout)
        can.filter_set(0, filter_config, extended=extended)
        if extended:
            can.extended_mask_set(0x1FFFFFFF)
        can.loopback_set(CanLoopback.INTERNAL)
        can.bus_config_set(
            CanBusConfig(
                monitor=True,
                restricted=False,
                timestamp_divisor=1,
                timestamp_source=CanTimestampSource.INTERNAL,
                timeout_source=CanTimeoutSource.CONTINUOUS,
                timeout_period=0,
                timeout_enabled=False,
                reject_remote_ext=False,
                reject_remote_std=False,
                unmatched_ext=CanUnmatchedPolicy.REJECT,
                unmatched_std=CanUnmatchedPolicy.REJECT,
            )
        )
        can.initializing_set(False)
        can.wait_initializing(False, timeout_s=TIMEOUT_S)

        # 允许刺激：Remote保留原始DLC，但Wire和Message RAM均不装载payload。
        can.tx_write(0, CanTxFrame(identifier, frame_flags, dlc, 1, b""))
        can.tx_request(1)
        can.wait_tx_complete(1, timeout_s=TIMEOUT_S)
        can.wait_rx_available(0, timeout_s=TIMEOUT_S)
        remote_frame = can.rx_read(CanRxSource.FIFO0)
        can.rx_fifo_ack(0, remote_frame.index)
        record_observation(
            record_property,
            key="remote_frame",
            value={
                "identifier": remote_frame.identifier,
                "flags": int(remote_frame.flags),
                "dlc": remote_frame.dlc,
                "payload_length": len(remote_frame.data),
            },
            source="dut",
            endpoint="RX_FIFO[0].REMOTE_FRAME",
        )

        # 允许判定：先保存真实帧，再核对RTR、ID、DLC和零payload。
        assert remote_frame.identifier == identifier
        assert remote_frame.flags == frame_flags
        assert remote_frame.dlc == dlc and remote_frame.data == b""

        # 拒绝阶段基线：硬件和资源重新复位，避免沿用允许阶段的FIFO状态。
        support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
        resource_driver.reset()

        can.initializing_set(True)
        can.wait_initializing(True, timeout_s=TIMEOUT_S)
        can.timing_set(timing)
        can.options_set(
            CanOptions(
                fd_enabled=False,
                brs_enabled=False,
                automatic_retry=True,
                tx_pause=False,
                edge_filter=False,
                protocol_exception=True,
                tdc_enabled=False,
                tdc_offset_cycles=0,
                tdc_filter_cycles=0,
                ram_watchdog_cycles=0,
            )
        )
        can.ram_layout_set(layout)
        can.filter_set(0, filter_config, extended=extended)
        if extended:
            can.extended_mask_set(0x1FFFFFFF)
        can.loopback_set(CanLoopback.INTERNAL)
        can.bus_config_set(
            CanBusConfig(
                monitor=True,
                restricted=False,
                timestamp_divisor=1,
                timestamp_source=CanTimestampSource.INTERNAL,
                timeout_source=CanTimeoutSource.CONTINUOUS,
                timeout_period=0,
                timeout_enabled=False,
                reject_remote_ext=extended,
                reject_remote_std=not extended,
                unmatched_ext=CanUnmatchedPolicy.REJECT,
                unmatched_std=CanUnmatchedPolicy.REJECT,
            )
        )
        can.initializing_set(False)
        can.wait_initializing(False, timeout_s=TIMEOUT_S)

        # 拒绝刺激：先确认Remote TX完成，再观察100 ms内RX0没有新增。
        can.tx_write(0, CanTxFrame(identifier, frame_flags, dlc, 2, b""))
        can.tx_request(1)
        can.wait_tx_complete(1, timeout_s=TIMEOUT_S)
        sleep(FILTER_OBSERVATION_S)
        rejected_status = can.rx_fifo_status_get(0)
        record_observation(
            record_property,
            key="reject_fifo0_status",
            value={
                "fill": rejected_status.fill,
                "full": rejected_status.full,
                "lost": rejected_status.lost,
            },
            source="dut",
            endpoint="RX_FIFO[0].STATUS_AFTER_REMOTE_REJECT",
        )

        # 正对照：保持Remote拒绝配置，发送同ID数据帧并读取真实payload。
        can.tx_write(
            0,
            CanTxFrame(identifier, recovery_flags, 8, 3, recovery_payload),
        )
        can.tx_request(1)
        can.wait_tx_complete(1, timeout_s=TIMEOUT_S)
        can.wait_rx_available(0, timeout_s=TIMEOUT_S)
        recovery_frame = can.rx_read(CanRxSource.FIFO0)
        can.rx_fifo_ack(0, recovery_frame.index)
        record_observation(
            record_property,
            key="recovery_frame",
            value={
                "identifier": recovery_frame.identifier,
                "flags": int(recovery_frame.flags),
                "dlc": recovery_frame.dlc,
                "data": recovery_frame.data.hex(" ").upper(),
            },
            source="dut",
            endpoint="RX_FIFO[0].DATA_FRAME_AFTER_REMOTE_REJECT",
        )

        # 最终判定：拒绝只作用于Remote，不得把整个Filter或RX路径关闭。
        assert rejected_status.fill == 0 and not rejected_status.lost
        assert recovery_frame.identifier == identifier
        assert recovery_frame.flags == recovery_flags and recovery_frame.dlc == 8
        assert recovery_frame.data == recovery_payload

        # 报告摘要：全部参数分支都生成相同字段，便于Excel稳定展示。
        record_property("remote_summary", expected)
        record_property(
            "reject_and_recovery",
            {
                "rejected_fill": rejected_status.fill,
                "recovery_data": recovery_frame.data.hex(" ").upper(),
            },
        )


# =============================================================================
# RX FIFO与Dedicated Buffer
# =============================================================================


# 测试 Feature：
# CAN RX FIFO0/1的新消息、水位、满状态、Get/Put索引环回及顺序保持。
#
# 测试方法：
# 1. 每个FIFO节点复位CAN和资源池，配置深度4、水位2、阻塞模式及内部回环。
# 2. 分别在第1、2、4帧后读取FIFO状态与IRQ Raw，验证New、Watermark和Full边界。
# 3. 先读取并Ack两帧，再发送两帧，最后排空并核对0～5序号和实际索引环回。
#
# 通过条件：
# 1. FILL依次到1、2、4，Watermark不提前，Full只在深度4出现，最终全部清零。
# 2. 六帧数据顺序完整，读取索引跨越3回到0，FIFO Lost始终为0。
@pytest.mark.parametrize("fifo", (0, 1), ids=("fifo0", "fifo1"))
def test_can_p1_005_rx_fifo_watermark_full_and_wrap(
    can_support, resource_driver, record_property, fifo
) -> None:

    # 准备：所有Expected仅由深度、水位和输入序号生成，不从硬件状态反推。
    support = can_support
    can = support.can
    fifo_depth = 4
    fifo_watermark = 2
    frame_count = 6
    payload_bytes = 8
    identifier = 0x245 + fifo
    layout = fifo_loopback_ram(
        support,
        fifo=fifo,
        watermark=fifo_watermark,
        overwrite=False,
    )
    timing = CanTiming(
        phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    )
    source = CanRxSource.FIFO0 if fifo == 0 else CanRxSource.FIFO1
    action = CanFilterAction.FIFO0 if fifo == 0 else CanFilterAction.FIFO1
    irq_new = CanIrqSource.RX_FIFO0_NEW if fifo == 0 else CanIrqSource.RX_FIFO1_NEW
    irq_watermark = (
        CanIrqSource.RX_FIFO0_WATERMARK if fifo == 0 else CanIrqSource.RX_FIFO1_WATERMARK
    )
    irq_full = CanIrqSource.RX_FIFO0_FULL if fifo == 0 else CanIrqSource.RX_FIFO1_FULL
    tracked_irq = irq_new | irq_watermark | irq_full
    actual_sequences = []
    actual_indices = []
    expected_sequences = list(range(frame_count))
    expected_indices = [0, 1, 2, 3, 0, 1]

    # Expected：在读取任何FIFO状态前固定独立判据，禁止从DUT结果反推。
    record_property(
        "expected",
        {
            "depth": fifo_depth,
            "watermark": fifo_watermark,
            "sequences": expected_sequences,
            "indices": expected_indices,
        },
    )

    # 清理：只恢复当前CAN和整池资源；本Case不启用NVIC路由或外部设备。
    with case_cleanup_scope(
        lambda: (
            ("CAN reset", lambda: support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)),
            ("Resource pool reset", resource_driver.reset),
        )
    ):
        # 基线：先复位，确保FIFO状态、Message RAM配置和历史IRQ不来自上一Case。
        support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
        resource_driver.reset()

        # 配置：一个精确标准ID只进入当前FIFO；另一FIFO和未匹配帧均不接收。
        can.initializing_set(True)
        can.wait_initializing(True, timeout_s=TIMEOUT_S)
        can.timing_set(timing)
        can.options_set(
            CanOptions(
                fd_enabled=False,
                brs_enabled=False,
                automatic_retry=True,
                tx_pause=False,
                edge_filter=False,
                protocol_exception=True,
                tdc_enabled=False,
                tdc_offset_cycles=0,
                tdc_filter_cycles=0,
                ram_watchdog_cycles=0,
            )
        )
        can.ram_layout_set(layout)
        can.filter_set(
            0,
            CanFilter(CanFilterType.DUAL, action, identifier, identifier),
            extended=False,
        )
        can.loopback_set(CanLoopback.INTERNAL)
        can.bus_config_set(
            CanBusConfig(
                monitor=True,
                restricted=False,
                timestamp_divisor=1,
                timestamp_source=CanTimestampSource.INTERNAL,
                timeout_source=CanTimeoutSource.CONTINUOUS,
                timeout_period=0,
                timeout_enabled=False,
                reject_remote_ext=True,
                reject_remote_std=True,
                unmatched_ext=CanUnmatchedPolicy.REJECT,
                unmatched_std=CanUnmatchedPolicy.REJECT,
            )
        )
        can.irq_mask_set(tracked_irq, False)
        can.irq_clear(tracked_irq)
        can.initializing_set(False)
        can.wait_initializing(False, timeout_s=TIMEOUT_S)

        # 激励一：第一帧只应达到New Message，不应提前达到Watermark或Full。
        payload = bytes((0,)) + pattern(payload_bytes - 1)
        can.tx_write(
            0,
            CanTxFrame(identifier, CanFrameFlags.NONE, payload_bytes, 0, payload),
        )
        can.tx_request(1)
        can.wait_tx_complete(1, timeout_s=TIMEOUT_S)
        first = can.wait_rx_available(fifo, minimum=1, timeout_s=TIMEOUT_S)
        first_irq = can.irq_snapshot_get().raw_status
        record_observation(
            record_property,
            key="first_status",
            value={
                "fill": first.fill,
                "get_index": first.get_index,
                "put_index": first.put_index,
                "full": first.full,
                "lost": first.lost,
            },
            source="dut",
            endpoint=f"RX_FIFO[{fifo}].STATUS",
        )
        record_observation(
            record_property,
            key="first_irq",
            value=int(first_irq & tracked_irq),
            source="dut",
            endpoint="IRQ.RAW",
        )
        assert first.fill == 1 and not first.full and not first.lost
        assert first_irq & tracked_irq == irq_new
        can.irq_clear(tracked_irq)

        # 激励二：第二帧首次跨到水位2，New和Watermark同时可见，Full仍不得置位。
        payload = bytes((1,)) + pattern(payload_bytes - 1, inverse=True)
        can.tx_write(
            0,
            CanTxFrame(identifier, CanFrameFlags.NONE, payload_bytes, 1, payload),
        )
        can.tx_request(1)
        can.wait_tx_complete(1, timeout_s=TIMEOUT_S)
        second = can.wait_rx_available(fifo, minimum=2, timeout_s=TIMEOUT_S)
        second_irq = can.irq_snapshot_get().raw_status
        record_observation(
            record_property,
            key="watermark_status",
            value={
                "fill": second.fill,
                "get_index": second.get_index,
                "put_index": second.put_index,
                "full": second.full,
                "lost": second.lost,
            },
            source="dut",
            endpoint=f"RX_FIFO[{fifo}].STATUS",
        )
        record_observation(
            record_property,
            key="watermark_irq",
            value=int(second_irq & tracked_irq),
            source="dut",
            endpoint="IRQ.RAW",
        )
        assert second.fill == 2 and not second.full and not second.lost
        assert second_irq & tracked_irq == irq_new | irq_watermark
        can.irq_clear(tracked_irq)

        # 激励三：继续写满深度4，只在第四帧后要求Full事件和硬件Full状态。
        for sequence in (2, 3):
            payload = bytes((sequence,)) + pattern(
                payload_bytes - 1,
                inverse=bool(sequence & 1),
            )
            can.tx_write(
                0,
                CanTxFrame(identifier, CanFrameFlags.NONE, payload_bytes, sequence, payload),
            )
            can.tx_request(1)
            can.wait_tx_complete(1, timeout_s=TIMEOUT_S)
        full = can.wait_rx_available(fifo, minimum=4, timeout_s=TIMEOUT_S)
        full_irq = can.irq_snapshot_get().raw_status
        record_observation(
            record_property,
            key="full_status",
            value={
                "fill": full.fill,
                "get_index": full.get_index,
                "put_index": full.put_index,
                "full": full.full,
                "lost": full.lost,
            },
            source="dut",
            endpoint=f"RX_FIFO[{fifo}].STATUS",
        )
        record_observation(
            record_property,
            key="full_irq",
            value=int(full_irq & tracked_irq),
            source="dut",
            endpoint="IRQ.RAW",
        )
        assert full.fill == 4 and full.full and not full.lost
        assert full_irq & tracked_irq & irq_full
        can.irq_clear(tracked_irq)

        # 环回准备：先按当前Get Index读取并Ack最早两帧，释放两个真实FIFO槽。
        for expected_sequence in (0, 1):
            received = can.rx_read(source)
            actual_sequences.append(received.data[0])
            actual_indices.append(received.index)
            can.rx_fifo_ack(fifo, received.index)
            record_observation(
                record_property,
                key="received_frame",
                value={
                    "identifier": received.identifier,
                    "sequence": received.data[0],
                    "index": received.index,
                },
                source="dut",
                endpoint=f"RX_FIFO[{fifo}].FRAME",
            )
            assert received.identifier == identifier and received.data[0] == expected_sequence

        # 环回刺激：新增序号4、5应使用已经释放的槽，Put Index必须跨界回到低索引。
        for sequence in (4, 5):
            payload = bytes((sequence,)) + pattern(
                payload_bytes - 1,
                inverse=bool(sequence & 1),
            )
            can.tx_write(
                0,
                CanTxFrame(identifier, CanFrameFlags.NONE, payload_bytes, sequence, payload),
            )
            can.tx_request(1)
            can.wait_tx_complete(1, timeout_s=TIMEOUT_S)
            can.wait_rx_available(fifo, minimum=sequence - 1, timeout_s=TIMEOUT_S)

        # 排空：逐帧读取并Ack剩余四帧，保留真实索引序列作为环回证据。
        for expected_sequence in (2, 3, 4, 5):
            received = can.rx_read(source)
            actual_sequences.append(received.data[0])
            actual_indices.append(received.index)
            can.rx_fifo_ack(fifo, received.index)
            record_observation(
                record_property,
                key="received_frame",
                value={
                    "identifier": received.identifier,
                    "sequence": received.data[0],
                    "index": received.index,
                },
                source="dut",
                endpoint=f"RX_FIFO[{fifo}].FRAME",
            )
            assert received.identifier == identifier and received.data[0] == expected_sequence

        # 终态：数据、索引和空FIFO必须同时成立，不能只凭IRQ判通过。
        final = can.rx_fifo_status_get(fifo)
        record_property("fifo", fifo)
        record_property(
            "sequence_and_indices",
            {"sequences": actual_sequences, "indices": actual_indices},
        )
        record_property(
            "status_summary",
            {
                "first": {"fill": first.fill, "full": first.full, "lost": first.lost},
                "watermark": {"fill": second.fill, "full": second.full, "lost": second.lost},
                "full": {"fill": full.fill, "full": full.full, "lost": full.lost},
                "final": {"fill": final.fill, "full": final.full, "lost": final.lost},
            },
        )
        record_observation(
            record_property,
            key="final_status",
            value={
                "fill": final.fill,
                "get_index": final.get_index,
                "put_index": final.put_index,
                "full": final.full,
                "lost": final.lost,
            },
            source="dut",
            endpoint=f"RX_FIFO[{fifo}].STATUS",
        )
        assert actual_sequences == expected_sequences
        assert actual_indices == expected_indices
        assert final.fill == 0 and not final.full and not final.lost


# 测试 Feature：
# CAN RX FIFO0/1满后的Blocking与Overwrite数据保留策略及恢复能力。
#
# 测试方法：
# 1. 每个FIFO和模式独立复位，配置深度4并顺序发送序号0～4共5帧。
# 2. 满后读取四个实际帧；Blocking期望保留0～3，Overwrite期望保留1～4。
# 3. 排空后清Lost事件，再发送序号5，验证FIFO能够恢复接收和Ack。
#
# 通过条件：
# 1. 两种模式的四帧保留序列准确，FILL不超过4；Blocking必须报告Lost。
# 2. 恢复帧5数据正确，Ack后FIFO为空且Full解除。
@pytest.mark.parametrize("fifo", (0, 1), ids=("fifo0", "fifo1"))
@pytest.mark.parametrize("overwrite", (False, True), ids=("blocking", "overwrite"))
def test_can_p1_006_rx_fifo_blocking_and_overwrite(
    can_support, resource_driver, record_property, fifo, overwrite
) -> None:

    # 准备：Overwrite的Lost语义不作假设，模式区别只按硬件实际保留帧判定。
    support = can_support
    can = support.can
    fifo_depth = 4
    payload_bytes = 8
    identifier = 0x255 + fifo
    layout = fifo_loopback_ram(support, fifo=fifo, watermark=0, overwrite=overwrite)
    timing = CanTiming(
        phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    )
    source = CanRxSource.FIFO0 if fifo == 0 else CanRxSource.FIFO1
    action = CanFilterAction.FIFO0 if fifo == 0 else CanFilterAction.FIFO1
    irq_lost = CanIrqSource.RX_FIFO0_LOST if fifo == 0 else CanIrqSource.RX_FIFO1_LOST
    expected_sequences = [1, 2, 3, 4] if overwrite else [0, 1, 2, 3]
    actual_sequences = []

    # Expected：模式、保留序列和恢复序号在硬件刺激前固定。
    record_property(
        "expected",
        {
            "mode": "overwrite" if overwrite else "blocking",
            "retained_sequences": expected_sequences,
            "recovery_sequence": 5,
        },
    )

    # 清理：即使序列或恢复断言失败，也复位当前CAN和整池资源。
    with case_cleanup_scope(
        lambda: (
            ("CAN reset", lambda: support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)),
            ("Resource pool reset", resource_driver.reset),
        )
    ):
        # 基线：每个FIFO/模式参数节点都从复位状态开始，禁止沿用上一节点Lost。
        support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
        resource_driver.reset()

        # 配置：一个精确标准ID进入当前FIFO，关闭外部路径和另一FIFO。
        can.initializing_set(True)
        can.wait_initializing(True, timeout_s=TIMEOUT_S)
        can.timing_set(timing)
        can.options_set(
            CanOptions(
                fd_enabled=False,
                brs_enabled=False,
                automatic_retry=True,
                tx_pause=False,
                edge_filter=False,
                protocol_exception=True,
                tdc_enabled=False,
                tdc_offset_cycles=0,
                tdc_filter_cycles=0,
                ram_watchdog_cycles=0,
            )
        )
        can.ram_layout_set(layout)
        can.filter_set(
            0,
            CanFilter(CanFilterType.DUAL, action, identifier, identifier),
            extended=False,
        )
        can.loopback_set(CanLoopback.INTERNAL)
        can.bus_config_set(
            CanBusConfig(
                monitor=True,
                restricted=False,
                timestamp_divisor=1,
                timestamp_source=CanTimestampSource.INTERNAL,
                timeout_source=CanTimeoutSource.CONTINUOUS,
                timeout_period=0,
                timeout_enabled=False,
                reject_remote_ext=True,
                reject_remote_std=True,
                unmatched_ext=CanUnmatchedPolicy.REJECT,
                unmatched_std=CanUnmatchedPolicy.REJECT,
            )
        )
        can.irq_mask_set(irq_lost, False)
        can.irq_clear(irq_lost)
        can.initializing_set(False)
        can.wait_initializing(False, timeout_s=TIMEOUT_S)

        # 刺激：连续提交五帧；前四帧填满，第五帧制造唯一一次满后输入。
        for sequence in range(5):
            payload = bytes((sequence,)) + pattern(
                payload_bytes - 1,
                inverse=bool(sequence & 1),
            )
            can.tx_write(
                0,
                CanTxFrame(identifier, CanFrameFlags.NONE, payload_bytes, sequence, payload),
            )
            can.tx_request(1)
            can.wait_tx_complete(1, timeout_s=TIMEOUT_S)
        overflow = can.rx_fifo_status_get(fifo)
        overflow_irq = can.irq_snapshot_get().raw_status
        record_observation(
            record_property,
            key="overflow_status",
            value={
                "fill": overflow.fill,
                "get_index": overflow.get_index,
                "put_index": overflow.put_index,
                "full": overflow.full,
                "lost": overflow.lost,
            },
            source="dut",
            endpoint=f"RX_FIFO[{fifo}].STATUS",
        )
        record_observation(
            record_property,
            key="overflow_irq",
            value=int(overflow_irq & irq_lost),
            source="dut",
            endpoint="IRQ.RAW",
        )
        assert overflow.fill == fifo_depth and overflow.full
        if not overwrite:
            assert overflow.lost and overflow_irq & irq_lost

        # 观测：停止发送后按Get Index读出四帧，数据序列是模式行为的主要判据。
        for expected_sequence in expected_sequences:
            received = can.rx_read(source)
            actual_sequences.append(received.data[0])
            can.rx_fifo_ack(fifo, received.index)
            record_observation(
                record_property,
                key="retained_frame",
                value={
                    "identifier": received.identifier,
                    "sequence": received.data[0],
                    "index": received.index,
                },
                source="dut",
                endpoint=f"RX_FIFO[{fifo}].FRAME",
            )
            assert received.identifier == identifier and received.data[0] == expected_sequence

        # 恢复：清Lost事件并写入新序号5，证明满后状态不阻塞后续正常接收。
        can.irq_clear(irq_lost)
        recovery_sequence = 5
        recovery_payload = bytes((recovery_sequence,)) + pattern(payload_bytes - 1, inverse=True)
        can.tx_write(
            0,
            CanTxFrame(
                identifier,
                CanFrameFlags.NONE,
                payload_bytes,
                recovery_sequence,
                recovery_payload,
            ),
        )
        can.tx_request(1)
        can.wait_tx_complete(1, timeout_s=TIMEOUT_S)
        can.wait_rx_available(fifo, timeout_s=TIMEOUT_S)
        recovered = can.rx_read(source)
        can.rx_fifo_ack(fifo, recovered.index)
        final = can.rx_fifo_status_get(fifo)

        # Evidence：恢复帧和终态均先记录，再执行最终强断言。
        record_observation(
            record_property,
            key="recovery_frame",
            value={
                "identifier": recovered.identifier,
                "sequence": recovered.data[0],
                "index": recovered.index,
                "data": recovered.data.hex(" ").upper(),
            },
            source="dut",
            endpoint=f"RX_FIFO[{fifo}].FRAME",
        )
        record_observation(
            record_property,
            key="final_status",
            value={
                "fill": final.fill,
                "get_index": final.get_index,
                "put_index": final.put_index,
                "full": final.full,
                "lost": final.lost,
            },
            source="dut",
            endpoint=f"RX_FIFO[{fifo}].STATUS",
        )

        # 判定：保留序列、恢复数据和终态同时保存，Overwrite不虚构Lost期望。
        record_property("fifo", fifo)
        record_property("mode", "overwrite" if overwrite else "blocking")
        record_property("retained_sequence", actual_sequences)
        record_property("overflow_raw", int(overflow_irq & irq_lost))
        record_property("recovery", recovered.data.hex(" ").upper())
        assert actual_sequences == expected_sequences
        assert recovered.identifier == identifier and recovered.data == recovery_payload
        assert final.fill == 0 and not final.full and not final.lost


# 测试 Feature：
# CAN Dedicated RX Buffer定向接收、64-bit New Data位图边界、独立清除与再次置位。
#
# 测试方法：
# 1. 按Capability选择Buffer 0、31、32、63等有效边界，分别配置唯一标准ID过滤器。
# 2. 逐个发送并读取目标Buffer，确认全部New Data位已置位且RX FIFO保持为空。
# 3. 先单独清一个位，再逐位清完；向Buffer 0重发新数据验证位图和内容更新。
#
# 通过条件：
# 1. 每个目标Buffer的ID和8-byte数据准确，相邻Buffer及FIFO没有误接收。
# 2. 低/高32-bit位图均能独立置位、清除并再次置位。
def test_can_p1_007_dedicated_rx_buffer_boundaries(
    can_support, resource_driver, record_property
) -> None:

    # 准备：索引仅取公开容量内的首尾和位图分界，ID与索引一一对应。
    support = can_support
    can = support.can
    payload_bytes = 8
    indices = rx_buffer_boundary_indices(support.ram_limits)
    layout = dedicated_loopback_ram(support, filter_count=len(indices))
    timing = CanTiming(
        phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    )
    identifiers = {index: 0x300 + position for position, index in enumerate(indices)}
    expected_low = sum(1 << index for index in indices if index < 32)
    expected_high = sum(1 << (index - 32) for index in indices if index >= 32)
    received_data = {}

    # Expected：边界索引、两组位图和各Buffer输入在读取NDAT前固定。
    record_property(
        "expected",
        {
            "indices": list(indices),
            "new_data_low": expected_low,
            "new_data_high": expected_high,
        },
    )

    # 清理：异常也复位当前CAN和整池资源，不逐项恢复Message RAM或位图。
    with case_cleanup_scope(
        lambda: (
            ("CAN reset", lambda: support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)),
            ("Resource pool reset", resource_driver.reset),
        )
    ):
        # 基线：复位后再进入INIT，确保Dedicated RX New Data位图初始为空。
        support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
        resource_driver.reset()

        # 配置：每个Filter精确指向一个不同Buffer；未匹配标准帧统一拒绝。
        can.initializing_set(True)
        can.wait_initializing(True, timeout_s=TIMEOUT_S)
        can.timing_set(timing)
        can.options_set(
            CanOptions(
                fd_enabled=False,
                brs_enabled=False,
                automatic_retry=True,
                tx_pause=False,
                edge_filter=False,
                protocol_exception=True,
                tdc_enabled=False,
                tdc_offset_cycles=0,
                tdc_filter_cycles=0,
                ram_watchdog_cycles=0,
            )
        )
        can.ram_layout_set(layout)

        # 配置每个独立Filter槽，当前循环不发送数据或读取硬件状态。
        for filter_index, buffer_index in enumerate(indices):
            identifier = identifiers[buffer_index]
            can.filter_set(
                filter_index,
                CanFilter(CanFilterType.RANGE, CanFilterAction.BUFFER, identifier, 0, buffer_index),
                extended=False,
            )
        can.loopback_set(CanLoopback.INTERNAL)
        can.bus_config_set(
            CanBusConfig(
                monitor=True,
                restricted=False,
                timestamp_divisor=1,
                timestamp_source=CanTimestampSource.INTERNAL,
                timeout_source=CanTimeoutSource.CONTINUOUS,
                timeout_period=0,
                timeout_enabled=False,
                reject_remote_ext=True,
                reject_remote_std=True,
                unmatched_ext=CanUnmatchedPolicy.REJECT,
                unmatched_std=CanUnmatchedPolicy.REJECT,
            )
        )
        can.initializing_set(False)
        can.wait_initializing(False, timeout_s=TIMEOUT_S)

        # 激励：逐个发送唯一ID和序号，等待对应New Data位后再发送下一帧。
        for sequence, buffer_index in enumerate(indices):
            identifier = identifiers[buffer_index]
            payload = bytes((buffer_index, sequence)) + pattern(
                payload_bytes - 2,
                inverse=bool(sequence & 1),
            )
            can.tx_write(
                0,
                CanTxFrame(identifier, CanFrameFlags.NONE, payload_bytes, sequence, payload),
            )
            can.tx_request(1)
            can.wait_tx_complete(1, timeout_s=TIMEOUT_S)
            status = can.rx_buffer_status_get()
            target_set = (
                bool(status.low & (1 << buffer_index))
                if buffer_index < 32
                else bool(status.high & (1 << (buffer_index - 32)))
            )
            record_observation(
                record_property,
                key="new_data_low",
                value=status.low,
                source="dut",
                endpoint="RX_BUFFER.NEW_DATA_LOW",
            )
            record_observation(
                record_property,
                key="new_data_high",
                value=status.high,
                source="dut",
                endpoint="RX_BUFFER.NEW_DATA_HIGH",
            )
            assert target_set

        # 观测：全部位同时保留；逐个读取真实Buffer且FIFO0没有误路由副本。
        all_set = can.rx_buffer_status_get()
        fifo = can.rx_fifo_status_get(0)
        record_observation(
            record_property,
            key="bitmap_low_all",
            value=all_set.low,
            source="dut",
            endpoint="RX_BUFFER.NEW_DATA_LOW",
        )
        record_observation(
            record_property,
            key="bitmap_high_all",
            value=all_set.high,
            source="dut",
            endpoint="RX_BUFFER.NEW_DATA_HIGH",
        )
        record_observation(
            record_property,
            key="fifo_status",
            value={"fill": fifo.fill, "full": fifo.full, "lost": fifo.lost},
            source="dut",
            endpoint="RX_FIFO[0].STATUS",
        )
        assert all_set.low == expected_low and all_set.high == expected_high
        assert fifo.fill == 0 and not fifo.lost

        # 读取每个目标Buffer的真实帧，位图继续保留到后续显式清除阶段。
        for sequence, buffer_index in enumerate(indices):
            actual = can.rx_read(CanRxSource.BUFFER, buffer_index)
            expected = bytes((buffer_index, sequence)) + pattern(
                payload_bytes - 2,
                inverse=bool(sequence & 1),
            )
            received_data[str(buffer_index)] = actual.data.hex(" ").upper()
            record_observation(
                record_property,
                key="rx_buffer_frame",
                value={
                    "index": actual.index,
                    "identifier": actual.identifier,
                    "data": actual.data.hex(" ").upper(),
                },
                source="dut",
                endpoint=f"RX_BUFFER[{buffer_index}].FRAME",
            )
            assert actual.index == buffer_index and actual.identifier == identifiers[buffer_index]
            assert actual.data == expected

        # 独立清除：先清第二项，确认其他New Data位保持，再逐项清空剩余位。
        isolated_index = indices[1] if len(indices) > 1 else indices[0]
        isolated_low = 1 << isolated_index if isolated_index < 32 else 0
        isolated_high = 1 << (isolated_index - 32) if isolated_index >= 32 else 0
        can.rx_buffer_ack(isolated_low, isolated_high)
        after_one = can.rx_buffer_status_get()
        record_observation(
            record_property,
            key="bitmap_low_after_one",
            value=after_one.low,
            source="dut",
            endpoint="RX_BUFFER.NEW_DATA_LOW",
        )
        record_observation(
            record_property,
            key="bitmap_high_after_one",
            value=after_one.high,
            source="dut",
            endpoint="RX_BUFFER.NEW_DATA_HIGH",
        )
        assert after_one.low == expected_low & ~isolated_low
        assert after_one.high == expected_high & ~isolated_high

        # 逐项确认剩余New Data位，重复清已经清零的目标位应保持无副作用。
        for buffer_index in indices:
            low = 1 << buffer_index if buffer_index < 32 else 0
            high = 1 << (buffer_index - 32) if buffer_index >= 32 else 0
            can.rx_buffer_ack(low, high)
        cleared = can.rx_buffer_status_get()
        record_observation(
            record_property,
            key="bitmap_low_cleared",
            value=cleared.low,
            source="dut",
            endpoint="RX_BUFFER.NEW_DATA_LOW",
        )
        record_observation(
            record_property,
            key="bitmap_high_cleared",
            value=cleared.high,
            source="dut",
            endpoint="RX_BUFFER.NEW_DATA_HIGH",
        )
        assert cleared.low == 0 and cleared.high == 0

        # 再次接收：向首Buffer发送反相新数据，验证位重新置位且内容已经更新。
        first_index = indices[0]
        recovery_marker = 0xA5
        recovery_payload = bytes((first_index, recovery_marker)) + pattern(
            payload_bytes - 2,
            inverse=True,
        )
        can.tx_write(
            0,
            CanTxFrame(
                identifiers[first_index],
                CanFrameFlags.NONE,
                payload_bytes,
                recovery_marker,
                recovery_payload,
            ),
        )
        can.tx_request(1)
        can.wait_tx_complete(1, timeout_s=TIMEOUT_S)
        repeated_status = can.rx_buffer_status_get()
        repeated = can.rx_read(CanRxSource.BUFFER, first_index)

        # Evidence：重新置位的两组位图和更新后的真实Buffer帧先于最终断言保存。
        record_observation(
            record_property,
            key="bitmap_low_repeated",
            value=repeated_status.low,
            source="dut",
            endpoint="RX_BUFFER.NEW_DATA_LOW",
        )
        record_observation(
            record_property,
            key="bitmap_high_repeated",
            value=repeated_status.high,
            source="dut",
            endpoint="RX_BUFFER.NEW_DATA_HIGH",
        )
        record_observation(
            record_property,
            key="rx_buffer_frame",
            value={
                "index": repeated.index,
                "identifier": repeated.identifier,
                "data": repeated.data.hex(" ").upper(),
            },
            source="dut",
            endpoint=f"RX_BUFFER[{first_index}].FRAME",
        )

        # 判定：记录具体Buffer、位图和数据，不能只输出一个布尔结果。
        record_property("indices", list(indices))
        record_property("new_data_all", {"low": all_set.low, "high": all_set.high})
        record_property("new_data_after_one", {"low": after_one.low, "high": after_one.high})
        record_property("buffer_payloads", received_data)
        record_property("repeated_payload", repeated.data.hex(" ").upper())
        repeated_low = 1 << first_index if first_index < 32 else 0
        repeated_high = 1 << (first_index - 32) if first_index >= 32 else 0
        assert repeated_status.low == repeated_low
        assert repeated_status.high == repeated_high
        assert repeated.identifier == identifiers[first_index] and repeated.data == recovery_payload


# =============================================================================
# TX Event FIFO
# =============================================================================


# 测试 Feature：
# CAN TX Event FIFO的新事件、水位、满、丢失、事件内容及Ack后恢复。
#
# 测试方法：
# 1. 复位CAN和资源池，配置深度4、水位2的TX Event FIFO及内部回环。
# 2. 依次发送5帧并保留每帧TX Event；在第1、2、4、5帧后读取状态与IRQ Raw。
# 3. FIFO满后读取并Ack前4项，核对ID、DLC、Marker、Event Type和硬件索引。
# 4. 排空后再发送第6帧，确认TX/RX及新事件均恢复，不要求硬件粘滞Lost自动清零。
#
# 通过条件：
# 1. FILL依次达到1、2、4且第5帧保持4；Watermark、Full、Lost在对应边界出现。
# 2. 前4项事件顺序、Marker和元数据准确，第5帧数据仍成功发送但事件未覆盖旧内容。
# 3. Ack后FILL清零，第6帧可生成并读取新的TX Event。
def test_can_p1_009_tx_event_fifo_watermark_full_and_recovery(
    can_support,
    resource_driver,
    record_property,
) -> None:

    # 准备：Expected只由固定输入序列和公开事件深度生成，不读取DUT结果。
    support = can_support
    can = support.can
    identifier = 0x369
    payload_bytes = 8
    event_depth = 4
    event_watermark = 2
    markers = (0x10, 0x11, 0x12, 0x13, 0x14)
    recovery_marker = 0x20
    tracked_irq = (
        CanIrqSource.TX_EVENT_NEW
        | CanIrqSource.TX_EVENT_WATERMARK
        | CanIrqSource.TX_EVENT_FULL
        | CanIrqSource.TX_EVENT_LOST
    )
    layout = tx_event_loopback_ram(support, watermark=event_watermark)
    timing = CanTiming(
        phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    )
    expected_event_indices = tuple(range(event_depth))
    expected_event_markers = markers[:event_depth]
    threshold_status = {}
    threshold_irq = {}

    # 报告：每个列表只登记一次，pytest在Case结束时采集已追加的真实值。
    # 空列表表示尚未到达该阶段；每次采样后、断言前追加，不重复登记历史快照。
    event_trace = []
    status_trace = []
    irq_trace = []
    rx_trace = []
    record_property("event_trace", event_trace)
    record_property("status_trace", status_trace)
    record_property("irq_trace", irq_trace)
    record_property("rx_trace", rx_trace)

    # Expected：先登记边界、事件顺序和恢复Marker，避免由Event读回反推期望。
    record_property(
        "expected",
        {
            "depth": event_depth,
            "watermark": event_watermark,
            "event_markers": list(expected_event_markers),
            "event_indices": list(expected_event_indices),
            "recovery_marker": recovery_marker,
        },
    )

    # 清理：失败或成功退出时，只整体复位当前CAN和资源池。
    with case_cleanup_scope(
        lambda: (
            ("CAN reset", lambda: support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)),
            ("Resource pool reset", resource_driver.reset),
        )
    ):
        # 隔离：先复位硬件和资源，排除上一Case遗留的控制状态。
        support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
        resource_driver.reset()

        # 配置：一个标准ID进入RX0；每个成功发送的帧同时请求保存TX Event。
        can.initializing_set(True)
        can.wait_initializing(True, timeout_s=TIMEOUT_S)
        can.timing_set(timing)
        can.options_set(
            CanOptions(
                fd_enabled=False,
                brs_enabled=False,
                automatic_retry=True,
                tx_pause=False,
                edge_filter=False,
                protocol_exception=True,
                tdc_enabled=False,
                tdc_offset_cycles=0,
                tdc_filter_cycles=0,
                ram_watchdog_cycles=0,
            )
        )
        can.ram_layout_set(layout)
        can.filter_set(
            0,
            CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, identifier, identifier),
            extended=False,
        )
        can.loopback_set(CanLoopback.INTERNAL)
        can.bus_config_set(
            CanBusConfig(
                monitor=True,
                restricted=False,
                timestamp_divisor=1,
                timestamp_source=CanTimestampSource.INTERNAL,
                timeout_source=CanTimeoutSource.CONTINUOUS,
                timeout_period=0,
                timeout_enabled=False,
                reject_remote_ext=True,
                reject_remote_std=True,
                unmatched_ext=CanUnmatchedPolicy.REJECT,
                unmatched_std=CanUnmatchedPolicy.REJECT,
            )
        )
        can.irq_mask_set(tracked_irq, False)
        can.irq_clear(tracked_irq)
        can.initializing_set(False)
        can.wait_initializing(False, timeout_s=TIMEOUT_S)

        # 激励：逐帧发送并立即读取RX0，防止RX深度干扰TX Event满/丢失边界。
        for sequence, marker in enumerate(markers, start=1):
            payload = bytes((sequence, marker)) + pattern(
                payload_bytes - 2,
                inverse=bool(sequence & 1),
            )
            can.tx_write(
                0,
                CanTxFrame(
                    identifier,
                    CanFrameFlags.STORE_EVENT,
                    payload_bytes,
                    marker,
                    payload,
                ),
            )
            can.tx_request(1)
            can.wait_tx_complete(1, timeout_s=TIMEOUT_S)
            can.wait_rx_available(0, timeout_s=TIMEOUT_S)
            received = can.rx_read(CanRxSource.FIFO0)
            can.rx_fifo_ack(0, received.index)
            record_observation(
                record_property,
                key="rx_frame",
                value={
                    "identifier": received.identifier,
                    "data": received.data,
                },
                source="dut",
                endpoint="RX_FIFO[0].FRAME",
            )
            rx_trace.append({"identifier": received.identifier, "data": received.data})
            assert received.identifier == identifier and received.data == payload

            # 观测：每次发送后保存Event状态；关键边界另外保存IRQ Raw。
            event_status = can.tx_event_status_get()
            record_observation(
                record_property,
                key="tx_event_status",
                value=asdict(event_status),
                source="dut",
                endpoint="TX_EVENT.STATUS",
            )
            status_trace.append(asdict(event_status))

            if sequence in (1, 2, 4, 5):
                irq_raw = can.irq_snapshot_get().raw_status & tracked_irq
                threshold_status[sequence] = event_status
                threshold_irq[sequence] = irq_raw
                record_observation(
                    record_property,
                    key="tx_event_irq",
                    value=int(irq_raw),
                    source="dut",
                    endpoint="IRQ.RAW.TX_EVENT",
                )
                irq_trace.append(f"0x{int(irq_raw):08X}")
                can.irq_clear(tracked_irq)

        # 边界判定：前四帧填满Event FIFO，第五帧不得覆盖但必须报告Lost。
        assert threshold_status[1].fill == 1 and not threshold_status[1].full
        assert not threshold_status[1].lost
        assert threshold_irq[1] & CanIrqSource.TX_EVENT_NEW
        assert not threshold_irq[1] & (
            CanIrqSource.TX_EVENT_WATERMARK
            | CanIrqSource.TX_EVENT_FULL
            | CanIrqSource.TX_EVENT_LOST
        )
        assert threshold_status[2].fill == 2 and not threshold_status[2].full
        assert not threshold_status[2].lost
        assert threshold_irq[2] & CanIrqSource.TX_EVENT_WATERMARK
        assert threshold_status[4].fill == event_depth and threshold_status[4].full
        assert not threshold_status[4].lost
        assert threshold_irq[4] & CanIrqSource.TX_EVENT_FULL
        assert threshold_status[5].fill == event_depth and threshold_status[5].full
        assert threshold_status[5].lost
        assert threshold_irq[5] & CanIrqSource.TX_EVENT_LOST

        # 读取与Ack：逐项核对实际事件，再用该项返回的Get Index进行确认。
        for expected_index, expected_marker in zip(
            expected_event_indices,
            expected_event_markers,
            strict=True,
        ):
            event = can.tx_event_read()
            record_observation(
                record_property,
                key="tx_event",
                value={
                    "index": event.index,
                    "identifier": event.identifier,
                    "flags": int(event.flags),
                    "dlc": event.dlc,
                    "timestamp": event.timestamp,
                    "event_type": int(event.event_type),
                    "marker": event.marker,
                },
                source="dut",
                endpoint=f"TX_EVENT[{event.index}]",
            )
            event_trace.append({"index": event.index, "marker": event.marker})
            assert event.index == expected_index
            assert event.identifier == identifier
            assert event.flags == CanFrameFlags.NONE and event.dlc == payload_bytes
            assert event.event_type is CanTxEventType.TRANSMITTED
            assert event.marker == expected_marker
            can.tx_event_ack(event.index)

        # 排空观测：FILL和FULL必须恢复；Lost可能是硬件粘滞历史事实，不伪造清零。
        drained = can.tx_event_status_get()
        record_observation(
            record_property,
            key="tx_event_status",
            value=asdict(drained),
            source="dut",
            endpoint="TX_EVENT.STATUS_AFTER_DRAIN",
        )
        status_trace.append(asdict(drained))
        assert drained.fill == 0 and not drained.full

        # 恢复刺激：排空后发送一帧，确认新的Event和RX数据均可再次产生。
        recovery_payload = bytes((0xA5, recovery_marker)) + pattern(payload_bytes - 2)
        can.tx_write(
            0,
            CanTxFrame(
                identifier,
                CanFrameFlags.STORE_EVENT,
                payload_bytes,
                recovery_marker,
                recovery_payload,
            ),
        )
        can.tx_request(1)
        can.wait_tx_complete(1, timeout_s=TIMEOUT_S)
        can.wait_rx_available(0, timeout_s=TIMEOUT_S)
        recovery_rx = can.rx_read(CanRxSource.FIFO0)
        can.rx_fifo_ack(0, recovery_rx.index)
        recovery_status = can.tx_event_status_get()
        record_observation(
            record_property,
            key="tx_event_status",
            value=asdict(recovery_status),
            source="dut",
            endpoint="TX_EVENT.STATUS_AFTER_RECOVERY",
        )
        status_trace.append(asdict(recovery_status))
        record_observation(
            record_property,
            key="rx_frame",
            value={"identifier": recovery_rx.identifier, "data": recovery_rx.data},
            source="dut",
            endpoint="RX_FIFO[0].FRAME",
        )
        rx_trace.append({"identifier": recovery_rx.identifier, "data": recovery_rx.data})
        recovery_event = can.tx_event_read()
        record_observation(
            record_property,
            key="tx_event",
            value=asdict(recovery_event),
            source="dut",
            endpoint="TX_EVENT.DATA",
        )
        event_trace.append({"index": recovery_event.index, "marker": recovery_event.marker})
        assert recovery_rx.data == recovery_payload
        assert recovery_status.fill == 1
        assert recovery_event.identifier == identifier
        assert recovery_event.event_type is CanTxEventType.TRANSMITTED
        assert recovery_event.marker == recovery_marker
        can.tx_event_ack(recovery_event.index)

        # 终态：记录原有最终查询再断言，失败时也保留最终实际状态。
        final_status = can.tx_event_status_get()
        record_observation(
            record_property,
            key="tx_event_status",
            value=asdict(final_status),
            source="dut",
            endpoint="TX_EVENT.STATUS_AFTER_FINAL_ACK",
        )
        status_trace.append(asdict(final_status))
        assert final_status.fill == 0


# =============================================================================
# Clock Stop请求与恢复
# =============================================================================


# 测试 Feature：
# CAN空闲停钟请求/应答、INIT进入及解除后的新帧收发。
#
# 测试方法：
# 1. 复位CAN和资源池，配置内部回环，发送PATTERN_A并读取/Ack接收帧。
# 2. 确认没有Pending TX后请求Clock Stop，等待实际ACK并读取INIT。
# 3. 保持CRG时钟开启，先撤销请求并等ACK解除，再清INIT，发送不同的PATTERN_B。
#
# 通过条件：
# 1. 请求后ACK和INIT均为1，撤销后ACK先为0，清INIT后恢复运行。
# 2. 两帧ID、格式、DLC和全部数据正确，TX无挂起、RX Ack后为空。
# 3. 仅验证停钟握手，不把请求位或命令成功当作ACK，也不宣称功耗通过。
def test_can_p1_015_clock_stop_and_recovery(can_support, resource_driver, record_property) -> None:

    # 准备：两组不同数据避免恢复阶段误读旧帧；时序来自实例时钟与公开上限。
    support = can_support
    can = support.can
    timing = CanTiming(
        phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    )
    layout = loopback_ram(support)
    clock_states, frame_text, tx_completed, rx_empty = [], [], [], []
    record_property("clock_states", clock_states)
    record_property("frame_text", frame_text)
    record_property("tx_completed", tx_completed)
    record_property("rx_empty", rx_empty)
    record_property("expected", {"before": PATTERN_A, "after": PATTERN_B})

    # 清理：每个退出路径都尝试CAN复位和资源整池复位，不改CRG输入时钟。
    with case_cleanup_scope(
        lambda: (
            ("CAN reset", lambda: support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)),
            ("Resource pool reset", resource_driver.reset),
        )
    ):
        # 隔离：先复位唯一参与的CAN，再复位资源池，不触碰控制UART。
        support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
        resource_driver.reset()

        # 配置：INIT窗口内设置Classic时序，关闭FD/BRS、TDC、Timeout等无关功能。
        can.initializing_set(True)
        can.wait_initializing(True, timeout_s=TIMEOUT_S)
        can.timing_set(timing)
        can.options_set(
            CanOptions(
                fd_enabled=False,
                brs_enabled=False,
                automatic_retry=True,
                tx_pause=False,
                edge_filter=False,
                protocol_exception=True,
                tdc_enabled=False,
                tdc_offset_cycles=0,
                tdc_filter_cycles=0,
                ram_watchdog_cycles=0,
            )
        )

        # 过滤与回环：只接收标准ID0x123到RX0；不用引脚、CAN盒子或外部仪器。
        can.ram_layout_set(layout)
        can.filter_set(
            0,
            CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x123, 0x123),
            extended=False,
        )
        can.loopback_set(CanLoopback.INTERNAL)
        can.bus_config_set(
            CanBusConfig(
                monitor=True,
                restricted=False,
                timestamp_divisor=1,
                timestamp_source=CanTimestampSource.INTERNAL,
                timeout_source=CanTimeoutSource.CONTINUOUS,
                timeout_period=0,
                timeout_enabled=False,
                reject_remote_ext=True,
                reject_remote_std=True,
                unmatched_ext=CanUnmatchedPolicy.REJECT,
                unmatched_std=CanUnmatchedPolicy.REJECT,
            )
        )
        can.initializing_set(False)
        can.wait_initializing(False, timeout_s=TIMEOUT_S)

        # 数据路径：第一次建立运行基线；握手完成后第二次验证新数据，不隐式重新配置。
        for sequence, payload in enumerate((PATTERN_A, PATTERN_B)):
            can.tx_write(0, CanTxFrame(0x123, CanFrameFlags.NONE, 8, sequence, payload))
            can.tx_request(1)
            tx = can.wait_tx_complete(1, timeout_s=TIMEOUT_S)
            can.wait_rx_available(0, timeout_s=TIMEOUT_S)
            received = can.rx_read(CanRxSource.FIFO0)
            can.rx_fifo_ack(0, received.index)
            drained = can.rx_fifo_status_get(0)

            # 观测：RX、TX和FIFO分别记录实际端点，摘要在断言前追加，失败现场也保留。
            record_observation(
                record_property,
                key="frame",
                value=asdict(received),
                source="dut",
                endpoint="RX.FRAME",
            )
            record_observation(
                record_property,
                key="completed",
                value=tx.completed,
                source="dut",
                endpoint="TX.COMPLETED",
            )
            record_observation(
                record_property,
                key="pending",
                value=tx.pending,
                source="dut",
                endpoint="TX.PENDING",
            )
            record_observation(
                record_property,
                key="rx",
                value=asdict(drained),
                source="dut",
                endpoint="RX0.STATUS",
            )
            frame_text.append(f"帧{sequence + 1}：{received.data.hex(' ').upper()}")
            tx_completed.append(tx.completed)
            rx_empty.append(drained.fill)
            assert received.identifier == 0x123 and received.flags == CanFrameFlags.NONE
            assert received.dlc == 8 and received.data == payload
            assert tx.completed & 1 and tx.pending == 0
            assert drained.fill == 0 and not drained.lost

            # 停钟握手只发生一次；恢复帧完成后直接结束，避免额外配置掩盖恢复问题。
            if sequence == 0:
                can.clock_stop_set(True)
                acknowledged = can.wait_clock_stop_ack(True, timeout_s=TIMEOUT_S)
                initializing = can.initializing_get()
                record_observation(
                    record_property,
                    key="stop_ack",
                    value=acknowledged,
                    source="dut",
                    endpoint="CLOCK.STOP_ACK",
                )
                record_observation(
                    record_property,
                    key="stop_init",
                    value=initializing,
                    source="dut",
                    endpoint="CONFIG.INIT",
                )
                clock_states.append(f"请求=1；ACK={int(acknowledged)}；INIT={int(initializing)}")
                assert acknowledged and initializing

                # 恢复顺序：先撤销请求并等ACK=0，再清INIT；绝不实际关闭CRG时钟。
                can.clock_stop_set(False)
                released = can.wait_clock_stop_ack(False, timeout_s=TIMEOUT_S)
                record_observation(
                    record_property,
                    key="released_ack",
                    value=released,
                    source="dut",
                    endpoint="CLOCK.STOP_ACK",
                )
                clock_states.append(f"请求=0；ACK={int(released)}")
                assert released is False
                can.initializing_set(False)
                can.wait_initializing(False, timeout_s=TIMEOUT_S)


# =============================================================================
# TX请求集合与发送顺序
# =============================================================================


# 测试 Feature：
# CAN专用Buffer、TX FIFO和TX Queue在三帧同时挂起时的发送顺序。
#
# 测试方法：
# 1. 每种组织独立复位CAN和资源池，配置三项TX与内部回环RX0。
# 2. 按0x300、0x100、0x200预装索引0/1/2，读回全部帧，确认没有Pending。
# 3. 一次批量请求三项，等待全部完成，按接收次序取出三帧并逐项Ack。
#
# 通过条件：
# 1. FIFO按0x300/0x100/0x200发送，Queue和专用Buffer按0x100/0x200/0x300发送。
# 2. 序号、完整数据和帧头一致，三项完成位有效、无Pending，TX/RX均回到空闲。
@pytest.mark.parametrize("mode", ("buffer", "fifo", "queue"))
def test_can_p1_008_tx_fifo_queue_order(
    can_support, resource_driver, record_property, mode
) -> None:

    # 准备：ID次序不同于数值优先次序；按公共文档以前四字节小端序号覆盖Pattern。
    support = can_support
    can = support.can
    layout = tx_order_ram(support, mode=mode)
    frames = tuple(
        CanTxFrame(
            identifier, CanFrameFlags.NONE, 8, index, index.to_bytes(4, "little") + PATTERN_A[4:]
        )
        for index, identifier in enumerate((0x300, 0x100, 0x200))
    )
    expected = frames if mode == "fifo" else (frames[1], frames[2], frames[0])
    order, preload = [], []
    record_property("mode", mode)
    record_property("expected", [asdict(frame) for frame in expected])
    record_property("order_text", order)
    record_property("preload_text", preload)

    # 清理：仅复位本Case CAN和整池资源，保留原始断言错误。
    with case_cleanup_scope(
        lambda: (
            ("CAN reset", lambda: support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)),
            ("Resource pool reset", resource_driver.reset),
        )
    ):
        # 隔离：硬件先复位，资源池随后清空，不触碰控制UART。
        support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
        resource_driver.reset()

        # 配置：Classic内部回环，三项TX和四项RX0；关闭无关计时和错误刺激。
        can.initializing_set(True)
        can.wait_initializing(True, timeout_s=TIMEOUT_S)
        can.timing_set(
            CanTiming(
                phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
                phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
            )
        )
        can.options_set(
            CanOptions(
                fd_enabled=False,
                brs_enabled=False,
                automatic_retry=True,
                tx_pause=False,
                edge_filter=False,
                protocol_exception=True,
                tdc_enabled=False,
                tdc_offset_cycles=0,
                tdc_filter_cycles=0,
                ram_watchdog_cycles=0,
            )
        )
        can.ram_layout_set(layout)
        can.filter_set(
            0,
            CanFilter(CanFilterType.RANGE, CanFilterAction.FIFO0, 0x100, 0x300),
            extended=False,
        )
        can.loopback_set(CanLoopback.INTERNAL)
        can.bus_config_set(
            CanBusConfig(
                monitor=True,
                restricted=False,
                timestamp_divisor=1,
                timestamp_source=CanTimestampSource.DISABLED,
                timeout_source=CanTimeoutSource.CONTINUOUS,
                timeout_period=0,
                timeout_enabled=False,
                reject_remote_ext=True,
                reject_remote_std=True,
                unmatched_ext=CanUnmatchedPolicy.REJECT,
                unmatched_std=CanUnmatchedPolicy.REJECT,
            )
        )
        can.initializing_set(False)
        can.wait_initializing(False, timeout_s=TIMEOUT_S)

        # 预装：全部写完、读回后才发请求；不通过逐槽发送改变仲裁输入集合。
        for index, frame in enumerate(frames):
            can.tx_write(index, frame)
            prepared = can.tx_read(index)
            record_observation(
                record_property,
                key="preload",
                value=asdict(prepared),
                source="dut",
                endpoint="TX.BUFFER",
            )
            preload.append(
                f"槽{index}：ID=0x{prepared.identifier:03X}，数据={prepared.data.hex(' ').upper()}"
            )
            assert prepared == frame

        # 启动：一次W1S请求三项，Pending基线必须为零；不使用循环单项请求。
        before = can.tx_status_get()
        record_observation(
            record_property,
            key="pending_before",
            value=before.pending,
            source="dut",
            endpoint="TX.PENDING",
        )
        assert before.pending == 0
        can.tx_request(0b111)
        completed = can.wait_tx_complete(0b111, timeout_s=TIMEOUT_S)
        record_observation(
            record_property,
            key="completed",
            value=completed.completed,
            source="dut",
            endpoint="TX.COMPLETED",
        )
        assert completed.completed & 0b111 == 0b111

        # 接收：预期次序独立给出，按FIFO真实Get Index读帧，记录后比较并Ack。
        for frame in expected:
            can.wait_rx_available(0, timeout_s=TIMEOUT_S)
            actual = can.rx_read(CanRxSource.FIFO0)
            record_observation(
                record_property,
                key="order",
                value=asdict(actual),
                source="dut",
                endpoint="RX.FRAME",
            )
            order.append(
                f"ID=0x{actual.identifier:03X}，序号={actual.data[0] if actual.data else '缺失'}"
            )
            assert actual.identifier == frame.identifier and actual.flags == frame.flags
            assert actual.dlc == frame.dlc and actual.data == frame.data
            can.rx_fifo_ack(0, actual.index)

        # 终态：额外帧、Pending、FIFO不空或丢帧都应失败，不能只比较三帧ID。
        final = can.tx_status_get()
        rx = can.rx_fifo_status_get(0)
        record_observation(
            record_property,
            key="pending",
            value=final.pending,
            source="dut",
            endpoint="TX.PENDING",
        )
        record_observation(
            record_property,
            key="free_count",
            value=final.free_count,
            source="dut",
            endpoint="TX.FIFO_FREE",
        )
        record_observation(
            record_property,
            key="rx_final",
            value=asdict(rx),
            source="dut",
            endpoint="RX0.STATUS",
        )
        assert final.pending == 0 and not final.full
        assert final.free_count == layout.tx_fifo_count
        assert rx.fill == 0 and not rx.lost
