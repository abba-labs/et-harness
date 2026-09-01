# RIGOL DM3068 主显示测量功能原子控制。
#
# 职责：映射 FUNCtion 子系统中基础测量功能选择和当前功能查询命令。
# 边界：只选择主测量功能，不配置量程、速率、数学运算或触发流程。
# 依赖：仅依赖公共 ScpiSession。

from __future__ import annotations

from ....common.scpi import ScpiSession


# 提供 DM3068 主显示基础测量功能的单命令选择和查询接口。
class Dm3068FunctionControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 查询当前主显示测量功能；只执行一次 FUNCtion? Query，不改变测量配置。
    def current_get(self) -> str:
        return self._session.query_text(":FUNCtion?").strip()

    # 选择电容测量功能；只发送 FUNCtion:CAPacitance，不配置量程或速率。
    def capacitance_select(self) -> None:
        self._session.write(":FUNCtion:CAPacitance")

    # 选择通断测量功能；只发送 FUNCtion:CONTinuity，不配置阈值或触发。
    def continuity_select(self) -> None:
        self._session.write(":FUNCtion:CONTinuity")

    # 选择交流电流测量功能；只发送 FUNCtion:CURRent:AC，不配置量程或速率。
    def current_ac_select(self) -> None:
        self._session.write(":FUNCtion:CURRent:AC")

    # 选择直流电流测量功能；只发送 FUNCtion:CURRent:DC，不配置量程或速率。
    def current_dc_select(self) -> None:
        self._session.write(":FUNCtion:CURRent:DC")

    # 选择二极管测量功能；只发送 FUNCtion:DIODe，不组合读取动作。
    def diode_select(self) -> None:
        self._session.write(":FUNCtion:DIODe")

    # 选择频率测量功能；只发送 FUNCtion:FREQuency，不配置门时间或量程。
    def frequency_select(self) -> None:
        self._session.write(":FUNCtion:FREQuency")

    # 选择四线电阻测量功能；只发送 FUNCtion:FRESistance，不配置量程或速率。
    def resistance_4wire_select(self) -> None:
        self._session.write(":FUNCtion:FRESistance")

    # 选择周期测量功能；只发送 FUNCtion:PERiod，不配置门时间或量程。
    def period_select(self) -> None:
        self._session.write(":FUNCtion:PERiod")

    # 选择两线电阻测量功能；只发送 FUNCtion:RESistance，不配置量程或速率。
    def resistance_2wire_select(self) -> None:
        self._session.write(":FUNCtion:RESistance")

    # 选择交流电压测量功能；只发送 FUNCtion:VOLTage:AC，不配置量程或速率。
    def voltage_ac_select(self) -> None:
        self._session.write(":FUNCtion:VOLTage:AC")

    # 选择直流电压测量功能；只发送 FUNCtion:VOLTage:DC，不配置量程或速率。
    def voltage_dc_select(self) -> None:
        self._session.write(":FUNCtion:VOLTage:DC")
