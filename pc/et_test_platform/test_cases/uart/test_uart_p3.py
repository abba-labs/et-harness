# Formal Case测试模块。
#
# 职责：按测试等级承载可执行Feature流程、证据和最终断言。
# 边界：不直接调用Codec、Transport或芯片专有接口。
# 依赖：仅依赖Fixture、公共Driver及Case本地Support。

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction
from ...drivers.crg import CrgPeripheral
from ...drivers.uart import UartFeature
from ...scheduling.run_context import record_evidence, record_observation
from ..case_cleanup import case_cleanup_scope
from .uart_helpers import DEFAULT_BAUDRATE, DEFAULT_MAX_POLLS, make_pattern, record_result

pytestmark = [pytest.mark.hardware, pytest.mark.ip("uart")]


# =============================================================================
# 特殊 FIFO 访问
# =============================================================================


# 测试 Feature：
# UART Shadow FIFO 配置（SFE/SRT/STET）。
#
# 测试方法：
# 1. 查询 UartFeature.SHADOW，开启 Shadow FIFO 并配置可区分的 TX/RX 阈值。
# 2. 读回后关闭 Shadow、恢复普通 FIFO，再执行普通内部回环恢复传输。
#
# 通过条件：
# 1. Shadow 配置读回与请求一致，关闭后 enabled=False。
# 2. 恢复后的普通 UART 数据完整收发且逐字节一致。
def test_uart_p3_007_shadow_fifo_configuration(
    uart_dut_handle,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 门禁：Shadow 能力必须在任何硬件状态变更前确认。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dut_handle.instance_id)
    resource_driver.reset()

    capabilities = uart_dut_handle.capabilities_get()
    if capabilities.features & UartFeature.SHADOW != UartFeature.SHADOW:
        pytest.skip(
            f"skip_by_runtime_feature: UART DUT feature {UartFeature.SHADOW.name} unavailable"
        )

    initialized = False
    loopback_cleanup_owned = False
    capture_cleanup_owned = False
    shadow_enabled = False

    # 清理：严格保持原顺序，先退出普通 UART 状态，最后恢复 Shadow/FIFO 配置。
    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if capture_cleanup_owned:
            actions.append(("UART DUT capture cancel", uart_dut_handle.capture_cancel))
        if loopback_cleanup_owned:
            actions.append(
                ("UART DUT loopback disable", lambda: uart_dut_handle.loopback_set(False))
            )
        if initialized:
            actions.append(("UART DUT deinitialize", uart_dut_handle.deinitialize))
        if shadow_enabled:
            actions.extend(
                (
                    (
                        "UART shadow FIFO disable",
                        lambda: uart_dut_handle.shadow_fifo_config(
                            enabled=False,
                            tx_threshold=0,
                            rx_threshold=1,
                        ),
                    ),
                    (
                        "UART normal FIFO restore",
                        lambda: uart_dut_handle.fifo_config(
                            enabled=True,
                            tx_threshold=0,
                            rx_threshold=1,
                        ),
                    ),
                )
            )
        return tuple(actions)

    # 配置：初始化 DUT；与原生命周期一致，初始化失败时不执行后续清理。
    uart_dut_handle.initialize(baudrate=DEFAULT_BAUDRATE, data_bits=8, stop_bits=1, parity=0)
    initialized = True

    with case_cleanup_scope(cleanup_actions):
        loopback_cleanup_owned = True
        capture_cleanup_owned = True

        # 配置：开启 Shadow FIFO 并设置可区分的 TX/RX 阈值。
        shadow = uart_dut_handle.shadow_fifo_config(
            enabled=True,
            tx_threshold=2,
            rx_threshold=4,
        )
        shadow_enabled = True

        record_observation(
            record_property,
            key="shadow_enabled",
            value=shadow.enabled,
            source="dut",
            endpoint="UART_SHADOW.ENABLED",
        )
        record_observation(
            record_property,
            key="shadow_tx_threshold",
            value=shadow.tx_threshold,
            source="dut",
            endpoint="UART_SHADOW.TX_THRESHOLD",
        )
        record_observation(
            record_property,
            key="shadow_rx_threshold",
            value=shadow.rx_threshold,
            source="dut",
            endpoint="UART_SHADOW.RX_THRESHOLD",
        )

        # 断言：Shadow 配置必须完整回读，不能只检查命令返回成功。
        assert shadow.enabled
        assert shadow.tx_threshold == 2
        assert shadow.rx_threshold == 4

        # 恢复：显式退出 Shadow，并恢复普通 FIFO。
        restored_shadow = uart_dut_handle.shadow_fifo_config(
            enabled=False,
            tx_threshold=0,
            rx_threshold=1,
        )
        uart_dut_handle.fifo_config(
            enabled=True,
            tx_threshold=0,
            rx_threshold=1,
        )
        shadow_enabled = False

        # 断言：Shadow 关闭状态必须明确回读为 False。
        assert not restored_shadow.enabled

        # 恢复：重新初始化 UART 默认数据路径。
        uart_dut_handle.initialize(baudrate=DEFAULT_BAUDRATE)

        # 准备：构造普通 FIFO 恢复路径 Payload。
        payload = bytes(make_pattern(4, seed=0xD3))

        # 配置：开启内部回环。
        uart_dut_handle.loopback_set(True)

        # 接收：Capture 必须先于恢复发送启动。
        uart_dut_handle.capture_start(len(payload))

        # 发送：写入恢复路径 Payload。
        transferred = uart_dut_handle.write(payload, max_polls=DEFAULT_MAX_POLLS)

        # 观测：等待普通 FIFO 数据接收完成。
        capture = uart_dut_handle.capture_wait(len(payload))

        record_observation(
            record_property,
            key="recovery_actual_data",
            value=capture.data,
            source="dut",
            endpoint="UART_CAPTURE.DATA",
        )

        # 断言：恢复后的普通 UART 数据路径必须完整一致。
        assert transferred == len(payload)
        assert capture.received == len(payload)
        assert capture.data == payload

    record_evidence(record_property, "dut")
    output = record_result(
        et_artifact_dir,
        "uart_p3_007_shadow_fifo_configuration",
        features=int(capabilities.features),
        shadow=asdict(shadow),
        restored_shadow=asdict(restored_shadow),
        recovery={
            "tx_requested": len(payload),
            "tx_completed": transferred,
            "rx_expected": len(payload),
            "rx_completed": capture.received,
            "data_match": capture.data == payload,
        },
    )
    record_property("uart_result", str(output))


