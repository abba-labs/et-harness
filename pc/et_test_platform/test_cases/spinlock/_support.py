# SPINLOCK Formal Case 本地 Support。
# 职责：保存已通过静态与运行时 Gate 的 SPINLOCK Driver 和只读能力事实。
# 边界：不修改硬件、不隐藏 Case 流程、不包含芯片地址、Key 或 Master 拓扑。
# 依赖：仅依赖SPINLOCK公开Driver及其Capability模型。

from dataclasses import dataclass

from ...drivers.spinlock import SpinlockCapabilities, SpinlockDriver


# 保存一个已通过 Capability/Registry Gate 的 SPINLOCK 实例。
@dataclass(frozen=True, slots=True)
class SpinlockCaseSupport:
    instance_id: int
    instance_name: str
    spinlock: SpinlockDriver
    runtime: SpinlockCapabilities
