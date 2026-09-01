# UART Formal Case显式执行白名单。
#
# 职责：声明允许进入正式pytest执行集合的UART稳定Case ID。
# 边界：不导入Case函数、不执行测试、不保存启停状态或芯片能力事实。
# 依赖：仅依赖Case稳定命名契约。

UART_CASE_REGISTRY = (
    "uart_p0_001",
    "uart_p0_002",
    "uart_p0_003",
    "uart_p0_004",
    "uart_p1_001",
    "uart_p1_002",
    "uart_p1_003",
    "uart_p1_004",
    "uart_p1_005",
    "uart_p1_006",
    "uart_p1_007",
    "uart_p1_008",
    "uart_p1_009",
    "uart_p1_010",
    "uart_p1_011",
    "uart_p1_012",
    "uart_p1_013",
    "uart_p1_014",
    "uart_p1_015",
    "uart_p1_016",
    "uart_p1_017",
    "uart_p2_001",
    "uart_p2_002",
    "uart_p2_003",
    "uart_p2_004",
    "uart_p2_005",
    "uart_p2_006",
    "uart_p2_007",
    "uart_p2_008",
    "uart_p2_010",
    "uart_p3_007",
    "uart_p3_009",
    "uart_p3_010",
)
