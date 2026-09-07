# CAN有界FIFO连续收发。
# 职责：固定20轮双向各32帧的全量数据、序号和错误取证。
# 边界：不测极限吞吐率，不逐帧复位，不以发送调用次数替代接收。
# 依赖：CAN/CRG/GPIO公共Driver、FD Peer、纯布局与时序映射。

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
    CanLoopback,
    CanOptions,
    CanPhaseTiming,
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
from ._support import TIMEOUT_S, batch_fifo_ram, pattern, phase_timing

pytestmark = [pytest.mark.hardware, pytest.mark.ip("can")]


# 测试 Feature：
# FD 64-byte/BRS连续FIFO收发，无复位跨20轮保存完整数据与序号。
#
# 测试方法：
# 1. 配置32项TX/RX FIFO，Normal模式1M/5M，读回时序和选项。
# 2. 每轮先写32个不同序号TX槽，一次提交全部，再由Peer逐条捕获。
# 3. Peer反向连发32帧，DUT等待FIFO累计32条后逐条读取及Ack。
# 4. 每轮独立5秒Deadline，保存累计实收数量、挂起和协议错误。
# 5. 20轮后两方向各640帧；额外100ms Peer静默窗口不能接收多余帧。
#
# 通过条件：
# 1. 全部ID、Flags、DLC、序号和64字节严格匹配，没有截断或末尾坏字节。
# 2. 无Lost、Bus Off、协议错误或残留TX；首错停止但仍清理所有参与资源。
def test_can_p3_001_bounded_fifo_traffic(
    can_external_support, resource_driver, record_property
) -> None:

    support, gpio, pins, box = can_external_support
    can = support.can
    rounds, depth = 20, 32
    mask = (1 << depth) - 1
    nominal_bitrate, data_bitrate = 1_000_000, 5_000_000
    phase, offset = support.mapping.CAN_TDC_TIMING_PROFILES[support.clock_hz][data_bitrate]
    timing = CanTiming(
        phase_timing(support.clock_hz, nominal_bitrate, support.timing_limits.nominal),
        CanPhaseTiming(*phase),
    )
    options = CanOptions(True, True, False, False, False, True, True, offset, 0, 0)
    layout = batch_fifo_ram(support, count=depth, payload_bytes=64)
    flags = CanFrameFlags.FD | CanFrameFlags.BRS
    counts, status_summary = [], []
    forward_count = reverse_count = 0
    record_property("counts", counts)
    record_property("status_summary", status_summary)
    # 报告只展示实收计数和最近帧；全部1280帧仍逐条进入原始Observation。
    peer_summary = {"count": 0, "last_frame": "NOT_OBSERVED"}
    dut_summary = {"count": 0, "last_frame": "NOT_OBSERVED"}
    record_property("peer_frame_summary", peer_summary)
    record_property("dut_frame_summary", dut_summary)
    record_property(
        "expected",
        {
            "rounds": rounds,
            "depth": depth,
            "each_direction": rounds * depth,
            "timing": asdict(timing),
            "sequence": "round*64 + offset; forward0..31/reverse32..63",
        },
    )

    # 清理：只有一次启动和一次最终复位，首错不能触发自动重跑。
    with case_cleanup_scope(
        lambda: (
            ("CAN box close", box.close),
            ("CAN reset", lambda: support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)),
            ("Resource pool reset", resource_driver.reset),
        )
    ):
        support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
        resource_driver.reset()
        # 仅使用已选连接的信号复用，不重配通信UART。
        for number, function in pins:
            gpio.configure_signal(number, function, can.instance_id)
        record_property("peer_identity", str(box.open()))
        box.configure(PeerBusConfig(nominal_bitrate=nominal_bitrate, data_bitrate=data_bitrate))
        box.clear()
        deadline = OperationDeadline.start(TIMEOUT_S, label="CAN batch setup")
        can.initializing_set(True, timeout_s=deadline.remaining_s())
        can.wait_initializing(True, timeout_s=deadline.remaining_s())
        can.timing_set(timing, timeout_s=deadline.remaining_s())
        can.options_set(options, timeout_s=deadline.remaining_s())
        can.ram_layout_set(layout, timeout_s=deadline.remaining_s())
        can.filter_set(
            0,
            CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x321, 0x321),
            extended=False,
            timeout_s=deadline.remaining_s(),
        )
        can.loopback_set(CanLoopback.DISABLED, timeout_s=deadline.remaining_s())
        can.bus_config_set(
            CanBusConfig(
                monitor=False,
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
        actual_timing = can.timing_get(timeout_s=deadline.remaining_s())
        actual_options = can.options_get(timeout_s=deadline.remaining_s())
        record_observation(
            record_property,
            key="timing",
            value=asdict(actual_timing),
            source="dut",
            endpoint="CONFIG.BIT_TIMING",
        )
        record_observation(
            record_property,
            key="retry",
            value=actual_options.automatic_retry,
            source="dut",
            endpoint="CONFIG.AUTOMATIC_RETRY",
        )
        assert actual_timing == timing and actual_options == options
        can.initializing_set(False, timeout_s=deadline.remaining_s())
        can.wait_initializing(False, timeout_s=deadline.remaining_s())

        # 固定轮次：不清缓存、不重配模式、不复位，重复与残留会进入下一轮的强比较。
        for round_index in range(rounds):
            deadline = OperationDeadline.start(TIMEOUT_S, label=f"CAN batch round {round_index}")
            forward = tuple(
                (round_index * depth * 2 + i).to_bytes(4, "little") + pattern(64)[4:]
                for i in range(depth)
            )
            reverse = tuple(
                (round_index * depth * 2 + depth + i).to_bytes(4, "little")
                + pattern(64, inverse=True)[4:]
                for i in range(depth)
            )
            before = can.tx_status_get(timeout_s=deadline.remaining_s())
            record_observation(
                record_property,
                key="tx_free",
                value=before.free_count,
                source="dut",
                endpoint="TX.FREE",
            )
            assert before.free_count == depth and before.pending == 0 and before.put_index == 0
            # 批量预装：32项全部准备后才发一个请求，不能退化为逐帧等待完成。
            for index, payload in enumerate(forward):
                can.tx_write(
                    index,
                    CanTxFrame(0x123, flags, 15, 0, payload),
                    timeout_s=deadline.remaining_s(),
                )
            can.tx_request(mask, timeout_s=deadline.remaining_s())
            tx = can.wait_tx_complete(mask, timeout_s=deadline.remaining_s())
            record_observation(
                record_property,
                key="tx_complete",
                value=tx.completed,
                source="dut",
                endpoint="TX.COMPLETED",
            )
            assert tx.completed == mask and tx.pending == 0 and tx.cancelled == 0
            # 全量Peer捕获：Expected来自预先生成序号和Pattern，完整帧相等包含FD/BRS标志。
            for payload in forward:
                received = box.receive(timeout_s=deadline.remaining_s())
                peer_summary.update(count=forward_count + 1, last_frame=str(received))
                record_observation(
                    record_property,
                    key="peer_frames",
                    value=str(received),
                    source="peer",
                    device_id=box.identity,
                    endpoint="CAN.CAPTURE",
                )
                assert not received.is_echo and received.frame == PeerFrame(
                    0x123, payload, fd=True, brs=True
                )
                forward_count += 1
            # 连续反向：先提交全部32帧，不穿插DUT读取，实际FIFO承受整批数据。
            for payload in reverse:
                deadline.remaining_s()
                box.send(PeerFrame(0x321, payload, fd=True, brs=True), single_shot=True)
            # FIFO必须实际累计整批；超时由本轮统一Deadline上抛。
            while True:
                rx_status = can.rx_fifo_status_get(0, timeout_s=deadline.remaining_s())
                record_observation(
                    record_property,
                    key="batch_lost",
                    value=rx_status.lost,
                    source="dut",
                    endpoint="RX0.LOST",
                )
                record_observation(
                    record_property,
                    key="batch_fill",
                    value=rx_status.fill,
                    source="dut",
                    endpoint="RX0.FILL",
                )
                assert not rx_status.lost and rx_status.fill <= depth
                if rx_status.fill == depth:
                    break
                deadline.sleep(0.001)
            # 逐条消费：每条保存完整数据再判定，读取成功不等于正确接收。
            for payload in reverse:
                frame = can.rx_read(CanRxSource.FIFO0, timeout_s=deadline.remaining_s())
                dut_summary.update(count=reverse_count + 1, last_frame=str(frame))
                record_observation(
                    record_property,
                    key="frames",
                    value=str(frame),
                    source="dut",
                    endpoint=f"RX0[{frame.index}].FRAME",
                )
                assert frame.identifier == 0x321 and frame.flags == flags
                assert frame.dlc == 15 and frame.data == payload
                can.rx_fifo_ack(0, frame.index, timeout_s=deadline.remaining_s())
                reverse_count += 1
            counts.append(
                {
                    "round": round_index + 1,
                    "peer_received": forward_count,
                    "dut_received": reverse_count,
                }
            )
            tx = can.tx_status_get(timeout_s=deadline.remaining_s())
            rx_status = can.rx_fifo_status_get(0, timeout_s=deadline.remaining_s())
            protocol = can.protocol_status_consume(timeout_s=deadline.remaining_s())
            peer_error = box.error_get()
            status_summary.append(
                {
                    "round": round_index + 1,
                    "tx": asdict(tx),
                    "rx": asdict(rx_status),
                    "protocol": asdict(protocol),
                    "peer_error": peer_error,
                }
            )
            # 每轮终态各自取证，不允许错误重试、Bus Off或额外数据被累计数量掩盖。
            for key, value in (
                ("tx_pending", tx.pending),
                ("rx_fill", rx_status.fill),
                ("rx_lost", rx_status.lost),
                ("bus_off", protocol.bus_off),
                ("tx_errors", protocol.tx_error_count),
                ("rx_errors", protocol.rx_error_count),
                ("error_log", protocol.error_log_count),
            ):
                record_observation(
                    record_property, key=key, value=value, source="dut", endpoint=key
                )
                assert value == 0
            record_observation(
                record_property,
                key="peer_error",
                value=peer_error,
                source="peer",
                device_id=box.identity,
                endpoint="CHANNEL.ERROR",
            )
            assert peer_error == 0
            assert protocol.last_error in (CanError.NONE, CanError.UNCHANGED)
            assert protocol.data_last_error in (CanError.NONE, CanError.UNCHANGED)
        assert forward_count == reverse_count == rounds * depth

        # 最后一批也不能隐藏多发：完整100ms静默且Observer无错误才接受超时。
        quiet_s = 0.1
        assert deadline.remaining_s() > quiet_s
        start = monotonic()
        try:
            unexpected = box.receive(timeout_s=quiet_s)
        except TimeoutError:
            elapsed = monotonic() - start
            record_property("quiet_seconds", elapsed)
            assert elapsed >= quiet_s
            assert box.error_get() == 0
        else:
            peer_summary.update(count=forward_count + 1, last_frame=str(unexpected))
            record_observation(
                record_property,
                key="peer_frames",
                value=str(unexpected),
                source="peer",
                device_id=box.identity,
                endpoint="CAN.EXTRA_CAPTURE",
            )
            raise AssertionError("CAN batch emitted an extra frame after the final round")
