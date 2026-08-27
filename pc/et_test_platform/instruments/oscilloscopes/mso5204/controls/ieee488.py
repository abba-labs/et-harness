# RIGOL MSO5204 IEEE488.2 通用命令控制。
#
# 职责：映射编程手册公开的 IEEE488.2 Common Commands，并解析基础状态响应。
# 边界：不组合型号专用命令、不解释测试业务，也不自动清空仪器错误队列。
# 依赖：仅依赖公共 ScpiSession、MSO5204 标识模型和解析辅助函数。

from __future__ import annotations

from ....common.scpi import ScpiSession
from ..models import Mso5204Identification
from ..validation import _parse_identification, _parse_int


# 提供 MSO5000 手册中的标准公共命令原子接口。
class Mso5204Ieee488Control:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 清除事件寄存器和状态队列；只发送一次 *CLS。
    def clear_status(self) -> None:
        self._session.write("*CLS")

    # 设置标准事件状态使能寄存器；只发送一次 *ESE 命令。
    def event_status_enable_set(self, value: int) -> None:
        self._session.write(f"*ESE {int(value)}")

    # 查询标准事件状态使能寄存器；只执行一次 *ESE? Query。
    def event_status_enable_get(self) -> int:
        return _parse_int(self._session.query_text("*ESE?"))

    # 查询并清除标准事件状态寄存器；只执行一次 *ESR? Query。
    def event_status_register_get(self) -> int:
        return _parse_int(self._session.query_text("*ESR?"))

    # 查询厂商、型号、序列号和软件版本；只执行一次 *IDN? Query。
    def identity_get(self) -> Mso5204Identification:
        return _parse_identification(self._session.query_text("*IDN?"))

    # 设置操作完成事件位；只发送一次 *OPC，不等待后续操作完成查询。
    def operation_complete(self) -> None:
        self._session.write("*OPC")

    # 查询此前操作是否完成；只执行一次 *OPC? Query 并返回整数状态。
    def operation_complete_get(self) -> int:
        return _parse_int(self._session.query_text("*OPC?"))

    # 保存当前仪器设置到指定内部位置；只发送一次 *SAV 命令。
    def state_save(self, index: int) -> None:
        self._session.write(f"*SAV {int(index)}")

    # 从指定内部位置恢复仪器设置；只发送一次 *RCL 命令。
    def state_recall(self, index: int) -> None:
        self._session.write(f"*RCL {int(index)}")

    # 将仪器恢复为手册定义的复位状态；只发送一次 *RST。
    def reset(self) -> None:
        self._session.write("*RST")

    # 设置服务请求使能寄存器；只发送一次 *SRE 命令。
    def service_request_enable_set(self, value: int) -> None:
        self._session.write(f"*SRE {int(value)}")

    # 查询服务请求使能寄存器；只执行一次 *SRE? Query。
    def service_request_enable_get(self) -> int:
        return _parse_int(self._session.query_text("*SRE?"))

    # 查询状态字节寄存器；只执行一次 *STB? Query。
    def status_byte_get(self) -> int:
        return _parse_int(self._session.query_text("*STB?"))

    # 执行仪器自检并返回结果码；只执行一次 *TST? Query。
    def self_test_get(self) -> int:
        return _parse_int(self._session.query_text("*TST?"))

    # 等待当前命令队列完成后再继续；只发送一次 *WAI。
    def wait(self) -> None:
        self._session.write("*WAI")
