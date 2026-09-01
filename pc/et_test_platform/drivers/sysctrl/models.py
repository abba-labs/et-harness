# SYSCTRL PC Driver Package 的models层。
#
# 职责：提供 SYSCTRL 的稳定 Model/Enum/Dataclass。
# 边界：不做 Wire 编解码、不访问 TargetClient/Profile，也不保存可变全局状态。
# 依赖：仅依赖标准库以及本 IP 必要的类型定义。

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


# 旧版 SYSCTRL V1 的 UART 端点枚举，仅用于兼容。
class DmaEndpoint(IntEnum):
    UART_TX = 0
    UART_RX = 1


# PC Resolver 完成核对后可直接执行的 DMAMUX Route。
@dataclass(frozen=True, slots=True)
class DmaRequestRoute:
    controller: int
    interface: int
    request_id: int
