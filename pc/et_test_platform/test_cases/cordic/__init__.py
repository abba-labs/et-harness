# CORDIC Formal Case 包的公共导出层。
#
# 职责：导出 CORDIC 已审核 Case 的稳定执行白名单。
# 边界：不创建 Driver、不读取芯片事实、不包含测试执行流程。
# 依赖：仅依赖本 IP Case Registry。

from .case_registry import CORDIC_CASE_REGISTRY

__all__ = ("CORDIC_CASE_REGISTRY",)
