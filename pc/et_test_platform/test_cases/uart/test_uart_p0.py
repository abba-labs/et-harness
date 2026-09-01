# Formal Case测试模块。
#
# 职责：按测试等级承载可执行Feature流程、证据和最终断言。
# 边界：不直接调用Codec、Transport或芯片专有接口。
# 依赖：仅依赖Fixture、公共Driver及Case本地Support。

from __future__ import annotations

from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction
from ...drivers.crg import CrgPeripheral
from ...drivers.uart import UartParity
from ...scheduling.run_context import record_evidence, record_observation
from ..case_cleanup import case_cleanup_scope
from .uart_helpers import DEFAULT_BAUDRATE, DEFAULT_MAX_POLLS, make_pattern, record_result

pytestmark = [pytest.mark.hardware, pytest.mark.ip("uart")]


# =============================================================================
# 基础能力与复位
# =============================================================================


# 测试 Feature：
# 选定 UART 实例的运行时能力和身份信息。
#
# 测试方法：
# 1. 查询Runtime Capability并初始化代表实例，读取组件parameter/version/type/scratch快照。
# 2. Capability作为Service/配置事实记录；组件身份字段作为目标侧硬件Observation记录。
#
# 通过条件：
# 1. 最小波特率为正且不大于最大波特率。
# 2. 最大读写长度均非零。
def test_uart_p0_001_selected_instance_identity_and_caps(
    uart_dut_handle,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 执行：按Formal Case契约完成受控硬件动作，并在决定性断言前保存证据。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dut_handle.instance_id)
    resource_driver.reset()

    capabilities = uart_dut_handle.capabilities_get()
    initialized = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        if not initialized:
            return ()
        return (("UART DUT deinitialize", uart_dut_handle.deinitialize),)

    with case_cleanup_scope(cleanup_actions):
        uart_dut_handle.initialize(baudrate=DEFAULT_BAUDRATE)
        initialized = True
        snapshot = uart_dut_handle.snapshot_get()

        record_property("capabilities_features", int(capabilities.features))
        record_observation(
            record_property,
            key="component_parameter",
            value=snapshot.component_parameter,
            source="dut",
            endpoint="UART_COMPONENT.COMPONENT_PARAMETER",
        )
        record_observation(
            record_property,
            key="component_version",
            value=snapshot.component_version,
            source="dut",
            endpoint="UART_COMPONENT.COMPONENT_VERSION",
        )
        record_observation(
            record_property,
            key="peripheral_id",
            value=snapshot.peripheral_id,
            source="dut",
            endpoint="UART_COMPONENT.PERIPHERAL_ID",
        )
        record_observation(
            record_property,
            key="scratch_readback",
            value=snapshot.scratch,
            source="dut",
            endpoint="UART_COMPONENT.SCRATCH",
        )
        record_property("min_baudrate", capabilities.min_baudrate)
        record_property("max_baudrate", capabilities.max_baudrate)
        record_property("max_read_size", capabilities.max_read_size)
        record_property("max_write_size", capabilities.max_write_size)

        assert capabilities.min_baudrate > 0
        assert capabilities.min_baudrate <= capabilities.max_baudrate
        assert capabilities.max_read_size > 0
        assert capabilities.max_write_size > 0
        assert snapshot.component_parameter >= 0
        assert snapshot.component_version >= 0
        assert snapshot.peripheral_id >= 0

    record_evidence(record_property, "dut")
    output = record_result(
        et_artifact_dir,
        "uart_p0_001_selected_instance_identity_and_caps",
        features=int(capabilities.features),
        min_baudrate=capabilities.min_baudrate,
        max_baudrate=capabilities.max_baudrate,
        max_read_size=capabilities.max_read_size,
        max_write_size=capabilities.max_write_size,
        component_parameter=snapshot.component_parameter,
        component_version=snapshot.component_version,
        peripheral_id=snapshot.peripheral_id,
        scratch=snapshot.scratch,
    )
    record_property("uart_result", str(output))


