# 跨 IP 执行事实 Resolver。
#
# 职责：组合 Chip Capability、Bench 与人工执行映射，返回强类型事实。
# 边界：不导入 Driver/TargetClient，不发送硬件命令，不等待设备，也不执行最终断言。
# 依赖：仅依赖 Profile/Capability Model、中立 Service ID 与芯片执行映射。

from .dma_routes import (
    AesDmaRoute,
    DmaInputRoute,
    DmaPeripheralRoute,
    resolve_aes_dma_route,
    resolve_dma_input_route,
    resolve_uart_dma_route,
)

__all__ = [
    "AesDmaRoute",
    "DmaInputRoute",
    "DmaPeripheralRoute",
    "resolve_aes_dma_route",
    "resolve_dma_input_route",
    "resolve_uart_dma_route",
]
