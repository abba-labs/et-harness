# FMAC P1 Formal Case。
#
# 职责：验证配置、Buffer、数值格式、输出处理、状态和IRQ等独立Feature。
# 边界：只通过CRG/FMAC/Resource Driver访问设备，不调用Codec或寄存器。
# 依赖：仅依赖CRG、FMAC、Resource Driver和本地Case辅助函数。

from __future__ import annotations

from dataclasses import asdict, replace
from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction
from ...drivers.crg import CrgPeripheral
from ...drivers.fmac import (
    FmacDataFormat,
    FmacFeature,
    FmacFinalPolicy,
    FmacFunction,
    FmacIrqEvent,
    FmacOutputMode,
    FmacShift,
    FmacWatermark,
)
from ...scheduling.run_context import record_evidence
from ..case_cleanup import case_cleanup_scope
from ._support import require_fmac_features
from .fmac_helpers import (
    Q15_MAX,
    Q15_MIN,
    default_config,
    float_to_q15,
    pack_float32,
    pack_q15,
    record_result,
    unpack_float32,
    unpack_q15,
)
from .fmac_helpers import (
    record_fmac_observation as record_observation,
)

pytestmark = [pytest.mark.hardware, pytest.mark.ip("fmac")]

FMAC_STREAM_COEFFICIENTS = (0x4000, 0x2000, 0x1000, 0x0800)
FMAC_STREAM_INPUT = (
    0x0400,
    -0x0800,
    0x0C00,
    0x1000,
    -0x1400,
    0x1800,
    0x1C00,
    -0x2000,
    0x2400,
    0x2800,
    -0x2C00,
    0x3000,
)
FMAC_STREAM_READ_MAX_POLLS = 16
FMAC_Q15_ITEM_SIZE_BYTES = 2
FMAC_FLOAT_ITEM_SIZE_BYTES = 4
FMAC_FORMAT_TEST_COEFFICIENT = 0x4000
FMAC_FORMAT_TEST_HISTORY = (0,)
FMAC_OVERFLOW_TEST_INPUT = 0x0100
FMAC_FLOAT_OVERFLOW_SAMPLE_COUNT = 4
FMAC_FLOAT_RECOVERY_INPUT = 0.25
FMAC_FLOAT_RECOVERY_SAMPLE_COUNT = 1


# 返回FMAC和Resource的统一清理动作；Case主体仍显式展示全部测试流程。
def _cleanup_actions(support, resource_ready: bool) -> tuple[CleanupAction, ...]:

    actions: list[CleanupAction] = [
        ("FMAC IRQ disable", lambda: support.fmac.irq_disable(FmacIrqEvent.ALL)),
        ("FMAC IRQ clear", lambda: support.fmac.irq_clear(FmacIrqEvent.ALL)),
        ("FMAC stop", support.fmac.stop),
        ("FMAC clear", support.fmac.clear),
    ]
    if resource_ready:
        actions.append(("Resource pool reset", support.resource.reset))
    return tuple(actions)


# 在Resource中准备Q15数据，并返回资源引用。
def _create_q15_resource(support, values: tuple[int, ...]):

    payload = pack_q15(values)
    resource = support.resource.create(len(payload), alignment=4)
    support.resource.write(resource, payload)
    return resource


# 将硬件FIFO的低16位按Q15有符号数解释。
def _q15_from_raw(value: int) -> int:

    raw = value & 0xFFFF
    return raw - 0x10000 if raw & 0x8000 else raw


# 测试 Feature：
# 1. X1、X2、Y三区域起始地址和容量配置。
# 2. X1/Y Watermark、输出策略、数据格式、Offset和Shift配置读回。
#
# 测试方法：
# 1. 构造一份覆盖全部公共字段的非默认配置并提交。
# 2. 通过CONFIG_SNAPSHOT_GET读取硬件配置快照。
# 3. 对全部字段逐项比较，不以“配置命令返回成功”代替读回验证。
#
# 通过条件：
# 1. 三区域布局和Watermark精确一致。
# 2. 输出策略、Float开关、Offset和Shift精确一致。
# 3. 未出现字段截断、默认值覆盖或枚举漂移。
def test_fmac_p1_001_configuration_snapshot(
    fmac_support,
    et_artifact_dir: Path,
    record_property,
) -> None:

    # 配置：使用非默认值覆盖全部公开字段，同时保持三区域互不重叠。
    support = fmac_support
    # 隔离：本 Case 配置前复位 FMAC、Service 状态和 Resource Pool。
    support.crg.reset(CrgPeripheral.FMAC, instance=support.instance_id)
    support.fmac.state_reset()
    support.resource.reset()
    config = replace(
        default_config(x1_size=12, x2_size=8, y_size=10),
        x1_full_watermark=FmacWatermark.ITEMS_4,
        y_empty_watermark=FmacWatermark.ITEMS_2,
        final_policy=FmacFinalPolicy.WRAP,
        output_mode=FmacOutputMode.SAT16,
        internal_clip=True,
        float_input=True,
        float_output=True,
        output_shift=FmacShift.RIGHT2,
        output_offset=0x1234,
    )

    with case_cleanup_scope(lambda: _cleanup_actions(support, False)):
        support.fmac.configure(config)
        actual = support.fmac.config_snapshot_get()

        # 观测：保存提交值和目标侧完整读回。
        record_property("expected_config", asdict(config))
        record_observation(
            record_property,
            key="actual_x1_size",
            value=actual.x1_size,
            source="dut",
            endpoint="FMAC_CONFIG_SNAPSHOT",
        )
        record_result(
            et_artifact_dir,
            "fmac_p1_001",
            expected=config,
            actual=actual,
            exact_match=actual == config,
        )

        # 断言：任何单字段差异都必须使Case失败。
        assert actual == config

    record_evidence(record_property, "dut")


# 测试 Feature：
# 1. X1 Watermark、Spare Count和Full状态。
# 2. X1无可写空间时的Overflow状态。
#
# 测试方法：
# 1. 参数化1/2/4 Watermark，并根据Runtime Capability建立最大安全X1区域。
# 2. 分别验证Spare Count、剩余空间跨越Watermark和真实容量外写入。
# 3. 读取Overflow状态，并在Clear后验证状态恢复。
#
# 通过条件：
# 1. 装载半容量数据后Spare Count正确；剩余空间等于Watermark时Full为0，再写1项后Full为1。
# 2. 填满X1后再直接写入1项，X1 Overflow为1。
# 3. Clear后Overflow为0，且不依赖Force伪造事件。
@pytest.mark.parametrize(
    "watermark",
    (FmacWatermark.ITEMS_1, FmacWatermark.ITEMS_2, FmacWatermark.ITEMS_4),
    ids=lambda value: f"wm_{int(value)}",
)
def test_fmac_p1_002_x1_watermark_and_overflow(
    fmac_support,
    watermark: FmacWatermark,
    et_artifact_dir: Path,
    record_property,
) -> None:

    # 准备：从Runtime Capability推导安全布局，不把某颗芯片的Buffer容量写进公共Case。
    support = fmac_support
    # 隔离：本 Case 配置前复位 FMAC、Service 状态和 Resource Pool。
    support.crg.reset(CrgPeripheral.FMAC, instance=support.instance_id)
    support.fmac.state_reset()
    support.resource.reset()
    require_fmac_features(support, FmacFeature.STATUS | FmacFeature.TEST_EXTENSIONS)
    logical_capacity = 1 << support.runtime.logical_address_bits
    x1_size = min(logical_capacity - 2, support.runtime.max_transfer_items - 1)
    if x1_size <= int(watermark):
        pytest.skip("skip_by_runtime_capability: FMAC X1 capacity cannot cover watermark boundary")
    config = replace(
        default_config(x1_size=x1_size, x2_size=1, y_size=1),
        x1_start=1,
        x2_start=0,
        y_start=x1_size + 1,
        x1_full_watermark=watermark,
    )
    coefficients = (FMAC_FORMAT_TEST_COEFFICIENT,)
    values = tuple(range(x1_size))
    spare_probe_count = x1_size // 2
    resource_ready = False

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_ready)):
        coefficient_resource = _create_q15_resource(support, coefficients)
        source = _create_q15_resource(support, values)
        resource_ready = True
        support.fmac.configure(config)

        # Spare Count：进入单抽头FIR后，同时核对启动消费的1项X1和产生的1项Y。
        support.fmac.coefficients_load(coefficient_resource.handle, 0, len(coefficients))
        spare_loaded = support.fmac.x1_preload(source.handle, 0, spare_probe_count)
        support.fmac.start(FmacFunction.FIR, len(coefficients))
        spare_status = support.fmac.status_get()

        # Watermark基线：预先补偿FIR启动消费的1项，使运行态剩余空间恰好等于Watermark。
        support.fmac.clear()
        support.fmac.coefficients_load(coefficient_resource.handle, 0, len(coefficients))
        before_count = config.x1_size - int(watermark) + 1
        before_loaded = support.fmac.x1_preload(source.handle, 0, before_count)
        support.fmac.start(FmacFunction.FIR, len(coefficients))
        before_full = support.fmac.status_get()

        # Watermark跨越：FIR运行态直写1项，使剩余空间低于Watermark。
        support.fmac.data_write_one_unchecked(values[0])
        threshold_loaded = 1
        after_full = support.fmac.status_get()

        # 等待：只轮询目标Full状态，最后一次快照用于决定性断言和Evidence。
        for _ in range(FMAC_STREAM_READ_MAX_POLLS):
            if after_full.x1_full:
                break
            after_full = support.fmac.status_get()

        # Overflow使用独立基线：先按容量完整装载X1，再进入FIR循环模式。
        support.fmac.clear()
        support.fmac.coefficients_load(coefficient_resource.handle, 0, len(coefficients))
        overflow_filled = support.fmac.x1_preload(source.handle, 0, config.x1_size)
        support.fmac.start(FmacFunction.FIR, len(coefficients))
        overflow_before = support.fmac.status_get()

        # 激励：先补回FIR启动消费的1项，再在X1无空闲空间时额外直写1项。
        support.fmac.data_write_one_unchecked(values[0])
        support.fmac.data_write_one_unchecked(values[0])
        overflow = support.fmac.status_get()

        # 等待：给Overflow状态一个有界可见窗口，不使用固定Sleep猜测时序。
        for _ in range(FMAC_STREAM_READ_MAX_POLLS):
            if overflow.x1_overflow:
                break
            overflow = support.fmac.status_get()

        # 恢复：Clear后重新读取Overflow状态。
        support.fmac.clear()
        cleared = support.fmac.status_get()

        # 观测：记录真实Watermark、计数和状态因果链。
        record_observation(
            record_property,
            key="actual_overflow",
            value=overflow.x1_overflow,
            source="dut",
            endpoint="FMAC_STATUS.X1",
        )
        record_result(
            et_artifact_dir,
            "fmac_p1_002",
            watermark=int(watermark),
            spare={
                "loaded": spare_loaded,
                "remaining": spare_status.x1_spare_count,
                "startup_y_unread": spare_status.y_unread_count,
            },
            counts={
                "capacity": config.x1_size,
                "before_written": before_count,
                "threshold_written": threshold_loaded,
                "overflow_filled": overflow_filled,
                "overflow_extra_written": 2,
            },
            threshold={
                "before": {"spare": before_full.x1_spare_count, "full": before_full.x1_full},
                "after": {"spare": after_full.x1_spare_count, "full": after_full.x1_full},
            },
            overflow={
                "before": overflow_before.x1_overflow,
                "set": overflow.x1_overflow,
                "after_clear": cleared.x1_overflow,
            },
        )

        # 断言：容量计数、Watermark比较、自然Overflow和Clear恢复分别成立。
        assert spare_loaded == spare_probe_count
        assert spare_status.y_unread_count == 1
        assert spare_status.x1_spare_count == config.x1_size - spare_probe_count + 1
        assert before_loaded == before_count
        assert before_full.y_unread_count == 1
        assert before_full.x1_spare_count == int(watermark)
        assert not before_full.x1_full
        assert threshold_loaded == 1
        assert after_full.x1_spare_count == int(watermark) - 1
        assert after_full.x1_full
        assert not overflow_before.x1_overflow
        assert overflow_filled == config.x1_size
        assert overflow_before.x1_spare_count == 1
        assert overflow.x1_overflow
        assert not cleared.x1_overflow

    record_evidence(record_property, "dut")


