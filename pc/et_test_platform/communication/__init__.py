# PC 通信层的稳定公共入口。
#
# 职责：集中导出协议无关的通信事实和 Service 标识。
# 边界：不执行设备业务命令，不读取 Profile/Capability，不承担 Case 编排。
# 依赖：仅依赖 communication 子模块自身的稳定定义。

from .transport import ByteTransport

__all__ = ["ByteTransport"]
