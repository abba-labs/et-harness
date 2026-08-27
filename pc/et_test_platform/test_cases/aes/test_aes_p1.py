# AES P1 Formal Case。
#
# 职责：验证 AES padding、IV/counter、状态、错误和中断源语义。
# 边界：每个 Case 直接编排可见 stimulus/observe/assert，Driver 只负责 AES 单 IP 协议。
# 依赖：AES Support、AES Golden、Resource Driver 和 pytest。

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction
from ...drivers.aes import (
    AesConfig,
    AesDirection,
    AesEndian,
    AesFeature,
    AesIrqEvent,
    AesIrqTransferState,
    AesKeySize,
    AesMode,
    AesPadding,
)
from ...drivers.aes.validation import expected_output_length
from ...drivers.crg import CrgDriver, CrgPeripheral
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import (
    require_aes_config_supported,
    require_aes_data_length_bits,
    require_aes_features_supported,
    require_aes_irq_supported,
)
from .aes_helpers import record_result
from .aes_reference import aes_golden

pytestmark = [pytest.mark.hardware, pytest.mark.ip("aes")]

_KEY128 = bytes.fromhex("2b7e151628aed2a6abf7158809cf4f3c")
_PAYLOAD16 = bytes.fromhex("6bc1bee22e409f96e93d7e117393172a")
_IV_A = bytes.fromhex("f0f1f2f3f4f5f6f7f8f9fafb00000000")
_IV_B = bytes.fromhex("00112233445566778899aabbccddeeff")


# 测试 Feature：ECB/CBC 的 NONE、ZERO、PKCS7 padding 输出语义。
#
# 测试方法：
# 1. 参数化 ECB/CBC、三种 padding 和 15/16-byte 输入边界。
# 2. 配置 AES 并按 expected_output_length 创建目标 Resource 后执行 PROCESS。
# 3. 读取完整 ciphertext，与独立 Golden 和 produced length 同时比较。
#
# 通过条件：
# 1. 每个参数的输出内容精确等于 Golden。
# 2. NONE 只接受整块，ZERO/PKCS7 的输出容量分别覆盖补齐块和额外 PKCS7 块。
# 3. produced_bytes 精确等于 expected_output_length，不能用“不为空”替代。
@pytest.mark.parametrize(
    ("mode", "padding", "length"),
    (
        (AesMode.ECB, AesPadding.NONE, 16),
        (AesMode.ECB, AesPadding.ZERO, 15),
        (AesMode.ECB, AesPadding.ZERO, 16),
        (AesMode.ECB, AesPadding.PKCS7, 15),
        (AesMode.ECB, AesPadding.PKCS7, 16),
        (AesMode.CBC, AesPadding.NONE, 16),
        (AesMode.CBC, AesPadding.ZERO, 15),
        (AesMode.CBC, AesPadding.ZERO, 16),
        (AesMode.CBC, AesPadding.PKCS7, 15),
        (AesMode.CBC, AesPadding.PKCS7, 16),
    ),
)
def test_aes_p1_001_padding_output_contract(
    aes_support,
    mode: AesMode,
    padding: AesPadding,
    length: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：使用非对称的确定性 payload，避免零填充结果无法分辨。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.AES, instance=aes_support.instance_id)
    resource_driver.reset()

    support = aes_support
    payload = bytes(range(length))
    config = AesConfig(AesDirection.ENCRYPT, AesKeySize.AES128, mode, padding, AesEndian.BIG)
    require_aes_config_supported(support, config)
    require_aes_features_supported(support, AesFeature.CPU_REGISTER_PATH)
    iv = _IV_A if mode is AesMode.CBC else None
    expected = aes_golden(payload, _KEY128, iv, config)
    output_length = expected_output_length(length, mode, padding, config.direction)
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
        # 资源：重置独占池，并为完整 padding 输出分配准确容量。
        support.resource.reset()
        resource_ready = True
        source = support.resource.create(length, alignment=4)
        destination = support.resource.create(output_length, alignment=4)
        support.resource.write(source, payload)

        # 配置：显式启用 AES，并写入算法配置、Key 和可选 IV。
        support.aes.enable()
        aes_enabled = True
        support.aes.configure(config)
        support.aes.key_set(_KEY128, config.key_size)
        if iv is not None:
            support.aes.iv_set(iv)

        # 刺激：执行一次 PROCESS，并只读取硬件报告的有效输出范围。
        result = support.aes.process(
            source.handle,
            0,
            destination.handle,
            0,
            length,
            destination_capacity=destination.size,
        )
        actual = support.resource.read(destination, result.produced_bytes)
        record_property("expected_output", expected.hex())
        record_observation(
            record_property,
            key="actual_output",
            value=actual.hex(),
            source="dut",
            endpoint="RESULT_DOUT[0..3]",
        )

        # 记录：保存当前参数节点的配置、Golden、DUT输出和产生字节数。
        record_result(
            et_artifact_dir,
            "aes_p1_001",
            config={
                "mode": mode.name,
                "padding": padding.name,
                "length": length,
            },
            expected=expected,
            actual=actual,
            produced_bytes=result.produced_bytes,
        )

        # 断言：输出长度和内容均由当前参数节点的独立 Golden 决定。
        assert result.produced_bytes == output_length == len(expected)
        assert actual == expected


# 测试 Feature：CBC/CTR IV 配置、读回和计算语义。
#
# 测试方法：
# 1. 参数化 CBC/CTR 和两组不同 IV，逐次重配同一 Key 与 payload。
# 2. 写入 IV 后立即读回，再执行一个完整块 PROCESS。
# 3. 保存每个 IV 对应的 output，并用 Golden 验证实际字节。
#
# 通过条件：
# 1. 每次 iv_get 精确等于刚写入的 16-byte IV。
# 2. 每次 ciphertext 精确等于对应 mode/IV Golden。
# 3. 两个不同 IV 的 ciphertext 不相同，证明 IV 未被旧配置覆盖。
@pytest.mark.parametrize("mode", (AesMode.CBC, AesMode.CTR))
def test_aes_p1_002_iv_readback_and_ciphertext(
    aes_support,
    mode: AesMode,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：固定 key/payload，仅改变 IV 和 mode。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.AES, instance=aes_support.instance_id)
    resource_driver.reset()

    support = aes_support
    config = AesConfig(AesDirection.ENCRYPT, AesKeySize.AES128, mode, endian=AesEndian.BIG)
    require_aes_config_supported(support, config)
    require_aes_features_supported(support, AesFeature.CPU_REGISTER_PATH)
    outputs: list[bytes] = []
    iv_results: list[dict[str, object]] = []
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
            # 资源：重置独占池；每个 IV 使用独立输入和输出 Resource。
            support.resource.reset()
            resource_ready = True

            # 生命周期：显式启用 AES，循环内每个 IV 都重新配置以避免延续链值。
            support.aes.enable()
            aes_enabled = True

            # 遍历：逐个刺激并观察 IV_A/IV_B 两个独立节点。
            for iv in (_IV_A, _IV_B):
                source = support.resource.create(16, alignment=4)
                destination = support.resource.create(16, alignment=4)
                support.resource.write(source, _PAYLOAD16)
                support.aes.configure(config)
                support.aes.key_set(_KEY128, config.key_size)
                support.aes.iv_set(iv)

                # 观测：IV 读回先进入 Canonical Observation，再做即时断言。
                iv_readback = support.aes.iv_get()
                record_property("expected_value", iv.hex())
                record_observation(
                    record_property,
                    key="actual_value",
                    value=iv_readback.hex(),
                    source="dut",
                    endpoint="IV[0..3]",
                )
                assert iv_readback == iv

                # 刺激：对当前 IV 执行一个完整块，并读取 canonical 输出。
                result = support.aes.process(
                    source.handle,
                    0,
                    destination.handle,
                    0,
                    16,
                    destination_capacity=destination.size,
                )
                actual = support.resource.read(destination, result.produced_bytes)
                expected = aes_golden(_PAYLOAD16, _KEY128, iv, config)
                record_property("expected_output", expected.hex())
                record_observation(
                    record_property,
                    key="actual_output",
                    value=actual.hex(),
                    source="dut",
                    endpoint="RESULT_DOUT[0..3]",
                )

                # 记录：在内存中累计当前 IV、回读、Golden、DUT输出和真实产生字节数。
                iv_results.append(
                    {
                        "iv": iv,
                        "iv_readback": iv_readback,
                        "expected": expected,
                        "actual": actual,
                        "produced_bytes": result.produced_bytes,
                    }
                )

                # 断言：每个 IV 节点立即与其独立 Golden 对照。
                assert result.produced_bytes == 16
                assert actual == expected
                outputs.append(actual)

                # 恢复：每个 IV 节点结束后关闭模块，下一节点重新建立独立生命周期。
                support.aes.disable()
                aes_enabled = False
                if iv != _IV_B:
                    support.aes.enable()
                    aes_enabled = True
    finally:
        # Evidence Closure：无论中途 PASS/FAIL，都只发布一次当前已形成的 IV Snapshot。
        record_result(
            et_artifact_dir,
            "aes_p1_002",
            mode=mode.name,
            iv_results=iv_results,
            outputs_distinct=(len(outputs) > 1 and outputs[0] != outputs[1]),
        )

    # 断言：IV 改变必须改变这组判别输入的 ciphertext。
    assert len(outputs) == 2 and outputs[0] != outputs[1]


