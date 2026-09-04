# Framework Validation测试模块。
#
# 职责：验证test_bench_config 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import pytest

from et_test_platform.core.errors import ConfigurationError
from et_test_platform.profiles.bench import (
    DebuggerConfig,
    PulseStimulusConfig,
    SignalObserverConfig,
    UartPairConfig,
    load_debugger,
    load_dma_peripheral_pair,
    load_pulse_stimulus,
    load_serial_target,
    load_signal_observer,
    load_uart_pair,
)
from et_test_platform.profiles.capabilities import load_packaged_chip_capabilities
from et_test_platform.profiles.hardware_connections import load_hardware_connections


# 验证逻辑脉冲绑定从Bench取输出参数，从环境取设备资源。
def test_pulse_stimulus_joins_bench_facts_with_runtime_environment(tmp_path) -> None:
    profile = tmp_path / "bench.yaml"
    profile.write_text(
        """
targets:
  dut:
    pulse_stimuli:
      emergency_input:
        instrument: scope0
        output_channel: 2
        amplitude_vpp: 3.0
        offset_v: 1.5
        timeout_s: 2.0
""".strip(),
        encoding="utf-8",
    )

    config = load_pulse_stimulus(
        profile,
        "dut",
        "emergency_input",
        environment={
            "ET_INSTRUMENT_SCOPE0_DRIVER": "mso5204",
            "ET_INSTRUMENT_SCOPE0_RESOURCE": "USB::SCOPE",
        },
    )

    assert config == PulseStimulusConfig(
        logical_stimulus="emergency_input",
        instrument_name="scope0",
        driver="mso5204",
        resource="USB::SCOPE",
        output_channel=2,
        amplitude_vpp=3.0,
        offset_v=1.5,
        timeout_s=2.0,
    )


# 验证缺少逻辑激励映射时失败关闭，不隐式选择任意输出。
def test_pulse_stimulus_requires_explicit_logical_mapping(tmp_path) -> None:
    profile = tmp_path / "bench.yaml"
    profile.write_text("targets:\n  dut: {}\n", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="no pulse stimulus"):
        load_pulse_stimulus(profile, "dut", "emergency_input", environment={})


# 验证Debugger的芯片连接事实来自Bench，本机工具与探针身份来自运行环境。
def test_debugger_joins_bench_facts_with_runtime_environment(tmp_path) -> None:
    profile = tmp_path / "bench.yaml"
    profile.write_text(
        """
targets:
  dut:
    debugger:
      driver: jlink
      device: Cortex-M7
      interface: JTAG
      speed_khz: 1200
      command_timeout_s: 3.0
""".strip(),
        encoding="utf-8",
    )

    config = load_debugger(
        profile,
        "dut",
        environment={
            "ET_TOOL_JLINK_EXECUTABLE": "C:/tools/JLink.exe",
            "ET_DUT_DEBUG_PROBE_SERIAL": "123456",
        },
    )

    assert config == DebuggerConfig(
        driver="jlink",
        executable="C:/tools/JLink.exe",
        device="Cortex-M7",
        interface="JTAG",
        speed_khz=1200,
        probe_serial="123456",
        command_timeout_s=3.0,
    )


# 验证逻辑信号名称只通过 Bench 绑定到仪器、资源和通道，Case 无需知道物理接线。
def test_signal_observer_uses_bench_binding_and_instrument_environment(tmp_path) -> None:
    profile = tmp_path / "bench.yaml"
    profile.write_text(
        """
targets:
  dut:
    signal_observers:
      timer_output:
        instrument: scope
        channel: 2
        vertical_scale_v: 1.0
        trigger_level_v: 1.65
        probe_ratio: 10
        timeout_s: 2.5
""".strip(),
        encoding="utf-8",
    )

    config = load_signal_observer(
        profile,
        "dut",
        "timer_output",
        environment={
            "ET_INSTRUMENT_SCOPE_DRIVER": "mso5204",
            "ET_INSTRUMENT_SCOPE_RESOURCE": "TCPIP0::scope::INSTR",
        },
    )

    assert config == SignalObserverConfig(
        logical_signal="timer_output",
        instrument_name="scope",
        driver="mso5204",
        resource="TCPIP0::scope::INSTR",
        channel=2,
        vertical_scale_v=1.0,
        trigger_level_v=1.65,
        probe_ratio=10.0,
        timeout_s=2.5,
    )


