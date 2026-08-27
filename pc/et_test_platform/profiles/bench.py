# Bench Topology 配置的强类型加载与校验。
#
# 职责：解析串口目标、UART Pair、DMA 外设 Pair 等台架事实并在使用前验证配置完整性。
# 边界：不发送硬件命令、不创建跨 IP Workflow，也不把 YAML 原始字典泄漏给 Test Case。
# 依赖：仅依赖 YAML、路径处理、强类型 Bench Model 与 ConfigurationError。

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core.errors import ConfigurationError

_ENV_VALUE = re.compile(r"^\$\{([A-Z_][A-Z0-9_]*)\}$")
_SERIAL_PARITIES = frozenset({"N", "E", "O", "M", "S"})
# This is a physical bench stimulus, not a UART error-bit enumeration.  Keep
# the vocabulary limited to the stimulus currently consumed by the framing
# error Case; adding another value requires a corresponding bench adapter.
_UART_ERROR_STIMULI = frozenset({"stop_mismatch_framing"})


# 表示 SerialTargetConfig 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
@dataclass(frozen=True)
class SerialTargetConfig:
    target_id: str
    chip_id: str
    firmware_build_id: str | None
    port: str
    baudrate: int
    bytesize: int
    parity: str
    stopbits: int
    dtr: bool
    rts: bool
    request_timeout_s: float


# 表示 DmaPeripheralPairConfig 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
@dataclass(frozen=True)
class DmaPeripheralPairConfig:
    provider: str
    controller_instance: int
    dma_port_instance: int
    peer_port_instance: int
    source_interface: int
    destination_interface: int
    baudrate: int
    data_bits: int
    parity: int
    stop_bits: int


# 表示 UartPairConfig 的稳定只读事实；只承载已解析数据，不执行 Wire 编解码、设备 I/O 或跨 IP 编排。
@dataclass(frozen=True)
class UartPairConfig:
    control_instance: int
    dut_instance: int
    peer_instance: int | None = None
    error_stimuli: frozenset[str] = frozenset()


# 表示一个逻辑 DUT 信号到外部示波器输入的 Bench 绑定；不包含测试期望或 IP 配置。
@dataclass(frozen=True)
class SignalObserverConfig:
    logical_signal: str
    instrument_name: str
    driver: str
    resource: str
    channel: int
    vertical_scale_v: float
    trigger_level_v: float
    probe_ratio: float | None
    timeout_s: float


# 表示一个逻辑 DUT 激励到外部脉冲输出的 Bench 绑定；不包含 Case 脉宽。
@dataclass(frozen=True)
class PulseStimulusConfig:
    logical_stimulus: str
    instrument_name: str
    driver: str
    resource: str
    output_channel: int
    amplitude_vpp: float
    offset_v: float
    timeout_s: float


# 表示目标 CPU 的真实 Debugger Bench 绑定；设备名和连接参数属于板级事实。
@dataclass(frozen=True)
class DebuggerConfig:
    driver: str
    executable: str
    device: str
    interface: str
    speed_khz: int
    probe_serial: str | None
    command_timeout_s: float


