# RIGOL DM3068 RATE 测量速率原子控制。
#
# 职责：映射各基础测量功能和 Any Sensor 的 RATE 单条设置/查询命令。
# 边界：不选择测量功能、不修改量程，也不把速率设置组合到采样流程。
# 依赖：仅依赖公共 ScpiSession 和 Dm3068Rate 枚举。

from __future__ import annotations

from ....common.scpi import ScpiSession
from ..models import Dm3068Rate


# 提供 DM3068 原生 RATE 子系统中各测量类型的单命令设置和查询接口。
class Dm3068RateControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 设置直流电压测量速率；只写入 RATE:VOLTage:DC，不改变量程或触发源。
    def voltage_dc_set(self, rate: Dm3068Rate) -> None:
        self._session.write(f":RATE:VOLTage:DC {rate.value}")

    # 查询直流电压测量速率；只读取 RATE:VOLTage:DC? 当前关键字。
    def voltage_dc_get(self) -> str:
        return self._session.query_text(":RATE:VOLTage:DC?").strip()

    # 设置交流电压测量速率；只写入 RATE:VOLTage:AC，不改变量程或触发源。
    def voltage_ac_set(self, rate: Dm3068Rate) -> None:
        self._session.write(f":RATE:VOLTage:AC {rate.value}")

    # 查询交流电压测量速率；只读取 RATE:VOLTage:AC? 当前关键字。
    def voltage_ac_get(self) -> str:
        return self._session.query_text(":RATE:VOLTage:AC?").strip()

    # 设置直流电流测量速率；只写入 RATE:CURRent:DC，不改变量程或触发源。
    def current_dc_set(self, rate: Dm3068Rate) -> None:
        self._session.write(f":RATE:CURRent:DC {rate.value}")

    # 查询直流电流测量速率；只读取 RATE:CURRent:DC? 当前关键字。
    def current_dc_get(self) -> str:
        return self._session.query_text(":RATE:CURRent:DC?").strip()

    # 设置交流电流测量速率；只写入 RATE:CURRent:AC，不改变量程或触发源。
    def current_ac_set(self, rate: Dm3068Rate) -> None:
        self._session.write(f":RATE:CURRent:AC {rate.value}")

    # 查询交流电流测量速率；只读取 RATE:CURRent:AC? 当前关键字。
    def current_ac_get(self) -> str:
        return self._session.query_text(":RATE:CURRent:AC?").strip()

    # 设置两线电阻测量速率；只写入 RATE:RESistance，不改变量程或触发源。
    def resistance_2wire_set(self, rate: Dm3068Rate) -> None:
        self._session.write(f":RATE:RESistance {rate.value}")

    # 查询两线电阻测量速率；只读取 RATE:RESistance? 当前关键字。
    def resistance_2wire_get(self) -> str:
        return self._session.query_text(":RATE:RESistance?").strip()

    # 设置四线电阻测量速率；只写入 RATE:FRESistance，不改变量程或触发源。
    def resistance_4wire_set(self, rate: Dm3068Rate) -> None:
        self._session.write(f":RATE:FRESistance {rate.value}")

    # 查询四线电阻测量速率；只读取 RATE:FRESistance? 当前关键字。
    def resistance_4wire_get(self) -> str:
        return self._session.query_text(":RATE:FRESistance?").strip()

    # 设置 Any Sensor 测量速率；只写入 RATE:SENSor，不配置传感器本身。
    def sensor_set(self, rate: Dm3068Rate) -> None:
        self._session.write(f":RATE:SENSor {rate.value}")

    # 查询 Any Sensor 测量速率；只读取 RATE:SENSor? 当前关键字。
    def sensor_get(self) -> str:
        return self._session.query_text(":RATE:SENSor?").strip()
