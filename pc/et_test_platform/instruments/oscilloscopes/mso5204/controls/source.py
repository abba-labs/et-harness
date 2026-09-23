# RIGOL MSO5204 built-in AWG atomic controls.
#
# 职责：用稳定命令表生成 AWG Source1/2 的单参数 set/get API，并保留 APPLY 原子动作。
# 边界：不自动打开输出、不缩放波形数据，也不把多个 AWG 配置步骤隐藏为 Driver 流程。
# 依赖：仅依赖公共 ScpiSession、Callable/Any 和本型号基础 SCPI 格式化与常用响应解析辅助函数。
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..._internal.scpi import ScpiSession
from ..validation import _command, _parse_bool, _parse_float, _parse_int

_SOURCE_FIELDS = (
    ("frequency", "FREQuency", "float"),
    ("phase", "PHASe", "float"),
    ("ramp_symmetry", "FUNCtion:RAMP:SYMMetry", "float"),
    ("amplitude", "VOLTage", "float"),
    ("offset", "VOLTage:OFFSet", "float"),
    ("pulse_duty_cycle", "PULSe:DCYCle", "float"),
    ("am_depth", "MOD:AM", "float"),
    ("am_internal_frequency", "MOD:AM:INTernal:FREQuency", "float"),
    ("fm_internal_frequency", "MOD:FM:INTernal:FREQuency", "float"),
    ("fm_deviation", "MOD:FM", "float"),
    ("sweep_time", "SWEep:STIMe", "float"),
    ("sweep_return_time", "SWEep:BTIMe", "float"),
    ("burst_delay", "BURSt:DELay", "float"),
    ("function", "FUNCtion", "text"),
    ("type", "TYPE", "text"),
    ("modulation_type", "MOD:TYPE", "text"),
    ("am_internal_function", "MOD:AM:INTernal:FUNCtion", "text"),
    ("fm_internal_function", "MOD:FM:INTernal:FUNCtion", "text"),
    ("sweep_type", "SWEep:TYPE", "text"),
    ("burst_type", "BURSt:TYPE", "text"),
    ("output_impedance", "OUTPut:IMPedance", "text"),
    ("burst_cycles", "BURSt:CYCLes", "int"),
    ("output_enabled", "OUTPut", "bool"),
)


def _channel(value: int) -> int:
    channel = int(value)
    if channel not in {1, 2}:
        raise ValueError("AWG channel must be 1 or 2")
    return channel


def _parse(kind: str, value: str) -> str | float | int | bool:
    if kind == "bool":
        return _parse_bool(value)
    if kind == "float":
        return _parse_float(value)
    if kind == "int":
        return _parse_int(value)
    return value


def _make_setter(suffix: str) -> Callable[[Any, int, Any], None]:
    def _setter(self: Any, channel: int, value: Any) -> None:
        self._session.write(_command(f":SOURce{_channel(channel)}:{suffix}", value))

    return _setter


def _make_getter(suffix: str, kind: str) -> Callable[[Any, int], str | float | int | bool]:
    def _getter(self: Any, channel: int) -> str | float | int | bool:
        response = self._session.query_text(f":SOURce{_channel(channel)}:{suffix}?")
        return _parse(kind, response)

    return _getter


# 提供内置 AWG Source1/2 的单参数和 APPLY 原子接口；构造对象时不会打开输出或执行波形配置流程。
class Mso5204SourceControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 使指定 AWG 通道的相位参考重新对齐；只发送 PHASe:INITiate，不修改相位值。
    def phase_align(self, channel: int) -> None:
        self._session.write(f":SOURce{_channel(channel)}:PHASe:INITiate")

    # 查询指定 AWG 通道当前 APPLY 配置摘要；不改变函数、频率、幅度或输出状态。
    def apply_get(self, channel: int) -> str:
        return self._session.query_text(f":SOURce{_channel(channel)}:APPLy?")

    def _apply(self, channel: int, waveform: str, *args: object) -> None:
        self._session.write(_command(f":SOURce{_channel(channel)}:APPLy:{waveform}", *args))

    def _apply_optional(self, channel: int, waveform: str, *values: float | None) -> None:
        args: list[object] = []
        seen_none = False
        for value in values:
            if value is None:
                seen_none = True
                continue
            if seen_none:
                raise ValueError("AWG APPLY optional arguments must be contiguous")
            args.append(value)
        self._apply(channel, waveform, *args)

    # 单条命令应用噪声波形及可选幅度/偏置；不自动使能 AWG 输出。
    def apply_noise(
        self,
        channel: int,
        amplitude: float | None = None,
        offset: float | None = None,
    ) -> None:
        args: tuple[object, ...] = ()
        if amplitude is not None:
            args = (amplitude,)
            if offset is not None:
                args += (offset,)
        self._apply(channel, "NOISe", *args)

    # 单条命令应用脉冲波及连续可选参数；不自动使能输出或配置 Burst。
    def apply_pulse(
        self,
        channel: int,
        frequency: float | None = None,
        amplitude: float | None = None,
        offset: float | None = None,
        phase: float | None = None,
    ) -> None:
        self._apply_optional(channel, "PULSe", frequency, amplitude, offset, phase)

    # 单条命令应用斜坡波及连续可选参数；不自动修改 Ramp Symmetry。
    def apply_ramp(
        self,
        channel: int,
        frequency: float | None = None,
        amplitude: float | None = None,
        offset: float | None = None,
        phase: float | None = None,
    ) -> None:
        self._apply_optional(channel, "RAMP", frequency, amplitude, offset, phase)

    # 单条命令应用正弦波及连续可选参数；不自动使能输出或执行相位对齐。
    def apply_sine(
        self,
        channel: int,
        frequency: float | None = None,
        amplitude: float | None = None,
        offset: float | None = None,
        phase: float | None = None,
    ) -> None:
        self._apply_optional(channel, "SINusoid", frequency, amplitude, offset, phase)

    # 单条命令应用方波及连续可选参数；不自动修改 Duty Cycle 或输出状态。
    def apply_square(
        self,
        channel: int,
        frequency: float | None = None,
        amplitude: float | None = None,
        offset: float | None = None,
        phase: float | None = None,
    ) -> None:
        self._apply_optional(channel, "SQUare", frequency, amplitude, offset, phase)

    # 单条命令应用用户任意波及连续可选参数；不负责下载任意波形数据。
    def apply_user(
        self,
        channel: int,
        frequency: float | None = None,
        amplitude: float | None = None,
        offset: float | None = None,
        phase: float | None = None,
    ) -> None:
        self._apply_optional(channel, "USER", frequency, amplitude, offset, phase)


for _name, _suffix, _kind in _SOURCE_FIELDS:
    setattr(Mso5204SourceControl, f"{_name}_set", _make_setter(_suffix))
    setattr(Mso5204SourceControl, f"{_name}_get", _make_getter(_suffix, _kind))