# 验证未声明接线或未启用仪器时失败关闭，不能让 Case 使用隐式默认通道。
def test_signal_observer_rejects_missing_runtime_instrument_binding(tmp_path) -> None:
    profile = tmp_path / "bench.yaml"
    profile.write_text(
        """
targets:
  dut:
    signal_observers:
      timer_output:
        instrument: scope
        channel: 1
        vertical_scale_v: 1.0
        trigger_level_v: 1.65
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="incomplete"):
        load_signal_observer(profile, "dut", "timer_output", environment={})


def test_serial_target_comes_from_bench_and_environment(tmp_path) -> None:
    profile = tmp_path / "bench.yaml"
    profile.write_text(
        """
targets:
  dut:
    chip: et6801
    firmware_build_id: test-build
    transport:
      kind: serial
      port: ${TEST_PORT}
      baud: ${TEST_BAUD}
      bytesize: 8
      parity: N
      stopbits: 1
      dtr: false
      rts: false
      request_timeout_s: 0.25
""".strip(),
        encoding="utf-8",
    )

    config = load_serial_target(
        profile,
        "dut",
        environment={"TEST_PORT": "COM_TEST", "TEST_BAUD": "460800"},
    )

    assert config.port == "COM_TEST"
    assert config.chip_id == "et6801"
    assert config.firmware_build_id == "test-build"
    assert config.baudrate == 460800
    assert config.dtr is False
    assert config.rts is False
    assert config.request_timeout_s == 0.25


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("bytesize", 4, "bytesize"),
        ("bytesize", 9, "bytesize"),
        ("parity", "X", "parity"),
        ("stopbits", 1.5, "stopbits"),
    ],
)
def test_serial_target_rejects_unsupported_line_settings(
    tmp_path,
    field,
    value,
    message,
) -> None:
    profile = tmp_path / "bench.yaml"
    profile.write_text(
        f"""
targets:
  dut:
    chip: et6801
    transport:
      kind: serial
      port: COM_TEST
      baud: 115200
      {field}: {value}
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match=message):
        load_serial_target(profile, "dut", environment={})


def test_missing_environment_variable_fails_closed(tmp_path) -> None:
    profile = tmp_path / "bench.yaml"
    profile.write_text(
        """
targets:
  dut:
    chip: et6801
    transport:
      kind: serial
      port: ${MISSING_PORT}
      baud: 115200
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="MISSING_PORT"):
        load_serial_target(profile, "dut", environment={})


def test_dma_pair_uses_logical_roles_from_bench(tmp_path) -> None:
    profile = tmp_path / "bench.yaml"
    profile.write_text(
        """
targets:
  dut:
    dma_peripheral_pair:
      provider: uart_loopback
      controller_instance: 1
      dma_port_instance: 4
      peer_port_instance: 6
      source_interface: 2
      destination_interface: 5
      baud: 230400
""".strip(),
        encoding="utf-8",
    )

    pair = load_dma_peripheral_pair(profile, "dut", environment={})

    assert pair.provider == "uart_loopback"
    assert pair.controller_instance == 1
    assert pair.dma_port_instance == 4
    assert pair.peer_port_instance == 6
    assert pair.source_interface == 2
    assert pair.destination_interface == 5
    assert pair.baudrate == 230400


def test_dma_pair_rejects_same_instance(tmp_path) -> None:
    profile = tmp_path / "bench.yaml"
    profile.write_text(
        """
targets:
  dut:
    dma_peripheral_pair:
      provider: uart_loopback
      controller_instance: 0
      dma_port_instance: 1
      peer_port_instance: 1
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="pair is invalid"):
        load_dma_peripheral_pair(profile, "dut", environment={})


