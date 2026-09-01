# 人工核对的芯片执行映射。
#
# 职责：保存 SVD 无法表达但已由 SDK/芯片资料证明的 Request ID、地址和接口约束。
# 边界：不修改自动生成 Capability，不访问 TargetClient，不执行任何硬件命令。
# 依赖：仅依赖不可变数据模型和已记录的芯片来源证据。

from .dma_routes import ET6801_UART_DMA_MAPPINGS, DmaPeripheralDirection, DmaPeripheralMapping

__all__ = [
    "DmaPeripheralDirection",
    "DmaPeripheralMapping",
    "ET6801_UART_DMA_MAPPINGS",
]
