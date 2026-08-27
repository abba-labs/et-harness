# SPINLOCK Formal Case 包边界。
# 职责：公开当前 SPINLOCK Case 注册表。
# 边界：不创建 Driver、不访问硬件、不定义芯片事实。
# 依赖：仅依赖本IP静态Case注册表。

from .case_registry import SPINLOCK_CASE_REGISTRY

__all__ = ("SPINLOCK_CASE_REGISTRY",)
