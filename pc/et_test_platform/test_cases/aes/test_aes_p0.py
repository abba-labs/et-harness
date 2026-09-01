# AES P0 Formal Case。
#
# 职责：验证 AES 身份门禁、完整核心向量矩阵和模块生命周期。
# 边界：只通过 AES Support 提供的 AES/Resource Driver 访问设备，不访问 Wire 或寄存器。
# 依赖：AES Case Fixture、Cryptodome 独立 Golden 和 pytest。

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction
from ...core.errors import UnsupportedCapability
from ...drivers.aes import AesConfig, AesDirection, AesEndian, AesFeature, AesKeySize, AesMode
from ...drivers.aes.validation import expected_output_length
from ...drivers.crg import CrgPeripheral
from ...profiles.capabilities import ChipCapabilities
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import (
    require_aes_config_supported,
    require_aes_features_supported,
    require_aes_static_capability,
)
from .aes_helpers import record_result
from .aes_reference import aes_golden, nist_vectors

pytestmark = [pytest.mark.hardware, pytest.mark.ip("aes")]


# 测试 Feature：代表 AES 实例的静态映射与目标侧运行时能力门禁。
#
# 测试方法：
# 1. 先从芯片 Capability 验证代表实例和 semantic mapping，缺失时不访问目标。
# 2. 映射存在后通过 AES Support Factory 构造 Driver 并执行只读 CAPABILITIES_GET。
# 3. 对照运行时 API、Feature 和基础块尺寸，形成可追溯门禁证据。
#
# 通过条件：
# 1. 静态 semantic mapping 存在，否则明确 skip_by_chip_capability。
# 2. 目标侧 CAPABILITIES_GET 返回有效 API、非空 Feature 和 16-byte block size。
# 3. 本 Case 仅执行只读能力查询，不改变 AES 运算状态。
def test_aes_p0_001_static_capability_gate(
    target_capabilities: ChipCapabilities,
    aes_instance_id: int,
    aes_support_for,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
) -> None:

    # 静态门禁必须先于 Support 构造，语义映射缺失时不触发目标侧能力查询。
    # 只读 Case：仅核对静态/运行时能力，不执行 Feature 配置，无需前置复位。

    try:
        require_aes_static_capability(
            target_capabilities,
            instance_id=aes_instance_id,
            require_semantic=True,
        )
    except UnsupportedCapability as error:
        pytest.skip(f"skip_by_chip_capability: {error}")

    capability_gate_passed = require_aes_static_capability(
        target_capabilities,
        instance_id=aes_instance_id,
    )
    assert capability_gate_passed

    # 运行时只读观测：静态门禁通过后才构造 Support，Factory 内读取一次 CAPABILITIES_GET。
    support = aes_support_for(aes_instance_id)
    runtime = support.runtime
    record_property("expected_capability", "api_version>0, features!=0, block_size_bytes=16")
    record_observation(
        record_property,
        key="actual_capability",
        value=(
            f"api={runtime.api_version}, features=0x{int(runtime.features):08X}, "
            f"block={runtime.block_size_bytes}, length_bits={runtime.hardware_data_length_bits}"
        ),
        source="dut",
        endpoint="AES_CAPABILITIES",
    )

    # 单次 Snapshot：保留静态实例和运行时 Capability，不伪装成寄存器读回。
    record_result(
        et_artifact_dir,
        "aes_p0_001",
        instance_id=aes_instance_id,
        capability_gate_passed=bool(capability_gate_passed),
        runtime={
            "api_version": runtime.api_version,
            "features": int(runtime.features),
            "block_size_bytes": runtime.block_size_bytes,
            "hardware_data_length_bits": runtime.hardware_data_length_bits,
        },
    )
    assert runtime.api_version > 0
    assert int(runtime.features) != 0
    assert runtime.block_size_bytes == 16