# 测试 Feature：
# 1. Y Watermark、Unread Count和Empty状态。
# 2. Y无未读数据时的Underflow状态。
#
# 测试方法：
# 1. 参数化1/2/4 Watermark，使用单抽头FIR产生四项真实Y输出。
# 2. 暂不读取直到Unread达到4，再逐项unchecked读取并观测Unread和Empty。
# 3. 输出耗尽后再读一次形成自然Underflow，并验证Clear恢复。
#
# 通过条件：
# 1. Unread准确递减，且仅当Unread小于Watermark时Empty为1。
# 2. 额外读取后Y Underflow为1。
# 3. Clear后Underflow为0，读取数据精确等于输入。
@pytest.mark.parametrize(
    "watermark",
    (FmacWatermark.ITEMS_1, FmacWatermark.ITEMS_2, FmacWatermark.ITEMS_4),
    ids=lambda value: f"wm_{int(value)}",
)
def test_fmac_p1_003_y_watermark_and_underflow(
    fmac_support,
    watermark: FmacWatermark,
    et_artifact_dir: Path,
    record_property,
) -> None:

    # 准备：单抽头FIR只负责产生四项真实Y数据，不承担数值Oracle。
    support = fmac_support
    # 隔离：本 Case 配置前复位 FMAC、Service 状态和 Resource Pool。
    support.crg.reset(CrgPeripheral.FMAC, instance=support.instance_id)
    support.fmac.state_reset()
    support.resource.reset()
    require_fmac_features(support, FmacFeature.STATUS | FmacFeature.TEST_EXTENSIONS)
    config = replace(default_config(y_size=4), y_empty_watermark=watermark)
    inputs = (0x0100, -0x0200, 0x0300, -0x0400)
    coefficients = (FMAC_FORMAT_TEST_COEFFICIENT,)
    resource_ready = False

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_ready)):
        resource_ready = True
        coefficient_resource = _create_q15_resource(support, coefficients)
        history_resource = _create_q15_resource(support, FMAC_FORMAT_TEST_HISTORY)
        source = _create_q15_resource(support, inputs)
        support.fmac.configure(config)

        # FIR准备：装载单抽头系数和零历史后启动连续处理会话。
        support.fmac.coefficients_load(coefficient_resource.handle, 0, len(coefficients))
        support.fmac.x1_preload(history_resource.handle, 0, len(FMAC_FORMAT_TEST_HISTORY))
        support.fmac.start(FmacFunction.FIR, feedforward_taps=len(coefficients))

        # 输出建立：一次写入四项输入，等待硬件报告四项Y未读数据。
        loaded = support.fmac.stream_write(source.handle, 0, len(inputs))
        after_load = support.fmac.status_get()
        # 有界轮询直到四项FIR输出全部进入Y，禁止使用固定延时猜测完成。
        for _ in range(FMAC_STREAM_READ_MAX_POLLS):
            if after_load.y_unread_count >= len(inputs):
                break
            after_load = support.fmac.status_get()

        # Watermark观测：按状态推进而不是假设FIFO读数据和Unread计数同拍可见。
        raw_reads: list[int] = []
        unread_statuses = []

        # 逐级读取到3、2、1、0项未读状态，每一级均使用有界轮询。
        for expected_unread in range(len(inputs) - 1, -1, -1):
            current = support.fmac.status_get()
            # 当前级持续读取，直到Unread达到本级目标或耗尽公共轮询预算。
            for _ in range(FMAC_STREAM_READ_MAX_POLLS):
                if current.y_unread_count <= expected_unread:
                    break
                raw_reads.append(support.fmac.data_read_one_unchecked())
                current = support.fmac.status_get()
            unread_statuses.append(current)

        # 异常刺激：持续空读直到硬件自然报告Underflow，仍使用严格有界循环。
        underflow = support.fmac.status_get()
        # 空Y最多追加容量加一次读取，既覆盖流水延迟又保持严格上界。
        for _ in range(config.y_size + 1):
            if underflow.y_underflow:
                break
            raw_reads.append(support.fmac.data_read_one_unchecked())
            underflow = support.fmac.status_get()

        # 恢复：Clear后Underflow必须回到未置位状态。
        support.fmac.clear()
        cleared = support.fmac.status_get()

        # 观测：记录装载、读取和空读后的全部关键状态。
        record_observation(
            record_property,
            key="actual_underflow",
            value=underflow.y_underflow,
            source="dut",
            endpoint="FMAC_STATUS.Y",
        )
        record_result(
            et_artifact_dir,
            "fmac_p1_003",
            watermark=int(watermark),
            counts={"loaded": loaded, "raw_reads": len(raw_reads)},
            raw_reads=raw_reads,
            status={
                "unread_after_load": after_load.y_unread_count,
                "unread_sequence": [asdict(status) for status in unread_statuses],
                "underflow": underflow.y_underflow,
                "underflow_after_clear": cleared.y_underflow,
            },
        )

        # 断言：输入接收、Unread递减、Watermark比较和Underflow恢复必须同时成立。
        assert loaded == len(inputs)
        assert after_load.y_unread_count == len(inputs)

        # 逐级验证Unread计数及Empty比较条件，不依赖特定读流水延迟。
        for expected_unread, status in zip(
            range(len(inputs) - 1, -1, -1), unread_statuses, strict=True
        ):
            assert status.y_unread_count == expected_unread
            assert status.y_empty is (expected_unread < int(watermark))
        assert underflow.y_underflow
        assert not cleared.y_underflow

    record_evidence(record_property, "dut")


