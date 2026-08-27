# RIGOL MSO5204 LAN 参数原子控制。
#
# 职责：用命令表生成 DHCP/AutoIP/Static IP、名称和网络状态的原子 API。
# 边界：不扫描网络、不创建 VISA 连接，也不自动执行 APPLy。
# 依赖：仅依赖公共 ScpiSession、Callable/Any 和本型号基础 SCPI 格式化与布尔解析辅助函数。
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ....common.scpi import ScpiSession
from ..validation import _command, _parse_bool

_LAN_FIELDS = (
    ("dhcp", ":LAN:DHCP", "bool"),
    ("auto_ip", ":LAN:AUToip", "bool"),
    ("gateway", ":LAN:GATeway", "text"),
    ("dns", ":LAN:DNS", "text"),
    ("manual_ip", ":LAN:MANual", "bool"),
    ("ip_address", ":LAN:IPADdress", "text"),
    ("subnet_mask", ":LAN:SMASk", "text"),
    ("mdns", ":LAN:MDNS", "bool"),
    ("host_name", ":LAN:HOST:NAME", "text"),
    ("description", ":LAN:DESCription", "text"),
)
_LAN_QUERIES = (
    ("mac", ":LAN:MAC?"),
    ("dhcp_server", ":LAN:DSErver?"),
    ("status", ":LAN:STATus?"),
    ("visa_address", ":LAN:VISA?"),
)


def _make_setter(header: str) -> Callable[[Any, Any], None]:
    def _setter(self: Any, value: Any) -> None:
        self._session.write(_command(header, value))

    return _setter


def _make_getter(header: str, kind: str) -> Callable[[Any], str | bool]:
    def _getter(self: Any) -> str | bool:
        value = self._session.query_text(header + "?")
        return _parse_bool(value) if kind == "bool" else value

    return _getter


def _make_query(command: str) -> Callable[[Any], str]:
    def _query(self: Any) -> str:
        return self._session.query_text(command)

    return _query


# 提供 LAN 参数、状态和 APPLy 原子访问；构造对象时不会扫描网络、建立 VISA 会话或应用配置。
class Mso5204LanControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 应用此前写入的仪器端 LAN 参数；只发送 LAN:APPLy，不扫描网络或重建 VISA 会话。
    def apply(self) -> None:
        self._session.write(":LAN:APPLy")


for _name, _header, _kind in _LAN_FIELDS:
    setattr(Mso5204LanControl, f"{_name}_set", _make_setter(_header))
    setattr(Mso5204LanControl, f"{_name}_get", _make_getter(_header, _kind))
for _name, _command_text in _LAN_QUERIES:
    setattr(Mso5204LanControl, f"{_name}_get", _make_query(_command_text))