# 测试 Feature：ECB/CBC/CTR × AES-128/256 × 加密/解密核心向量。
#
# 测试方法：
# 1. 参数化六种模式/密钥尺寸的固定 NIST 加密和解密向量。
# 2. 为每个向量创建独立 Resource，配置 AES、写入 Key/IV 并执行 PROCESS。
# 3. 读取 canonical 输出，与独立 Cryptodome Golden 和 produced 长度比较。
#
# 通过条件：
# 1. 每个向量的 actual bytes 精确等于 Golden bytes。
# 2. produced_bytes 精确等于 expected_output_length，不能只检查非空。
# 3. PROCESS 返回的 FINISH 状态为真，且没有伪造本地 PASS。
@pytest.mark.parametrize("vector", nist_vectors(), ids=lambda item: item[0])
def test_aes_p0_002_core_reference_matrix(
    aes_support,
    vector,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：解包一个独立向量，解密向量的 payload 是 ciphertext。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.AES, instance=aes_support.instance_id)
    resource_driver.reset()

    vector_id, key, payload, iv, config, expected = vector
    support = aes_support
    require_aes_config_supported(support, config)
    require_aes_features_supported(support, AesFeature.CPU_REGISTER_PATH)
    expected_length = expected_output_length(
        len(payload), config.mode, config.padding, config.direction
    )
    resource_ready = False
    aes_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if aes_enabled:
            actions.append(("AES module disable", support.aes.disable))
        if resource_ready:
            actions.append(("Resource pool reset", support.resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 资源：重置独占池，容量严格覆盖 expected output，避免 padding 截断。
        support.resource.reset()
        resource_ready = True
        source = support.resource.create(len(payload), alignment=4)
        destination = support.resource.create(expected_length, alignment=4)
        support.resource.write(source, payload)

        # 配置：显式启用 AES，并写入本向量的算法配置、Key 和可选 IV。
        support.aes.enable()
        aes_enabled = True
        support.aes.configure(config)
        support.aes.key_set(key, config.key_size)
        if iv is not None:
            support.aes.iv_set(iv)

        # 刺激：执行一次同步 PROCESS，并读取固件报告的有效输出长度。
        result = support.aes.process(
            source.handle,
            0,
            destination.handle,
            0,
            len(payload),
            destination_capacity=destination.size,
        )
        actual = support.resource.read(destination, result.produced_bytes)

        # 证据：独立 Golden、硬件结果端点和 FINISH 在决定性断言前进入 Canonical Result。
        record_property("expected_output", expected.hex())
        record_observation(
            record_property,
            key="actual_output",
            value=actual.hex(),
            source="dut",
            endpoint="RESULT_DOUT[0..3]",
        )
        record_observation(
            record_property,
            key="finish_status",
            value=result.status.finish,
            source="dut",
            endpoint="STATUS.FINISH",
        )

        # 记录：一次性保存向量、期望值、DUT输出、产生字节数和完成状态。
        record_result(
            et_artifact_dir,
            "aes_p0_002",
            vector_id=vector_id,
            expected=expected,
            actual=actual,
            produced_bytes=result.produced_bytes,
            finish=result.status.finish,
        )

        # 断言：保持 vector_id 可定位，并执行严格内容、长度和完成状态 Oracle。
        assert vector_id
        assert result.produced_bytes == expected_length == len(expected)
        assert actual == expected == aes_golden(payload, key, iv, config)
        assert result.status.finish


# 测试 Feature：AES enable、configure、process、disable 和重新启用生命周期。
#
# 测试方法：
# 1. 准备两个不同的 ECB 输入，分别在独立 Resource 中保存。
# 2. 每轮显式 enable、配置 Key、执行一次 PROCESS，再主动 disable。
# 3. 第一轮关闭后重新启用模块，验证第二轮不继承旧状态。
#
# 通过条件：
# 1. 两轮 actual 都精确等于对应独立 Golden。
# 2. 两轮 produced_bytes 和 FINISH 都准确，不能只验证调用未抛错。
# 3. 每轮结束由 AES-local cleanup 完成 disable，不依赖未文档化 disabled 行为。
def test_aes_p0_003_lifecycle_recovery(
    aes_support,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：两个 16-byte 输入避免 padding 语义干扰生命周期判断。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.AES, instance=aes_support.instance_id)
    resource_driver.reset()

    support = aes_support
    key = bytes.fromhex("2b7e151628aed2a6abf7158809cf4f3c")
    config = AesConfig(
        AesDirection.ENCRYPT,
        AesKeySize.AES128,
        AesMode.ECB,
        endian=AesEndian.BIG,
    )
    require_aes_config_supported(support, config)
    require_aes_features_supported(support, AesFeature.CPU_REGISTER_PATH)
    payloads = (
        bytes.fromhex("6bc1bee22e409f96e93d7e117393172a"),
        bytes(range(16)),
    )
    outputs: list[bytes] = []
    round_results: list[dict[str, object]] = []
    resource_ready = False
    aes_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if aes_enabled:
            actions.append(("AES module disable", support.aes.disable))
        if resource_ready:
            actions.append(("Resource pool reset", support.resource.reset))
        return tuple(actions)

    try:
        with case_cleanup_scope(cleanup_actions):
            # 资源：重置本 Case 独占资源池，输入和输出按轮次独立创建。
            support.resource.reset()
            resource_ready = True

            # 遍历：每轮显式建立并关闭 AES 生命周期，验证重新进入不继承旧状态。
            for payload in payloads:
                source = support.resource.create(len(payload), alignment=4)
                destination = support.resource.create(16, alignment=4)
                support.resource.write(source, payload)

                # 配置：当前轮重新启用模块，并重新下发完整配置和 Key。
                support.aes.enable()
                aes_enabled = True
                support.aes.configure(config)
                support.aes.key_set(key, config.key_size)

                # 刺激：处理当前输入并读取 canonical 输出。
                result = support.aes.process(
                    source.handle,
                    0,
                    destination.handle,
                    0,
                    len(payload),
                    destination_capacity=destination.size,
                )
                actual = support.resource.read(destination, result.produced_bytes)
                expected = aes_golden(payload, key, None, config)

                # 证据：每轮硬件输出与 FINISH 在单轮断言前进入 Canonical Result。
                outputs.append(actual)
                round_results.append(
                    {
                        "expected": expected,
                        "actual": actual,
                        "produced_bytes": result.produced_bytes,
                        "finish": result.status.finish,
                    }
                )
                record_property("round_expected_output", expected.hex())
                record_property("round_produced_bytes", result.produced_bytes)
                record_observation(
                    record_property,
                    key="round_actual_output",
                    value=actual.hex(),
                    source="dut",
                    endpoint="RESULT_DOUT[0..3]",
                )
                record_observation(
                    record_property,
                    key="round_finish_status",
                    value=result.status.finish,
                    source="dut",
                    endpoint="STATUS.FINISH",
                )

                # 断言：每轮在关闭模块前立即校验内容、长度和完成状态。
                assert actual == expected
                assert result.produced_bytes == len(expected)
                assert result.status.finish

                # 恢复：本轮成功结束后关闭 AES，下一轮从新生命周期开始。
                support.aes.disable()
                aes_enabled = False
    finally:
        # Evidence Closure：失败也保留已完成轮次，且同一路径只发布一次。
        record_result(
            et_artifact_dir,
            "aes_p0_003",
            rounds=round_results,
            output_count=len(outputs),
            outputs_distinct=(len(outputs) > 1 and outputs[0] != outputs[1]),
        )

    # 断言：两轮均完成且内容随当前 payload 变化，证明没有结果残留。
    assert len(outputs) == len(payloads)
    assert outputs[0] != outputs[1]