# 测试 Feature：
# FMAC在同一活动会话中跨Chunk保持滤波状态和输出顺序连续。
#
# 测试方法：
# 1. 使用固定非重复Q15输入和四个2的幂系数建立one-shot硬件参考输出。
# 2. Stop/Clear后用完全相同的配置和系数重新启动FIR。
# 3. 分别按1/3/2/6和4/4/4切分输入，每块写入后有界读取对应输出。
#
# 通过条件：
# 1. 每个Chunk的接受和读取数量精确等于计划长度。
# 2. 拼接后的12项输出逐元素等于one-shot硬件参考。
# 3. Chunk会话期间Active为1，显式Stop后Active为0。
@pytest.mark.parametrize(
    "chunk_plan",
    ((1, 3, 2, 6), (4, 4, 4)),
    ids=("1_3_2_6", "4_4_4"),
)
def test_fmac_p1_004_stream_chunk_continuity(
    fmac_support,
    chunk_plan: tuple[int, ...],
    et_artifact_dir: Path,
    record_property,
) -> None:

    # 准备：one-shot和Chunk会话共用完全相同的输入、系数和配置。
    support = fmac_support
    # 隔离：本 Case 配置前复位 FMAC、Service 状态和 Resource Pool。
    support.crg.reset(CrgPeripheral.FMAC, instance=support.instance_id)
    support.fmac.state_reset()
    support.resource.reset()
    require_fmac_features(
        support,
        FmacFeature.FIXED_Q15 | FmacFeature.FIR | FmacFeature.STREAM | FmacFeature.STATUS,
    )
    resource_ready = False
    source_payload = pack_q15(FMAC_STREAM_INPUT)
    coefficient_payload = pack_q15(FMAC_STREAM_COEFFICIENTS)

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_ready)):
        resource_ready = True
        coefficients = support.resource.create(len(coefficient_payload), alignment=4)
        history = support.resource.create(len(coefficient_payload), alignment=4)
        source = support.resource.create(len(source_payload), alignment=4)
        one_shot_destination = support.resource.create(len(source_payload), alignment=4)
        chunk_destination = support.resource.create(len(source_payload), alignment=4)
        support.resource.write(coefficients, coefficient_payload)
        support.resource.fill(history, 0)
        support.resource.write(source, source_payload)

        # One-shot参考：完整执行同一FIR，参考只用于判断Chunk边界不变性。
        support.fmac.configure(default_config())
        support.fmac.coefficients_load(
            coefficients.handle,
            0,
            len(FMAC_STREAM_COEFFICIENTS),
        )
        support.fmac.x1_preload(history.handle, 0, len(FMAC_STREAM_COEFFICIENTS))
        one_shot_result = support.fmac.process(
            FmacFunction.FIR,
            len(FMAC_STREAM_COEFFICIENTS),
            0,
            FmacDataFormat.Q15,
            source.handle,
            0,
            one_shot_destination.handle,
            0,
            len(FMAC_STREAM_INPUT),
        )
        one_shot_output = unpack_q15(
            support.resource.read(one_shot_destination, len(source_payload))
        )
        support.fmac.stop()
        support.fmac.clear()

        # 流式配置：重新提交同一配置和系数，再启动一个连续FIR会话。
        support.fmac.configure(default_config())
        support.fmac.coefficients_load(
            coefficients.handle,
            0,
            len(FMAC_STREAM_COEFFICIENTS),
        )
        support.fmac.x1_preload(history.handle, 0, len(FMAC_STREAM_COEFFICIENTS))
        support.fmac.start(
            FmacFunction.FIR,
            feedforward_taps=len(FMAC_STREAM_COEFFICIENTS),
        )
        started = support.fmac.status_get()

        # Chunk激励：每个Chunk必须完整写入，输出读取使用统一有界轮询。
        source_item_offset = 0
        destination_item_offset = 0
        chunk_counts: list[dict[str, int]] = []

        # 分块：按文档固定顺序逐块推进，不在运行时重排或合并Chunk。
        for chunk_size in chunk_plan:
            accepted_count = support.fmac.stream_write(
                source.handle,
                source_item_offset * FMAC_Q15_ITEM_SIZE_BYTES,
                chunk_size,
            )
            read_count = 0

            # 等待：只轮询本Chunk所需的Y未读数量，达到后一次读取完整Chunk。
            for _ in range(FMAC_STREAM_READ_MAX_POLLS):
                status = support.fmac.status_get()
                if status.y_unread_count >= chunk_size:
                    read_count = support.fmac.stream_read(
                        chunk_destination.handle,
                        destination_item_offset * FMAC_Q15_ITEM_SIZE_BYTES,
                        chunk_size,
                    )
                    break

            chunk_counts.append({"accepted": accepted_count, "read": read_count})
            source_item_offset += chunk_size
            destination_item_offset += read_count

        chunked_output = unpack_q15(support.resource.read(chunk_destination, len(source_payload)))
        active_during_stream = support.fmac.status_get()

        # 结束：显式Stop并确认Active清零。
        support.fmac.stop()
        stopped = support.fmac.status_get()

        # 观测：同时保留one-shot参考、Chunk拼接结果和各块实际数量。
        record_observation(
            record_property,
            key="one_shot_output",
            value=one_shot_output,
            source="dut",
            endpoint="FMAC_DATA.OUTPUT_STREAM",
        )
        record_observation(
            record_property,
            key="actual_stream",
            value=chunked_output,
            source="dut",
            endpoint="FMAC_DATA.OUTPUT_STREAM",
        )
        record_observation(
            record_property,
            key="active_sequence",
            value=(started.active, active_during_stream.active, stopped.active),
            source="dut",
            endpoint="FMAC_STATUS.ACTIVE",
        )
        record_result(
            et_artifact_dir,
            "fmac_p1_004",
            chunk_plan=chunk_plan,
            one_shot_output=one_shot_output,
            chunked_output=chunked_output,
            chunk_counts=chunk_counts,
        )

        # 断言：参考事务、各Chunk数量、输出连续性和Active状态必须全部成立。
        assert one_shot_result.accepted_count == len(FMAC_STREAM_INPUT)
        assert one_shot_result.read_count == len(FMAC_STREAM_INPUT)
        assert all(
            counts["accepted"] == chunk_size and counts["read"] == chunk_size
            for counts, chunk_size in zip(chunk_counts, chunk_plan, strict=True)
        )
        assert sum(counts["accepted"] for counts in chunk_counts) == len(FMAC_STREAM_INPUT)
        assert sum(counts["read"] for counts in chunk_counts) == len(FMAC_STREAM_INPUT)
        assert chunked_output == one_shot_output
        assert started.active
        assert active_during_stream.active
        assert not stopped.active

    record_evidence(record_property, "dut")


# 测试 Feature：
# 1. FMAC Float32输入转换为Q15。
# 2. FMAC Q15输出转换为Float32。
#
# 测试方法：
# 1. 使用0.5单抽头FIR，先装载Q15系数和零历史，再开启Float输入转换。
# 2. 写入四项Float32并按Q15读取稳态输出；复位事务后反向配置Float输出。
# 3. 写入四项Q15并按Float32读取稳态输出，分别与独立Oracle比较。
#
# 通过条件：
# 1. Float输入路径的稳态Q15输出精确等于独立转换参考值。
# 2. Q15输出路径的稳态Float32输出在单精度量化误差内等于参考值。
# 3. 正常范围转换不置位Float-to-Q15 Overflow。
def test_fmac_p1_005_float_bidirectional_conversion(
    fmac_support,
    et_artifact_dir: Path,
    record_property,
) -> None:

    # 准备：恒定输入避开FIR启动对齐差异，0.5系数使两个方向都有精确Oracle。
    support = fmac_support
    # 隔离：本 Case 配置前复位 FMAC、Service 状态和 Resource Pool。
    support.crg.reset(CrgPeripheral.FMAC, instance=support.instance_id)
    support.fmac.state_reset()
    support.resource.reset()
    require_fmac_features(
        support,
        FmacFeature.FLOAT_INPUT | FmacFeature.FLOAT_OUTPUT | FmacFeature.STATUS,
    )
    float_values = (0.5,) * 4
    q15_values = tuple(float_to_q15(value) for value in float_values)
    expected_q15 = float_to_q15(0.25)
    expected_float = 0.25
    resource_ready = False

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_ready)):
        resource_ready = True

        # 资源：系数和历史始终用Q15装载，数据流再分别选择Float输入或输出。
        float_source_payload = pack_float32(float_values)
        float_source = support.resource.create(len(float_source_payload), alignment=4)
        q15_source = _create_q15_resource(support, q15_values)
        coefficient = _create_q15_resource(support, (FMAC_FORMAT_TEST_COEFFICIENT,))
        history = _create_q15_resource(support, FMAC_FORMAT_TEST_HISTORY)
        q15_destination = support.resource.create(len(float_values) * 2, alignment=4)
        float_destination = support.resource.create(len(q15_values) * 4, alignment=4)
        support.resource.write(float_source, float_source_payload)

        # Float输入准备：先在Q15模式装载系数和历史，避免把Q15系数误解释为Float32。
        support.fmac.configure(default_config())
        support.fmac.coefficients_load(coefficient.handle, 0, 1)
        support.fmac.x1_preload(history.handle, 0, 1)
        support.fmac.configure(replace(default_config(), float_input=True))
        support.fmac.start(FmacFunction.FIR, 1)

        # Float输入激励：写入Float32，等待Y产生全部输出后按Q15读取。
        float_loaded = support.fmac.stream_write(
            float_source.handle, 0, len(float_values), FmacDataFormat.FLOAT32
        )
        input_status = support.fmac.status_get()

        # 等待：有界轮询Y未读计数，避免用固定延时猜测转换完成。
        for _ in range(FMAC_STREAM_READ_MAX_POLLS):
            if input_status.y_unread_count >= len(float_values):
                break
            input_status = support.fmac.status_get()
        q15_read = support.fmac.stream_read(
            q15_destination.handle,
            0,
            len(float_values),
            FmacDataFormat.Q15,
        )
        actual_q15 = unpack_q15(
            support.resource.read(q15_destination, len(float_values) * FMAC_Q15_ITEM_SIZE_BYTES)
        )

        # Float输出准备：Clear后重新装载同一Q15系数和历史，再单独开启Float输出。
        support.fmac.stop()
        support.fmac.clear()
        support.fmac.configure(default_config())
        support.fmac.coefficients_load(coefficient.handle, 0, 1)
        support.fmac.x1_preload(history.handle, 0, 1)
        support.fmac.configure(replace(default_config(), float_output=True))
        support.fmac.start(FmacFunction.FIR, 1)

        # Float输出激励：写入Q15，等待Y产生全部输出后按Float32读取。
        q15_loaded = support.fmac.stream_write(q15_source.handle, 0, len(q15_values))
        output_status = support.fmac.status_get()

        # 等待：有界轮询Y未读计数，避免在输出尚未形成时提前读取。
        for _ in range(FMAC_STREAM_READ_MAX_POLLS):
            if output_status.y_unread_count >= len(q15_values):
                break
            output_status = support.fmac.status_get()
        float_read = support.fmac.stream_read(
            float_destination.handle,
            0,
            len(q15_values),
            FmacDataFormat.FLOAT32,
        )
        actual_float = unpack_float32(
            support.resource.read(
                float_destination,
                len(q15_values) * FMAC_FLOAT_ITEM_SIZE_BYTES,
            )
        )

        # 观测：记录两条方向独立的硬件转换结果和Overflow状态。
        record_observation(
            record_property,
            key="actual_numeric",
            value=actual_q15,
            source="dut",
            endpoint="FMAC_Y_DATA.Q15",
        )
        record_observation(
            record_property,
            key="q15_to_float_actual",
            value=actual_float,
            source="dut",
            endpoint="FMAC_Y_DATA.FLOAT32",
        )
        record_result(
            et_artifact_dir,
            "fmac_p1_005",
            input_values=float_values,
            actual_q15=actual_q15,
            actual_float=actual_float,
            counts={
                "float_loaded": float_loaded,
                "q15_read": q15_read,
                "q15_loaded": q15_loaded,
                "float_read": float_read,
            },
            overflow=input_status.float_to_q15_overflow,
        )

        # 断言：双向转换必须同时成立，正常输入不能误报Overflow。
        assert float_loaded == q15_read == len(float_values)
        assert q15_loaded == float_read == len(q15_values)
        assert actual_q15[-2:] == (expected_q15, expected_q15)
        assert actual_float[-2:] == pytest.approx(
            (expected_float, expected_float), abs=1.0 / 32768.0
        )
        assert not input_status.float_to_q15_overflow

    record_evidence(record_property, "dut")


