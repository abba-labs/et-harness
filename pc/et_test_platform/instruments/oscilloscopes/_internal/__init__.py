# 示波器库自包含支撑层入口。
#
# 职责：集中导出本库内部使用的 SCPI 会话、VISA Transport、字节 Transport、Deadline 与异常。
# 边界：只服务 oscilloscopes 包内部，不承载型号 SCPI 命令、测试流程或 PASS/FAIL 判定。
# 依赖：仅依赖本目录稳定实现与 PyVISA。

from .deadline import OperationDeadline
from .errors import (
    InstrumentProtocolError,
    OscilloscopeError,
    OscilloscopeTimeout,
    TransportError,
)
from .scpi import ScpiSession
from .transport import ByteTransport
from .visa import VisaTransport

__all__ = [
    "ByteTransport",
    "InstrumentProtocolError",
    "OperationDeadline",
    "OscilloscopeError",
    "OscilloscopeTimeout",
    "ScpiSession",
    "TransportError",
    "VisaTransport",
]
