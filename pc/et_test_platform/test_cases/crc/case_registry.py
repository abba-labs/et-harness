# CRC Formal Case 显式执行白名单。
#
# 职责：声明允许进入正式 pytest 执行集合的 CRC 稳定 Case ID。
# 边界：不导入 Case 函数、不执行测试、不保存芯片能力事实。
# 依赖：仅依赖 Case 稳定命名契约。

CRC_CASE_REGISTRY = (
    "crc_p0_001",
    "crc_p0_002",
    "crc_p0_003",
    "crc_p1_001",
    "crc_p1_002",
    "crc_p1_003",
    "crc_p1_004",
    "crc_p1_005",
    "crc_p1_006",
    "crc_p1_007",
    "crc_p1_008",
    "crc_p1_009",
    "crc_p1_010",
    "crc_p1_011",
    "crc_p1_012",
    "crc_p1_013",
    "crc_p1_014",
    "crc_p1_015",
    "crc_p1_016",
    "crc_p1_018",
    "crc_p2_001",
    "crc_p3_001",
    "crc_p3_002",
    "crc_p3_003",
)