# 测试 Feature：
# 1. Float32超范围输入钳位到Q15上下边界。
# 2. Float-to-Q15 Overflow状态置位和Clear恢复。
#
# 测试方法：
# 1. 使用0.5单抽头FIR，分别以四项+2.0和四项-2.0形成正负越界输入。
# 2. 每轮写入Float32并按Q15读取稳态输出，同时采集Float-to-Q15 Overflow状态。
# 3. 每轮越界后再输入一个0.25正常值，解除硬件实时Overflow条件，然后执行Clear。
#
# 通过条件：
# 1. 输出分别等于Q15上下边界。
# 2. 越界转换后Overflow为1。
# 3. 正常输入被完整处理，Clear后Overflow恢复为0。
def test_fmac_p1_006_float_clamp_and_overflow(
    fmac_support,
    et_artifact_dir: Path,
    record_property,
) -> None:

    # 准备：正负越界分成两个独立短事务，避免流水线中的前后样本相互影响。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    fmac_support.crg.reset(CrgPeripheral.FMAC, instance=fmac_support.instance_id)
    fmac_support.fmac.state_reset()
    fmac_support.resource.reset()

    support = fmac_support
    require_fmac_features(support, FmacFeature.FLOAT_INPUT | FmacFeature.STATUS)
    values = (2.0, -2.0)
    expected = (Q15_MAX // 2, Q15_MIN // 2)
    resource_ready = False

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_ready)):
        resource_ready = True
        coefficient = _create_q15_resource(support, (FMAC_FORMAT_TEST_COEFFICIENT,))
        history = _create_q15_resource(support, FMAC_FORMAT_TEST_HISTORY)
        actual: list[int] = []
        counts: list[dict[str, int]] = []
        overflow_states: list[bool] = []
        recovery_statuses: list[bool] = []
        clear_states: list[bool] = []

        # 边界矩阵：每轮只改变Float输入值，配置、系数和读取格式保持一致。
        for value in values:
            # 基线：每个正负边界子实例都从独立的FMAC硬件和Service状态开始。
            support.crg.reset(CrgPeripheral.FMAC, instance=support.instance_id)
            support.fmac.state_reset()

            source_payload = pack_float32((value,) * FMAC_FLOAT_OVERFLOW_SAMPLE_COUNT)
            source = support.resource.create(len(source_payload), alignment=4)
            destination = support.resource.create(
                FMAC_FLOAT_OVERFLOW_SAMPLE_COUNT * FMAC_Q15_ITEM_SIZE_BYTES,
                alignment=4,
            )
            recovery_payload = pack_float32((FMAC_FLOAT_RECOVERY_INPUT,))
            recovery_source = support.resource.create(len(recovery_payload), alignment=4)
            recovery_destination = support.resource.create(FMAC_Q15_ITEM_SIZE_BYTES, alignment=4)
            support.resource.write(source, source_payload)
            support.resource.write(recovery_source, recovery_payload)

            # 装载：先按Q15准备系数和零历史，再开启Float输入转换。
            support.fmac.configure(default_config())
            support.fmac.coefficients_load(coefficient.handle, 0, 1)
            support.fmac.x1_preload(history.handle, 0, 1)
            support.fmac.configure(replace(default_config(), float_input=True))
            support.fmac.start(FmacFunction.FIR, 1)

            # 激励：写入四项同值Float32，等待全部输出后按Q15读取。
            loaded = support.fmac.stream_write(
                source.handle,
                0,
                FMAC_FLOAT_OVERFLOW_SAMPLE_COUNT,
                FmacDataFormat.FLOAT32,
            )
            status = support.fmac.status_get()

            # 等待：当前边界值的四项输出必须全部进入Y。
            for _ in range(FMAC_STREAM_READ_MAX_POLLS):
                if status.y_unread_count >= FMAC_FLOAT_OVERFLOW_SAMPLE_COUNT:
                    break
                status = support.fmac.status_get()
            read = support.fmac.stream_read(
                destination.handle,
                0,
                FMAC_FLOAT_OVERFLOW_SAMPLE_COUNT,
                FmacDataFormat.Q15,
            )
            output = unpack_q15(
                support.resource.read(
                    destination,
                    FMAC_FLOAT_OVERFLOW_SAMPLE_COUNT * FMAC_Q15_ITEM_SIZE_BYTES,
                )
            )
            actual.append(output[-1])
            counts.append({"loaded": loaded, "read": read})
            overflow_states.append(status.float_to_q15_overflow)

            # 恢复输入：继续处理一个正常Float值，使硬件实时Overflow条件先撤销。
            recovery_loaded = support.fmac.stream_write(
                recovery_source.handle,
                0,
                FMAC_FLOAT_RECOVERY_SAMPLE_COUNT,
                FmacDataFormat.FLOAT32,
            )
            recovery_status = support.fmac.status_get()

            # 等待：正常恢复输入必须产生一项可读输出，证明实时Overflow条件已经撤销。
            for _ in range(FMAC_STREAM_READ_MAX_POLLS):
                if recovery_status.y_unread_count >= FMAC_FLOAT_RECOVERY_SAMPLE_COUNT:
                    break
                recovery_status = support.fmac.status_get()
            recovery_read = support.fmac.stream_read(
                recovery_destination.handle,
                0,
                FMAC_FLOAT_RECOVERY_SAMPLE_COUNT,
                FmacDataFormat.Q15,
            )
            recovery_statuses.append(
                recovery_loaded == FMAC_FLOAT_RECOVERY_SAMPLE_COUNT
                and recovery_read == FMAC_FLOAT_RECOVERY_SAMPLE_COUNT
            )

            # 软件清除：实时条件撤销后，Stop和Clear必须清除Sticky报告位。
            support.fmac.stop()
            support.fmac.clear()
            clear_states.append(support.fmac.status_get().float_to_q15_overflow)

        # 观测：保存钳位结果及状态置位/清除序列。
        record_observation(
            record_property,
            key="actual_overflow",
            value=overflow_states,
            source="dut",
            endpoint="FMAC_Y_DATA.Q15",
        )
        record_result(
            et_artifact_dir,
            "fmac_p1_006",
            input_values=values,
            actual=actual,
            counts=counts,
            recovery_input=FMAC_FLOAT_RECOVERY_INPUT,
            recovery_completed=recovery_statuses,
            overflow={
                "after_input": overflow_states,
                "after_clear": clear_states,
            },
        )

        # 断言：数值边界和状态因果链必须同时成立。
        assert all(
            item
            == {
                "loaded": FMAC_FLOAT_OVERFLOW_SAMPLE_COUNT,
                "read": FMAC_FLOAT_OVERFLOW_SAMPLE_COUNT,
            }
            for item in counts
        )
        assert tuple(actual) == expected
        assert all(overflow_states)
        assert all(recovery_statuses)
        assert not any(clear_states)

    record_evidence(record_property, "dut")