def test_dma_pair_requires_explicit_controller_instance(tmp_path) -> None:
    profile = tmp_path / "bench.yaml"
    profile.write_text(
        """
targets:
  dut:
    dma_peripheral_pair:
      provider: uart_loopback
      dma_port_instance: 1
      peer_port_instance: 2
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="controller_instance"):
        load_dma_peripheral_pair(profile, "dut", environment={})


def test_uart_pair_uses_logical_roles_from_bench(tmp_path) -> None:
    profile = tmp_path / "bench.yaml"
    profile.write_text(
        """
targets:
  dut:
    ip_pairs:
      uart:
        control_instance: 0
        dut_instance: 4
        peer_instance: 6
        error_stimuli:
          - stop_mismatch_framing
""".strip(),
        encoding="utf-8",
    )

    pair = load_uart_pair(profile, "dut", environment={})

    assert pair == UartPairConfig(
        control_instance=0,
        dut_instance=4,
        peer_instance=6,
        error_stimuli=frozenset({"stop_mismatch_framing"}),
    )
    assert pair.control_instance == 0
    assert pair.dut_instance == 4
    assert pair.peer_instance == 6
    assert pair.error_stimuli == frozenset({"stop_mismatch_framing"})


def test_uart_pair_allows_missing_peer(tmp_path) -> None:
    profile = tmp_path / "bench.yaml"
    profile.write_text(
        """
targets:
  dut:
    ip_pairs:
      uart:
        control_instance: 0
        dut_instance: 1
""".strip(),
        encoding="utf-8",
    )

    pair = load_uart_pair(profile, "dut", environment={})

    assert pair.peer_instance is None


def test_uart_pair_rejects_unknown_error_stimulus(tmp_path) -> None:
    profile = tmp_path / "bench.yaml"
    profile.write_text(
        """
targets:
  dut:
    ip_pairs:
      uart:
        control_instance: 0
        dut_instance: 1
        error_stimuli:
          - arbitrary_error_bit
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="unsupported stimulus"):
        load_uart_pair(profile, "dut", environment={})


@pytest.mark.parametrize(
    ("control_instance", "dut_instance", "peer_instance"),
    [
        (1, 1, None),
        (0, 1, 0),
        (0, 1, 1),
        (-1, 1, None),
        (0, -1, None),
    ],
)
def test_uart_pair_rejects_invalid_instance_roles(
    tmp_path,
    control_instance,
    dut_instance,
    peer_instance,
) -> None:
    profile = tmp_path / "bench.yaml"
    peer_line = f"        peer_instance: {peer_instance}\n" if peer_instance is not None else ""
    profile.write_text(
        (
            "targets:\n"
            "  dut:\n"
            "    ip_pairs:\n"
            "      uart:\n"
            f"        control_instance: {control_instance}\n"
            f"        dut_instance: {dut_instance}\n"
            f"{peer_line}"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="UART pair"):
        load_uart_pair(profile, "dut", environment={})


def test_uart_pair_is_immutable() -> None:
    pair = UartPairConfig(control_instance=0, dut_instance=1, peer_instance=2)

    with pytest.raises(AttributeError):
        pair.dut_instance = 3  # type: ignore[misc]


# 验证实际CAN接线使用Capability中的can0，不把盒子的CAN1当作芯片实例。
def test_packaged_can_connection_uses_dut_handle_and_gpio() -> None:

    capabilities = load_packaged_chip_capabilities("et6801")
    connections = load_hardware_connections(capabilities=capabilities, expected_lane="fpga")
    endpoint = connections.select("can")["can"]["dut"]

    assert endpoint.handle == "can0"
    assert endpoint.gpio == {"rx": 58, "tx": 59}
    assert set(connections.select("can")["can"]) == {"dut"}
