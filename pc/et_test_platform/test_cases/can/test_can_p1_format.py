# CAN FD ISO/Non-ISO格式矩阵。
# 职责：实际格式读回、匹配双向通信、失配首次错误及ISO恢复取证。
# 边界：不访问寄存器，不以发送成功或接收超时替代协议差异证据。
# 依赖：CAN/GPIO/CRG Driver、CAN FD Peer和统一Deadline/Evidence。

from dataclasses import asdict
from time import monotonic

import pytest

from ...core.deadline import OperationDeadline
from ...drivers.can import (
    CanBusConfig,
    CanError,
    CanFilter,
    CanFilterAction,
    CanFilterType,
    CanFrameFlags,
    CanIrqSource,
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
from ...instruments.can_boxes.models import CanBusConfig as PeerBusConfig
from ...instruments.can_boxes.models import CanFrame as PeerFrame
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import TIMEOUT_S, loopback_ram, pattern, phase_timing

pytestmark = [pytest.mark.hardware, pytest.mark.ip("can")]
NEGATIVE_WINDOW_S = 0.1


# 测试 Feature：
# ISO/Non-ISO两种FD编码匹配收发、交叉格式拒绝及恢复。
#
# 测试方法：
# 1. 四种DUT/Peer格式组合分别执行16/64-byte，固定500k/2M及BRS。
# 2. 逐节点复位，配置实际读回，两端禁重发；匹配时双向核对完整帧。
# 3. 失配时Peer单发，等待真实IRQ后首次读PSR，100ms内不得产生有效RX。
# 4. 清错误并重新基线到ISO，双向收发证明恢复；全节点共用5秒Deadline。
#
# 通过条件：
# 1. 同格式及恢复帧全部相等；失配必须同时有协议错误IRQ、真实错误码和零RX。
# 2. 不接受回显、错误帧、丢帧、残留IRQ或Bus Off，失败也清理Peer/CAN资源。
@pytest.mark.parametrize("length", (16, 64))
@pytest.mark.parametrize(
    "dut_non_iso,peer_non_iso", ((False, False), (True, True), (False, True), (True, False))
)
def test_can_p1_020_fd_format_matrix(
    can_external_support, resource_driver, record_property, length, dut_non_iso, peer_non_iso
) -> None:

    # 准备：Expected只来自固定输入；两种长度分别覆盖FD的两类CRC长度。
    support, gpio, pins, box = can_external_support
    can = support.can
    timing = CanTiming(
        phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    )
    payload = pattern(length)
    dlc = 10 if length == 16 else 15
    flags = CanFrameFlags.FD | CanFrameFlags.BRS
    errors = CanIrqSource.PROTOCOL_ARBITRATION | CanIrqSource.PROTOCOL_DATA
    format_summary, result_summary = [], []
    record_property("format_summary", format_summary)
    record_property("result_summary", result_summary)
    captures = []
    record_property("peer_capture_summary", "NOT_OBSERVED")
    record_property(
        "expected",
        {
            "dut_non_iso": dut_non_iso,
            "peer_non_iso": peer_non_iso,
            "payload": payload.hex(),
            "dlc": dlc,
            "timing": asdict(timing),
        },
    )

    # 清理：停止Peer刺激后复位CAN及Service，整池复位最后执行。
    with case_cleanup_scope(
        lambda: (
            ("CAN box close", box.close),
            ("CAN reset", lambda: support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)),
            ("Resource pool reset", resource_driver.reset),
        )
    ):
        record_property("peer_identity", str(box.open()))
        # 引脚只选连接映射，不复位控制UART所在GPIO域。
        for number, function in pins:
            gpio.configure_signal(number, function, can.instance_id)
        deadline = OperationDeadline.start(TIMEOUT_S, label="CAN FD format node")

        # 每个参数都执行主阶段和ISO恢复阶段，恢复结果不能替代主阶段。
        for stage, dut_format, peer_format in (
            ("primary", dut_non_iso, peer_non_iso),
            ("recovery", False, False),
        ):
            # 隔离：CAN及Service复位后整池复位，清空Peer历史捕获。
            support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
            resource_driver.reset()
            box.configure(
                PeerBusConfig(nominal_bitrate=500_000, data_bitrate=2_000_000, non_iso=peer_format)
            )
            box.clear()
            record_property("peer_format_request", {"stage": stage, "non_iso": peer_format})
            can.initializing_set(True, timeout_s=deadline.remaining_s())
            can.wait_initializing(True, timeout_s=deadline.remaining_s())
            can.timing_set(timing, timeout_s=deadline.remaining_s())
            can.options_set(
                CanOptions(True, True, False, False, False, False, False, 0, 0, 0),
                timeout_s=deadline.remaining_s(),
            )
            can.non_iso_set(dut_format, timeout_s=deadline.remaining_s())
            can.ram_layout_set(
                loopback_ram(support, payload_bytes=64), timeout_s=deadline.remaining_s()
            )
            can.filter_set(
                0,
                CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x123, 0x123),
                extended=False,
                timeout_s=deadline.remaining_s(),
            )
            can.loopback_set(CanLoopback.DISABLED, timeout_s=deadline.remaining_s())
            can.bus_config_set(
                CanBusConfig(
                    False,
                    False,
                    1,
                    CanTimestampSource.DISABLED,
                    CanTimeoutSource.CONTINUOUS,
                    0,
                    False,
                    True,
                    True,
                    CanUnmatchedPolicy.REJECT,
                    CanUnmatchedPolicy.REJECT,
                ),
                timeout_s=deadline.remaining_s(),
            )
            actual_format = can.non_iso_get(timeout_s=deadline.remaining_s())
            options = can.options_get(timeout_s=deadline.remaining_s())
            format_summary.append(
                {"stage": stage, "non_iso": actual_format, "options": asdict(options)}
            )
            record_observation(
                record_property,
                key="non_iso",
                value=actual_format,
                source="dut",
                endpoint="CONFIG.NON_ISO",
            )
            record_observation(
                record_property,
                key="automatic_retry",
                value=options.automatic_retry,
                source="dut",
                endpoint="CONFIG.AUTOMATIC_RETRY",
            )
            assert actual_format is dut_format
            assert options.automatic_retry is False
            can.irq_clear(errors, timeout_s=deadline.remaining_s())
            baseline = can.protocol_status_consume(timeout_s=deadline.remaining_s())
            record_property("baseline_protocol", asdict(baseline))
            can.initializing_set(False, timeout_s=deadline.remaining_s())
            can.wait_initializing(False, timeout_s=deadline.remaining_s())

            # 失配只刺激一次：先等真实Raw，再消费首个协议状态，期间不发成功帧。
            if dut_format != peer_format:
                started = monotonic()
                box.send(PeerFrame(0x123, payload, fd=True, brs=True), single_shot=True)
                irq = can.wait_irq_pending(
                    errors, timeout_s=min(NEGATIVE_WINDOW_S, deadline.remaining_s())
                )
                protocol = can.protocol_status_consume(timeout_s=deadline.remaining_s())
                record_observation(
                    record_property,
                    key="error_irq",
                    value=int(irq.raw_status),
                    source="dut",
                    endpoint="IRQ.RAW",
                )
                record_observation(
                    record_property,
                    key="first_last_error",
                    value=int(protocol.last_error),
                    source="dut",
                    endpoint="PROTOCOL.LAST_ERROR",
                )
                record_observation(
                    record_property,
                    key="first_data_error",
                    value=int(protocol.data_last_error),
                    source="dut",
                    endpoint="PROTOCOL.DATA_LAST_ERROR",
                )
                result_summary.append(
                    {"stage": stage, "irq": int(irq.raw_status), "protocol": asdict(protocol)}
                )
                assert irq.raw_status & errors
                assert protocol.last_error not in (
                    CanError.NONE,
                    CanError.UNCHANGED,
                ) or protocol.data_last_error not in (CanError.NONE, CanError.UNCHANGED)
                # 负向窗口只补足剩余观察时间，不用固定延时替代事件等待。
                remaining_window = NEGATIVE_WINDOW_S - (monotonic() - started)
                if remaining_window > 0:
                    deadline.sleep(remaining_window)
                elapsed = monotonic() - started
                record_property("negative_elapsed_s", elapsed)
                assert elapsed >= NEGATIVE_WINDOW_S
            else:
                # 匹配及恢复：DUT先发一帧，由独立Peer核对全部字段，拒绝本机回显。
                can.tx_write(
                    0, CanTxFrame(0x123, flags, dlc, 0, payload), timeout_s=deadline.remaining_s()
                )
                can.tx_request(1, timeout_s=deadline.remaining_s())
                tx = can.wait_tx_complete(1, timeout_s=deadline.remaining_s())
                record_observation(
                    record_property,
                    key="tx_completed",
                    value=tx.completed,
                    source="dut",
                    endpoint="TX.COMPLETED",
                )
                assert tx.completed & 1
                received = box.receive(timeout_s=deadline.remaining_s())
                captures.append({"stage": stage, "frame": str(received)})
                record_property("peer_capture_summary", captures)
                record_observation(
                    record_property,
                    key="peer_frames",
                    value=str(received),
                    source="peer",
                    device_id=box.identity,
                    endpoint="CAN.CAPTURE",
                )
                assert received is not None and not received.is_echo
                assert received.frame == PeerFrame(0x123, payload, fd=True, brs=True)
                box.send(PeerFrame(0x123, payload, fd=True, brs=True), single_shot=True)
                ready = can.wait_rx_available(0, timeout_s=deadline.remaining_s())
                dut_frame = can.rx_read(CanRxSource.FIFO0, timeout_s=deadline.remaining_s())
                record_observation(
                    record_property,
                    key="dut_frames",
                    value=str(dut_frame),
                    source="dut",
                    endpoint="RX.FRAME",
                )
                record_observation(
                    record_property,
                    key="ready_fill",
                    value=ready.fill,
                    source="dut",
                    endpoint="RX0.FILL",
                )
                record_observation(
                    record_property,
                    key="ready_lost",
                    value=ready.lost,
                    source="dut",
                    endpoint="RX0.LOST",
                )
                assert ready.fill == 1 and not ready.lost
                assert dut_frame.identifier == 0x123 and dut_frame.flags == flags
                assert dut_frame.dlc == dlc and dut_frame.data == payload
                can.rx_fifo_ack(0, dut_frame.index, timeout_s=deadline.remaining_s())
                protocol = can.protocol_status_consume(timeout_s=deadline.remaining_s())
                result_summary.append(
                    {"stage": stage, "protocol": asdict(protocol), "rx": str(dut_frame)}
                )

            # 终态：失配必须零RX，匹配在Ack后也须排空；错误清除后再读Raw。
            rx = can.rx_fifo_status_get(0, timeout_s=deadline.remaining_s())
            record_observation(
                record_property, key="rx_fill", value=rx.fill, source="dut", endpoint="RX0.FILL"
            )
            record_observation(
                record_property, key="rx_lost", value=rx.lost, source="dut", endpoint="RX0.LOST"
            )
            record_observation(
                record_property,
                key="bus_off",
                value=protocol.bus_off,
                source="dut",
                endpoint="PROTOCOL.BUS_OFF",
            )
            assert rx.fill == 0
            assert rx.lost is False
            assert protocol.bus_off is False
            can.irq_clear(errors, timeout_s=deadline.remaining_s())
            cleared = can.irq_snapshot_get(timeout_s=deadline.remaining_s())
            record_observation(
                record_property,
                key="cleared_irq",
                value=int(cleared.raw_status),
                source="dut",
                endpoint="IRQ.RAW",
            )
            assert not cleared.raw_status & errors
