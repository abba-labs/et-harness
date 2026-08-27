# Formal Case本地Support模块。
#
# 职责：聚合本测试域的只读事实、Driver构造和小粒度复用操作。
# 边界：不隐藏完整Case、不拥有最终断言，也不改变公共Scheduling。
# 依赖：仅依赖本IP Driver、Profile事实和稳定公共工具。

from __future__ import annotations

__all__ = ["DMA_P0_REQUIRED_CAPABILITIES"]

_DMA_IP = "dma"
_TRANSFER_TYPE_OPTION = "transfer_type_and_flow_control"
_MAX_BLOCK_PARAMETER = "max_block_size"
_TRANSFER_DONE_INTERRUPT = "transfer_done"
DMA_P0_REQUIRED_CAPABILITIES = (
    f"{_DMA_IP}.interrupt.{_TRANSFER_DONE_INTERRUPT}",
    f"{_DMA_IP}.option.{_TRANSFER_TYPE_OPTION}",
    f"{_DMA_IP}.parameter.{_MAX_BLOCK_PARAMETER}",
)
