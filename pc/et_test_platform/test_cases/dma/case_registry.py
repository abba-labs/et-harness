# DMA Formal Case显式执行白名单。
#
# 职责：声明允许进入正式pytest执行集合的DMA稳定Case ID。
# 边界：不导入Case函数、不执行测试、不保存启停状态或芯片能力事实。
# 依赖：仅依赖Case稳定命名契约。

DMA_CASE_REGISTRY = (
    "dma_p0_001",
    "dma_p0_002",
    "dma_p1_001",
    "dma_p1_004",
    "dma_p1_005",
    "dma_p1_006",
    "dma_p1_007",
    "dma_p1_008",
    "dma_p1_009",
    "dma_p1_010",
    "dma_p1_011",
    "dma_p1_014",
    "dma_p1_015",
    "dma_p1_016",
    "dma_p1_017",
    "dma_p2_001",
    "dma_p2_002",
    "dma_p2_004",
    "dma_p2_005",
    "dma_p2_006",
    "dma_p2_008",
    "dma_p2_009",
    "dma_p2_010",
    "dma_p2_011",
    "dma_p2_012",
    "dma_p2_013",
    "dma_p2_015",
    "dma_p3_007",
)
