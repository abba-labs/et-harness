# CAN DMU通过片内DMA的收发与事件搬运。
# 职责：显式编排CAN、DMA、SYSCTRL和Resource，独立比较数据与硬件终态。
# 边界：Case不解释芯片元素位域，不由CPU读写DMU虚拟窗口，不形成未执行HIL结论。
# 依赖：公共IP Driver、只读CAN执行映射、统一Deadline与Evidence。

from dataclasses import asdict

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
    CanTxEventType,
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


# 测试 Feature：
# DMA通过DMU虚拟TX及RX0/RX1窗口搬运完整FD 64-byte帧，自动推进FIFO。
#
# 测试方法：
# 1. 每个参数节点复位CAN/DMA和资源，建立独立零计数基线，保持UTSU关闭。
# 2. 配置内部回环与FIFO，公共CAN Driver只生成TX内存镜像。
# 3. 先启动RX DMA，再启动TX DMA，逐帧比较PATTERN_A/B的完整接收数据。
# 4. 独立核对DMA实际地址推进、CAN TX完成、RX FIFO推进和DMU错误/计数。
#
# 通过条件：
# 1. RX0/RX1两个节点各两帧头部和64-byte负载一致，DMA无错误且实际搬运长度正确。
# 2. TX入队和当前RX出队各两次，非目标队列零；无CPU窗口访问或隐式补传。
@pytest.mark.parametrize("fifo", [0, 1], ids=["rx0", "rx1"])
def test_can_p2_001_dmu_tx_rx(
    can_support, can_dma_support, resource_driver, record_property, fifo
) -> None:

    support, transport = can_support, can_dma_support
    controller = transport.controller
    can, dma, sysctrl = support.can, transport.dma, transport.sysctrl
    mapping = support.mapping
    requests = mapping.CAN_DMU_REQUESTS[can.instance_id]
    layout = dmu_ram(support)
    rx_bytes = mapping.CAN_RAM_HEADER_BYTES + 64
    word_bytes = mapping.CAN_DMU_WORD_BYTES
    tx_channel, rx_channel = 0, 1
    tx_interface, rx_interface = 0, 1
    assert word_bytes == 4 and rx_bytes % word_bytes == 0
    assert rx_bytes // word_bytes <= transport.capabilities.max_transfer_count
    record_property(
        "expected",
        f"DMA{controller} RX{fifo}; ID=0x123; FD/BRS DLC15; PATTERN_A/B 64 bytes; counters=2/2",
    )
    frames, states = [], []
    record_property("frame", frames)
    record_property("dma", states)

    # 清理先停DMA，再释放请求路由，最后复位CAN和资源；不触碰控制UART。
    with case_cleanup_scope(
        lambda: (
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
        # 隔离：辅助DMA先复位，CAN随后复位，最后释放资源池。
        support.crg.reset(CrgPeripheral.DMA, instance=controller)
        support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
        resource_driver.reset()
        dma.deconfigure(tx_channel)
        dma.deconfigure(rx_channel)
        deadline = OperationDeadline.start(TIMEOUT_S, label="CAN DMU TX/RX")
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
            CanFilter(
                CanFilterType.DUAL,
                CanFilterAction.FIFO0 if fifo == 0 else CanFilterAction.FIFO1,
                0x123,
                0x123,
            ),
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
        can.dmu_request_set(
            CanDmuRequest.RX0 if fifo == 0 else CanDmuRequest.RX1, timeout_s=deadline.remaining_s()
        )
        actual_request = can.dmu_request_get(timeout_s=deadline.remaining_s())
        record_observation(
            record_property,
            key="dmu_request",
            value=int(actual_request),
            source="dut",
            endpoint="DMU.RX_REQUEST_SELECT",
        )
        assert actual_request == (CanDmuRequest.RX0 if fifo == 0 else CanDmuRequest.RX1)
        tx_endpoint = can.dmu_endpoint_get(CanDmuElement.TX, timeout_s=deadline.remaining_s())
        rx_endpoint = can.dmu_endpoint_get(
            CanDmuElement.RX0 if fifo == 0 else CanDmuElement.RX1, timeout_s=deadline.remaining_s()
        )
        can.initializing_set(False, timeout_s=deadline.remaining_s())
        can.wait_initializing(False, timeout_s=deadline.remaining_s())
        initial = can.dmu_status_consume(timeout_s=deadline.remaining_s())
        baseline = can.dmu_counters_get(timeout_s=deadline.remaining_s())
        # 隔离后的使能、错误和计数分别保留为硬件证据。
        for key, value, endpoint in (
            ("dmu_initial_errors", int(initial.errors), "DMU.ERROR"),
            ("dmu_initial_enabled", initial.enabled, "DMU.ENABLED"),
            ("dmu_initial_timestamp", initial.transfer_timestamp, "DMU.TRANSFER_TIMESTAMP"),
            (
                "counters_initial",
                [
                    baseline.tx_enqueued,
                    baseline.rx0_dequeued,
                    baseline.rx1_dequeued,
                    baseline.tx_event_dequeued,
                ],
                "DMU.COUNTERS",
            ),
        ):
            record_observation(
                record_property, key=key, value=value, source="dut", endpoint=endpoint
            )
        assert (
            initial.enabled
            and not initial.transfer_timestamp
            and initial.errors == CanDmuError.NONE
        )
        assert (
            baseline.tx_enqueued,
            baseline.rx0_dequeued,
            baseline.rx1_dequeued,
            baseline.tx_event_dequeued,
        ) == (0, 0, 0, 0)
        sysctrl.configure_dma_request_v2(controller, tx_interface, requests["tx"])
        sysctrl.configure_dma_request_v2(controller, rx_interface, requests["rx"])
        dma.controller_enable()
        source = resource_driver.create(rx_bytes)
        destination = resource_driver.create(rx_bytes)

        # 每帧起址重新配置，DMU虚拟窗口不能跨帧线性越界。
        for inverse in (False, True):
            expected = CanTxFrame(
                0x123, CanFrameFlags.FD | CanFrameFlags.BRS, 15, 0, pattern(64, inverse=inverse)
            )
            image = can.dmu_tx_image_encode(expected, timeout_s=deadline.remaining_s())
            assert len(image) == rx_bytes
            resource_driver.write(source, image)
            resource_driver.write(destination, b"\xa5" * rx_bytes)
            before = can.rx_fifo_status_get(fifo, timeout_s=deadline.remaining_s())
            tx_before = can.tx_status_get(timeout_s=deadline.remaining_s())
            record_observation(
                record_property,
                key="rx_before",
                value=asdict(before),
                source="dut",
                endpoint="RX.FIFO_STATUS",
            )
            # TX请求位与FIFO字段分属不同端点，不合并为伪快照。
            for field, value in (
                ("PENDING", tx_before.pending),
                ("FIFO.FULL", tx_before.full),
                ("FIFO.PUT_INDEX", tx_before.put_index),
            ):
                record_observation(
                    record_property,
                    key=f"tx_before_{field}",
                    value=value,
                    source="dut",
                    endpoint=f"TX.{field}",
                )
            assert (
                before.fill == 0
                and not before.lost
                and not tx_before.full
                and tx_before.pending == 0
            )
            configs = (
                DmaConfig(
                    rx_channel,
                    rx_endpoint,
                    destination.address,
                    rx_bytes // word_bytes,
                    transfer_type=DmaTransferType.PERIPHERAL_TO_MEMORY,
                    source_width=DmaWidth.BITS_32,
                    destination_width=DmaWidth.BITS_32,
                    source_address_mode=DmaAddressMode.INCREMENT,
                    destination_address_mode=DmaAddressMode.INCREMENT,
                    source_burst=DmaBurst.ITEMS_32,
                    destination_burst=DmaBurst.ITEMS_32,
                    source_interface=rx_interface,
                ),
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
                ),
            )
            dma.configure(configs[0])
            dma.start(rx_channel)
            dma.configure(configs[1])
            dma.start(tx_channel)
            actual_dma = dma.wait_channels_free(
                (tx_channel, rx_channel), timeout_s=deadline.remaining_s()
            )
            actual_tx = can.wait_tx_complete(
                1 << tx_before.put_index, timeout_s=deadline.remaining_s()
            )
            snapshots = {
                channel: dma.channel_snapshot_get(channel) for channel in (tx_channel, rx_channel)
            }
            raw = resource_driver.read(destination)
            # 原始搬运结果先留证；解码拒绝畸形头时不能丢失实际DMA输出。
            record_observation(
                record_property,
                key="received_image",
                value=raw.hex(),
                source="dut",
                endpoint="DMA.DESTINATION",
            )
            after = can.rx_fifo_status_get(fifo, timeout_s=deadline.remaining_s())
            errors = can.dmu_status_consume(timeout_s=deadline.remaining_s())
            states.append(
                {
                    "dma": {str(key): asdict(value) for key, value in actual_dma.items()},
                    "snapshots": {str(key): asdict(value) for key, value in snapshots.items()},
                    "tx": asdict(actual_tx),
                }
            )
            frames.append(
                {
                    "image": raw.hex(),
                    "decoded": "NOT_DECODED",
                    "fifo": asdict(after),
                    "dmu": asdict(errors),
                }
            )
            record_property("dma", str(states[-1]))
            record_property("frame", str(frames[-1]))
            # 每个DMA通道及CAN端点保留独立来源，不把汇总当成一个寄存器。
            for channel in (tx_channel, rx_channel):
                record_observation(
                    record_property,
                    key=f"dma_free_{channel}",
                    value=actual_dma[channel].is_free,
                    source="dut",
                    endpoint=f"DMA.CHANNEL[{channel}].FREE",
                )
                record_observation(
                    record_property,
                    key=f"dma_source_{channel}",
                    value=snapshots[channel].source_address,
                    source="dut",
                    endpoint=f"DMA.CHANNEL[{channel}].SOURCE_ADDRESS",
                )
                record_observation(
                    record_property,
                    key=f"dma_destination_{channel}",
                    value=snapshots[channel].destination_address,
                    source="dut",
                    endpoint=f"DMA.CHANNEL[{channel}].DESTINATION_ADDRESS",
                )
                record_observation(
                    record_property,
                    key=f"dma_fifo_empty_{channel}",
                    value=actual_dma[channel].fifo_empty,
                    source="dut",
                    endpoint=f"DMA.CHANNEL[{channel}].FIFO_EMPTY",
                )
                record_observation(
                    record_property,
                    key=f"dma_error_{channel}",
                    value=bool(actual_dma[channel].interrupt_events & DmaIrqEvent.ERROR),
                    source="dut",
                    endpoint=f"DMA.CHANNEL[{channel}].IRQ.ERROR",
                )
            # 接收FIFO与发送完成分别留证，保留失败前的实际终态。
            for key, value, endpoint in (
                ("rx_after", asdict(after), "RX.FIFO_STATUS"),
                ("dmu_after_errors", int(errors.errors), "DMU.ERROR"),
                ("dmu_after_enabled", errors.enabled, "DMU.ENABLED"),
                ("dmu_after_timestamp", errors.transfer_timestamp, "DMU.TRANSFER_TIMESTAMP"),
                ("tx_after", actual_tx.completed, "TX.COMPLETED"),
            ):
                record_observation(
                    record_property, key=key, value=value, source="dut", endpoint=endpoint
                )
            actual = can.dmu_rx_image_decode(fifo, raw, timeout_s=deadline.remaining_s())
            frames[-1]["decoded"] = str(actual)
            record_property("frame", str(frames[-1]))
            assert all(
                status.is_free
                and status.fifo_empty
                and not status.interrupt_events & DmaIrqEvent.ERROR
                for status in actual_dma.values()
            )
            assert snapshots[tx_channel].source_address == source.address + len(image)
            assert snapshots[tx_channel].destination_address == tx_endpoint + len(image)
            assert snapshots[rx_channel].source_address == rx_endpoint + rx_bytes
            assert snapshots[rx_channel].destination_address == destination.address + rx_bytes
            assert actual_tx.completed & (1 << tx_before.put_index)
            assert (
                actual.frame.identifier,
                actual.frame.flags,
                actual.frame.dlc,
                actual.frame.data,
            ) == (expected.identifier, expected.flags, expected.dlc, expected.data)
            assert (
                actual.internal_timestamp_valid
                and actual.tsu_pointer is None
                and actual.transferred_timestamp is None
            )
            assert (
                after.fill == 0 and not after.lost and after.get_index == (before.get_index + 1) % 4
            )
            assert (
                errors.enabled
                and not errors.transfer_timestamp
                and errors.errors == CanDmuError.NONE
            )
            dma.deconfigure(tx_channel)
            dma.deconfigure(rx_channel)

        # 计数只在两次完整传输之后读取一次，不用轮询消耗读清证据。
        counters = can.dmu_counters_get(timeout_s=deadline.remaining_s())
        other = can.rx_fifo_status_get(1 - fifo, timeout_s=deadline.remaining_s())
        # 最终累计计数及非目标FIFO共同证明未发生错误路由。
        for key, value, endpoint in (
            (
                "counters_final",
                [
                    counters.tx_enqueued,
                    counters.rx0_dequeued,
                    counters.rx1_dequeued,
                    counters.tx_event_dequeued,
                ],
                "DMU.COUNTERS",
            ),
            ("other_fifo", asdict(other), "RX.OTHER_FIFO_STATUS"),
        ):
            record_observation(
                record_property, key=key, value=value, source="dut", endpoint=endpoint
            )
        assert counters.tx_enqueued == 2 and counters.tx_event_dequeued == 0
        assert (counters.rx0_dequeued, counters.rx1_dequeued) == ((2, 0) if fifo == 0 else (0, 2))
        assert other.fill == 0 and not other.lost


# 测试 Feature：
# DMA从DMU Event虚拟窗口搬运两次真实发送事件并自动推进队列。
#
# 测试方法：
# 1. 复位参与IP，建立零计数、空Event FIFO和A5目标内存基线。
# 2. CPU只经CAN Driver发送两帧FD64，Marker分别12/34，不读取事件窗口。
# 3. 各帧TX完成后观察Event非空，再由DMA将一个完整Event写入目标区独立位置。
# 4. 公共CAN Driver解码复制字节，比较ID、Marker、类型和实际DMA地址推进。
#
# 通过条件：
# 1. 两项事件分别匹配独立输入，DMA无错误，Event队列归零且DMU Event出队计数为2。
def test_can_p2_002_dmu_tx_event(
    can_support, can_dma_support, resource_driver, record_property
) -> None:

    support, transport = can_support, can_dma_support
    controller = transport.controller
    can, dma, sysctrl = support.can, transport.dma, transport.sysctrl
    mapping = support.mapping
    event_bytes = mapping.CAN_EVENT_BYTES
    word_bytes = mapping.CAN_DMU_WORD_BYTES
    channel, interface = 0, 0
    assert word_bytes == 4 and event_bytes % word_bytes == 0
    assert event_bytes // word_bytes <= transport.capabilities.max_transfer_count
    layout = dmu_ram(support)
    expected_markers = (0x12, 0x34)
    record_property(
        "expected",
        "Internal FD64 ID=0x123; Event markers=0x12/0x34; DMA Event dequeue=2; no CPU Event read",
    )
    events, states = [], []
    record_property("events", events)
    record_property("status", states)

    # 保证DMA先停止；不会在可能仍写入目标区时重置Resource池。
    with case_cleanup_scope(
        lambda: (
            ("Event DMA stop", lambda: dma.stop(channel)),
            ("Event DMA deconfigure", lambda: dma.deconfigure(channel)),
            ("Event request release", lambda: sysctrl.release_dma_request(controller, interface)),
            ("DMA disable", dma.controller_disable),
            ("DMA reset", lambda: support.crg.reset(CrgPeripheral.DMA, instance=controller)),
            ("CAN reset", lambda: support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)),
            ("Resource reset", resource_driver.reset),
        )
    ):
        # 隔离：辅助DMA先复位，CAN随后复位，最后释放资源池。
        support.crg.reset(CrgPeripheral.DMA, instance=controller)
        support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
        resource_driver.reset()
        dma.deconfigure(channel)
        deadline = OperationDeadline.start(TIMEOUT_S, label="CAN DMU TX Event")
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
            CanFilter(CanFilterType.DUAL, CanFilterAction.FIFO0, 0x123, 0x123),
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
        can.dmu_request_set(CanDmuRequest.TX_EVENT, timeout_s=deadline.remaining_s())
        request_readback = can.dmu_request_get(timeout_s=deadline.remaining_s())
        record_observation(
            record_property,
            key="dmu_request",
            value=int(request_readback),
            source="dut",
            endpoint="DMU.RX_REQUEST_SELECT",
        )
        assert request_readback == CanDmuRequest.TX_EVENT
        endpoint = can.dmu_endpoint_get(CanDmuElement.TX_EVENT, timeout_s=deadline.remaining_s())
        can.initializing_set(False, timeout_s=deadline.remaining_s())
        can.wait_initializing(False, timeout_s=deadline.remaining_s())
        initial = can.dmu_status_consume(timeout_s=deadline.remaining_s())
        counters = can.dmu_counters_get(timeout_s=deadline.remaining_s())
        before = can.tx_event_status_get(timeout_s=deadline.remaining_s())
        # Event搬运前必须保留空队列和零计数基线。
        for key, value, endpoint_name in (
            ("dmu_initial_errors", int(initial.errors), "DMU.ERROR"),
            ("dmu_initial_enabled", initial.enabled, "DMU.ENABLED"),
            ("dmu_initial_timestamp", initial.transfer_timestamp, "DMU.TRANSFER_TIMESTAMP"),
            (
                "counters_initial",
                [
                    counters.tx_enqueued,
                    counters.rx0_dequeued,
                    counters.rx1_dequeued,
                    counters.tx_event_dequeued,
                ],
                "DMU.COUNTERS",
            ),
            ("event_initial", asdict(before), "TX.EVENT_STATUS"),
        ):
            record_observation(
                record_property, key=key, value=value, source="dut", endpoint=endpoint_name
            )
        assert (
            initial.enabled
            and not initial.transfer_timestamp
            and initial.errors == CanDmuError.NONE
        )
        assert (
            counters.tx_enqueued,
            counters.rx0_dequeued,
            counters.rx1_dequeued,
            counters.tx_event_dequeued,
        ) == (0, 0, 0, 0)
        assert before.fill == 0 and not before.lost
        sysctrl.configure_dma_request_v2(
            controller, interface, mapping.CAN_DMU_REQUESTS[can.instance_id]["rx"]
        )
        dma.controller_enable()
        destination = resource_driver.create(2 * event_bytes)
        resource_driver.write(destination, b"\xa5" * (2 * event_bytes))

        # 每次DMA都从同一虚拟起点开始，但写入目标区不同元素，不能覆盖首帧证据。
        for sequence, marker in enumerate(expected_markers):
            offset = sequence * event_bytes
            dma.configure(
                DmaConfig(
                    channel,
                    endpoint,
                    destination.address + offset,
                    event_bytes // word_bytes,
                    transfer_type=DmaTransferType.PERIPHERAL_TO_MEMORY,
                    source_width=DmaWidth.BITS_32,
                    destination_width=DmaWidth.BITS_32,
                    source_address_mode=DmaAddressMode.INCREMENT,
                    destination_address_mode=DmaAddressMode.INCREMENT,
                    source_burst=DmaBurst.ITEMS_32,
                    destination_burst=DmaBurst.ITEMS_32,
                    source_interface=interface,
                )
            )
            tx_before = can.tx_status_get(timeout_s=deadline.remaining_s())
            # 保留当前TX槽及待发送状态，不能用后续完成位推断初态。
            for field, value in (
                ("PENDING", tx_before.pending),
                ("FIFO.FULL", tx_before.full),
                ("FIFO.PUT_INDEX", tx_before.put_index),
            ):
                record_observation(
                    record_property,
                    key=f"tx_before_{field}",
                    value=value,
                    source="dut",
                    endpoint=f"TX.{field}",
                )
            assert tx_before.pending == 0 and not tx_before.full
            frame = CanTxFrame(
                0x123,
                CanFrameFlags.FD | CanFrameFlags.BRS | CanFrameFlags.STORE_EVENT,
                15,
                marker,
                pattern(64, inverse=bool(sequence)),
            )
            can.tx_write(tx_before.put_index, frame, timeout_s=deadline.remaining_s())
            can.tx_request(1 << tx_before.put_index, timeout_s=deadline.remaining_s())
            tx = can.wait_tx_complete(1 << tx_before.put_index, timeout_s=deadline.remaining_s())
            queued = can.tx_event_status_get(timeout_s=deadline.remaining_s())
            # 真实TX完成和Event入队是两个独立硬件事实。
            for key, value, endpoint_name in (
                ("tx_complete", tx.completed, "TX.COMPLETED"),
                ("event_queued", asdict(queued), "TX.EVENT_STATUS"),
            ):
                record_observation(
                    record_property, key=key, value=value, source="dut", endpoint=endpoint_name
                )
            assert tx.completed & (1 << tx_before.put_index)
            assert queued.fill == 1 and not queued.lost
            dma.start(channel)
            done = dma.wait_channel_free(channel, timeout_s=deadline.remaining_s())
            snapshot = dma.channel_snapshot_get(channel)
            raw = resource_driver.read(destination, size=event_bytes, offset=offset)
            actual = can.dmu_event_image_decode(raw, timeout_s=deadline.remaining_s())
            after = can.tx_event_status_get(timeout_s=deadline.remaining_s())
            errors = can.dmu_status_consume(timeout_s=deadline.remaining_s())
            events.append({"sequence": sequence, "raw": raw.hex(), "decoded": str(actual)})
            states.append(
                {
                    "dma": asdict(done),
                    "address": asdict(snapshot),
                    "fifo": asdict(after),
                    "dmu": asdict(errors),
                }
            )
            # 出队后的DMA、FIFO与DMU错误分别绑定自身来源。
            for key, value, endpoint_name in (
                ("event_image", raw.hex(), "DMA.DESTINATION"),
                ("dma_complete", done.is_free, "DMA.CHANNEL.FREE"),
                ("dma_fifo_empty", done.fifo_empty, "DMA.CHANNEL.FIFO_EMPTY"),
                (
                    "dma_error",
                    bool(done.interrupt_events & DmaIrqEvent.ERROR),
                    "DMA.CHANNEL.IRQ.ERROR",
                ),
                ("dma_source_address", snapshot.source_address, "DMA.CHANNEL.SOURCE_ADDRESS"),
                (
                    "dma_destination_address",
                    snapshot.destination_address,
                    "DMA.CHANNEL.DESTINATION_ADDRESS",
                ),
                ("event_after", asdict(after), "TX.EVENT_STATUS"),
                ("dmu_after_errors", int(errors.errors), "DMU.ERROR"),
                ("dmu_after_enabled", errors.enabled, "DMU.ENABLED"),
                ("dmu_after_timestamp", errors.transfer_timestamp, "DMU.TRANSFER_TIMESTAMP"),
            ):
                record_observation(
                    record_property, key=key, value=value, source="dut", endpoint=endpoint_name
                )
            assert (
                done.is_free and done.fifo_empty and not done.interrupt_events & DmaIrqEvent.ERROR
            )
            assert snapshot.source_address == endpoint + event_bytes
            assert snapshot.destination_address == destination.address + offset + event_bytes
            assert (
                actual.event.identifier,
                actual.event.flags,
                actual.event.dlc,
                actual.event.marker,
                actual.event.event_type,
            ) == (
                0x123,
                CanFrameFlags.FD | CanFrameFlags.BRS,
                15,
                marker,
                # automatic_retry=False：DAR模式成功发送的精确事件类型为2。
                CanTxEventType.TRANSMITTED_AFTER_CANCEL,
            )
            assert actual.event.tsu_pointer is None and actual.transferred_timestamp is None
            assert (
                after.fill == 0
                and not after.lost
                and after.get_index == (queued.get_index + 1) % layout.event_count
            )
            assert (
                errors.enabled
                and not errors.transfer_timestamp
                and errors.errors == CanDmuError.NONE
            )
            dma.deconfigure(channel)

        # 单次最终计数读取及整区重读证明两项事件同时保留，非A5预填或单元素覆盖。
        counters = can.dmu_counters_get(timeout_s=deadline.remaining_s())
        final = resource_driver.read(destination)
        record_observation(
            record_property,
            key="events",
            value=final.hex(),
            source="dut",
            endpoint="DMA.DESTINATION_ALL",
        )
        record_observation(
            record_property,
            key="status",
            value=[
                counters.tx_enqueued,
                counters.rx0_dequeued,
                counters.rx1_dequeued,
                counters.tx_event_dequeued,
            ],
            source="dut",
            endpoint="DMU.COUNTERS",
        )
        assert (
            counters.tx_enqueued,
            counters.rx0_dequeued,
            counters.rx1_dequeued,
            counters.tx_event_dequeued,
        ) == (0, 0, 0, 2)
        assert final == b"".join(bytes.fromhex(event["raw"]) for event in events)
