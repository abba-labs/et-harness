# AES 正式测试用例显式执行白名单。
#
# 职责：列出全部 AES P0-P3 Case ID，不执行动态发现。
# 边界：不进行 pytest 收集、Capability 读取、Service 调用或硬件 I/O。
# 依赖：只依赖稳定 Case ID 命名。

AES_CASE_REGISTRY = (
    "aes_p0_001",
    "aes_p0_002",
    "aes_p0_003",
    "aes_p1_001",
    "aes_p1_002",
    "aes_p1_003",
    "aes_p1_004",
    "aes_p1_005",
    "aes_p1_006",
    "aes_p1_007",
    "aes_p1_008",
    "aes_p1_009",
    "aes_p1_010",
    "aes_p1_011",
    "aes_p1_012",
    "aes_p1_013",
    "aes_p1_014",
    "aes_p1_015",
    "aes_p1_016",
    "aes_p1_017",
    "aes_p2_001",
    "aes_p2_002",
    "aes_p2_003",
    "aes_p3_001",
    "aes_p3_002",
    "aes_p3_003",
)
