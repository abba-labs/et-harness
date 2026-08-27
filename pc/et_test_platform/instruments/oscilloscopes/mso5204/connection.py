# RIGOL MSO5204 VISA 连接构造。
#
# 职责：把 USBTMC、TCPIP/VXI-11 或 GPIB VISA 资源名创建为 VisaTransport、ScpiSession 和 Mso5204Driver。
# 边界：不自动打开资源、不扫描设备、不发送 *IDN?，也不修改示波器的通信或测量配置。
# 依赖：仅依赖公共 VisaTransport、ScpiSession 和 Mso5204Driver。

from __future__ import annotations

from ....communication.transports.visa import VisaTransport
from ...common.scpi import ScpiSession
from .driver import Mso5204Driver


# 创建一个尚未打开的 MSO5204 VISA Driver；资源字符串可指向 USB、LAN/VXI-11 或 GPIB。
def create_mso5204_visa_driver(
    resource_name: str,
    *,
    visa_library: str | None = None,
    timeout_s: float = 5.0,
    open_timeout_s: float = 5.0,
) -> Mso5204Driver:
    transport = VisaTransport(
        resource_name=resource_name,
        visa_library=visa_library,
        open_timeout_s=open_timeout_s,
    )
    return Mso5204Driver(ScpiSession(transport, terminator=b"\n", timeout_s=timeout_s))
