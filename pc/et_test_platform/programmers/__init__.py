# 烧录与调试工具适配层的命名空间入口。
#
# 职责：承载J-Link、Vivado、OpenOCD等具体工具的受门禁适配器。
# 边界：不管理示波器等观测仪器，不承载芯片Profile，不定义空的通用Programmer基类。
# 依赖：具体适配器接入真实工具时再新增；当前命名空间不执行任何外部操作。
# 调试器公共接口导出；导入模块不会启动探针、扫描设备或执行硬件动作。
from .debugger import (
    DebugAction,
    DebugController,
    HaltSamples,
    HaltSampleSpec,
    JLinkDebugController,
)

__all__ = [
    "DebugAction",
    "DebugController",
    "HaltSampleSpec",
    "HaltSamples",
    "JLinkDebugController",
]
