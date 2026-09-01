# FMAC P0 Formal Case。
#
# 职责：验证Clear恢复和活动控制两项最小硬件闭环。
# 边界：只通过CRG/FMAC/Resource Driver访问设备，不读取寄存器。
# 依赖：仅依赖CRG、FMAC、Resource Driver和本地Case辅助函数。

from __future__ import annotations

from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction
from ...drivers.crg import CrgPeripheral
from ...drivers.fmac import FmacDataFormat, FmacFeature, FmacFunction
from ...scheduling.run_context import record_evidence
from ..case_cleanup import case_cleanup_scope
from ._support import require_fmac_features
from .fmac_helpers import (
    default_config,
    iir_direct_form1_q15,
    pack_q15,
    record_result,
    unpack_q15,
)
from .fmac_helpers import (
    record_fmac_observation as record_observation,
)

pytestmark = [pytest.mark.hardware, pytest.mark.ip("fmac")]

FMAC_FIR_COEFFICIENTS = (0x4000, 0x2000, 0x1000, 0x0800)
FMAC_FIR_SAMPLE_COUNT = 12
FMAC_FIR_STEADY_TAIL_COUNT = 4
FMAC_IIR_REFLECTION = (19448, -29793, 9645, -4884, 671, -81)
FMAC_IIR_LADDER = (590, 3540, 8851, 11801, 8851, 3540, 590)
FMAC_IIR_INPUT = (
    0,
    5276,
    -1548,
    13844,
    7,
    17551,
    5802,
    16142,
    14198,
    12009,
    21624,
    8678,
    24576,
    8672,
    21611,
    11990,
    14172,
    16111,
    5765,
    17510,
    -37,
    13797,
    -1598,
    5225,
    -51,
    -5327,
    1498,
    -13892,
    -52,
    -17592,
    -5838,
    -16174,
)


