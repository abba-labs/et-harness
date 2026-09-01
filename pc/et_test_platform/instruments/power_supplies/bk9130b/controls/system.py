# B&K Precision 9130B 系统控制命令。
#
# 职责：映射错误、版本、远程/本地、GPIB、蜂鸣器、接口和存储组等系统原子命令。
# 边界：不重连物理接口、不循环读取错误队列，也不组合其他能力命令。
# 依赖：仅依赖 ScpiSession、本型号 Models 和 Validation。

from __future__ import annotations

from ....common.scpi import ScpiSession
from ..models import Bk9130bInterface, Bk9130bSystemError
from ..validation import parse_system_error, require_integer


# 提供 9130B 系统级单命令控制；通信接口切换后由调用方负责实际重连。
class Bk9130bSystemControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 读取错误队列中的一条错误记录；不会自动继续清空后续错误。
    def error_get(self) -> Bk9130bSystemError:
        return parse_system_error(self._session.query_text("SYSTem:ERRor?"))

    # 查询仪器软件版本；只读取本次 SYSTem:VERSion? 响应。
    def version_get(self) -> str:
        return self._session.query_text("SYSTem:VERSion?")

    # 把仪器切到远程控制模式；只发送一次 SYSTem:REMote。
    def remote(self) -> None:
        self._session.write("SYSTem:REMote")

    # 把仪器切回前面板本地控制模式；只发送一次 SYSTem:LOCal。
    def local(self) -> None:
        self._session.write("SYSTem:LOCal")

    # 执行手册定义的远程写锁命令；该条目没有独立查询语义。
    def remote_write_lock(self) -> None:
        self._session.write("SYSTem:RWLock")

    # 设置 GPIB 设备地址 0~30；不自动切换当前通信接口或重连。
    def gpib_address_set(self, address: int) -> None:
        normalized = require_integer(address, 0, 30, "address")
        self._session.write(f"SYSTem:COMMunicate:GPIB:RDEVice:ADDRess {normalized}")

    # 查询当前 GPIB 设备地址；查询过程不会修改通信配置。
    def gpib_address_get(self) -> int:
        return int(self._session.query_text("SYSTem:COMMunicate:GPIB:RDEVice:ADDRess?"))

    # 让仪器蜂鸣一次；只发送一次 SYSTem:BEEPer 命令。
    def beep(self) -> None:
        self._session.write("SYSTem:BEEPer")

    # 选择 RS232、USB 或 GPIB 接口；物理重连由调用方显式负责。
    def interface_set(self, interface: Bk9130bInterface) -> None:
        if not isinstance(interface, Bk9130bInterface):
            raise ValueError("interface must be Bk9130bInterface")
        self._session.write(f"SYSTem:INTerface {interface.value}")

    # 选择四个参数存储组之一；只修改 SYSTem:MEMory:GROUP 配置。
    def memory_group_set(self, group: int) -> None:
        self._session.write(f"SYSTem:MEMory:GROUP {require_integer(group, 1, 4, 'group')}")

    # 查询当前参数存储组；查询过程不会召回或保存任何设置。
    def memory_group_get(self) -> int:
        return int(self._session.query_text("SYSTem:MEMory:GROUP?"))