# 测试 Feature：36-bit DATA_LENGTH 与两块运算后的 BUSY/FINISH 生命周期。
#
# 测试方法：
# 1. 写入包含 bit32 的 data length 并读回，确认高位没有被截断。
# 2. 准备 32-byte payload，执行两个完整块的 Resource-backed PROCESS。
# 3. PROCESS 返回后读取 status 和完整 output，保存 busy/finish 事实。
#
# 通过条件：
# 1. 36-bit length readback 精确等于写入值。
# 2. 两块输出精确等于 Golden，produced_bytes 为 32。
# 3. 完成后 busy=False、finish=True，不用固定 sleep 猜测终态。
def test_aes_p1_003_length_and_busy(
    aes_support,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：先验证高位长度字段，再构造两个完整 AES block。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.AES, instance=aes_support.instance_id)
    resource_driver.reset()

    support = aes_support
    high_length = 1 << 32
    payload = _PAYLOAD16 + bytes(range(16))
    config = AesConfig(AesDirection.ENCRYPT, AesKeySize.AES128, AesMode.ECB, endian=AesEndian.BIG)
    require_aes_config_supported(support, config)
    require_aes_features_supported(support, AesFeature.CPU_REGISTER_PATH | AesFeature.STATUS)
    require_aes_data_length_bits(support, 33)
    expected = aes_golden(payload, _KEY128, None, config)
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
        # 长度字段：在独立模块生命周期内写入 bit32，并立即读取硬件值。
        support.aes.enable()
        aes_enabled = True
        support.aes.data_length_set(high_length)
        data_length_readback = support.aes.data_length_get()

        # 记录与断言：高位读回先进入 Canonical Observation，避免后续阶段覆盖。
        record_property("expected_value", high_length)
        record_observation(
            record_property,
            key="actual_value",
            value=data_length_readback,
            source="dut",
            endpoint="DATA_LENGTH[1:0]",
        )
        assert data_length_readback == high_length

        # 恢复：结束长度字段子阶段，第二阶段重新建立 AES 生命周期。
        support.aes.disable()
        aes_enabled = False

        # 资源：重置独占池，并为两个完整块创建输入和输出 Buffer。
        support.resource.reset()
        resource_ready = True
        source = support.resource.create(len(payload), alignment=4)
        destination = support.resource.create(len(expected), alignment=4)
        support.resource.write(source, payload)

        # 配置：重新启用 AES，并下发 ECB 配置与 Key。
        support.aes.enable()
        aes_enabled = True
        support.aes.configure(config)
        support.aes.key_set(_KEY128, config.key_size)

        # 刺激：处理两个完整块并读取真实输出及最终状态。
        result = support.aes.process(
            source.handle,
            0,
            destination.handle,
            0,
            len(payload),
            destination_capacity=destination.size,
        )
        actual = support.resource.read(destination, result.produced_bytes)
        status = support.aes.status_get()
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
            key="busy_final",
            value=status.busy,
            source="dut",
            endpoint="STATUS.BUSY",
        )
        record_observation(
            record_property,
            key="finish_final",
            value=status.finish,
            source="dut",
            endpoint="STATUS.FINISH",
        )

        # 记录：单次发布高位读回、Golden、DUT输出和 BUSY/FINISH 终态。
        record_result(
            et_artifact_dir,
            "aes_p1_003",
            configured_length=high_length,
            data_length_readback=data_length_readback,
            expected=expected,
            actual=actual,
            status={
                "busy": status.busy,
                "finish": status.finish,
                "produced_bytes": result.produced_bytes,
            },
        )

        # 断言：只接受硬件返回的终态和完整结果。
        assert actual == expected
        assert result.produced_bytes == len(expected) == len(payload)
        assert not status.busy
        assert status.finish


# 测试 Feature：LITTLE/BIG 32-bit word packing 的 AES canonical 输出语义。
#
# 测试方法：
# 1. 参数化两个 endian，使用 byte-distinguishing key 和 plaintext。
# 2. 配置同一 AES-ECB 流程并执行一个完整 block。
# 3. 读取 Driver 返回的 canonical bytes，与同一个独立 AES Golden 比较。
#
# 通过条件：
# 1. LITTLE 和 BIG 的 actual 都精确等于同一个 canonical Golden。
# 2. produced_bytes 恒为 16，不能由 Resource 尾部数据补足。
# 3. 两个 endian 节点独立配置，不能复用上一次硬件状态。
@pytest.mark.parametrize("endian", (AesEndian.LITTLE, AesEndian.BIG))
def test_aes_p1_004_endian_packing(
    aes_support,
    endian: AesEndian,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：输入每个 32-bit word 均不同，能暴露 word byte order 错误。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.AES, instance=aes_support.instance_id)
    resource_driver.reset()

    support = aes_support
    payload = bytes.fromhex("00112233445566778899aabbccddeeff")
    config = AesConfig(AesDirection.ENCRYPT, AesKeySize.AES128, AesMode.ECB, endian=endian)
    require_aes_config_supported(support, config)
    require_aes_features_supported(support, AesFeature.CPU_REGISTER_PATH)
    expected = aes_golden(payload, _KEY128, None, config)
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
        # 资源：重置独占池，并创建一个完整块的输入和输出 Buffer。
        support.resource.reset()
        resource_ready = True
        source = support.resource.create(16, alignment=4)
        destination = support.resource.create(16, alignment=4)
        support.resource.write(source, payload)

        # 配置：当前 endian 节点独立启用并配置 AES，避免继承前一节点状态。
        support.aes.enable()
        aes_enabled = True
        support.aes.configure(config)
        support.aes.key_set(_KEY128, config.key_size)

        # 刺激：执行一个完整块并读取 canonical logical bytes。
        result = support.aes.process(
            source.handle,
            0,
            destination.handle,
            0,
            16,
            destination_capacity=destination.size,
        )
        actual = support.resource.read(destination, result.produced_bytes)
        record_property("expected_output", expected.hex())
        record_observation(
            record_property,
            key="actual_output",
            value=actual.hex(),
            source="dut",
            endpoint="RESULT_DOUT[0..3]",
        )

        # 记录：保存 endian、独立 Golden、DUT输出和产生字节数。
        record_result(
            et_artifact_dir,
            "aes_p1_004",
            endian=endian.name,
            expected=expected,
            actual=actual,
            produced_bytes=result.produced_bytes,
        )

        # 断言：Driver 只返回 canonical logical bytes，不暴露 raw words。
        assert result.produced_bytes == 16
        assert actual == expected


# 测试 Feature：CTR BLOCK_CNT 初始 counter 语义。
#
# 测试方法：
# 1. 参数化历史 counter=0xfcfdfeff 与另一个确定值。
# 2. 每组重新配置 CTR、Key、WORK_IV，并执行相同 payload。
# 3. 使用显式 IV 最后 word 为零的 Golden 计算 expected。
#
# 通过条件：
# 1. 每组 ciphertext 精确等于其 counter Golden。
# 2. 两个 counter 的输出精确不同，证明 BLOCK_CNT 被实际采用。
# 3. 输出长度为一个 block 且状态 FINISH 为真。
@pytest.mark.parametrize("counter", (0xFCFDFEFF, 0xFCFDFF00))
def test_aes_p1_005_ctr_counter(
    aes_support,
    counter: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：固定 key/IV/payload，只改变单独的 32-bit counter。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.AES, instance=aes_support.instance_id)
    resource_driver.reset()

    support = aes_support
    config = AesConfig(
        AesDirection.ENCRYPT,
        AesKeySize.AES128,
        AesMode.CTR,
        endian=AesEndian.BIG,
        ctr_counter=counter,
    )
    require_aes_config_supported(support, config)
    require_aes_features_supported(support, AesFeature.CPU_REGISTER_PATH)
    expected = aes_golden(_PAYLOAD16, _KEY128, _IV_A, config)
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
        # 资源：重置独占池，并创建固定输入和一个块的输出 Buffer。
        support.resource.reset()
        resource_ready = True
        source = support.resource.create(16, alignment=4)
        destination = support.resource.create(16, alignment=4)
        support.resource.write(source, _PAYLOAD16)

        # 配置：显式启用并写入当前 counter、Key 和 IV。
        support.aes.enable()
        aes_enabled = True
        support.aes.configure(config)
        support.aes.key_set(_KEY128, config.key_size)
        support.aes.iv_set(_IV_A)

        # 刺激：执行一个 CTR block，并读取真实产生范围。
        result = support.aes.process(
            source.handle,
            0,
            destination.handle,
            0,
            16,
            destination_capacity=destination.size,
        )
        actual = support.resource.read(destination, result.produced_bytes)
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

        # 记录：保存 counter、独立 Golden、DUT输出和完成状态。
        record_result(
            et_artifact_dir,
            "aes_p1_005",
            counter=counter,
            expected=expected,
            actual=actual,
            status={
                "produced_bytes": result.produced_bytes,
                "finish": result.status.finish,
            },
        )

        # 断言：counter 参与独立 Golden，禁止只做 round-trip。
        assert actual == expected
        assert result.produced_bytes == 16
        assert result.status.finish


