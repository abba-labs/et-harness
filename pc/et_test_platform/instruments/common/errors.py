# 外部仪器协议层异常。
#
# 职责：区分传输已成功但仪器响应不符合预期格式的协议错误。
# 边界：不负责设备连接、重试、SCPI 命令生成或业务判定。
# 依赖：仅依赖 Python 标准异常语义。


# 表示仪器已经响应，但返回内容无法按当前命令契约解释。
class InstrumentProtocolError(RuntimeError):
    pass