# 测试 Feature：
# UART 软件复位、默认配置和实例生命周期。
#
# 测试方法：
# 1. 初始化非默认帧格式，读取快照后执行软件复位并重新初始化默认 8N1。
# 2. 检查身份与 FIFO 状态，再执行一字节内部回环收发。
#
# 通过条件：
# 1. 软件复位前后组件身份不变且 TX/RX FIFO 为空。
# 2. 恢复后的发送数、接收数和数据均与请求一致。
def test_uart_p0_002_reset_and_default_config(
    uart_dut_handle,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 所有权：初始化成功后，Case 退出时必须恢复 UART、Capture 和回环状态。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dut_handle.instance_id)
    resource_driver.reset()

    initialized = False
    loopback_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if loopback_enabled:
            actions.append(("UART capture cancel", uart_dut_handle.capture_cancel))
            actions.append(("UART loopback disable", lambda: uart_dut_handle.loopback_set(False)))
        if initialized:
            actions.append(("UART deinitialize", uart_dut_handle.deinitialize))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 配置：先使用非默认 7E2 帧格式建立可被复位的运行状态。
        uart_dut_handle.initialize(
            baudrate=DEFAULT_BAUDRATE,
            data_bits=7,
            stop_bits=2,
            parity=int(UartParity.EVEN),
        )
        initialized = True

        # 观测：软件复位前保存组件身份和 FIFO 状态。
        before = uart_dut_handle.snapshot_get()

        # 复位：执行软件复位，再显式恢复默认 8N1 配置。
        uart_dut_handle.software_reset()
        uart_dut_handle.initialize(
            baudrate=DEFAULT_BAUDRATE,
            data_bits=8,
            stop_bits=1,
            parity=int(UartParity.NONE),
        )

        # 观测：读取复位并重新初始化后的组件身份和 FIFO 状态。
        after = uart_dut_handle.snapshot_get()

        identity_stable = (
            after.component_parameter == before.component_parameter
            and after.component_version == before.component_version
            and after.peripheral_id == before.peripheral_id
        )
        record_property("identity_stable", identity_stable)
        record_observation(
            record_property,
            key="final_tx_fifo_level",
            value=after.tx_fifo_level,
            source="dut",
            endpoint="UART_FIFO.TX_LEVEL",
        )
        record_observation(
            record_property,
            key="final_rx_fifo_level",
            value=after.rx_fifo_level,
            source="dut",
            endpoint="UART_FIFO.RX_LEVEL",
        )

        # 断言：复位不得改变组件身份，复位后的 FIFO 必须为空。
        assert after.component_parameter == before.component_parameter
        assert after.component_version == before.component_version
        assert after.peripheral_id == before.peripheral_id
        assert after.tx_fifo_level == 0
        assert after.rx_fifo_level == 0

        # 准备：构造最小一字节确定性 Payload。
        payload = bytes(make_pattern(1))

        # 配置：开启内部回环；成功后由统一清理边界关闭回环并取消 Capture。
        uart_dut_handle.loopback_set(True)
        loopback_enabled = True

        # 接收：Capture 必须先于发送启动，避免丢失首字节。
        uart_dut_handle.capture_start(len(payload))

        # 发送：写入一字节 Payload，并使用原有有界轮询预算。
        transferred = uart_dut_handle.write(payload, max_polls=DEFAULT_MAX_POLLS)

        # 观测：等待最小数据路径产生完整接收结果。
        capture = uart_dut_handle.capture_wait(len(payload))

        record_observation(
            record_property,
            key="recovery_actual_data",
            value=capture.data,
            source="dut",
            endpoint="UART_CAPTURE.DATA",
        )

        # 断言：最小数据路径必须完整且逐字节一致。
        assert transferred == len(payload)
        assert capture.received == len(payload)
        assert capture.data == payload

    # 记录：保存复位前后身份、FIFO 和最小数据路径事实。
    record_evidence(record_property, "dut")
    output = record_result(
        et_artifact_dir,
        "uart_p0_002_reset_and_default_config",
        before_identity={
            "component_parameter": before.component_parameter,
            "component_version": before.component_version,
            "peripheral_id": before.peripheral_id,
        },
        after_identity={
            "component_parameter": after.component_parameter,
            "component_version": after.component_version,
            "peripheral_id": after.peripheral_id,
        },
        after_fifo={"tx": after.tx_fifo_level, "rx": after.rx_fifo_level},
        transfer={
            "tx_requested": len(payload),
            "tx_completed": transferred,
            "rx_expected": len(payload),
            "rx_completed": capture.received,
            "data_match": capture.data == payload,
        },
    )
    record_property("uart_result", str(output))


