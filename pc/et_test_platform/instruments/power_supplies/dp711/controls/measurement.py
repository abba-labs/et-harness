# RIGOL DP711 输出端测量控制。
#
# 职责：把 MEASure 查询映射为电压、电流、功率和一次全量测量 API。
# 边界：不修改输出配置、不做量程判断或测试断言。
# 依赖：仅依赖 ScpiSession、本型号 Measurement Model 和响应解析。

from __future__ import annotations

from ....common.scpi import ScpiSession
from ..models import Dp711Measurement
from ..validation import parse_measurement


# 提供 DP711 测量查询；每个方法只发送一条查询命令。
class Dp711MeasurementControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 一次查询输出端电压、电流和功率；查询或解析过程不会修改仪器配置。
    def all_get(self) -> Dp711Measurement:
        return parse_measurement(self._session.query_text(":MEASure:ALL? CH1"))

    # 查询输出端实际电流，单位 A；查询或解析过程不会修改仪器配置。
    def current_get(self) -> float:
        return float(self._session.query_text(":MEASure:CURRent? CH1"))

    # 查询输出端实际功率，单位 W；查询或解析过程不会修改仪器配置。
    def power_get(self) -> float:
        return float(self._session.query_text(":MEASure:POWEr? CH1"))

    # 查询输出端实际电压，单位 V；查询或解析过程不会修改仪器配置。
    def voltage_get(self) -> float:
        return float(self._session.query_text(":MEASure:VOLTage? CH1"))
