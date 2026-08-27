# FMAC P3 Formal Case。
#
# 职责：验证FMAC长流稳定性、CPU路径周期和DMA路径周期。
# 边界：Case只编排公共Driver；芯片DMA地址和Request由执行映射提供。
# 依赖：仅依赖FMAC、DMA、Resource Driver及本地参考计算函数。

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction
from ...drivers.crg import CrgPeripheral
from ...drivers.dma import (
    DmaAddressMode,
    DmaBurst,
    DmaConfig,
    DmaFeature,
    DmaIrqEvent,
    DmaTransferType,
    DmaWidth,
)
from ...drivers.fmac import (
    FmacDataFormat,
    FmacDmaRequest,
    FmacFeature,
    FmacFunction,
)
from ...drivers.sysctrl import DmaRequestRoute
from ...scheduling.run_context import record_evidence
from ..case_cleanup import case_cleanup_scope
from ._support import require_fmac_features
from .fmac_helpers import (
    default_config,
    pack_q15,
    record_result,
    unpack_q15,
)
from .fmac_helpers import (
    record_fmac_observation as record_observation,
)

pytestmark = [pytest.mark.hardware, pytest.mark.ip("fmac")]

FMAC_LONG_STREAM_ITEMS = 4096
FMAC_LONG_STREAM_ROUNDS = 2
FMAC_LONG_STREAM_VALUE = 0x2000
FMAC_LONG_STREAM_EXPECTED_STEADY = 0x1E00
FMAC_LONG_STREAM_CHUNKS = (31, 47, 64)
FMAC_LONG_STREAM_BUFFER_ITEMS = max(FMAC_LONG_STREAM_CHUNKS)
FMAC_LONG_STREAM_READ_MAX_POLLS = 64
FMAC_PERFORMANCE_LENGTHS = (64, 128, 240)
FMAC_PERFORMANCE_ROUNDS = 5
FMAC_Q15_ITEM_SIZE_BYTES = 2
FMAC_FIR_COEFFICIENTS = (0x4000, 0x2000, 0x1000, 0x0800)


# 构造可容纳最大64项Chunk且三区域互不重叠的完整公共配置。
def _stream_config():

    return replace(
        default_config(x1_size=64, x2_size=16, y_size=64),
        x2_start=64,
        y_start=80,
    )


# 返回P3 CPU路径使用的FMAC和Resource逆序清理动作。
def _cleanup_actions(support) -> tuple[CleanupAction, ...]:

    return (
        ("FMAC stop", support.fmac.stop),
        ("FMAC clear", support.fmac.clear),
        ("Resource pool reset", support.resource.reset),
    )


# 把总长度按31/47/64循环切分，最后一块缩短到剩余长度。
def _build_chunk_plan(total_items: int) -> tuple[int, ...]:

    chunks: list[int] = []
    remaining = total_items
    chunk_index = 0

    while remaining > 0:
        chunk = min(FMAC_LONG_STREAM_CHUNKS[chunk_index % len(FMAC_LONG_STREAM_CHUNKS)], remaining)
        chunks.append(chunk)
        remaining -= chunk
        chunk_index += 1

    return tuple(chunks)


