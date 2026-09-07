# CAN固定位时钟下的速率矩阵。
# 职责：按公开Profile计算时序、实读配置并进行外部双向完整帧检查。
# 边界：不修改CRG输入时钟；Profile频率不是寄存器读数或示波器实测。
# 依赖：CAN/GPIO/CRG Driver、Peer、纯时序公式和统一Deadline。

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
RATE_NODES = (
    (125_000, None),
    (250_000, None),
    (500_000, None),
    (800_000, None),
    (1_000_000, None),
    (500_000, 2_000_000),
    (500_000, 5_000_000),
    (1_000_000, 2_000_000),
    (1_000_000, 5_000_000),
)


# 测试 Feature：
# 固定输入时钟下五种Classic速率、四种FD仲裁/数据组合。
#
# 测试方法：
# 1. Profile指定输入时钟，不配置bypass的CRG分频；复位DUT和资源。
# 2. 独立公式计算实际速率/采样点，设置两端Normal模式并实读DUT时序。
# 3. DUT向Peer发两组8/64-byte，Peer反向发另外两组；FD显式开启BRS/TDC。
# 4. 逐帧比较完整数据和格式，记录实际TX/RX终态及无Bus Off。
#
# 通过条件：
# 1. 所有九组速率配置精确，读回匹配，双向四帧均完整且无回显。
# 2. Pending/Fill归零，无Lost和Bus Off；不声明分频或物理频率精度通过。
@pytest.mark.parametrize("nominal_bitrate,data_bitrate", RATE_NODES)
def test_can_p1_012_bitrate_matrix(
    can_external_support, resource_driver, record_property, nominal_bitrate, data_bitrate
):

    support, gpio, pins, box = can_external_support
    can = support.can
    fd = data_bitrate is not None
    size, dlc = (64, 15) if fd else (8, 8)
    flags = CanFrameFlags.FD | CanFrameFlags.BRS if fd else CanFrameFlags.NONE
    timing = CanTiming(
        phase_timing(
            support.clock_hz,
            nominal_bitrate,
            support.timing_limits.nominal,
            quanta=25 if nominal_bitrate == 800_000 else 20,
        ),
        phase_timing(
            support.clock_hz,
            data_bitrate or 2_000_000,
            support.timing_limits.data,
            quanta=8 if data_bitrate == 5_000_000 else 20,
        ),
    )
    offset = (1 + timing.data.segment1) * timing.data.prescaler if fd else 0
    options = CanOptions(fd, fd, True, False, False, True, fd, offset, 0, 0)
    forward = tuple(i.to_bytes(4, "little") + pattern(size)[4:] for i in (1, 2))
    reverse = tuple(i.to_bytes(4, "little") + pattern(size, inverse=True)[4:] for i in (3, 4))
    timing_trace = []
    record_property("timing", timing_trace)
    record_property(
        "expected",
        {
            "input_clock_hz": support.clock_hz,
            "clock_source": "chip_profile",
            "nominal_bitrate": nominal_bitrate,
            "data_bitrate": data_bitrate,
            "forward": [p.hex() for p in forward],
            "reverse": [p.hex() for p in reverse],
        },
    )
    # 独立公式确认每个时序的实际速率和合法SJW，不把配置对象回显当硬件读回。
    for name, phase, requested in (
        ("nominal", timing.nominal, nominal_bitrate),
        ("data", timing.data, data_bitrate or 2_000_000),
    ):
        total = 1 + phase.segment1 + phase.segment2
        assert support.clock_hz == requested * phase.prescaler * total
        assert 0 < phase.sjw <= min(phase.segment1, phase.segment2)
        timing_trace.append(
            {
                "phase": name,
                "configured_bitrate": requested,
                "sample_point": (1 + phase.segment1) / total,
                "input_source": "chip_profile",
            }
        )

    # 清理：先关闭Peer，再复位CAN和整池资源；不修改时钟源或控制UART。
    with case_cleanup_scope(
        lambda: (
            ("CAN box close", box.close),
            ("CAN reset", lambda: support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)),
            ("Resource pool reset", resource_driver.reset),
        )
    ):
        # 隔离：每个速率节点重建CAN/Resource空基线。
        support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
        resource_driver.reset()
        # 只配置当前连接文件明确的RX/TX引脚。
        for number, function in pins:
            gpio.configure_signal(number, function, can.instance_id)
        record_property("peer_identity", str(box.open()))
        box.configure(
            PeerBusConfig(nominal_bitrate=nominal_bitrate, data_bitrate=data_bitrate or 2_000_000)
        )
        box.clear()
        deadline = OperationDeadline.start(TIMEOUT_S, label="CAN bitrate node")

        # 配置：Classic不启用FD；FD数据相位开启TDC，Normal模式提供真实ACK链路。
        can.initializing_set(True, timeout_s=deadline.remaining_s())
        can.wait_initializing(True, timeout_s=deadline.remaining_s())
        can.timing_set(timing, timeout_s=deadline.remaining_s())
        can.options_set(options, timeout_s=deadline.remaining_s())
        can.ram_layout_set(
            loopback_ram(support, payload_bytes=size), timeout_s=deadline.remaining_s()
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
        actual_timing = can.timing_get(timeout_s=deadline.remaining_s())
        actual_options = can.options_get(timeout_s=deadline.remaining_s())
        record_observation(
            record_property,
            key="bit_timing",
            value=asdict(actual_timing),
            source="dut",
            endpoint="CONFIG.BIT_TIMING",
        )
        record_observation(
            record_property,
            key="options",
            value=asdict(actual_options),
            source="dut",
            endpoint="CONFIG.OPTIONS",
        )
        timing_trace.append(
            {"actual_timing": asdict(actual_timing), "options": asdict(actual_options)}
        )
        assert actual_timing == timing and actual_options == options
        can.initializing_set(False, timeout_s=deadline.remaining_s())
        can.wait_initializing(False, timeout_s=deadline.remaining_s())

        # 正向：两组不同序号，独立Peer捕获完整帧，拒绝发送回显。
        for payload in forward:
            can.tx_write(
                0, CanTxFrame(0x123, flags, dlc, 0, payload), timeout_s=deadline.remaining_s()
            )
            can.tx_request(1, timeout_s=deadline.remaining_s())
            tx = can.wait_tx_complete(1, timeout_s=deadline.remaining_s())
            record_observation(
                record_property,
                key="tx_complete",
                value=asdict(tx),
                source="dut",
                endpoint="TX.STATE",
            )
            assert tx.completed & 1 and not tx.pending & 1
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
            assert received.frame == PeerFrame(0x123, payload, fd=fd, brs=fd)

        # 反向：Peer单次发送，完整读取DUT后才Ack，不能以API接受替代实际接收。
        for payload in reverse:
            box.send(PeerFrame(0x321, payload, fd=fd, brs=fd), single_shot=True)
            ready = can.wait_rx_available(0, timeout_s=deadline.remaining_s())
            frame = can.rx_read(CanRxSource.FIFO0, timeout_s=deadline.remaining_s())
            record_observation(
                record_property,
                key="frame",
                value=str(frame),
                source="dut",
                endpoint="RX.FRAME",
            )
            assert ready.fill == 1 and not ready.lost
            assert frame.identifier == 0x321 and frame.flags == flags
            assert frame.dlc == dlc and frame.data == payload
            can.rx_fifo_ack(0, frame.index, timeout_s=deadline.remaining_s())

        # 终态：分别保存并检查队列归零、Lost和Bus Off。
        tx = can.tx_status_get(timeout_s=deadline.remaining_s())
        rx = can.rx_fifo_status_get(0, timeout_s=deadline.remaining_s())
        protocol = can.protocol_status_consume(timeout_s=deadline.remaining_s())
        # 字段原值进入证据，不只记录一个组合布尔值。
        for key, actual, expected in (
            ("pending", tx.pending, 0),
            ("fill", rx.fill, 0),
            ("lost", rx.lost, False),
            ("bus_off", protocol.bus_off, False),
        ):
            record_observation(
                record_property,
                key=key,
                value=actual,
                source="dut",
                endpoint=f"FINAL.{key}",
            )
            assert actual == expected
