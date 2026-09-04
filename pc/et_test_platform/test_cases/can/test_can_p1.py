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
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import (
    FD_LENGTHS,
    TIMEOUT_S,
    dedicated_loopback_ram,
    fifo_loopback_ram,
    loopback_ram,
    pattern,
    phase_timing,
    rx_buffer_boundary_indices,
)

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


# =============================================================================
# RX FIFO与Dedicated Buffer
# =============================================================================


# 测试 Feature：
# CAN RX FIFO0/1的新消息、水位、满状态、Get/Put索引环回及顺序保持。
#
# 测试方法：
# 1. 每个FIFO节点复位CAN和资源池，配置深度4、水位2、阻塞模式及内部回环。
# 2. 分别在第1、2、4帧后读取FIFO状态与IRQ Raw，验证New、Watermark和Full边界。
# 3. 先读取并Ack两帧，再发送两帧，最后排空并核对0～5序号和实际索引环回。
#
# 通过条件：
# 1. FILL依次到1、2、4，Watermark不提前，Full只在深度4出现，最终全部清零。
# 2. 六帧数据顺序完整，读取索引跨越3回到0，FIFO Lost始终为0。
@pytest.mark.parametrize("fifo", (0, 1), ids=("fifo0", "fifo1"))
def test_can_p1_005_rx_fifo_watermark_full_and_wrap(
    can_support, resource_driver, record_property, fifo
) -> None:

    # 准备：所有Expected仅由深度、水位和输入序号生成，不从硬件状态反推。
    support = can_support
    can = support.can
    fifo_depth = 4
    fifo_watermark = 2
    frame_count = 6
    payload_bytes = 8
    identifier = 0x245 + fifo
    layout = fifo_loopback_ram(
        support,
        fifo=fifo,
        watermark=fifo_watermark,
        overwrite=False,
    )
    timing = CanTiming(
        phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    )
    source = CanRxSource.FIFO0 if fifo == 0 else CanRxSource.FIFO1
    action = CanFilterAction.FIFO0 if fifo == 0 else CanFilterAction.FIFO1
    irq_new = CanIrqSource.RX_FIFO0_NEW if fifo == 0 else CanIrqSource.RX_FIFO1_NEW
    irq_watermark = (
        CanIrqSource.RX_FIFO0_WATERMARK if fifo == 0 else CanIrqSource.RX_FIFO1_WATERMARK
    )
    irq_full = CanIrqSource.RX_FIFO0_FULL if fifo == 0 else CanIrqSource.RX_FIFO1_FULL
    tracked_irq = irq_new | irq_watermark | irq_full
    actual_sequences = []
    actual_indices = []
    expected_sequences = list(range(frame_count))
    expected_indices = [0, 1, 2, 3, 0, 1]

    # Expected：在读取任何FIFO状态前固定独立判据，禁止从DUT结果反推。
    record_property(
        "expected",
        {
            "depth": fifo_depth,
            "watermark": fifo_watermark,
            "sequences": expected_sequences,
            "indices": expected_indices,
        },
    )

    # 清理：只恢复当前CAN和整池资源；本Case不启用NVIC路由或外部设备。
    with case_cleanup_scope(
        lambda: (
            ("CAN reset", lambda: support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)),
            ("Resource pool reset", resource_driver.reset),
        )
    ):
        # 基线：先复位，确保FIFO状态、Message RAM配置和历史IRQ不来自上一Case。
        support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
        resource_driver.reset()

        # 配置：一个精确标准ID只进入当前FIFO；另一FIFO和未匹配帧均不接收。
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
        can.ram_layout_set(layout)
        can.filter_set(
            0,
            CanFilter(CanFilterType.DUAL, action, identifier, identifier),
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
        can.irq_mask_set(tracked_irq, False)
        can.irq_clear(tracked_irq)
        can.initializing_set(False)
        can.wait_initializing(False, timeout_s=TIMEOUT_S)

        # 激励一：第一帧只应达到New Message，不应提前达到Watermark或Full。
        payload = bytes((0,)) + pattern(payload_bytes - 1)
        can.tx_write(
            0,
            CanTxFrame(identifier, CanFrameFlags.NONE, payload_bytes, 0, payload),
        )
        can.tx_request(1)
        can.wait_tx_complete(1, timeout_s=TIMEOUT_S)
        first = can.wait_rx_available(fifo, minimum=1, timeout_s=TIMEOUT_S)
        first_irq = can.irq_snapshot_get().raw_status
        record_observation(
            record_property,
            key="first_status",
            value={
                "fill": first.fill,
                "get_index": first.get_index,
                "put_index": first.put_index,
                "full": first.full,
                "lost": first.lost,
            },
            source="dut",
            endpoint=f"RX_FIFO[{fifo}].STATUS",
        )
        record_observation(
            record_property,
            key="first_irq",
            value=int(first_irq & tracked_irq),
            source="dut",
            endpoint="IRQ.RAW",
        )
        assert first.fill == 1 and not first.full and not first.lost
        assert first_irq & tracked_irq == irq_new
        can.irq_clear(tracked_irq)

        # 激励二：第二帧首次跨到水位2，New和Watermark同时可见，Full仍不得置位。
        payload = bytes((1,)) + pattern(payload_bytes - 1, inverse=True)
        can.tx_write(
            0,
            CanTxFrame(identifier, CanFrameFlags.NONE, payload_bytes, 1, payload),
        )
        can.tx_request(1)
        can.wait_tx_complete(1, timeout_s=TIMEOUT_S)
        second = can.wait_rx_available(fifo, minimum=2, timeout_s=TIMEOUT_S)
        second_irq = can.irq_snapshot_get().raw_status
        record_observation(
            record_property,
            key="watermark_status",
            value={
                "fill": second.fill,
                "get_index": second.get_index,
                "put_index": second.put_index,
                "full": second.full,
                "lost": second.lost,
            },
            source="dut",
            endpoint=f"RX_FIFO[{fifo}].STATUS",
        )
        record_observation(
            record_property,
            key="watermark_irq",
            value=int(second_irq & tracked_irq),
            source="dut",
            endpoint="IRQ.RAW",
        )
        assert second.fill == 2 and not second.full and not second.lost
        assert second_irq & tracked_irq == irq_new | irq_watermark
        can.irq_clear(tracked_irq)

        # 激励三：继续写满深度4，只在第四帧后要求Full事件和硬件Full状态。
        for sequence in (2, 3):
            payload = bytes((sequence,)) + pattern(
                payload_bytes - 1,
                inverse=bool(sequence & 1),
            )
            can.tx_write(
                0,
                CanTxFrame(identifier, CanFrameFlags.NONE, payload_bytes, sequence, payload),
            )
            can.tx_request(1)
            can.wait_tx_complete(1, timeout_s=TIMEOUT_S)
        full = can.wait_rx_available(fifo, minimum=4, timeout_s=TIMEOUT_S)
        full_irq = can.irq_snapshot_get().raw_status
        record_observation(
            record_property,
            key="full_status",
            value={
                "fill": full.fill,
                "get_index": full.get_index,
                "put_index": full.put_index,
                "full": full.full,
                "lost": full.lost,
            },
            source="dut",
            endpoint=f"RX_FIFO[{fifo}].STATUS",
        )
        record_observation(
            record_property,
            key="full_irq",
            value=int(full_irq & tracked_irq),
            source="dut",
            endpoint="IRQ.RAW",
        )
        assert full.fill == 4 and full.full and not full.lost
        assert full_irq & tracked_irq & irq_full
        can.irq_clear(tracked_irq)

        # 环回准备：先按当前Get Index读取并Ack最早两帧，释放两个真实FIFO槽。
        for expected_sequence in (0, 1):
            received = can.rx_read(source)
            actual_sequences.append(received.data[0])
            actual_indices.append(received.index)
            can.rx_fifo_ack(fifo, received.index)
            record_observation(
                record_property,
                key="received_frame",
                value={
                    "identifier": received.identifier,
                    "sequence": received.data[0],
                    "index": received.index,
                },
                source="dut",
                endpoint=f"RX_FIFO[{fifo}].FRAME",
            )
            assert received.identifier == identifier and received.data[0] == expected_sequence

        # 环回刺激：新增序号4、5应使用已经释放的槽，Put Index必须跨界回到低索引。
        for sequence in (4, 5):
            payload = bytes((sequence,)) + pattern(
                payload_bytes - 1,
                inverse=bool(sequence & 1),
            )
            can.tx_write(
                0,
                CanTxFrame(identifier, CanFrameFlags.NONE, payload_bytes, sequence, payload),
            )
            can.tx_request(1)
            can.wait_tx_complete(1, timeout_s=TIMEOUT_S)
            can.wait_rx_available(fifo, minimum=sequence - 1, timeout_s=TIMEOUT_S)

        # 排空：逐帧读取并Ack剩余四帧，保留真实索引序列作为环回证据。
        for expected_sequence in (2, 3, 4, 5):
            received = can.rx_read(source)
            actual_sequences.append(received.data[0])
            actual_indices.append(received.index)
            can.rx_fifo_ack(fifo, received.index)
            record_observation(
                record_property,
                key="received_frame",
                value={
                    "identifier": received.identifier,
                    "sequence": received.data[0],
                    "index": received.index,
                },
                source="dut",
                endpoint=f"RX_FIFO[{fifo}].FRAME",
            )
            assert received.identifier == identifier and received.data[0] == expected_sequence

        # 终态：数据、索引和空FIFO必须同时成立，不能只凭IRQ判通过。
        final = can.rx_fifo_status_get(fifo)
        record_property("fifo", fifo)
        record_property(
            "sequence_and_indices",
            {"sequences": actual_sequences, "indices": actual_indices},
        )
        record_property(
            "status_summary",
            {
                "first": {"fill": first.fill, "full": first.full, "lost": first.lost},
                "watermark": {"fill": second.fill, "full": second.full, "lost": second.lost},
                "full": {"fill": full.fill, "full": full.full, "lost": full.lost},
                "final": {"fill": final.fill, "full": final.full, "lost": final.lost},
            },
        )
        record_observation(
            record_property,
            key="final_status",
            value={
                "fill": final.fill,
                "get_index": final.get_index,
                "put_index": final.put_index,
                "full": final.full,
                "lost": final.lost,
            },
            source="dut",
            endpoint=f"RX_FIFO[{fifo}].STATUS",
        )
        assert actual_sequences == expected_sequences
        assert actual_indices == expected_indices
        assert final.fill == 0 and not final.full and not final.lost


# 测试 Feature：
# CAN RX FIFO0/1满后的Blocking与Overwrite数据保留策略及恢复能力。
#
# 测试方法：
# 1. 每个FIFO和模式独立复位，配置深度4并顺序发送序号0～4共5帧。
# 2. 满后读取四个实际帧；Blocking期望保留0～3，Overwrite期望保留1～4。
# 3. 排空后清Lost事件，再发送序号5，验证FIFO能够恢复接收和Ack。
#
# 通过条件：
# 1. 两种模式的四帧保留序列准确，FILL不超过4；Blocking必须报告Lost。
# 2. 恢复帧5数据正确，Ack后FIFO为空且Full解除。
@pytest.mark.parametrize("fifo", (0, 1), ids=("fifo0", "fifo1"))
@pytest.mark.parametrize("overwrite", (False, True), ids=("blocking", "overwrite"))
def test_can_p1_006_rx_fifo_blocking_and_overwrite(
    can_support, resource_driver, record_property, fifo, overwrite
) -> None:

    # 准备：Overwrite的Lost语义不作假设，模式区别只按硬件实际保留帧判定。
    support = can_support
    can = support.can
    fifo_depth = 4
    payload_bytes = 8
    identifier = 0x255 + fifo
    layout = fifo_loopback_ram(support, fifo=fifo, watermark=0, overwrite=overwrite)
    timing = CanTiming(
        phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    )
    source = CanRxSource.FIFO0 if fifo == 0 else CanRxSource.FIFO1
    action = CanFilterAction.FIFO0 if fifo == 0 else CanFilterAction.FIFO1
    irq_lost = CanIrqSource.RX_FIFO0_LOST if fifo == 0 else CanIrqSource.RX_FIFO1_LOST
    expected_sequences = [1, 2, 3, 4] if overwrite else [0, 1, 2, 3]
    actual_sequences = []

    # Expected：模式、保留序列和恢复序号在硬件刺激前固定。
    record_property(
        "expected",
        {
            "mode": "overwrite" if overwrite else "blocking",
            "retained_sequences": expected_sequences,
            "recovery_sequence": 5,
        },
    )

    # 清理：即使序列或恢复断言失败，也复位当前CAN和整池资源。
    with case_cleanup_scope(
        lambda: (
            ("CAN reset", lambda: support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)),
            ("Resource pool reset", resource_driver.reset),
        )
    ):
        # 基线：每个FIFO/模式参数节点都从复位状态开始，禁止沿用上一节点Lost。
        support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
        resource_driver.reset()

        # 配置：一个精确标准ID进入当前FIFO，关闭外部路径和另一FIFO。
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
        can.ram_layout_set(layout)
        can.filter_set(
            0,
            CanFilter(CanFilterType.DUAL, action, identifier, identifier),
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
        can.irq_mask_set(irq_lost, False)
        can.irq_clear(irq_lost)
        can.initializing_set(False)
        can.wait_initializing(False, timeout_s=TIMEOUT_S)

        # 刺激：连续提交五帧；前四帧填满，第五帧制造唯一一次满后输入。
        for sequence in range(5):
            payload = bytes((sequence,)) + pattern(
                payload_bytes - 1,
                inverse=bool(sequence & 1),
            )
            can.tx_write(
                0,
                CanTxFrame(identifier, CanFrameFlags.NONE, payload_bytes, sequence, payload),
            )
            can.tx_request(1)
            can.wait_tx_complete(1, timeout_s=TIMEOUT_S)
        overflow = can.rx_fifo_status_get(fifo)
        overflow_irq = can.irq_snapshot_get().raw_status
        record_observation(
            record_property,
            key="overflow_status",
            value={
                "fill": overflow.fill,
                "get_index": overflow.get_index,
                "put_index": overflow.put_index,
                "full": overflow.full,
                "lost": overflow.lost,
            },
            source="dut",
            endpoint=f"RX_FIFO[{fifo}].STATUS",
        )
        record_observation(
            record_property,
            key="overflow_irq",
            value=int(overflow_irq & irq_lost),
            source="dut",
            endpoint="IRQ.RAW",
        )
        assert overflow.fill == fifo_depth and overflow.full
        if not overwrite:
            assert overflow.lost and overflow_irq & irq_lost

        # 观测：停止发送后按Get Index读出四帧，数据序列是模式行为的主要判据。
        for expected_sequence in expected_sequences:
            received = can.rx_read(source)
            actual_sequences.append(received.data[0])
            can.rx_fifo_ack(fifo, received.index)
            record_observation(
                record_property,
                key="retained_frame",
                value={
                    "identifier": received.identifier,
                    "sequence": received.data[0],
                    "index": received.index,
                },
                source="dut",
                endpoint=f"RX_FIFO[{fifo}].FRAME",
            )
            assert received.identifier == identifier and received.data[0] == expected_sequence

        # 恢复：清Lost事件并写入新序号5，证明满后状态不阻塞后续正常接收。
        can.irq_clear(irq_lost)
        recovery_sequence = 5
        recovery_payload = bytes((recovery_sequence,)) + pattern(payload_bytes - 1, inverse=True)
        can.tx_write(
            0,
            CanTxFrame(
                identifier,
                CanFrameFlags.NONE,
                payload_bytes,
                recovery_sequence,
                recovery_payload,
            ),
        )
        can.tx_request(1)
        can.wait_tx_complete(1, timeout_s=TIMEOUT_S)
        can.wait_rx_available(fifo, timeout_s=TIMEOUT_S)
        recovered = can.rx_read(source)
        can.rx_fifo_ack(fifo, recovered.index)
        final = can.rx_fifo_status_get(fifo)

        # Evidence：恢复帧和终态均先记录，再执行最终强断言。
        record_observation(
            record_property,
            key="recovery_frame",
            value={
                "identifier": recovered.identifier,
                "sequence": recovered.data[0],
                "index": recovered.index,
                "data": recovered.data.hex(" ").upper(),
            },
            source="dut",
            endpoint=f"RX_FIFO[{fifo}].FRAME",
        )
        record_observation(
            record_property,
            key="final_status",
            value={
                "fill": final.fill,
                "get_index": final.get_index,
                "put_index": final.put_index,
                "full": final.full,
                "lost": final.lost,
            },
            source="dut",
            endpoint=f"RX_FIFO[{fifo}].STATUS",
        )

        # 判定：保留序列、恢复数据和终态同时保存，Overwrite不虚构Lost期望。
        record_property("fifo", fifo)
        record_property("mode", "overwrite" if overwrite else "blocking")
        record_property("retained_sequence", actual_sequences)
        record_property("overflow_raw", int(overflow_irq & irq_lost))
        record_property("recovery", recovered.data.hex(" ").upper())
        assert actual_sequences == expected_sequences
        assert recovered.identifier == identifier and recovered.data == recovery_payload
        assert final.fill == 0 and not final.full and not final.lost


# 测试 Feature：
# CAN Dedicated RX Buffer定向接收、64-bit New Data位图边界、独立清除与再次置位。
#
# 测试方法：
# 1. 按Capability选择Buffer 0、31、32、63等有效边界，分别配置唯一标准ID过滤器。
# 2. 逐个发送并读取目标Buffer，确认全部New Data位已置位且RX FIFO保持为空。
# 3. 先单独清一个位，再逐位清完；向Buffer 0重发新数据验证位图和内容更新。
#
# 通过条件：
# 1. 每个目标Buffer的ID和8-byte数据准确，相邻Buffer及FIFO没有误接收。
# 2. 低/高32-bit位图均能独立置位、清除并再次置位。
def test_can_p1_007_dedicated_rx_buffer_boundaries(
    can_support, resource_driver, record_property
) -> None:

    # 准备：索引仅取公开容量内的首尾和位图分界，ID与索引一一对应。
    support = can_support
    can = support.can
    payload_bytes = 8
    indices = rx_buffer_boundary_indices(support.ram_limits)
    layout = dedicated_loopback_ram(support, filter_count=len(indices))
    timing = CanTiming(
        phase_timing(support.clock_hz, 500_000, support.timing_limits.nominal),
        phase_timing(support.clock_hz, 2_000_000, support.timing_limits.data),
    )
    identifiers = {index: 0x300 + position for position, index in enumerate(indices)}
    expected_low = sum(1 << index for index in indices if index < 32)
    expected_high = sum(1 << (index - 32) for index in indices if index >= 32)
    received_data = {}

    # Expected：边界索引、两组位图和各Buffer输入在读取NDAT前固定。
    record_property(
        "expected",
        {
            "indices": list(indices),
            "new_data_low": expected_low,
            "new_data_high": expected_high,
        },
    )

    # 清理：异常也复位当前CAN和整池资源，不逐项恢复Message RAM或位图。
    with case_cleanup_scope(
        lambda: (
            ("CAN reset", lambda: support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)),
            ("Resource pool reset", resource_driver.reset),
        )
    ):
        # 基线：复位后再进入INIT，确保Dedicated RX New Data位图初始为空。
        support.crg.reset(CrgPeripheral.CAN, instance=can.instance_id)
        resource_driver.reset()

        # 配置：每个Filter精确指向一个不同Buffer；未匹配标准帧统一拒绝。
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
        can.ram_layout_set(layout)

        # 配置每个独立Filter槽，当前循环不发送数据或读取硬件状态。
        for filter_index, buffer_index in enumerate(indices):
            identifier = identifiers[buffer_index]
            can.filter_set(
                filter_index,
                CanFilter(CanFilterType.RANGE, CanFilterAction.BUFFER, identifier, 0, buffer_index),
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
        can.initializing_set(False)
        can.wait_initializing(False, timeout_s=TIMEOUT_S)

        # 激励：逐个发送唯一ID和序号，等待对应New Data位后再发送下一帧。
        for sequence, buffer_index in enumerate(indices):
            identifier = identifiers[buffer_index]
            payload = bytes((buffer_index, sequence)) + pattern(
                payload_bytes - 2,
                inverse=bool(sequence & 1),
            )
            can.tx_write(
                0,
                CanTxFrame(identifier, CanFrameFlags.NONE, payload_bytes, sequence, payload),
            )
            can.tx_request(1)
            can.wait_tx_complete(1, timeout_s=TIMEOUT_S)
            status = can.rx_buffer_status_get()
            target_set = (
                bool(status.low & (1 << buffer_index))
                if buffer_index < 32
                else bool(status.high & (1 << (buffer_index - 32)))
            )
            record_observation(
                record_property,
                key="new_data_low",
                value=status.low,
                source="dut",
                endpoint="RX_BUFFER.NEW_DATA_LOW",
            )
            record_observation(
                record_property,
                key="new_data_high",
                value=status.high,
                source="dut",
                endpoint="RX_BUFFER.NEW_DATA_HIGH",
            )
            assert target_set

        # 观测：全部位同时保留；逐个读取真实Buffer且FIFO0没有误路由副本。
        all_set = can.rx_buffer_status_get()
        fifo = can.rx_fifo_status_get(0)
        record_observation(
            record_property,
            key="bitmap_low_all",
            value=all_set.low,
            source="dut",
            endpoint="RX_BUFFER.NEW_DATA_LOW",
        )
        record_observation(
            record_property,
            key="bitmap_high_all",
            value=all_set.high,
            source="dut",
            endpoint="RX_BUFFER.NEW_DATA_HIGH",
        )
        record_observation(
            record_property,
            key="fifo_status",
            value={"fill": fifo.fill, "full": fifo.full, "lost": fifo.lost},
            source="dut",
            endpoint="RX_FIFO[0].STATUS",
        )
        assert all_set.low == expected_low and all_set.high == expected_high
        assert fifo.fill == 0 and not fifo.lost

        # 读取每个目标Buffer的真实帧，位图继续保留到后续显式清除阶段。
        for sequence, buffer_index in enumerate(indices):
            actual = can.rx_read(CanRxSource.BUFFER, buffer_index)
            expected = bytes((buffer_index, sequence)) + pattern(
                payload_bytes - 2,
                inverse=bool(sequence & 1),
            )
            received_data[str(buffer_index)] = actual.data.hex(" ").upper()
            record_observation(
                record_property,
                key="rx_buffer_frame",
                value={
                    "index": actual.index,
                    "identifier": actual.identifier,
                    "data": actual.data.hex(" ").upper(),
                },
                source="dut",
                endpoint=f"RX_BUFFER[{buffer_index}].FRAME",
            )
            assert actual.index == buffer_index and actual.identifier == identifiers[buffer_index]
            assert actual.data == expected

        # 独立清除：先清第二项，确认其他New Data位保持，再逐项清空剩余位。
        isolated_index = indices[1] if len(indices) > 1 else indices[0]
        isolated_low = 1 << isolated_index if isolated_index < 32 else 0
        isolated_high = 1 << (isolated_index - 32) if isolated_index >= 32 else 0
        can.rx_buffer_ack(isolated_low, isolated_high)
        after_one = can.rx_buffer_status_get()
        record_observation(
            record_property,
            key="bitmap_low_after_one",
            value=after_one.low,
            source="dut",
            endpoint="RX_BUFFER.NEW_DATA_LOW",
        )
        record_observation(
            record_property,
            key="bitmap_high_after_one",
            value=after_one.high,
            source="dut",
            endpoint="RX_BUFFER.NEW_DATA_HIGH",
        )
        assert after_one.low == expected_low & ~isolated_low
        assert after_one.high == expected_high & ~isolated_high

        # 逐项确认剩余New Data位，重复清已经清零的目标位应保持无副作用。
        for buffer_index in indices:
            low = 1 << buffer_index if buffer_index < 32 else 0
            high = 1 << (buffer_index - 32) if buffer_index >= 32 else 0
            can.rx_buffer_ack(low, high)
        cleared = can.rx_buffer_status_get()
        record_observation(
            record_property,
            key="bitmap_low_cleared",
            value=cleared.low,
            source="dut",
            endpoint="RX_BUFFER.NEW_DATA_LOW",
        )
        record_observation(
            record_property,
            key="bitmap_high_cleared",
            value=cleared.high,
            source="dut",
            endpoint="RX_BUFFER.NEW_DATA_HIGH",
        )
        assert cleared.low == 0 and cleared.high == 0

        # 再次接收：向首Buffer发送反相新数据，验证位重新置位且内容已经更新。
        first_index = indices[0]
        recovery_marker = 0xA5
        recovery_payload = bytes((first_index, recovery_marker)) + pattern(
            payload_bytes - 2,
            inverse=True,
        )
        can.tx_write(
            0,
            CanTxFrame(
                identifiers[first_index],
                CanFrameFlags.NONE,
                payload_bytes,
                recovery_marker,
                recovery_payload,
            ),
        )
        can.tx_request(1)
        can.wait_tx_complete(1, timeout_s=TIMEOUT_S)
        repeated_status = can.rx_buffer_status_get()
        repeated = can.rx_read(CanRxSource.BUFFER, first_index)

        # Evidence：重新置位的两组位图和更新后的真实Buffer帧先于最终断言保存。
        record_observation(
            record_property,
            key="bitmap_low_repeated",
            value=repeated_status.low,
            source="dut",
            endpoint="RX_BUFFER.NEW_DATA_LOW",
        )
        record_observation(
            record_property,
            key="bitmap_high_repeated",
            value=repeated_status.high,
            source="dut",
            endpoint="RX_BUFFER.NEW_DATA_HIGH",
        )
        record_observation(
            record_property,
            key="rx_buffer_frame",
            value={
                "index": repeated.index,
                "identifier": repeated.identifier,
                "data": repeated.data.hex(" ").upper(),
            },
            source="dut",
            endpoint=f"RX_BUFFER[{first_index}].FRAME",
        )

        # 判定：记录具体Buffer、位图和数据，不能只输出一个布尔结果。
        record_property("indices", list(indices))
        record_property("new_data_all", {"low": all_set.low, "high": all_set.high})
        record_property("new_data_after_one", {"low": after_one.low, "high": after_one.high})
        record_property("buffer_payloads", received_data)
        record_property("repeated_payload", repeated.data.hex(" ").upper())
        repeated_low = 1 << first_index if first_index < 32 else 0
        repeated_high = 1 << (first_index - 32) if first_index >= 32 else 0
        assert repeated_status.low == repeated_low
        assert repeated_status.high == repeated_high
        assert repeated.identifier == identifiers[first_index] and repeated.data == recovery_payload