# 测试 Feature：
# 1. FMAC同一活动会话跨大量Chunk保持FIR状态连续。
# 2. 4096项长流无丢样、重样或跨轮不一致。
#
# 测试方法：
# 1. 使用四抽头和4096项恒定0x2000输入，按31/47/64循环分块。
# 2. 在同一FIR会话中逐块写入并有界读取，完整执行两轮独立会话。
# 3. 比较两轮完整输出，并检查抽头数之后的稳态输出为0x1E00。
#
# 通过条件：
# 1. 每轮接受和读取数量均为4096，且每个Chunk数量完整。
# 2. 两轮输出逐元素一致。
# 3. 两轮稳态区全部等于0x1E00，显式Stop后Active为0。
def test_fmac_p3_001_long_stream_stability(
    fmac_support,
    et_artifact_dir: Path,
    record_property,
) -> None:

    # 准备：建立两轮共用的确定性输入、系数和固定Chunk计划。
    support = fmac_support
    # 隔离：本 Case 配置前复位 FMAC、Service 状态和 Resource Pool。
    support.crg.reset(CrgPeripheral.FMAC, instance=support.instance_id)
    support.fmac.state_reset()
    support.resource.reset()
    require_fmac_features(
        support,
        FmacFeature.FIXED_Q15 | FmacFeature.FIR | FmacFeature.STREAM | FmacFeature.STATUS,
    )
    samples = (FMAC_LONG_STREAM_VALUE,) * FMAC_LONG_STREAM_ITEMS
    coefficient_payload = pack_q15(FMAC_FIR_COEFFICIENTS)
    chunk_plan = _build_chunk_plan(len(samples))
    round_outputs: list[tuple[int, ...]] = []
    round_counts: list[dict[str, int | bool]] = []

    with case_cleanup_scope(lambda: _cleanup_actions(support)):
        coefficients = support.resource.create(len(coefficient_payload), alignment=4)
        history = support.resource.create(len(coefficient_payload), alignment=4)
        stream_buffer_size = FMAC_LONG_STREAM_BUFFER_ITEMS * FMAC_Q15_ITEM_SIZE_BYTES
        source = support.resource.create(stream_buffer_size, alignment=4)
        destination = support.resource.create(stream_buffer_size, alignment=4)
        support.resource.write(coefficients, coefficient_payload)
        support.resource.fill(history, 0)

        # 双轮执行：复用固定大小的Chunk Buffer，每轮从Clear和完整配置开始。
        for _ in range(FMAC_LONG_STREAM_ROUNDS):
            support.fmac.configure(_stream_config())
            support.fmac.coefficients_load(
                coefficients.handle,
                0,
                len(FMAC_FIR_COEFFICIENTS),
            )
            support.fmac.x1_preload(history.handle, 0, len(FMAC_FIR_COEFFICIENTS))
            support.fmac.start(
                FmacFunction.FIR,
                feedforward_taps=len(FMAC_FIR_COEFFICIENTS),
            )

            source_offset = 0
            accepted_total = 0
            read_total = 0
            current_output: list[int] = []

            # Chunk激励：每块数据覆写同一输入Buffer，避免长流占满目标资源池。
            for chunk_size in chunk_plan:
                chunk_bytes = chunk_size * FMAC_Q15_ITEM_SIZE_BYTES
                support.resource.write(
                    source,
                    pack_q15(samples[source_offset : source_offset + chunk_size]),
                )
                support.resource.fill(destination, 0)
                accepted = support.fmac.stream_write(
                    source.handle,
                    0,
                    chunk_size,
                )
                read = 0

                # 有界读取：等待当前Chunk全部进入Y后一次性取回，不跨Chunk消费数据。
                for _ in range(FMAC_LONG_STREAM_READ_MAX_POLLS):
                    if support.fmac.status_get().y_unread_count >= chunk_size:
                        read = support.fmac.stream_read(
                            destination.handle,
                            0,
                            chunk_size,
                        )
                        break

                # 当前Chunk读回后立即转存到PC，目标Buffer供下一Chunk复用。
                if read != 0:
                    current_output.extend(
                        unpack_q15(support.resource.read(destination, chunk_bytes))
                    )

                source_offset += accepted
                accepted_total += accepted
                read_total += read

            output = tuple(current_output)
            round_outputs.append(output)

            support.fmac.stop()
            stopped = support.fmac.status_get()
            round_counts.append(
                {
                    "accepted": accepted_total,
                    "read": read_total,
                    "stopped": not stopped.active,
                }
            )
            support.fmac.clear()

        # 观测：保存双轮摘要、完整数量和稳态尾段。
        record_observation(
            record_property,
            key="actual_stream_tail",
            value=[output[-8:] for output in round_outputs],
            source="dut",
            endpoint="FMAC_DATA.OUTPUT_STREAM",
        )
        record_result(
            et_artifact_dir,
            "fmac_p3_001",
            chunk_plan=chunk_plan,
            round_counts=round_counts,
            steady_tail=[output[-8:] for output in round_outputs],
            rounds_equal=round_outputs[0] == round_outputs[1],
        )

        # 断言：长度、跨轮一致性和完整稳态区必须同时闭合。
        assert all(
            counts
            == {
                "accepted": FMAC_LONG_STREAM_ITEMS,
                "read": FMAC_LONG_STREAM_ITEMS,
                "stopped": True,
            }
            for counts in round_counts
        )
        assert round_outputs[0] == round_outputs[1]
        assert all(
            value == FMAC_LONG_STREAM_EXPECTED_STEADY
            for value in round_outputs[0][len(FMAC_FIR_COEFFICIENTS) :]
        )

    record_evidence(record_property, "dut")