# 测试 Feature：
# 1. FMAC内部s(26,22)累加越界的Wrap和Clip策略。
# 2. FMAC累加器Saturation状态及Clear恢复。
#
# 测试方法：
# 1. 使用16项0x7FFF系数和16项0x7FFF输入形成确定性内部累加越界。
# 2. 保持最终输出策略为Wrap，只切换internal_clip并分别执行相同FIR事务。
# 3. 比较两轮稳态输出，读取Saturation状态并验证Clear恢复。
#
# 通过条件：
# 1. 两轮事务均完整接收和读取16项数据。
# 2. Clip与Wrap稳态输出不同，且至少一轮报告累加器Saturation。
# 3. Clear后Saturation状态恢复为0。
def test_fmac_p1_007_internal_clip_and_saturation(
    fmac_support,
    et_artifact_dir: Path,
    record_property,
) -> None:

    # 准备：16个最大正Q15乘积的累加结果超过内部s(26,22)正范围。
    support = fmac_support
    # 隔离：本 Case 配置前复位 FMAC、Service 状态和 Resource Pool。
    support.crg.reset(CrgPeripheral.FMAC, instance=support.instance_id)
    support.fmac.state_reset()
    support.resource.reset()
    require_fmac_features(
        support,
        FmacFeature.FIR | FmacFeature.OUTPUT_POLICY | FmacFeature.STATUS,
    )
    samples = (Q15_MAX,) * 16
    coefficients = (Q15_MAX,) * 16
    resource_ready = False
    outputs: dict[str, tuple[int, ...]] = {}
    saturation: dict[str, bool] = {}
    transfer_counts: dict[str, tuple[int, int]] = {}

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_ready)):
        resource_ready = True
        coefficient_resource = _create_q15_resource(support, coefficients)
        history_resource = _create_q15_resource(support, (0,) * len(coefficients))
        source = _create_q15_resource(support, samples)
        destination = support.resource.create(len(samples) * FMAC_Q15_ITEM_SIZE_BYTES, alignment=4)

        # 策略矩阵：每轮只切换内部Clip，其他输入、系数和输出策略保持一致。
        for clip_enabled in (False, True):
            policy_name = "clip" if clip_enabled else "wrap"
            support.fmac.configure(
                replace(
                    default_config(x1_size=32, x2_size=16, y_size=32),
                    final_policy=FmacFinalPolicy.WRAP,
                    internal_clip=clip_enabled,
                )
            )
            support.fmac.coefficients_load(
                coefficient_resource.handle,
                0,
                len(coefficients),
            )
            support.fmac.x1_preload(history_resource.handle, 0, len(coefficients))

            # 激励：执行相同FIR并保存完整输出和Saturation状态。
            result = support.fmac.process(
                FmacFunction.FIR,
                len(coefficients),
                0,
                FmacDataFormat.Q15,
                source.handle,
                0,
                destination.handle,
                0,
                len(samples),
            )
            outputs[policy_name] = unpack_q15(
                support.resource.read(
                    destination,
                    len(samples) * FMAC_Q15_ITEM_SIZE_BYTES,
                )
            )
            saturation[policy_name] = support.fmac.status_get().accumulator_saturation
            transfer_counts[policy_name] = (result.accepted_count, result.read_count)

            support.fmac.stop()
            support.fmac.clear()

        # 恢复：两轮越界刺激结束后确认Clear清除Saturation状态。
        cleared = support.fmac.status_get()

        # 观测：保存两种内部策略的稳态输出和硬件Saturation状态。
        record_observation(
            record_property,
            key="actual_output",
            value={name: values[-4:] for name, values in outputs.items()},
            source="dut",
            endpoint="FMAC_DATA.OUTPUT_STREAM",
        )
        record_observation(
            record_property,
            key="actual_saturation",
            value=saturation,
            source="dut",
            endpoint="FMAC_STATUS.ACCUMULATOR_SATURATION",
        )
        record_result(
            et_artifact_dir,
            "fmac_p1_007",
            steady_outputs={name: values[-4:] for name, values in outputs.items()},
            saturation=saturation,
            after_clear=cleared.accumulator_saturation,
            transfer_counts=transfer_counts,
        )

        # 断言：内部策略必须产生可观测差异，且状态与Clear形成闭环。
        assert all(counts == (len(samples), len(samples)) for counts in transfer_counts.values())
        assert outputs["wrap"][-4:] != outputs["clip"][-4:]
        assert any(saturation.values())
        assert not cleared.accumulator_saturation

    record_evidence(record_property, "dut")


# 测试 Feature：
# 1. FMAC最终Q15 Saturate策略。
# 2. FMAC最终Q15 Wrap策略。
#
# 测试方法：
# 1. 使用四抽头全0x7FFF系数和恒定0x7FFF输入建立确定性远越界稳态。
# 2. 分别配置Saturate和Wrap，执行相同FIR事务。
# 3. 只比较稳态末尾输出，避开尚未冻结的首有效输出位置。
#
# 通过条件：
# 1. Saturate稳态末值为0x7FFF。
# 2. Wrap稳态末值与Saturate不同。
# 3. 两次事务均完成相同数量的输入输出，不借助历史数组平移。
def test_fmac_p1_008_final_saturate_and_wrap(
    fmac_support,
    et_artifact_dir: Path,
    record_property,
) -> None:

    # 准备：长于抽头数的恒定输入确保末尾样本已经进入稳态。
    support = fmac_support
    # 隔离：本 Case 配置前复位 FMAC、Service 状态和 Resource Pool。
    support.crg.reset(CrgPeripheral.FMAC, instance=support.instance_id)
    support.fmac.state_reset()
    support.resource.reset()
    require_fmac_features(support, FmacFeature.FIR | FmacFeature.OUTPUT_POLICY)
    samples = (Q15_MAX,) * 16
    coefficients = (Q15_MAX,) * 4
    resource_ready = False

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_ready)):
        resource_ready = True

        # Saturate配置：显式建立系数、输入和输出Resource。
        support.fmac.configure(replace(default_config(), final_policy=FmacFinalPolicy.SATURATE))
        coefficient_resource = _create_q15_resource(support, coefficients)
        history_resource = _create_q15_resource(support, (0,) * len(coefficients))
        source = _create_q15_resource(support, samples)
        destination = support.resource.create(len(samples) * 2, alignment=4)
        support.fmac.coefficients_load(coefficient_resource.handle, 0, len(coefficients))
        support.fmac.x1_preload(history_resource.handle, 0, len(coefficients))

        # Saturate激励：执行一次有界FIR事务并读取完整输出。
        saturate_result = support.fmac.process(
            FmacFunction.FIR,
            len(coefficients),
            0,
            FmacDataFormat.Q15,
            source.handle,
            0,
            destination.handle,
            0,
            len(samples),
        )
        saturate_outputs = unpack_q15(support.resource.read(destination, len(samples) * 2))
        support.fmac.stop()
        support.fmac.clear()

        # Wrap配置：复用相同Resource，仅切换最终策略。
        support.fmac.configure(replace(default_config(), final_policy=FmacFinalPolicy.WRAP))
        support.fmac.coefficients_load(coefficient_resource.handle, 0, len(coefficients))
        support.fmac.x1_preload(history_resource.handle, 0, len(coefficients))

        # Wrap激励：执行相同事务并读取对应输出。
        wrap_result = support.fmac.process(
            FmacFunction.FIR,
            len(coefficients),
            0,
            FmacDataFormat.Q15,
            source.handle,
            0,
            destination.handle,
            0,
            len(samples),
        )
        wrap_outputs = unpack_q15(support.resource.read(destination, len(samples) * 2))

        # 观测：只报告稳定窗口末尾四个样本，避免将未知首对齐伪装成事实。
        record_observation(
            record_property,
            key="actual_output",
            value=saturate_outputs[-4:],
            source="dut",
            endpoint="FMAC_Y_DATA.Q15",
        )
        record_observation(
            record_property,
            key="wrap_steady_tail",
            value=wrap_outputs[-4:],
            source="dut",
            endpoint="FMAC_Y_DATA.Q15",
        )
        record_result(
            et_artifact_dir,
            "fmac_p1_008",
            saturate_tail=saturate_outputs[-4:],
            wrap_tail=wrap_outputs[-4:],
            final_values={"saturate": saturate_outputs[-1], "wrap": wrap_outputs[-1]},
        )

        # 断言：策略差异必须在相同稳态刺激上形成可观测结果。
        assert saturate_result.accepted_count == len(samples)
        assert saturate_result.read_count == len(samples)
        assert wrap_result.accepted_count == len(samples)
        assert wrap_result.read_count == len(samples)
        assert saturate_outputs[-1] == Q15_MAX
        assert wrap_outputs[-1] != saturate_outputs[-1]

    record_evidence(record_property, "dut")


# 测试 Feature：
# 1. FMAC RAW输出模式。
# 2. FMAC SAT12和SAT16输出模式。
#
# 测试方法：
# 1. 对同一单抽头恒定输入分别配置RAW、SAT12、SAT16。
# 2. 每次Clear后重建完整配置、系数和输入，读取稳态末值。
# 3. 检查SAT12范围、SAT16范围以及RAW与SAT12的硬件差异。
#
# 通过条件：
# 1. SAT12结果落在有符号12-bit范围。
# 2. SAT16结果落在有符号16-bit范围。
# 3. 大幅度输入下RAW与SAT12结果不同，证明模式选择实际生效。
def test_fmac_p1_009_output_modes(
    fmac_support,
    et_artifact_dir: Path,
    record_property,
) -> None:

    # 准备：0x7000输入足以触发12-bit限制，同时不超出Q15输入范围。
    support = fmac_support
    # 隔离：本 Case 配置前复位 FMAC、Service 状态和 Resource Pool。
    support.crg.reset(CrgPeripheral.FMAC, instance=support.instance_id)
    support.fmac.state_reset()
    support.resource.reset()
    require_fmac_features(support, FmacFeature.FIR | FmacFeature.OUTPUT_POLICY)
    samples = (0x7000,) * 12
    coefficients = (Q15_MAX,)
    resource_ready = False
    outputs: dict[str, int] = {}

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_ready)):
        resource_ready = True
        coefficient_resource = _create_q15_resource(support, coefficients)
        history_resource = _create_q15_resource(support, (0,) * len(coefficients))
        source = _create_q15_resource(support, samples)
        destination = support.resource.create(len(samples) * 2, alignment=4)

        # 参数化执行：每轮只改变Output Mode，其他刺激完全一致。
        for mode in (FmacOutputMode.RAW, FmacOutputMode.SAT12, FmacOutputMode.SAT16):
            # 配置：应用当前Output Mode并重新装载相同系数。
            support.fmac.configure(replace(default_config(), output_mode=mode))
            support.fmac.coefficients_load(
                coefficient_resource.handle,
                0,
                len(coefficients),
            )
            support.fmac.x1_preload(history_resource.handle, 0, len(coefficients))

            # 激励：执行相同FIR事务并读取当前模式的完整输出。
            process_result = support.fmac.process(
                FmacFunction.FIR,
                len(coefficients),
                0,
                FmacDataFormat.Q15,
                source.handle,
                0,
                destination.handle,
                0,
                len(samples),
            )
            mode_outputs = unpack_q15(support.resource.read(destination, len(samples) * 2))
            outputs[mode.name] = mode_outputs[-1]

            # 单轮判定：事务数量必须完整，避免数值比较掩盖不完整传输。
            assert process_result.accepted_count == len(samples)
            assert process_result.read_count == len(samples)
            support.fmac.stop()
            support.fmac.clear()

        # 观测：保存三种硬件模式的稳态末值。
        record_observation(
            record_property,
            key="actual_output",
            value=outputs,
            source="dut",
            endpoint="FMAC_Y_DATA.Q15",
        )
        record_result(et_artifact_dir, "fmac_p1_009", output_values=outputs)

        # 断言：输出范围和模式差异必须由硬件结果证明。
        assert -2048 <= outputs["SAT12"] <= 2047
        assert Q15_MIN <= outputs["SAT16"] <= Q15_MAX
        assert outputs["RAW"] != outputs["SAT12"]

    record_evidence(record_property, "dut")