# 测试 Feature：非 DMA Data-In Request 与 W1C 清除。
#
# 测试方法：
# 1. 配置 AES-ECB 和 Key，在输入请求阶段读取 DIN_REQ。
# 2. 通过 BLOCK_WRITE 写入一个完整块，再读取状态确认请求被消费。
# 3. 对 DIN_REQ 执行 status W1C，并读取清除后的状态。
#
# 通过条件：
# 1. 写入前 DIN_REQ 精确为 True。
# 2. 写入后 DIN_REQ 精确为 False，且没有用 bool 类型检查替代状态断言。
# 3. W1C 后 DIN_REQ 仍为 False，目标 bit 没有残留。
def test_aes_p1_006_data_in_request_status(
    aes_support,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：配置输入路径但不提前写入 block。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.AES, instance=aes_support.instance_id)
    resource_driver.reset()

    support = aes_support
    config = AesConfig(AesDirection.ENCRYPT, AesKeySize.AES128, AesMode.ECB, endian=AesEndian.BIG)
    require_aes_config_supported(support, config)
    require_aes_features_supported(support, AesFeature.CPU_REGISTER_PATH | AesFeature.STATUS)
    aes_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if aes_enabled:
            actions.append(("AES status clear", lambda: support.aes.status_clear(0x07)))
            actions.append(("AES module disable", support.aes.disable))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 配置：显式启用 AES，再下发 ECB 配置和 Key。
        support.aes.enable()
        aes_enabled = True
        support.aes.configure(config)
        support.aes.key_set(_KEY128, config.key_size)

        # 观测：输入前先读取 Data-In Request，确认硬件正在请求数据。
        before = support.aes.status_get()
        record_property("expected_value", True)
        record_observation(
            record_property,
            key="actual_value",
            value=before.data_in_request,
            source="dut",
            endpoint="STATUS.DIN_REQ",
        )
        assert before.data_in_request

        # 刺激：BLOCK_WRITE 是实际 CPU input stimulus，再读取请求消费后的状态。
        support.aes.block_write(_PAYLOAD16)
        after_write = support.aes.status_get()
        record_observation(
            record_property,
            key="din_req_after_write",
            value=after_write.data_in_request,
            source="dut",
            endpoint="STATUS.DIN_REQ",
        )
        assert not after_write.data_in_request

        # 恢复：清除 DIN status bit 后重新取样，确认目标位无残留。
        support.aes.status_clear(0x02)
        after_clear = support.aes.status_get()
        record_observation(
            record_property,
            key="din_req_after_clear",
            value=after_clear.data_in_request,
            source="dut",
            endpoint="STATUS.DIN_REQ",
        )
        record_result(
            et_artifact_dir,
            "aes_p1_006",
            status={
                "before": before.data_in_request,
                "after_write": after_write.data_in_request,
                "after_clear": after_clear.data_in_request,
            },
        )
        assert not after_clear.data_in_request


# 测试 Feature：非 DMA Data-Out Request、BLOCK_READ 和 W1C 清除。
#
# 测试方法：
# 1. 配置 AES-ECB、Key，写入一个完整输入 block。
# 2. 在结果可读阶段读取 DOUT_REQ，再通过 BLOCK_READ 取出结果。
# 3. 对 DOUT_REQ 执行 W1C，并重新读取状态。
#
# 通过条件：
# 1. BLOCK_READ 前 DOUT_REQ 精确为 True。
# 2. 读出的 block 精确等于 AES Golden。
# 3. 读出并 W1C 后 DOUT_REQ 精确为 False。
def test_aes_p1_007_data_out_request_status(
    aes_support,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：配置 ECB 并写入一块输入，触发结果请求阶段。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.AES, instance=aes_support.instance_id)
    resource_driver.reset()

    support = aes_support
    config = AesConfig(AesDirection.ENCRYPT, AesKeySize.AES128, AesMode.ECB, endian=AesEndian.BIG)
    require_aes_config_supported(support, config)
    require_aes_features_supported(support, AesFeature.CPU_REGISTER_PATH | AesFeature.STATUS)
    expected = aes_golden(_PAYLOAD16, _KEY128, None, config)
    aes_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if aes_enabled:
            actions.append(("AES status clear", lambda: support.aes.status_clear(0x07)))
            actions.append(("AES module disable", support.aes.disable))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 配置：显式启用 AES，写入 ECB 配置和 Key。
        support.aes.enable()
        aes_enabled = True
        support.aes.configure(config)
        support.aes.key_set(_KEY128, config.key_size)

        # 刺激：写入一个完整 block，使结果进入 Data-Out 请求阶段。
        support.aes.block_write(_PAYLOAD16)
        before_read = support.aes.status_get()
        record_property("expected_value", expected.hex())
        record_observation(
            record_property,
            key="dout_req_before_read",
            value=before_read.data_out_request,
            source="dut",
            endpoint="STATUS.DOUT_REQ",
        )
        assert before_read.data_out_request

        # 观测：结果请求为真时读取唯一结果 block。
        actual = support.aes.block_read()
        record_observation(
            record_property,
            key="actual_value",
            value=actual.hex(),
            source="dut",
            endpoint="RESULT_DOUT[0..3]",
        )
        assert actual == expected

        # 恢复：读取后清除 DOUT 状态并检查目标 bit。
        after_read = support.aes.status_get()
        record_observation(
            record_property,
            key="dout_req_after_read",
            value=after_read.data_out_request,
            source="dut",
            endpoint="STATUS.DOUT_REQ",
        )
        assert not after_read.data_out_request
        support.aes.status_clear(0x04)
        after_clear = support.aes.status_get()
        record_observation(
            record_property,
            key="dout_req_after_clear",
            value=after_clear.data_out_request,
            source="dut",
            endpoint="STATUS.DOUT_REQ",
        )
        record_result(
            et_artifact_dir,
            "aes_p1_007",
            expected=expected,
            actual=actual,
            status={
                "before_read": before_read.data_out_request,
                "after_read": after_read.data_out_request,
                "after_clear": after_clear.data_out_request,
            },
        )
        assert not after_clear.data_out_request