# 测试 Feature：
# FMAC CPU有界处理路径的目标侧DWT周期表征。
#
# 测试方法：
# 1. 使用64、128、240项恒定输入，分别执行1轮预热和5轮目标侧原子计时。
# 2. 每轮由固件在同一临界区内记录FMAC启动至最后输出读取的DWT周期。
# 3. 同时检查传输数量、稳态Golden和周期正值，防止只测速度不测正确性。
#
# 通过条件：
# 1. 每个长度的5个周期样本均大于0。
# 2. 每轮接受/读取数量等于配置长度。
# 3. 每轮稳态尾段全部等于0x1E00。
@pytest.mark.parametrize("item_count", FMAC_PERFORMANCE_LENGTHS, ids=lambda value: f"n{value}")
def test_fmac_p3_002_cpu_timed_process(
    fmac_support,
    item_count: int,
    et_artifact_dir: Path,
    record_property,
) -> None:

    # 准备：输入长度不超过运行时单事务上限，系数和输入保持固定。
    support = fmac_support
    # 隔离：本 Case 配置前复位 FMAC、Service 状态和 Resource Pool。
    support.crg.reset(CrgPeripheral.FMAC, instance=support.instance_id)
    support.fmac.state_reset()
    support.resource.reset()
    require_fmac_features(
        support,
        FmacFeature.FIXED_Q15 | FmacFeature.FIR | FmacFeature.TIMED_PROCESS,
    )
    samples = (FMAC_LONG_STREAM_VALUE,) * item_count
    source_payload = pack_q15(samples)
    coefficient_payload = pack_q15(FMAC_FIR_COEFFICIENTS)
    cycles: list[int] = []
    transfer_counts: list[tuple[int, int]] = []
    steady_tails: list[tuple[int, ...]] = []

    with case_cleanup_scope(lambda: _cleanup_actions(support)):
        coefficients = support.resource.create(len(coefficient_payload), alignment=4)
        history = support.resource.create(len(coefficient_payload), alignment=4)
        source = support.resource.create(len(source_payload), alignment=4)
        destination = support.resource.create(len(source_payload), alignment=4)
        support.resource.write(coefficients, coefficient_payload)
        support.resource.fill(history, 0)
        support.resource.write(source, source_payload)

        # 预热：执行一次不计入样本的相同事务，消除首次调用路径影响。
        support.fmac.configure(_stream_config())
        support.fmac.coefficients_load(coefficients.handle, 0, len(FMAC_FIR_COEFFICIENTS))
        support.fmac.x1_preload(history.handle, 0, len(FMAC_FIR_COEFFICIENTS))
        warmup = support.fmac.process_timed(
            FmacFunction.FIR,
            len(FMAC_FIR_COEFFICIENTS),
            0,
            FmacDataFormat.Q15,
            source.handle,
            0,
            destination.handle,
            0,
            item_count,
        )
        support.fmac.clear()

        # 正式测量：每轮重建配置和系数，保存目标侧原始周期及Golden尾段。
        for _ in range(FMAC_PERFORMANCE_ROUNDS):
            support.fmac.configure(_stream_config())
            support.fmac.coefficients_load(
                coefficients.handle,
                0,
                len(FMAC_FIR_COEFFICIENTS),
            )
            support.fmac.x1_preload(history.handle, 0, len(FMAC_FIR_COEFFICIENTS))
            timed = support.fmac.process_timed(
                FmacFunction.FIR,
                len(FMAC_FIR_COEFFICIENTS),
                0,
                FmacDataFormat.Q15,
                source.handle,
                0,
                destination.handle,
                0,
                item_count,
            )
            actual = unpack_q15(support.resource.read(destination, len(source_payload)))
            cycles.append(timed.elapsed_cycles)
            transfer_counts.append((timed.accepted_count, timed.read_count))
            steady_tails.append(actual[-8:])
            support.fmac.clear()

        # 观测：报告目标侧原始周期、传输数量和同一轮硬件输出。
        record_observation(
            record_property,
            key="elapsed_cycles",
            value=cycles,
            source="dut",
            endpoint="TARGET_CYCLE_COUNT",
        )
        record_result(
            et_artifact_dir,
            "fmac_p3_002",
            item_count=item_count,
            warmup_cycles=warmup.elapsed_cycles,
            elapsed_cycles=cycles,
            steady_tails=steady_tails,
        )

        # 断言：性能样本必须建立在完整且数值正确的事务之上。
        assert warmup.accepted_count == item_count
        assert warmup.read_count == item_count
        assert all(value > 0 for value in cycles)
        assert all(counts == (item_count, item_count) for counts in transfer_counts)
        assert all(
            value == FMAC_LONG_STREAM_EXPECTED_STEADY for tail in steady_tails for value in tail
        )

    record_evidence(record_property, "dut")


