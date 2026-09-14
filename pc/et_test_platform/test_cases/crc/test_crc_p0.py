# CRC P0 Formal Case。
#
# 职责：验证 CRC 能力身份、基础模式、结果链路和生命周期恢复。
# 边界：只通过稳定 Driver API 操作设备，不访问 Codec/Transport/Register。
# 依赖：仅依赖 CRC Case Fixture、本地 Support、Resource Driver 和结果记录器。

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction
from ...drivers.crc import CrcConfig, CrcFeature, CrcMode, CrcXorOut
from ...drivers.crg import CrgPeripheral
from ...profiles.capabilities import ChipCapabilities
from ...results.recorder import write_json_result
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import (
    CrcSupportFactory,
    calculate_crc_reference,
    make_crc_pattern,
    require_crc_runtime_capability,
    require_crc_static_capability,
)

pytestmark = [pytest.mark.hardware, pytest.mark.ip("crc")]


# =============================================================================
# 能力与身份
# =============================================================================


# 测试 Feature：
# CRC 全部声明实例的静态能力、运行时能力和身份一致性。
#
# 测试方法：
# 1. 读取 Capability/Runtime Registry 共有的全部 CRC 实例。
# 2. 逐实例核对模式、IRQ、阈值、同步上限和核心 Feature。
# 3. 保存每个实例的静态声明与运行时返回，便于定位 Profile 或 Firmware 偏差。
#
# 通过条件：
# 1. 至少存在一个 CRC 实例，静态模式与运行时模式完全一致。
# 2. 运行时能力结构合法，核心 Feature、IRQ 和限制均不缺失。
# 3. 每个静态实例都存在对应 Runtime Service，不接受缺失实例或未知能力位。
def test_crc_p0_001_runtime_capabilities(
    target_capabilities: ChipCapabilities,
    crc_support_for: CrcSupportFactory,
    crc_instance_ids: tuple[int, ...],
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
) -> None:

    # 只读 Case：仅核对静态/运行时能力，不执行 Feature 配置，无需前置复位。

    static_features = (
        "module_enable",
        "polynomial",
        "initial_seed",
        "result",
        "length",
    )
    runtime_features = (
        CrcFeature.MODULE_ENABLE
        | CrcFeature.POLYNOMIAL
        | CrcFeature.INITIAL_SEED
        | CrcFeature.RESULT
        | CrcFeature.LENGTH
        | CrcFeature.CALCULATE
    )
    results: list[dict[str, object]] = []
    validations: list[dict[str, object]] = []

    # 先收集所有实例的只读能力快照；最终 Artifact 发布后再统一执行断言，
    # 避免某个实例的首个失败让同一 Case 的报告证据半途丢失。
    for instance_id in crc_instance_ids:
        support = crc_support_for(instance_id)
        # Gate：逐项确认当前实例具备 P0 依赖的基础静态 Feature。
        for feature in static_features:
            require_crc_static_capability(
                target_capabilities,
                instance_id=instance_id,
                feature=feature,
            )

        require_crc_runtime_capability(
            support.runtime,
            feature_bits=int(runtime_features),
        )
        static_modes = target_capabilities.options(
            "crc",
            "modes",
            instance=support.instance_name,
        )
        actual_modes = tuple(mode.name.lower() for mode in support.runtime.modes)
        expected_fifo_threshold_max = target_capabilities.limit(
            "crc",
            "fifo_threshold_max",
            instance=support.instance_name,
        )

        record_property("expected_modes", static_modes)
        record_property("expected_irq_events", 0x07)
        record_observation(
            record_property,
            key="actual_modes",
            value=list(actual_modes),
            source="dut",
            endpoint="CRC_CAPABILITIES.MODES",
        )
        record_observation(
            record_property,
            key="actual_irq_events",
            value=int(support.runtime.irq_events),
            source="dut",
            endpoint="CRC_CAPABILITIES.IRQ_EVENTS",
        )
        record_observation(
            record_property,
            key="actual_max_calculate_bytes",
            value=support.runtime.max_calculate_bytes,
            source="dut",
            endpoint="CRC_CAPABILITIES.MAX_CALCULATE_BYTES",
        )

        results.append(
            {
                "instance": support.instance_name,
                "api_version": support.runtime.api_version,
                "features": int(support.runtime.features),
                "modes": [mode.name for mode in support.runtime.modes],
                "irq_events": int(support.runtime.irq_events),
                "fifo_threshold_max": support.runtime.fifo_threshold_max,
                "max_calculate_bytes": support.runtime.max_calculate_bytes,
                "bounded_synchronous_calculate": support.runtime.bounded_synchronous_calculate,
            }
        )
        validations.append(
            {
                "instance": support.instance_name,
                "modes_match": actual_modes == static_modes,
                "irq_match": support.runtime.irq_events.value == 0x07,
                "fifo_limit_match": (
                    support.runtime.fifo_threshold_max == expected_fifo_threshold_max
                ),
                "bounded_calculate": support.runtime.bounded_synchronous_calculate,
                "calculate_limit_valid": 0 < support.runtime.max_calculate_bytes <= 4096,
            }
        )

    write_json_result(
        et_artifact_dir / "crc_p0_001_runtime_capabilities.json",
        {
            "measurement_schema": "et.measurement.v1",
            "ip": "crc",
            "instances": results,
            "validations": validations,
        },
    )

    assert validations
    assert all(bool(item["modes_match"]) for item in validations), validations
    assert all(bool(item["irq_match"]) for item in validations), validations
    assert all(bool(item["fifo_limit_match"]) for item in validations), validations
    assert all(bool(item["bounded_calculate"]) for item in validations), validations
    assert all(bool(item["calculate_limit_valid"]) for item in validations), validations


