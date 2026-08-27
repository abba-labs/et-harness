# ServiceMessage 协议的纯 Wire 编解码。
#
# 职责：定义 ServiceMessage 的稳定字段、长度检查和流式解码规则。
# 边界：不访问 Transport、TargetClient、Capability 或任何 IP Driver，不执行设备 I/O。
# 依赖：仅依赖标准库字节/结构处理与平台 ProtocolError。

from .et_frame import Frame, FrameCodec, FrameDecoder, MessageType
from .et_message import ServiceMessage, Status

__all__ = [
    "Frame",
    "FrameCodec",
    "FrameDecoder",
    "MessageType",
    "ServiceMessage",
    "Status",
]
