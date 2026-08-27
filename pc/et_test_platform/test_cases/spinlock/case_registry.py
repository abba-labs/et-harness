# SPINLOCK Formal Case 显式执行白名单。
# 职责：只注册已经实现且具有完整 SPEC/Report Contract 的 SPINLOCK Case。
# 边界：不动态发现 Case、不读取 Capability、不访问 Firmware 或硬件。
# 依赖：无运行时依赖，仅保存稳定Case ID元组。

SPINLOCK_CASE_REGISTRY = (
    "spinlock_p0_001",
    "spinlock_p0_002",
    "spinlock_p0_003",
    "spinlock_p1_001",
    "spinlock_p1_002",
    "spinlock_p1_003",
    "spinlock_p2_001",
    "spinlock_p2_002",
    "spinlock_p2_003",
    "spinlock_p2_004",
    "spinlock_p3_001",
)