# 测试 Feature：
# 1. FMAC X2系数装载。
# 2. FMAC signed Q15四抽头FIR稳态卷积。
# 3. FMAC Process收发数量和显式Stop状态。
#
# 测试方法：
# 1. 向X2装载四个2的幂Q15系数，避免参考结果受舍入策略影响。
# 2. 分别输入12个固定正样本和12个固定负样本，执行one-shot FIR。
# 3. 固定比较最后4个稳态输出，不搜索首有效输出位置。
#
# 通过条件：
# 1. 正负稳态尾段分别精确等于四个0x1E00和四个-0x1E00。
# 2. Process接受和读取数量均为12，不存在静默截断。
# 3. 显式Stop后Active为0。
@pytest.mark.parametrize(
    ("input_value", "expected_value"),
    ((0x2000, 0x1E00), (-0x2000, -0x1E00)),
    ids=("positive", "negative"),
)
def test_fmac_p0_001_q15_fir_steady_state(
    fmac_support,
    input_value: int,
    expected_value: int,
    et_artifact_dir: Path,
    record_property,
) -> None:

    # 准备：建立本参数实例独立的Resource和清理状态。
    support = fmac_support
    # 隔离：本 Case 配置前复位 FMAC、Service 状态和 Resource Pool。
    support.crg.reset(CrgPeripheral.FMAC, instance=support.instance_id)
    support.fmac.state_reset()
    support.resource.reset()
    require_fmac_features(
        support,
        FmacFeature.FIXED_Q15 | FmacFeature.FIR | FmacFeature.STATUS,
    )
    samples = (input_value,) * FMAC_FIR_SAMPLE_COUNT
    expected_tail = (expected_value,) * FMAC_FIR_STEADY_TAIL_COUNT
    configured = False
    resource_ready = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if configured:
            actions.extend(
                (
                    ("FMAC stop", support.fmac.stop),
                    ("FMAC clear", support.fmac.clear),
                )
            )
        if resource_ready:
            actions.append(("Resource pool reset", support.resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        resource_ready = True
        coefficient_payload = pack_q15(FMAC_FIR_COEFFICIENTS)
        history_payload = pack_q15((0,) * len(FMAC_FIR_COEFFICIENTS))
        source_payload = pack_q15(samples)
        coefficients = support.resource.create(len(coefficient_payload), alignment=4)
        history = support.resource.create(len(history_payload), alignment=4)
        source = support.resource.create(len(source_payload), alignment=4)
        destination = support.resource.create(len(source_payload), alignment=4)
        support.resource.write(coefficients, coefficient_payload)
        support.resource.write(history, history_payload)
        support.resource.write(source, source_payload)

        # 配置：提交完整公共配置，装载全部前馈系数并用零样本建立FIR初始历史。
        support.fmac.configure(default_config())
        configured = True
        support.fmac.coefficients_load(
            coefficients.handle,
            0,
            len(FMAC_FIR_COEFFICIENTS),
        )
        history_loaded = support.fmac.x1_preload(
            history.handle,
            0,
            len(FMAC_FIR_COEFFICIENTS),
        )

        # 激励：执行一笔固定12样本的Q15 FIR事务。
        process_result = support.fmac.process(
            FmacFunction.FIR,
            len(FMAC_FIR_COEFFICIENTS),
            0,
            FmacDataFormat.Q15,
            source.handle,
            0,
            destination.handle,
            0,
            len(samples),
        )
        actual_output = unpack_q15(support.resource.read(destination, len(source_payload)))
        actual_tail = actual_output[-FMAC_FIR_STEADY_TAIL_COUNT:]

        # 结束：显式Stop后读取Active，证明本参数实例有界结束。
        support.fmac.stop()
        stopped = support.fmac.status_get()

        # 观测：保存完整硬件输出、固定稳态尾段和事务数量。
        record_observation(
            record_property,
            key="actual_output",
            value=actual_output,
            source="dut",
            endpoint="FMAC_DATA.OUTPUT_STREAM",
        )
        record_observation(
            record_property,
            key="actual_active",
            value=stopped.active,
            source="dut",
            endpoint="FMAC_STATUS.ACTIVE",
        )
        record_result(
            et_artifact_dir,
            "fmac_p0_001",
            input_value=input_value,
            expected_tail=expected_tail,
            actual_tail=actual_tail,
            counts={
                "history_loaded": history_loaded,
                "accepted": process_result.accepted_count,
                "read": process_result.read_count,
            },
        )

        # 断言：独立Golden、传输完整性和停止状态必须同时成立。
        assert history_loaded == len(FMAC_FIR_COEFFICIENTS)
        assert process_result.accepted_count == len(samples)
        assert process_result.read_count == len(samples)
        assert actual_tail == expected_tail
        assert not stopped.active

    record_evidence(record_property, "dut")


# 测试 Feature：
# 1. FMAC X2前馈/反馈系数分段装载。
# 2. FMAC Q15 IIR Direct Form 1数据路径和反馈状态初始化。
#
# 测试方法：
# 1. 装载固定7项Ladder前馈系数、6级Reflection反馈系数及零初态。
# 2. 对32个历史确定性Q15样本执行一次IIR事务。
# 3. 使用独立Q15 Direct Form 1软件Oracle逐元素比较全部输出。
#
# 通过条件：
# 1. Process接受和读取数量均为32。
# 2. 32个硬件输出与独立Q15 Oracle逐元素完全一致。
# 3. 显式Stop后FMAC不再处于Active状态。
def test_fmac_p0_002_q15_iir_reference(
    fmac_support,
    et_artifact_dir: Path,
    record_property,
) -> None:

    # 准备：计算独立Oracle并建立本Case全部Resource。
    support = fmac_support
    # 隔离：本 Case 配置前复位 FMAC、Service 状态和 Resource Pool。
    support.crg.reset(CrgPeripheral.FMAC, instance=support.instance_id)
    support.fmac.state_reset()
    support.resource.reset()
    require_fmac_features(support, FmacFeature.IIR | FmacFeature.FIXED_Q15)
    expected = iir_direct_form1_q15(
        FMAC_IIR_INPUT,
        FMAC_IIR_REFLECTION,
        FMAC_IIR_LADDER,
    )
    reflection_payload = pack_q15(FMAC_IIR_REFLECTION)
    ladder_payload = pack_q15(FMAC_IIR_LADDER)
    input_payload = pack_q15(FMAC_IIR_INPUT)
    initial_payload = pack_q15((0,) * len(FMAC_IIR_REFLECTION))

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        return (
            ("FMAC stop", support.fmac.stop),
            ("FMAC clear", support.fmac.clear),
            ("Resource pool reset", support.resource.reset),
        )

    with case_cleanup_scope(cleanup_actions):
        reflection = support.resource.create(len(reflection_payload), alignment=4)
        ladder = support.resource.create(len(ladder_payload), alignment=4)
        source = support.resource.create(len(input_payload), alignment=4)
        initial = support.resource.create(len(initial_payload), alignment=4)
        destination = support.resource.create(len(input_payload), alignment=4)
        support.resource.write(reflection, reflection_payload)
        support.resource.write(ladder, ladder_payload)
        support.resource.write(source, input_payload)
        support.resource.write(initial, initial_payload)

        # 配置：使用互不重叠的三区域并装载两段系数。
        support.fmac.configure(default_config(x1_size=32, x2_size=16, y_size=32))
        support.fmac.coefficients_load(
            ladder.handle,
            0,
            len(FMAC_IIR_LADDER),
            feedback_handle=reflection.handle,
            feedback_offset=0,
            feedback_count=len(FMAC_IIR_REFLECTION),
        )

        # 初态：X1和Y均装载六项零状态，与独立Direct Form 1 Oracle的初始状态一致。
        x1_loaded = support.fmac.x1_preload(
            initial.handle,
            0,
            len(FMAC_IIR_REFLECTION),
        )
        y_loaded = support.fmac.y_preload(
            initial.handle,
            0,
            len(FMAC_IIR_REFLECTION),
        )

        # 激励与观测：执行IIR并读取全部硬件输出。
        result = support.fmac.process(
            FmacFunction.IIR,
            len(FMAC_IIR_LADDER),
            len(FMAC_IIR_REFLECTION),
            FmacDataFormat.Q15,
            source.handle,
            0,
            destination.handle,
            0,
            len(FMAC_IIR_INPUT),
        )
        actual = unpack_q15(support.resource.read(destination, len(input_payload)))
        support.fmac.stop()
        stopped = support.fmac.status_get()

        # 记录：在决定性断言前保存输入状态、完整输出和传输数量。
        record_observation(
            record_property,
            key="actual_output",
            value=actual,
            source="dut",
            endpoint="FMAC_DATA.OUTPUT_STREAM",
        )
        record_observation(
            record_property,
            key="actual_active",
            value=stopped.active,
            source="dut",
            endpoint="FMAC_STATUS.ACTIVE",
        )
        record_result(
            et_artifact_dir,
            "fmac_p0_002",
            expected=expected,
            actual=actual,
            preload_counts={"x1": x1_loaded, "y": y_loaded},
            process_counts={"accepted": result.accepted_count, "read": result.read_count},
        )

        # 断言：系数/初态装载、输出Golden和停止终态必须全部闭合。
        assert x1_loaded == len(FMAC_IIR_REFLECTION)
        assert y_loaded == len(FMAC_IIR_REFLECTION)
        assert result.accepted_count == len(FMAC_IIR_INPUT)
        assert result.read_count == len(FMAC_IIR_INPUT)
        assert actual == expected
        assert not stopped.active

    record_evidence(record_property, "dut")


# 测试 Feature：
# 1. FMAC Clear清除动态错误状态。
# 2. FMAC Clear后保持准静态配置，可重新进入正常操作。
#
# 测试方法：
# 1. 配置单抽头FIR并输入一个样本，产生真实Y输出。
# 2. 在活动会话中执行有界超量读取，建立Y Underflow动态现场，再显式Stop。
# 3. 执行Clear，对比Clear前后Y Underflow和准静态配置。
#
# 通过条件：
# 1. Clear前Y Underflow为1，证明动态状态真实建立。
# 2. 显式Stop后Active为0，Clear后Y Underflow恢复为0。
# 3. Clear后配置快照与提交配置一致。
def test_fmac_p0_003_clear_and_recovery(
    fmac_support,
    et_artifact_dir: Path,
    record_property,
) -> None:

    # 准备：建立最小FIR资源；Unchecked Read仅用于产生可由Clear清除的硬件状态。
    support = fmac_support
    # 隔离：本 Case 配置前复位 FMAC、Service 状态和 Resource Pool。
    support.crg.reset(CrgPeripheral.FMAC, instance=support.instance_id)
    support.fmac.state_reset()
    support.resource.reset()
    require_fmac_features(
        support,
        FmacFeature.CLEAR | FmacFeature.FIR | FmacFeature.STATUS | FmacFeature.TEST_EXTENSIONS,
    )
    config = default_config(x1_size=4, x2_size=4, y_size=4)
    configured = False
    resource_ready = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if configured:
            actions.extend(
                (
                    ("FMAC stop", support.fmac.stop),
                    ("FMAC clear", support.fmac.clear),
                )
            )
        if resource_ready:
            actions.append(("Resource pool reset", support.resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        resource_ready = True
        coefficient_payload = pack_q15((0x7FFF,))
        history_payload = pack_q15((0,))
        source_payload = pack_q15((0x1000,))
        coefficients = support.resource.create(len(coefficient_payload), alignment=4)
        history = support.resource.create(len(history_payload), alignment=4)
        source = support.resource.create(len(source_payload), alignment=4)
        support.resource.write(coefficients, coefficient_payload)
        support.resource.write(history, history_payload)
        support.resource.write(source, source_payload)

        # 配置：装载单抽头系数和零历史，启动FIR并产生一个真实Y输出。
        support.fmac.configure(config)
        configured = True
        support.fmac.coefficients_load(coefficients.handle, 0, 1)
        history_loaded = support.fmac.x1_preload(history.handle, 0, 1)
        support.fmac.start(FmacFunction.FIR, feedforward_taps=1)
        written = support.fmac.stream_write(source.handle, 0, 1)

        # 激励：读取次数大于Y总容量，确保在活动会话内自然触发Underflow。
        for _ in range(config.y_size + 1):
            support.fmac.data_read_one_unchecked()
        before = support.fmac.status_get()
        support.fmac.stop()
        stopped = support.fmac.status_get()

        # 清除：Clear后重新读取动态状态和准静态配置快照。
        support.fmac.clear()
        after = support.fmac.status_get()
        snapshot = support.fmac.config_snapshot_get()

        # 观测：保存Clear前后真实Underflow状态和配置读回。
        record_observation(
            record_property,
            key="underflow_before_clear",
            value=before.y_underflow,
            source="dut",
            endpoint="FMAC_STATUS.Y_UNDERFLOW",
        )
        record_observation(
            record_property,
            key="underflow_after_clear",
            value=after.y_underflow,
            source="dut",
            endpoint="FMAC_STATUS.Y_UNDERFLOW",
        )
        record_result(
            et_artifact_dir,
            "fmac_p0_003",
            counts={"history_loaded": history_loaded, "written": written},
            before={"active": before.active, "y_underflow": before.y_underflow},
            stopped={"active": stopped.active},
            after={"active": after.active, "y_underflow": after.y_underflow},
            config_preserved=snapshot == config,
        )

        # 断言：真实输出、显式Stop和Clear动态状态恢复必须同时成立。
        assert history_loaded == 1
        assert written == 1
        assert before.y_underflow
        assert not stopped.active
        assert not after.y_underflow
        assert snapshot == config

    record_evidence(record_property, "dut")


# 测试 Feature：
# 1. FMAC Start使过滤功能进入活动状态。
# 2. FMAC Stop显式终止活动功能并允许再次启动。
#
# 测试方法：
# 1. 配置最小FMAC布局，启动单抽头FIR但不写入输入数据。
# 2. 读取Active状态，随后执行Stop并再次读取状态。
# 3. 重复一次Start/Stop，验证控制路径可恢复。
#
# 通过条件：
# 1. 两次Start后Active均为1。
# 2. 两次Stop后Active均为0。
# 3. 控制过程无超时、永久Busy或残留活动状态。
def test_fmac_p0_004_start_stop_recovery(
    fmac_support,
    et_artifact_dir: Path,
    record_property,
) -> None:

    # 准备：只验证活动控制，不引入数值Oracle或跨IP依赖。
    support = fmac_support
    # 隔离：本 Case 配置前复位 FMAC、Service 状态和 Resource Pool。
    support.crg.reset(CrgPeripheral.FMAC, instance=support.instance_id)
    support.fmac.state_reset()
    support.resource.reset()
    require_fmac_features(support, FmacFeature.FIR | FmacFeature.STATUS)
    support.fmac.configure(default_config())

    with case_cleanup_scope(
        lambda: (
            ("FMAC stop", support.fmac.stop),
            ("FMAC clear", support.fmac.clear),
        )
    ):
        # 第一轮：Start后读取Active，再显式Stop。
        support.fmac.start(FmacFunction.FIR, feedforward_taps=1)
        first_started = support.fmac.status_get()
        support.fmac.stop()
        first_stopped = support.fmac.status_get()

        # 第二轮：重复同一控制序列，证明前轮没有残留Busy状态。
        support.fmac.start(FmacFunction.FIR, feedforward_taps=1)
        second_started = support.fmac.status_get()
        support.fmac.stop()
        second_stopped = support.fmac.status_get()

        # 观测：活动位直接来自目标侧状态快照。
        record_observation(
            record_property,
            key="actual_active",
            value=(
                first_started.active,
                first_stopped.active,
                second_started.active,
                second_stopped.active,
            ),
            source="dut",
            endpoint="FMAC_STATUS.ACTIVE",
        )
        record_result(
            et_artifact_dir,
            "fmac_p0_004",
            active_sequence=(
                first_started.active,
                first_stopped.active,
                second_started.active,
                second_stopped.active,
            ),
        )

        # 断言：活动控制必须形成1→0→1→0的完整硬件序列。
        assert first_started.active
        assert not first_stopped.active
        assert second_started.active
        assert not second_stopped.active

    record_evidence(record_property, "dut")
