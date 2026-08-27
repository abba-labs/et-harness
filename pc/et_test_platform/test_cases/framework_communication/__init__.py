# Formal Case包边界。
#
# 职责：组织所属测试域的Case模块，不执行测试流程。
# 边界：不创建Driver、不访问硬件，也不定义第二套测试状态。
# 依赖：仅作为Python包入口。

from .stress_case import (
    FORMAL_STRESS_PLAN,
    CommunicationStressPlan,
    PayloadClass,
    payload_for_round,
    percentile,
)

__all__ = [
    "FORMAL_STRESS_PLAN",
    "CommunicationStressPlan",
    "PayloadClass",
    "payload_for_round",
    "percentile",
]
