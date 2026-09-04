# CAN P1帧格式与DLC边界。
# 职责：明确配置、双Pattern激励、实际帧观测和独立Expected比较。
# 边界：不把内部回环当作外部位速率测量，不在Case绑定芯片地址或实例。
# 依赖：CAN/CRG/Resource公共Driver及只读Support。

import pytest

from ...drivers.can import (
    CanBusConfig,
    CanFilter,
    CanFilterAction,
    CanFilterType,
    CanFrameFlags,
    CanLoopback,
    CanOptions,
    CanRxSource,
    CanTimeoutSource,
    CanTimestampSource,
    CanTiming,
    CanTxFrame,
    CanUnmatchedPolicy,
)
from ...drivers.crg import CrgPeripheral
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import FD_LENGTHS, TIMEOUT_S, loopback_ram, pattern, phase_timing

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
