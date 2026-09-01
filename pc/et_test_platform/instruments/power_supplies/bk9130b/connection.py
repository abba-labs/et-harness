# B&K Precision 9130B 连接构造。
#
# 职责：提供项目采用的 USBTMC/VISA 构造，并保留现有 RS232 兼容构造。
# 边界：不自动打开连接、不探测设备，也不替调用方选择或修改仪器端通信接口。
# 依赖：仅依赖公共 VisaTransport/SerialTransport、ScpiSession 和本型号 Driver。

from __future__ import annotations

from ....communication.transports.serial import SerialTransport
from ....communication.transports.visa import VisaTransport
from ...common.scpi import ScpiSession
from .driver import Bk9130bDriver


# 使用 USBTMC VISA 资源构造尚未打开的 9130B Driver；构造过程不访问 USB 设备。
def create_bk9130b_usb_driver(
    resource_name: str,
    *,
    visa_library: str | None = None,
    timeout_s: float = 2.0,
    open_timeout_s: float = 5.0,
) -> Bk9130bDriver:
    resource = _require_usb_visa_resource(resource_name)
    transport = VisaTransport(
        resource_name=resource,
        visa_library=visa_library,
        open_timeout_s=open_timeout_s,
    )
    return Bk9130bDriver(ScpiSession(transport, terminator=b"\n", timeout_s=timeout_s))


# 使用显式 RS232 参数构造 9130B Driver；保留旧台架兼容入口，不作为新台架默认连接方式。
def create_serial_driver(
    *,
    port: str,
    baudrate: int,
    bytesize: int = 8,
    parity: str = "N",
    stopbits: int = 1,
    timeout_s: float = 2.0,
) -> Bk9130bDriver:
    transport = SerialTransport(
        port=port,
        baudrate=baudrate,
        bytesize=bytesize,
        parity=parity,
        stopbits=stopbits,
    )
    return Bk9130bDriver(ScpiSession(transport, terminator=b"\n", timeout_s=timeout_s))


def _require_usb_visa_resource(resource_name: str) -> str:
    normalized = resource_name.strip()
    if not normalized:
        raise ValueError("resource_name must not be empty")
    if "\r" in normalized or "\n" in normalized:
        raise ValueError("resource_name must contain exactly one VISA resource")
    if not normalized.upper().startswith("USB"):
        raise ValueError("9130B USB resource_name must be a USB VISA resource")
    return normalized
