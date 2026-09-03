# IPCM 公开 Driver 入口。
# 职责：导出芯片中立 API。
# 边界：不初始化设备，不注册 Case。
# 依赖：仅本 IP Driver。

from .contract import IPCM_SERVICE_ID
from .driver import IpcmDriver

__all__ = ["IPCM_SERVICE_ID", "IpcmDriver"]
