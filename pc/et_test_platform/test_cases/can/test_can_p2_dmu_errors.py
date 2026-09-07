# CAN DMU最短非法窗口刺激及独立IRQ、复位后真实DMA恢复。
# 职责：Case显式编排九个独立故障节点，保存首个ISR值并比较合法恢复帧。
# 边界：只调用命名窗口Driver，不访问任意地址；不推测DMUIR W1C。
# 依赖：公共CAN/DMA/SYSCTRL/Resource、只读Mapping和统一Evidence。

from dataclasses import asdict, replace

import pytest

from ...core.deadline import OperationDeadline
from ...drivers.can import (
    CanBusConfig,
    CanDmuElement,
    CanDmuError,
    CanDmuRequest,
    CanEventFormat,
    CanFilter,
    CanFilterAction,
    CanFilterType,
    CanFrameFlags,
    CanLoopback,
    CanOptions,
    CanTimeoutSource,
    CanTimestampSource,
    CanTiming,
    CanTxFrame,
    CanUnmatchedPolicy,
)
from ...drivers.crg import CrgPeripheral
from ...drivers.dma import (
    DmaAddressMode,
    DmaBurst,
    DmaConfig,
    DmaIrqEvent,
    DmaTransferType,
    DmaWidth,
)
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import TIMEOUT_S, dmu_ram, pattern, phase_timing

pytestmark = [pytest.mark.hardware, pytest.mark.ip("can")]

# 每行只有一种违规；参数是公共语义，不包含芯片寄存器位号。
FAULTS = (
    ("tx_read", CanDmuError.TX_READ),
    ("rx1_write", CanDmuError.RX1_WRITE),
    ("event_write", CanDmuError.EVENT_WRITE),
    ("rx1_empty", CanDmuError.RX1_DEQUEUE),
    ("event_empty", CanDmuError.EVENT_DEQUEUE),
    ("tx_dlc", CanDmuError.TX_DLC),
    ("configuration", CanDmuError.CONFIGURATION_ACCESS),
    ("tx_start", CanDmuError.TX_START),
    ("tx_sequence", CanDmuError.TX_SEQUENCE),
)


