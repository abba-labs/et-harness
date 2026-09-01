# 外部仪器公共协议能力入口。
#
# 职责：导出 SCPI 会话和协议异常。
# 边界：不包含具体仪器型号命令或测试流程。
# 依赖：仅依赖本目录稳定公共实现。

from .errors import InstrumentProtocolError
from .scpi import ScpiSession

__all__ = ["InstrumentProtocolError", "ScpiSession"]
