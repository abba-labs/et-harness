# RIGOL DM3068 UTILity 接口配置原子控制。
#
# 职责：映射 LAN、GPIB 和 RS232 参数的 UTILity 单条设置/查询命令。
# 边界：只改变仪器端接口参数，不负责 PC Transport 重连或 VISA 资源发现。
# 依赖：仅依赖公共 ScpiSession、本型号 Parity 与 validation。

from __future__ import annotations

from ....common.scpi import ScpiSession
from ..models import Dm3068Parity
from ..validation import _bool_token, _nonempty_token, _parse_bool, _parse_int, _require_baudrate


# 提供 DM3068 LAN/GPIB/RS232 仪器端参数的单命令设置和查询接口。
class Dm3068InterfaceControl:
    def __init__(self, session: ScpiSession) -> None:
        self._session = session

    # 设置 LAN DHCP 状态；只写入 UTILity:LAN:DHCP，不执行网络重连。
    def lan_dhcp_set(self, enabled: bool) -> None:
        self._session.write(f":UTILity:INTErface:LAN:DHCP {_bool_token(enabled)}")

    # 查询 LAN DHCP 状态；只读取 UTILity:LAN:DHCP? 当前值。
    def lan_dhcp_get(self) -> bool:
        return _parse_bool(self._session.query_text(":UTILity:INTErface:LAN:DHCP?"))

    # 设置 LAN Auto-IP 状态；只写入 UTILity:LAN:AUTOip，不执行网络重连。
    def lan_auto_ip_set(self, enabled: bool) -> None:
        self._session.write(f":UTILity:INTErface:LAN:AUTOip {_bool_token(enabled)}")

    # 查询 LAN Auto-IP 状态；只读取 UTILity:LAN:AUTOip? 当前值。
    def lan_auto_ip_get(self) -> bool:
        return _parse_bool(self._session.query_text(":UTILity:INTErface:LAN:AUTOip?"))

    # 设置 LAN 手动 IP 模式状态；只写入 MANUip，不自动写入具体地址。
    def lan_manual_ip_set(self, enabled: bool) -> None:
        self._session.write(f":UTILity:INTErface:LAN:MANUip {_bool_token(enabled)}")

    # 查询 LAN 手动 IP 模式状态；只读取 MANUip? 当前值。
    def lan_manual_ip_get(self) -> bool:
        return _parse_bool(self._session.query_text(":UTILity:INTErface:LAN:MANUip?"))

    # 设置 LAN IPv4 地址文本；只写入 UTILity:LAN:IP，不执行 Transport 重连。
    def lan_ip_set(self, address: str) -> None:
        self._session.write(f":UTILity:INTErface:LAN:IP {_nonempty_token(address, 'address')}")

    # 查询 LAN IPv4 地址文本；只读取 UTILity:LAN:IP? 当前值。
    def lan_ip_get(self) -> str:
        return self._session.query_text(":UTILity:INTErface:LAN:IP?").strip()

    # 设置 LAN 子网掩码文本；只写入 UTILity:LAN:MASK，不执行 Transport 重连。
    def lan_mask_set(self, mask: str) -> None:
        self._session.write(f":UTILity:INTErface:LAN:MASK {_nonempty_token(mask, 'mask')}")

    # 查询 LAN 子网掩码文本；只读取 UTILity:LAN:MASK? 当前值。
    def lan_mask_get(self) -> str:
        return self._session.query_text(":UTILity:INTErface:LAN:MASK?").strip()

    # 设置 LAN 默认网关文本；只写入 UTILity:LAN:GATEway，不执行网络重连。
    def lan_gateway_set(self, gateway: str) -> None:
        self._session.write(f":UTILity:INTErface:LAN:GATEway {_nonempty_token(gateway, 'gateway')}")

    # 查询 LAN 默认网关文本；只读取 UTILity:LAN:GATEway? 当前值。
    def lan_gateway_get(self) -> str:
        return self._session.query_text(":UTILity:INTErface:LAN:GATEway?").strip()

    # 设置 LAN DNS 地址文本；只写入 UTILity:LAN:DNS，不执行网络重连。
    def lan_dns_set(self, address: str) -> None:
        self._session.write(f":UTILity:INTErface:LAN:DNS {_nonempty_token(address, 'address')}")

    # 查询 LAN DNS 地址文本；只读取 UTILity:LAN:DNS? 当前值。
    def lan_dns_get(self) -> str:
        return self._session.query_text(":UTILity:INTErface:LAN:DNS?").strip()

    # 设置 GPIB 地址；只写入 UTILity:GPIB:ADDRess，不操作 PC GPIB 资源。
    def gpib_address_set(self, address: int) -> None:
        self._session.write(f":UTILity:INTErface:GPIB:ADDRess {address}")

    # 查询 GPIB 地址；只读取 UTILity:GPIB:ADDRess? 当前值。
    def gpib_address_get(self) -> int:
        return _parse_int(self._session.query_text(":UTILity:INTErface:GPIB:ADDRess?"))

    # 设置 RS232 波特率；只写入仪器参数，调用者负责按新参数重新建立连接。
    def rs232_baudrate_set(self, baudrate: int) -> None:
        self._session.write(f":UTILity:INTErface:RS232:BAUD {_require_baudrate(baudrate)}")

    # 查询 RS232 波特率；只读取 UTILity:RS232:BAUD? 当前值。
    def rs232_baudrate_get(self) -> int:
        return _parse_int(self._session.query_text(":UTILity:INTErface:RS232:BAUD?"))

    # 设置 RS232 校验方式；只写入仪器参数，调用者负责按新参数重新建立连接。
    def rs232_parity_set(self, parity: Dm3068Parity) -> None:
        self._session.write(f":UTILity:INTErface:RS232:PARIty {parity.value}")

    # 查询 RS232 校验方式；只读取 UTILity:RS232:PARIty? 当前关键字。
    def rs232_parity_get(self) -> str:
        return self._session.query_text(":UTILity:INTErface:RS232:PARIty?").strip()
