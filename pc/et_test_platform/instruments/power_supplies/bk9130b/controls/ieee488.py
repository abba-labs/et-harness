# B&K Precision 9130B IEEE488.2 公共命令控制。
#
# 职责：把编程手册的 IEEE488.2 公共命令逐一映射为原子 Python API。
# 边界：每个 API 最多发送一条 SCPI 命令，不组合电源业务流程或跨能力状态。
# 依赖：仅依赖 ScpiSession、本型号 Models 和 Validation。

from __future__ import annotations

from ....common.scpi import ScpiSession
from ..models import Bk9130bIdentification
from ..validation import parse_bool, parse_identification, require_integer


# 提供 9130B IEEE488.2 单命令控制；方法与手册语义一一对应。
class Bk9130bCommonControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 清除标准事件、查询、操作、状态字节和错误状态；只发送一次 *CLS。
    def clear_status(self) -> None:
        self._session.write("*CLS")

    # 设置标准事件使能寄存器；只修改对应寄存器，不执行额外仪器动作。
    def event_status_enable_set(self, value: int) -> None:
        self._session.write(f"*ESE {require_integer(value, 0, 255, 'value')}")

    # 查询标准事件使能寄存器；查询过程不会修改仪器配置。
    def event_status_enable_get(self) -> int:
        return int(self._session.query_text("*ESE?"))

    # 读取并按仪器语义清除标准事件寄存器；只执行一次 *ESR? 查询。
    def event_status_register_get(self) -> int:
        return int(self._session.query_text("*ESR?"))

    # 查询设备厂商、型号、序列号和固件版本；只读取 *IDN? 响应。
    def identity_get(self) -> Bk9130bIdentification:
        return parse_identification(self._session.query_text("*IDN?"))

    # 请求在此前命令完成后设置 OPC 事件位；不等待另一次状态查询。
    def operation_complete(self) -> None:
        self._session.write("*OPC")

    # 查询此前命令是否完成并返回 OPC 数值；只等待本次查询响应。
    def operation_complete_get(self) -> int:
        return int(self._session.query_text("*OPC?"))

    # 恢复编程手册定义的 *RST 默认状态；不等待输出进一步稳定。
    def reset(self) -> None:
        self._session.write("*RST")

    # 设置状态字节使能寄存器；只修改对应寄存器，不执行额外仪器动作。
    def service_request_enable_set(self, value: int) -> None:
        self._session.write(f"*SRE {require_integer(value, 0, 255, 'value')}")

    # 查询状态字节使能寄存器；查询过程不会修改仪器配置。
    def service_request_enable_get(self) -> int:
        return int(self._session.query_text("*SRE?"))

    # 查询状态字节寄存器；只读取仪器返回的当前状态值。
    def status_byte_get(self) -> int:
        return int(self._session.query_text("*STB?"))

    # 产生一次总线触发；受 INSTrument:COUPle 配置影响，不执行额外命令。
    def trigger(self) -> None:
        self._session.write("*TRG")

    # 保存当前设置到 1~36 的指定存储位置；只发送一次 *SAV。
    def state_save(self, position: int) -> None:
        self._session.write(f"*SAV {require_integer(position, 1, 36, 'position')}")

    # 从 1~36 的指定存储位置召回设置；只发送一次 *RCL。
    def state_recall(self, position: int) -> None:
        self._session.write(f"*RCL {require_integer(position, 1, 36, 'position')}")

    # 执行仪器自检并返回数值结果；非零值由上层决定如何判定。
    def self_test_get(self) -> int:
        return int(self._session.query_text("*TST?"))

    # 阻止后续命令直到待处理重叠命令完成；只发送一次 *WAI。
    def wait(self) -> None:
        self._session.write("*WAI")

    # 设置重新上电时是否清零状态使能寄存器；只修改 *PSC 配置。
    def power_on_status_clear_set(self, enabled: bool) -> None:
        self._session.write(f"*PSC {'ON' if enabled else 'OFF'}")

    # 查询 *PSC 的上电状态清除配置；查询过程不会修改仪器状态。
    def power_on_status_clear_get(self) -> bool:
        return parse_bool(self._session.query_text("*PSC?"))
