# CAN TDC开启后的外部FD通信。
# 职责：配置读回、双向独立帧比较、实际采样点和错误状态取证。
# 边界：不测物理延迟极限；芯片时序仅来自只读Mapping，不直写寄存器。
# 依赖：CAN/GPIO/CRG Driver、CAN盒子和公共Deadline/Evidence接口。

from dataclasses import asdict

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
from ._support import TIMEOUT_S, loopback_ram, pattern, phase_timing

pytestmark = [pytest.mark.hardware, pytest.mark.ip("can")]


# 测试 Feature：
# TDC Enable/Offset/Filter读回及开启补偿后的FD BRS外部收发。
#
# 测试方法：
# 1. 独立复位、配置1M仲裁和2M/5M数据时序，开启Profile指定的TDC。
# 2. 核对硬件配置；DUT发送两个不同序号的64-byte帧，Peer实际捕获。
# 3. Peer反向发送两帧，DUT逐帧读取并Ack，检查完整元数据和有效字节。
# 4. 读取采样点、TX Pending、RX Lost及Bus Off；每节点使用统一5秒边界。
#
# 通过条件：
# 1. TDC配置和时序等于输入，双向各两帧完全匹配，没有回显、Lost或Bus Off。
# 2. 不把采样点常量或TDC关闭失败作为判据，不声称补偿极限通过。
@pytest.mark.parametrize("data_bitrate", (2_000_000, 5_000_000))
def test_can_p1_021_tdc_external_fd(
    can_external_support, resource_driver, record_property, data_bitrate
) -> None:

    # 准备：Profile只提供芯片合法时序；Expected来自固定输入，不依赖捕获数据。
    support, gpio, pins, box = can_external_support
    can = support.can
    phase, offset = support.mapping.CAN_TDC_TIMING_PROFILES[support.clock_hz][data_bitrate]
    timing = CanTiming(
        phase_timing(support.clock_hz, 1_000_000, support.timing_limits.nominal),
        CanPhaseTiming(*phase),
    )
    options = CanOptions(True, True, True, False, False, True, True, offset, 0, 0)
    tdc_summary = []
    record_property("tdc_summary", tdc_summary)
    flags = CanFrameFlags.FD | CanFrameFlags.BRS
    forward = tuple(i.to_bytes(4, "little") + pattern(64)[4:] for i in (1, 2))
    reverse = tuple(i.to_bytes(4, "little") + pattern(64, inverse=True)[4:] for i in (3, 4))
    record_property(
        "expected",
        {
            "timing": asdict(timing),
            "tdc_offset": offset,
            "forward": [p.hex() for p in forward],
            "reverse": [p.hex() for p in reverse],
        },
    )

    # 清理：先关闭外部Peer再复位DUT及资源，失败也不能污染下一节点。
    with case_cleanup_scope(
        lambda: (
            ("CAN box close", box.close),
            ("CAN reset", lambda: support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)),
            ("Resource pool reset", resource_driver.reset),
        )
    ):
        support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
        resource_driver.reset()

        # GPIO仅配置连接文件指定的信号，保留控制UART所在复位域。
        for number, function in pins:
            gpio.configure_signal(number, function, can.instance_id)
        record_property("peer_identity", str(box.open()))
        box.configure(PeerBusConfig(nominal_bitrate=1_000_000, data_bitrate=data_bitrate))
        box.clear()
        deadline = OperationDeadline.start(TIMEOUT_S, label="CAN TDC FD rate node")

        # 配置：显式Normal FD/BRS，不借用内部回环证明物理总线。
        can.initializing_set(True, timeout_s=deadline.remaining_s())
        can.wait_initializing(True, timeout_s=deadline.remaining_s())
        can.timing_set(timing, timeout_s=deadline.remaining_s())
        can.options_set(options, timeout_s=deadline.remaining_s())
        can.ram_layout_set(
            loopback_ram(support, payload_bytes=64), timeout_s=deadline.remaining_s()
        )
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
        actual_options = can.options_get(timeout_s=deadline.remaining_s())
        actual_timing = can.timing_get(timeout_s=deadline.remaining_s())
        tdc_summary.append({"options": asdict(actual_options), "timing": asdict(actual_timing)})

        # 原子观测：逐字段保存读回，不把独立字段组合成一个布尔PASS。
        record_observation(
            record_property,
            key="tdc_enabled",
            value=actual_options.tdc_enabled,
            source="dut",
            endpoint="CONFIG.TDC_ENABLED",
        )
        record_observation(
            record_property,
            key="tdc_offset_cycles",
            value=actual_options.tdc_offset_cycles,
            source="dut",
            endpoint="CONFIG.TDC_OFFSET",
        )
        record_observation(
            record_property,
            key="tdc_filter_cycles",
            value=actual_options.tdc_filter_cycles,
            source="dut",
            endpoint="CONFIG.TDC_FILTER",
        )
        assert actual_options.tdc_enabled is True
        assert actual_options.tdc_offset_cycles == options.tdc_offset_cycles
        assert actual_options.tdc_filter_cycles == 0
        record_observation(
            record_property,
            key="bit_timing",
            value=asdict(actual_timing),
            source="dut",
            endpoint="CONFIG.BIT_TIMING",
        )
        assert actual_timing == timing
        can.initializing_set(False, timeout_s=deadline.remaining_s())
        can.wait_initializing(False, timeout_s=deadline.remaining_s())

        # 正向：独立Peer捕获，不接受本机发送回显；帧完整相等涵盖FD/BRS/DLC及64字节。
        for payload in forward:
            can.tx_write(
                0, CanTxFrame(0x123, flags, 15, 0, payload), timeout_s=deadline.remaining_s()
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
            protocol = can.protocol_status_consume(timeout_s=deadline.remaining_s())
            tdc_summary.append({"sample_point": protocol.tdc_position})
            record_observation(
                record_property,
                key="tdc_sample_point",
                value=protocol.tdc_position,
                source="dut",
                endpoint="TDC.SAMPLE_POINT",
            )

        # 反向：Peer单次发送，DUT读取后才Ack；不以发送API成功代替接收。
        for payload in reverse:
            box.send(PeerFrame(0x321, payload, fd=True, brs=True), single_shot=True)
            ready = can.wait_rx_available(0, timeout_s=deadline.remaining_s())
            dut_frame = can.rx_read(CanRxSource.FIFO0, timeout_s=deadline.remaining_s())
            record_observation(
                record_property,
                key="dut_frames",
                value=str(dut_frame),
                source="dut",
                endpoint="RX.FRAME",
            )
            assert ready.fill == 1 and not ready.lost
            assert dut_frame.identifier == 0x321 and dut_frame.flags == flags
            assert dut_frame.dlc == 15 and dut_frame.data == payload
            can.rx_fifo_ack(0, dut_frame.index, timeout_s=deadline.remaining_s())

        # 终态：分别记录Pending、Lost、Fill和Bus Off，实际采样点不参与极限判定。
        tx = can.tx_status_get(timeout_s=deadline.remaining_s())
        rx = can.rx_fifo_status_get(0, timeout_s=deadline.remaining_s())
        protocol = can.protocol_status_consume(timeout_s=deadline.remaining_s())
        # 各字段单独取证和比较，保留首个失败字段的真实读数。
        for key, actual, expected, endpoint in (
            ("tx_pending", tx.pending, 0, "TX.PENDING"),
            ("rx_fill", rx.fill, 0, "RX0.FILL"),
            ("rx_lost", rx.lost, False, "RX0.LOST"),
            ("bus_off", protocol.bus_off, False, "PROTOCOL.BUS_OFF"),
        ):
            record_observation(
                record_property, key=key, value=actual, source="dut", endpoint=endpoint
            )
            assert actual == expected
