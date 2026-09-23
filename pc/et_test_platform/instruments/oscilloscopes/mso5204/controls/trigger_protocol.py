# RIGOL MSO5204 协议触发原子控制。
#
# 职责：映射 RS232、I2C、CAN、SPI、FlexRay、I2S、LIN 和 MIL-STD-1553 触发命令，
#       并从固定注册表生成一项命令对应一个 set/get API。
# 边界：每个生成 API 只发送或查询一条 SCPI，不自动切换触发模式或配置 BUS 解码。
# 依赖：仅依赖公共 ScpiSession 和本型号 SCPI 格式化/解析辅助函数。

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..._internal.scpi import ScpiSession
from ..validation import _command, _parse_float, _parse_int, _query_command

_PROTOCOL_FIELDS = (
    ("rs232_source", ":TRIGger:RS232:SOURce", "text"),
    ("rs232_condition", ":TRIGger:RS232:WHEN", "text"),
    ("rs232_parity", ":TRIGger:RS232:PARity", "text"),
    ("rs232_stop_bits", ":TRIGger:RS232:STOP", "text"),
    ("rs232_data", ":TRIGger:RS232:DATA", "int"),
    ("rs232_data_width", ":TRIGger:RS232:WIDTh", "int"),
    ("rs232_baud", ":TRIGger:RS232:BAUD", "int"),
    ("rs232_level", ":TRIGger:RS232:LEVel", "float"),
    ("iic_scl_source", ":TRIGger:IIC:SCL", "text"),
    ("iic_sda_source", ":TRIGger:IIC:SDA", "text"),
    ("iic_condition", ":TRIGger:IIC:WHEN", "text"),
    ("iic_address_width", ":TRIGger:IIC:AWIDth", "int"),
    ("iic_address", ":TRIGger:IIC:ADDRess", "int"),
    ("iic_direction", ":TRIGger:IIC:DIRection", "text"),
    ("iic_data", ":TRIGger:IIC:DATA", "int"),
    ("iic_clock_level", ":TRIGger:IIC:CLEVel", "float"),
    ("iic_data_level", ":TRIGger:IIC:DLEVel", "float"),
    ("iic_data_bytes", ":TRIGger:IIC:DBYTes", "int"),
    ("can_baud", ":TRIGger:CAN:BAUD", "int"),
    ("can_source", ":TRIGger:CAN:SOURce", "text"),
    ("can_signal_type", ":TRIGger:CAN:STYPe", "text"),
    ("can_condition", ":TRIGger:CAN:WHEN", "text"),
    ("can_sample_point", ":TRIGger:CAN:SPOint", "int"),
    ("can_level", ":TRIGger:CAN:LEVel", "float"),
    ("spi_clock_source", ":TRIGger:SPI:SCL", "text"),
    ("spi_data_source", ":TRIGger:SPI:SDA", "text"),
    ("spi_condition", ":TRIGger:SPI:WHEN", "text"),
    ("spi_data_width", ":TRIGger:SPI:WIDTh", "int"),
    ("spi_data", ":TRIGger:SPI:DATA", "int"),
    ("spi_timeout", ":TRIGger:SPI:TIMeout", "float"),
    ("spi_clock_slope", ":TRIGger:SPI:SLOPe", "text"),
    ("spi_clock_level", ":TRIGger:SPI:CLEVel", "float"),
    ("spi_data_level", ":TRIGger:SPI:DLEVel", "float"),
    ("spi_select_level", ":TRIGger:SPI:SLEVel", "float"),
    ("spi_mode", ":TRIGger:SPI:MODE", "text"),
    ("spi_chip_select_source", ":TRIGger:SPI:CS", "text"),
    ("flexray_baud", ":TRIGger:FLEXray:BAUD", "int"),
    ("flexray_level", ":TRIGger:FLEXray:LEVel", "float"),
    ("flexray_source", ":TRIGger:FLEXray:SOURce", "text"),
    ("flexray_condition", ":TRIGger:FLEXray:WHEN", "text"),
    ("iis_alignment", ":TRIGger:IIS:ALIGnment", "text"),
    ("iis_clock_slope", ":TRIGger:IIS:CLOCk:SLOPe", "text"),
    ("iis_clock_source", ":TRIGger:IIS:SOURce:CLOCk", "text"),
    ("iis_data_source", ":TRIGger:IIS:SOURce:DATA", "text"),
    ("iis_word_select_source", ":TRIGger:IIS:SOURce:WSELect", "text"),
    ("iis_condition", ":TRIGger:IIS:WHEN", "text"),
    ("iis_audio_channel", ":TRIGger:IIS:AUDio", "text"),
    ("iis_data", ":TRIGger:IIS:DATA", "int"),
    ("lin_source", ":TRIGger:LIN:SOURce", "text"),
    ("lin_id", ":TRIGger:LIN:ID", "int"),
    ("lin_baud", ":TRIGger:LIN:BAUD", "int"),
    ("lin_standard", ":TRIGger:LIN:STANdard", "text"),
    ("lin_sample_point", ":TRIGger:LIN:SAMPlepoint", "int"),
    ("lin_condition", ":TRIGger:LIN:WHEN", "text"),
    ("lin_level", ":TRIGger:LIN:LEVel", "float"),
    ("m1553_source", ":TRIGger:M1553:SOURce", "text"),
    ("m1553_condition", ":TRIGger:M1553:WHEN", "text"),
    ("m1553_polarity", ":TRIGger:M1553:POLarity", "text"),
    ("m1553_upper_level", ":TRIGger:M1553:ALEVel", "float"),
    ("m1553_lower_level", ":TRIGger:M1553:BLEVel", "float"),
)


def _parse_response(kind: str, value: str) -> str | float | int:
    if kind == "float":
        return _parse_float(value)
    if kind == "int":
        return _parse_int(value)
    return value


def _make_setter(header: str) -> Callable[[Any, Any], None]:
    def _setter(self: Any, value: Any) -> None:
        self._session.write(_command(header, value))

    return _setter


def _make_getter(header: str, kind: str) -> Callable[[Any], str | float | int]:
    def _getter(self: Any) -> str | float | int:
        return _parse_response(kind, self._session.query_text(_query_command(header)))

    return _getter


# 提供协议触发子系统的稳定单命令访问；所有 set/get API 由下方不可变命令注册表生成。
class Mso5204ProtocolTriggerControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session


def _install_protocol_apis() -> None:
    for name, header, kind in _PROTOCOL_FIELDS:
        setter = _make_setter(header)
        getter = _make_getter(header, kind)
        setter.__name__ = f"{name}_set"
        getter.__name__ = f"{name}_get"
        setattr(Mso5204ProtocolTriggerControl, setter.__name__, setter)
        setattr(Mso5204ProtocolTriggerControl, getter.__name__, getter)


_install_protocol_apis()
