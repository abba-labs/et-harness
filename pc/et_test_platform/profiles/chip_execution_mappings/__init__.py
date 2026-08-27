# 芯片执行映射的公共入口。
#
# 职责：导出芯片无关的执行映射类型和按 chip_id 加载接口。
# 边界：不硬编码任何具体芯片，也不执行硬件命令或测试流程。
# 依赖：仅依赖同目录的芯片无关执行映射模型；具体芯片通过独立扩展模块提供数据。

from .dma_routes import (
    AesDmaMapping,
    DmaInputMapping,
    DmaPeripheralDirection,
    DmaPeripheralMapping,
    load_aes_dma_mapping,
    load_crc_dma_mapping,
    load_dma_input_mappings,
    load_uart_dma_mappings,
)

__all__ = [
    "AesDmaMapping",
    "DmaInputMapping",
    "DmaPeripheralDirection",
    "DmaPeripheralMapping",
    "load_crc_dma_mapping",
    "load_dma_input_mappings",
    "load_aes_dma_mapping",
    "load_uart_dma_mappings",
]
