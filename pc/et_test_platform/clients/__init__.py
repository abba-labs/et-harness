# ET PC 控制面的稳定包入口。
#
# 职责：组织并导出自动化测试平台的分层公共能力。
# 边界：不在包入口中实现设备业务逻辑、跨 IP 编排或最终测试断言。
# 依赖：仅依赖当前包内已批准的稳定公共接口。

from .target import TargetClient

__all__ = ["TargetClient"]