# 测试 Feature：
# 1. FMAC双向DMA Q15 FIR路径。
# 2. DMA输出Channel从启动到完成IRQ的目标侧周期计数。
#
# 测试方法：
# 1. 从芯片执行映射取得16-bit FIFO端点和双向Request，选择两条空闲DMA Channel。
# 2. FMAC保持idle时打开双向Gate，再依次启动输出计时、输入Channel和FIR。
# 3. 等待两条Channel完成，读取周期、错误状态和240项输出稳态Golden。
#
# 通过条件：
# 1. DMA计时完成且elapsed_cycles大于0。
# 2. 输入/输出Channel均回到Free且无ERROR。
# 3. 输出稳态末8项全部为0x1E00。
def test_fmac_p3_003_dma_timed_fir(
    fmac_dma_support,
    et_artifact_dir: Path,
    record_property,
) -> None:

    # 准备：确认FMAC和DMA同时发布双向传输及中断计时能力。
    # 隔离：本 Case 配置前先复位辅助 DMA；随后沿用既有 FMAC 和 Resource 复位。
    fmac_dma_support.fmac_support.crg.reset(
        CrgPeripheral.DMA,
        instance=fmac_dma_support.route.controller,
    )

    support = fmac_dma_support
    support.fmac_support.crg.reset(
        CrgPeripheral.FMAC,
        instance=support.fmac_support.instance_id,
    )
    support.fmac_support.fmac.state_reset()
    support.fmac_support.resource.reset()
    fmac = support.fmac_support.fmac
    resource = support.fmac_support.resource
    dma = support.dma
    route = support.route
    require_fmac_features(
        support.fmac_support,
        FmacFeature.FIXED_Q15 | FmacFeature.FIR | FmacFeature.DMA_REQUEST,
    )
    dma_capabilities = dma.capabilities_get()
    required = (
        DmaFeature.MEMORY_TO_PERIPHERAL | DmaFeature.PERIPHERAL_TO_MEMORY | DmaFeature.INTERRUPTS
    )
    if dma_capabilities.features & required != required:
        pytest.skip("skip_by_runtime_feature: FMAC DMA timing prerequisites are unavailable")
    free_channels = tuple(
        channel
        for channel in range(dma_capabilities.channel_count)
        if dma.channel_status(channel).is_free
    )
    if len(free_channels) < 2:
        pytest.skip("skip_by_runtime_resource: FMAC DMA timing needs two free channels")
    input_channel, output_channel = free_channels[:2]

    # 清理状态：逐项记录本Case已取得的跨IP资源。
    resource_ready = False
    controller_enabled = False
    input_route_configured = False
    output_route_configured = False
    input_channel_configured = False
    output_channel_configured = False
    irq_enabled = False
    dma_request_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        # FMAC Request Gate只能在idle修改，因此必须先Stop再关闭Gate。
        actions: list[CleanupAction] = [("FMAC stop", fmac.stop)]
        if dma_request_enabled:
            actions.append(
                (
                    "FMAC DMA request disable",
                    lambda: fmac.dma_request_set(FmacDmaRequest.NONE),
                )
            )
        if irq_enabled:
            actions.append(
                ("DMA timing IRQ disable", lambda: dma.irq_disable(DmaIrqEvent.TRANSFER_DONE))
            )
        if input_channel_configured:
            actions.append(("DMA input channel stop", lambda: dma.stop(input_channel)))
            actions.append(
                ("DMA input channel deconfigure", lambda: dma.deconfigure(input_channel))
            )
        if output_channel_configured:
            actions.append(("DMA output channel stop", lambda: dma.stop(output_channel)))
            actions.append(
                ("DMA output channel deconfigure", lambda: dma.deconfigure(output_channel))
            )
        if input_route_configured:
            actions.append(
                (
                    "SYSCTRL FMAC input route release",
                    lambda: support.sysctrl.release_dma_request(
                        route.controller, route.input_interface
                    ),
                )
            )
        if output_route_configured:
            actions.append(
                (
                    "SYSCTRL FMAC output route release",
                    lambda: support.sysctrl.release_dma_request(
                        route.controller, route.output_interface
                    ),
                )
            )
        if controller_enabled:
            actions.append(("DMA controller disable", dma.controller_disable))
        actions.append(("FMAC clear", fmac.clear))
        if resource_ready:
            actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 资源：240项长度满足单次FMAC/DMA限制并足以形成稳定区。
        samples = (FMAC_LONG_STREAM_VALUE,) * max(FMAC_PERFORMANCE_LENGTHS)
        source_payload = pack_q15(samples)
        coefficient_payload = pack_q15(FMAC_FIR_COEFFICIENTS)
        history_payload = pack_q15((0,) * len(FMAC_FIR_COEFFICIENTS))
        resource_ready = True
        coefficients = resource.create(len(coefficient_payload), alignment=4)
        history = resource.create(len(history_payload), alignment=4)
        source = resource.create(len(source_payload), alignment=4)
        destination = resource.create(len(source_payload), alignment=4)
        resource.write(coefficients, coefficient_payload)
        resource.write(history, history_payload)
        resource.write(source, source_payload)
        resource.fill(destination, 0xA5)

        # FMAC：配置、装载系数并保持DMA Gate关闭。
        fmac.configure(_stream_config())
        fmac.coefficients_load(coefficients.handle, 0, len(FMAC_FIR_COEFFICIENTS))
        fmac.x1_preload(history.handle, 0, len(FMAC_FIR_COEFFICIENTS))
        fmac.dma_request_set(FmacDmaRequest.NONE)

        # DMAMUX：应用当前芯片已审核的输入和输出Request。
        dma.controller_enable()
        controller_enabled = True
        support.sysctrl.configure_route(
            DmaRequestRoute(route.controller, route.input_interface, route.input_request_id)
        )
        input_route_configured = True
        support.sysctrl.configure_route(
            DmaRequestRoute(route.controller, route.output_interface, route.output_request_id)
        )
        output_route_configured = True

        # Channel：两条Channel均使用16-bit固定FIFO外设端点。
        input_config = DmaConfig(
            channel=input_channel,
            source_address=source.address,
            destination_address=route.fifo_address,
            transfer_count=len(samples),
            transfer_type=DmaTransferType.MEMORY_TO_PERIPHERAL,
            source_width=DmaWidth.BITS_16,
            destination_width=DmaWidth.BITS_16,
            source_address_mode=DmaAddressMode.INCREMENT,
            destination_address_mode=DmaAddressMode.FIXED,
            source_burst=DmaBurst.ITEMS_1,
            destination_burst=DmaBurst.ITEMS_1,
            destination_interface=route.input_interface,
        )
        output_config = DmaConfig(
            channel=output_channel,
            source_address=route.fifo_address,
            destination_address=destination.address,
            transfer_count=len(samples),
            transfer_type=DmaTransferType.PERIPHERAL_TO_MEMORY,
            source_width=DmaWidth.BITS_16,
            destination_width=DmaWidth.BITS_16,
            source_address_mode=DmaAddressMode.FIXED,
            destination_address_mode=DmaAddressMode.INCREMENT,
            source_burst=DmaBurst.ITEMS_1,
            destination_burst=DmaBurst.ITEMS_1,
            source_interface=route.output_interface,
        )
        dma.configure(output_config)
        output_channel_configured = True
        dma.configure(input_config)
        input_channel_configured = True

        # Gate配置：FMAC保持idle时打开双向Request，避免运行中修改被硬件拒绝。
        fmac.dma_request_set(FmacDmaRequest.ALL)
        dma_request_enabled = True

        # 计时刺激：输出Channel先进入计时等待，再启动输入Channel和FIR。
        dma.irq_enable(output_channel, DmaIrqEvent.TRANSFER_DONE, priority=4)
        irq_enabled = True
        dma.start_timed(output_channel)
        dma.start(input_channel)
        fmac.start(FmacFunction.FIR, feedforward_taps=len(FMAC_FIR_COEFFICIENTS))
        timing = dma.wait_timing_complete(output_channel)
        input_status = dma.wait_channel_free(input_channel)
        output_status = dma.wait_channel_free(output_channel)
        actual = unpack_q15(resource.read(destination, len(source_payload)))

        # 观测：保留原始周期、Channel终态和硬件稳态输出。
        record_observation(
            record_property,
            key="elapsed_cycles",
            value=timing.elapsed_cycles,
            source="dut",
            endpoint="DMA_TIMING.CYCLE_COUNT",
        )
        record_observation(
            record_property,
            key="actual_output",
            value=actual[-8:],
            source="dut",
            endpoint="DMA_DESTINATION_SEQUENCE",
        )
        record_result(
            et_artifact_dir,
            "fmac_p3_003",
            timing={"complete": timing.complete, "elapsed_cycles": timing.elapsed_cycles},
            channel_status={
                "input_free": input_status.is_free,
                "output_free": output_status.is_free,
                "input_events": int(input_status.interrupt_events),
                "output_events": int(output_status.interrupt_events),
            },
            steady_tail=actual[-8:],
        )

        # 断言：周期数据必须建立在无错误且数值正确的DMA事务上。
        assert timing.complete
        assert timing.elapsed_cycles > 0
        assert input_status.is_free and output_status.is_free
        assert not input_status.interrupt_events & DmaIrqEvent.ERROR
        assert not output_status.interrupt_events & DmaIrqEvent.ERROR
        assert actual[-8:] == (FMAC_LONG_STREAM_EXPECTED_STEADY,) * 8

    record_evidence(record_property, "dut")
