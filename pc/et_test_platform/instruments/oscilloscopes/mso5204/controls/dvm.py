# RIGOL MSO5204 内置数字电压表原子控制。
#
# 职责：完整映射 DVM 命令组中的当前值、开关、来源和测量模式控制。
# 边界：不自动打开模拟通道、不选择量程，也不执行外部万用表级精度判定。
# 依赖：仅依赖公共 ScpiSession 和基础 SCPI 格式化/解析辅助函数。

from __future__ import annotations

from ..._internal.scpi import ScpiSession
from ..validation import _command, _parse_bool, _parse_float


# 提供 MSO5000 内置 DVM 全部公开命令的稳定原子接口。
class Mso5204DvmControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 查询 DVM 当前测量值；只执行一次 DVM:CURRent? Query。
    def current_get(self) -> float:
        return _parse_float(self._session.query_text(":DVM:CURRent?"))

    # 打开或关闭 DVM；只发送一次 DVM:ENABle 命令。
    def enabled_set(self, enabled: bool) -> None:
        self._session.write(_command(":DVM:ENABle", enabled))

    # 查询 DVM 开关；只执行一次 DVM:ENABle? Query。
    def enabled_get(self) -> bool:
        return _parse_bool(self._session.query_text(":DVM:ENABle?"))

    # 设置 DVM 来源；参数接受 CHANnel1..4，不联动通道显示状态。
    def source_set(self, source: str) -> None:
        self._session.write(_command(":DVM:SOURce", source))

    # 查询 DVM 来源；保留仪器返回的 CHAN1..CHAN4 字符串。
    def source_get(self) -> str:
        return self._session.query_text(":DVM:SOURce?")

    # 设置 DVM 模式；参数接受 ACRMs、DC 或 DCRMs。
    def mode_set(self, mode: str) -> None:
        self._session.write(_command(":DVM:MODE", mode))

    # 查询 DVM 模式；保留仪器返回的 ACRM、DC 或 DCRM 字符串。
    def mode_get(self) -> str:
        return self._session.query_text(":DVM:MODE?")
