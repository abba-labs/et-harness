# CAN静态Case注册表。
# 职责：仅登记已经与正式SPEC双向绑定的测试ID。
# 边界：不自动发现函数、不配置硬件、不把未实现PLAN当作已覆盖Case。
# 依赖：按P级分类的本IP正式测试函数。

CAN_CASE_REGISTRY = (
    "can_p0_002",
    "can_p1_001",
    "can_p1_002",
    "can_p1_003",
    "can_p1_004",
    "can_p1_005",
    "can_p1_006",
    "can_p1_007",
    "can_p1_008",
    "can_p1_009",
    "can_p1_015",
)