# 测试 Feature：
# UART Direct FIFO 访问（FAR/TFR/RFW）。
#
# 测试方法：
# 1. 查询 UartFeature.FIFO_ACCESS，开启 FAR 后 Halt TX，并通过 TFR 读回一个 TX 字节。
# 2. 通过 RFW 注入一个 RX 字节，关闭 FAR/HTX，恢复普通 FIFO 后执行内部回环。
#
# 通过条件：
# 1. TFR 读回 0x5A、RFW 普通 RX 读回 0xA5，FAR 显式关闭。
# 2. 恢复后的普通 UART 数据完整收发且逐字节一致。
def test_uart_p3_009_direct_fifo_access(
    uart_dut_handle,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 门禁：Direct FIFO 能力必须在初始化之前确认，避免 Skip 遗留硬件状态。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dut_handle.instance_id)
    resource_driver.reset()

    capabilities = uart_dut_handle.capabilities_get()
    if capabilities.features & UartFeature.FIFO_ACCESS != UartFeature.FIFO_ACCESS:
        pytest.skip(
            f"skip_by_runtime_feature: UART DUT feature {UartFeature.FIFO_ACCESS.name} unavailable"
        )

    initialized = False
    loopback_cleanup_owned = False
    fifo_access_cleanup_owned = False
    halt_cleanup_owned = False
    capture_cleanup_owned = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if capture_cleanup_owned:
            actions.append(("UART DUT capture cancel", uart_dut_handle.capture_cancel))
        if halt_cleanup_owned:
            actions.append(("UART DUT halt release", lambda: uart_dut_handle.halt_set(False)))
        if fifo_access_cleanup_owned:
            actions.append(
                (
                    "UART DUT FIFO access disable",
                    lambda: uart_dut_handle.test_fifo_access_set(False),
                )
            )
        if loopback_cleanup_owned:
            actions.append(
                ("UART DUT loopback disable", lambda: uart_dut_handle.loopback_set(False))
            )
        if initialized:
            actions.append(("UART DUT deinitialize", uart_dut_handle.deinitialize))
        return tuple(actions)

    # 配置：初始化 DUT；初始化失败时保持原行为，不执行后续清理。
    uart_dut_handle.initialize(baudrate=DEFAULT_BAUDRATE)
    initialized = True

    with case_cleanup_scope(cleanup_actions):
        loopback_cleanup_owned = True

        # 配置：开启 Direct FIFO Access。
        fifo_enabled = uart_dut_handle.test_fifo_access_set(True)
        fifo_access_cleanup_owned = True

        # 配置：Halt TX，确保 TFR 可读取确定的单字节数据。
        uart_dut_handle.halt_set(True)
        halt_cleanup_owned = True
        capture_cleanup_owned = True

        record_observation(
            record_property,
            key="fifo_access_enabled",
            value=fifo_enabled,
            source="dut",
            endpoint="UART_FIFO_ACCESS.ENABLED",
        )

        # 断言：Direct FIFO Access 必须明确处于使能状态。
        assert fifo_enabled

        # 激励：写入一个 TX 字节，并通过 TFR 直接读回。
        queued = uart_dut_handle.write_partial(bytes((0x5A,)))
        assert queued == 1
        tx_value = uart_dut_handle.test_fifo_tx_read()
        record_observation(
            record_property,
            key="tx_fifo_value",
            value=tx_value,
            source="dut",
            endpoint="UART_FIFO_ACCESS.TX_VALUE",
        )
        assert tx_value == 0x5A

        # 恢复：显式 Resume TX，再通过 RFW 注入一个 RX 字节。
        uart_dut_handle.halt_set(False)
        uart_dut_handle.test_fifo_rx_write(0xA5)

        # 观测与断言：普通 RX 路径必须读回 RFW 注入值。
        rx_value = uart_dut_handle.read_exact(1)
        record_observation(
            record_property,
            key="rx_fifo_value",
            value=rx_value[0],
            source="dut",
            endpoint="UART_FIFO_ACCESS.RX_VALUE",
        )
        assert rx_value == bytes((0xA5,))

        # 恢复：显式关闭 FAR，并确认返回状态。
        far_after = uart_dut_handle.test_fifo_access_set(False)
        assert far_after is False

        # 配置：恢复普通 FIFO 模式。
        uart_dut_handle.fifo_config(enabled=True, tx_threshold=0, rx_threshold=1)

        # 准备：构造普通 FIFO 恢复路径 Payload。
        payload = make_pattern(4, seed=0xD3)

        # 配置：开启内部回环。
        uart_dut_handle.loopback_set(True)

        # 接收：Capture 必须先于恢复发送启动。
        uart_dut_handle.capture_start(len(payload))

        # 发送：写入恢复路径 Payload。
        transferred = uart_dut_handle.write(payload, max_polls=DEFAULT_MAX_POLLS)

        # 观测：等待普通 FIFO 数据接收完成。
        capture = uart_dut_handle.capture_wait(len(payload))

        record_observation(
            record_property,
            key="recovery_actual_data",
            value=capture.data,
            source="dut",
            endpoint="UART_CAPTURE.DATA",
        )

        # 断言：Direct FIFO 测试后普通 UART 路径必须完整恢复。
        assert transferred == len(payload)
        assert capture.received == len(payload)
        assert capture.data == payload

    record_evidence(record_property, "dut")
    output = record_result(
        et_artifact_dir,
        "uart_p3_009_direct_fifo_access",
        features=int(capabilities.features),
        tx_value=tx_value,
        rx_value=rx_value,
        far_after=far_after,
        recovery={
            "tx_requested": len(payload),
            "tx_completed": transferred,
            "rx_expected": len(payload),
            "rx_completed": capture.received,
            "data_match": capture.data == payload,
        },
    )
    record_property("uart_result", str(output))