# =============================================================================
# 基础模式与结果
# =============================================================================


_P0_MODE_VECTORS = (
    (
        CrcConfig(
            mode=CrcMode.CRC8,
            polynomial=0x07,
            initial_value=0xFF,
            ref_in=True,
            ref_out=True,
        ),
        bytes(range(1, 8)),
        0x5C,
    ),
    (
        CrcConfig(
            mode=CrcMode.CRC16,
            polynomial=0x1021,
            initial_value=0xC6C6,
            ref_in=True,
            ref_out=True,
            byte_swap=True,
        ),
        bytes(range(1, 8)),
        0x6656,
    ),
    (
        CrcConfig(
            mode=CrcMode.CRC32,
            polynomial=0xA833982B,
            initial_value=0xFFFFFFFF,
            ref_in=True,
            ref_out=True,
            byte_swap=True,
            xor_out=CrcXorOut.ALL_ONE,
        ),
        bytes(range(1, 9)),
        0x9D23C4CA,
    ),
)


# 测试 Feature：
# CRC8、CRC16、CRC32 基础计算、Result 和 Length 完成链路。
#
# 测试方法：
# 1. 参数化历史固定向量，先用独立 PC Golden 复核固定 Expected。
# 2. 将 Payload 写入 Resource，通过 CRC Driver 配置并同步计算。
# 3. 计算完成后分别读取返回结果、Remaining Input Count 和 Result 寄存器事实。
#
# 通过条件：
# 1. PC Golden 与历史固定 Expected 完全一致。
# 2. 硬件结果等于 Expected，Remaining Input Count 为零且 Result 读回一致。
# 3. CRC8、CRC16、CRC32 三种自然宽度都独立通过，不以模式间差异代替精确判断。
@pytest.mark.usefixtures("crc_reference_evidence")
@pytest.mark.parametrize(
    ("config", "payload", "fixed_expected"),
    _P0_MODE_VECTORS,
    ids=("crc8", "crc16", "crc32"),
)
def test_crc_p0_002_mode_reference_vectors(
    crc0, resource_driver, config: CrcConfig, payload: bytes, fixed_expected: int
) -> None:
    # 1）复位：硬件、固件上下文和资源池由同一个公开入口建立基线。
    crc_handle = crc0
    crc_handle.reset()
    expected = calculate_crc_reference(config, payload)
    assert expected == fixed_expected

    # 2）IP 配置与激励：保持原向量、对齐和 enable/configure 顺序。
    source = resource_driver.create(len(payload), alignment=4)
    resource_driver.write(source, payload)
    crc_handle.enable()
    crc_handle.configure(config)

    # 3）获取并判断结果：计算返回、剩余输入数和独立 Result 读回。
    measured = crc_handle.calculate(source.address, len(payload))
    readback = crc_handle.result_get()
    assert measured.result == expected
    assert measured.remaining_input_count == 0
    assert readback == expected


