# Formal Case测试模块。
#
# 职责：按测试等级承载可执行Feature流程、证据和最终断言。
# 边界：不直接调用Codec、Transport或芯片专有接口。
# 依赖：仅依赖Fixture、公共Driver及Case本地Support。

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction, run_cleanup
from ...core.errors import OperationBusy
from ...drivers.crg import CrgPeripheral
from ...drivers.uart import UartErrorFlag, UartIrqSource, UartParity, UartStopBits
from ...scheduling.run_context import record_evidence, record_observation
from ..case_cleanup import case_cleanup_scope
from .uart_helpers import DEFAULT_BAUDRATE, DEFAULT_MAX_POLLS, make_pattern, record_result

pytestmark = [pytest.mark.hardware, pytest.mark.ip("uart")]


# Track only the cross-UART states acquired by one matrix iteration.
@dataclass(slots=True)
class _PairOwnership:
    dut_initialized: bool = False
    peer_initialized: bool = False
    dut_capture_started: bool = False
    peer_capture_started: bool = False


# Build evidence only; hardware execution and assertions stay in the Case.
def _transfer_evidence(payload: bytes, transferred: int, capture) -> dict[str, object]:
    return {
        "tx_requested": len(payload),
        "tx_completed": transferred,
        "rx_expected": len(payload),
        "rx_completed": capture.received,
        "data_match": capture.data == payload,
    }


# Calculate IRQ deltas only; final judgment stays in the Case.
def _irq_observation(baseline, state, source: UartIrqSource) -> tuple[int, int, bool]:
    event_delta = state.event_count - baseline.event_count
    fault_delta = state.fault_count - baseline.fault_count
    source_observed = bool(state.pending_mask & int(source) or state.active_mask & int(source))
    return event_delta, fault_delta, source_observed


# =============================================================================
# 实例隔离
# =============================================================================


# 测试 Feature：
# DUT UART 实例隔离和独立复位。
#
# 测试方法：
# 1. 保存 Peer 快照，只复位并重新初始化 DUT，再执行 DUT 内部回环。
# 2. 由 Peer 向 DUT 发送数据并再次读取 Peer 快照。
#
# 通过条件：
# 1. DUT 内部回环和 Peer→DUT 传输均完整一致。
# 2. Peer 的组件身份字段在 DUT 复位前后保持不变。
def test_uart_p1_001_dut_instance_isolation(
    uart_dut_handle,
    uart_peer_handle,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 所有权：按实际获得状态登记 DUT、Peer、Capture 和回环清理责任。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dut_handle.instance_id)
    crg_driver.reset(CrgPeripheral.UART, instance=uart_peer_handle.instance_id)
    resource_driver.reset()

    dut_initialized = False
    peer_initialized = False
    capture_cleanup_owned = False
    loopback_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if loopback_enabled:
            actions.append(
                ("UART DUT loopback disable", lambda: uart_dut_handle.loopback_set(False))
            )
        if capture_cleanup_owned:
            actions.append(("UART DUT capture cancel", uart_dut_handle.capture_cancel))
        if dut_initialized:
            actions.append(("UART DUT deinitialize", uart_dut_handle.deinitialize))
        if peer_initialized:
            actions.append(("UART peer deinitialize", uart_peer_handle.deinitialize))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 配置：初始化 DUT；成功后建立与原 Capture Scope 等价的清理责任。
        uart_dut_handle.initialize(baudrate=DEFAULT_BAUDRATE)
        dut_initialized = True
        capture_cleanup_owned = True

        # 配置：Peer 使用与 DUT 相同的默认帧格式。
        uart_peer_handle.initialize(
            baudrate=DEFAULT_BAUDRATE,
            data_bits=8,
            stop_bits=1,
            parity=0,
        )
        peer_initialized = True

        # 观测：保存 Peer 身份，后续验证 DUT 复位不会影响 Peer。
        peer_before = uart_peer_handle.snapshot_get()

        # 复位：仅复位 DUT，并显式恢复 DUT 默认配置。
        uart_dut_handle.software_reset()
        uart_dut_handle.initialize(baudrate=DEFAULT_BAUDRATE)

        # 准备：构造 DUT 内部回环的确定性 Payload。
        loopback_payload = bytes(make_pattern(8))

        # 配置：开启 DUT 内部回环，并登记异常退出时的关闭责任。
        uart_dut_handle.loopback_set(True)
        loopback_enabled = True

        # 接收：Capture 必须先于 DUT 发送启动。
        uart_dut_handle.capture_start(len(loopback_payload))

        # 发送：DUT 写入完整 Payload。
        loopback_tx = uart_dut_handle.write(
            loopback_payload,
            max_polls=DEFAULT_MAX_POLLS,
        )

        # 观测：等待 DUT 内部回环接收完成。
        loopback_capture = uart_dut_handle.capture_wait(len(loopback_payload))

        # 断言：DUT 复位后的最小数据路径必须完整恢复。
        assert loopback_tx == len(loopback_payload)
        assert loopback_capture.received == len(loopback_payload)
        assert loopback_capture.data == loopback_payload

        # 配置：按原命令顺序关闭内部回环，再测试独立的 Peer→DUT 路径。
        uart_dut_handle.loopback_set(False)
        loopback_enabled = False

        # 准备：Peer→DUT 使用另一组确定性 Payload。
        peer_payload = bytes(make_pattern(4, seed=0x18))

        # 接收：DUT Capture 先于 Peer 发送启动。
        uart_dut_handle.capture_start(len(peer_payload))

        # 发送：Peer 向 DUT 写入完整 Payload。
        peer_tx = uart_peer_handle.write(peer_payload, max_polls=DEFAULT_MAX_POLLS)

        # 观测：等待 DUT 接收完成，并读取 Peer 测试后的身份。
        peer_capture = uart_dut_handle.capture_wait(len(peer_payload))
        peer_after = uart_peer_handle.snapshot_get()

        peer_identity_unchanged = (
            peer_after.component_parameter == peer_before.component_parameter
            and peer_after.component_version == peer_before.component_version
            and peer_after.peripheral_id == peer_before.peripheral_id
        )
        record_observation(
            record_property,
            key="peer_component_parameter_before",
            value=peer_before.component_parameter,
            source="peer",
            device_id="peer",
            endpoint="UART_COMPONENT.COMPONENT_PARAMETER",
        )
        record_observation(
            record_property,
            key="peer_component_parameter_after",
            value=peer_after.component_parameter,
            source="peer",
            device_id="peer",
            endpoint="UART_COMPONENT.COMPONENT_PARAMETER",
        )
        record_property("peer_identity_unchanged", peer_identity_unchanged)
        record_observation(
            record_property,
            key="peer_to_dut_actual_data",
            value=peer_capture.data,
            source="dut",
            endpoint="UART_CAPTURE.DATA",
        )

        # 断言：Peer→DUT 数据必须一致，Peer 身份不得受 DUT 复位影响。
        assert peer_tx == len(peer_payload)
        assert peer_capture.received == len(peer_payload)
        assert peer_capture.data == peer_payload
        assert (
            peer_after.component_parameter,
            peer_after.component_version,
            peer_after.peripheral_id,
        ) == (
            peer_before.component_parameter,
            peer_before.component_version,
            peer_before.peripheral_id,
        )

    record_evidence(record_property, "dut", "peer")
    output = record_result(
        et_artifact_dir,
        "uart_p1_001_dut_instance_isolation",
        transfer=_transfer_evidence(loopback_payload, loopback_tx, loopback_capture),
        peer_transfer=_transfer_evidence(peer_payload, peer_tx, peer_capture),
        peer_identity_unchanged=True,
    )
    record_property("uart_result", str(output))


# =============================================================================
# 基础收发中断
# =============================================================================


# 测试 Feature：
# UART RX data available 中断和事件计数。
#
# 测试方法：
# 1. 使能 RX_READY 中断并读取基线，随后开启回环和 Capture。
# 2. 发送已知数据，读取 IRQ 状态并比较本次事件增量和来源。
#
# 通过条件：
# 1. 数据完整一致且 fault_count 不增加。
# 2. event_count 增加且 RX_READY 来源被观测到。
def test_uart_p1_002_rx_data_available_irq(
    uart_dut_handle,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 所有权：只为已经成功获得的资源登记清理动作。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dut_handle.instance_id)
    resource_driver.reset()

    initialized = False
    loopback_cleanup_owned = False
    irq_enabled = False
    capture_cleanup_owned = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if capture_cleanup_owned:
            actions.append(("UART DUT capture cancel", uart_dut_handle.capture_cancel))
        if irq_enabled:
            actions.append(
                (
                    "UART DUT IRQ disable RX_READY",
                    lambda: uart_dut_handle.irq_config(
                        UartIrqSource.RX_READY,
                        False,
                        priority=4,
                    ),
                )
            )
        if loopback_cleanup_owned:
            actions.append(
                ("UART DUT loopback disable", lambda: uart_dut_handle.loopback_set(False))
            )
        if initialized:
            actions.append(("UART DUT deinitialize", uart_dut_handle.deinitialize))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 配置：初始化 DUT，并按原生命周期顺序取得后续清理责任。
        uart_dut_handle.initialize(
            baudrate=DEFAULT_BAUDRATE,
            data_bits=8,
            stop_bits=1,
            parity=0,
        )
        initialized = True
        loopback_cleanup_owned = True

        # 配置：使能 RX_READY 中断；成功后登记对应关闭动作。
        uart_dut_handle.irq_config(UartIrqSource.RX_READY, True, priority=4)
        irq_enabled = True
        capture_cleanup_owned = True

        # 观测：读取激励前的 IRQ 计数基线。
        baseline = uart_dut_handle.irq_state_get()

        # 准备：构造确定性的短 Payload。
        payload = bytes(make_pattern(4))

        # 配置：开启内部回环。
        uart_dut_handle.loopback_set(True)

        # 接收：Capture 必须先于发送启动。
        uart_dut_handle.capture_start(len(payload))

        # 发送：写入完整 Payload。
        transferred = uart_dut_handle.write(payload, max_polls=DEFAULT_MAX_POLLS)

        # 观测：等待回环数据并读取 IRQ 状态。
        capture = uart_dut_handle.capture_wait(len(payload))
        state = uart_dut_handle.irq_state_get()

        # 分析：计算本轮 IRQ 事件、故障和来源变化。
        event_delta, fault_delta, source_observed = _irq_observation(
            baseline,
            state,
            UartIrqSource.RX_READY,
        )

        record_observation(
            record_property,
            key="rx_actual_data",
            value=capture.data,
            source="dut",
            endpoint="UART_CAPTURE.DATA",
        )
        record_property("irq_pending_mask", state.pending_mask)
        record_property("event_count_delta", event_delta)
        record_property("fault_count_delta", fault_delta)
        record_property("source_observed", source_observed)

        # 断言：数据路径与 RX_READY 中断事实必须同时成立。
        assert transferred == len(payload)
        assert capture.received == len(payload)
        assert capture.data == payload
        assert fault_delta == 0
        assert event_delta > 0
        assert source_observed

    record_evidence(record_property, "dut")
    output = record_result(
        et_artifact_dir,
        "uart_p1_002_rx_data_available_irq",
        transfer=_transfer_evidence(payload, transferred, capture),
        irq_state=asdict(state),
        event_count_delta=event_delta,
    )
    record_property("uart_result", str(output))


