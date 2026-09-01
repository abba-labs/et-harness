# RIGOL DP711 串口连接构造。
#
# 职责：按 DP700 手册 RS232 参数创建 SerialTransport、ScpiSession 和 Dp711Driver。
# 边界：不自动打开串口、不探测设备，也不修改仪器端通信参数。
# 依赖：仅依赖现有 SerialTransport、公共 ScpiSession 和 Dp711Driver。

from __future__ import annotations

from ....communication.transports.serial import SerialTransport
from ...common.scpi import ScpiSession
from .driver import Dp711Driver
from .models import Dp711Parity
from .validation import DP711_RS232_BAUDRATES


# 创建一个尚未打开的 DP711 RS232 Driver；默认使用手册默认值 9600/8/N/1。
def create_dp711_serial_driver(
    port: str,
    *,
    baudrate: int = 9600,
    parity: Dp711Parity = Dp711Parity.NONE,
    timeout_s: float = 2.0,
) -> Dp711Driver:
    if baudrate not in DP711_RS232_BAUDRATES:
        raise ValueError(f"unsupported DP711 baudrate: {baudrate}")
    pyserial_parity = {
        Dp711Parity.NONE: "N",
        Dp711Parity.ODD: "O",
        Dp711Parity.EVEN: "E",
    }[parity]
    transport = SerialTransport(
        port=port,
        baudrate=baudrate,
        bytesize=8,
        parity=pyserial_parity,
        stopbits=1,
        dtr=False,
        rts=False,
    )
    return Dp711Driver(ScpiSession(transport, terminator=b"\n", timeout_s=timeout_s))
