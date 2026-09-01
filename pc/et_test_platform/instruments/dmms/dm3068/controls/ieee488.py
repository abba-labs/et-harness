# RIGOL DM3068 Command Set 与 IEEE488.2 原子控制。
#
# 职责：映射 CMDSET 和 Common Command System 中可确认的单条控制/查询语义。
# 边界：每个公开方法最多发送一条 SCPI，不组合测量、触发或接口配置流程。
# 依赖：仅依赖公共 ScpiSession、本型号 models 与 validation。

from __future__ import annotations

from ....common.scpi import ScpiSession
from ..models import Dm3068CommandSet, Dm3068Identification
from ..validation import _parse_bool, _parse_identification, _parse_int


# 提供 DM3068 命令集切换和 IEEE488.2 Common Commands 的原子接口。
class Dm3068CommonControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 切换仪器命令集；只写入 CMDSET，不隐式修改测量或触发状态。
    def command_set_set(self, command_set: Dm3068CommandSet) -> None:
        self._session.write(f"CMDSet {command_set.value}")

    # 查询当前仪器命令集；只执行一次 CMDSET? Query，不改变其他配置。
    def command_set_get(self) -> str:
        return self._session.query_text("CMDSet?").strip()

    # 清除标准状态寄存器；只发送 *CLS，不执行复位或错误查询。
    def clear_status(self) -> None:
        self._session.write("*CLS")

    # 设置 Standard Event Status Enable 掩码；只发送一条 *ESE 命令。
    def event_status_enable_set(self, value: int) -> None:
        self._session.write(f"*ESE {value}")

    # 查询 Standard Event Status Enable 掩码；只读取当前 *ESE? 值。
    def event_status_enable_get(self) -> int:
        return _parse_int(self._session.query_text("*ESE?"))

    # 读取 Standard Event Status Register；只执行一次 *ESR? Query。
    def event_status_register_get(self) -> int:
        return _parse_int(self._session.query_text("*ESR?"))

    # 查询厂家、型号、序列号和软件版本；只执行一次 *IDN? Query。
    def identity_get(self) -> Dm3068Identification:
        return _parse_identification(self._session.query_text("*IDN?"))

    # 设置 Operation Complete 状态；只发送 *OPC，不额外等待其他仪器状态。
    def operation_complete(self) -> None:
        self._session.write("*OPC")

    # 查询 Operation Complete；只执行一次 *OPC? 并解析布尔完成状态。
    def operation_complete_get(self) -> bool:
        return _parse_bool(self._session.query_text("*OPC?"))

    # 设置 Power-on Status Clear 标志；只发送一条 *PSC 命令。
    def power_on_status_clear_set(self, enabled: bool) -> None:
        self._session.write(f"*PSC {1 if enabled else 0}")

    # 查询 Power-on Status Clear 标志；只读取 *PSC? 当前值。
    def power_on_status_clear_get(self) -> bool:
        return _parse_bool(self._session.query_text("*PSC?"))

    # 恢复仪器默认复位状态；只发送 *RST，不追加其他配置或等待逻辑。
    def reset(self) -> None:
        self._session.write("*RST")

    # 设置 Service Request Enable 掩码；只发送一条 *SRE 命令。
    def service_request_enable_set(self, value: int) -> None:
        self._session.write(f"*SRE {value}")

    # 查询 Service Request Enable 掩码；只执行一次 *SRE? Query。
    def service_request_enable_get(self) -> int:
        return _parse_int(self._session.query_text("*SRE?"))

    # 读取 Status Byte Register；只执行一次 *STB? Query，不清理其他状态。
    def status_byte_get(self) -> int:
        return _parse_int(self._session.query_text("*STB?"))

    # 触发一次标准总线触发动作；只发送 *TRG，不组合采样读取流程。
    def trigger(self) -> None:
        self._session.write("*TRG")

    # 执行标准自检查询并返回仪器原始整数结果；只执行一次 *TST? Query。
    def self_test_get(self) -> int:
        return _parse_int(self._session.query_text("*TST?"))

    # 请求仪器等待先前操作完成；只发送 *WAI，不在 PC 侧实现额外轮询。
    def wait(self) -> None:
        self._session.write("*WAI")