# =============================================================================
# 生命周期与恢复
# =============================================================================


# 测试 Feature：
# CRC Enable、Configure、Calculate、Disable 和重新启用恢复。
#
# 测试方法：
# 1. 对第一份 Payload 执行完整 Module 生命周期并精确核对结果。
# 2. Module 退出后重新 Enable/Configure，对第二份 Payload 再计算。
# 3. 两轮使用不同输入并保存独立结果，防止旧 Result 被误判为第二轮成功。
#
# 通过条件：
# 1. 第一次计算结果等于独立 Golden，退出时 Disable 成功。
# 2. 重新启用后第二次计算仍精确正确，不继承上轮配置状态。
# 3. 两轮 Remaining Input Count 均为零，第二轮结果来自本轮输入而非状态残留。
def test_crc_p0_003_lifecycle_recovery(
    crc_support_for: CrcSupportFactory,
    crc_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CRC, instance=crc_instance_id)
    resource_driver.reset()

    support = crc_support_for(crc_instance_id)
    config = CrcConfig(
        mode=CrcMode.CRC32,
        polynomial=0x04C11DB7,
        initial_value=0xFFFFFFFF,
        byte_swap=True,
    )
    first_payload = make_crc_pattern(32, seed=0x68010001)
    second_payload = make_crc_pattern(32, seed=0x68010002)
    first_expected = calculate_crc_reference(config, first_payload)
    second_expected = calculate_crc_reference(config, second_payload)
    resource_owned = False
    crc_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if crc_enabled:
            actions.append(("CRC module disable", support.crc.disable))
        if resource_owned:
            actions.append(("Resource pool reset", support.resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        support.resource.reset()
        resource_owned = True
        first_source = support.resource.create(len(first_payload), alignment=4)
        second_source = support.resource.create(len(second_payload), alignment=4)
        support.resource.write(first_source, first_payload)
        support.resource.write(second_source, second_payload)

        support.crc.enable()
        crc_enabled = True
        support.crc.configure(config)

        first_actual = support.crc.calculate(
            first_source.address,
            len(first_payload),
        )
        record_property("first_expected_crc", first_expected)
        record_observation(
            record_property,
            key="first_actual_crc",
            value=first_actual.result,
            source="dut",
            endpoint="RESULT.CRC",
        )
        record_observation(
            record_property,
            key="first_remaining_input_count",
            value=first_actual.remaining_input_count,
            source="dut",
            endpoint="LENGTH.REMAINING_INPUT_COUNT",
        )

        # 第二轮属于本 Case 的必要证明，即使第一轮数据错误，也先安全完成第二轮观测，
        # 再统一断言，保证 FAIL 与 PASS 使用同一组决定性 Evidence。
        support.crc.disable()
        crc_enabled = False
        support.crc.enable()
        crc_enabled = True
        support.crc.configure(config)

        second_actual = support.crc.calculate(
            second_source.address,
            len(second_payload),
        )
        record_property("second_expected_crc", second_expected)
        record_observation(
            record_property,
            key="second_actual_crc",
            value=second_actual.result,
            source="dut",
            endpoint="RESULT.CRC",
        )
        record_observation(
            record_property,
            key="second_remaining_input_count",
            value=second_actual.remaining_input_count,
            source="dut",
            endpoint="LENGTH.REMAINING_INPUT_COUNT",
        )

    write_json_result(
        et_artifact_dir / "crc_p0_003_lifecycle_recovery.json",
        {
            "measurement_schema": "et.measurement.v1",
            "ip": "crc",
            "case_id": "crc_p0_003",
            "instance": support.instance_name,
            "first_expected": first_expected,
            "first_actual": first_actual.result,
            "first_remaining_input_count": first_actual.remaining_input_count,
            "second_expected": second_expected,
            "second_actual": second_actual.result,
            "second_remaining_input_count": second_actual.remaining_input_count,
        },
    )

    assert first_actual.result == first_expected
    assert first_actual.remaining_input_count == 0
    assert second_actual.result == second_expected
    assert second_actual.remaining_input_count == 0
