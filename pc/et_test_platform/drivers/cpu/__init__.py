# CPU Owner PC Driver 包公开入口。
# 职责：导出 CPU/NMI Owner 的稳定 Contract、Model 和 Driver API。
# 边界：不执行跨 IP 编排、不读取 Profile、不实现测试结论。
# 依赖：仅依赖本包内公开 Contract、Model 和 Driver。

from .contract import CPU_SERVICE_ID, CpuCommand
from .driver import CpuDriver
from .models import CpuNmiCapabilities, CpuNmiSnapshot

__all__ = (
    "CPU_SERVICE_ID",
    "CpuCommand",
    "CpuDriver",
    "CpuNmiCapabilities",
    "CpuNmiSnapshot",
)
