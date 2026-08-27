# PC Profile/Capability 层的稳定公共入口。
#
# 职责：集中导出静态芯片事实和台架事实。
# 边界：不访问设备、不调用 Driver、不拥有测试生命周期或最终断言。
# 依赖：仅依赖 profiles 子模块自身的强类型事实。

from .bench import SerialTargetConfig, load_serial_target
from .capabilities import (
    CapabilityAudit,
    CapabilityEvidence,
    CapabilityProfile,
    ChipCapabilities,
    InterruptCapability,
    UnclassifiedFact,
    load_capability_audit,
    load_capability_profile,
    load_chip_capabilities,
    load_packaged_chip_capabilities,
)

__all__ = [
    "CapabilityAudit",
    "CapabilityEvidence",
    "CapabilityProfile",
    "ChipCapabilities",
    "InterruptCapability",
    "SerialTargetConfig",
    "UnclassifiedFact",
    "load_capability_audit",
    "load_capability_profile",
    "load_chip_capabilities",
    "load_packaged_chip_capabilities",
    "load_serial_target",
]
