# STIMER Formal Case本地Support。
# 职责：保存通过静态和Runtime Gate的Driver与能力事实。
# 边界：不修改硬件、不隐藏Case流程、不包含芯片物理事实。
# 依赖：仅依赖 STIMER Driver、Runtime Capability 和公共错误类型。

from collections.abc import Callable
from dataclasses import dataclass

import pytest

from ...drivers.dma import DmaDriver
from ...drivers.resource import ResourceDriver
from ...drivers.stimer import StimerCapabilities, StimerDriver, StimerFeature
from ...drivers.sysctrl import SysctrlDriver
from ...profiles.resolvers import DmaInputRoute


@dataclass(frozen=True, slots=True)
class StimerCaseSupport:
    instance_id: int
    instance_name: str
    stimer: StimerDriver
    runtime: StimerCapabilities


@dataclass(frozen=True, slots=True)
class StimerDmaCaseSupport:
    stimer_support: StimerCaseSupport
    dma: DmaDriver
    sysctrl: SysctrlDriver
    resource: ResourceDriver
    route: DmaInputRoute


StimerSupportFactory = Callable[[int], StimerCaseSupport]


# 核对Runtime Service发布了Case要求的全部Feature位。
def require_stimer_runtime_feature(runtime: StimerCapabilities, feature: StimerFeature) -> None:

    if runtime.features & feature != feature:
        pytest.skip(
            f"skip_by_runtime_feature: running STIMER service is missing feature {feature!r}"
        )