# 测试 Feature：
# 1. FMAC输出Offset参与非RAW输出处理。
# 2. Offset处理后负值状态可置位并经Clear恢复。
#
# 测试方法：
# 1. 在SAT16模式下用负稳态输入形成负值输出并读取状态。
# 2. 输入正稳态样本撤销实时负值条件，再执行Clear并读取清除后状态。
# 3. 保持负输入，仅加入正Offset重新执行并比较两次稳态结果。
#
# 通过条件：
# 1. 加Offset后的稳态输出与零Offset结果不同。
# 2. 负输出子实例置位Negative After Offset状态。
# 3. Clear后该状态归零，第二子实例可继续执行。
def test_fmac_p1_010_output_offset_and_negative_status(
    fmac_support,
    et_artifact_dir: Path,
    record_property,
) -> None:

    # 准备：单抽头负输入提供简单、稳定且不依赖首对齐的输出。
    support = fmac_support
    # 隔离：本 Case 配置前复位 FMAC、Service 状态和 Resource Pool。
    support.crg.reset(CrgPeripheral.FMAC, instance=support.instance_id)
    support.fmac.state_reset()
    support.resource.reset()
    require_fmac_features(support, FmacFeature.FIR | FmacFeature.STATUS)
    samples = (-0x2000,) * 12
    recovery_samples = (0x2000,) * len(samples)
    coefficients = (Q15_MAX,)
    resource_ready = False

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_ready)):
        resource_ready = True
        coefficient_resource = _create_q15_resource(support, coefficients)
        history_resource = _create_q15_resource(support, (0,) * len(coefficients))
        source = _create_q15_resource(support, samples)
        recovery_source = _create_q15_resource(support, recovery_samples)
        destination = support.resource.create(len(samples) * 2, alignment=4)

        # 零Offset配置：装载相同系数并建立负输出路径。
        support.fmac.configure(
            replace(default_config(), output_mode=FmacOutputMode.SAT16, output_offset=0),
        )
        support.fmac.coefficients_load(coefficient_resource.handle, 0, len(coefficients))
        support.fmac.x1_preload(history_resource.handle, 0, len(coefficients))

        # 零Offset激励：执行FIR并读取负值状态。
        baseline_result = support.fmac.process(
            FmacFunction.FIR,
            len(coefficients),
            0,
            FmacDataFormat.Q15,
            source.handle,
            0,
            destination.handle,
            0,
            len(samples),
        )
        baseline_outputs = unpack_q15(support.resource.read(destination, len(samples) * 2))
        negative_status = support.fmac.status_get()

        # 状态恢复准备：先停止已完成事务，再重建同一FMAC配置和单抽头数据路径。
        support.fmac.stop()
        support.fmac.configure(
            replace(default_config(), output_mode=FmacOutputMode.SAT16, output_offset=0),
        )
        support.fmac.coefficients_load(coefficient_resource.handle, 0, len(coefficients))
        support.fmac.x1_preload(history_resource.handle, 0, len(coefficients))

        # 状态恢复激励：用正稳态输入撤销实时负值条件，再验证W1C清除Sticky状态。
        recovery_result = support.fmac.process(
            FmacFunction.FIR,
            len(coefficients),
            0,
            FmacDataFormat.Q15,
            recovery_source.handle,
            0,
            destination.handle,
            0,
            len(recovery_samples),
        )
        support.fmac.stop()
        support.fmac.clear()
        cleared_status = support.fmac.status_get()

        # 正Offset配置：使用相同刺激，仅改变Offset。
        support.fmac.configure(
            replace(
                default_config(),
                output_mode=FmacOutputMode.SAT16,
                output_offset=0x3000,
            ),
        )
        support.fmac.coefficients_load(coefficient_resource.handle, 0, len(coefficients))
        support.fmac.x1_preload(history_resource.handle, 0, len(coefficients))

        # 正Offset激励：执行FIR并读取完整输出。
        offset_result = support.fmac.process(
            FmacFunction.FIR,
            len(coefficients),
            0,
            FmacDataFormat.Q15,
            source.handle,
            0,
            destination.handle,
            0,
            len(samples),
        )
        offset_outputs = unpack_q15(support.resource.read(destination, len(samples) * 2))

        # 观测：保存两类稳态输出和负值状态恢复序列。
        record_observation(
            record_property,
            key="actual_negative",
            value=negative_status.negative_after_offset,
            source="dut",
            endpoint="FMAC_Y_DATA.Q15",
        )
        record_result(
            et_artifact_dir,
            "fmac_p1_010",
            outputs={"zero_offset": baseline_outputs[-1], "positive_offset": offset_outputs[-1]},
            negative_status={
                "after_negative": negative_status.negative_after_offset,
                "after_clear": cleared_status.negative_after_offset,
            },
            recovery_transfer={
                "accepted_count": recovery_result.accepted_count,
                "read_count": recovery_result.read_count,
            },
        )

        # 断言：Offset数值影响与负值状态因果链必须同时成立。
        assert baseline_result.accepted_count == len(samples)
        assert baseline_result.read_count == len(samples)
        assert recovery_result.accepted_count == len(recovery_samples)
        assert recovery_result.read_count == len(recovery_samples)
        assert offset_result.accepted_count == len(samples)
        assert offset_result.read_count == len(samples)
        assert baseline_outputs[-1] == 0
        assert offset_outputs[-1] > baseline_outputs[-1]
        assert negative_status.negative_after_offset
        assert not cleared_status.negative_after_offset

    record_evidence(record_property, "dut")


# 测试 Feature：
# FMAC LEFT1、NONE和RIGHT1输出Shift编码及相对数值关系。
#
# 测试方法：
# 1. 使用同一单抽头、小幅正输入分别配置LEFT1、NONE和RIGHT1。
# 2. 每轮Clear并重建完整配置，读取稳态末值。
# 3. 比较三个结果的绝对值顺序，不依赖首有效输出位置。
#
# 通过条件：
# 1. LEFT1稳态幅值大于NONE。
# 2. NONE稳态幅值大于RIGHT1。
# 3. 三轮输入、系数和输出模式完全相同，仅Shift不同。
def test_fmac_p1_011_output_shift(
    fmac_support,
    et_artifact_dir: Path,
    record_property,
) -> None:

    # 准备：低幅度输入避免LEFT1触发最终饱和，确保相对关系可观察。
    support = fmac_support
    # 隔离：本 Case 配置前复位 FMAC、Service 状态和 Resource Pool。
    support.crg.reset(CrgPeripheral.FMAC, instance=support.instance_id)
    support.fmac.state_reset()
    support.resource.reset()
    require_fmac_features(support, FmacFeature.FIR | FmacFeature.OUTPUT_POLICY)
    samples = (0x1000,) * 12
    coefficients = (Q15_MAX,)
    resource_ready = False
    outputs: dict[str, int] = {}

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_ready)):
        resource_ready = True
        coefficient_resource = _create_q15_resource(support, coefficients)
        history_resource = _create_q15_resource(support, (0,) * len(coefficients))
        source = _create_q15_resource(support, samples)
        destination = support.resource.create(len(samples) * 2, alignment=4)

        # 参数化执行：仅切换Shift编码，统一使用SAT16使Shift路径生效。
        for shift in (FmacShift.LEFT1, FmacShift.NONE, FmacShift.RIGHT1):
            # 配置：应用当前Shift并重新装载相同系数。
            support.fmac.configure(
                replace(
                    default_config(),
                    output_mode=FmacOutputMode.SAT16,
                    output_shift=shift,
                ),
            )
            support.fmac.coefficients_load(
                coefficient_resource.handle,
                0,
                len(coefficients),
            )
            support.fmac.x1_preload(history_resource.handle, 0, len(coefficients))

            # 激励：执行相同FIR事务并读取当前Shift输出。
            process_result = support.fmac.process(
                FmacFunction.FIR,
                len(coefficients),
                0,
                FmacDataFormat.Q15,
                source.handle,
                0,
                destination.handle,
                0,
                len(samples),
            )
            shift_outputs = unpack_q15(support.resource.read(destination, len(samples) * 2))
            outputs[shift.name] = shift_outputs[-1]

            # 单轮判定：事务数量必须完整，避免不完整传输伪造Shift差异。
            assert process_result.accepted_count == len(samples)
            assert process_result.read_count == len(samples)
            support.fmac.stop()
            support.fmac.clear()

        # 观测：保存三种Shift下的硬件稳态末值。
        record_observation(
            record_property,
            key="actual_output",
            value=outputs,
            source="dut",
            endpoint="FMAC_Y_DATA.Q15",
        )
        record_result(et_artifact_dir, "fmac_p1_011", output_values=outputs)

        # 断言：三种Shift必须形成严格、单调的幅值关系。
        assert abs(outputs["LEFT1"]) > abs(outputs["NONE"])
        assert abs(outputs["NONE"]) > abs(outputs["RIGHT1"])

    record_evidence(record_property, "dut")


