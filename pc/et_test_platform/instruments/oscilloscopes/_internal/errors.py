# 示波器库自包含异常层。
#
# 职责：定义本库独立可用的传输、超时和仪器协议异常层次。
# 边界：不依赖宿主工程 core 层，不包含 IP 业务错误或测试判定语义。
# 依赖：仅依赖 Python 标准异常语义。

from __future__ import annotations


# 表示示波器库自身的全部可预期失败；宿主捕获本基类即可覆盖传输与协议两类错误。
class OscilloscopeError(Exception):
    pass


# 表示与示波器的字节连接失败、未打开、短写或底层 VISA 调用异常。
class TransportError(OscilloscopeError):
    pass


# 表示一次操作的总时间预算已经耗尽；继承传输异常以便调用方按传输失败统一处理。
class OscilloscopeTimeout(TransportError):
    pass


# 表示仪器已经响应，但返回内容无法按当前命令契约解释。
class InstrumentProtocolError(OscilloscopeError):
    pass


__all__ = [
    "InstrumentProtocolError",
    "OscilloscopeError",
    "OscilloscopeTimeout",
    "TransportError",
]
