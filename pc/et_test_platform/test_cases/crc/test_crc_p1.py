# CRC P1 Formal Case。
#
# 职责：验证 CRC 配置变换、Length/FIFO/Check 和 IRQ 原子 Feature。
# 边界：只通过稳定 Driver API 操作设备，不访问 Codec/Transport/Register。
# 依赖：仅依赖 CRC Case Fixture、本地 Support、Resource Driver 和结果记录器。

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction
from ...drivers.crc import (
    CrcConfig,
    CrcInputAccessWidth,
    CrcIrqEvent,
    CrcMode,
    CrcXorOut,
)
from ...drivers.crg import CrgPeripheral
from ...results.recorder import write_json_result
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import (
    CrcSupportFactory,
    calculate_crc_reference,
    make_crc_pattern,
)

pytestmark = [pytest.mark.hardware, pytest.mark.ip("crc")]

_BASE_PAYLOAD = bytes(range(1, 33))


# =============================================================================
# Polynomial、Seed 与数据变换
# =============================================================================


# 测试 Feature：
# CRC Polynomial 可编程能力。
#
# 测试方法：
# 1. 参数化多个 CRC32 Polynomial，对同一 Payload 计算独立 Golden。
# 2. 每组都重新配置硬件并执行一次同步计算。
# 3. 读取计算结果和 Remaining Input Count，保存 Polynomial 与对应 Oracle。
#
# 通过条件：
# 1. 每个 Polynomial 的硬件结果精确等于对应 Golden。
# 2. 每轮 Remaining Input Count 都为零。
# 3. 三个 Polynomial 独立完成生命周期，不允许复用上一参数的配置或结果。
@pytest.mark.parametrize("polynomial", (0x04C11DB7, 0x1EDC6F41, 0xA833982B))
def test_crc_p1_001_programmable_polynomial(
    crc_support_for: CrcSupportFactory,
    crc_instance_id: int,
    et_artifact_dir: Path,
    polynomial: int,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：使用固定 Seed 和 Payload，仅改变 Polynomial。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CRC, instance=crc_instance_id)
    resource_driver.reset()

    support = crc_support_for(crc_instance_id)
    config = CrcConfig(
        mode=CrcMode.CRC32,
        polynomial=polynomial,
        initial_value=0xFFFFFFFF,
        byte_swap=True,
    )
    expected = calculate_crc_reference(config, _BASE_PAYLOAD)
    crc_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if crc_enabled:
            actions.append(("CRC module disable", support.crc.disable))
        actions.append(("Resource pool reset", support.resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 资源：重置独占池，创建并写入固定Payload Buffer。
        support.resource.reset()
        source = support.resource.create(len(_BASE_PAYLOAD), alignment=4)
        support.resource.write(source, _BASE_PAYLOAD)

        # 配置：启用CRC Module并写入当前Polynomial。
        support.crc.enable()
        crc_enabled = True
        support.crc.configure(config)

        # 刺激与观测：计算固定Payload并读取同步结果。
        measured = support.crc.calculate(source.address, len(_BASE_PAYLOAD))

        # 证据：配置/Golden保持Measurement，Result与LENGTH保持DUT硬件来源。
        record_property("polynomial", polynomial)
        record_property("expected_crc", expected)
        record_observation(
            record_property,
            key="actual_crc",
            value=measured.result,
            source="dut",
            endpoint="RESULT.CRC",
        )
        record_observation(
            record_property,
            key="remaining_input_count",
            value=measured.remaining_input_count,
            source="dut",
            endpoint="LENGTH.REMAINING_INPUT_COUNT",
        )

        # 断言：Polynomial对应的结果和Length终态必须精确。
        assert measured.result == expected
        assert measured.remaining_input_count == 0

    # 记录：保存 Polynomial、Expected 和 Actual。
    write_json_result(
        et_artifact_dir / f"crc_p1_001_poly_{polynomial:08x}.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "crc_p1_001",
            "polynomial": polynomial,
            "expected": expected,
            "actual": measured.result,
            "remaining_input_count": measured.remaining_input_count,
        },
    )


# 测试 Feature：
# CRC Initial Seed 可编程能力和 Case 间无残留。
#
# 测试方法：
# 1. 参数化零、全一和普通 Seed，每轮完整重新配置。
# 2. 对同一 Payload 分别计算并与独立 Golden 比较。
# 3. 每轮记录 Seed、Expected、Actual 和 Length 终态，便于区分配置残留与计算错误。
#
# 通过条件：
# 1. 每个 Seed 的硬件结果精确等于对应 Golden。
# 2. 各参数独立通过，不依赖上一轮硬件结果。
# 3. 三轮 Remaining Input Count 均为零，结果宽度保持 CRC32 规范值。
@pytest.mark.parametrize("initial_value", (0x00000000, 0xFFFFFFFF, 0x13579BDF))
def test_crc_p1_002_initial_seed(
    crc_support_for: CrcSupportFactory,
    crc_instance_id: int,
    et_artifact_dir: Path,
    initial_value: int,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：构造只改变 Initial Seed 的 CRC32 配置。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CRC, instance=crc_instance_id)
    resource_driver.reset()

    support = crc_support_for(crc_instance_id)
    config = CrcConfig(
        mode=CrcMode.CRC32,
        polynomial=0x04C11DB7,
        initial_value=initial_value,
        byte_swap=True,
    )
    expected = calculate_crc_reference(config, _BASE_PAYLOAD)
    crc_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if crc_enabled:
            actions.append(("CRC module disable", support.crc.disable))
        actions.append(("Resource pool reset", support.resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 资源：重置独占池，创建并写入固定Payload Buffer。
        support.resource.reset()
        source = support.resource.create(len(_BASE_PAYLOAD), alignment=4)
        support.resource.write(source, _BASE_PAYLOAD)

        # 配置：启用CRC Module并写入当前Initial Seed。
        support.crc.enable()
        crc_enabled = True
        support.crc.configure(config)

        # 刺激与观测：计算固定Payload并读取同步结果。
        measured = support.crc.calculate(source.address, len(_BASE_PAYLOAD))

        # 证据：Seed/Golden是配置和Oracle；Result/LENGTH来自DUT。
        record_property("initial_value", initial_value)
        record_property("expected_crc", expected)
        record_observation(
            record_property,
            key="actual_crc",
            value=measured.result,
            source="dut",
            endpoint="RESULT.CRC",
        )
        record_observation(
            record_property,
            key="remaining_input_count",
            value=measured.remaining_input_count,
            source="dut",
            endpoint="LENGTH.REMAINING_INPUT_COUNT",
        )

        # 断言：硬件结果只由当前配置和输入决定。
        assert measured.result == expected
        assert measured.remaining_input_count == 0

    # 记录：保存 Seed 和精确结果。
    write_json_result(
        et_artifact_dir / f"crc_p1_002_seed_{initial_value:08x}.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "crc_p1_002",
            "initial_value": initial_value,
            "expected": expected,
            "actual": measured.result,
            "remaining_input_count": measured.remaining_input_count,
        },
    )


# 测试 Feature：
# CRC16/CRC32 ByteSwap 输入单元变换。
#
# 测试方法：
# 1. 参数化 CRC16/CRC32 和 ByteSwap Off/On，使用非对称 Payload。
# 2. 按 CPU 小端 Access 语义计算独立 Golden，再执行硬件计算。
# 3. 对完整访问单元和尾部不足单元分别保留输入语义，记录模式与开关组合。
#
# 通过条件：
# 1. 四组硬件结果分别精确等于 Golden。
# 2. 同一模式的 Off/On 结果与各自预处理语义一致。
# 3. ByteSwap 只改变完整 CRC16/32 输入单元顺序，不错误交换尾部剩余 Byte。
@pytest.mark.parametrize(
    ("mode", "byte_swap"),
    (
        (CrcMode.CRC16, False),
        (CrcMode.CRC16, True),
        (CrcMode.CRC32, False),
        (CrcMode.CRC32, True),
    ),
)
def test_crc_p1_003_byte_swap(
    crc_support_for: CrcSupportFactory,
    crc_instance_id: int,
    et_artifact_dir: Path,
    mode: CrcMode,
    byte_swap: bool,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：选择当前模式自然宽度的 Polynomial 和 Seed。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CRC, instance=crc_instance_id)
    resource_driver.reset()

    support = crc_support_for(crc_instance_id)
    config = CrcConfig(
        mode=mode,
        polynomial=0x1021 if mode is CrcMode.CRC16 else 0x04C11DB7,
        initial_value=0xFFFF if mode is CrcMode.CRC16 else 0xFFFFFFFF,
        byte_swap=byte_swap,
    )
    payload = bytes((0x11, 0x22, 0x43, 0x84, 0x15, 0xA6, 0x37, 0xC8))
    expected = calculate_crc_reference(config, payload)
    crc_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if crc_enabled:
            actions.append(("CRC module disable", support.crc.disable))
        actions.append(("Resource pool reset", support.resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 资源：重置独占池，创建并写入四字节对齐Payload。
        support.resource.reset()
        source = support.resource.create(len(payload), alignment=4)
        support.resource.write(source, payload)

        # 配置：启用CRC Module并写入当前ByteSwap参数。
        support.crc.enable()
        crc_enabled = True
        support.crc.configure(config)

        # 刺激与观测：计算Payload并读取同步结果。
        measured = support.crc.calculate(source.address, len(payload))

        # 证据：变换配置是Measurement，Result/LENGTH保留DUT端点身份。
        record_property("mode", mode.name)
        record_property("byte_swap", byte_swap)
        record_property("expected_crc", expected)
        record_observation(
            record_property,
            key="actual_crc",
            value=measured.result,
            source="dut",
            endpoint="RESULT.CRC",
        )
        record_observation(
            record_property,
            key="remaining_input_count",
            value=measured.remaining_input_count,
            source="dut",
            endpoint="LENGTH.REMAINING_INPUT_COUNT",
        )

        # 断言：ByteSwap变换后的CRC必须精确。
        assert measured.result == expected
        assert measured.remaining_input_count == 0

    # 记录：保存模式、ByteSwap 和结果。
    write_json_result(
        et_artifact_dir / f"crc_p1_003_{mode.name.lower()}_swap_{int(byte_swap)}.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "crc_p1_003",
            "mode": mode.name,
            "byte_swap": byte_swap,
            "expected": expected,
            "actual": measured.result,
            "remaining_input_count": measured.remaining_input_count,
        },
    )


# 测试 Feature：
# CRC RefIn 对每个输入 Byte 的 bit reflection。
#
# 测试方法：
# 1. 参数化 RefIn Off/On，对相同 Payload 使用相同 CRC32 配置。
# 2. 独立 Golden 明确执行逐 Byte reflection，硬件执行同一配置。
# 3. 保存 RefIn、Expected 和 Actual，确保评审时能直接对照同一输入的两种语义。
#
# 通过条件：
# 1. Off/On 两组硬件结果分别等于 Golden。
# 2. 不使用“两个结果不相等”替代精确 Oracle。
# 3. 两轮 Remaining Input Count 都为零，硬件完整消费本轮 Payload。
@pytest.mark.parametrize("ref_in", (False, True))
def test_crc_p1_004_ref_in(
    crc_support_for: CrcSupportFactory,
    crc_instance_id: int,
    et_artifact_dir: Path,
    ref_in: bool,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：固定其余配置，只改变 RefIn。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CRC, instance=crc_instance_id)
    resource_driver.reset()

    support = crc_support_for(crc_instance_id)
    config = CrcConfig(
        mode=CrcMode.CRC32,
        polynomial=0x1EDC6F41,
        initial_value=0xFFFFFFFF,
        ref_in=ref_in,
        byte_swap=True,
    )
    expected = calculate_crc_reference(config, _BASE_PAYLOAD)
    crc_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if crc_enabled:
            actions.append(("CRC module disable", support.crc.disable))
        actions.append(("Resource pool reset", support.resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 资源：重置独占池，创建并写入固定Payload。
        support.resource.reset()
        source = support.resource.create(len(_BASE_PAYLOAD), alignment=4)
        support.resource.write(source, _BASE_PAYLOAD)

        # 配置：启用CRC Module并写入当前RefIn参数。
        support.crc.enable()
        crc_enabled = True
        support.crc.configure(config)

        # 刺激与观测：计算固定Payload并读取同步结果。
        measured = support.crc.calculate(source.address, len(_BASE_PAYLOAD))

        # 证据：RefIn和Golden为Measurement；Result/LENGTH为DUT Observation。
        record_property("ref_in", ref_in)
        record_property("expected_crc", expected)
        record_observation(
            record_property,
            key="actual_crc",
            value=measured.result,
            source="dut",
            endpoint="RESULT.CRC",
        )
        record_observation(
            record_property,
            key="remaining_input_count",
            value=measured.remaining_input_count,
            source="dut",
            endpoint="LENGTH.REMAINING_INPUT_COUNT",
        )

        # 断言：硬件结果必须等于逐Byte Reflection Golden，且输入完整消费。
        assert measured.result == expected
        assert measured.remaining_input_count == 0

    # 记录：保存 RefIn 和精确结果。
    write_json_result(
        et_artifact_dir / f"crc_p1_004_refin_{int(ref_in)}.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "crc_p1_004",
            "ref_in": ref_in,
            "expected": expected,
            "actual": measured.result,
            "remaining_input_count": measured.remaining_input_count,
        },
    )


# 测试 Feature：
# CRC RefOut 对 Kernel 结果的自然宽度 bit reflection。
#
# 测试方法：
# 1. 参数化 RefOut Off/On，固定输入和其余配置。
# 2. 独立 Golden 在 Kernel 结束后执行对应宽度 reflection。
# 3. 使用非整双字节 Payload 同时覆盖尾部输入，再保存 RefOut 与精确结果。
#
# 通过条件：
# 1. 两组硬件结果分别精确等于 Golden。
# 2. Result 高位保持当前 CRC 宽度内的规范值。
# 3. RefOut 只作用于最终 CRC16 结果，不改变输入消费数量和尾部处理。
@pytest.mark.parametrize("ref_out", (False, True))
def test_crc_p1_005_ref_out(
    crc_support_for: CrcSupportFactory,
    crc_instance_id: int,
    et_artifact_dir: Path,
    ref_out: bool,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：使用 CRC16 观察自然宽度 RefOut。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CRC, instance=crc_instance_id)
    resource_driver.reset()

    support = crc_support_for(crc_instance_id)
    config = CrcConfig(
        mode=CrcMode.CRC16,
        polynomial=0x1021,
        initial_value=0xC6C6,
        ref_in=True,
        ref_out=ref_out,
        byte_swap=True,
    )
    payload = _BASE_PAYLOAD[:15]
    expected = calculate_crc_reference(config, payload)
    crc_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if crc_enabled:
            actions.append(("CRC module disable", support.crc.disable))
        actions.append(("Resource pool reset", support.resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 资源：重置独占池，创建非整双字节长度Payload。
        support.resource.reset()
        source = support.resource.create(len(payload), alignment=4)
        support.resource.write(source, payload)

        # 配置：启用CRC Module并写入当前RefOut参数。
        support.crc.enable()
        crc_enabled = True
        support.crc.configure(config)

        # 刺激与观测：计算Payload并读取同步结果。
        measured = support.crc.calculate(source.address, len(payload))

        # 证据：RefOut和Golden为Measurement；Result/LENGTH为DUT Observation。
        record_property("ref_out", ref_out)
        record_property("expected_crc", expected)
        record_observation(
            record_property,
            key="actual_crc",
            value=measured.result,
            source="dut",
            endpoint="RESULT.CRC",
        )
        record_observation(
            record_property,
            key="remaining_input_count",
            value=measured.remaining_input_count,
            source="dut",
            endpoint="LENGTH.REMAINING_INPUT_COUNT",
        )

        # 断言：Result必须等于当前RefOut的精确Golden并完整消费输入。
        assert measured.result == expected
        assert measured.result <= 0xFFFF
        assert measured.remaining_input_count == 0

    # 记录：保存 RefOut 和结果。
    write_json_result(
        et_artifact_dir / f"crc_p1_005_refout_{int(ref_out)}.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "crc_p1_005",
            "ref_out": ref_out,
            "expected": expected,
            "actual": measured.result,
            "remaining_input_count": measured.remaining_input_count,
        },
    )


# 测试 Feature：
# CRC XorOut 全零和当前模式全一变换。
#
# 测试方法：
# 1. 参数化 ALL_ZERO/ALL_ONE，固定 CRC16 Kernel 配置。
# 2. 独立 Golden 按 16-Bit 宽度执行最终 XOR，再读取硬件结果。
# 3. 保存 XorOut 选择、Expected、Actual 和 Remaining Input Count。
#
# 通过条件：
# 1. 两种 XorOut 的硬件结果分别精确等于 Golden。
# 2. ALL_ONE 只作用于 16-Bit，不污染高位。
# 3. 两轮输入均完整消费，XorOut 不影响 Length 完成路径。
@pytest.mark.parametrize("xor_out", tuple(CrcXorOut))
def test_crc_p1_006_xor_out(
    crc_support_for: CrcSupportFactory,
    crc_instance_id: int,
    et_artifact_dir: Path,
    xor_out: CrcXorOut,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：固定 CRC16 配置，只改变最终 XOR。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CRC, instance=crc_instance_id)
    resource_driver.reset()

    support = crc_support_for(crc_instance_id)
    config = CrcConfig(
        mode=CrcMode.CRC16,
        polynomial=0x3D65,
        initial_value=0,
        ref_in=True,
        ref_out=True,
        byte_swap=True,
        xor_out=xor_out,
    )
    payload = bytes(range(1, 8))
    expected = calculate_crc_reference(config, payload)
    crc_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if crc_enabled:
            actions.append(("CRC module disable", support.crc.disable))
        actions.append(("Resource pool reset", support.resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 资源：重置独占池，创建并写入CRC16 Payload。
        support.resource.reset()
        source = support.resource.create(len(payload), alignment=4)
        support.resource.write(source, payload)

        # 配置：启用CRC Module并写入当前XorOut参数。
        support.crc.enable()
        crc_enabled = True
        support.crc.configure(config)

        # 刺激与观测：计算Payload并读取同步结果。
        measured = support.crc.calculate(source.address, len(payload))

        # 证据：XorOut和Golden为Measurement；Result/LENGTH为DUT Observation。
        record_property("xor_out", xor_out.name)
        record_property("expected_crc", expected)
        record_observation(
            record_property,
            key="actual_crc",
            value=measured.result,
            source="dut",
            endpoint="RESULT.CRC",
        )
        record_observation(
            record_property,
            key="remaining_input_count",
            value=measured.remaining_input_count,
            source="dut",
            endpoint="LENGTH.REMAINING_INPUT_COUNT",
        )

        # 断言：XorOut和自然宽度必须精确，且输入完整消费。
        assert measured.result == expected
        assert measured.result <= 0xFFFF
        assert measured.remaining_input_count == 0

    # 记录：保存 XorOut 选择和结果。
    write_json_result(
        et_artifact_dir / f"crc_p1_006_xor_{xor_out.name.lower()}.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "crc_p1_006",
            "xor_out": xor_out.name,
            "expected": expected,
            "actual": measured.result,
            "remaining_input_count": measured.remaining_input_count,
        },
    )


# =============================================================================
# Length、ALR 与 Check
# =============================================================================


# 测试 Feature：
# CRC32 任意 Byte remainder、CRC16 奇偶 Byte Length，以及 LENGTH 编程读回。
#
# 测试方法：
# 1. 参数化 CRC32 的 N*4+0/1/2/3 与 CRC16 奇偶长度。
# 2. 对每个长度先编程 LENGTH 并读回输入事务计数，再执行硬件计算。
# 3. 对每个长度计算独立 Golden，逐项记录模式、Byte 长度、Expected 和 Actual。
#
# 通过条件：
# 1. LENGTH 读回精确等于当前模式的完整访问单元数加尾部 Byte 事务数。
# 2. 每个长度的硬件结果精确等于 Golden，计算后 Remaining Input Count 均归零。
# 3. 所有自然对齐长度和非整单元尾部都被真实执行，不通过补零规避 remainder。
@pytest.mark.parametrize(
    ("mode", "length_bytes"),
    (
        (CrcMode.CRC32, 8),
        (CrcMode.CRC32, 9),
        (CrcMode.CRC32, 10),
        (CrcMode.CRC32, 11),
        (CrcMode.CRC16, 8),
        (CrcMode.CRC16, 9),
    ),
)
def test_crc_p1_007_arbitrary_byte_length(
    crc_support_for: CrcSupportFactory,
    crc_instance_id: int,
    et_artifact_dir: Path,
    mode: CrcMode,
    length_bytes: int,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：按模式选择配置并生成指定 Byte 长度的确定性Payload。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CRC, instance=crc_instance_id)
    resource_driver.reset()

    support = crc_support_for(crc_instance_id)
    config = CrcConfig(
        mode=mode,
        polynomial=0x1021 if mode is CrcMode.CRC16 else 0x04C11DB7,
        initial_value=0xFFFF if mode is CrcMode.CRC16 else 0xFFFFFFFF,
        byte_swap=True,
    )
    payload = make_crc_pattern(length_bytes, seed=0x70000000 + length_bytes)
    expected = calculate_crc_reference(config, payload)
    unit_bytes = int(mode) // 8
    expected_input_count = (length_bytes // unit_bytes) + (length_bytes % unit_bytes)
    crc_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if crc_enabled:
            actions.append(("CRC module disable", support.crc.disable))
        actions.append(("Resource pool reset", support.resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 资源：重置独占池并写入参数化Byte长度Payload。
        support.resource.reset()
        source = support.resource.create(length_bytes, alignment=4)
        support.resource.write(source, payload)

        # 配置：启用CRC Module并写入当前模式配置。
        support.crc.enable()
        crc_enabled = True
        support.crc.configure(config)

        # LENGTH证明：显式设置Byte长度并读取硬件事务计数，独立证明编程/读回语义。
        support.crc.data_length_set(length_bytes)
        programmed_count = support.crc.remaining_input_count_get()
        record_property("mode", mode.name)
        record_property("length_bytes", length_bytes)
        record_property("expected_input_count", expected_input_count)
        record_observation(
            record_property,
            key="programmed_input_count",
            value=programmed_count,
            source="dut",
            endpoint="LENGTH.REMAINING_INPUT_COUNT",
        )
        assert programmed_count == expected_input_count

        # 刺激与观测：按Byte长度执行同步计算。
        measured = support.crc.calculate(source.address, length_bytes)
        record_property("expected_crc", expected)
        record_observation(
            record_property,
            key="actual_crc",
            value=measured.result,
            source="dut",
            endpoint="RESULT.CRC",
        )
        record_observation(
            record_property,
            key="remaining_input_count",
            value=measured.remaining_input_count,
            source="dut",
            endpoint="LENGTH.REMAINING_INPUT_COUNT",
        )

        # 断言：Remainder输入和Length终态必须正确。
        assert measured.result == expected
        assert measured.remaining_input_count == 0

    # 记录：保存LENGTH读回、模式、Byte长度和精确结果。
    write_json_result(
        et_artifact_dir / f"crc_p1_007_{mode.name.lower()}_{length_bytes}.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "crc_p1_007",
            "mode": mode.name,
            "length_bytes": length_bytes,
            "expected_input_count": expected_input_count,
            "programmed_input_count": programmed_count,
            "expected": expected,
            "actual": measured.result,
            "remaining_input_count": measured.remaining_input_count,
        },
    )


# 测试 Feature：
# CRC Auto Length Reload 连续同长度计算。
#
# 测试方法：
# 1. 开启 ALR，显式写入一次 Length，并准备两份相同长度但内容不同的 Payload。
# 2. 同一配置下连续执行两次计算，并分别与独立 Golden 比较。
# 3. 第二轮不重新写 Length，通过不同 Payload 排除 Result 复用造成的假通过。
#
# 通过条件：
# 1. 两轮结果分别精确等于各自 Golden。
# 2. 两轮 Remaining Input Count 都自动恢复到初始 16 个 32-Bit 输入事务。
# 3. 第二轮 Result 与第二份输入的 Golden 一致，证明 Length 自动重载而非状态残留。
def test_crc_p1_008_auto_length_reload(
    crc_support_for: CrcSupportFactory,
    crc_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：生成两份相同长度的确定性输入。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CRC, instance=crc_instance_id)
    resource_driver.reset()

    support = crc_support_for(crc_instance_id)
    config = CrcConfig(
        mode=CrcMode.CRC32,
        polynomial=0x04C11DB7,
        initial_value=0xFFFFFFFF,
        byte_swap=True,
        auto_length_reload=True,
    )
    first_payload = make_crc_pattern(64, seed=0xA1)
    second_payload = make_crc_pattern(64, seed=0xA2)
    first_expected = calculate_crc_reference(config, first_payload)
    second_expected = calculate_crc_reference(config, second_payload)
    crc_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if crc_enabled:
            actions.append(("CRC module disable", support.crc.disable))
        actions.append(("Resource pool reset", support.resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 资源：重置独占池并准备两份相同长度的独立输入。
        support.resource.reset()
        first_source = support.resource.create(64, alignment=4)
        second_source = support.resource.create(64, alignment=4)
        support.resource.write(first_source, first_payload)
        support.resource.write(second_source, second_payload)

        # 配置：启用CRC Module、开启Auto Length Reload并写入一次Length。
        support.crc.enable()
        crc_enabled = True
        support.crc.configure(config)
        support.crc.data_length_set(len(first_payload))

        # 第一轮刺激与证据：计算第一份输入，并观测Reload后的Length。
        first = support.crc.calculate(first_source.address, 64)
        record_property("first_expected_crc", first_expected)
        record_observation(
            record_property,
            key="first_actual_crc",
            value=first.result,
            source="dut",
            endpoint="RESULT.CRC",
        )
        record_observation(
            record_property,
            key="first_remaining_input_count",
            value=first.remaining_input_count,
            source="dut",
            endpoint="LENGTH.REMAINING_INPUT_COUNT",
        )
        assert first.result == first_expected
        assert first.remaining_input_count == len(first_payload) // 4

        # 第二轮刺激与证据：不重写Length，直接计算不同输入。
        second = support.crc.calculate(second_source.address, 64)
        record_property("second_expected_crc", second_expected)
        record_observation(
            record_property,
            key="second_actual_crc",
            value=second.result,
            source="dut",
            endpoint="RESULT.CRC",
        )
        record_observation(
            record_property,
            key="second_remaining_input_count",
            value=second.remaining_input_count,
            source="dut",
            endpoint="LENGTH.REMAINING_INPUT_COUNT",
        )
        assert second.result == second_expected
        assert second.remaining_input_count == len(second_payload) // 4

    # 记录：保存两轮精确结果。
    write_json_result(
        et_artifact_dir / "crc_p1_008_auto_length_reload.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "crc_p1_008",
            "first_expected": first_expected,
            "first_actual": first.result,
            "first_remaining_input_count": first.remaining_input_count,
            "second_expected": second_expected,
            "second_actual": second.result,
            "second_remaining_input_count": second.remaining_input_count,
        },
    )


# 测试 Feature：
# CRC Check 匹配路径。
#
# 测试方法：
# 1. 由 PC Golden 计算 Expected，配置 Result Check 并写入相同 CHECK。
# 2. 执行计算并读取 Result 与 CHECK_ERROR Raw/Status。
# 3. 在计算前清除旧 Pending，避免历史错误状态冒充本轮结果。
#
# 通过条件：
# 1. CRC Result 精确等于 Expected。
# 2. CHECK_ERROR 在本轮硬件 Raw 和 Status 中均不置位。
# 3. 不使用历史 Service Last Event 作为匹配路径的必要证明。
def test_crc_p1_009_check_match(
    crc_support_for: CrcSupportFactory,
    crc_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：构造启用 Result Check 的确定性向量。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CRC, instance=crc_instance_id)
    resource_driver.reset()

    support = crc_support_for(crc_instance_id)
    config = CrcConfig(
        mode=CrcMode.CRC32,
        polynomial=0x1EDC6F41,
        initial_value=0xFFFFFFFF,
        ref_in=True,
        ref_out=True,
        byte_swap=True,
        result_check=True,
        xor_out=CrcXorOut.ALL_ONE,
    )
    payload = bytes(range(1, 8))
    expected = calculate_crc_reference(config, payload)
    event = CrcIrqEvent.CHECK_ERROR
    crc_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if crc_enabled:
            actions.append(("CRC module disable", support.crc.disable))
        actions.append(("Resource pool reset", support.resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 资源：重置独占池并写入确定性Payload。
        support.resource.reset()
        source = support.resource.create(len(payload), alignment=4)
        support.resource.write(source, payload)

        # 配置：启用CRC Module、清旧IRQ并写入正确Check Value。
        support.crc.enable()
        crc_enabled = True
        support.crc.configure(config)
        support.crc.irq_clear(CrcIrqEvent.ALL)
        support.crc.check_value_set(expected)

        # 刺激与观测：执行计算并读取当前硬件IRQ快照。
        measured = support.crc.calculate(source.address, len(payload))
        snapshot = support.crc.irq_snapshot_get()

        # 证据：Result与CHECK_ERROR两个硬件端点在断言前分别记录。
        record_property("expected_crc", expected)
        record_observation(
            record_property,
            key="actual_crc",
            value=measured.result,
            source="dut",
            endpoint="RESULT.CRC",
        )
        record_observation(
            record_property,
            key="check_error_raw",
            value=bool(snapshot.raw & event),
            source="dut",
            endpoint="IRQ_RAW.CHECK_ERROR",
        )
        record_observation(
            record_property,
            key="check_error_status",
            value=bool(snapshot.status & event),
            source="dut",
            endpoint="IRQ_STATUS.CHECK_ERROR",
        )

        # 断言：匹配时结果正确且硬件CHECK_ERROR不置位。
        assert measured.result == expected
        assert snapshot.raw & event == CrcIrqEvent.NONE
        assert snapshot.status & event == CrcIrqEvent.NONE

    # 记录：保存 Result 和当前硬件 IRQ 证据。
    write_json_result(
        et_artifact_dir / "crc_p1_009_check_match.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "crc_p1_009",
            "expected": expected,
            "actual": measured.result,
            "check_error_raw": bool(snapshot.raw & event),
            "check_error_status": bool(snapshot.status & event),
        },
    )


# 测试 Feature：
# CRC Check 不匹配错误源、IRQ Delivery 和回调事件记录。
#
# 测试方法：
# 1. Enable/Unmask CHECK_ERROR，设置一个确定错误的 CHECK。
# 2. 计算 Payload，比较前后 IRQ Event Count 和 ISR 保存的目标事件。
# 3. 同时保存正确 CRC Result、当前硬件Raw/Status与Service ISR证据。
#
# 通过条件：
# 1. CRC Result 仍精确等于 Golden。
# 2. Event Count 恰好增加一次，ISR Last Event/Last Raw 仅包含 CHECK_ERROR。
# 3. 当前 Raw/Status 与 ISR latch 分开记录，不互相冒充来源。
def test_crc_p1_010_check_mismatch_irq(
    crc_support_for: CrcSupportFactory,
    crc_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：使用固定向量和确定不相等的 CHECK 值。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CRC, instance=crc_instance_id)
    resource_driver.reset()

    support = crc_support_for(crc_instance_id)
    config = CrcConfig(
        mode=CrcMode.CRC32,
        polynomial=0x1EDC6F41,
        initial_value=0xFFFFFFFF,
        ref_in=True,
        ref_out=True,
        byte_swap=True,
        result_check=True,
        xor_out=CrcXorOut.ALL_ONE,
    )
    payload = bytes(range(1, 8))
    expected = calculate_crc_reference(config, payload)
    wrong_check = expected ^ 0x1
    event = CrcIrqEvent.CHECK_ERROR
    crc_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if crc_enabled:
            actions.append(("CRC module disable", support.crc.disable))
        actions.append(("Resource pool reset", support.resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 资源：重置独占池并写入确定性Payload。
        support.resource.reset()
        source = support.resource.create(len(payload), alignment=4)
        support.resource.write(source, payload)

        # 配置：启用CRC Module并建立CHECK_ERROR IRQ会话。
        support.crc.enable()
        crc_enabled = True
        support.crc.configure(config)
        support.crc.irq_clear(CrcIrqEvent.ALL)
        support.crc.irq_enable(event)
        support.crc.irq_unmask(event)
        before = support.crc.irq_snapshot_get()
        support.crc.check_value_set(wrong_check)

        # 刺激与观测：计算触发真实CHECK_ERROR，再读取当前硬件与Service快照。
        measured = support.crc.calculate(source.address, len(payload))
        after = support.crc.irq_snapshot_get()

        # 证据：寄存器事实、ISR latch和Service计数按来源分别进入Canonical Result。
        record_property("check_value", wrong_check)
        record_property("expected_crc", expected)
        record_property("event_count_before", before.event_count)
        record_property("event_count_after", after.event_count)
        record_property("event_count_delta", after.event_count - before.event_count)
        record_observation(
            record_property,
            key="actual_crc",
            value=measured.result,
            source="dut",
            endpoint="RESULT.CRC",
        )
        record_observation(
            record_property,
            key="check_error_raw",
            value=bool(after.raw & event),
            source="dut",
            endpoint="IRQ_RAW.CHECK_ERROR",
        )
        record_observation(
            record_property,
            key="check_error_status",
            value=bool(after.status & event),
            source="dut",
            endpoint="IRQ_STATUS.CHECK_ERROR",
        )
        record_observation(
            record_property,
            key="isr_latched_event",
            value=int(after.last_event),
            source="dut",
            endpoint="ISR.LATCHED.CHECK_ERROR",
        )
        record_observation(
            record_property,
            key="isr_last_raw",
            value=int(after.last_raw),
            source="dut",
            endpoint="ISR.LAST_RAW.CHECK_ERROR",
        )

        # 断言：计算结果正确，且真实IRQ回调只记录目标错误源。
        assert measured.result == expected
        assert after.event_count == before.event_count + 1
        assert after.last_event == event
        assert after.last_raw == event

    # 记录：保存 Check、Result 和前后 IRQ 快照。
    write_json_result(
        et_artifact_dir / "crc_p1_010_check_mismatch_irq.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "crc_p1_010",
            "expected": expected,
            "wrong_check": wrong_check,
            "actual": measured.result,
            "event_count_before": before.event_count,
            "event_count_after": after.event_count,
            "raw": int(after.raw),
            "status": int(after.status),
            "last_event": int(after.last_event),
            "last_raw": int(after.last_raw),
        },
    )


# =============================================================================
# FIFO 与 IRQ 原子控制
# =============================================================================


# 测试 Feature：
# CRC FIFO Threshold 对输入处理时机的控制。
#
# 测试方法：
# 1. 配置 CRC32 Threshold=5，在目标端连续写入五个相同的 32-Bit 值。
# 2. 在第四次写入后读取检查点 Result，第五次写入后读取最终 Result 和 Overflow。
# 3. PC 只发一个原子 Burst 命令，避免串口命令间隔改变 FIFO 硬件时序。
#
# 通过条件：
# 1. 第四次写入后的检查点 Result 保持写入前的实际 Result，不提前消费未达阈值的 FIFO。
# 2. 第五次写入后 Result 必须发生变化。
# 3. 本 Case 只证明 Threshold 节拍，不把该行为升级为 FIFO 物理深度动态证明。
def test_crc_p1_011_fifo_threshold(
    crc_support_for: CrcSupportFactory,
    crc_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：复用历史参考资料覆盖的五次相同 32-Bit 输入刺激。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CRC, instance=crc_instance_id)
    resource_driver.reset()

    support = crc_support_for(crc_instance_id)
    config = CrcConfig(
        mode=CrcMode.CRC32,
        polynomial=0x04C11DB7,
        initial_value=0xFFFFFFFF,
        byte_swap=True,
        fifo_threshold=5,
    )
    values = (0x12345678,) * 5
    crc_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        if not crc_enabled:
            return ()
        return (("CRC module disable", support.crc.disable),)

    with case_cleanup_scope(cleanup_actions):
        # 配置：启用CRC Module；不设置Length，保留五次紧凑写入时序。
        support.crc.enable()
        crc_enabled = True
        support.crc.configure(config)

        # 观测基线：读取任何FIFO写入前的Result。
        initial_result = support.crc.result_get()

        # 刺激：一次目标端原子Burst完成五次相同32-Bit写入。
        burst = support.crc.test_input_burst_32(values, checkpoint_count=4)

        # 证据：三个Result采样和Overflow分别绑定真实硬件端点。
        record_property("fifo_threshold", config.fifo_threshold)
        record_property("write_count", len(values))
        record_observation(
            record_property,
            key="result_before",
            value=initial_result,
            source="dut",
            endpoint="RESULT.CRC",
        )
        record_observation(
            record_property,
            key="result_after_write_4",
            value=burst.checkpoint_result,
            source="dut",
            endpoint="RESULT.CRC",
        )
        record_observation(
            record_property,
            key="result_after_write_5",
            value=burst.final_result,
            source="dut",
            endpoint="RESULT.CRC",
        )
        record_observation(
            record_property,
            key="fifo_overflow",
            value=burst.overflow,
            source="dut",
            endpoint="FIFO.OVERFLOW",
        )

        # 断言：第四次后结果不变，第五次达到阈值后结果发生变化且未溢出。
        assert burst.checkpoint_result == initial_result
        assert burst.final_result != burst.checkpoint_result
        assert not burst.overflow

    # 记录：保存逐次 Result 和最终精确结果。
    write_json_result(
        et_artifact_dir / "crc_p1_011_fifo_threshold.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "crc_p1_011",
            "threshold": config.fifo_threshold,
            "write_count": len(values),
            "checkpoint_count": burst.checkpoint_count,
            "initial_result": initial_result,
            "checkpoint_result": burst.checkpoint_result,
            "actual": burst.final_result,
            "overflow": burst.overflow,
        },
    )


# 测试 Feature：
# CRC FIFO Overflow 状态产生、清理和重新配置恢复。
#
# 测试方法：
# 1. 配置 Threshold=1，在目标端连续执行历史覆盖的七次 32-Bit 写入。
# 2. 读取 Overflow，随后退出 Module 并重新配置一轮正常短计算。
# 3. 分别保存溢出前、溢出后和恢复后的状态，区分错误产生与恢复能力。
#
# 通过条件：
# 1. Overflow 从 False 精确转换为 True。
# 2. 重新启用后的正常计算结果等于 Golden，证明错误状态可恢复。
# 3. 本 Case 只证明 Overflow/Recovery，不宣称精确动态测得 FIFO 物理深度。
def test_crc_p1_012_fifo_overflow_recovery(
    crc_support_for: CrcSupportFactory,
    crc_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：复用历史参考资料覆盖的 Threshold=1 和七次写入刺激。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CRC, instance=crc_instance_id)
    resource_driver.reset()

    support = crc_support_for(crc_instance_id)
    config = CrcConfig(
        mode=CrcMode.CRC32,
        polynomial=0x04C11DB7,
        initial_value=0xFFFFFFFF,
        byte_swap=True,
        fifo_threshold=1,
    )
    writes = 7
    crc_enabled = False
    resource_owned = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if crc_enabled:
            actions.append(("CRC module disable", support.crc.disable))
        if resource_owned:
            actions.append(("Resource pool reset", support.resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 第一轮配置：启用CRC Module并设置Threshold=1。
        support.crc.enable()
        crc_enabled = True
        support.crc.configure(config)

        # 第一轮观测：读取连续写入前的FIFO状态。
        before = support.crc.fifo_status_get()

        # 第一轮刺激：一个目标端原子Burst保留FIFO溢出所需的紧凑时序。
        values = (0x12345678,) * writes
        overflowed = support.crc.test_input_burst_32(values, checkpoint_count=0)

        # 第一轮证据：Overflow转换在任何最终断言前绑定硬件端点。
        record_property("fifo_threshold", config.fifo_threshold)
        record_property("write_count", writes)
        record_property("expected_overflow", True)
        record_observation(
            record_property,
            key="overflow_before",
            value=before.overflow,
            source="dut",
            endpoint="FIFO.OVERFLOW",
        )
        record_observation(
            record_property,
            key="overflow_after",
            value=overflowed.overflow,
            source="dut",
            endpoint="FIFO.OVERFLOW",
        )

        # 生命周期：显式Disable溢出轮，确保恢复轮重新进入Module。
        support.crc.disable()
        crc_enabled = False

        # 恢复准备：重置Resource池并写入最小正常向量。
        payload = bytes(range(1, 9))
        expected = calculate_crc_reference(config, payload)
        support.resource.reset()
        resource_owned = True
        source = support.resource.create(len(payload), alignment=4)
        support.resource.write(source, payload)

        # 恢复配置：重新Enable并写入同一CRC配置。
        support.crc.enable()
        crc_enabled = True
        support.crc.configure(config)

        # 恢复刺激：正常计算链路必须继续可用。
        recovery = support.crc.calculate(source.address, len(payload))
        record_property("recovery_expected_crc", expected)
        record_observation(
            record_property,
            key="recovery_actual_crc",
            value=recovery.result,
            source="dut",
            endpoint="RESULT.CRC",
        )
        record_observation(
            record_property,
            key="recovery_remaining_input_count",
            value=recovery.remaining_input_count,
            source="dut",
            endpoint="LENGTH.REMAINING_INPUT_COUNT",
        )

        # 记录：在最终断言前保存 Overflow 转换和恢复结果。
        write_json_result(
            et_artifact_dir / "crc_p1_012_fifo_overflow_recovery.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "crc_p1_012",
                "overflow_before": before.overflow,
                "overflow_after": overflowed.overflow,
                "recovery_expected": expected,
                "recovery_actual": recovery.result,
                "recovery_remaining_input_count": recovery.remaining_input_count,
            },
        )

        # 断言：先验证错误现象，再验证恢复链路没有被旧状态污染。
        assert not before.overflow
        assert overflowed.overflow
        assert recovery.result == expected
        assert recovery.remaining_input_count == 0


# 测试 Feature：
# CRC 三类 IRQ Source 的 Enable、Force、Delivery、Disable 和事件隔离。
#
# 测试方法：
# 1. 参数化 BUS/LENGTH/CHECK Source，分别 Enable、Unmask 并 Force。
# 2. 用 Event Count、ISR Last Event/Last Raw 证明一次真实 Delivery。
# 3. Clear并Disable同一Source后再次Force，证明硬件可保留Raw刺激但不会再递送CPU事件。
#
# 通过条件：
# 1. Enable阶段每个 Source 都恰好增加一次回调计数，ISR latch只包含当前Source。
# 2. Disable阶段再次Force后 Event Count 不增加。
# 3. 三类 Source 均独立执行，不允许其他 Source 或历史回调混入。
@pytest.mark.parametrize(
    "event",
    (
        CrcIrqEvent.BUS_ERROR,
        CrcIrqEvent.LENGTH_ERROR,
        CrcIrqEvent.CHECK_ERROR,
    ),
)
def test_crc_p1_013_irq_force_delivery(
    crc_support_for: CrcSupportFactory,
    crc_instance_id: int,
    et_artifact_dir: Path,
    event: CrcIrqEvent,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：使用最小 CRC8 配置建立 IRQ 命令前置状态。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CRC, instance=crc_instance_id)
    resource_driver.reset()

    support = crc_support_for(crc_instance_id)
    config = CrcConfig(
        mode=CrcMode.CRC8,
        polynomial=0x07,
        initial_value=0xFF,
    )
    crc_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        if not crc_enabled:
            return ()
        return (("CRC module disable", support.crc.disable),)

    with case_cleanup_scope(cleanup_actions):
        # Enable阶段：启用CRC Module、清旧状态并建立单Source IRQ会话。
        support.crc.enable()
        crc_enabled = True
        support.crc.configure(config)
        support.crc.irq_clear(CrcIrqEvent.ALL)
        support.crc.irq_enable(event)
        support.crc.irq_unmask(event)
        before = support.crc.irq_snapshot_get()

        # Enable阶段刺激：Force当前Source并读取新的硬件/Service快照。
        support.crc.irq_force(event)
        delivered = support.crc.irq_snapshot_get()

        # Enable阶段证据：Service计数与ISR latch分开保存。
        record_property("expected_irq_event", event.name)
        record_property("event_count_before", before.event_count)
        record_property("event_count_after", delivered.event_count)
        record_property("event_count_delta", delivered.event_count - before.event_count)
        record_observation(
            record_property,
            key="delivered_isr_event",
            value=int(delivered.last_event),
            source="dut",
            endpoint=f"ISR.LATCHED.{event.name}",
        )
        record_observation(
            record_property,
            key="delivered_isr_last_raw",
            value=int(delivered.last_raw),
            source="dut",
            endpoint=f"ISR.LAST_RAW.{event.name}",
        )
        assert delivered.event_count == before.event_count + 1
        assert delivered.last_event == event
        assert delivered.last_raw == event

        # Disable阶段：清除旧Pending并关闭Source，再对同一Source执行新的Force。
        support.crc.irq_clear(event)
        support.crc.irq_disable(event)
        disabled_before = support.crc.irq_snapshot_get()
        support.crc.irq_force(event)
        disabled_after = support.crc.irq_snapshot_get()

        # Disable阶段证据：Raw可反映Force刺激，但Service事件计数必须保持不变。
        record_property(
            "disabled_event_count_delta",
            disabled_after.event_count - disabled_before.event_count,
        )
        record_observation(
            record_property,
            key="disabled_force_raw",
            value=bool(disabled_after.raw & event),
            source="dut",
            endpoint=f"IRQ_RAW.{event.name}",
        )
        assert disabled_after.event_count == disabled_before.event_count

        # 恢复：清除Disable阶段Force留下的Pending，避免污染后续Case。
        support.crc.irq_clear(event)

    # 记录：保存Enable/Disable两阶段完整证据。
    write_json_result(
        et_artifact_dir / f"crc_p1_013_{event.name.lower()}.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "crc_p1_013",
            "event": event.name,
            "event_count_before": before.event_count,
            "event_count_after": delivered.event_count,
            "last_event": int(delivered.last_event),
            "last_raw": int(delivered.last_raw),
            "disabled_event_count_before": disabled_before.event_count,
            "disabled_event_count_after": disabled_after.event_count,
            "disabled_force_raw": int(disabled_after.raw),
        },
    )


# 测试 Feature：
# CRC IRQ Pending Clear 原子能力。
#
# 测试方法：
# 1. Mask BUS_ERROR 后 Force，使 Raw 置位且不进入回调。
# 2. 执行 Clear，再读取同一 Source 的 Raw/Status。
# 3. 比较 Clear 前后的 Event Count，证明 Clear 本身不会制造新的 IRQ Delivery。
#
# 通过条件：
# 1. Clear 前 Raw 仅为 BUS_ERROR、Status 为零。
# 2. Clear 后 Raw/Status 都为零，Event Count 不增加。
# 3. Pending硬件清除与Service事件历史保持分离。
def test_crc_p1_014_irq_clear(
    crc_support_for: CrcSupportFactory,
    crc_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：建立 CRC8 配置并选择单一 BUS_ERROR Source。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CRC, instance=crc_instance_id)
    resource_driver.reset()

    support = crc_support_for(crc_instance_id)
    config = CrcConfig(CrcMode.CRC8, polynomial=0x07, initial_value=0xFF)
    event = CrcIrqEvent.BUS_ERROR
    crc_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        if not crc_enabled:
            return ()
        return (("CRC module disable", support.crc.disable),)

    with case_cleanup_scope(cleanup_actions):
        # 配置：启用CRC Module，保持BUS_ERROR Mask并清除旧Pending。
        support.crc.enable()
        crc_enabled = True
        support.crc.configure(config)
        support.crc.irq_clear(CrcIrqEvent.ALL)
        support.crc.irq_enable(event)
        support.crc.irq_mask(event)
        before = support.crc.irq_snapshot_get()

        # 刺激与观测：Force BUS_ERROR，读取Clear前后的两份快照。
        support.crc.irq_force(event)
        pending = support.crc.irq_snapshot_get()
        support.crc.irq_clear(event)
        cleared = support.crc.irq_snapshot_get()

        # 证据：Raw/Status四个原子硬件事实和Service计数分别保存。
        record_property("event_count_before", before.event_count)
        record_property("event_count_after", cleared.event_count)
        record_observation(
            record_property,
            key="raw_before_clear",
            value=bool(pending.raw & event),
            source="dut",
            endpoint="IRQ_RAW.BUS_ERROR",
        )
        record_observation(
            record_property,
            key="status_before_clear",
            value=bool(pending.status & event),
            source="dut",
            endpoint="IRQ_STATUS.BUS_ERROR",
        )
        record_observation(
            record_property,
            key="raw_after_clear",
            value=bool(cleared.raw & event),
            source="dut",
            endpoint="IRQ_RAW.BUS_ERROR",
        )
        record_observation(
            record_property,
            key="status_after_clear",
            value=bool(cleared.status & event),
            source="dut",
            endpoint="IRQ_STATUS.BUS_ERROR",
        )

        # 断言：Clear 只清 Pending，回调计数保持不变。
        assert pending.raw == event
        assert pending.status == CrcIrqEvent.NONE
        assert pending.event_count == before.event_count
        assert cleared.raw == CrcIrqEvent.NONE
        assert cleared.status == CrcIrqEvent.NONE
        assert cleared.event_count == before.event_count

    # 记录：保存 Clear 前后原始状态。
    write_json_result(
        et_artifact_dir / "crc_p1_014_irq_clear.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "crc_p1_014",
            "pending_raw": int(pending.raw),
            "pending_status": int(pending.status),
            "cleared_raw": int(cleared.raw),
            "cleared_status": int(cleared.status),
            "event_count_before": before.event_count,
            "event_count_after": cleared.event_count,
        },
    )


# 测试 Feature：
# CRC IRQ Mask 对 Raw、Status 和 Delivery 的区分。
#
# 测试方法：
# 1. Enable 后 Mask LENGTH_ERROR 并 Force，读取 Raw/Status/Event Count。
# 2. Clear、Unmask 后再次 Force，读取真实Delivery的Service ISR证据。
# 3. 保存 Mask 和 Unmask 两阶段快照，直接比较同一 Source 的 Raw 与 Delivery 差异。
#
# 通过条件：
# 1. Mask 阶段 Raw 置位、Status 为零且回调计数不变。
# 2. Unmask 阶段回调计数增加，ISR Last Event/Last Raw仅为LENGTH_ERROR。
# 3. 第二阶段必须来自 Clear 后的新 Force，不允许复用第一阶段 Pending。
def test_crc_p1_015_irq_mask_raw_status(
    crc_support_for: CrcSupportFactory,
    crc_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：建立 CRC8 配置并选择 LENGTH_ERROR。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CRC, instance=crc_instance_id)
    resource_driver.reset()

    support = crc_support_for(crc_instance_id)
    config = CrcConfig(CrcMode.CRC8, polynomial=0x07, initial_value=0xFF)
    event = CrcIrqEvent.LENGTH_ERROR
    crc_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        if not crc_enabled:
            return ()
        return (("CRC module disable", support.crc.disable),)

    with case_cleanup_scope(cleanup_actions):
        # Mask阶段配置：启用CRC Module并屏蔽LENGTH_ERROR Delivery。
        support.crc.enable()
        crc_enabled = True
        support.crc.configure(config)
        support.crc.irq_clear(CrcIrqEvent.ALL)
        support.crc.irq_enable(event)
        support.crc.irq_mask(event)
        baseline = support.crc.irq_snapshot_get()

        # Mask阶段刺激与观测：Force后只允许Raw置位。
        support.crc.irq_force(event)
        masked = support.crc.irq_snapshot_get()

        # Mask阶段证据：硬件Raw/Status与Service计数分开保存。
        record_property("masked_event_count_delta", masked.event_count - baseline.event_count)
        record_observation(
            record_property,
            key="masked_raw_status",
            value=bool(masked.raw & event),
            source="dut",
            endpoint="IRQ_RAW.LENGTH_ERROR",
        )
        record_observation(
            record_property,
            key="masked_effective_status",
            value=bool(masked.status & event),
            source="dut",
            endpoint="IRQ_STATUS.LENGTH_ERROR",
        )
        assert masked.raw == event
        assert masked.status == CrcIrqEvent.NONE
        assert masked.event_count == baseline.event_count

        # Unmask阶段：先清旧Pending，再Force一次新事件。
        support.crc.irq_clear(event)
        support.crc.irq_unmask(event)
        support.crc.irq_force(event)
        delivered = support.crc.irq_snapshot_get()

        # Unmask阶段证据：当前寄存器状态与ISR latch分别记录，不互相替代。
        record_property("unmasked_event_count_delta", delivered.event_count - baseline.event_count)
        record_observation(
            record_property,
            key="unmasked_raw_status",
            value=bool(delivered.raw & event),
            source="dut",
            endpoint="IRQ_RAW.LENGTH_ERROR",
        )
        record_observation(
            record_property,
            key="unmasked_effective_status",
            value=bool(delivered.status & event),
            source="dut",
            endpoint="IRQ_STATUS.LENGTH_ERROR",
        )
        record_observation(
            record_property,
            key="unmasked_isr_event",
            value=int(delivered.last_event),
            source="dut",
            endpoint="ISR.LATCHED.LENGTH_ERROR",
        )
        record_observation(
            record_property,
            key="unmasked_isr_last_raw",
            value=int(delivered.last_raw),
            source="dut",
            endpoint="ISR.LAST_RAW.LENGTH_ERROR",
        )

        # 断言：解除Mask后必须形成一次准确Delivery。
        assert delivered.event_count == baseline.event_count + 1
        assert delivered.last_event == event
        assert delivered.last_raw == event

    # 记录：保存 Mask 和 Unmask 两阶段证据。
    write_json_result(
        et_artifact_dir / "crc_p1_015_irq_mask_raw_status.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "crc_p1_015",
            "masked_raw": int(masked.raw),
            "masked_status": int(masked.status),
            "masked_event_count": masked.event_count,
            "delivered_raw": int(delivered.raw),
            "delivered_status": int(delivered.status),
            "delivered_event_count": delivered.event_count,
            "delivered_last_event": int(delivered.last_event),
            "delivered_last_raw": int(delivered.last_raw),
        },
    )


# 测试 Feature：
# CRC LENGTH_ERROR 的真实错误刺激与 IRQ Delivery。
#
# 测试方法：
# 1. 配置 CRC32，Enable/Unmask LENGTH_ERROR 并将 Length 设置为零。
# 2. 执行一次合法宽度 32-Bit 输入写入，读取 IRQ 回调证据。
# 3. 刺激前清除旧 Pending，并保存前后 Event Count、硬件Raw/Status与ISR latch。
#
# 通过条件：
# 1. Event Count 恰好增加一次。
# 2. ISR Last Event 和 Last Raw 仅包含 LENGTH_ERROR。
# 3. 当前硬件Raw/Status与Service ISR证据保持独立来源。
def test_crc_p1_016_length_error_irq(
    crc_support_for: CrcSupportFactory,
    crc_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：构造 CRC32 配置和目标错误源。
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
    event = CrcIrqEvent.LENGTH_ERROR
    crc_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        if not crc_enabled:
            return ()
        return (("CRC module disable", support.crc.disable),)

    with case_cleanup_scope(cleanup_actions):
        # 配置：启用CRC Module并建立LENGTH_ERROR IRQ会话。
        support.crc.enable()
        crc_enabled = True
        support.crc.configure(config)
        support.crc.irq_clear(CrcIrqEvent.ALL)
        support.crc.irq_enable(event)
        support.crc.irq_unmask(event)
        before = support.crc.irq_snapshot_get()

        # 刺激：设置Length=0后写入一个合法32-Bit输入。
        support.crc.data_length_set(0)
        support.crc.test_input_write(CrcInputAccessWidth.BITS_32, 0x12345678)

        # 观测：读取真实错误刺激后的IRQ快照。
        after = support.crc.irq_snapshot_get()

        # 证据：当前硬件寄存器和Service ISR/Event Count按来源分离。
        record_property("expected_irq_event", event.name)
        record_property("event_count_before", before.event_count)
        record_property("event_count_after", after.event_count)
        record_property("event_count_delta", after.event_count - before.event_count)
        record_observation(
            record_property,
            key="irq_raw_status",
            value=bool(after.raw & event),
            source="dut",
            endpoint="IRQ_RAW.LENGTH_ERROR",
        )
        record_observation(
            record_property,
            key="irq_status",
            value=bool(after.status & event),
            source="dut",
            endpoint="IRQ_STATUS.LENGTH_ERROR",
        )
        record_observation(
            record_property,
            key="isr_latched_event",
            value=int(after.last_event),
            source="dut",
            endpoint="ISR.LATCHED.LENGTH_ERROR",
        )
        record_observation(
            record_property,
            key="isr_last_raw",
            value=int(after.last_raw),
            source="dut",
            endpoint="ISR.LAST_RAW.LENGTH_ERROR",
        )

        # 断言：真实刺激只能产生 LENGTH_ERROR Delivery。
        assert after.event_count == before.event_count + 1
        assert after.last_event == event
        assert after.last_raw == event

    # 记录：保存真实错误刺激的 IRQ 证据。
    write_json_result(
        et_artifact_dir / "crc_p1_016_length_error_irq.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "crc_p1_016",
            "event_count_before": before.event_count,
            "event_count_after": after.event_count,
            "raw": int(after.raw),
            "status": int(after.status),
            "last_event": int(after.last_event),
            "last_raw": int(after.last_raw),
        },
    )


# 测试 Feature：
# CRC 非法输入访问宽度错误、错误源隔离和恢复。
#
# 测试方法：
# 1. CRC8配置下先对合法8-Bit写入采集前后IRQ快照，证明合法路径不产生BUS_ERROR。
# 2. 再执行一次32-Bit非法输入写入，用Event Count和ISR latch证明BUS_ERROR真实到达。
# 3. 退出并重新配置后执行正常CRC8计算，证明错误状态不会破坏后续链路。
#
# 通过条件：
# 1. 合法8-Bit写入前后BUS_ERROR Raw/Status均不置位且Event Count不增加。
# 2. 非法32-Bit写入恰好产生一次BUS_ERROR Delivery，ISR Last Event/Last Raw仅为BUS_ERROR。
# 3. 重新启用后的CRC8结果精确等于Golden且Remaining Input Count为0。
def test_crc_p1_018_bus_error_irq_recovery(
    crc_support_for: CrcSupportFactory,
    crc_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：选择稳定契约规定的 CRC8 + 32-Bit Access 错误组合。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CRC, instance=crc_instance_id)
    resource_driver.reset()

    support = crc_support_for(crc_instance_id)
    config = CrcConfig(
        mode=CrcMode.CRC8,
        polynomial=0x07,
        initial_value=0xFF,
        ref_in=True,
        ref_out=True,
    )
    event = CrcIrqEvent.BUS_ERROR
    crc_enabled = False
    resource_owned = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if crc_enabled:
            actions.append(("CRC module disable", support.crc.disable))
        if resource_owned:
            actions.append(("Resource pool reset", support.resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 第一轮配置：启用CRC Module并建立BUS_ERROR IRQ会话。
        support.crc.enable()
        crc_enabled = True
        support.crc.configure(config)
        support.crc.irq_clear(CrcIrqEvent.ALL)
        support.crc.irq_enable(event)
        support.crc.irq_unmask(event)

        # 合法基线：先采集起点，再执行一次合法8-Bit写入并重新读取快照。
        support.crc.data_length_set(1)
        legal_before = support.crc.irq_snapshot_get()
        support.crc.test_input_write(CrcInputAccessWidth.BITS_8, 0x12)
        legal_after = support.crc.irq_snapshot_get()
        record_property(
            "legal_event_count_delta",
            legal_after.event_count - legal_before.event_count,
        )
        record_observation(
            record_property,
            key="legal_bus_error_raw",
            value=bool(legal_after.raw & event),
            source="dut",
            endpoint="IRQ_RAW.BUS_ERROR",
        )
        record_observation(
            record_property,
            key="legal_bus_error_status",
            value=bool(legal_after.status & event),
            source="dut",
            endpoint="IRQ_STATUS.BUS_ERROR",
        )
        assert legal_after.event_count == legal_before.event_count
        assert legal_after.raw & event == CrcIrqEvent.NONE
        assert legal_after.status & event == CrcIrqEvent.NONE

        # 非法刺激：使用错误Access Width产生BUS_ERROR。
        support.crc.data_length_set(1)
        support.crc.test_input_write(CrcInputAccessWidth.BITS_32, 0x12345678)
        error_after = support.crc.irq_snapshot_get()

        # 错误证据：当前硬件Raw/Status、ISR latch与Service计数分别保存。
        record_property("expected_irq_event", event.name)
        record_property(
            "event_count_delta",
            error_after.event_count - legal_after.event_count,
        )
        record_observation(
            record_property,
            key="irq_raw_status",
            value=bool(error_after.raw & event),
            source="dut",
            endpoint="IRQ_RAW.BUS_ERROR",
        )
        record_observation(
            record_property,
            key="irq_status",
            value=bool(error_after.status & event),
            source="dut",
            endpoint="IRQ_STATUS.BUS_ERROR",
        )
        record_observation(
            record_property,
            key="isr_latched_event",
            value=int(error_after.last_event),
            source="dut",
            endpoint="ISR.LATCHED.BUS_ERROR",
        )
        record_observation(
            record_property,
            key="isr_last_raw",
            value=int(error_after.last_raw),
            source="dut",
            endpoint="ISR.LAST_RAW.BUS_ERROR",
        )
        assert error_after.event_count == legal_after.event_count + 1
        assert error_after.last_event == event
        assert error_after.last_raw == event

        # 生命周期：显式Disable错误轮，确保恢复轮重新进入Module。
        support.crc.disable()
        crc_enabled = False

        # 恢复准备：重置Resource池并写入正常CRC8 Payload。
        payload = bytes(range(1, 8))
        expected = calculate_crc_reference(config, payload)
        support.resource.reset()
        resource_owned = True
        source = support.resource.create(len(payload), alignment=4)
        support.resource.write(source, payload)

        # 恢复配置：重新Enable并写入CRC8配置。
        support.crc.enable()
        crc_enabled = True
        support.crc.configure(config)

        # 恢复刺激与证据：正常计算链路必须继续可用。
        recovery = support.crc.calculate(source.address, len(payload))
        record_property("recovery_expected_crc", expected)
        record_observation(
            record_property,
            key="recovery_actual_crc",
            value=recovery.result,
            source="dut",
            endpoint="RESULT.CRC",
        )
        record_observation(
            record_property,
            key="recovery_remaining_input_count",
            value=recovery.remaining_input_count,
            source="dut",
            endpoint="LENGTH.REMAINING_INPUT_COUNT",
        )
        assert recovery.result == expected
        assert recovery.remaining_input_count == 0

    # 记录：保存合法基线、错误Delivery和恢复计算三阶段证据。
    write_json_result(
        et_artifact_dir / "crc_p1_018_bus_error_irq_recovery.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "crc_p1_018",
            "legal_event_count_before": legal_before.event_count,
            "legal_event_count_after": legal_after.event_count,
            "error_event_count_after": error_after.event_count,
            "error_raw": int(error_after.raw),
            "error_status": int(error_after.status),
            "last_event": int(error_after.last_event),
            "last_raw": int(error_after.last_raw),
            "recovery_expected": expected,
            "recovery_actual": recovery.result,
            "recovery_remaining_input_count": recovery.remaining_input_count,
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
        },
    )