# 测试 Feature：
# DMU非法读写、空出队、超容量DLC、CCE访问及起址/步进错误产生真实专用IRQ。
#
# 测试方法：
# 1. 每节点复位并建立8-byte FIFO独立基线，确认没有DMA活动和旧DMU错误。
# 2. 只注册目标DMU错误源，执行该节点最短窗口访问，保存ISR首个读值和实例。
# 3. 停止捕获后硬复位CAN，重新配置，通过DMA发一帧Classic回环并DMA收回。
# 4. 核对实际帧、DMA完成、DMU入出队及恢复后错误；不猜W1C、不用API成功替代IRQ。
#
# 通过条件：
# 1. 九个独立节点目标错误和真实ISR同时成立，无回调Fault或错误实例归属。
# 2. 每节点复位后的合法DMA收发数据准确、计数为1/1，无残留错误或DMA活动。
@pytest.mark.parametrize("fault,expected_error", FAULTS, ids=[item[0] for item in FAULTS])
def test_can_p2_007_dmu_illegal_irq(
    can_support,
    can_dma_support,
    resource_driver,
    record_property,
    fault,
    expected_error,
) -> None:

    support, transport = can_support, can_dma_support
    controller = transport.controller
    can, dma, sysctrl = support.can, transport.dma, transport.sysctrl
    mapping = support.mapping
    requests = mapping.CAN_DMU_REQUESTS[can.instance_id]
    layout = replace(
        dmu_ram(support),
        tx_payload_bytes=8,
        rx0_payload_bytes=8,
        rx1_payload_bytes=8,
        rx0_count=2,
        rx1_count=2,
        event_count=2,
    )
    expected = CanTxFrame(0x123, CanFrameFlags(0), 8, 0, pattern(8))
    record_property("expected", f"fault={fault}; target={expected_error.name}; recovery={expected}")
    record_property("error", "NOT_OBSERVED")
    record_property("irq", "NOT_OBSERVED")
    record_property("recovery", "NOT_OBSERVED")
    tx_channel, rx_channel = 0, 1
    tx_interface, rx_interface = 0, 1
    word_bytes = mapping.CAN_DMU_WORD_BYTES
    frame_bytes = mapping.CAN_RAM_HEADER_BYTES + 8
    with case_cleanup_scope(
        lambda: (
            ("DMU IRQ stop", can.dmu_capture_stop),
            ("TX DMA stop", lambda: dma.stop(tx_channel)),
            ("RX DMA stop", lambda: dma.stop(rx_channel)),
            ("TX DMA deconfigure", lambda: dma.deconfigure(tx_channel)),
            ("RX DMA deconfigure", lambda: dma.deconfigure(rx_channel)),
            ("TX request release", lambda: sysctrl.release_dma_request(controller, tx_interface)),
            ("RX request release", lambda: sysctrl.release_dma_request(controller, rx_interface)),
            ("DMA disable", dma.controller_disable),
            ("DMA reset", lambda: support.crg.reset(CrgPeripheral.DMA, instance=controller)),
            ("CAN reset", lambda: support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)),
            ("Resource reset", resource_driver.reset),
        )
    ):
        # 两阶段都从硬复位重建；第二阶段是独立恢复判定而非隐式重试。
        for recovery in (False, True):
            can.dmu_capture_stop()
            # 隔离：先停止辅助总线主设备，再复位CAN及Resource Pool。
            support.crg.reset(CrgPeripheral.DMA, instance=controller)
            support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
            resource_driver.reset()
            dma.deconfigure(tx_channel)
            dma.deconfigure(rx_channel)
            deadline = OperationDeadline.start(TIMEOUT_S, label="CAN DMU illegal/recovery")
            can.initializing_set(True, timeout_s=deadline.remaining_s())
            can.wait_initializing(True, timeout_s=deadline.remaining_s())
            can.timing_set(
                CanTiming(
                    phase_timing(support.clock_hz, 1_000_000, support.timing_limits.nominal),
                    phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
                ),
                timeout_s=deadline.remaining_s(),
            )
            can.options_set(
                CanOptions(True, True, False, False, False, True, False, 0, 0, 0),
                timeout_s=deadline.remaining_s(),
            )
            can.event_format_set(CanEventFormat(8, False), timeout_s=deadline.remaining_s())
            can.ram_layout_set(layout, timeout_s=deadline.remaining_s())
            can.filter_set(
                0,
                CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO1, 0x123, 0x123),
                extended=False,
                timeout_s=deadline.remaining_s(),
            )
            can.loopback_set(CanLoopback.INTERNAL, timeout_s=deadline.remaining_s())
            can.bus_config_set(
                CanBusConfig(
                    True,
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
            can.dmu_request_set(CanDmuRequest.RX1, timeout_s=deadline.remaining_s())
            if recovery or fault != "configuration":
                can.initializing_set(False, timeout_s=deadline.remaining_s())
                can.wait_initializing(False, timeout_s=deadline.remaining_s())
            else:
                can.configuration_write_set(True, timeout_s=deadline.remaining_s())
            baseline = can.dmu_status_consume(timeout_s=deadline.remaining_s())
            counters = can.dmu_counters_get(timeout_s=deadline.remaining_s())
            rx_before = can.rx_fifo_status_get(1, timeout_s=deadline.remaining_s())
            event_before = can.tx_event_status_get(timeout_s=deadline.remaining_s())
            tx_before = can.tx_status_get(timeout_s=deadline.remaining_s())
            # 注入前的零错误及空队列排除前一节点残留。
            for key, value, endpoint in (
                ("error_baseline", int(baseline.errors), "DMU.ERROR"),
                (
                    "counters_baseline",
                    [
                        counters.tx_enqueued,
                        counters.rx0_dequeued,
                        counters.rx1_dequeued,
                        counters.tx_event_dequeued,
                    ],
                    "DMU.COUNTERS",
                ),
                ("rx_baseline", asdict(rx_before), "RX.FIFO_STATUS"),
                ("event_baseline", asdict(event_before), "TX.EVENT_STATUS"),
                ("tx_pending_baseline", tx_before.pending, "TX.PENDING"),
                ("tx_full_baseline", tx_before.full, "TX.FIFO.FULL"),
                ("tx_free_baseline", tx_before.free_count, "TX.FIFO.FREE_COUNT"),
                ("tx_put_baseline", tx_before.put_index, "TX.FIFO.PUT_INDEX"),
            ):
                record_observation(
                    record_property, key=key, value=value, source="dut", endpoint=endpoint
                )
            assert baseline.errors == CanDmuError.NONE
            assert (
                counters.tx_enqueued
                == counters.rx0_dequeued
                == counters.rx1_dequeued
                == counters.tx_event_dequeued
                == 0
            )
            assert rx_before.fill == event_before.fill == 0
            assert not tx_before.full and tx_before.pending == 0 and tx_before.free_count > 0
            configuration_write = can.configuration_write_get()
            record_observation(
                record_property,
                key="configuration_write",
                value=configuration_write,
                source="dut",
                endpoint="CONFIGURATION.WRITE_ENABLED",
            )
            assert configuration_write == (not recovery and fault == "configuration")
            image = can.dmu_tx_image_encode(expected, timeout_s=deadline.remaining_s())

            if not recovery:
                # PC只拆分目标生成的镜像word；不解释芯片Header字段。
                words = tuple(
                    int.from_bytes(image[offset : offset + word_bytes], "little")
                    for offset in range(0, len(image), word_bytes)
                )
                if fault == "tx_dlc":
                    oversized = can.dmu_tx_image_encode(
                        CanTxFrame(0x123, CanFrameFlags.FD, 15, 0, pattern(64)),
                        timeout_s=deadline.remaining_s(),
                    )
                    words = tuple(
                        int.from_bytes(oversized[offset : offset + word_bytes], "little")
                        for offset in range(0, len(oversized), word_bytes)
                    )
                # 最短刺激序列在Case中显式可见；固件一次命令只访问一个word。
                accesses = {
                    "tx_read": ((CanDmuElement.TX, 0, False, 0),),
                    "rx1_write": ((CanDmuElement.RX1, 0, True, 0),),
                    "event_write": ((CanDmuElement.TX_EVENT, 0, True, 0),),
                    "rx1_empty": ((CanDmuElement.RX1, 0, False, 0),),
                    "event_empty": ((CanDmuElement.TX_EVENT, 0, False, 0),),
                    "tx_dlc": (
                        (CanDmuElement.TX, 0, True, words[0]),
                        (CanDmuElement.TX, 1, True, words[1]),
                    ),
                    "tx_sequence": (
                        (CanDmuElement.TX, 0, True, words[0]),
                        (CanDmuElement.TX, 2, True, words[2]),
                    ),
                    "tx_start": ((CanDmuElement.TX, 1, True, words[1]),),
                    "configuration": ((CanDmuElement.TX, 0, True, words[0]),),
                }[fault]
                can.dmu_capture_start(expected_error, timeout_s=deadline.remaining_s())
                initial_event = can.dmu_event_get(timeout_s=deadline.remaining_s())
                record_property("irq_initial", asdict(initial_event))
                assert initial_event.event_count == 0 and initial_event.fault_flags == 0
                # 每次只执行预先选定的一条命名窗口访问，不补写缺失word。
                for element, index, write, value in accesses:
                    result = can.dmu_word_access(
                        element, index, write=write, value=value, timeout_s=deadline.remaining_s()
                    )
                    record_property(
                        "access_stimulus",
                        {
                            "element": element.name,
                            "word": index,
                            "write": write,
                            "value": value,
                            "returned": result,
                        },
                    )
                    # 写命令返回的是输入回显，只有读访问的返回值才属于硬件Observation。
                    if not write:
                        record_observation(
                            record_property,
                            key="access_returned",
                            value=result,
                            source="dut",
                            endpoint=f"DMU.{element.name}.WORD[{index}]",
                        )
                event = can.wait_dmu_event(
                    initial_event.event_count, timeout_s=deadline.remaining_s()
                )
                # Service锁存、掩码及计数是软件事实；仅首个原始读值归属硬件。
                record_property("irq", asdict(event))
                record_observation(
                    record_property,
                    key="error",
                    value=int(event.raw_status),
                    source="dut",
                    endpoint="DMU.ERROR",
                )
                assert event.raw_status & expected_error
                assert (
                    event.masked_status & expected_error and event.latched_events & expected_error
                )
                assert event.event_count > 0 and event.generation == initial_event.generation
                assert event.instance_id == can.instance_id
                assert event.fault_flags == event.unexpected_count == event.overflow_count == 0
                can.dmu_capture_stop(timeout_s=deadline.remaining_s())
                continue

            # 恢复只用真实DMA搬运；CPU不补写DMU或补Ack来伪装完成。
            source = resource_driver.create(frame_bytes)
            destination = resource_driver.create(frame_bytes)
            resource_driver.write(source, image)
            resource_driver.write(destination, b"\xa5" * frame_bytes)
            tx_endpoint = can.dmu_endpoint_get(CanDmuElement.TX)
            rx_endpoint = can.dmu_endpoint_get(CanDmuElement.RX1)
            sysctrl.configure_dma_request_v2(controller, tx_interface, requests["tx"])
            sysctrl.configure_dma_request_v2(controller, rx_interface, requests["rx"])
            dma.controller_enable()
            dma.configure(
                DmaConfig(
                    rx_channel,
                    rx_endpoint,
                    destination.address,
                    frame_bytes // word_bytes,
                    transfer_type=DmaTransferType.PERIPHERAL_TO_MEMORY,
                    source_width=DmaWidth.BITS_32,
                    destination_width=DmaWidth.BITS_32,
                    source_address_mode=DmaAddressMode.INCREMENT,
                    destination_address_mode=DmaAddressMode.INCREMENT,
                    source_burst=DmaBurst.ITEMS_32,
                    destination_burst=DmaBurst.ITEMS_32,
                    source_interface=rx_interface,
                )
            )
            dma.start(rx_channel)
            dma.configure(
                DmaConfig(
                    tx_channel,
                    source.address,
                    tx_endpoint,
                    len(image) // word_bytes,
                    transfer_type=DmaTransferType.MEMORY_TO_PERIPHERAL,
                    source_width=DmaWidth.BITS_32,
                    destination_width=DmaWidth.BITS_32,
                    source_address_mode=DmaAddressMode.INCREMENT,
                    destination_address_mode=DmaAddressMode.INCREMENT,
                    source_burst=DmaBurst.ITEMS_32,
                    destination_burst=DmaBurst.ITEMS_32,
                    destination_interface=tx_interface,
                )
            )
            dma.start(tx_channel)
            dma_status = dma.wait_channels_free(
                (tx_channel, rx_channel), timeout_s=deadline.remaining_s()
            )
            tx_after = can.wait_tx_complete(
                1 << tx_before.put_index, timeout_s=deadline.remaining_s()
            )
            raw = resource_driver.read(destination)
            actual = can.dmu_rx_image_decode(1, raw, timeout_s=deadline.remaining_s())
            errors = can.dmu_status_consume(timeout_s=deadline.remaining_s())
            counters = can.dmu_counters_get(timeout_s=deadline.remaining_s())
            rx_after = can.rx_fifo_status_get(1, timeout_s=deadline.remaining_s())
            record_property(
                "recovery",
                {
                    "image": raw.hex(),
                    "frame": str(actual),
                    "errors": asdict(errors),
                    "counters": asdict(counters),
                    "fifo": asdict(rx_after),
                    "dma": {key: asdict(value) for key, value in dma_status.items()},
                    "tx": asdict(tx_after),
                },
            )
            # 汇总保留为报告属性，各独立硬件端点分别保存实际采样。
            for key, value, endpoint in (
                ("recovery_image", raw.hex(), "DMA.DESTINATION"),
                ("recovery_errors", int(errors.errors), "DMU.ERROR"),
                ("recovery_enabled", errors.enabled, "DMU.ENABLED"),
                (
                    "recovery_counters",
                    [
                        counters.tx_enqueued,
                        counters.rx0_dequeued,
                        counters.rx1_dequeued,
                        counters.tx_event_dequeued,
                    ],
                    "DMU.COUNTERS",
                ),
                ("recovery_fifo", asdict(rx_after), "RX.FIFO_STATUS"),
                ("recovery_tx", tx_after.completed, "TX.COMPLETED"),
            ):
                record_observation(
                    record_property, key=key, value=value, source="dut", endpoint=endpoint
                )
            # 恢复发送与接收通道都须有独立完成及无错误证据。
            for channel, status in dma_status.items():
                record_observation(
                    record_property,
                    key=f"recovery_dma_free_{channel}",
                    value=status.is_free,
                    source="dut",
                    endpoint=f"DMA.CHANNEL[{channel}].FREE",
                )
                record_observation(
                    record_property,
                    key=f"recovery_dma_fifo_{channel}",
                    value=status.fifo_empty,
                    source="dut",
                    endpoint=f"DMA.CHANNEL[{channel}].FIFO_EMPTY",
                )
                record_observation(
                    record_property,
                    key=f"recovery_dma_error_{channel}",
                    value=bool(status.interrupt_events & DmaIrqEvent.ERROR),
                    source="dut",
                    endpoint=f"DMA.CHANNEL[{channel}].IRQ.ERROR",
                )
            assert all(
                status.is_free
                and status.fifo_empty
                and not status.interrupt_events & DmaIrqEvent.ERROR
                for status in dma_status.values()
            )
            assert (
                actual.frame.identifier,
                actual.frame.flags,
                actual.frame.dlc,
                actual.frame.data,
            ) == (expected.identifier, expected.flags, expected.dlc, expected.data)
            assert errors.enabled and errors.errors == CanDmuError.NONE
            assert (
                counters.tx_enqueued,
                counters.rx0_dequeued,
                counters.rx1_dequeued,
                counters.tx_event_dequeued,
            ) == (1, 0, 1, 0)
            assert rx_after.fill == 0 and not rx_after.lost
            assert rx_after.get_index == (rx_before.get_index + 1) % layout.rx1_count