# 加载或描述 load serial target 对应的 Bench 强类型事实；只解析配置，不发送硬件命令，非法配置明确失败。
def load_serial_target(
    profile_path: str | Path,
    target_id: str,
    *,
    environment: dict[str, str] | None = None,
) -> SerialTargetConfig:

    expanded = _load_profile(profile_path, environment)
    try:
        target = expanded["targets"][target_id]
        transport = target["transport"]
    except (KeyError, TypeError) as exc:
        raise ConfigurationError(f"target {target_id!r} is not fully defined") from exc
    if transport.get("kind") != "serial":
        raise ConfigurationError(f"target {target_id!r} transport is not serial")

    try:
        config = SerialTargetConfig(
            target_id=target_id,
            chip_id=str(target["chip"]),
            firmware_build_id=(
                str(target["firmware_build_id"]) if "firmware_build_id" in target else None
            ),
            port=str(transport["port"]),
            baudrate=_parse_int_setting(transport["baud"], "baud"),
            bytesize=_parse_int_setting(transport.get("bytesize", 8), "bytesize"),
            parity=str(transport.get("parity", "N")),
            stopbits=_parse_int_setting(transport.get("stopbits", 1), "stopbits"),
            dtr=_parse_bool(transport.get("dtr", False), "dtr"),
            rts=_parse_bool(transport.get("rts", False), "rts"),
            request_timeout_s=float(transport.get("request_timeout_s", 1.0)),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigurationError(f"target {target_id!r} has invalid serial settings") from exc
    if (
        not config.chip_id
        or not config.port
        or config.baudrate <= 0
        or config.request_timeout_s <= 0
    ):
        raise ConfigurationError(f"target {target_id!r} has empty or non-positive serial settings")
    if not 5 <= config.bytesize <= 8:
        raise ConfigurationError(f"target {target_id!r} serial bytesize must be between 5 and 8")
    if config.parity not in _SERIAL_PARITIES:
        raise ConfigurationError(f"target {target_id!r} serial parity must be one of N/E/O/M/S")
    if config.stopbits not in (1, 2):
        raise ConfigurationError(f"target {target_id!r} serial stopbits must be 1 or 2")
    return config


# 加载或描述 load uart pair 对应的 Bench 强类型事实；只解析配置，不发送硬件命令，非法配置明确失败。
def load_uart_pair(
    profile_path: str | Path,
    target_id: str,
    *,
    environment: dict[str, str] | None = None,
) -> UartPairConfig:

    raw = _load_profile(profile_path, environment)
    try:
        target = raw["targets"][target_id]
        pair = target["ip_pairs"]["uart"]
    except (KeyError, TypeError) as exc:
        raise ConfigurationError(f"target {target_id!r} has no valid UART pair") from exc
    if not isinstance(pair, dict):
        raise ConfigurationError(f"target {target_id!r} UART pair must be a mapping")

    required = {"control_instance", "dut_instance"}
    allowed = required | {"peer_instance", "error_stimuli"}
    missing = required - set(pair)
    unknown = set(pair) - allowed
    if missing or unknown:
        details: list[str] = []
        if missing:
            details.append("missing " + ", ".join(sorted(missing)))
        if unknown:
            details.append("unknown " + ", ".join(sorted(unknown)))
        raise ConfigurationError(f"target {target_id!r} UART pair is invalid: {'; '.join(details)}")

    control_instance = _parse_uart_instance(pair["control_instance"], "control_instance")
    dut_instance = _parse_uart_instance(pair["dut_instance"], "dut_instance")
    peer_value = pair.get("peer_instance")
    peer_instance = (
        None if peer_value is None else _parse_uart_instance(peer_value, "peer_instance")
    )
    error_stimuli_value = pair.get("error_stimuli", [])
    if not isinstance(error_stimuli_value, list) or any(
        not isinstance(item, str) or not item for item in error_stimuli_value
    ):
        raise ConfigurationError(f"target {target_id!r} UART error_stimuli must be a string list")
    unknown_stimuli = set(error_stimuli_value) - _UART_ERROR_STIMULI
    if unknown_stimuli:
        raise ConfigurationError(
            f"target {target_id!r} UART error_stimuli contains unsupported "
            "stimulus: " + ", ".join(sorted(unknown_stimuli))
        )
    if control_instance == dut_instance:
        raise ConfigurationError(
            f"target {target_id!r} UART pair is invalid: "
            "control_instance and dut_instance must differ"
        )
    if peer_instance is not None and peer_instance in {
        control_instance,
        dut_instance,
    }:
        raise ConfigurationError(
            f"target {target_id!r} UART pair is invalid: "
            "peer_instance must differ from control_instance and "
            "dut_instance"
        )
    return UartPairConfig(
        control_instance=control_instance,
        dut_instance=dut_instance,
        peer_instance=peer_instance,
        error_stimuli=frozenset(error_stimuli_value),
    )


# 加载或描述 load dma peripheral pair 对应的 Bench 强类型事实；只解析配置，不发送硬件命令，非法配置明确失败。
def load_dma_peripheral_pair(
    profile_path: str | Path,
    target_id: str,
    *,
    environment: dict[str, str] | None = None,
) -> DmaPeripheralPairConfig:

    raw = _load_profile(profile_path, environment)
    try:
        pair = raw["targets"][target_id]["dma_peripheral_pair"]
        config = DmaPeripheralPairConfig(
            provider=str(pair["provider"]),
            controller_instance=int(pair["controller_instance"]),
            dma_port_instance=int(pair["dma_port_instance"]),
            peer_port_instance=int(pair["peer_port_instance"]),
            source_interface=int(pair.get("source_interface", 0)),
            destination_interface=int(pair.get("destination_interface", 1)),
            baudrate=int(pair.get("baud", 115200)),
            data_bits=int(pair.get("data_bits", 8)),
            parity=int(pair.get("parity", 0)),
            stop_bits=int(pair.get("stop_bits", 1)),
        )
    except KeyError as exc:
        missing = exc.args[0] if exc.args else "field"
        raise ConfigurationError(
            f"target {target_id!r} DMA peripheral pair is missing {missing!r}"
        ) from exc
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(f"target {target_id!r} has no valid DMA peripheral pair") from exc
    if (
        not config.provider
        or config.controller_instance < 0
        or config.dma_port_instance < 0
        or config.peer_port_instance < 0
        or config.dma_port_instance == config.peer_port_instance
        or not 0 <= config.source_interface <= 7
        or not 0 <= config.destination_interface <= 7
        or config.source_interface == config.destination_interface
        or config.baudrate <= 0
        or not 5 <= config.data_bits <= 8
        or config.parity not in (0, 1, 2)
        or config.stop_bits not in (1, 2)
    ):
        raise ConfigurationError(f"target {target_id!r} DMA peripheral pair is invalid")
    return config


# 加载一个逻辑信号的示波器 Bench 绑定；设备型号、资源和通道缺失时明确失败。
def load_signal_observer(
    profile_path: str | Path,
    target_id: str,
    logical_signal: str,
    *,
    environment: dict[str, str] | None = None,
) -> SignalObserverConfig:

    env = environment or dict(os.environ)
    raw = _load_profile(profile_path, env)
    try:
        binding = raw["targets"][target_id]["signal_observers"][logical_signal]
        instrument_name = str(binding["instrument"])
    except (KeyError, TypeError) as exc:
        raise ConfigurationError(
            f"target {target_id!r} has no signal observer for {logical_signal!r}"
        ) from exc
    if not isinstance(binding, dict):
        raise ConfigurationError(
            f"target {target_id!r} signal observer {logical_signal!r} must be a mapping"
        )

    environment_prefix = f"ET_INSTRUMENT_{instrument_name.upper()}"
    driver = env.get(f"{environment_prefix}_DRIVER", "")
    resource = env.get(f"{environment_prefix}_RESOURCE", "")
    try:
        channel = _parse_int_setting(binding["channel"], "signal observer channel")
        vertical_scale_v = _parse_positive_float(
            binding["vertical_scale_v"], "signal observer vertical_scale_v"
        )
        trigger_level_v = float(binding["trigger_level_v"])
        probe_value = binding.get("probe_ratio")
        probe_ratio = (
            None
            if probe_value is None
            else _parse_positive_float(probe_value, "signal observer probe_ratio")
        )
        timeout_s = _parse_positive_float(
            binding.get("timeout_s", 5.0), "signal observer timeout_s"
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigurationError(
            f"target {target_id!r} signal observer {logical_signal!r} is invalid"
        ) from exc
    if not instrument_name or not driver or not resource or channel <= 0:
        raise ConfigurationError(
            f"target {target_id!r} signal observer {logical_signal!r} is incomplete"
        )

    return SignalObserverConfig(
        logical_signal=logical_signal,
        instrument_name=instrument_name,
        driver=driver,
        resource=resource,
        channel=channel,
        vertical_scale_v=vertical_scale_v,
        trigger_level_v=trigger_level_v,
        probe_ratio=probe_ratio,
        timeout_s=timeout_s,
    )


# 加载一个逻辑脉冲激励的 Bench 绑定；设备型号、资源和输出通道均由环境显式提供。
def load_pulse_stimulus(
    profile_path: str | Path,
    target_id: str,
    logical_stimulus: str,
    *,
    environment: dict[str, str] | None = None,
) -> PulseStimulusConfig:

    env = environment or dict(os.environ)
    raw = _load_profile(profile_path, env)
    try:
        binding = raw["targets"][target_id]["pulse_stimuli"][logical_stimulus]
        instrument_name = str(binding["instrument"])
    except (KeyError, TypeError) as exc:
        raise ConfigurationError(
            f"target {target_id!r} has no pulse stimulus for {logical_stimulus!r}"
        ) from exc
    if not isinstance(binding, dict):
        raise ConfigurationError(
            f"target {target_id!r} pulse stimulus {logical_stimulus!r} must be a mapping"
        )

    environment_prefix = f"ET_INSTRUMENT_{instrument_name.upper()}"
    driver = env.get(f"{environment_prefix}_DRIVER", "")
    resource = env.get(f"{environment_prefix}_RESOURCE", "")
    try:
        output_channel = _parse_int_setting(
            binding["output_channel"], "pulse stimulus output_channel"
        )
        amplitude_vpp = _parse_positive_float(
            binding["amplitude_vpp"], "pulse stimulus amplitude_vpp"
        )
        offset_v = float(binding.get("offset_v", 0.0))
        timeout_s = _parse_positive_float(binding.get("timeout_s", 5.0), "pulse stimulus timeout_s")
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigurationError(
            f"target {target_id!r} pulse stimulus {logical_stimulus!r} is invalid"
        ) from exc
    if not instrument_name or not driver or not resource or output_channel <= 0:
        raise ConfigurationError(
            f"target {target_id!r} pulse stimulus {logical_stimulus!r} is incomplete"
        )

    return PulseStimulusConfig(
        logical_stimulus=logical_stimulus,
        instrument_name=instrument_name,
        driver=driver,
        resource=resource,
        output_channel=output_channel,
        amplitude_vpp=amplitude_vpp,
        offset_v=offset_v,
        timeout_s=timeout_s,
    )


# 加载目标的Debugger绑定；工具路径和探针身份来自运行环境，芯片连接事实来自Bench。
def load_debugger(
    profile_path: str | Path,
    target_id: str,
    *,
    environment: dict[str, str] | None = None,
) -> DebuggerConfig:

    env = environment or dict(os.environ)
    raw = _load_profile(profile_path, env)
    try:
        debugger = raw["targets"][target_id]["debugger"]
        driver = str(debugger["driver"])
        device = str(debugger["device"])
        interface = str(debugger.get("interface", "JTAG"))
        speed_khz = _parse_int_setting(debugger.get("speed_khz", 1000), "debugger speed_khz")
        command_timeout_s = _parse_positive_float(
            debugger.get("command_timeout_s", 10.0), "debugger command_timeout_s"
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigurationError(f"target {target_id!r} has no valid debugger binding") from exc

    executable = env.get("ET_TOOL_JLINK_EXECUTABLE", "")
    probe_serial_value = env.get("ET_DUT_DEBUG_PROBE_SERIAL", "").strip()
    probe_serial = probe_serial_value or None
    if not driver or not executable or not device or not interface or speed_khz <= 0:
        raise ConfigurationError(f"target {target_id!r} debugger binding is incomplete")

    return DebuggerConfig(
        driver=driver,
        executable=executable,
        device=device,
        interface=interface,
        speed_khz=speed_khz,
        probe_serial=probe_serial,
        command_timeout_s=command_timeout_s,
    )


def _parse_uart_instance(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ConfigurationError(f"UART pair {name} must be a non-negative integer")
    return value


def _load_profile(
    profile_path: str | Path,
    environment: dict[str, str] | None,
) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise ConfigurationError("PyYAML is required to load bench profiles") from exc

    path = Path(profile_path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigurationError(f"cannot read bench profile {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"invalid YAML in bench profile {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigurationError("bench profile root must be a mapping")
    return _expand_environment(raw, environment or dict(os.environ))


def _parse_bool(value: Any, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    raise ConfigurationError(f"serial setting {name!r} must be boolean")


# Parse an integral serial setting without truncating fractional YAML.
def _parse_int_setting(value: Any, name: str) -> int:

    if isinstance(value, bool):
        raise ConfigurationError(f"serial setting {name!r} must be an integer")
    if isinstance(value, float) and not value.is_integer():
        raise ConfigurationError(f"serial setting {name!r} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(f"serial setting {name!r} must be an integer") from exc


def _parse_positive_float(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise ConfigurationError(f"{name} must be a positive number")
    number = float(value)
    if number <= 0:
        raise ConfigurationError(f"{name} must be a positive number")
    return number


def _expand_environment(value: Any, environment: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _expand_environment(item, environment) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand_environment(item, environment) for item in value]
    if isinstance(value, str):
        match = _ENV_VALUE.match(value)
        if match:
            name = match.group(1)
            if name not in environment:
                raise ConfigurationError(f"bench profile requires environment variable {name}")
            return environment[name]
    return value