# 测试 Feature：
# 1. FMAC逐Source IRQ Enable、Disable、Mask、Unmask、Force和Clear。
# 2. FMAC IRQ Raw/Status、Service latch和真实投递计数。
#
# 测试方法：
# 1. 参数化全部11个Source，先在Enable+Mask条件下Force并读取Raw/Status。
# 2. Clear后Unmask再次Force，读取Service latch和event count证明真实ISR投递。
# 3. Clear并Disable当前Source，确认状态恢复且不污染下一参数实例。
#
# 通过条件：
# 1. Mask阶段Raw置位、Status不置位且event count不增加。
# 2. Unmask阶段latched包含当前Source且event count增加。
# 3. Clear后Raw/Status/latched均不包含当前Source，Disable成功完成。
@pytest.mark.parametrize(
    "event",
    tuple(event for event in FmacIrqEvent if event is not FmacIrqEvent.ALL),
    ids=lambda value: value.name.lower(),
)
def test_fmac_p1_012_irq_control_matrix(
    fmac_support,
    event: FmacIrqEvent,
    et_artifact_dir: Path,
    record_property,
) -> None:

    # 准备：每个Source从Clear、Enable和Mask的独立状态开始。
    support = fmac_support
    # 隔离：本 Case 配置前复位 FMAC、Service 状态和 Resource Pool。
    support.crg.reset(CrgPeripheral.FMAC, instance=support.instance_id)
    support.fmac.state_reset()
    support.resource.reset()
    require_fmac_features(support, FmacFeature.INTERRUPTS | FmacFeature.TEST_EXTENSIONS)
    support.fmac.configure(default_config())

    with case_cleanup_scope(lambda: _cleanup_actions(support, False)):
        support.fmac.irq_clear(event)
        support.fmac.irq_enable(event)
        support.fmac.irq_mask(event)
        baseline = support.fmac.irq_snapshot_get()

        # Mask刺激：Force进入Raw事件面，但不得形成有效投递。
        support.fmac.irq_force(event)
        masked = support.fmac.irq_snapshot_get()
        support.fmac.irq_clear(event)

        # Unmask刺激：同一Force必须进入Service latch并增加投递计数。
        support.fmac.irq_unmask(event)
        before_delivery = support.fmac.irq_snapshot_get()
        support.fmac.irq_force(event)
        delivered = support.fmac.irq_snapshot_get()

        # 恢复：清除Source并Disable，读取最终快照。
        support.fmac.irq_clear(event)
        support.fmac.irq_disable(event)
        cleared = support.fmac.irq_snapshot_get()

        # 观测：保留Mask和Unmask两个阶段的完整IRQ因果链。
        record_observation(
            record_property,
            key="masked_irq_snapshot",
            value=masked,
            source="dut",
            endpoint="FMAC_IRQ_SNAPSHOT",
        )
        record_observation(
            record_property,
            key="actual_irq_delivery",
            value=int(delivered.latched),
            source="dut",
            endpoint="FMAC_IRQ_SNAPSHOT",
        )
        record_result(
            et_artifact_dir,
            "fmac_p1_012",
            event=event,
            baseline=baseline,
            masked=masked,
            delivered=delivered,
            cleared=cleared,
        )

        # 断言：控制面、状态面和真实ISR投递三类证据必须同时成立。
        assert masked.raw & event
        assert not masked.status & event
        assert masked.event_count == baseline.event_count
        assert delivered.latched & event
        assert delivered.event_count > before_delivery.event_count
        assert not cleared.raw & event
        assert not cleared.status & event
        assert not cleared.latched & event

    record_evidence(record_property, "dut")


# 测试 Feature：
# 1. X1 Write Request由真实X1可写状态产生。
# 2. Y Read Request由真实Y可读状态产生。
#
# 测试方法：
# 1. 参数化两个Request Source，建立对应Buffer状态并启用IRQ。
# 2. X1子实例启动等待输入的FIR；Y子实例执行单抽头FIR并保留一项未读输出。
# 3. 读取Buffer状态和IRQ latch，证明事件不是Force产生。
#
# 通过条件：
# 1. X1子实例存在可写空间且latched包含X1 Write Request。
# 2. Y子实例存在未读数据且latched包含Y Read Request。
# 3. 两个子实例event count均增加，且测试中未调用IRQ Force。
@pytest.mark.parametrize(
    "event",
    (FmacIrqEvent.X1_WRITE_REQUEST, FmacIrqEvent.Y_READ_REQUEST),
    ids=lambda value: value.name.lower(),
)
def test_fmac_p1_013_natural_request_irqs(
    fmac_support,
    event: FmacIrqEvent,
    et_artifact_dir: Path,
    record_property,
) -> None:

    # 准备：两个子实例共用最小布局，但各自只构造目标Buffer条件。
    support = fmac_support
    # 隔离：本 Case 配置前复位 FMAC、Service 状态和 Resource Pool。
    support.crg.reset(CrgPeripheral.FMAC, instance=support.instance_id)
    support.fmac.state_reset()
    support.resource.reset()
    require_fmac_features(support, FmacFeature.INTERRUPTS | FmacFeature.STATUS)
    resource_ready = False

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_ready)):
        resource_ready = True
        support.fmac.configure(default_config())
        support.fmac.irq_clear(event)
        support.fmac.irq_enable(event)
        support.fmac.irq_unmask(event)
        before = support.fmac.irq_snapshot_get()

        # 激励：根据Source建立真实X1可写或Y可读硬件条件。
        if event is FmacIrqEvent.X1_WRITE_REQUEST:
            support.fmac.start(FmacFunction.FIR, feedforward_taps=1)
        else:
            coefficient = _create_q15_resource(support, (FMAC_FORMAT_TEST_COEFFICIENT,))
            history = _create_q15_resource(support, FMAC_FORMAT_TEST_HISTORY)
            source = _create_q15_resource(support, (0x1000,))
            support.fmac.coefficients_load(coefficient.handle, 0, 1)
            support.fmac.x1_preload(history.handle, 0, 1)
            support.fmac.start(FmacFunction.FIR, feedforward_taps=1)
            support.fmac.stream_write(source.handle, 0, 1)

        status = support.fmac.status_get()
        after = support.fmac.irq_snapshot_get()

        # 观测：记录真实Buffer状态和Service latch，不使用Force辅助。
        record_observation(
            record_property,
            key="actual_irq_source",
            value=int(after.latched),
            source="dut",
            endpoint="FMAC_STATUS.BUFFER",
        )
        record_result(
            et_artifact_dir,
            "fmac_p1_013",
            event=event,
            status={"x1_spare": status.x1_spare_count, "y_unread": status.y_unread_count},
            before=before,
            after=after,
        )

        # 断言：Source对应的Buffer现场和真实投递必须一起成立。
        if event is FmacIrqEvent.X1_WRITE_REQUEST:
            assert status.x1_spare_count > 0
        else:
            assert status.y_unread_count > 0
        assert after.latched & event
        assert after.event_count > before.event_count

    record_evidence(record_property, "dut")


