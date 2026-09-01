# ET6801 FMAC执行映射。
#
# 职责：保存FMAC FIFO端点、输入/输出DMA Request及可用控制器/接口事实。
# 边界：只提供ET6801 FMAC数据，不访问TargetClient，也不执行测试流程。
# 依赖：仅依赖标准库dataclass。

from __future__ import annotations

from dataclasses import dataclass


# 保存一个FMAC实例的FIFO端点、DMA Request和可用DMA资源事实。
@dataclass(frozen=True, slots=True)
class FmacDmaMapping:
    instance_id: int
    fifo_address: int
    input_request_id: int
    output_request_id: int
    transfer_width_bits: int
    allowed_controllers: tuple[int, ...]
    allowed_interfaces: tuple[int, ...]
    address_evidence: str
    request_evidence: str


FMAC_DMA_MAPPING = FmacDmaMapping(
    instance_id=0,
    fifo_address=0x40204020,
    input_request_id=2,
    output_request_id=1,
    transfer_width_bits=16,
    allowed_controllers=(0, 1),
    allowed_interfaces=tuple(range(8)),
    address_evidence="ET6801.svd:FMAC.baseAddress+FIFO_DATA(0x20)",
    request_evidence=(
        "firmware/chips/et6801/sdk/ET6x_Driver/Inc/et6x_sysctrl.h:"
        "DMAMUX_REQ_FMAC_WR/DMAMUX_REQ_FMAC_RD"
    ),
)
