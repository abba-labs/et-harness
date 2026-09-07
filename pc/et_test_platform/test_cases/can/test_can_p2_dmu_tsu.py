# CAN DMU接收时间戳搬运与满payload覆盖检测。
# 职责：显式配置TSU/过滤器、定位TS0关联帧、DMA搬运后独立比较TS0及ATB区间。
# 边界：不提前读取TS0、不解释芯片Header位域、不由CPU补写DMA目标或补Ack。
# 依赖：公共IP Driver、CAN只读执行Mapping、Deadline和Evidence。

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
    CanTsuConfig,
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
# RX0/RX1在真实DMA搬运中携带TSU时间戳，满payload时准确报告覆盖并验证复位恢复。
#
# 测试方法：
# 1. 四个正常节点覆盖RX0/RX1及TTS开关；负向节点只用已映射覆盖错误的RX1。
# 2. 复位CAN/DMA/资源，开启内部TSU、EOF捕获和接收过滤SYNC，禁止TX捕获。
# 3. 最多N帧定位头部Pointer=0，记录ATB包围区间，当前帧保持未出队且不读TS0。
# 4. DMA搬运完整元素到带Guard的目标，随后读取TS0；比较目标时间戳、头部和数据。
# 5. 核对FIFO/DMU推进及覆盖错误；负向节点独立复位后再搬运8-byte帧验证恢复。
#
# 通过条件：
# 1. 正常帧有效8-byte完整、Guard不变、出队一次，TTS开启时目标末word等于TS0且位于ATB区间。
# 2. 64-byte负向帧仅前60-byte保持，RX1覆盖错误真实置位；复位恢复8-byte帧无错误。
@pytest.mark.parametrize(
    "fifo,transfer_timestamp,overwrite",
    (
        (0, False, False),
        (0, True, False),
        (1, False, False),
        (1, True, False),
        (1, True, True),
    ),
    ids=["rx0_plain", "rx0_tsu", "rx1_plain", "rx1_tsu", "rx1_overwrite_recover"],
)
def test_can_p2_008_dmu_rx_timestamp(
    can_support,
    can_dma_support,
    resource_driver,
    record_property,
    fifo,
    transfer_timestamp,
    overwrite,
) -> None:

    support, transport = can_support, can_dma_support
    controller = transport.controller
    can, dma, sysctrl = support.can, transport.dma, transport.sysctrl
    mapping = support.mapping
    layout = dmu_ram(support)
    channel, interface = 0, 0
    word_bytes = mapping.CAN_DMU_WORD_BYTES
    element_bytes = mapping.CAN_RAM_HEADER_BYTES + 64
    guard = b"\xa5" * word_bytes
    record_property("expected_payload", pattern(64 if overwrite else 8).hex())
    record_property(
        "expected",
        f"RX{fifo}, TTS={transfer_timestamp}, overwrite={overwrite}; TS0 pointer=0; DMA guard and dequeue=1",
    )
    record_property("timestamp_word", "NOT_OBSERVED")
    record_property("ts0", "NOT_OBSERVED")
    record_property("atb_before", "NOT_OBSERVED")
    record_property("atb_after", "NOT_OBSERVED")
    record_property("overwrite_error", "NOT_OBSERVED")
    with case_cleanup_scope(
        lambda: (
            ("RX DMA stop", lambda: dma.stop(channel)),
            ("RX DMA deconfigure", lambda: dma.deconfigure(channel)),
            ("RX request release", lambda: sysctrl.release_dma_request(controller, interface)),
            ("DMA disable", dma.controller_disable),
            ("DMA reset", lambda: support.crg.reset(CrgPeripheral.DMA, instance=controller)),
            ("CAN reset", lambda: support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)),
            ("Resource reset", resource_driver.reset),
        )
    ):
        # 满payload错误后单独复位重建8-byte恢复，正常节点只执行一次。
        for payload_bytes in (64, 8) if overwrite else (8,):
            support.crg.reset(CrgPeripheral.DMA, instance=controller)
            support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
            resource_driver.reset()
            dma.deconfigure(channel)
            deadline = OperationDeadline.start(TIMEOUT_S, label="CAN DMU RX TSU")
            can.initializing_set(True, timeout_s=deadline.remaining_s())
            can.wait_initializing(True, timeout_s=deadline.remaining_s())
            limits = can.tsu_limits_get(timeout_s=deadline.remaining_s())
            record_property("tsu_limits", asdict(limits))
            assert limits.internal and 4 <= limits.slots <= 16
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
            can.event_format_set(CanEventFormat(16, True), timeout_s=deadline.remaining_s())
            can.tsu_config_set(
                CanTsuConfig(True, False, False, 1), timeout_s=deadline.remaining_s()
            )
            can.dmu_timestamp_set(transfer_timestamp, timeout_s=deadline.remaining_s())
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
            can.filter_sync_set(0, True, timeout_s=deadline.remaining_s())
            actual_sync = can.filter_sync_get(0, timeout_s=deadline.remaining_s())
            actual_tsu = can.tsu_config_get(timeout_s=deadline.remaining_s())
            record_observation(
                record_property,
                key="filter_sync",
                value=actual_sync,
                source="dut",
                endpoint="FILTER.SYNC",
            )
            record_observation(
                record_property,
                key="tsu_config",
                value=asdict(actual_tsu),
                source="dut",
                endpoint="TSU.CONFIG",
            )
            assert actual_sync and actual_tsu == CanTsuConfig(True, False, False, 1)
            can.loopback_set(CanLoopback.INTERNAL, timeout_s=deadline.remaining_s())
            can.bus_config_set(
                CanBusConfig(
                    True,
                    False,
                    1,
                    CanTimestampSource.EXTERNAL,
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
                CanDmuRequest.RX0 if fifo == 0 else CanDmuRequest.RX1,
                timeout_s=deadline.remaining_s(),
            )
            can.initializing_set(False, timeout_s=deadline.remaining_s())
            can.wait_initializing(False, timeout_s=deadline.remaining_s())
            initial = can.dmu_status_consume(timeout_s=deadline.remaining_s())
            record_observation(
                record_property,
                key="dmu_enabled",
                value=initial.enabled,
                source="dut",
                endpoint="DMU.ENABLED",
            )
            record_observation(
                record_property,
                key="dmu_timestamp_enabled",
                value=initial.transfer_timestamp,
                source="dut",
                endpoint="DMU.TRANSFER_TIMESTAMP",
            )
            record_observation(
                record_property,
                key="dmu_initial_errors",
                value=int(initial.errors),
                source="dut",
                endpoint="DMU.ERROR",
            )
            assert initial.enabled and initial.transfer_timestamp == transfer_timestamp
            assert initial.errors == CanDmuError.NONE
            new, lost = can.tsu_flags_get(timeout_s=deadline.remaining_s())
            record_observation(
                record_property,
                key="tsu_flags_initial",
                value={"new": new, "lost": lost},
                source="dut",
                endpoint="TSU.FLAGS",
            )
            assert new == lost == 0
            expected = CanTxFrame(
                0x123,
                CanFrameFlags.FD | CanFrameFlags.BRS,
                15 if payload_bytes == 64 else 8,
                0,
                pattern(payload_bytes),
            )

            # TSU指针来自实际头部；非TS0帧单独Ack，不读取任何未映射槽地址。
            head = None
            # 只按真实槽数重试分配；非TS0帧显式Ack，不猜测TSU地址。
            for _attempt in range(limits.slots):
                tx = can.tx_status_get(timeout_s=deadline.remaining_s())
                assert not tx.full and tx.pending == 0
                can.tx_write(tx.put_index, expected, timeout_s=deadline.remaining_s())
                atb_before = can.tsu_timebase_get(timeout_s=deadline.remaining_s())
                can.tx_request(1 << tx.put_index, timeout_s=deadline.remaining_s())
                can.wait_tx_complete(1 << tx.put_index, timeout_s=deadline.remaining_s())
                fifo_before = can.wait_rx_available(fifo, timeout_s=deadline.remaining_s())
                atb_after = can.tsu_timebase_get(timeout_s=deadline.remaining_s())
                head = can.rx_timestamp_get(fifo, timeout_s=deadline.remaining_s())
                record_property("rx_timestamp_head", asdict(head))
                record_observation(
                    record_property,
                    key="rx_timestamp_pointer",
                    value=head.tsu_pointer,
                    source="dut",
                    endpoint="RX.HEADER.TSU_POINTER",
                )
                record_observation(
                    record_property,
                    key="rx_timestamp_internal",
                    value=head.internal_timestamp,
                    source="dut",
                    endpoint="RX.HEADER.INTERNAL_TIMESTAMP",
                )
                record_observation(
                    record_property,
                    key="rx_timestamp_index",
                    value=head.index,
                    source="dut",
                    endpoint="RX.FIFO.GET_INDEX",
                )
                record_observation(
                    record_property,
                    key="rx_timestamp_fill",
                    value=fifo_before.fill,
                    source="dut",
                    endpoint="RX.FIFO.FILL",
                )
                assert head.internal_timestamp is None and head.tsu_pointer is not None
                assert head.index == fifo_before.get_index and fifo_before.fill == 1
                if head.tsu_pointer == 0:
                    break
                can.rx_fifo_ack(fifo, head.index, timeout_s=deadline.remaining_s())
            assert head is not None and head.tsu_pointer == 0
            new, lost = can.tsu_flags_get(timeout_s=deadline.remaining_s())
            record_observation(
                record_property, key="tsu_new_before", value=new, source="dut", endpoint="TSU.NEW"
            )
            record_observation(
                record_property,
                key="tsu_lost_before",
                value=lost,
                source="dut",
                endpoint="TSU.LOST",
            )
            record_observation(
                record_property,
                key="atb_before",
                value=atb_before,
                source="dut",
                endpoint="TSU.ATB",
            )
            record_observation(
                record_property, key="atb_after", value=atb_after, source="dut", endpoint="TSU.ATB"
            )
            assert new & 1 and not lost & 1
            span = (atb_after - atb_before) & 0xFFFFFFFF
            assert span < (1 << 31)
            baseline = can.dmu_counters_get(timeout_s=deadline.remaining_s())
            record_observation(
                record_property,
                key="dmu_counters_before",
                value=[
                    baseline.tx_enqueued,
                    baseline.rx0_dequeued,
                    baseline.rx1_dequeued,
                    baseline.tx_event_dequeued,
                ],
                source="dut",
                endpoint="DMU.COUNTERS",
            )
            assert (
                baseline.tx_enqueued,
                baseline.rx0_dequeued,
                baseline.rx1_dequeued,
                baseline.tx_event_dequeued,
            ) == (0, 0, 0, 0)

            # TS0直到DMA完成才读取；目标前后Guard不进入DMA传输范围。
            destination = resource_driver.create(element_bytes + 2 * word_bytes)
            resource_driver.write(destination, b"\xa5" * destination.size)
            endpoint = can.dmu_endpoint_get(CanDmuElement.RX0 if fifo == 0 else CanDmuElement.RX1)
            sysctrl.configure_dma_request_v2(
                controller, interface, mapping.CAN_DMU_REQUESTS[can.instance_id]["rx"]
            )
            dma.controller_enable()
            dma.configure(
                DmaConfig(
                    channel,
                    endpoint,
                    destination.address + word_bytes,
                    element_bytes // word_bytes,
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
            dma.start(channel)
            completion = dma.wait_channel_free(channel, timeout_s=deadline.remaining_s())
            addresses = dma.channel_snapshot_get(channel)
            copied = resource_driver.read(destination)
            raw = copied[word_bytes:-word_bytes]
            ts0 = can.tsu_slot0_consume(timeout_s=deadline.remaining_s())
            actual = can.dmu_rx_image_decode(fifo, raw, timeout_s=deadline.remaining_s())
            errors = can.dmu_status_consume(timeout_s=deadline.remaining_s())
            counters = can.dmu_counters_get(timeout_s=deadline.remaining_s())
            fifo_after = can.rx_fifo_status_get(fifo, timeout_s=deadline.remaining_s())
            expected_error = (
                CanDmuError.RX1_TIMESTAMP_OVERWRITE if payload_bytes == 64 else CanDmuError.NONE
            )
            record_observation(
                record_property,
                key="dma_free",
                value=completion.is_free,
                source="dut",
                endpoint="DMA.CHANNEL.FREE",
            )
            record_observation(
                record_property,
                key="dma_source_address",
                value=addresses.source_address,
                source="dut",
                endpoint="DMA.CHANNEL.SOURCE_ADDRESS",
            )
            record_observation(
                record_property,
                key="dma_destination_address",
                value=addresses.destination_address,
                source="dut",
                endpoint="DMA.CHANNEL.DESTINATION_ADDRESS",
            )
            record_observation(
                record_property,
                key="dma_fifo_empty",
                value=completion.fifo_empty,
                source="dut",
                endpoint="DMA.CHANNEL.FIFO_EMPTY",
            )
            record_observation(
                record_property,
                key="dma_error",
                value=bool(completion.interrupt_events & DmaIrqEvent.ERROR),
                source="dut",
                endpoint="DMA.CHANNEL.IRQ.ERROR",
            )
            record_observation(
                record_property,
                key="dma_image",
                value=copied.hex(),
                source="dut",
                endpoint="DMA.DESTINATION",
            )
            record_observation(
                record_property, key="ts0", value=ts0, source="dut", endpoint="TSU.TS0"
            )
            record_property("decoded", str(actual))
            record_observation(
                record_property,
                key="overwrite_error",
                value=int(errors.errors),
                source="dut",
                endpoint="DMU.ERROR",
            )
            record_observation(
                record_property,
                key="dmu_counters",
                value=[
                    counters.tx_enqueued,
                    counters.rx0_dequeued,
                    counters.rx1_dequeued,
                    counters.tx_event_dequeued,
                ],
                source="dut",
                endpoint="DMU.COUNTERS",
            )
            record_observation(
                record_property,
                key="fifo_after",
                value=asdict(fifo_after),
                source="dut",
                endpoint="RX.FIFO_STATUS",
            )
            # 关闭TTS时末word是无效padding，只保存实际值而不赋予timestamp语义。
            record_observation(
                record_property,
                key="dmu_final_enabled",
                value=errors.enabled,
                source="dut",
                endpoint="DMU.ENABLED",
            )
            record_observation(
                record_property,
                key="dmu_final_timestamp",
                value=errors.transfer_timestamp,
                source="dut",
                endpoint="DMU.TRANSFER_TIMESTAMP",
            )
            timestamp_word = int.from_bytes(raw[-word_bytes:], "little")
            record_observation(
                record_property,
                key="timestamp_word",
                value=timestamp_word,
                source="dut",
                endpoint="DMA.DESTINATION.LAST_WORD",
            )
            assert completion.is_free and completion.fifo_empty
            assert not completion.interrupt_events & DmaIrqEvent.ERROR
            assert addresses.source_address == endpoint + element_bytes
            assert addresses.destination_address == destination.address + word_bytes + element_bytes
            assert copied[:word_bytes] == copied[-word_bytes:] == guard
            assert (
                actual.frame.identifier == expected.identifier
                and actual.frame.flags == expected.flags
            )
            assert actual.frame.dlc == expected.dlc
            expected_data = expected.data[:60] if payload_bytes == 64 else expected.data
            assert actual.frame.data == expected_data
            assert not actual.internal_timestamp_valid and actual.tsu_pointer == 0
            if transfer_timestamp:
                assert actual.transferred_timestamp == timestamp_word == ts0
                assert ((ts0 - atb_before) & 0xFFFFFFFF) <= span
            else:
                assert actual.transferred_timestamp is None
            assert errors.errors == expected_error
            assert errors.enabled and errors.transfer_timestamp == transfer_timestamp
            assert counters.tx_enqueued == counters.tx_event_dequeued == 0
            assert (counters.rx0_dequeued, counters.rx1_dequeued) == (
                (1, 0) if fifo == 0 else (0, 1)
            )
            assert fifo_after.fill == 0 and not fifo_after.lost
            assert fifo_after.get_index == (fifo_before.get_index + 1) % (
                layout.rx0_count if fifo == 0 else layout.rx1_count
            )
            dma.deconfigure(channel)