# 测试 Feature：
# UART TX empty 中断在发送完成阶段的触发和关闭。
#
# 测试方法：
# 1. 先读取 IRQ 基线，再使能 TX_READY，开启回环并发送短数据。
# 2. 读取 IRQ 状态后显式关闭 TX_READY，比较事件增量和来源。
#
# 通过条件：
# 1. 数据完整一致且 fault_count 不增加。
# 2. event_count 增加且 TX_READY 来源被观测到。
def test_uart_p1_003_tx_empty_irq(
    uart_dut_handle,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 配置：初始化 DUT；TX_READY、回环和 Capture 由 Case 显式清理。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dut_handle.instance_id)
    resource_driver.reset()

    uart_dut_handle.initialize(
        baudrate=DEFAULT_BAUDRATE,
        data_bits=8,
        stop_bits=1,
        parity=0,
    )

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        return (
            ("UART DUT capture cancel", uart_dut_handle.capture_cancel),
            (
                "UART DUT IRQ disable TX_READY",
                lambda: uart_dut_handle.irq_config(
                    UartIrqSource.TX_READY,
                    False,
                    priority=4,
                ),
            ),
            ("UART DUT loopback disable", lambda: uart_dut_handle.loopback_set(False)),
            ("UART DUT deinitialize", uart_dut_handle.deinitialize),
        )

    with case_cleanup_scope(cleanup_actions):
        # 观测：读取发送前的 IRQ 计数基线。
        baseline = uart_dut_handle.irq_state_get()

        # 配置：使能 TX_READY 中断。
        uart_dut_handle.irq_config(UartIrqSource.TX_READY, True, priority=4)

        # 准备：构造确定性的短 Payload。
        payload = bytes(make_pattern(8, seed=0x52))

        # 配置：开启内部回环。
        uart_dut_handle.loopback_set(True)

        # 接收：Capture 必须先于发送启动。
        uart_dut_handle.capture_start(len(payload))

        # 发送：写入完整 Payload。
        transferred = uart_dut_handle.write(payload, max_polls=DEFAULT_MAX_POLLS)

        # 观测：等待回环数据并读取 IRQ 状态。
        capture = uart_dut_handle.capture_wait(len(payload))
        state = uart_dut_handle.irq_state_get()

        # 配置：按原命令顺序显式关闭 TX_READY。
        uart_dut_handle.irq_config(UartIrqSource.TX_READY, False, priority=4)

        # 分析：计算本轮 IRQ 事件、故障和来源变化。
        event_delta, fault_delta, source_observed = _irq_observation(
            baseline,
            state,
            UartIrqSource.TX_READY,
        )

        record_observation(
            record_property,
            key="tx_actual_data",
            value=capture.data,
            source="dut",
            endpoint="UART_CAPTURE.DATA",
        )
        record_property("irq_pending_mask", state.pending_mask)
        record_property("event_count_delta", event_delta)
        record_property("fault_count_delta", fault_delta)
        record_property("source_observed", source_observed)

        # 断言：数据路径与 TX_READY 中断事实必须同时成立。
        assert transferred == len(payload)
        assert capture.received == len(payload)
        assert capture.data == payload
        assert fault_delta == 0
        assert event_delta > 0
        assert source_observed

    record_evidence(record_property, "dut")
    output = record_result(
        et_artifact_dir,
        "uart_p1_003_tx_empty_irq",
        transfer=_transfer_evidence(payload, transferred, capture),
        irq_state=asdict(state),
        event_count_delta=event_delta,
    )
    record_property("uart_result", str(output))


# =============================================================================
# FIFO 与超时中断
# =============================================================================


