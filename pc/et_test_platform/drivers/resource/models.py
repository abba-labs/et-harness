# RESOURCE PC Driver Package 的models层。
#
# 职责：提供 RESOURCE 的稳定 Model/Enum/Dataclass。
# 边界：不做 Wire 编解码、不访问 TargetClient/Profile，也不保存可变全局状态。
# 依赖：仅依赖标准库以及本 IP 必要的类型定义。

from dataclasses import dataclass


# Firmware 固定池中一个已分配资源的稳定引用。
@dataclass(frozen=True, slots=True)
class ResourceRef:
    handle: int
    size: int
    address: int