# =============================================================================
# 基本数据通路
# =============================================================================


# 测试 Feature：
# UART 内部回环的基本发送、接收和回环开关。
#
# 测试方法：
# 1. 初始化默认 8N1，依次发送 1、16、17、64 字节模式数据。
# 2. 每轮显式开启回环、启动 Capture、发送并等待接收完成。
#
# 通过条件：
# 1. 每个长度的发送完成数等于请求长度。
# 2. 每个长度的接收数据逐字节等于发送数据。
def test_uart_p0_003_internal_loopback_basic(
    uart_dut_handle,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 准备：保存每个长度的传输事实，最终统一写入结果文件。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dut_handle.instance_id)
    resource_driver.reset()

    transfers = []

    # 所有权：初始化成功后，Case 退出时必须取消 Capture、关闭回环并反初始化。
    initialized = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        if not initialized:
            return ()
        return (
            ("UART capture cancel", uart_dut_handle.capture_cancel),
            ("UART loopback disable", lambda: uart_dut_handle.loopback_set(False)),
            ("UART deinitialize", uart_dut_handle.deinitialize),
        )

    with case_cleanup_scope(cleanup_actions):
        # 配置：初始化 UART 为默认 8N1，后续各轮复用同一实例。
        uart_dut_handle.initialize(
            baudrate=DEFAULT_BAUDRATE,
            data_bits=8,
            stop_bits=1,
            parity=0,
        )
        initialized = True

        # 边界：依次覆盖最小长度、FIFO 边界和跨 FIFO 场景。
        for length in (1, 16, 17, 64):
            # 准备：每个长度使用不同种子的确定性 Payload。
            payload = bytes(make_pattern(length, seed=length))

            # 配置：每轮显式确认内部回环开启，保持原有硬件命令顺序。
            uart_dut_handle.loopback_set(True)

            # 接收：每轮重新启动 Capture，避免复用上一轮状态。
            uart_dut_handle.capture_start(len(payload))

            # 发送：写入本轮完整 Payload，并使用原有有界轮询预算。
            transferred = uart_dut_handle.write(payload, max_polls=DEFAULT_MAX_POLLS)

            # 观测：等待当前长度的数据全部返回。
            capture = uart_dut_handle.capture_wait(len(payload))

            record_observation(
                record_property,
                key="actual_capture_data",
                value=capture.data,
                source="dut",
                endpoint="UART_CAPTURE.DATA",
            )
            record_property("tx_completed", transferred)
            record_property("rx_completed", capture.received)

            # 断言：本轮发送数、接收数和数据必须全部匹配。
            assert transferred == len(payload)
            assert capture.received == len(payload)
            assert capture.data == payload

            # 记录准备：保存本轮确定性事实，最终统一写入结构化附件。
            transfers.append(
                {
                    "length": length,
                    "tx_requested": length,
                    "tx_completed": transferred,
                    "rx_expected": length,
                    "rx_completed": capture.received,
                    "data_match": capture.data == payload,
                }
            )

    # 记录：保存全部长度子项和实际使用的 DUT Evidence。
    record_evidence(record_property, "dut")
    output = record_result(
        et_artifact_dir,
        "uart_p0_003_internal_loopback_basic",
        transfers=transfers,
        last_capture_data=list(capture.data),
    )
    record_property("uart_result", str(output))


