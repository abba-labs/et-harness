# RIGOL DM3068 连接构造。
#
# 职责：提供项目采用的 LAN/LXI-C VISA 构造，并保留现有 RS232 兼容构造。
# 边界：不自动打开连接、不探测设备，也不在改变仪器端通信参数后自动重连。
# 依赖：仅依赖现有 VisaTransport/SerialTransport、公共 ScpiSession 和本型号 Driver/Parity。

from __future__ import annotations

from ....communication.transports.serial import SerialTransport
from ....communication.transports.visa import VisaTransport
from ...common.scpi import ScpiSession
from .driver import Dm3068Driver
from .models import Dm3068Parity
from .validation import _require_baudrate


# 使用调用方提供的 TCPIP VISA 资源构造尚未打开的 DM3068 LAN Driver；构造过程不访问网络。
def create_dm3068_lan_driver(
    resource_name: str,
    *,
    visa_library: str | None = None,
    timeout_s: float = 2.0,
    open_timeout_s: float = 5.0,
) -> Dm3068Driver:
    resource = _require_lan_visa_resource(resource_name)
    transport = VisaTransport(
        resource_name=resource,
        visa_library=visa_library,
        open_timeout_s=open_timeout_s,
    )
    return Dm3068Driver(ScpiSession(transport, terminator=b"\n", timeout_s=timeout_s))


# 创建尚未打开的 DM3068 RS232 Driver；保留旧台架兼容入口，不作为新台架默认连接方式。
def create_dm3068_serial_driver(
    port: str,
    *,
    baudrate: int,
    parity: Dm3068Parity = Dm3068Parity.NONE,
    timeout_s: float = 2.0,
) -> Dm3068Driver:
    pyserial_parity = {
        Dm3068Parity.NONE: "N",
        Dm3068Parity.ODD: "O",
        Dm3068Parity.EVEN: "E",
    }[parity]
    transport = SerialTransport(
        port=port,
        baudrate=_require_baudrate(baudrate),
        bytesize=8,
        parity=pyserial_parity,
        stopbits=1,
        dtr=False,
        rts=False,
    )
    return Dm3068Driver(ScpiSession(transport, terminator=b"\r\n", timeout_s=timeout_s))


def _require_lan_visa_resource(resource_name: str) -> str:
    normalized = resource_name.strip()
    if not normalized:
        raise ValueError("resource_name must not be empty")
    if "\r" in normalized or "\n" in normalized:
        raise ValueError("resource_name must contain exactly one VISA resource")
    if not normalized.upper().startswith("TCPIP"):
        raise ValueError("DM3068 LAN resource_name must be a TCPIP VISA resource")
    return normalized
