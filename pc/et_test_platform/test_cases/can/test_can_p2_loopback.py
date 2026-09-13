# CAN内部/外部回环的引脚输出对照。
# 职责：先证明正常捕获，再用只听Observer比较内部静默与外部真实帧。
# 边界：只调用公共Driver和盒子API；错误捕获窗口不能解释成无外发。
# 依赖：CAN/GPIO/CRG、CAN盒子、统一Deadline和Evidence。

from dataclasses import asdict
from time import monotonic

import pytest

from ...core.deadline import OperationDeadline
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
from ...instruments.can_boxes.models import CanBusConfig as PeerBusConfig
from ...instruments.can_boxes.models import CanFrame as PeerFrame
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import PATTERN_A, TIMEOUT_S, loopback_ram, phase_timing

pytestmark = [pytest.mark.hardware, pytest.mark.ip("can")]
SILENT_WINDOW_S = 0.1


# 测试 Feature：
# 内部回环无引脚输出、外部回环有引脚输出，且两者本机都完成收发。
#
# 测试方法：
# 1. 保持同一接线，三个阶段Peer均以正常模式捕获，先完成Normal正对照帧。
# 2. 切内部回环发两帧并核对本机RX；观察100ms无外发。
# 3. 独立复位并改外部回环，Peer继续捕获，两帧必须被真实捕获。
# 4. 分别记录模式、TX完成、实际帧、窗口耗时和Observer错误，失败也清理。
#
# 通过条件：
# 1. 正对照有效，内部两帧本机通过而Observer为0帧，外部两帧两端均匹配。
# 2. 无设备错误、回显、丢帧或Bus Off，不把捕获异常作为静默通过。
def test_can_p2_005_loopback_pin_comparison(
    can_external_support, resource_driver, record_property
) -> None:

    # 准备：三阶段使用独立序号，不能把上一阶段遗留帧当作新的观察结果。
    support, gpio, pins, box = can_external_support
    can = support.can
    timing = CanTiming(
        phase_timing(support.clock_hz, 1_000_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    )
    record_property(
        "expected",
        "1M Classic ID=0x123；Normal序号0，Internal=1/2，External=3/4；内部捕获0帧，外部2帧",
    )
    captures = []
    loop_frames = []
    record_property("capture_summary", captures)
    record_property("loop_summary", loop_frames)

    # 异常边界：停止盒子之后再复位CAN及整池资源，不关闭控制UART。
    with case_cleanup_scope(
        lambda: (
            ("CAN box close", box.close),
            ("CAN reset", lambda: support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)),
            ("Resource pool reset", resource_driver.reset),
        )
    ):
        record_property("peer_identity", str(box.open()))

        # 引脚只来自已选连接；不触碰GPIO复位域。
        for number, function in pins:
            gpio.configure_signal(number, function, can.instance_id)
        deadline = OperationDeadline.start(TIMEOUT_S, label="CAN loopback pin comparison")

        # 三个阶段Peer均以正常模式捕获：外部回环忽略ACK且忽略RX引脚输入，Peer的ACK不改变判据。
        for stage, mode, sequences in (
            ("normal", CanLoopback.DISABLED, (0,)),
            ("internal", CanLoopback.INTERNAL, (1, 2)),
            ("external", CanLoopback.EXTERNAL, (3, 4)),
        ):
            support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
            resource_driver.reset()
            box.configure(PeerBusConfig(nominal_bitrate=1_000_000, listen_only=False))
            box.clear()
            can.initializing_set(True, timeout_s=deadline.remaining_s())
            can.wait_initializing(True, timeout_s=deadline.remaining_s())
            can.timing_set(timing, timeout_s=deadline.remaining_s())
            can.options_set(
                CanOptions(False, False, True, False, False, True, False, 0, 0, 0),
                timeout_s=deadline.remaining_s(),
            )
            can.ram_layout_set(loopback_ram(support), timeout_s=deadline.remaining_s())
            can.filter_set(
                0,
                CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x123, 0x123),
                extended=False,
                timeout_s=deadline.remaining_s(),
            )
            can.loopback_set(mode, timeout_s=deadline.remaining_s())
            can.bus_config_set(
                CanBusConfig(
                    monitor=stage == "internal",
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
                ),
                timeout_s=deadline.remaining_s(),
            )
            can.initializing_set(False, timeout_s=deadline.remaining_s())
            can.wait_initializing(False, timeout_s=deadline.remaining_s())
            actual_mode = can.loopback_get(timeout_s=deadline.remaining_s())
            record_observation(
                record_property,
                key="mode",
                value=int(actual_mode),
                source="dut",
                endpoint="CONFIG.LOOPBACK",
            )
            assert actual_mode == mode

            # 所有帧先确认本机TX；回环还必须读取本机RX，排除没有真正发送的假静默。
            for sequence in sequences:
                payload = sequence.to_bytes(4, "little") + PATTERN_A[4:]
                can.tx_write(
                    0,
                    CanTxFrame(0x123, CanFrameFlags.NONE, 8, 0, payload),
                    timeout_s=deadline.remaining_s(),
                )
                can.tx_request(1, timeout_s=deadline.remaining_s())
                tx = can.wait_tx_complete(1, timeout_s=deadline.remaining_s())
                record_observation(
                    record_property,
                    key="tx_complete",
                    value=tx.completed,
                    source="dut",
                    endpoint="TX.COMPLETED",
                )
                assert tx.completed & 1
                if stage != "normal":
                    can.wait_rx_available(0, timeout_s=deadline.remaining_s())
                    local = can.rx_read(CanRxSource.FIFO0, timeout_s=deadline.remaining_s())
                    record_observation(
                        record_property,
                        key="loop",
                        value=str(local),
                        source="dut",
                        endpoint="RX.FRAME",
                    )
                    loop_frames.append({"stage": stage, "frame": str(local)})
                    assert local.identifier == 0x123 and local.flags == CanFrameFlags.NONE
                    assert local.dlc == 8 and local.data == payload
                    can.rx_fifo_ack(0, local.index, timeout_s=deadline.remaining_s())
                if stage != "internal":
                    captured = box.receive(timeout_s=deadline.remaining_s())
                    record_observation(
                        record_property,
                        key="capture",
                        value=str(captured),
                        source="peer",
                        device_id=box.identity,
                        endpoint="CAN.CAPTURE",
                    )
                    captures.append({"stage": stage, "frame": str(captured)})
                    assert not captured.is_echo and captured.frame == PeerFrame(0x123, payload)

            # 内部回环观察完整100ms；只接受正常超时，任何返回帧或设备错误都失败。
            if stage == "internal":
                assert deadline.remaining_s() >= SILENT_WINDOW_S
                started = monotonic()
                unexpected = None
                capture_timed_out = False
                try:
                    unexpected = box.receive(timeout_s=SILENT_WINDOW_S)
                except TimeoutError:
                    capture_timed_out = True
                elapsed = monotonic() - started
                peer_error = box.error_get()
                record_observation(
                    record_property,
                    key="silent_capture",
                    value=str(unexpected),
                    source="peer",
                    device_id=box.identity,
                    endpoint="CAN.CAPTURE",
                )
                record_observation(
                    record_property,
                    key="peer_error",
                    value=peer_error,
                    source="peer",
                    device_id=box.identity,
                    endpoint="CAN.ERROR",
                )
                record_property("silent_window_elapsed_s", elapsed)
                captures.append(
                    {
                        "stage": stage,
                        "frame": str(unexpected),
                        "elapsed_s": elapsed,
                        "error": peer_error,
                    }
                )
                assert unexpected is None and capture_timed_out
                assert elapsed >= SILENT_WINDOW_S and peer_error == 0

            # 每阶段终态独立读取；外部观察失败时上面的决定性现场已保留。
            rx = can.rx_fifo_status_get(0, timeout_s=deadline.remaining_s())
            protocol = can.protocol_status_consume(timeout_s=deadline.remaining_s())
            record_observation(
                record_property,
                key="rx_status",
                value=asdict(rx),
                source="dut",
                endpoint="RX0.STATUS",
            )
            record_observation(
                record_property,
                key="bus_off",
                value=protocol.bus_off,
                source="dut",
                endpoint="PROTOCOL.BUS_OFF",
            )
            assert rx.fill == 0 and not rx.lost and not protocol.bus_off
