# CORDIC Formal Case 显式执行白名单。
#
# 职责：只注册已经实现且具有完整 SPEC/Report Contract 的 CORDIC Case。
# 边界：不动态发现 Case、不读取 Capability、不访问 Firmware 或硬件。
# 依赖：仅依赖稳定 Case ID 命名。

CORDIC_CASE_REGISTRY = (
    "cordic_p0_002",
    "cordic_p0_003",
    "cordic_p0_004",
    "cordic_p1_001",
    "cordic_p1_002",
    "cordic_p1_003",
    "cordic_p1_004",
    "cordic_p1_005",
    "cordic_p1_006",
    "cordic_p1_007",
    "cordic_p1_008",
    "cordic_p1_009",
    "cordic_p1_011",
    "cordic_p1_013",
    "cordic_p1_015",
    "cordic_p1_016",
    "cordic_p1_017",
    "cordic_p1_018",
    "cordic_p1_019",
    "cordic_p1_020",
    "cordic_p2_001",
    "cordic_p3_001",
    "cordic_p3_002",
    "cordic_p3_003",
)
