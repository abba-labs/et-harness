# RIGOL MSO5204 总线解码原子控制。
#
# 职责：完整映射 BUS1..BUS4 的公共、Parallel、RS232、I2C、SPI、CAN、FlexRay、LIN、
#       I2S 和 MIL-STD-1553 解码命令，并生成一项命令对应一个 set/get API。
# 边界：每个生成 API 只操作一个 BUS 的一项参数，不自动打开总线、切换协议或配置触发器。
# 依赖：仅依赖公共 ScpiSession 和本型号 SCPI 格式化/解析辅助函数。

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..._internal.scpi import ScpiSession
from ..validation import _command, _parse_bool, _parse_float, _parse_int, _query_command

_BUS_FIELDS = (
    ("mode", "MODE", "text"),
    ("display", "DISPlay", "bool"),
    ("format", "FORMat", "text"),
    ("event_enabled", "EVENt", "bool"),
    ("event_format", "EVENt:FORMat", "text"),
    ("event_view", "EVENt:VIEW", "text"),
    ("label_enabled", "LABel", "bool"),
    ("position", "POSition", "int"),
    ("parallel_bus_source", "PARallel:BUS", "text"),
    ("parallel_clock_source", "PARallel:CLK", "text"),
    ("parallel_clock_slope", "PARallel:SLOPe", "text"),
    ("parallel_width", "PARallel:WIDTh", "int"),
    ("parallel_bitx", "PARallel:BITX", "int"),
    ("parallel_source", "PARallel:SOURce", "text"),
    ("parallel_polarity", "PARallel:POLarity", "text"),
    ("parallel_noise_reject", "PARallel:NREJect", "bool"),
    ("parallel_noise_reject_time", "PARallel:NRTime", "float"),
    ("rs232_tx_source", "RS232:TX", "text"),
    ("rs232_rx_source", "RS232:RX", "text"),
    ("rs232_polarity", "RS232:POLarity", "text"),
    ("rs232_endian", "RS232:ENDian", "text"),
    ("rs232_baud", "RS232:BAUD", "int"),
    ("rs232_data_bits", "RS232:DBITs", "int"),
    ("rs232_stop_bits", "RS232:SBITs", "text"),
    ("rs232_parity", "RS232:PARity", "text"),
    ("rs232_packet_enabled", "RS232:PACKet", "bool"),
    ("rs232_packet_end", "RS232:PEND", "int"),
    ("iic_clock_source", "IIC:SCLK:SOURce", "text"),
    ("iic_data_source", "IIC:SDA:SOURce", "text"),
    ("iic_address", "IIC:ADDRess", "text"),
    ("spi_clock_source", "SPI:SCLK:SOURce", "text"),
    ("spi_clock_slope", "SPI:SCLK:SLOPe", "text"),
    ("spi_miso_source", "SPI:MISO:SOURce", "text"),
    ("spi_miso_polarity", "SPI:MISO:POLarity", "text"),
    ("spi_mosi_source", "SPI:MOSI:SOURce", "text"),
    ("spi_mosi_polarity", "SPI:MOSI:POLarity", "text"),
    ("spi_data_bits", "SPI:DBITs", "int"),
    ("spi_endian", "SPI:ENDian", "text"),
    ("spi_mode", "SPI:MODE", "text"),
    ("spi_timeout", "SPI:TIMeout:TIME", "float"),
    ("spi_select_source", "SPI:SS:SOURce", "text"),
    ("spi_select_polarity", "SPI:SS:POLarity", "text"),
    ("can_source", "CAN:SOURce", "text"),
    ("can_signal_type", "CAN:STYPe", "text"),
    ("can_baud", "CAN:BAUD", "int"),
    ("can_sample_point", "CAN:SPOint", "int"),
    ("flexray_baud", "FLEXray:BAUD", "int"),
    ("flexray_source", "FLEXray:SOURce", "text"),
    ("flexray_sample_point", "FLEXray:SPOint", "int"),
    ("flexray_signal_type", "FLEXray:STYPe", "text"),
    ("lin_baud", "LIN:BAUD", "int"),
    ("lin_polarity", "LIN:POLarity", "bool"),
    ("lin_source", "LIN:SOURce", "text"),
    ("lin_standard", "LIN:STANdard", "text"),
    ("iis_clock_source", "IIS:SOURce:CLOCk", "text"),
    ("iis_data_source", "IIS:SOURce:DATA", "text"),
    ("iis_word_select_source", "IIS:SOURce:WSELect", "text"),
    ("iis_alignment", "IIS:ALIGnment", "text"),
    ("iis_clock_slope", "IIS:CLOCk:SLOPe", "text"),
    ("iis_receive_width", "IIS:RWIDth", "int"),
    ("m1553_source", "M1553:SOURce", "text"),
)


def _validate_bus(bus: int) -> int:
    number = int(bus)
    if number not in {1, 2, 3, 4}:
        raise ValueError("MSO5204 decode bus must be 1..4")
    return number


def _parse_response(kind: str, value: str) -> str | float | int | bool:
    if kind == "float":
        return _parse_float(value)
    if kind == "int":
        return _parse_int(value)
    if kind == "bool":
        return _parse_bool(value)
    return value


def _make_setter(suffix: str) -> Callable[[Any, int, Any], None]:
    def _setter(self: Any, bus: int, value: Any) -> None:
        self._session.write(_command(self._header(bus, suffix), value))

    return _setter


def _make_getter(
    suffix: str,
    kind: str,
) -> Callable[[Any, int], str | float | int | bool]:
    def _getter(self: Any, bus: int) -> str | float | int | bool:
        response = self._session.query_text(_query_command(self._header(bus, suffix)))
        return _parse_response(kind, response)

    return _getter


# 提供四路协议解码总线的稳定单命令访问；标量 set/get API 由固定 BUS 命令注册表生成。
class Mso5204BusControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    def _header(self, bus: int, suffix: str) -> str:
        return f":BUS{_validate_bus(bus)}:{suffix}"

    # 读取指定 BUS 的事件表数据块；返回去除 IEEE488.2 block header 后的原始有效负载。
    def event_data_get(self, bus: int, *, timeout_s: float | None = None) -> bytes:
        return self._session.query_bytes(self._header(bus, "DATA?"), timeout_s=timeout_s)

    # 导出指定 BUS 的事件表 CSV 到示波器本地路径；只执行一次 EEXPort 命令。
    def event_export(self, bus: int, path: str) -> None:
        normalized = path.strip()
        if not normalized or "\r" in normalized or "\n" in normalized:
            raise ValueError("bus export path must be one non-empty line")
        self._session.write(_command(self._header(bus, "EEXPort"), normalized))

    # 设置指定 BUS 解码源类型对应的门限；只修改一个 threshold type 的电平。
    def threshold_set(self, bus: int, threshold_type: str, level: float) -> None:
        self._session.write(_command(self._header(bus, "THReshold"), level, threshold_type))

    # 查询指定 BUS 解码源类型对应的当前门限；只执行一次带 type 参数的 Query。
    def threshold_get(self, bus: int, threshold_type: str) -> float:
        response = self._session.query_text(
            _query_command(self._header(bus, "THReshold"), threshold_type)
        )
        return _parse_float(response)


def _install_bus_apis() -> None:
    for name, suffix, kind in _BUS_FIELDS:
        setter = _make_setter(suffix)
        getter = _make_getter(suffix, kind)
        setter.__name__ = f"{name}_set"
        getter.__name__ = f"{name}_get"
        setattr(Mso5204BusControl, setter.__name__, setter)
        setattr(Mso5204BusControl, getter.__name__, getter)


_install_bus_apis()
