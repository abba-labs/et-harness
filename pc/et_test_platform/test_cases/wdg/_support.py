# WDG Formal Case 本地 Support。
# 职责：保存通过静态与运行时 Gate 的 Driver 和只读能力事实。
# 边界：不修改硬件、不隐藏 Case 流程、不包含芯片 ID、地址或 IRQn。
# 依赖：仅依赖 WDG Driver、Capability 和稳定错误类型。

from collections.abc import Callable
from dataclasses import dataclass

import pytest

from ...core.errors import CapabilityLookupError, UnsupportedCapability
from ...drivers.cpu import CpuDriver, CpuNmiCapabilities
from ...drivers.wdg import WdgCapabilities, WdgDriver, WdgFeature
from ...profiles.capabilities import ChipCapabilities


@dataclass(frozen=True, slots=True)
class WdgCaseSupport:
    instance_id: int
    instance_name: str
    wdg: WdgDriver
    runtime: WdgCapabilities


WdgSupportFactory = Callable[[int], WdgCaseSupport]


@dataclass(frozen=True, slots=True)
class CpuNmiCaseSupport:
    instance_id: int
    instance_name: str
    cpu: CpuDriver
    runtime: CpuNmiCapabilities | None
    available: bool


CpuNmiSupportFactory = Callable[[int], CpuNmiCaseSupport]


# 核对一个 WDG 实例和可选静态 Feature 由当前 Capability 明确声明。
def require_wdg_static_capability(
    capabilities: ChipCapabilities,
    *,
    instance_id: int,
    feature: str | None = None,
) -> str:

    instance = f"wdg{instance_id}"
    try:
        if instance not in capabilities.instances("wdg"):
            raise UnsupportedCapability(f"WDG instance {instance!r} is unavailable")
        if feature is not None and not capabilities.has_feature("wdg", feature, instance=instance):
            raise UnsupportedCapability(f"{instance} does not declare feature {feature!r}")
        return instance
    except UnsupportedCapability:
        raise
    except CapabilityLookupError as error:
        raise UnsupportedCapability(f"WDG static capability is unavailable: {error}") from error


# 核对运行中 Service 发布了 Case 要求的 Feature 位。
def require_wdg_runtime_feature(runtime: WdgCapabilities, feature: WdgFeature) -> None:

    if runtime.features & feature != feature:
        pytest.skip(f"skip_by_runtime_feature: running WDG service is missing feature {feature!r}")
