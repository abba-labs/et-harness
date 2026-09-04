# CAN P0基础数据通路。
# 职责：明确配置、逐帧激励、独立硬件观测和完整数据断言。
# 边界：实例/IO来自连接文件，时钟与RAM几何来自芯片映射；不直写寄存器。
# 依赖：CAN/CRG/Resource Driver、只读Support与既有Evidence接口。

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
from ._support import PATTERN_A, PATTERN_B, TIMEOUT_S, loopback_ram, phase_timing

pytestmark = [pytest.mark.hardware, pytest.mark.ip("can")]


# ------------------------------ 内部回环 ------------------------------


# 测试 Feature：
# CAN内部回环的Classic标准帧发送、接收、FIFO Ack和数据完整性。
#
# 测试方法：
# 1. 复位选中CAN和整池资源；配置500 kbit/s内部回环、单ID过滤与四项RX FIFO。
# 2. 两组独立8-byte数据逐帧发送，等待TX完成和RX可读，再读取完整帧并Ack。
# 3. 每帧核对ID、格式、DLC、长度和所有字节，记录FIFO填充变化及Lost。
#
# 通过条件：
# 1. 两帧均完成发送，实际元数据和全部数据与输入一致。
# 2. FIFO每帧由空到非空再回空，Lost始终未置位；不声称验证了外部引脚。
def test_can_p0_002_internal_loopback(can_support, resource_driver, record_property) -> None:

    # 准备：输入与实际帧独立，位时序只由输入时钟及明确速率计算。
    support = can_support
    can = support.can
    timing = CanTiming(
        phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    )
    layout = loopback_ram(support)
    expected = (PATTERN_A, PATTERN_B)
    record_property(
        "expected",
        "ID=0x123；DLC=8；" + " / ".join(payload.hex(" ").upper() for payload in expected),
    )

    # 隔离：本Case只有CAN内部回环，复位该CAN及资源池，不碰控制UART或其他IP。
    support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
    resource_driver.reset()

    # 清理：无论哪项断言失败，都尝试CAN复位和整池复位，保留原始失败原因。
    with case_cleanup_scope(
        lambda: (
            ("CAN reset", lambda: support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)),
            ("Resource pool reset", resource_driver.reset),
        )
    ):
        # 配置窗口：请求INIT并确认后设置明确时序；Classic禁FD/BRS，保留自动重发。
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

        # 配置RAM与过滤：只接收标准ID0x123到RX0，所有未匹配帧拒绝。
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

        # 启动：模式必须实际读回为内部回环；不配置GPIO，不启动DMA或IRQ捕获。
        can.initializing_set(False)
        can.wait_initializing(False, timeout_s=TIMEOUT_S)
        actual_mode = can.loopback_get()
        actual_timing = can.timing_get()
        record_property("mode", actual_mode.name)
        record_property("timing", str(actual_timing))
        assert actual_mode is CanLoopback.INTERNAL
        assert actual_timing == timing
        frame_lines = []

        # 激励：两帧顺序执行，每帧必须发送完成并接收/Ack后才能准备下一帧。
        for sequence, payload in enumerate(expected, start=1):
            before = can.rx_fifo_status_get(0)
            outgoing = CanTxFrame(0x123, CanFrameFlags(0), 8, sequence, payload)
            can.tx_write(0, outgoing)
            can.tx_request(1)
            tx = can.wait_tx_complete(1, timeout_s=TIMEOUT_S)
            ready = can.wait_rx_available(0, timeout_s=TIMEOUT_S)

            # 观测：先读取实际帧并Ack该索引，再读FIFO终态；记录数据后才断言。
            actual = can.rx_read(CanRxSource.FIFO0)
            can.rx_fifo_ack(0, actual.index)
            after = can.rx_fifo_status_get(0)
            frame_lines.append(
                f"帧{sequence}：ID=0x{actual.identifier:X}，flags=0x{int(actual.flags):02X}，"
                f"DLC={actual.dlc}，长度={len(actual.data)}，数据={actual.data.hex(' ').upper()}"
            )
            record_property("frame_text", "\n".join(frame_lines))
            record_property(
                f"frame_{sequence}",
                {
                    "id": actual.identifier,
                    "flags": int(actual.flags),
                    "dlc": actual.dlc,
                    "data": list(actual.data),
                    "tx_completed": tx.completed,
                    "fill_before": before.fill,
                    "fill_ready": ready.fill,
                    "fill_after": after.fill,
                },
            )
            record_observation(
                record_property,
                key="frame",
                value={
                    "identifier": actual.identifier,
                    "flags": int(actual.flags),
                    "dlc": actual.dlc,
                    "data": list(actual.data),
                },
                source="dut",
                endpoint="RX.FRAME",
            )
            record_observation(
                record_property,
                key="rx_fill",
                value=[before.fill, ready.fill, after.fill],
                source="dut",
                endpoint="RX0.FILL",
            )
            record_observation(
                record_property,
                key="rx_lost",
                value=[before.lost, ready.lost, after.lost],
                source="dut",
                endpoint="RX0.LOST",
            )
            record_observation(
                record_property,
                key="tx_completed",
                value=tx.completed,
                source="dut",
                endpoint="TX.COMPLETED",
            )

            # 判定：命令接受不等于数据正确，必须逐字段和逐Byte比较并确认无残留。
            assert actual.identifier == outgoing.identifier
            assert actual.flags == CanFrameFlags(0) and actual.dlc == 8
            assert actual.data == payload and len(actual.data) == len(payload)
            assert not actual.nonmatching and actual.filter_index == 0
            assert tx.completed & 1
            assert (before.fill, ready.fill, after.fill) == (0, 1, 0)
            assert not (before.lost or ready.lost or after.lost)