# 测试 Feature：
# UART 双向混合收发 20 轮稳定性能力。
#
# 测试方法：
# 1. 固定轮换 4、32、257 字节长度，使用确定种子生成 Payload，逐轮执行 DUT→Peer。
# 2. 同一轮用相同 Payload 执行 Peer→DUT，逐轮断言并累计事务数和字节数。
#
# 通过条件：
# 1. 20 轮两个方向均完整收发且数据逐字节一致。
# 2. 最终事务数为 40，累计字节数等于所有轮次双向长度总和。
def test_uart_p3_010_long_run_mixed_transfer(
    uart_dut_handle,
    uart_peer_handle,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 准备：固定20轮和三档载荷长度，避免普通回归退化为长时间老化。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dut_handle.instance_id)
    crg_driver.reset(CrgPeripheral.UART, instance=uart_peer_handle.instance_id)
    resource_driver.reset()

    round_count = 20
    lengths = (4, 32, 257)
    transactions = 0
    payload_bytes = 0
    dut_initialized = False
    peer_initialized = False
    dut_capture_started = False
    peer_capture_started = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if dut_capture_started:
            actions.append(("UART DUT capture cancel", uart_dut_handle.capture_cancel))
        if peer_capture_started:
            actions.append(("UART peer capture cancel", uart_peer_handle.capture_cancel))
        if peer_initialized:
            actions.append(("UART peer deinitialize", uart_peer_handle.deinitialize))
        if dut_initialized:
            actions.append(("UART DUT deinitialize", uart_dut_handle.deinitialize))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 配置：DUT 与 Peer 使用相同的默认帧格式。
        uart_dut_handle.initialize(
            baudrate=DEFAULT_BAUDRATE,
            data_bits=8,
            stop_bits=1,
            parity=0,
        )
        dut_initialized = True
        uart_peer_handle.initialize(
            baudrate=DEFAULT_BAUDRATE,
            data_bits=8,
            stop_bits=1,
            parity=0,
        )
        peer_initialized = True

        # 遍历：轮换三档长度；每轮完成双向传输、断言并累计证据。
        for index in range(round_count):
            length = lengths[index % len(lengths)]
            payload = make_pattern(length, seed=(index * 13) & 0xFF)

            # DUT→Peer：启动 Peer Capture 后发送本轮载荷。
            uart_peer_handle.capture_start(len(payload))
            peer_capture_started = True
            dut_tx = uart_dut_handle.write(payload, max_polls=DEFAULT_MAX_POLLS)
            peer_capture = uart_peer_handle.capture_wait(len(payload))

            record_property("round_index", index)
            record_observation(
                record_property,
                key="peer_actual_data",
                value=peer_capture.data,
                source="peer",
                device_id="peer",
                endpoint="PEER_UART.RX_CAPTURE",
            )

            # 断言：正向长度和数据必须完整一致。
            assert dut_tx == len(payload)
            assert peer_capture.received == len(payload)
            assert peer_capture.data == payload

            # Peer→DUT：切换方向并复用本轮载荷。
            uart_dut_handle.capture_start(len(payload))
            dut_capture_started = True
            peer_tx = uart_peer_handle.write(payload, max_polls=DEFAULT_MAX_POLLS)
            dut_capture = uart_dut_handle.capture_wait(len(payload))

            record_observation(
                record_property,
                key="dut_actual_data",
                value=dut_capture.data,
                source="dut",
                endpoint="UART_CAPTURE.DATA",
            )
            all_data_match = peer_capture.data == payload and dut_capture.data == payload
            record_property("all_data_match", all_data_match)

            # 断言：反向长度和数据必须完整一致。
            assert peer_tx == len(payload)
            assert dut_capture.received == len(payload)
            assert dut_capture.data == payload

            transactions += 2
            payload_bytes += length * 2

    # 断言与记录：最终事务计数必须等于轮数的双向总和。
    assert transactions == round_count * 2
    record_property("round_count", round_count)
    record_property("transaction_count", transactions)
    record_property("all_rounds_data_match", True)
    record_evidence(record_property, "dut", "peer")
    output = record_result(
        et_artifact_dir,
        "uart_p3_010_long_run_mixed_transfer",
        rounds=round_count,
        transactions=transactions,
        payload_bytes=payload_bytes,
        lengths=list(lengths),
        last_peer_actual_data=list(peer_capture.data),
        last_dut_actual_data=list(dut_capture.data),
    )
    record_property("uart_result", str(output))