# 测试 Feature：
# UART 逻辑 DUT 与 Peer 之间的双向基本收发。
#
# 测试方法：
# 1. DUT 与 Peer 配置相同帧格式，DUT 发送并由 Peer 捕获。
# 2. Peer 使用另一组数据反向发送，由 DUT 捕获。
#
# 通过条件：
# 1. 两个方向的发送完成数和接收数均等于请求长度。
# 2. 两个方向的数据均逐字节一致。
def test_uart_p0_004_paired_bidirectional_basic(
    uart_dut_handle,
    uart_peer_handle,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 所有权：多 Driver 生命周期由 Case 显式记录，清理顺序保持可审核。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dut_handle.instance_id)
    crg_driver.reset(CrgPeripheral.UART, instance=uart_peer_handle.instance_id)
    resource_driver.reset()

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
        # 配置：先初始化 DUT 为默认 8N1 帧格式。
        uart_dut_handle.initialize(
            baudrate=DEFAULT_BAUDRATE,
            data_bits=8,
            stop_bits=1,
            parity=0,
        )
        dut_initialized = True

        # 配置：Peer 使用与 DUT 完全相同的帧格式，保证链路参数一致。
        uart_peer_handle.initialize(
            baudrate=DEFAULT_BAUDRATE,
            data_bits=8,
            stop_bits=1,
            parity=0,
        )
        peer_initialized = True

        # 准备：DUT→Peer 使用固定种子的 64 Byte 确定性 Payload。
        dut_payload = bytes(make_pattern(64, seed=0x21))

        # 接收：Peer Capture 必须先于 DUT 发送启动，避免丢失起始字节。
        uart_peer_handle.capture_start(len(dut_payload))
        peer_capture_started = True

        # 发送：DUT 写入完整 Payload，并使用原有有界轮询预算。
        dut_transferred = uart_dut_handle.write(dut_payload, max_polls=DEFAULT_MAX_POLLS)

        # 观测：等待 Peer 接收 DUT 发出的全部数据。
        peer_capture = uart_peer_handle.capture_wait(len(dut_payload))

        # 准备：Peer→DUT 切换方向，并使用不同种子的确定性 Payload。
        peer_payload = bytes(make_pattern(64, seed=0xA1))

        # 接收：DUT Capture 必须先于 Peer 发送启动。
        uart_dut_handle.capture_start(len(peer_payload))
        dut_capture_started = True

        # 发送：Peer 写入完整 Payload，并使用相同有界轮询预算。
        peer_transferred = uart_peer_handle.write(peer_payload, max_polls=DEFAULT_MAX_POLLS)

        # 观测：等待 DUT 接收 Peer 发出的全部数据。
        dut_capture = uart_dut_handle.capture_wait(len(peer_payload))

        record_observation(
            record_property,
            key="peer_rx_data",
            value=peer_capture.data,
            source="peer",
            device_id="peer",
            endpoint="PEER_UART.RX_CAPTURE",
        )
        record_observation(
            record_property,
            key="dut_rx_data",
            value=dut_capture.data,
            source="dut",
            endpoint="UART_CAPTURE.DATA",
        )
        record_property("dut_to_peer_match", peer_capture.data == dut_payload)
        record_property("peer_to_dut_match", dut_capture.data == peer_payload)

        # 断言：两个方向的发送数、接收数和数据必须全部匹配。
        assert dut_transferred == len(dut_payload)
        assert peer_capture.received == len(dut_payload)
        assert peer_capture.data == dut_payload
        assert peer_transferred == len(peer_payload)
        assert dut_capture.received == len(peer_payload)
        assert dut_capture.data == peer_payload

    # 记录：保存双向传输事实和实际使用的 DUT/Peer Evidence。
    record_evidence(record_property, "dut", "peer")
    output = record_result(
        et_artifact_dir,
        "uart_p0_004_paired_bidirectional_basic",
        dut_to_peer={
            "tx_requested": len(dut_payload),
            "tx_completed": dut_transferred,
            "rx_expected": len(dut_payload),
            "rx_completed": peer_capture.received,
            "data_match": peer_capture.data == dut_payload,
        },
        peer_to_dut={
            "tx_requested": len(peer_payload),
            "tx_completed": peer_transferred,
            "rx_expected": len(peer_payload),
            "rx_completed": dut_capture.received,
            "data_match": dut_capture.data == peer_payload,
        },
    )
    record_property("uart_result", str(output))
