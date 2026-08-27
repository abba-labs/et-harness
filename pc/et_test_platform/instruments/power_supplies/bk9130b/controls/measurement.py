# B&K Precision 9130B 输出测量查询。
#
# 职责：映射当前通道和三通道电压、电流、功率的单次测量查询。
# 边界：不改变量程或输出、不做统计，也不根据测量结果给出测试 PASS/FAIL。
# 依赖：仅依赖 ScpiSession 和 Validation。

from __future__ import annotations

from ....common.scpi import ScpiSession
from ..validation import parse_float_tuple


# 提供 9130B 测量单查询 API；每次调用只读取一条仪器响应。
class Bk9130bMeasurementControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 查询当前选中通道的实际输出电压；不会改变电压设定值。
    def voltage_get(self) -> float:
        return float(self._session.query_text("MEASure:SCALar:VOLTage:DC?"))

    # 查询当前选中通道的实际输出电流；不会改变电流设定值。
    def current_get(self) -> float:
        return float(self._session.query_text("MEASure:SCALar:CURRent:DC?"))

    # 查询当前选中通道的实际输出功率；不会修改任何输出配置。
    def power_get(self) -> float:
        return float(self._session.query_text("MEASure:SCALar:POWer:DC?"))

    # 一次查询三个通道的实际输出电流；返回顺序固定为 CH1、CH2、CH3。
    def all_currents_get(self) -> tuple[float, float, float]:
        values = parse_float_tuple(
            self._session.query_text("MEASure:SCALar:CURRent:ALL:DC?"),
            3,
            "CURR ALL",
        )
        return values[0], values[1], values[2]

    # 一次查询三个通道的实际输出电压；返回顺序固定为 CH1、CH2、CH3。
    def all_voltages_get(self) -> tuple[float, float, float]:
        values = parse_float_tuple(
            self._session.query_text("MEASure:SCALar:VOLTage:ALL:DC?"),
            3,
            "VOLT ALL",
        )
        return values[0], values[1], values[2]
