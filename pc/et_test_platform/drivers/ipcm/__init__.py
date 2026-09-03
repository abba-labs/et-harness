# IPCM 公开 Driver 入口。
# 职责：导出芯片中立 API。
# 边界：不初始化设备，不注册 Case。
# 依赖：仅本 IP Driver。

from .driver import IpcmDriver

__all__ = ["IpcmDriver"]
