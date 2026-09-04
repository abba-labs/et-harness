# CAN盒子接入。
# 职责：提供型号中立的帧模型和ZLG设备Adapter。
# 边界：不包含DUT芯片信息、测试步骤或最终断言。
# 依赖：本包接口与设备实现。

from .models import CanBusConfig, CanFrame, CanReceivedFrame
from .zlg import ZlgCanBox, ZlgConnection

__all__ = ["CanBusConfig", "CanFrame", "CanReceivedFrame", "ZlgCanBox", "ZlgConnection"]