# 测试 Feature：
# UART RX FIFO 阈值中断边界。
#
# 测试方法：
# 1. 逐阈值发送threshold-1负对照；若有数据先由Driver read_exact确认数据已真实到达，再读取IRQ session。
# 2. 重新建立基线后发送threshold正对照，并由Driver capture_wait等待完整数据再判断RX_READY边界。
#
# 通过条件：
# 1. 每个阈值的数据完整一致且无新增 IRQ fault。
# 2. 每项均产生事件增量并观测到 RX_READY 来源。
def test_uart_p1_004_rx_fifo_threshold_irq(
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

    results = []
    initialized = False
    irq_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if irq_enabled:
            actions.append(
                (
                    "UART DUT IRQ disable RX_READY",
                    lambda: uart_dut_handle.irq_config(UartIrqSource.RX_READY, False, priority=4),
                )
            )
        if initialized:
            actions.extend(
                (
                    ("UART DUT capture cancel", uart_dut_handle.capture_cancel),
                    ("UART DUT loopback disable", lambda: uart_dut_handle.loopback_set(False)),
                    ("UART DUT deinitialize", uart_dut_handle.deinitialize),
                )
            )
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        uart_dut_handle.initialize(baudrate=DEFAULT_BAUDRATE, data_bits=8, stop_bits=1, parity=0)
        initialized = True
        uart_dut_handle.loopback_set(True)

        # 遍历：覆盖本Case声明的矩阵/边界子项，并保持每个子项独立可定位。
        for threshold in (1, 4, 8, 14):
            uart_dut_handle.fifo_config(rx_threshold=threshold, tx_threshold=0)
            uart_dut_handle.irq_config(UartIrqSource.RX_READY, True, priority=4)
            irq_enabled = True
            below_baseline = uart_dut_handle.irq_state_get()
            below_payload = (
                bytes(make_pattern(threshold - 1, seed=0x30 + threshold)) if threshold > 1 else b""
            )
            below_tx = 0
            below_data = b""
            if below_payload:
                # 低于阈值的数据最终会形成 Character Timeout。先启动 Capture，
                # 让固件 ISR 在超时到来时读取 RBR，避免 RX level 中断持续占用 CPU。
                uart_dut_handle.capture_start(len(below_payload))
                below_tx = uart_dut_handle.write(below_payload, max_polls=DEFAULT_MAX_POLLS)
                below_data = uart_dut_handle.capture_wait(len(below_payload)).data
            below_state = uart_dut_handle.irq_state_get()
            below_event_delta, below_fault_delta, below_source = _irq_observation(
                below_baseline, below_state, UartIrqSource.RX_READY
            )

            uart_dut_handle.irq_config(UartIrqSource.RX_READY, False, priority=4)
            irq_enabled = False
            uart_dut_handle.irq_config(UartIrqSource.RX_READY, True, priority=4)
            irq_enabled = True
            at_baseline = uart_dut_handle.irq_state_get()
            at_payload = bytes(make_pattern(threshold, seed=0x60 + threshold))
            uart_dut_handle.capture_start(len(at_payload))
            at_tx = uart_dut_handle.write(at_payload, max_polls=DEFAULT_MAX_POLLS)
            at_capture = uart_dut_handle.capture_wait(len(at_payload))
            at_state = uart_dut_handle.irq_state_get()
            at_event_delta, at_fault_delta, at_source = _irq_observation(
                at_baseline, at_state, UartIrqSource.RX_READY
            )

            record_property("below_event_delta", below_event_delta)
            record_property("below_fault_count_delta", below_fault_delta)
            record_property("below_source_observed", below_source)
            record_property("at_event_delta", at_event_delta)
            record_property("at_source_observed", at_source)
            record_observation(
                record_property,
                key="actual_capture_data",
                value=at_capture.data,
                source="dut",
                endpoint="UART_CAPTURE.DATA",
            )
            record_property("fault_count_delta", at_fault_delta)

            assert below_tx == len(below_payload)
            assert below_data == below_payload
            assert below_fault_delta == 0
            assert below_event_delta == 0
            assert not below_source
            assert at_tx == len(at_payload)
            assert at_capture.received == len(at_payload)
            assert at_capture.data == at_payload
            assert at_fault_delta == 0
            assert at_event_delta > 0
            assert at_source

            results.append(
                {
                    "threshold": threshold,
                    "below_length": len(below_payload),
                    "below_event_delta": below_event_delta,
                    "at_event_delta": at_event_delta,
                    "data_match": at_capture.data == at_payload,
                }
            )
            uart_dut_handle.irq_config(UartIrqSource.RX_READY, False, priority=4)
            irq_enabled = False

    record_property("threshold_count", len(results))
    record_property(
        "all_threshold_boundaries_valid",
        all(item["below_event_delta"] == 0 and item["at_event_delta"] > 0 for item in results),
    )
    record_evidence(record_property, "dut")
    output = record_result(
        et_artifact_dir,
        "uart_p1_004_rx_fifo_threshold_irq",
        results=results,
        last_capture_data=list(at_capture.data),
    )
    record_property("uart_result", str(output))


# 测试 Feature：
# UART TX FIFO 阈值中断边界。
#
# 测试方法：
# 1. 逐阈值Halt TX并预装同一短Payload，读取TX FIFO level建立明确的高于阈值负对照。
# 2. 使能TX_READY后立即读取held session，再Resume并由Driver capture_wait等待同一Payload完成，比较终态FIFO/IRQ。
#
# 通过条件：
# 1. 每个阈值的数据完整一致且无新增 IRQ fault。
# 2. 每项均产生事件增量并观测到 TX_READY 来源。
def test_uart_p1_005_tx_fifo_threshold_irq(
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

    results = []
    initialized = False
    irq_enabled = False
    halt_owned = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if halt_owned:
            actions.append(("UART DUT halt release", lambda: uart_dut_handle.halt_set(False)))
        if irq_enabled:
            actions.append(
                (
                    "UART DUT IRQ disable TX_READY",
                    lambda: uart_dut_handle.irq_config(UartIrqSource.TX_READY, False, priority=4),
                )
            )
        if initialized:
            actions.extend(
                (
                    ("UART DUT capture cancel", uart_dut_handle.capture_cancel),
                    ("UART DUT loopback disable", lambda: uart_dut_handle.loopback_set(False)),
                    ("UART DUT deinitialize", uart_dut_handle.deinitialize),
                )
            )
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        uart_dut_handle.initialize(baudrate=DEFAULT_BAUDRATE, data_bits=8, stop_bits=1, parity=0)
        initialized = True
        uart_dut_handle.loopback_set(True)

        # 遍历：覆盖本Case声明的矩阵/边界子项，并保持每个子项独立可定位。
        for threshold in (0, 2, 4, 8):
            uart_dut_handle.fifo_config(tx_threshold=threshold, rx_threshold=1)
            payload = bytes(make_pattern(12, seed=0x70 + threshold))
            uart_dut_handle.capture_start(len(payload))
            uart_dut_handle.halt_set(True)
            halt_owned = True
            accepted = uart_dut_handle.write_partial(payload)
            halted_status = uart_dut_handle.status_get()

            baseline = uart_dut_handle.irq_state_get()
            uart_dut_handle.irq_config(UartIrqSource.TX_READY, True, priority=4)
            irq_enabled = True
            held_state = uart_dut_handle.irq_state_get()
            held_event_delta, held_fault_delta, held_source = _irq_observation(
                baseline, held_state, UartIrqSource.TX_READY
            )

            uart_dut_handle.halt_set(False)
            halt_owned = False
            capture = uart_dut_handle.capture_wait(len(payload))
            resumed_status = uart_dut_handle.status_get()
            resumed_state = uart_dut_handle.irq_state_get()
            resumed_event_delta, resumed_fault_delta, resumed_source = _irq_observation(
                baseline, resumed_state, UartIrqSource.TX_READY
            )

            record_observation(
                record_property,
                key="halted_tx_fifo_level",
                value=halted_status.tx_fifo_level,
                source="dut",
                endpoint="UART_FIFO.TX_LEVEL",
            )
            record_observation(
                record_property,
                key="resumed_tx_fifo_level",
                value=resumed_status.tx_fifo_level,
                source="dut",
                endpoint="UART_FIFO.TX_LEVEL",
            )
            record_property("held_event_delta", held_event_delta)
            record_property("held_fault_count_delta", held_fault_delta)
            record_property("held_source_observed", held_source)
            record_property("resumed_event_delta", resumed_event_delta)
            record_property("resumed_source_observed", resumed_source)
            record_observation(
                record_property,
                key="actual_capture_data",
                value=capture.data,
                source="dut",
                endpoint="UART_CAPTURE.DATA",
            )
            record_property("fault_count_delta", resumed_fault_delta)

            assert accepted == len(payload)
            assert halted_status.tx_fifo_level > threshold
            assert resumed_status.tx_fifo_level <= threshold
            assert held_fault_delta == 0
            assert held_event_delta == 0
            assert not held_source
            assert capture.received == len(payload)
            assert capture.data == payload
            assert resumed_fault_delta == 0
            assert resumed_event_delta > 0
            assert resumed_source

            results.append(
                {
                    "threshold": threshold,
                    "halted_tx_fifo_level": halted_status.tx_fifo_level,
                    "held_event_delta": held_event_delta,
                    "resumed_event_delta": resumed_event_delta,
                    "data_match": capture.data == payload,
                }
            )
            uart_dut_handle.irq_config(UartIrqSource.TX_READY, False, priority=4)
            irq_enabled = False

    record_property("threshold_count", len(results))
    record_property(
        "all_resume_events_observed", all(item["resumed_event_delta"] > 0 for item in results)
    )
    record_evidence(record_property, "dut")
    output = record_result(
        et_artifact_dir,
        "uart_p1_005_tx_fifo_threshold_irq",
        results=results,
        last_capture_data=list(capture.data),
    )
    record_property("uart_result", str(output))


# 测试 Feature：
# UART character timeout 中断和低于阈值数据的收取。
#
# 测试方法：
# 1. RX 阈值设为 14，使能 CHARACTER_TIMEOUT 后读取 IRQ 基线。
# 2. 回环发送 2 字节并读取 Capture 与 IRQ 状态。
#
# 通过条件：
# 1. 两字节数据完整一致且无新增 IRQ fault。
# 2. event_count 增加并观测到 CHARACTER_TIMEOUT 来源。
def test_uart_p1_006_character_timeout_irq(
    uart_dut_handle,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 配置：提高RX阈值，使短帧只能通过Character Timeout形成接收事件。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dut_handle.instance_id)
    resource_driver.reset()

    uart_dut_handle.initialize(
        baudrate=DEFAULT_BAUDRATE,
        data_bits=8,
        stop_bits=1,
        parity=0,
    )
    uart_dut_handle.fifo_config(rx_threshold=14, tx_threshold=0)
    initialized = True
    loopback_cleanup_owned = True
    irq_enabled = False
    capture_cleanup_owned = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if capture_cleanup_owned:
            actions.append(("UART DUT capture cancel", uart_dut_handle.capture_cancel))
        if irq_enabled:
            actions.append(
                (
                    "UART DUT IRQ disable CHARACTER_TIMEOUT",
                    lambda: uart_dut_handle.irq_config(
                        UartIrqSource.CHARACTER_TIMEOUT,
                        False,
                        priority=4,
                    ),
                )
            )
        if loopback_cleanup_owned:
            actions.append(
                ("UART DUT loopback disable", lambda: uart_dut_handle.loopback_set(False))
            )
        if initialized:
            actions.append(("UART DUT deinitialize", uart_dut_handle.deinitialize))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 配置：使能字符超时中断，并登记异常退出时的关闭责任。
        uart_dut_handle.irq_config(UartIrqSource.CHARACTER_TIMEOUT, True, priority=4)
        irq_enabled = True
        capture_cleanup_owned = True

        # 观测：读取发送前的 IRQ 计数基线。
        baseline = uart_dut_handle.irq_state_get()

        # 准备：使用低于 RX FIFO 阈值的两字节 Payload。
        payload = bytes(make_pattern(2, seed=0x91))

        # 配置：开启内部回环。
        uart_dut_handle.loopback_set(True)

        # 接收：Capture 必须先于发送启动。
        uart_dut_handle.capture_start(len(payload))

        # 发送：写入不足以触发 FIFO 阈值的 Payload。
        transferred = uart_dut_handle.write(payload, max_polls=DEFAULT_MAX_POLLS)

        # 观测：等待数据和 CHARACTER_TIMEOUT 中断事件。
        capture = uart_dut_handle.capture_wait(len(payload))
        state = uart_dut_handle.wait_irq_event(
            UartIrqSource.CHARACTER_TIMEOUT,
            baseline.event_count,
        )

        # 分析：计算本轮中断事件、故障和来源变化。
        event_delta, fault_delta, source_observed = _irq_observation(
            baseline,
            state,
            UartIrqSource.CHARACTER_TIMEOUT,
        )

        record_observation(
            record_property,
            key="timeout_actual_data",
            value=capture.data,
            source="dut",
            endpoint="UART_CAPTURE.DATA",
        )
        record_property("irq_pending_mask", state.pending_mask)
        record_property("event_count_delta", event_delta)
        record_property("fault_count_delta", fault_delta)
        record_property("source_observed", source_observed)

        # 断言：短帧数据与 CHARACTER_TIMEOUT 事件必须同时成立。
        assert transferred == len(payload)
        assert capture.received == len(payload)
        assert capture.data == payload
        assert fault_delta == 0
        assert event_delta > 0
        assert source_observed

    record_evidence(record_property, "dut")
    output = record_result(
        et_artifact_dir,
        "uart_p1_006_character_timeout_irq",
        transfer=_transfer_evidence(payload, transferred, capture),
        irq_state=asdict(state),
        event_count_delta=event_delta,
    )
    record_property("uart_result", str(output))


# =============================================================================
# 错误检测与恢复
# =============================================================================


# 测试 Feature：
# UART 奇偶校验错误检测和恢复。
#
# 测试方法：
# 1. DUT 配 ODD、Peer 配 EVEN，打开 LINE_ERROR 中断并发送失配短帧。
# 2. 验证 PARITY 错误和中断来源后执行既有过渡清理，再以 NONE/NONE 恢复传输。
#
# 通过条件：
# 1. 状态包含 PARITY，LINE_ERROR 事件增加且无 IRQ fault 增量。
# 2. 恢复帧完整一致，过渡清理无失败。
def test_uart_p1_007_parity_error_detection(
    uart_dut_handle,
    uart_peer_handle,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 所有权：Case 显式管理两端初始化、DUT 中断和 Capture 恢复顺序。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dut_handle.instance_id)
    crg_driver.reset(CrgPeripheral.UART, instance=uart_peer_handle.instance_id)
    resource_driver.reset()

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        return (
            ("UART peer deinitialize", uart_peer_handle.deinitialize),
            ("UART DUT capture cancel", uart_dut_handle.capture_cancel),
            (
                "UART DUT IRQ disable LINE_ERROR",
                lambda: uart_dut_handle.irq_config(
                    UartIrqSource.LINE_ERROR,
                    False,
                    priority=4,
                ),
            ),
            ("UART DUT deinitialize", uart_dut_handle.deinitialize),
        )

    with case_cleanup_scope(cleanup_actions):
        # 配置：DUT 使用奇校验，Peer 使用偶校验，形成确定性失配。
        uart_dut_handle.initialize(
            baudrate=DEFAULT_BAUDRATE,
            parity=int(UartParity.ODD),
        )
        uart_peer_handle.initialize(
            baudrate=DEFAULT_BAUDRATE,
            parity=int(UartParity.EVEN),
        )

        # 配置：使能 DUT 的 LINE_ERROR 中断。
        uart_dut_handle.irq_config(UartIrqSource.LINE_ERROR, True, priority=4)

        # 观测：读取失配激励前的 IRQ 基线。
        baseline = uart_dut_handle.irq_state_get()

        # 准备：构造校验失配 Payload。
        mismatch_payload = bytes(make_pattern(4, seed=0xA7))

        # 接收：DUT Capture 必须先于 Peer 发送启动。
        uart_dut_handle.capture_start(len(mismatch_payload))

        # 激励：Peer 使用相反校验方式发送 Payload。
        mismatch_tx = uart_peer_handle.write(
            mismatch_payload,
            max_polls=DEFAULT_MAX_POLLS,
        )

        # 观测：等待失配帧并读取 UART 与 IRQ 状态。
        mismatch_capture = uart_dut_handle.capture_wait(len(mismatch_payload))
        status = uart_dut_handle.status_get()
        irq_state = uart_dut_handle.irq_state_get()
        event_delta, fault_delta, source_observed = _irq_observation(
            baseline,
            irq_state,
            UartIrqSource.LINE_ERROR,
        )

        record_observation(
            record_property,
            key="error_flags",
            value=status.error_flags,
            source="dut",
            endpoint="UART_STATUS.ERROR_FLAGS",
        )
        record_property("irq_pending_mask", irq_state.pending_mask)
        record_property("event_count_delta", event_delta)
        record_property("fault_count_delta", fault_delta)
        record_property("source_observed", source_observed)

        # 断言：必须观测到 Parity Error 与 LINE_ERROR 中断事实。
        assert status.error_flags & int(UartErrorFlag.PARITY)
        assert fault_delta == 0
        assert event_delta > 0
        assert source_observed

        # 过渡清理：先完整退出失配配置，再进入正常帧格式恢复验证。
        transition_failures = run_cleanup(cleanup_actions())
        assert not transition_failures, transition_failures

        # 恢复：两端统一切换为无校验格式。
        uart_dut_handle.initialize(
            baudrate=DEFAULT_BAUDRATE,
            parity=int(UartParity.NONE),
        )
        uart_peer_handle.initialize(
            baudrate=DEFAULT_BAUDRATE,
            parity=int(UartParity.NONE),
        )

        # 准备：构造恢复路径 Payload。
        recovery_payload = bytes(make_pattern(4, seed=0xB7))

        # 接收：DUT Capture 必须先于 Peer 恢复发送启动。
        uart_dut_handle.capture_start(len(recovery_payload))

        # 发送：Peer 写入恢复路径 Payload。
        recovery_tx = uart_peer_handle.write(
            recovery_payload,
            max_polls=DEFAULT_MAX_POLLS,
        )

        # 观测：等待恢复路径接收完成。
        recovery_capture = uart_dut_handle.capture_wait(len(recovery_payload))

        record_observation(
            record_property,
            key="recovery_actual_data",
            value=recovery_capture.data,
            source="dut",
            endpoint="UART_CAPTURE.DATA",
        )

        # 断言：恢复后的数据路径必须完整一致。
        assert recovery_tx == len(recovery_payload)
        assert recovery_capture.received == len(recovery_payload)
        assert recovery_capture.data == recovery_payload

    record_evidence(record_property, "dut", "peer")
    output = record_result(
        et_artifact_dir,
        "uart_p1_007_parity_error_detection",
        mismatch=_transfer_evidence(mismatch_payload, mismatch_tx, mismatch_capture),
        error_flags=status.error_flags,
        event_count_delta=event_delta,
        recovery=_transfer_evidence(recovery_payload, recovery_tx, recovery_capture),
    )
    record_property("uart_result", str(output))


# 测试 Feature：
# UART 停止位失配导致的 framing error 检测和恢复。
#
# 测试方法：
# 1. Bench 声明支持该刺激时，DUT 配 2 stop bits、Peer 配 1 stop bit 并发送失配帧。
# 2. 验证 FRAMING/LINE_ERROR 后执行既有过渡清理，再恢复默认帧格式传输。
#
# 通过条件：
# 1. 状态包含 FRAMING，LINE_ERROR 事件增加且无 IRQ fault 增量。
# 2. 恢复帧完整一致，过渡清理无失败。
def test_uart_p1_008_framing_error_detection(
    uart_dut_handle,
    uart_peer_handle,
    uart_pair_config,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 门禁：先确认 Bench 具备确定性停止位失配刺激，再修改两端 UART 状态。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dut_handle.instance_id)
    crg_driver.reset(CrgPeripheral.UART, instance=uart_peer_handle.instance_id)
    resource_driver.reset()

    if "stop_mismatch_framing" not in uart_pair_config.error_stimuli:
        pytest.skip(
            "blocked_by_board: current TX/RX pair has no deterministic framing-error stimulus"
        )

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        return (
            ("UART peer deinitialize", uart_peer_handle.deinitialize),
            ("UART DUT capture cancel", uart_dut_handle.capture_cancel),
            (
                "UART DUT IRQ disable LINE_ERROR",
                lambda: uart_dut_handle.irq_config(
                    UartIrqSource.LINE_ERROR,
                    False,
                    priority=4,
                ),
            ),
            ("UART DUT deinitialize", uart_dut_handle.deinitialize),
        )

    with case_cleanup_scope(cleanup_actions):
        # 配置：DUT 使用两个停止位，Peer 使用一个停止位。
        uart_dut_handle.initialize(baudrate=DEFAULT_BAUDRATE, stop_bits=2)
        uart_peer_handle.initialize(baudrate=DEFAULT_BAUDRATE, stop_bits=1)

        # 配置：使能 DUT 的 LINE_ERROR 中断。
        uart_dut_handle.irq_config(UartIrqSource.LINE_ERROR, True, priority=4)

        # 观测：读取失配激励前的 IRQ 基线。
        baseline = uart_dut_handle.irq_state_get()

        # 准备：构造停止位失配 Payload。
        mismatch_payload = bytes(make_pattern(4, seed=0xC7))

        # 接收：DUT Capture 必须先于 Peer 发送启动。
        uart_dut_handle.capture_start(len(mismatch_payload))

        # 激励：Peer 使用不同停止位配置发送 Payload。
        mismatch_tx = uart_peer_handle.write(
            mismatch_payload,
            max_polls=DEFAULT_MAX_POLLS,
        )

        # 观测：等待失配帧并读取 UART 与 IRQ 状态。
        mismatch_capture = uart_dut_handle.capture_wait(len(mismatch_payload))
        status = uart_dut_handle.status_get()
        irq_state = uart_dut_handle.irq_state_get()
        event_delta, fault_delta, source_observed = _irq_observation(
            baseline,
            irq_state,
            UartIrqSource.LINE_ERROR,
        )

        record_observation(
            record_property,
            key="error_flags",
            value=status.error_flags,
            source="dut",
            endpoint="UART_STATUS.ERROR_FLAGS",
        )
        record_property("irq_pending_mask", irq_state.pending_mask)
        record_property("event_count_delta", event_delta)
        record_property("fault_count_delta", fault_delta)
        record_property("source_observed", source_observed)

        # 断言：必须观测到 Framing Error 与 LINE_ERROR 中断事实。
        assert status.error_flags & int(UartErrorFlag.FRAMING)
        assert fault_delta == 0
        assert event_delta > 0
        assert source_observed

        # 过渡清理：先完整退出失配配置，再进入默认帧格式恢复验证。
        transition_failures = run_cleanup(cleanup_actions())
        assert not transition_failures, transition_failures

        # 恢复：两端统一恢复默认帧格式。
        uart_dut_handle.initialize(baudrate=DEFAULT_BAUDRATE)
        uart_peer_handle.initialize(baudrate=DEFAULT_BAUDRATE)

        # 准备：构造恢复路径 Payload。
        recovery_payload = bytes(make_pattern(4, seed=0xD7))

        # 接收：DUT Capture 必须先于 Peer 恢复发送启动。
        uart_dut_handle.capture_start(len(recovery_payload))

        # 发送：Peer 写入恢复路径 Payload。
        recovery_tx = uart_peer_handle.write(
            recovery_payload,
            max_polls=DEFAULT_MAX_POLLS,
        )

        # 观测：等待恢复路径接收完成。
        recovery_capture = uart_dut_handle.capture_wait(len(recovery_payload))

        record_observation(
            record_property,
            key="recovery_actual_data",
            value=recovery_capture.data,
            source="dut",
            endpoint="UART_CAPTURE.DATA",
        )

        # 断言：恢复后的数据路径必须完整一致。
        assert recovery_tx == len(recovery_payload)
        assert recovery_capture.received == len(recovery_payload)
        assert recovery_capture.data == recovery_payload

    record_evidence(record_property, "dut", "peer")
    output = record_result(
        et_artifact_dir,
        "uart_p1_008_framing_error_detection",
        mismatch=_transfer_evidence(mismatch_payload, mismatch_tx, mismatch_capture),
        error_flags=status.error_flags,
        event_count_delta=event_delta,
        recovery=_transfer_evidence(recovery_payload, recovery_tx, recovery_capture),
    )
    record_property("uart_result", str(output))


# 测试 Feature：
# UART RX overrun 错误检测和 FIFO 恢复。
#
# 测试方法：
# 1. 开启内部回环和 LINE_ERROR，发送 64 字节但延迟读取以形成接收压力。
# 2. 验证 OVERRUN/LINE_ERROR 后软件复位并执行 8 字节恢复回环。
#
# 通过条件：
# 1. 状态包含 OVERRUN，LINE_ERROR 事件增加且无 IRQ fault 增量。
# 2. 软件复位后的恢复帧完整一致。
def test_uart_p1_009_overrun_error_detection(
    uart_dut_handle,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 所有权：按原生命周期顺序登记 Capture、中断、回环和反初始化责任。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dut_handle.instance_id)
    resource_driver.reset()

    initialized = False
    loopback_cleanup_owned = False
    irq_enabled = False
    capture_cleanup_owned = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if capture_cleanup_owned:
            actions.append(("UART DUT capture cancel", uart_dut_handle.capture_cancel))
        if irq_enabled:
            actions.append(
                (
                    "UART DUT IRQ disable LINE_ERROR",
                    lambda: uart_dut_handle.irq_config(
                        UartIrqSource.LINE_ERROR,
                        False,
                        priority=4,
                    ),
                )
            )
        if loopback_cleanup_owned:
            actions.append(
                ("UART DUT loopback disable", lambda: uart_dut_handle.loopback_set(False))
            )
        if initialized:
            actions.append(("UART DUT deinitialize", uart_dut_handle.deinitialize))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 配置：初始化 DUT。
        uart_dut_handle.initialize(
            baudrate=DEFAULT_BAUDRATE,
            data_bits=8,
            stop_bits=1,
            parity=0,
        )
        initialized = True
        loopback_cleanup_owned = True

        # 配置：使能 LINE_ERROR 中断。
        uart_dut_handle.irq_config(UartIrqSource.LINE_ERROR, True, priority=4)
        irq_enabled = True
        capture_cleanup_owned = True

        # 配置：开启内部回环，为 RX FIFO 压力提供输入。
        uart_dut_handle.loopback_set(True)

        # 观测：读取压力激励前的 IRQ 基线。
        baseline = uart_dut_handle.irq_state_get()

        # 激励：发送 64 字节但不提前启动 Capture，形成受控接收压力。
        sent = uart_dut_handle.write(make_pattern(64, seed=0xE1))

        # 观测：读取错误状态和 IRQ 状态。
        status = uart_dut_handle.status_get()
        state = uart_dut_handle.irq_state_get()

        # 分析：计算 LINE_ERROR 中断事件和故障变化。
        event_delta, fault_delta, source_observed = _irq_observation(
            baseline,
            state,
            UartIrqSource.LINE_ERROR,
        )

        record_observation(
            record_property,
            key="error_flags",
            value=status.error_flags,
            source="dut",
            endpoint="UART_STATUS.ERROR_FLAGS",
        )
        record_property("event_count_delta", event_delta)
        record_property("fault_count_delta", fault_delta)
        record_property("source_observed", source_observed)

        # 断言：必须观测到 Overrun 与对应中断事件。
        assert status.error_flags & int(UartErrorFlag.OVERRUN)
        assert fault_delta == 0
        assert event_delta > 0
        assert source_observed

        # 恢复：复位并重新初始化 DUT 数据路径。
        uart_dut_handle.software_reset()
        uart_dut_handle.initialize(baudrate=DEFAULT_BAUDRATE)

        # 准备：构造恢复路径 Payload。
        recovery_payload = bytes(make_pattern(8, seed=0xE2))

        # 配置：复位后重新开启内部回环。
        uart_dut_handle.loopback_set(True)

        # 接收：Capture 必须先于恢复发送启动。
        uart_dut_handle.capture_start(len(recovery_payload))

        # 发送：写入恢复路径 Payload。
        recovery_tx = uart_dut_handle.write(
            recovery_payload,
            max_polls=DEFAULT_MAX_POLLS,
        )

        # 观测：等待恢复路径接收完成。
        recovery_capture = uart_dut_handle.capture_wait(len(recovery_payload))

        record_observation(
            record_property,
            key="recovery_actual_data",
            value=recovery_capture.data,
            source="dut",
            endpoint="UART_CAPTURE.DATA",
        )

        # 断言：复位后的 UART 数据路径必须完整恢复。
        assert recovery_tx == len(recovery_payload)
        assert recovery_capture.received == len(recovery_payload)
        assert recovery_capture.data == recovery_payload

    record_evidence(record_property, "dut")
    output = record_result(
        et_artifact_dir,
        "uart_p1_009_overrun_error_detection",
        tx_completed=sent,
        error_flags=status.error_flags,
        event_count_delta=event_delta,
        recovery=_transfer_evidence(recovery_payload, recovery_tx, recovery_capture),
    )
    record_property("uart_result", str(output))


# 测试 Feature：
# UART break 发送、接收检测和退出恢复。
#
# 测试方法：
# 1. 初始化 DUT/Peer，DUT 使能 LINE_ERROR，Peer 发送 10 ms Break。
# 2. 关闭 Break 后读取错误/IRQ，再发送正常帧验证恢复。
#
# 通过条件：
# 1. DUT 状态包含 BREAK，LINE_ERROR 事件增加且无 IRQ fault 增量。
# 2. Break 关闭后的恢复帧完整一致。
def test_uart_p1_010_break_send_and_detect(
    uart_dut_handle,
    uart_peer_handle,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 所有权：Case 显式管理两端初始化、Peer Break 和 DUT 中断/Capture 状态。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dut_handle.instance_id)
    crg_driver.reset(CrgPeripheral.UART, instance=uart_peer_handle.instance_id)
    resource_driver.reset()

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        return (
            ("UART peer break release", lambda: uart_peer_handle.break_set(False)),
            ("UART peer deinitialize", uart_peer_handle.deinitialize),
            ("UART DUT capture cancel", uart_dut_handle.capture_cancel),
            (
                "UART DUT IRQ disable LINE_ERROR",
                lambda: uart_dut_handle.irq_config(
                    UartIrqSource.LINE_ERROR,
                    False,
                    priority=4,
                ),
            ),
            ("UART DUT deinitialize", uart_dut_handle.deinitialize),
        )

    with case_cleanup_scope(cleanup_actions):
        # 配置：DUT 与 Peer 使用相同默认帧格式。
        uart_dut_handle.initialize(baudrate=DEFAULT_BAUDRATE)
        uart_peer_handle.initialize(baudrate=DEFAULT_BAUDRATE)

        # 配置：使能 DUT 的 LINE_ERROR 中断。
        uart_dut_handle.irq_config(UartIrqSource.LINE_ERROR, True, priority=4)

        # 观测：读取 Break 激励前的 IRQ 基线。
        baseline = uart_dut_handle.irq_state_get()

        # 激励：Peer 保持 Break 10 ms 后显式释放。
        uart_peer_handle.break_set(True)
        time.sleep(0.01)
        uart_peer_handle.break_set(False)

        # 观测：读取 Break 后的 UART 与 IRQ 状态。
        status = uart_dut_handle.status_get()
        state = uart_dut_handle.irq_state_get()
        event_delta, fault_delta, source_observed = _irq_observation(
            baseline,
            state,
            UartIrqSource.LINE_ERROR,
        )

        record_observation(
            record_property,
            key="error_flags",
            value=status.error_flags,
            source="dut",
            endpoint="UART_STATUS.ERROR_FLAGS",
        )
        record_property("irq_pending_mask", state.pending_mask)
        record_property("event_count_delta", event_delta)
        record_property("fault_count_delta", fault_delta)
        record_property("source_observed", source_observed)

        # 断言：必须观测到 Break Error 与 LINE_ERROR 中断事实。
        assert status.error_flags & int(UartErrorFlag.BREAK)
        assert fault_delta == 0
        assert event_delta > 0
        assert source_observed

        # 准备：构造 Break 释放后的恢复 Payload。
        recovery_payload = bytes(make_pattern(2, seed=0xF1))

        # 接收：DUT Capture 必须先于 Peer 恢复发送启动。
        uart_dut_handle.capture_start(len(recovery_payload))

        # 发送：Peer 写入恢复路径 Payload。
        recovery_tx = uart_peer_handle.write(
            recovery_payload,
            max_polls=DEFAULT_MAX_POLLS,
        )

        # 观测：等待恢复路径接收完成。
        recovery_capture = uart_dut_handle.capture_wait(len(recovery_payload))

        record_observation(
            record_property,
            key="recovery_actual_data",
            value=recovery_capture.data,
            source="dut",
            endpoint="UART_CAPTURE.DATA",
        )

        # 断言：释放 Break 后的数据路径必须完整恢复。
        assert recovery_tx == len(recovery_payload)
        assert recovery_capture.received == len(recovery_payload)
        assert recovery_capture.data == recovery_payload

    record_evidence(record_property, "dut", "peer")
    output = record_result(
        et_artifact_dir,
        "uart_p1_010_break_send_and_detect",
        error_flags=status.error_flags,
        event_count_delta=event_delta,
        recovery=_transfer_evidence(recovery_payload, recovery_tx, recovery_capture),
    )
    record_property("uart_result", str(output))


# =============================================================================
# 中断掩码与状态控制
# =============================================================================


# 测试 Feature：
# UART 中断源的 mask 使能、关闭和 Service session 状态。
#
# 测试方法：
# 1. 同时使能 RX_READY、TX_READY、CHARACTER_TIMEOUT 并执行内部回环。
# 2. 读取Service enabled/session事实后逐项关闭三个源；不把Service重配置称为硬件pending W1C。
#
# 通过条件：
# 1. enabled_mask 包含全部请求源且本次产生有效 IRQ 事件。
# 2. cleared.enabled_mask 不再包含任一请求源，且无 IRQ fault 增量。
def test_uart_p1_011_interrupt_mask_enable_clear(
    uart_dut_handle,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 准备：组合三个可共同触发的 IRQ 来源，并初始化 DUT。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dut_handle.instance_id)
    resource_driver.reset()

    sources = (
        UartIrqSource.RX_READY,
        UartIrqSource.TX_READY,
        UartIrqSource.CHARACTER_TIMEOUT,
    )
    uart_dut_handle.initialize(
        baudrate=DEFAULT_BAUDRATE,
        data_bits=8,
        stop_bits=1,
        parity=0,
    )

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        return (
            ("UART DUT capture cancel", uart_dut_handle.capture_cancel),
            *tuple(
                (
                    f"UART DUT IRQ disable {source.name}",
                    lambda source=source: uart_dut_handle.irq_config(
                        source,
                        False,
                        priority=4,
                    ),
                )
                for source in sources
            ),
            ("UART DUT loopback disable", lambda: uart_dut_handle.loopback_set(False)),
            ("UART DUT deinitialize", uart_dut_handle.deinitialize),
        )

    with case_cleanup_scope(cleanup_actions):
        # 配置：逐个使能请求源，随后用同一短帧形成IRQ事件。
        for source in sources:
            uart_dut_handle.irq_config(source, True, priority=4)

        # 观测：读取激励前的 IRQ 计数基线。
        baseline = uart_dut_handle.irq_state_get()

        # 准备：构造确定性的短 Payload。
        payload = bytes(make_pattern(12, seed=0x12))

        # 配置：开启内部回环。
        uart_dut_handle.loopback_set(True)

        # 接收：Capture 必须先于发送启动。
        uart_dut_handle.capture_start(len(payload))

        # 发送：写入完整 Payload。
        transferred = uart_dut_handle.write(payload, max_polls=DEFAULT_MAX_POLLS)

        # 观测：等待回环数据并读取中断使能状态。
        capture = uart_dut_handle.capture_wait(len(payload))
        enabled = uart_dut_handle.irq_state_get()

        # 清理与观测：逐个关闭请求源，再读取清除后的掩码事实。
        for source in sources:
            uart_dut_handle.irq_config(source, False, priority=4)
        cleared = uart_dut_handle.irq_state_get()

        # 分析：合并请求掩码并计算中断事件与故障变化。
        requested_mask = sum(int(source) for source in sources)
        event_delta = enabled.event_count - baseline.event_count
        fault_delta = enabled.fault_count - baseline.fault_count
        source_observed = bool(
            enabled.pending_mask & requested_mask or enabled.active_mask & requested_mask
        )

        record_property("enabled_mask", enabled.enabled_mask)
        record_property("disabled_mask", cleared.enabled_mask)
        record_property("event_count_delta", event_delta)
        record_property("fault_count_delta", fault_delta)
        record_property("source_observed", source_observed)
        record_observation(
            record_property,
            key="actual_capture_data",
            value=capture.data,
            source="dut",
            endpoint="UART_CAPTURE.DATA",
        )

        # 断言：数据、中断使能、关闭和事件事实必须全部成立。
        assert transferred == len(payload)
        assert capture.received == len(payload)
        assert capture.data == payload
        assert enabled.enabled_mask & requested_mask == requested_mask
        assert cleared.enabled_mask & requested_mask == 0
        assert fault_delta == 0
        assert event_delta > 0
        assert source_observed

    record_evidence(record_property, "dut")
    output = record_result(
        et_artifact_dir,
        "uart_p1_011_interrupt_mask_enable_clear",
        transfer=_transfer_evidence(payload, transferred, capture),
        enabled_mask=enabled.enabled_mask,
        cleared_mask=cleared.enabled_mask,
        event_count_delta=event_delta,
    )
    record_property("uart_result", str(output))


# 测试 Feature：
# UART busy detect 中断、清除条件和恢复路径。
#
# 测试方法：
# 1. 调用 Driver 原子 busy-detect 接口；若运行时无法形成确定刺激则按既有规则 skip。
# 2. 检查 busy/interruption/clear/recovery 事实，再重新初始化并执行回环恢复。
#
# 通过条件：
# 1. Driver 返回四个判定字段均为真且 trigger_count 为 1。
# 2. 恢复回环完整收发且数据一致。
def test_uart_p1_012_busy_detect_irq(
    uart_dut_handle,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 所有权：登记 Capture、回环和反初始化责任。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dut_handle.instance_id)
    resource_driver.reset()

    initialized = False
    loopback_cleanup_owned = False
    capture_cleanup_owned = False

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
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 配置：初始化 DUT，并登记原生命周期对应的清理责任。
        uart_dut_handle.initialize(
            baudrate=DEFAULT_BAUDRATE,
            data_bits=8,
            stop_bits=1,
            parity=0,
        )
        initialized = True
        loopback_cleanup_owned = True
        capture_cleanup_owned = True

        # 激励：由 Driver 形成有界 Busy Detect 条件。
        try:
            result = uart_dut_handle.busy_detect_trigger()
        except OperationBusy:
            pytest.skip(
                "blocked_by_runtime: current UART did not form a deterministic Busy Detect condition within the Driver's bounded trigger window"
            )

        record_observation(
            record_property,
            key="pre_trigger_usr",
            value=result.pre_trigger_usr,
            source="dut",
            endpoint="UART_BUSY.PRE_TRIGGER_USR",
        )
        record_observation(
            record_property,
            key="observed_iir",
            value=result.observed_iir,
            source="dut",
            endpoint="UART_BUSY.OBSERVED_IIR",
        )
        record_observation(
            record_property,
            key="observed_usr",
            value=result.observed_usr,
            source="dut",
            endpoint="UART_BUSY.OBSERVED_USR",
        )
        record_property("trigger_count", result.trigger_count)
        record_property("busy_observed", result.busy_observed)
        record_property("interrupt_observed", result.interrupt_observed)
        record_property("busy_cleared", result.cleared)
        record_property("busy_recovered", result.recovered)

        # 断言：Busy Detect 的中断、清除和恢复事实必须完整。
        assert result.busy_observed
        assert result.interrupt_observed
        assert result.cleared
        assert result.recovered
        assert result.trigger_count == 1

        # 恢复：重新初始化 UART 默认数据路径。
        uart_dut_handle.initialize(baudrate=DEFAULT_BAUDRATE)

        # 准备：构造恢复验证 Payload。
        payload = bytes(make_pattern(4, seed=0xC1))

        # 配置：开启内部回环。
        uart_dut_handle.loopback_set(True)

        # 接收：Capture 必须先于恢复发送启动。
        uart_dut_handle.capture_start(len(payload))

        # 发送：写入恢复验证 Payload。
        transferred = uart_dut_handle.write(payload, max_polls=DEFAULT_MAX_POLLS)

        # 观测：等待恢复数据接收完成。
        capture = uart_dut_handle.capture_wait(len(payload))

        # 断言：Busy Detect 后的数据路径必须完整恢复。
        assert transferred == len(payload)
        assert capture.received == len(payload)
        assert capture.data == payload

    record_evidence(record_property, "dut")
    output = record_result(
        et_artifact_dir,
        "uart_p1_012_busy_detect_irq",
        busy_detect=asdict(result),
        recovery=_transfer_evidence(payload, transferred, capture),
    )
    record_property("uart_result", str(output))


# 测试 Feature：
# UART 发送 halt、resume 和数据路径恢复。
#
# 测试方法：
# 1. 开启内部回环和Capture后Halt TX，只提交一次短Payload，并连续读取4次Capture观察暂停进度。
# 2. 不重新提交Payload，解除Halt后等待原Capture完成并比较实际数据。
#
# 通过条件：
# 1. halt/resume 均成功返回且快照可读取。
# 2. 恢复数据完整收发且逐字节一致。
def test_uart_p1_013_halt_resume_and_recovery(
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

    initialized = False
    halt_owned = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if halt_owned:
            actions.append(("UART DUT halt release", lambda: uart_dut_handle.halt_set(False)))
        if initialized:
            actions.extend(
                (
                    ("UART DUT capture cancel", uart_dut_handle.capture_cancel),
                    ("UART DUT loopback disable", lambda: uart_dut_handle.loopback_set(False)),
                    ("UART DUT deinitialize", uart_dut_handle.deinitialize),
                )
            )
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        uart_dut_handle.initialize(baudrate=DEFAULT_BAUDRATE, data_bits=8, stop_bits=1, parity=0)
        initialized = True
        uart_dut_handle.loopback_set(True)
        payload = bytes(make_pattern(8, seed=0x32))
        uart_dut_handle.capture_start(len(payload))
        uart_dut_handle.halt_set(True)
        halt_owned = True
        accepted = uart_dut_handle.write_partial(payload)
        halted_status = uart_dut_handle.status_get()
        paused_samples: list[int] = []
        # 观察：连续四次独立Capture请求均受Driver请求超时约束，用于证明Halt期间接收进度不前进。
        for _ in range(4):
            paused_samples.append(uart_dut_handle.capture_get().received)
        paused_received = max(paused_samples, default=-1)

        record_observation(
            record_property,
            key="halted_tx_fifo_level",
            value=halted_status.tx_fifo_level,
            source="dut",
            endpoint="UART_FIFO.TX_LEVEL",
        )
        record_property("accepted_bytes", accepted)
        record_property("pause_sample_count", len(paused_samples))
        record_property("paused_received", paused_received)
        assert accepted == len(payload)
        assert halted_status.tx_fifo_level > 0
        assert len(paused_samples) == 4
        assert paused_received == 0

        uart_dut_handle.halt_set(False)
        halt_owned = False
        capture = uart_dut_handle.capture_wait(len(payload))
        data_match = capture.data == payload
        record_observation(
            record_property,
            key="resumed_actual_data",
            value=capture.data,
            source="dut",
            endpoint="UART_CAPTURE.DATA",
        )
        record_property("resume_data_match", data_match)
        assert capture.received == len(payload)
        assert data_match

    record_evidence(record_property, "dut")
    output = record_result(
        et_artifact_dir,
        "uart_p1_013_halt_resume_and_recovery",
        accepted=accepted,
        halted_tx_fifo_level=halted_status.tx_fifo_level,
        paused_received=paused_received,
        paused_samples=paused_samples,
        resumed_data_match=data_match,
    )
    record_property("uart_result", str(output))


# =============================================================================
# 格式与速率配置
# =============================================================================


# 测试 Feature：
# UART 数据位、停止位和校验方式的合法帧格式组合。
#
# 测试方法：
# 1. 逐项配置代表性的 data bits、stop bits 和 parity 组合。
# 2. 每个组合分别执行 DUT→Peer 和 Peer→DUT 收发。
#
# 通过条件：
# 1. 每个组合两个方向的发送/接收长度均完整。
# 2. 每个组合两个方向的数据均逐字节一致。
def test_uart_p1_014_line_format_matrix(
    uart_dut_handle,
    uart_peer_handle,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 准备：定义代表性合法帧格式矩阵，避免复制多个同目标Case。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dut_handle.instance_id)
    crg_driver.reset(CrgPeripheral.UART, instance=uart_peer_handle.instance_id)
    resource_driver.reset()

    matrix = (
        (5, UartStopBits.ONE_AND_HALF, UartParity.NONE),
        (6, UartStopBits.TWO, UartParity.EVEN),
        (7, UartStopBits.ONE, UartParity.ODD),
        (8, UartStopBits.TWO, UartParity.STICK_ZERO),
        (8, UartStopBits.ONE, UartParity.STICK_ONE),
    )
    results = []

    # 遍历：每个合法帧格式使用独立生命周期，并验证两个方向的完整数据证据。
    for data_bits, stop_bits, parity in matrix:
        ownership = _PairOwnership()

        def cleanup_actions(owned: _PairOwnership = ownership) -> tuple[CleanupAction, ...]:
            actions: list[CleanupAction] = []
            if owned.dut_capture_started:
                actions.append(("UART DUT capture cancel", uart_dut_handle.capture_cancel))
            if owned.peer_capture_started:
                actions.append(("UART peer capture cancel", uart_peer_handle.capture_cancel))
            if owned.peer_initialized:
                actions.append(("UART peer deinitialize", uart_peer_handle.deinitialize))
            if owned.dut_initialized:
                actions.append(("UART DUT deinitialize", uart_dut_handle.deinitialize))
            return tuple(actions)

        with case_cleanup_scope(cleanup_actions):
            # 配置：DUT 与 Peer 使用当前同一组帧格式。
            uart_dut_handle.initialize(
                baudrate=DEFAULT_BAUDRATE,
                data_bits=data_bits,
                stop_bits=stop_bits,
                parity=parity,
            )
            ownership.dut_initialized = True
            uart_peer_handle.initialize(
                baudrate=DEFAULT_BAUDRATE,
                data_bits=data_bits,
                stop_bits=stop_bits,
                parity=parity,
            )
            ownership.peer_initialized = True

            # 准备：按当前数据位宽裁剪确定性载荷。
            raw_payload = make_pattern(12, seed=data_bits + int(stop_bits))
            payload = bytes(value & ((1 << data_bits) - 1) for value in raw_payload)

            # DUT→Peer：启动 Peer Capture 后发送当前载荷。
            uart_peer_handle.capture_start(len(payload))
            ownership.peer_capture_started = True
            dut_transferred = uart_dut_handle.write(payload, max_polls=DEFAULT_MAX_POLLS)
            peer_capture = uart_peer_handle.capture_wait(len(payload))

            # Peer→DUT：切换方向并复用相同载荷验证帧格式对称性。
            uart_dut_handle.capture_start(len(payload))
            ownership.dut_capture_started = True
            peer_transferred = uart_peer_handle.write(payload, max_polls=DEFAULT_MAX_POLLS)
            dut_capture = uart_dut_handle.capture_wait(len(payload))

            record_observation(
                record_property,
                key="peer_actual_data",
                value=peer_capture.data,
                source="peer",
                device_id="peer",
                endpoint="PEER_UART.RX_CAPTURE",
            )
            record_observation(
                record_property,
                key="dut_actual_data",
                value=dut_capture.data,
                source="dut",
                endpoint="UART_CAPTURE.DATA",
            )
            record_property(
                "all_data_match", peer_capture.data == payload and dut_capture.data == payload
            )

            # 断言：两个方向的长度和数据必须全部匹配。
            assert dut_transferred == len(payload)
            assert peer_capture.received == len(payload)
            assert peer_capture.data == payload
            assert peer_transferred == len(payload)
            assert dut_capture.received == len(payload)
            assert dut_capture.data == payload

            # 记录：保存当前帧格式下两个方向的实际传输事实。
            results.append(
                {
                    "data_bits": data_bits,
                    "stop_bits": stop_bits,
                    "parity": int(parity),
                    "dut_to_peer": {
                        "tx_requested": len(payload),
                        "tx_completed": dut_transferred,
                        "rx_expected": len(payload),
                        "rx_completed": peer_capture.received,
                        "data_match": peer_capture.data == payload,
                    },
                    "peer_to_dut": {
                        "tx_requested": len(payload),
                        "tx_completed": peer_transferred,
                        "rx_expected": len(payload),
                        "rx_completed": dut_capture.received,
                        "data_match": dut_capture.data == payload,
                    },
                }
            )

    # 记录：保存全部帧格式组合和实际使用的 DUT/Peer Evidence。
    record_property("combination_count", len(results))
    record_property("matrix_all_data_match", True)
    record_evidence(record_property, "dut", "peer")
    output = record_result(
        et_artifact_dir,
        "uart_p1_014_line_format_matrix",
        combinations=results,
        last_peer_actual_data=list(peer_capture.data),
        last_dut_actual_data=list(dut_capture.data),
    )
    record_property("uart_result", str(output))


# 测试 Feature：
# UART 代表性波特率配置和双向收发。
#
# 测试方法：
# 1. 从 DUT/Peer 能力交集生成最小值、常用值、高速值和非整除值候选。
# 2. 每个候选波特率重新初始化 DUT/Peer 并执行双向短帧传输。
#
# 通过条件：
# 1. 至少有一个能力范围内的候选波特率被执行。
# 2. 所有候选值的两个方向均完整收发且数据一致。
def test_uart_p1_015_baudrate_matrix(
    uart_dut_handle,
    uart_peer_handle,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 能力：读取 DUT 与 Peer 的波特率边界。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dut_handle.instance_id)
    crg_driver.reset(CrgPeripheral.UART, instance=uart_peer_handle.instance_id)
    resource_driver.reset()

    dut_capabilities = uart_dut_handle.capabilities_get()
    peer_capabilities = uart_peer_handle.capabilities_get()

    # 分析：计算两端共同支持的有效波特率区间。
    lower = max(dut_capabilities.min_baudrate, peer_capabilities.min_baudrate)
    upper = min(dut_capabilities.max_baudrate, peer_capabilities.max_baudrate)
    if lower > upper:
        pytest.skip("skip_by_runtime_feature: UART DUT/Peer baudrate ranges do not overlap")

    # 准备：在共同区间内选择最小、常用、高速和非整除代表值。
    candidates = {
        lower,
        max(lower, min(9_600, upper)),
        max(lower, min(DEFAULT_BAUDRATE, upper)),
        max(lower, min(1_000_000, upper)),
        max(lower, min(1_000_003, upper)),
    }
    baudrates = tuple(sorted(value for value in candidates if lower <= value <= upper))
    results = []

    # 遍历：每个候选波特率使用独立生命周期并验证双向短帧。
    for baudrate in baudrates:
        ownership = _PairOwnership()

        def cleanup_actions(owned: _PairOwnership = ownership) -> tuple[CleanupAction, ...]:
            actions: list[CleanupAction] = []
            if owned.dut_capture_started:
                actions.append(("UART DUT capture cancel", uart_dut_handle.capture_cancel))
            if owned.peer_capture_started:
                actions.append(("UART peer capture cancel", uart_peer_handle.capture_cancel))
            if owned.peer_initialized:
                actions.append(("UART peer deinitialize", uart_peer_handle.deinitialize))
            if owned.dut_initialized:
                actions.append(("UART DUT deinitialize", uart_dut_handle.deinitialize))
            return tuple(actions)

        with case_cleanup_scope(cleanup_actions):
            # 配置：DUT 与 Peer 使用当前同一波特率和默认帧格式。
            uart_dut_handle.initialize(baudrate=baudrate)
            ownership.dut_initialized = True
            uart_peer_handle.initialize(baudrate=baudrate)
            ownership.peer_initialized = True

            # 准备：由波特率低字节生成可重复载荷。
            payload = make_pattern(24, seed=baudrate & 0xFF)

            # DUT→Peer：启动 Peer Capture 后发送当前载荷。
            uart_peer_handle.capture_start(len(payload))
            ownership.peer_capture_started = True
            dut_transferred = uart_dut_handle.write(payload, max_polls=DEFAULT_MAX_POLLS)
            peer_capture = uart_peer_handle.capture_wait(len(payload))

            # Peer→DUT：切换方向并复用相同载荷。
            uart_dut_handle.capture_start(len(payload))
            ownership.dut_capture_started = True
            peer_transferred = uart_peer_handle.write(payload, max_polls=DEFAULT_MAX_POLLS)
            dut_capture = uart_dut_handle.capture_wait(len(payload))

            record_property("requested_baudrate", baudrate)
            record_observation(
                record_property,
                key="peer_actual_data",
                value=peer_capture.data,
                source="peer",
                device_id="peer",
                endpoint="PEER_UART.RX_CAPTURE",
            )
            record_observation(
                record_property,
                key="dut_actual_data",
                value=dut_capture.data,
                source="dut",
                endpoint="UART_CAPTURE.DATA",
            )
            record_property(
                "all_data_match", peer_capture.data == payload and dut_capture.data == payload
            )

            # 断言：两个方向的长度和数据必须全部匹配。
            assert dut_transferred == len(payload)
            assert peer_capture.received == len(payload)
            assert peer_capture.data == payload
            assert peer_transferred == len(payload)
            assert dut_capture.received == len(payload)
            assert dut_capture.data == payload

            # 记录：保存当前波特率下两个方向的实际传输事实。
            results.append(
                {
                    "baudrate": baudrate,
                    "dut_to_peer": {
                        "tx_requested": len(payload),
                        "tx_completed": dut_transferred,
                        "rx_expected": len(payload),
                        "rx_completed": peer_capture.received,
                        "data_match": peer_capture.data == payload,
                    },
                    "peer_to_dut": {
                        "tx_requested": len(payload),
                        "tx_completed": peer_transferred,
                        "rx_expected": len(payload),
                        "rx_completed": dut_capture.received,
                        "data_match": dut_capture.data == payload,
                    },
                }
            )

    # 断言与记录：能力交集必须至少产生一个子项，并保存全部测量事实。
    assert results
    record_property("baudrate_count", len(results))
    record_property("last_requested_baudrate", baudrates[-1])
    record_property("matrix_all_data_match", True)
    record_evidence(record_property, "dut", "peer")
    output = record_result(
        et_artifact_dir,
        "uart_p1_015_baudrate_matrix",
        results=results,
        last_peer_actual_data=list(peer_capture.data),
        last_dut_actual_data=list(dut_capture.data),
    )
    record_property("uart_result", str(output))


# =============================================================================
# FIFO 与参数边界
# =============================================================================


# 测试 Feature：
# UART FIFO 配置、边界收发和状态快照。
#
# 测试方法：
# 1. 配置 FIFO 阈值，依次执行 1、15、16、17、32 字节内部回环。
# 2. 每轮读取发送前后 FIFO 状态，并保留逐长度证据。
#
# 通过条件：
# 1. 每个边界长度完整发送、完整接收且数据一致。
# 2. 每轮结束后 RX FIFO level 为 0。
def test_uart_p1_016_fifo_boundary_and_status(
    uart_dut_handle,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 准备：收集每个FIFO边界配置、快照和回环数据事实。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dut_handle.instance_id)
    resource_driver.reset()

    results = []
    initialized = False
    loopback_cleanup_owned = False
    capture_cleanup_owned = False

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
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 配置：初始化 DUT，并登记回环、Capture 和反初始化责任。
        uart_dut_handle.initialize(
            baudrate=DEFAULT_BAUDRATE,
            data_bits=8,
            stop_bits=1,
            parity=0,
        )
        initialized = True
        loopback_cleanup_owned = True
        capture_cleanup_owned = True

        # 配置：设置代表性的 FIFO 阈值并保持 FIFO 使能。
        uart_dut_handle.fifo_config(tx_threshold=2, rx_threshold=4, enabled=True)

        # 遍历：覆盖FIFO深度边界附近长度，每轮检查状态和完整回环数据。
        for length in (1, 15, 16, 17, 32):
            # 观测：保存本轮发送前的 FIFO 状态。
            before = uart_dut_handle.status_get()

            # 准备：构造与当前边界长度一致的确定性 Payload。
            payload = bytes(make_pattern(length, seed=0x60 + length))

            # 配置：显式保持内部回环开启。
            uart_dut_handle.loopback_set(True)

            # 接收：Capture 必须先于发送启动。
            uart_dut_handle.capture_start(len(payload))

            # 发送：写入本轮边界 Payload。
            transferred = uart_dut_handle.write(payload, max_polls=DEFAULT_MAX_POLLS)

            # 观测：等待接收完成并读取发送后的 FIFO 状态。
            capture = uart_dut_handle.capture_wait(len(payload))
            after = uart_dut_handle.status_get()

            record_observation(
                record_property,
                key="actual_capture_data",
                value=capture.data,
                source="dut",
                endpoint="UART_CAPTURE.DATA",
            )
            record_observation(
                record_property,
                key="before_rx_fifo_level",
                value=before.rx_fifo_level,
                source="dut",
                endpoint="UART_FIFO.RX_LEVEL",
            )
            record_observation(
                record_property,
                key="after_rx_fifo_level",
                value=after.rx_fifo_level,
                source="dut",
                endpoint="UART_FIFO.RX_LEVEL",
            )
            record_property("all_data_match", capture.data == payload)

            # 断言：数据必须完整一致，接收 FIFO 必须回到空闲状态。
            assert transferred == len(payload)
            assert capture.received == len(payload)
            assert capture.data == payload
            assert after.rx_fifo_level == 0

            # 记录：保存当前长度对应的状态和传输事实。
            results.append(
                {
                    "length": length,
                    "before_rx_fifo_level": before.rx_fifo_level,
                    "after_rx_fifo_level": after.rx_fifo_level,
                    "transfer": {
                        "tx_requested": len(payload),
                        "tx_completed": transferred,
                        "rx_expected": len(payload),
                        "rx_completed": capture.received,
                        "data_match": capture.data == payload,
                    },
                }
            )

    record_property("boundary_count", len(results))
    record_property("matrix_all_data_match", True)
    record_property("final_rx_fifo_level", after.rx_fifo_level)
    record_evidence(record_property, "dut")
    output = record_result(
        et_artifact_dir,
        "uart_p1_016_fifo_boundary_and_status",
        results=results,
        last_capture_data=list(capture.data),
    )
    record_property("uart_result", str(output))


# 测试 Feature：
# UART 参数校验对非法输入的拒绝和合法路径恢复。
#
# 测试方法：
# 1. 提交零波特率、非法帧格式、零长度和非法 FIFO 阈值操作。
# 2. 逐项确认 ValueError 后执行合法内部回环恢复传输。
#
# 通过条件：
# 1. 七项非法请求均在硬件传输前被拒绝。
# 2. 合法恢复传输完整收发且数据一致。
def test_uart_p1_017_invalid_parameter_rejection(
    uart_dut_handle,
    et_artifact_dir: Path,
    record_property,
    crg_driver,
    resource_driver,
) -> None:

    # 准备：构造仅验证公共Driver参数契约的非法操作矩阵。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.UART, instance=uart_dut_handle.instance_id)
    resource_driver.reset()

    invalid_operations = (
        lambda: uart_dut_handle.initialize(baudrate=0),
        lambda: uart_dut_handle.configure_extended(baudrate=DEFAULT_BAUDRATE, data_bits=4),
        lambda: uart_dut_handle.configure_extended(baudrate=DEFAULT_BAUDRATE, stop_bits=0),
        lambda: uart_dut_handle.write(b""),
        lambda: uart_dut_handle.read_exact(0),
        lambda: uart_dut_handle.capture_start(0),
        lambda: uart_dut_handle.fifo_config(tx_threshold=3),
    )
    rejected = 0

    # 遍历：每个非法操作都必须在设备传输前由公共Driver参数校验拒绝。
    for operation in invalid_operations:
        with pytest.raises(ValueError):
            operation()
        rejected += 1

    # 准备：构造合法路径恢复验证 Payload。
    payload = bytes(make_pattern(8))
    initialized = False
    loopback_enabled = False
    capture_cleanup_owned = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if capture_cleanup_owned:
            actions.append(("UART DUT capture cancel", uart_dut_handle.capture_cancel))
        if loopback_enabled:
            actions.append(
                ("UART DUT loopback disable", lambda: uart_dut_handle.loopback_set(False))
            )
        if initialized:
            actions.append(("UART DUT deinitialize", uart_dut_handle.deinitialize))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 配置：使用合法参数初始化 DUT。
        uart_dut_handle.initialize(
            baudrate=DEFAULT_BAUDRATE,
            data_bits=8,
            stop_bits=1,
            parity=0,
        )
        initialized = True

        # 配置：开启内部回环，并登记异常退出时的关闭责任。
        uart_dut_handle.loopback_set(True)
        loopback_enabled = True
        capture_cleanup_owned = True

        # 接收：Capture 必须先于恢复发送启动。
        uart_dut_handle.capture_start(len(payload))

        # 发送：写入合法路径 Payload。
        transferred = uart_dut_handle.write(payload, max_polls=DEFAULT_MAX_POLLS)

        # 观测：等待合法路径数据接收完成。
        capture = uart_dut_handle.capture_wait(len(payload))

        record_property("rejected_count", rejected)
        record_observation(
            record_property,
            key="recovery_actual_data",
            value=capture.data,
            source="dut",
            endpoint="UART_CAPTURE.DATA",
        )
        record_property("recovery_data_match", capture.data == payload)

        # 断言：非法输入不得破坏后续合法数据路径。
        assert transferred == len(payload)
        assert capture.received == len(payload)
        assert capture.data == payload

    record_evidence(record_property, "dut")
    output = record_result(
        et_artifact_dir,
        "uart_p1_017_invalid_parameter_rejection",
        rejected_count=rejected,
        recovery={
            "tx_requested": len(payload),
            "tx_completed": transferred,
            "rx_expected": len(payload),
            "rx_completed": capture.received,
            "data_match": capture.data == payload,
        },
    )
    record_property("uart_result", str(output))