# 测试 Feature：完整 PROCESS 的 FINISH 状态和 W1C 清除。
#
# 测试方法：
# 1. 配置 ECB、Key 和一个完整 block Resource。
# 2. 执行 PROCESS 并先保存 output，再读取 FINISH 状态。
# 3. 对 FINISH 执行 W1C 后重新读取状态。
#
# 通过条件：
# 1. PROCESS output 精确等于 Golden，FINISH 精确为 True。
# 2. W1C 后 FINISH 精确为 False。
# 3. 清状态不改变已经读取的 output 事实。
def test_aes_p1_008_finish_status_clear(
    aes_support,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：准备完整输入和严格容量的输出 Resource。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.AES, instance=aes_support.instance_id)
    resource_driver.reset()

    support = aes_support
    config = AesConfig(AesDirection.ENCRYPT, AesKeySize.AES128, AesMode.ECB, endian=AesEndian.BIG)
    require_aes_config_supported(support, config)
    require_aes_features_supported(support, AesFeature.CPU_REGISTER_PATH | AesFeature.STATUS)
    expected = aes_golden(_PAYLOAD16, _KEY128, None, config)
    resource_ready = False
    aes_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if aes_enabled:
            actions.append(("AES status clear", lambda: support.aes.status_clear(0x07)))
            actions.append(("AES module disable", support.aes.disable))
        if resource_ready:
            actions.append(("Resource pool reset", support.resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 资源：重置独占池，并创建严格一块容量的输入和输出 Buffer。
        support.resource.reset()
        resource_ready = True
        source = support.resource.create(16, alignment=4)
        destination = support.resource.create(16, alignment=4)
        support.resource.write(source, _PAYLOAD16)

        # 配置：显式启用 AES，写入 ECB 配置和 Key。
        support.aes.enable()
        aes_enabled = True
        support.aes.configure(config)
        support.aes.key_set(_KEY128, config.key_size)

        # 刺激：执行完整 PROCESS 后先读取结果，再取 FINISH。
        result = support.aes.process(
            source.handle,
            0,
            destination.handle,
            0,
            16,
            destination_capacity=destination.size,
        )
        actual = support.resource.read(destination, result.produced_bytes)
        before_clear = support.aes.status_get()
        record_property("expected_state", "FINISH=1 and output matches Golden")
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
            key="actual_state",
            value=before_clear.finish,
            source="dut",
            endpoint="STATUS.FINISH",
        )
        assert actual == expected
        assert before_clear.finish

        # 恢复：W1C 清除 FINISH，并确认目标状态位精确归零。
        support.aes.status_clear(0x01)
        after_clear = support.aes.status_get()
        record_observation(
            record_property,
            key="finish_after_clear",
            value=after_clear.finish,
            source="dut",
            endpoint="STATUS.FINISH",
        )
        record_result(
            et_artifact_dir,
            "aes_p1_008",
            expected=expected,
            actual=actual,
            produced_bytes=result.produced_bytes,
            finish_before=before_clear.finish,
            finish_after=after_clear.finish,
        )
        assert not after_clear.finish


# 测试 Feature：OUTPUT_CONFLICT 错误 IRQ 与恢复。
#
# 测试方法：
# 1. 清除旧事件，配置 ECB 并开启 OUTPUT_CONFLICT source。
# 2. 连续写入两个 block 而不读取第一块结果，直接取 IRQ snapshot。
# 3. 清除目标事件后恢复正常 PROCESS 并验证 Golden。
#
# 通过条件：
# 1. ISR 清除硬件 raw/status 后，Service latched 精确记录 OUTPUT_CONFLICT。
# 2. event_count 相比清除前精确增加 1。
# 3. 清除事件后恢复 PROCESS 精确成功，证明错误状态可恢复。
def test_aes_p1_009_output_conflict_error(
    aes_support,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：建立错误刺激所需的 ECB CPU block 路径。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.AES, instance=aes_support.instance_id)
    resource_driver.reset()

    support = aes_support
    event = AesIrqEvent.OUTPUT_CONFLICT
    config = AesConfig(AesDirection.ENCRYPT, AesKeySize.AES128, AesMode.ECB, endian=AesEndian.BIG)
    require_aes_config_supported(support, config)
    require_aes_features_supported(
        support, AesFeature.CPU_REGISTER_PATH | AesFeature.TEST_EXTENSIONS
    )
    require_aes_irq_supported(support, event)
    aes_enabled = False
    irq_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if irq_enabled:
            actions.append(("AES IRQ disable", lambda: support.aes.irq_disable(event)))
            actions.append(("AES IRQ clear", lambda: support.aes.irq_clear(event)))
        if aes_enabled:
            actions.append(("AES module disable", support.aes.disable))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 配置：显式启用 AES，清除旧事件并开启目标错误源。
        support.aes.enable()
        aes_enabled = True
        support.aes.irq_clear(AesIrqEvent.ALL)
        support.aes.data_length_set(32)
        support.aes.configure(config)
        support.aes.key_set(_KEY128, config.key_size)
        support.aes.irq_enable(event)
        irq_enabled = True
        support.aes.irq_unmask(event)
        baseline = support.aes.irq_snapshot_get()
        record_property("irq_event_count_before", baseline.event_count)

        # 执行：第二次输入在第一块 DOUT 未读取时制造冲突。
        support.aes.block_write_pair_direct(_PAYLOAD16, bytes(range(16)))
        snapshot = support.aes.irq_snapshot_get()

        # 恢复：先清除目标事件并采集恢复事实，随后一次性发布完整 Snapshot。
        support.aes.irq_clear(event)
        cleared = support.aes.irq_snapshot_get()
        record_property("expected_state", "OUTPUT_CONFLICT latched")
        record_property("irq_event_count_after", snapshot.event_count)
        record_property("irq_event_count_delta", snapshot.event_count - baseline.event_count)
        record_observation(
            record_property,
            key="actual_state",
            value=int(snapshot.latched),
            source="dut",
            endpoint="ISR.LATCHED.OUTPUT_CONFLICT",
        )
        record_observation(
            record_property,
            key="irq_raw_after_isr",
            value=int(snapshot.raw),
            source="dut",
            endpoint="IRQ_RAW.OUTPUT_CONFLICT",
        )
        record_observation(
            record_property,
            key="irq_status_after_isr",
            value=int(snapshot.status),
            source="dut",
            endpoint="IRQ_STATUS.OUTPUT_CONFLICT",
        )
        record_observation(
            record_property,
            key="cleared_irq_raw",
            value=int(cleared.raw),
            source="dut",
            endpoint="IRQ_RAW.OUTPUT_CONFLICT",
        )
        record_result(
            et_artifact_dir,
            "aes_p1_009",
            event=event.name,
            baseline_event_count=baseline.event_count,
            snapshot={
                "raw": int(snapshot.raw),
                "status": int(snapshot.status),
                "latched": int(snapshot.latched),
                "event_count": snapshot.event_count,
            },
            cleared={
                "raw": int(cleared.raw),
                "status": int(cleared.status),
                "latched": int(cleared.latched),
            },
            recovery={"cleared_raw": int(cleared.raw), "recovered": not (cleared.raw & event)},
        )

        # 断言：目标错误位、事件计数和清除结果必须提供精确证据。
        assert snapshot.raw == AesIrqEvent(0)
        assert snapshot.status == AesIrqEvent(0)
        assert snapshot.latched == event
        assert snapshot.event_count == baseline.event_count + 1
        assert not (cleared.raw & event)


# 测试 Feature：KEY_MISSING 错误 IRQ。
#
# 测试方法：
# 1. 清除旧事件并只配置 AES mode，不写入 Key。
# 2. 通过一个完整 Resource PROCESS 触发缺失 Key 的硬件错误路径。
# 3. 读取 snapshot，清除 KEY_MISSING 并验证目标位消失。
#
# 通过条件：
# 1. PROCESS 被硬件拒绝或返回错误，不能在缺 Key 时产生成功 output。
# 2. ISR 清除硬件 raw/status 后，Service latched 精确记录 KEY_MISSING。
# 3. clear 后 KEY_MISSING 的三个视图均为零，event_count 不被伪造增加。
def test_aes_p1_010_key_missing_error(
    aes_support,
    crg_driver: CrgDriver,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    resource_driver,
) -> None:

    # 准备：配置 module/mode，但故意省略 key_set。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.AES, instance=aes_support.instance_id)
    resource_driver.reset()

    support = aes_support
    event = AesIrqEvent.KEY_MISSING
    config = AesConfig(AesDirection.ENCRYPT, AesKeySize.AES128, AesMode.ECB, endian=AesEndian.BIG)
    require_aes_config_supported(support, config)
    require_aes_features_supported(
        support, AesFeature.CPU_REGISTER_PATH | AesFeature.TEST_EXTENSIONS
    )
    require_aes_irq_supported(support, event)
    aes_enabled = False
    irq_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if irq_enabled:
            actions.append(("AES IRQ disable", lambda: support.aes.irq_disable(event)))
            actions.append(("AES IRQ clear", lambda: support.aes.irq_clear(event)))
        if aes_enabled:
            actions.append(("AES module disable", support.aes.disable))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 隔离：复位当前逻辑 AES 实例，避免继承前序 Case 写入的 Key。
        crg_driver.reset(CrgPeripheral.AES, instance=support.instance_id)

        # 配置：显式启用 AES，只配置 mode，故意不调用 key_set。
        support.aes.enable()
        aes_enabled = True
        support.aes.irq_clear(AesIrqEvent.ALL)
        support.aes.data_length_set(16)
        support.aes.configure(config)
        support.aes.irq_enable(event)
        irq_enabled = True
        support.aes.irq_unmask(event)
        baseline = support.aes.irq_snapshot_get()
        record_property("irq_event_count_before", baseline.event_count)

        # 执行：写入一个完整块，直接触发缺失 Key 的硬件检查路径。
        support.aes.block_write_direct(_PAYLOAD16)
        snapshot = support.aes.irq_snapshot_get()
        record_property("expected_state", "KEY_MISSING latched")
        record_property("irq_event_count_after", snapshot.event_count)
        record_property("irq_event_count_delta", snapshot.event_count - baseline.event_count)
        record_observation(
            record_property,
            key="actual_state",
            value=int(snapshot.latched),
            source="dut",
            endpoint="ISR.LATCHED.KEY_MISSING",
        )
        record_observation(
            record_property,
            key="irq_raw_after_isr",
            value=int(snapshot.raw),
            source="dut",
            endpoint="IRQ_RAW.KEY_MISSING",
        )
        record_observation(
            record_property,
            key="irq_status_after_isr",
            value=int(snapshot.status),
            source="dut",
            endpoint="IRQ_STATUS.KEY_MISSING",
        )

        # 断言：只接受目标错误位的精确硬件快照。
        assert snapshot.raw == AesIrqEvent(0)
        assert snapshot.status == AesIrqEvent(0)
        assert snapshot.latched == event
        assert snapshot.event_count == baseline.event_count + 1
        support.aes.irq_clear(event)
        cleared = support.aes.irq_snapshot_get()
        record_observation(
            record_property,
            key="cleared_irq_raw",
            value=int(cleared.raw),
            source="dut",
            endpoint="IRQ_RAW.KEY_MISSING",
        )
        record_observation(
            record_property,
            key="cleared_irq_status",
            value=int(cleared.status),
            source="dut",
            endpoint="IRQ_STATUS.KEY_MISSING",
        )
        record_observation(
            record_property,
            key="cleared_irq_latched",
            value=int(cleared.latched),
            source="dut",
            endpoint="ISR.LATCHED.KEY_MISSING",
        )
        record_result(
            et_artifact_dir,
            "aes_p1_010",
            event=event.name,
            baseline_event_count=baseline.event_count,
            snapshot={
                "raw": int(snapshot.raw),
                "status": int(snapshot.status),
                "latched": int(snapshot.latched),
                "event_count": snapshot.event_count,
            },
            cleared={
                "raw": int(cleared.raw),
                "status": int(cleared.status),
                "latched": int(cleared.latched),
                "event_count": cleared.event_count,
            },
        )
        assert not (cleared.raw & event)
        assert not (cleared.status & event)
        assert not (cleared.latched & event)


# 测试 Feature：CBC IV_MISSING 错误 IRQ。
#
# 测试方法：
# 1. 清除旧事件并配置 CBC/Key，但故意不写入 IV。
# 2. 通过完整 Resource PROCESS 触发缺失 IV 的错误路径。
# 3. 读取并清除 IV_MISSING snapshot，确认错误状态恢复为空。
#
# 通过条件：
# 1. 缺失 IV 的 PROCESS 被拒绝，不能伪造成功结果。
# 2. ISR 清除硬件 raw/status 后，Service latched 精确记录 IV_MISSING。
# 3. clear 后目标 bit 在三个视图均为零。
def test_aes_p1_011_iv_missing_error(
    aes_support,
    crg_driver: CrgDriver,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    resource_driver,
) -> None:

    # 准备：CBC 必须配置 Key，但刻意不调用 iv_set。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.AES, instance=aes_support.instance_id)
    resource_driver.reset()

    support = aes_support
    event = AesIrqEvent.IV_MISSING
    config = AesConfig(AesDirection.ENCRYPT, AesKeySize.AES128, AesMode.CBC, endian=AesEndian.BIG)
    require_aes_config_supported(support, config)
    require_aes_features_supported(
        support, AesFeature.CPU_REGISTER_PATH | AesFeature.TEST_EXTENSIONS
    )
    require_aes_irq_supported(support, event)
    aes_enabled = False
    irq_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if irq_enabled:
            actions.append(("AES IRQ disable", lambda: support.aes.irq_disable(event)))
            actions.append(("AES IRQ clear", lambda: support.aes.irq_clear(event)))
        if aes_enabled:
            actions.append(("AES module disable", support.aes.disable))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 隔离：复位当前逻辑 AES 实例，避免继承前序 Case 写入的 IV。
        crg_driver.reset(CrgPeripheral.AES, instance=support.instance_id)

        # 配置：显式启用 AES，配置 CBC 和 Key，但故意不调用 iv_set。
        support.aes.enable()
        aes_enabled = True
        support.aes.irq_clear(AesIrqEvent.ALL)
        support.aes.data_length_set(16)
        support.aes.configure(config)
        support.aes.key_set(_KEY128, config.key_size)
        support.aes.irq_enable(event)
        irq_enabled = True
        support.aes.irq_unmask(event)
        baseline = support.aes.irq_snapshot_get()
        record_property("irq_event_count_before", baseline.event_count)

        # 执行：写入一个完整块，直接触发缺失 IV 的硬件检查路径。
        support.aes.block_write_direct(_PAYLOAD16)
        snapshot = support.aes.irq_snapshot_get()
        record_property("expected_state", "IV_MISSING latched")
        record_property("irq_event_count_after", snapshot.event_count)
        record_property("irq_event_count_delta", snapshot.event_count - baseline.event_count)
        record_observation(
            record_property,
            key="actual_state",
            value=int(snapshot.latched),
            source="dut",
            endpoint="ISR.LATCHED.IV_MISSING",
        )
        record_observation(
            record_property,
            key="irq_raw_after_isr",
            value=int(snapshot.raw),
            source="dut",
            endpoint="IRQ_RAW.IV_MISSING",
        )
        record_observation(
            record_property,
            key="irq_status_after_isr",
            value=int(snapshot.status),
            source="dut",
            endpoint="IRQ_STATUS.IV_MISSING",
        )

        # 断言：错误位必须精确匹配 IV_MISSING，不能只检查 snapshot 非空。
        assert snapshot.raw == AesIrqEvent(0)
        assert snapshot.status == AesIrqEvent(0)
        assert snapshot.latched == event
        assert snapshot.event_count == baseline.event_count + 1
        support.aes.irq_clear(event)
        cleared = support.aes.irq_snapshot_get()
        record_observation(
            record_property,
            key="cleared_irq_raw",
            value=int(cleared.raw),
            source="dut",
            endpoint="IRQ_RAW.IV_MISSING",
        )
        record_observation(
            record_property,
            key="cleared_irq_status",
            value=int(cleared.status),
            source="dut",
            endpoint="IRQ_STATUS.IV_MISSING",
        )
        record_observation(
            record_property,
            key="cleared_irq_latched",
            value=int(cleared.latched),
            source="dut",
            endpoint="ISR.LATCHED.IV_MISSING",
        )
        record_result(
            et_artifact_dir,
            "aes_p1_011",
            event=event.name,
            baseline_event_count=baseline.event_count,
            snapshot={
                "raw": int(snapshot.raw),
                "status": int(snapshot.status),
                "latched": int(snapshot.latched),
                "event_count": snapshot.event_count,
            },
            cleared={
                "raw": int(cleared.raw),
                "status": int(cleared.status),
                "latched": int(cleared.latched),
                "event_count": cleared.event_count,
            },
        )
        assert not (cleared.raw & event)
        assert not (cleared.status & event)
        assert not (cleared.latched & event)


# 测试 Feature：正常完成 COMPLETE IRQ source。
#
# 测试方法：
# 1. 清除旧事件并 enable/unmask COMPLETE。
# 2. 执行一块完整 AES PROCESS，读取 output 和 IRQ snapshot。
# 3. 清除 COMPLETE 后重新取样，确认 W1C 作用于目标 bit。
#
# 通过条件：
# 1. output 精确等于 Golden，PROCESS produced_bytes 为 16。
# 2. ISR 清除硬件 raw/status 后，Service latched=COMPLETE 且 event_count 增加 1。
# 3. clear 后 COMPLETE 在三个视图均为零，且结果已在清除前保存。
def test_aes_p1_012_complete_irq(
    aes_support,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：配置正常 ECB 路径并打开 COMPLETE source。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.AES, instance=aes_support.instance_id)
    resource_driver.reset()

    support = aes_support
    event = AesIrqEvent.COMPLETE
    config = AesConfig(AesDirection.ENCRYPT, AesKeySize.AES128, AesMode.ECB, endian=AesEndian.BIG)
    require_aes_config_supported(support, config)
    require_aes_features_supported(support, AesFeature.CPU_REGISTER_PATH)
    require_aes_irq_supported(support, event)
    expected = aes_golden(_PAYLOAD16, _KEY128, None, config)
    resource_ready = False
    aes_enabled = False
    irq_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if irq_enabled:
            actions.append(("AES IRQ disable", lambda: support.aes.irq_disable(event)))
            actions.append(("AES IRQ clear", lambda: support.aes.irq_clear(event)))
        if aes_enabled:
            actions.append(("AES module disable", support.aes.disable))
        if resource_ready:
            actions.append(("Resource pool reset", support.resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 资源：重置独占池，并准备一块正常完成路径的输入和输出 Buffer。
        support.resource.reset()
        resource_ready = True
        source = support.resource.create(16, alignment=4)
        destination = support.resource.create(16, alignment=4)
        support.resource.write(source, _PAYLOAD16)

        # 配置：显式启用 AES，清除旧事件并开启 COMPLETE source。
        support.aes.enable()
        aes_enabled = True
        support.aes.irq_clear(AesIrqEvent.ALL)
        support.aes.data_length_set(16)
        support.aes.configure(config)
        support.aes.key_set(_KEY128, config.key_size)
        support.aes.irq_enable(event)
        irq_enabled = True
        support.aes.irq_unmask(event)
        baseline = support.aes.irq_snapshot_get()
        record_property("irq_event_count_before", baseline.event_count)

        # 执行：完成一笔真实 PROCESS，再取得结果和完成事件。
        result = support.aes.process(
            source.handle,
            0,
            destination.handle,
            0,
            16,
            destination_capacity=destination.size,
        )
        actual = support.resource.read(destination, result.produced_bytes)
        snapshot = support.aes.irq_snapshot_get()
        record_property("expected_irq", "COMPLETE latched")
        record_property("irq_event_count_after", snapshot.event_count)
        record_property("irq_event_count_delta", snapshot.event_count - baseline.event_count)
        record_observation(
            record_property,
            key="actual_irq_raw",
            value=int(snapshot.raw),
            source="dut",
            endpoint="IRQ_RAW.COMPLETE",
        )
        record_observation(
            record_property,
            key="actual_irq",
            value=int(snapshot.latched),
            source="dut",
            endpoint="ISR.LATCHED.COMPLETE",
        )
        record_observation(
            record_property,
            key="actual_irq_status",
            value=int(snapshot.status),
            source="dut",
            endpoint="IRQ_STATUS.COMPLETE",
        )
        record_property("expected_output", expected.hex())
        record_observation(
            record_property,
            key="actual_output",
            value=actual.hex(),
            source="dut",
            endpoint="RESULT_DOUT[0..3]",
        )

        # 断言：功能和 IRQ 证据同时成立，事件计数只增加一次。
        assert actual == expected
        assert result.produced_bytes == 16
        assert snapshot.raw == AesIrqEvent(0)
        assert snapshot.status == AesIrqEvent(0)
        assert snapshot.latched == event
        assert snapshot.event_count == baseline.event_count + 1
        support.aes.irq_clear(event)
        cleared = support.aes.irq_snapshot_get()
        record_observation(
            record_property,
            key="cleared_irq_raw",
            value=int(cleared.raw),
            source="dut",
            endpoint="IRQ_RAW.COMPLETE",
        )
        record_observation(
            record_property,
            key="cleared_irq_status",
            value=int(cleared.status),
            source="dut",
            endpoint="IRQ_STATUS.COMPLETE",
        )
        record_observation(
            record_property,
            key="cleared_irq_latched",
            value=int(cleared.latched),
            source="dut",
            endpoint="ISR.LATCHED.COMPLETE",
        )
        record_result(
            et_artifact_dir,
            "aes_p1_012",
            expected=expected,
            actual=actual,
            produced_bytes=result.produced_bytes,
            baseline_event_count=baseline.event_count,
            snapshot={
                "raw": int(snapshot.raw),
                "status": int(snapshot.status),
                "latched": int(snapshot.latched),
                "event_count": snapshot.event_count,
            },
            cleared={
                "raw": int(cleared.raw),
                "status": int(cleared.status),
                "latched": int(cleared.latched),
                "event_count": cleared.event_count,
            },
        )
        assert not (cleared.raw & event)
        assert not (cleared.status & event)
        assert not (cleared.latched & event)


# 测试 Feature：INCOMPLETE_DISABLE 中断和 disable 后恢复。
#
# 测试方法：
# 1. 配置单块寄存器路径并开启 INCOMPLETE_DISABLE source。
# 2. 写入输入块但不读取结果，立即 disable 后读取中断 snapshot。
# 3. 重新 enable/configure/key 并执行正常 KAT，验证恢复路径。
#
# 通过条件：
# 1. disable 中止未读结果，Service latched 精确记录 INCOMPLETE_DISABLE。
# 2. event_count 相比启动前精确增加 1。
# 3. 重新配置后的 KAT 精确等于 Golden，错误清理不掩盖功能失败。
def test_aes_p1_013_incomplete_disable_recovery(
    aes_support,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：使用单块寄存器路径，在结果未读取时关闭模块。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.AES, instance=aes_support.instance_id)
    resource_driver.reset()

    support = aes_support
    event = AesIrqEvent.INCOMPLETE_DISABLE
    config = AesConfig(AesDirection.ENCRYPT, AesKeySize.AES128, AesMode.ECB, endian=AesEndian.BIG)
    require_aes_config_supported(support, config)
    require_aes_features_supported(
        support, AesFeature.CPU_REGISTER_PATH | AesFeature.TEST_EXTENSIONS
    )
    require_aes_irq_supported(support, event)
    expected = aes_golden(_PAYLOAD16, _KEY128, None, config)
    resource_ready = False
    aes_enabled = False
    irq_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if irq_enabled:
            actions.append(("AES IRQ disable", lambda: support.aes.irq_disable(event)))
            actions.append(("AES IRQ clear", lambda: support.aes.irq_clear(AesIrqEvent.ALL)))
        if aes_enabled:
            actions.append(("AES module disable", support.aes.disable))
        if resource_ready:
            actions.append(("Resource pool reset", support.resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 资源：重置独占池，供事件后的正常 KAT 恢复验证使用。
        support.resource.reset()
        resource_ready = True
        # 配置：显式启用 AES，只开启未完成关闭事件并声明一个完整块长度。
        support.aes.enable()
        aes_enabled = True
        support.aes.data_length_set(16)
        support.aes.configure(config)
        support.aes.key_set(_KEY128, config.key_size)
        support.aes.irq_clear(AesIrqEvent.ALL)
        support.aes.irq_enable(event)
        irq_enabled = True
        support.aes.irq_unmask(event)
        baseline = support.aes.irq_snapshot_get()
        record_property("irq_event_count_before", baseline.event_count)

        # 执行：写入一块但不读取输出，随后关闭模块制造未完成关闭事件。
        support.aes.block_write_disable_direct(_PAYLOAD16)
        aes_enabled = False
        # DISABLE 命令已由固件关闭并解绑本次 AES IRQ session。
        irq_enabled = False
        snapshot = support.aes.irq_snapshot_get()
        record_property("expected_irq", "INCOMPLETE_DISABLE latched")
        record_property("irq_event_count_after", snapshot.event_count)
        record_property("irq_event_count_delta", snapshot.event_count - baseline.event_count)
        record_observation(
            record_property,
            key="actual_irq_raw",
            value=int(snapshot.raw),
            source="dut",
            endpoint="IRQ_RAW.INCOMPLETE_DISABLE",
        )
        record_observation(
            record_property,
            key="actual_irq",
            value=int(snapshot.latched),
            source="dut",
            endpoint="ISR.LATCHED.INCOMPLETE_DISABLE",
        )
        record_observation(
            record_property,
            key="actual_irq_status",
            value=int(snapshot.status),
            source="dut",
            endpoint="IRQ_STATUS.INCOMPLETE_DISABLE",
        )
        assert snapshot.raw == AesIrqEvent(0)
        assert snapshot.status == AesIrqEvent(0)
        assert snapshot.latched == event
        assert snapshot.event_count == baseline.event_count + 1

        # 恢复：重新 enable/configure/key，执行一块 KAT 证明状态已复原。
        support.aes.enable()
        aes_enabled = True
        support.aes.data_length_set(16)
        support.aes.configure(config)
        support.aes.key_set(_KEY128, config.key_size)
        source2 = support.resource.create(16, alignment=4)
        destination2 = support.resource.create(16, alignment=4)
        support.resource.write(source2, _PAYLOAD16)
        result = support.aes.process(
            source2.handle,
            0,
            destination2.handle,
            0,
            16,
            destination_capacity=destination2.size,
        )
        actual = support.resource.read(destination2, result.produced_bytes)
        record_property("recovery_expected", expected.hex())
        record_observation(
            record_property,
            key="recovery_actual",
            value=actual.hex(),
            source="dut",
            endpoint="RESULT_DOUT[0..3]",
        )
        record_result(
            et_artifact_dir,
            "aes_p1_013",
            event=event.name,
            baseline_event_count=baseline.event_count,
            snapshot={
                "raw": int(snapshot.raw),
                "status": int(snapshot.status),
                "latched": int(snapshot.latched),
                "event_count": snapshot.event_count,
            },
            recovery={
                "expected": expected,
                "actual": actual,
                "produced_bytes": result.produced_bytes,
            },
        )
        assert actual == expected
        assert result.produced_bytes == 16
        support.aes.irq_clear(event)


# 测试 Feature：IRQ transfer block session 的状态/offset 进展。
#
# 测试方法：
# 1. 用一个完整 block Resource 启动 IRQ_TRANSFER_START。
# 2. 反复读取 typed status，只有 state/offset 变化或终态才结束轮询。
# 3. 在 COMPLETE 终态读取 output，并执行 abort/clear cleanup。
#
# 通过条件：
# 1. 初始 state 为 IDLE，启动后 offset 单调不减且不超过 logical length。
# 2. 终态必须是 COMPLETE，produced_bytes 和 output 精确匹配 Golden。
# 3. 不使用固定 sleep；未达到终态时继续依赖 status state/offset 证据。
def test_aes_p1_014_irq_transfer_session(
    aes_support,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：创建一个 block 的输入/输出 Resource 和 AES 配置。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.AES, instance=aes_support.instance_id)
    resource_driver.reset()

    support = aes_support
    transfer_events = AesIrqEvent.DATA_IN_REQ | AesIrqEvent.DATA_OUT_REQ | AesIrqEvent.COMPLETE
    config = AesConfig(AesDirection.ENCRYPT, AesKeySize.AES128, AesMode.ECB, endian=AesEndian.BIG)
    require_aes_config_supported(support, config)
    require_aes_irq_supported(support, transfer_events, require_transfer=True)
    payload = _PAYLOAD16
    expected = aes_golden(payload, _KEY128, None, config)
    resource_ready = False
    aes_enabled = False
    irq_enabled = False
    transfer_started = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if transfer_started:
            actions.append(("AES IRQ transfer abort", support.aes.irq_transfer_abort))
        if irq_enabled:
            actions.append(("AES IRQ disable", lambda: support.aes.irq_disable(transfer_events)))
            actions.append(("AES IRQ clear", lambda: support.aes.irq_clear(transfer_events)))
        if aes_enabled:
            actions.append(("AES module disable", support.aes.disable))
        if resource_ready:
            actions.append(("Resource pool reset", support.resource.reset))
        return tuple(actions)

    initial = None
    observed = None
    irq_snapshot = None
    actual = None
    try:
        with case_cleanup_scope(cleanup_actions):
            # 资源：重置独占池，并创建两个 block 的输入和输出 Buffer。
            support.resource.reset()
            resource_ready = True
            source = support.resource.create(len(payload), alignment=4)
            destination = support.resource.create(len(payload), alignment=4)
            support.resource.write(source, payload)

            # 配置：显式启用 AES，并开启 IRQ transfer 所需事件。
            support.aes.enable()
            aes_enabled = True
            support.aes.configure(config)
            support.aes.key_set(_KEY128, config.key_size)
            support.aes.irq_clear(AesIrqEvent.ALL)
            support.aes.irq_enable(transfer_events)
            irq_enabled = True
            support.aes.irq_unmask(transfer_events)
            initial = support.aes.irq_transfer_status_get()
            observed = initial
            record_property("expected_irq", "IRQ transfer starts from IDLE and reaches COMPLETE")
            record_observation(
                record_property,
                key="irq_transfer_initial_state",
                value=initial.state.name,
                source="dut",
                endpoint="IRQ_TRANSFER.STATE",
            )
            assert initial.state is AesIrqTransferState.IDLE
            support.aes.irq_transfer_start(source.handle, 0, destination.handle, 0, len(payload))
            transfer_started = True

            # 执行：状态驱动轮询，offset/状态决定是否继续，不能固定等待时间。
            for _ in range(64):
                observed = support.aes.irq_transfer_status_get()
                record_observation(
                    record_property,
                    key="irq_transfer_state",
                    value=observed.state.name,
                    source="dut",
                    endpoint="IRQ_TRANSFER.STATE",
                )
                record_observation(
                    record_property,
                    key="irq_transfer_input_offset",
                    value=observed.input_offset,
                    source="dut",
                    endpoint="IRQ_TRANSFER.INPUT_OFFSET",
                )
                record_observation(
                    record_property,
                    key="irq_transfer_output_offset",
                    value=observed.output_offset,
                    source="dut",
                    endpoint="IRQ_TRANSFER.OUTPUT_OFFSET",
                )
                assert 0 <= observed.input_offset <= len(payload)
                assert 0 <= observed.output_offset <= len(payload)
                if observed.state in (
                    AesIrqTransferState.COMPLETE,
                    AesIrqTransferState.ABORTED,
                    AesIrqTransferState.FAULT,
                ):
                    break

            irq_snapshot = support.aes.irq_snapshot_get()
            record_observation(
                record_property,
                key="actual_irq",
                value=observed.state.name,
                source="dut",
                endpoint="IRQ_TRANSFER.STATE",
            )
            record_observation(
                record_property,
                key="actual_irq_status",
                value=int(irq_snapshot.latched),
                source="dut",
                endpoint="ISR.LATCHED.IRQ_TRANSFER",
            )
            assert observed.state is AesIrqTransferState.COMPLETE
            assert observed.input_offset == len(payload)
            assert observed.output_offset == len(payload)
            assert observed.produced_bytes == len(expected)

            # 观测：终态 output 必须等于独立 Golden。
            actual = support.resource.read(destination, observed.produced_bytes)
            record_property("expected_output", expected.hex())
            record_observation(
                record_property,
                key="actual_output",
                value=actual.hex(),
                source="dut",
                endpoint="RESULT_DOUT[0..3]",
            )
            assert actual == expected
            support.aes.irq_transfer_abort()
            transfer_started = False
    finally:
        # Evidence Closure：即使会话中途失败，也只发布一次当前终态 Snapshot。
        record_result(
            et_artifact_dir,
            "aes_p1_014",
            states={
                "initial": initial.state.name if initial is not None else None,
                "observed": observed.state.name if observed is not None else None,
            },
            offsets={
                "input": observed.input_offset if observed is not None else None,
                "output": observed.output_offset if observed is not None else None,
            },
            produced_bytes=observed.produced_bytes if observed is not None else None,
            irq_snapshot=(
                {
                    "raw": int(irq_snapshot.raw),
                    "status": int(irq_snapshot.status),
                    "latched": int(irq_snapshot.latched),
                    "event_count": irq_snapshot.event_count,
                }
                if irq_snapshot is not None
                else {"raw": None, "status": None, "latched": None, "event_count": None}
            ),
            expected=expected,
            actual=actual,
        )


# 测试 Feature：五个非请求型 AES IRQ source 的 force/delivery 语义。
#
# 测试方法：
# 1. 每个参数节点清除旧事件，enable/unmask 一个目标 source。
# 2. 调用 irq_force 并读取 force 前后 snapshot。
# 3. disable/clear 目标 source，再读取终态 snapshot。
#
# 通过条件：
# 1. ISR 清除 raw/status 后，latched 精确等于目标 bit。
# 2. event_count 相比 force 前精确增加 1。
# 3. clear 后目标 bit 在三个视图均为零，计数不因 clear 虚增。
@pytest.mark.parametrize("event", tuple(AesIrqEvent(item) for item in (1, 2, 4, 8, 16)))
def test_aes_p1_015_irq_force_delivery(
    event: AesIrqEvent,
    aes_support,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：只保留当前参数的 AES-owned IRQ source。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.AES, instance=aes_support.instance_id)
    resource_driver.reset()

    support = aes_support
    require_aes_irq_supported(support, event)
    aes_enabled = False
    irq_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if irq_enabled:
            actions.append(("AES IRQ disable", lambda: support.aes.irq_disable(event)))
            actions.append(("AES IRQ clear", lambda: support.aes.irq_clear(event)))
        if aes_enabled:
            actions.append(("AES module disable", support.aes.disable))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 配置：启用模块、清除旧事件，并 enable/unmask 当前参数 source。
        support.aes.enable()
        aes_enabled = True
        support.aes.irq_clear(AesIrqEvent.ALL)
        support.aes.irq_enable(event)
        irq_enabled = True
        support.aes.irq_unmask(event)
        before = support.aes.irq_snapshot_get()
        record_property("irq_event_count_before", before.event_count)

        # 刺激：force 是硬件事件 stimulus，不是只读 status。
        support.aes.irq_force(event)
        after_force = support.aes.irq_snapshot_get()
        record_property("expected_irq", f"{event.name} latched")
        record_property("irq_event_count_after", after_force.event_count)
        record_property("irq_event_count_delta", after_force.event_count - before.event_count)
        record_observation(
            record_property,
            key="actual_irq_raw",
            value=int(after_force.raw),
            source="dut",
            endpoint=f"IRQ_RAW.{event.name}",
        )
        record_observation(
            record_property,
            key="actual_irq",
            value=int(after_force.latched),
            source="dut",
            endpoint=f"ISR.LATCHED.{event.name}",
        )
        record_observation(
            record_property,
            key="actual_irq_status",
            value=int(after_force.status),
            source="dut",
            endpoint=f"IRQ_STATUS.{event.name}",
        )

        # 断言：ISR 已确认硬件状态，latched 和 event count 保留投递证据。
        assert after_force.raw == AesIrqEvent(0)
        assert after_force.status == AesIrqEvent(0)
        assert after_force.latched == event
        assert after_force.event_count == before.event_count + 1

        # 恢复：禁用并清除目标 source，再检查三个状态视图与计数。
        support.aes.irq_disable(event)
        irq_enabled = False
        support.aes.irq_clear(event)
        after_clear = support.aes.irq_snapshot_get()
        record_property(
            "clear_event_count_delta", after_clear.event_count - after_force.event_count
        )
        record_observation(
            record_property,
            key="cleared_irq_raw",
            value=int(after_clear.raw),
            source="dut",
            endpoint=f"IRQ_RAW.{event.name}",
        )
        record_observation(
            record_property,
            key="cleared_irq_status",
            value=int(after_clear.status),
            source="dut",
            endpoint=f"IRQ_STATUS.{event.name}",
        )
        record_observation(
            record_property,
            key="cleared_irq_latched",
            value=int(after_clear.latched),
            source="dut",
            endpoint=f"ISR.LATCHED.{event.name}",
        )
        record_result(
            et_artifact_dir,
            "aes_p1_015",
            event=event.name,
            baseline_event_count=before.event_count,
            after_force={
                "raw": int(after_force.raw),
                "status": int(after_force.status),
                "latched": int(after_force.latched),
                "event_count": after_force.event_count,
            },
            after_clear={
                "raw": int(after_clear.raw),
                "status": int(after_clear.status),
                "latched": int(after_clear.latched),
                "event_count": after_clear.event_count,
            },
        )
        assert not (after_clear.raw & event)
        assert not (after_clear.status & event)
        assert not (after_clear.latched & event)
        assert after_clear.event_count == after_force.event_count


# 测试 Feature：IRQ mask/unmask 保留 raw、抑制和恢复 status。
#
# 测试方法：
# 1. enable 目标 COMPLETE source 后先 mask，再 force 一次事件。
# 2. 分别读取 masked snapshot 和 unmask 后 snapshot。
# 3. 比较两次 raw/status/latched/event_count，并清理事件。
#
# 通过条件：
# 1. masked 状态 raw=COMPLETE、status=0，证明 mask 只抑制 delivery。
# 2. unmask 后 ISR 清除 raw/status，并在 latched 中记录 COMPLETE。
# 3. masked 阶段不计事件，unmask 后 event_count 精确增加 1。
def test_aes_p1_016_irq_mask_semantics(
    aes_support,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：清掉旧 COMPLETE，再建立 enable/mask 状态。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.AES, instance=aes_support.instance_id)
    resource_driver.reset()

    support = aes_support
    event = AesIrqEvent.COMPLETE
    require_aes_irq_supported(support, event)
    aes_enabled = False
    irq_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if irq_enabled:
            actions.append(("AES IRQ disable", lambda: support.aes.irq_disable(event)))
            actions.append(("AES IRQ clear", lambda: support.aes.irq_clear(event)))
        if aes_enabled:
            actions.append(("AES module disable", support.aes.disable))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 配置：启用模块、清除旧 COMPLETE，enable 后保持 mask 状态。
        support.aes.enable()
        aes_enabled = True
        support.aes.irq_clear(AesIrqEvent.ALL)
        support.aes.irq_enable(event)
        irq_enabled = True
        support.aes.irq_mask(event)

        # 刺激：force 事件并取得屏蔽视图，然后解除屏蔽。
        support.aes.irq_force(event)
        masked = support.aes.irq_snapshot_get()
        record_property("expected_irq", "Mask keeps RAW and suppresses STATUS/ISR")
        record_property("irq_event_count_before", masked.event_count)
        record_observation(
            record_property,
            key="masked_raw",
            value=int(masked.raw),
            source="dut",
            endpoint="IRQ_RAW.COMPLETE",
        )
        record_observation(
            record_property,
            key="actual_irq_status",
            value=int(masked.status),
            source="dut",
            endpoint="IRQ_STATUS.COMPLETE",
        )
        record_observation(
            record_property,
            key="masked_latched",
            value=int(masked.latched),
            source="dut",
            endpoint="ISR.LATCHED.COMPLETE",
        )
        assert masked.raw == event
        assert masked.status == AesIrqEvent(0)
        assert masked.latched == AesIrqEvent(0)

        # 观测：unmask 触发一次真实 ISR 投递，随后硬件状态被确认清除。
        support.aes.irq_unmask(event)
        unmasked = support.aes.irq_snapshot_get()
        record_property("irq_event_count_after", unmasked.event_count)
        record_property("irq_event_count_delta", unmasked.event_count - masked.event_count)
        record_observation(
            record_property,
            key="unmasked_raw",
            value=int(unmasked.raw),
            source="dut",
            endpoint="IRQ_RAW.COMPLETE",
        )
        record_observation(
            record_property,
            key="unmasked_status",
            value=int(unmasked.status),
            source="dut",
            endpoint="IRQ_STATUS.COMPLETE",
        )
        record_observation(
            record_property,
            key="actual_irq",
            value=int(unmasked.latched),
            source="dut",
            endpoint="ISR.LATCHED.COMPLETE",
        )
        record_result(
            et_artifact_dir,
            "aes_p1_016",
            event=event.name,
            masked={
                "raw": int(masked.raw),
                "status": int(masked.status),
                "latched": int(masked.latched),
                "event_count": masked.event_count,
            },
            unmasked={
                "raw": int(unmasked.raw),
                "status": int(unmasked.status),
                "latched": int(unmasked.latched),
                "event_count": unmasked.event_count,
            },
        )
        assert unmasked.raw == AesIrqEvent(0)
        assert unmasked.status == AesIrqEvent(0)
        assert unmasked.latched == event
        assert unmasked.event_count == masked.event_count + 1

        # 恢复：清除并禁用本 Case 获取的 IRQ source。
        support.aes.irq_clear(event)
        support.aes.irq_disable(event)
        irq_enabled = False


# 测试 Feature：INT_CLR 对单个 IRQ source 的精确清除。
#
# 测试方法：
# 1. 清除全部旧事件，force 一个参数化目标 source。
# 2. 保持 source 屏蔽并保存 force 后 raw/status/latched 和 event_count。
# 3. 只清除目标 source，再读取三个视图和计数。
#
# 通过条件：
# 1. force 后 raw 精确等于目标 bit，status/latched 保持为零。
# 2. clear 后目标 bit 在 raw/status/latched 均为零。
# 3. clear 不增加 event_count，且没有用恒真表达式替代断言。
@pytest.mark.parametrize("event", tuple(AesIrqEvent(item) for item in (1, 2, 4, 8, 16, 32, 64)))
def test_aes_p1_017_irq_exact_clear(
    event: AesIrqEvent,
    aes_support,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：每个 source 节点从干净的 IRQ 状态开始。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.AES, instance=aes_support.instance_id)
    resource_driver.reset()

    support = aes_support
    require_aes_irq_supported(support, event)
    aes_enabled = False
    irq_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if irq_enabled:
            actions.append(("AES IRQ disable", lambda: support.aes.irq_disable(event)))
            actions.append(("AES IRQ clear", lambda: support.aes.irq_clear(event)))
        if aes_enabled:
            actions.append(("AES module disable", support.aes.disable))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 配置：启用模块、清除全部旧事件，再 enable/unmask 当前参数 source。
        support.aes.enable()
        aes_enabled = True
        support.aes.irq_clear(AesIrqEvent.ALL)
        support.aes.irq_enable(event)
        irq_enabled = True
        support.aes.irq_mask(event)

        # 刺激：force 目标事件并保存清除前的硬件快照。
        support.aes.irq_force(event)
        before = support.aes.irq_snapshot_get()
        record_property("expected_irq", f"RAW={event.name} before clear")
        record_property("irq_event_count_before", before.event_count)
        record_observation(
            record_property,
            key="actual_irq",
            value=int(before.raw),
            source="dut",
            endpoint=f"IRQ_RAW.{event.name}",
        )
        record_observation(
            record_property,
            key="actual_irq_status",
            value=int(before.status),
            source="dut",
            endpoint=f"IRQ_STATUS.{event.name}",
        )
        record_observation(
            record_property,
            key="before_latched",
            value=int(before.latched),
            source="dut",
            endpoint=f"ISR.LATCHED.{event.name}",
        )
        assert before.raw == event
        assert before.status == AesIrqEvent(0)
        assert before.latched == AesIrqEvent(0)

        # 观测：单 bit clear 后只接受目标位消失和计数保持不变。
        support.aes.irq_clear(event)
        after = support.aes.irq_snapshot_get()
        record_property("irq_event_count_after", after.event_count)
        record_property("clear_event_count_delta", after.event_count - before.event_count)
        record_observation(
            record_property,
            key="cleared_irq_raw",
            value=int(after.raw),
            source="dut",
            endpoint=f"IRQ_RAW.{event.name}",
        )
        record_observation(
            record_property,
            key="cleared_irq_status",
            value=int(after.status),
            source="dut",
            endpoint=f"IRQ_STATUS.{event.name}",
        )
        record_observation(
            record_property,
            key="cleared_irq_latched",
            value=int(after.latched),
            source="dut",
            endpoint=f"ISR.LATCHED.{event.name}",
        )
        record_result(
            et_artifact_dir,
            "aes_p1_017",
            event=event.name,
            before={
                "raw": int(before.raw),
                "status": int(before.status),
                "latched": int(before.latched),
                "event_count": before.event_count,
            },
            after={
                "raw": int(after.raw),
                "status": int(after.status),
                "latched": int(after.latched),
                "event_count": after.event_count,
            },
        )
        assert not (after.raw & event)
        assert not (after.status & event)
        assert not (after.latched & event)
        assert after.event_count == before.event_count

        # 恢复：禁用本 Case 获取的 IRQ source。
        support.aes.irq_disable(event)
        irq_enabled = False