# 测试 Feature：
# 1. 累加器Saturation自然状态与IRQ。
# 2. X1 Overflow自然状态与IRQ。
# 3. Y Underflow自然状态与IRQ。
#
# 测试方法：
# 1. 参数化三类异常Source，先Clear并启用对应IRQ。
# 2. Saturation使用远越界FIR刺激；Overflow装满X1后额外写；Underflow在空Y额外读。
# 3. 读取硬件状态、IRQ latch和投递计数，再逐Source清理。
#
# 通过条件：
# 1. 当前Source对应的硬件状态为1。
# 2. IRQ latch包含且只要求包含当前Source，event count增加。
# 3. 刺激来自真实数据路径，不调用IRQ Force伪造覆盖。
@pytest.mark.parametrize(
    "event",
    (
        FmacIrqEvent.SATURATION,
        FmacIrqEvent.X1_OVERFLOW,
        FmacIrqEvent.Y_UNDERFLOW,
    ),
    ids=lambda value: value.name.lower(),
)
def test_fmac_p1_014_natural_error_irqs(
    fmac_support,
    event: FmacIrqEvent,
    et_artifact_dir: Path,
    record_property,
) -> None:

    # 准备：每个参数实例独立重置Resource与FMAC状态。
    support = fmac_support
    # 隔离：本 Case 配置前复位 FMAC、Service 状态和 Resource Pool。
    support.crg.reset(CrgPeripheral.FMAC, instance=support.instance_id)
    support.fmac.state_reset()
    support.resource.reset()
    require_fmac_features(
        support,
        FmacFeature.INTERRUPTS | FmacFeature.STATUS | FmacFeature.TEST_EXTENSIONS,
    )
    resource_ready = False

    with case_cleanup_scope(lambda: _cleanup_actions(support, resource_ready)):
        resource_ready = True

        # 激励：只执行当前Source对应的自然硬件动作。
        if event is FmacIrqEvent.SATURATION:
            # Saturation配置：16抽头最大正值超过内部s(26,22)范围。
            saturation_samples = (Q15_MAX,) * 16
            saturation_coefficients = (Q15_MAX,) * 16
            support.fmac.configure(
                replace(
                    default_config(x1_size=32, x2_size=16, y_size=32),
                    final_policy=FmacFinalPolicy.WRAP,
                )
            )
            coefficient_resource = _create_q15_resource(support, saturation_coefficients)
            history_resource = _create_q15_resource(support, (0,) * len(saturation_coefficients))
            source = _create_q15_resource(support, saturation_samples)
            destination = support.resource.create(
                len(saturation_samples) * 2,
                alignment=4,
            )
            support.fmac.coefficients_load(
                coefficient_resource.handle,
                0,
                len(saturation_coefficients),
            )
            support.fmac.x1_preload(
                history_resource.handle,
                0,
                len(saturation_coefficients),
            )

            # IRQ基线：在配置和装载完成后再启用，确保只捕获运算产生的Saturation。
            support.fmac.irq_clear(event)
            support.fmac.irq_enable(event)
            support.fmac.irq_unmask(event)
            before = support.fmac.irq_snapshot_get()

            # Saturation激励：执行完整FIR事务，状态断言在统一观测阶段完成。
            saturation_result = support.fmac.process(
                FmacFunction.FIR,
                len(saturation_coefficients),
                0,
                FmacDataFormat.Q15,
                source.handle,
                0,
                destination.handle,
                0,
                len(saturation_samples),
            )
            assert saturation_result.accepted_count == len(saturation_samples)
            assert saturation_result.read_count == len(saturation_samples)
        elif event is FmacIrqEvent.X1_OVERFLOW:
            # Overflow准备：配置200项X1和单抽头系数，先用正式装载接口填满X1。
            overflow_capacity = 200
            overflow_config = replace(
                default_config(x1_size=overflow_capacity, x2_size=1, y_size=1),
                x1_start=1,
                x2_start=0,
                y_start=201,
            )
            coefficient_resource = _create_q15_resource(support, (FMAC_FORMAT_TEST_COEFFICIENT,))
            overflow_resource = _create_q15_resource(
                support,
                (FMAC_OVERFLOW_TEST_INPUT,) * overflow_capacity,
            )
            support.fmac.configure(overflow_config)
            support.fmac.coefficients_load(coefficient_resource.handle, 0, 1)
            overflow_loaded = support.fmac.x1_preload(
                overflow_resource.handle,
                0,
                overflow_capacity,
            )

            # IRQ基线：在启动FIR前启用，只捕获后续无空间直写产生的Overflow。
            support.fmac.irq_clear(event)
            support.fmac.irq_enable(event)
            support.fmac.irq_unmask(event)
            before = support.fmac.irq_snapshot_get()

            # 运行态建立：单抽头FIR启动会先消费一项X1，并产生一项Y输出。
            support.fmac.start(FmacFunction.FIR, 1)
            overflow_startup = support.fmac.status_get()

            # 越界刺激：第一笔补回启动消费形成的空位，第二笔在X1无空间时形成Overflow。
            support.fmac.data_write_one_unchecked(FMAC_OVERFLOW_TEST_INPUT)
            support.fmac.data_write_one_unchecked(FMAC_OVERFLOW_TEST_INPUT)

            overflow_status = support.fmac.status_get()

            # 等待：给Overflow状态一个有界可见窗口，再进入统一IRQ观测阶段。
            for _ in range(FMAC_STREAM_READ_MAX_POLLS):
                if overflow_status.x1_overflow:
                    break
                overflow_status = support.fmac.status_get()
        else:
            # Underflow准备：建立一笔真实FIR输出，再把Y中的有效数据全部读空。
            coefficient_resource = _create_q15_resource(support, (FMAC_FORMAT_TEST_COEFFICIENT,))
            history_resource = _create_q15_resource(support, FMAC_FORMAT_TEST_HISTORY)
            input_resource = _create_q15_resource(support, (0x1000,) * 4)
            support.fmac.configure(default_config(x1_size=16, x2_size=1, y_size=4))
            support.fmac.coefficients_load(coefficient_resource.handle, 0, 1)
            support.fmac.x1_preload(history_resource.handle, 0, 1)
            support.fmac.start(FmacFunction.FIR, 1)
            support.fmac.stream_write(input_resource.handle, 0, 4)

            # 等待四项输出进入Y后全部读出，再额外空读一次产生Underflow。
            output_status = support.fmac.status_get()

            # 等待：有界轮询确认输出数据已经进入Y Buffer。
            for _ in range(FMAC_STREAM_READ_MAX_POLLS):
                if output_status.y_unread_count >= 4:
                    break
                output_status = support.fmac.status_get()

            # 先耗尽四项有效输出，再建立IRQ基线，避免正常读操作干扰目标Source。
            for _ in range(4):
                support.fmac.data_read_one_unchecked()

            support.fmac.irq_clear(event)
            support.fmac.irq_enable(event)
            support.fmac.irq_unmask(event)
            before = support.fmac.irq_snapshot_get()

            # 空读：按状态推进而不是假设一次读取即可跨过硬件读流水线。
            underflow_status = support.fmac.status_get()

            # 有界刺激：最多追加Y容量加一次空读，直到自然Underflow Source出现。
            for _ in range(5):
                if underflow_status.y_underflow:
                    break
                support.fmac.data_read_one_unchecked()
                underflow_status = support.fmac.status_get()

        status = support.fmac.status_get()
        after = support.fmac.irq_snapshot_get()

        # 观测：保存硬件状态与IRQ投递证据，避免只看命令返回值。
        status_set = {
            FmacIrqEvent.SATURATION: status.accumulator_saturation,
            FmacIrqEvent.X1_OVERFLOW: status.x1_overflow,
            FmacIrqEvent.Y_UNDERFLOW: status.y_underflow,
        }[event]
        source_observed = status_set or bool(after.raw & event)
        record_observation(
            record_property,
            key="actual_irq_source",
            value=int(after.latched),
            source="dut",
            endpoint=f"FMAC_STATUS.{event.name}",
        )
        record_result(
            et_artifact_dir,
            "fmac_p1_014",
            event=event,
            status_set=status_set,
            source_observed=source_observed,
            before=before,
            after=after,
        )

        # 断言：状态位或IRQ Raw至少保留一个硬件Source证据，并且ISR投递必须成立。
        if event is FmacIrqEvent.X1_OVERFLOW:
            assert overflow_loaded == overflow_capacity
            assert overflow_startup.x1_spare_count == 1
            assert overflow_status.x1_overflow
        assert source_observed
        assert after.latched & event
        assert after.event_count > before.event_count

    record_evidence(record_property, "dut")


# 测试 Feature：
# 1. FMAC P、P+Q和Q参数错误自然IRQ。
# 2. 参数错误IRQ经目标ISR投递，并可Clear后合法恢复。
#
# 测试方法：
# 1. P Error使用FIR P=0；PQ Error使用IIR P=4、Q=5且X2容量为8。
# 2. Q Error使用IIR P=1、Q=5且Y容量为4、X2容量为8。
# 3. 每个子实例只使能目标Source，采集Raw/Status/latch后Clear并执行合法对照。
#
# 通过条件：
# 1. 参数错误三位中只有当前目标Source置位。
# 2. 当前Source进入有效Status和ISR latch，投递计数增加。
# 3. Clear后合法参数不再产生相同错误Source，且功能可正常启动。
@pytest.mark.parametrize(
    "event,function,invalid_p,invalid_q,valid_p,valid_q,x2_size,y_size",
    (
        (FmacIrqEvent.P_ERROR, FmacFunction.FIR, 17, 0, 1, 0, 32, 16),
        (FmacIrqEvent.PQ_ERROR, FmacFunction.IIR, 5, 4, 4, 3, 8, 8),
        (FmacIrqEvent.Q_ERROR, FmacFunction.IIR, 1, 5, 1, 3, 8, 4),
    ),
    ids=("p_error", "pq_error", "q_error"),
)
def test_fmac_p1_015_natural_parameter_error_irqs(
    fmac_support,
    event: FmacIrqEvent,
    function: FmacFunction,
    invalid_p: int,
    invalid_q: int,
    valid_p: int,
    valid_q: int,
    x2_size: int,
    y_size: int,
    et_artifact_dir: Path,
    record_property,
) -> None:

    # 准备：参数错误测试需要绕过PC合法性门禁，但仍由受管Service/Wrap执行。
    support = fmac_support
    # 隔离：本 Case 配置前复位 FMAC、Service 状态和 Resource Pool。
    support.crg.reset(CrgPeripheral.FMAC, instance=support.instance_id)
    support.fmac.state_reset()
    support.resource.reset()
    require_fmac_features(
        support,
        FmacFeature.INTERRUPTS | FmacFeature.TEST_EXTENSIONS,
    )
    parameter_error_mask = FmacIrqEvent.P_ERROR | FmacIrqEvent.PQ_ERROR | FmacIrqEvent.Q_ERROR

    with case_cleanup_scope(lambda: _cleanup_actions(support, False)):
        support.fmac.configure(default_config(x1_size=16, x2_size=x2_size, y_size=y_size))
        support.fmac.irq_clear(parameter_error_mask)
        support.fmac.irq_enable(event)
        support.fmac.irq_unmask(event)
        before = support.fmac.irq_snapshot_get()

        # 错误刺激：只让当前P/Q约束越界，其他布局参数保持合法。
        support.fmac.start_unchecked(function, invalid_p, invalid_q)
        invalid = support.fmac.irq_snapshot_get()

        # 恢复：先提交合法P/Q消除电平错误条件，再清除目标IRQ状态。
        support.fmac.stop()
        support.fmac.clear()
        support.fmac.configure(default_config(x1_size=16, x2_size=x2_size, y_size=y_size))
        support.fmac.start(function, valid_p, valid_q)
        recovered_status = support.fmac.status_get()
        support.fmac.irq_clear(event)
        before_recovery = support.fmac.irq_snapshot_get()
        support.fmac.stop()
        recovered_irq = support.fmac.irq_snapshot_get()

        # 观测：记录错误Source、投递计数和合法恢复终态。
        record_observation(
            record_property,
            key="actual_irq_source",
            value=int(invalid.raw & parameter_error_mask),
            source="dut",
            endpoint="FMAC_IRQ.PARAMETER_ERROR",
        )
        record_result(
            et_artifact_dir,
            "fmac_p1_015",
            event=event,
            parameters={"invalid": [invalid_p, invalid_q], "valid": [valid_p, valid_q]},
            invalid_snapshot=invalid,
            recovery={"active": recovered_status.active, "snapshot": recovered_irq},
        )

        # 断言：错误身份、真实投递和合法恢复必须同时成立。
        assert invalid.raw & parameter_error_mask == event
        assert invalid.status & event
        assert invalid.latched & event
        assert invalid.event_count > before.event_count
        assert recovered_status.active
        assert not recovered_irq.raw & event
        assert not recovered_irq.status & event
        assert recovered_irq.event_count == before_recovery.event_count

    record_evidence(record_property, "dut")
