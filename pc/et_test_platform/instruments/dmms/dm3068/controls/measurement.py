# RIGOL DM3068 MEASure 原子控制。
#
# 职责：映射原生 MEASure 子系统的测量模式、量程配置和即时结果查询命令。
# 边界：每个方法最多产生一条 SCPI；不自动切换 FUNCtion、不改变 Trigger 或 Math。
# 依赖：仅依赖公共 ScpiSession、本型号 MeasurementMode/RangeKeyword 与 validation。

from __future__ import annotations

from ....common.scpi import ScpiSession
from ..models import Dm3068MeasurementMode, Dm3068RangeKeyword
from ..validation import _nonempty_token, _parse_bool, _parse_float, _parse_int, _range_token

RangeValue = int | Dm3068RangeKeyword


# 提供 DM3068 MEASure 子系统的逐项量程配置和测量查询接口。
class Dm3068MeasurementControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 查询当前触发配置下是否已获得新数据；只执行一次 MEASure? Query。
    def new_data_get(self) -> bool:
        return _parse_bool(self._session.query_text(":MEASure?"))

    # 设置 AUTO 或 MANU 测量类型；离散参数在写入前拒绝其他字符串。
    def mode_set(self, mode: Dm3068MeasurementMode | str) -> None:
        token = (
            mode.value if isinstance(mode, Dm3068MeasurementMode) else _nonempty_token(mode, "mode")
        )
        normalized = token.strip().upper()
        if normalized not in {"AUTO", "MANU"}:
            raise ValueError("measurement mode must be AUTO or MANU")
        self._session.write(f":MEASure {normalized}")

    # 查询当前直流电压测量结果；只执行一次 MEASure:VOLTage:DC? Query。
    def voltage_dc_get(self) -> float:
        return _parse_float(self._session.query_text(":MEASure:VOLTage:DC?"))

    # 设置直流电压量程索引或 MIN/MAX/DEF；只发送一条量程配置命令。
    def voltage_dc_range_set(self, value: RangeValue) -> None:
        self._session.write(f":MEASure:VOLTage:DC {_range_token(value)}")

    # 查询当前直流电压量程索引；只执行一次 RANGe? Query。
    def voltage_dc_range_get(self) -> int:
        return _parse_int(self._session.query_text(":MEASure:VOLTage:DC:RANGe?"))

    # 设置直流电压输入阻抗关键字；只写入 IMPEdance，不调整量程。
    def voltage_dc_impedance_set(self, impedance: str) -> None:
        token = _nonempty_token(impedance, "impedance")
        self._session.write(f":MEASure:VOLTage:DC:IMPEdance {token}")

    # 查询直流电压输入阻抗关键字；只读取当前 IMPEdance? 配置。
    def voltage_dc_impedance_get(self) -> str:
        return self._session.query_text(":MEASure:VOLTage:DC:IMPEdance?").strip()

    # 查询当前交流电压测量结果；只执行一次 MEASure:VOLTage:AC? Query。
    def voltage_ac_get(self) -> float:
        return _parse_float(self._session.query_text(":MEASure:VOLTage:AC?"))

    # 设置交流电压量程索引或 MIN/MAX/DEF；只发送一条量程配置命令。
    def voltage_ac_range_set(self, value: RangeValue) -> None:
        self._session.write(f":MEASure:VOLTage:AC {_range_token(value)}")

    # 查询当前交流电压量程索引；只执行一次 RANGe? Query。
    def voltage_ac_range_get(self) -> int:
        return _parse_int(self._session.query_text(":MEASure:VOLTage:AC:RANGe?"))

    # 查询当前直流电流测量结果；只执行一次 MEASure:CURRent:DC? Query。
    def current_dc_get(self) -> float:
        return _parse_float(self._session.query_text(":MEASure:CURRent:DC?"))

    # 设置直流电流量程索引或 MIN/MAX/DEF；只发送一条量程配置命令。
    def current_dc_range_set(self, value: RangeValue) -> None:
        self._session.write(f":MEASure:CURRent:DC {_range_token(value)}")

    # 查询当前直流电流量程索引；只执行一次 RANGe? Query。
    def current_dc_range_get(self) -> int:
        return _parse_int(self._session.query_text(":MEASure:CURRent:DC:RANGe?"))

    # 查询当前交流电流测量结果；只执行一次 MEASure:CURRent:AC? Query。
    def current_ac_get(self) -> float:
        return _parse_float(self._session.query_text(":MEASure:CURRent:AC?"))

    # 设置交流电流量程索引或 MIN/MAX/DEF；只发送一条量程配置命令。
    def current_ac_range_set(self, value: RangeValue) -> None:
        self._session.write(f":MEASure:CURRent:AC {_range_token(value)}")

    # 查询当前交流电流量程索引；只执行一次 RANGe? Query。
    def current_ac_range_get(self) -> int:
        return _parse_int(self._session.query_text(":MEASure:CURRent:AC:RANGe?"))

    # 查询当前两线电阻测量结果；只执行一次 MEASure:RESistance? Query。
    def resistance_2wire_get(self) -> float:
        return _parse_float(self._session.query_text(":MEASure:RESistance?"))

    # 设置两线电阻量程索引或 MIN/MAX/DEF；只发送一条量程配置命令。
    def resistance_2wire_range_set(self, value: RangeValue) -> None:
        self._session.write(f":MEASure:RESistance {_range_token(value)}")

    # 查询当前两线电阻量程索引；只执行一次 RANGe? Query。
    def resistance_2wire_range_get(self) -> int:
        return _parse_int(self._session.query_text(":MEASure:RESistance:RANGe?"))

    # 查询当前四线电阻测量结果；只执行一次 MEASure:FRESistance? Query。
    def resistance_4wire_get(self) -> float:
        return _parse_float(self._session.query_text(":MEASure:FRESistance?"))

    # 设置四线电阻量程索引或 MIN/MAX/DEF；只发送一条量程配置命令。
    def resistance_4wire_range_set(self, value: RangeValue) -> None:
        self._session.write(f":MEASure:FRESistance {_range_token(value)}")

    # 查询当前四线电阻量程索引；只执行一次 RANGe? Query。
    def resistance_4wire_range_get(self) -> int:
        return _parse_int(self._session.query_text(":MEASure:FRESistance:RANGe?"))

    # 查询当前频率测量结果；只执行一次 MEASure:FREQuency? Query。
    def frequency_get(self) -> float:
        return _parse_float(self._session.query_text(":MEASure:FREQuency?"))

    # 设置频率测量量程索引或 MIN/MAX/DEF；只发送一条量程配置命令。
    def frequency_range_set(self, value: RangeValue) -> None:
        self._session.write(f":MEASure:FREQuency {_range_token(value)}")

    # 查询当前频率测量量程索引；只执行一次 RANGe? Query。
    def frequency_range_get(self) -> int:
        return _parse_int(self._session.query_text(":MEASure:FREQuency:RANGe?"))

    # 查询当前周期测量结果；只执行一次 MEASure:PERiod? Query。
    def period_get(self) -> float:
        return _parse_float(self._session.query_text(":MEASure:PERiod?"))

    # 设置周期测量量程索引或 MIN/MAX/DEF；只发送一条量程配置命令。
    def period_range_set(self, value: RangeValue) -> None:
        self._session.write(f":MEASure:PERiod {_range_token(value)}")

    # 查询当前周期测量量程索引；只执行一次 RANGe? Query。
    def period_range_get(self) -> int:
        return _parse_int(self._session.query_text(":MEASure:PERiod:RANGe?"))

    # 查询当前电容测量结果；只执行一次 MEASure:CAPacitance? Query。
    def capacitance_get(self) -> float:
        return _parse_float(self._session.query_text(":MEASure:CAPacitance?"))

    # 设置电容量程索引或 MIN/MAX/DEF；只发送一条量程配置命令。
    def capacitance_range_set(self, value: RangeValue) -> None:
        self._session.write(f":MEASure:CAPacitance {_range_token(value)}")

    # 查询当前电容量程索引；只执行一次 RANGe? Query。
    def capacitance_range_get(self) -> int:
        return _parse_int(self._session.query_text(":MEASure:CAPacitance:RANGe?"))

    # 查询当前通断测量结果；只执行一次 MEASure:CONTinuity? Query。
    def continuity_get(self) -> float:
        return _parse_float(self._session.query_text(":MEASure:CONTinuity?"))

    # 设置通断测量量程索引或 MIN/MAX/DEF；只发送一条 CONTinuity 配置命令。
    def continuity_range_set(self, value: RangeValue) -> None:
        self._session.write(f":MEASure:CONTinuity {_range_token(value)}")

    # 查询当前二极管测量结果；只执行一次 MEASure:DIODe? Query。
    def diode_get(self) -> float:
        return _parse_float(self._session.query_text(":MEASure:DIODe?"))
