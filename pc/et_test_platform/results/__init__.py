# 测试 Measurement 与结果附件序列化层。
#
# 职责：把已观测事实整理为稳定 Measurement/JSON 附件，供报告和人工审阅使用。
# 边界：不执行设备操作、不重复计算 pytest 最终 PASS/FAIL，也不隐藏测试流程。
# 依赖：仅依赖不可变结果模型、JSON 和文件系统。

from .communication import (
    FrameworkCommunicationStressResult,
    LatencySummary,
    PayloadClassSummary,
)
from .recorder import write_json_result

__all__ = [
    "FrameworkCommunicationStressResult",
    "LatencySummary",
    "PayloadClassSummary",
    "write_json_result",
]
