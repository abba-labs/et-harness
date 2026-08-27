# ET6801 已人工核对的 UART DMA 执行映射。
#
# 职责：保存 SVD 无法表达但已由 SDK/芯片资料证明的 Request ID、地址和接口约束。
# 边界：只提供 ET6801 数据，不访问 TargetClient、不执行硬件命令，也不包含公共 Resolver 逻辑。
# 依赖：仅依赖芯片无关的 DMA 执行映射公共模型。

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from ..dma_routes import (
    AesDmaMapping,
    DmaInputMapping,
    DmaPeripheralDirection,
    DmaPeripheralMapping,
)


def _uart(
    instance_id: int,
    direction: DmaPeripheralDirection,
    address: int,
    request_id: int,
) -> DmaPeripheralMapping:
    return DmaPeripheralMapping(
        peripheral="uart",
        instance_id=instance_id,
        direction=direction,
        peripheral_address=address,
        request_id=request_id,
        allowed_controllers=(0, 1),
        allowed_interfaces=tuple(range(8)),
        address_evidence=(f"ET6801.svd:UART{instance_id}.baseAddress+RBR_THR(0x0)"),
        request_evidence=(
            "firmware/chips/et6801/sdk/ET6x_Driver/Inc/et6x_sysctrl.h:"
            f"DMAMUX_REQ_UART{instance_id}_{direction.value.upper()}"
        ),
    )


UART_DMA_MAPPINGS: Mapping[tuple[int, DmaPeripheralDirection], DmaPeripheralMapping] = (
    MappingProxyType(
        {
            (0, DmaPeripheralDirection.TX): _uart(0, DmaPeripheralDirection.TX, 0x40500000, 192),
            (0, DmaPeripheralDirection.RX): _uart(0, DmaPeripheralDirection.RX, 0x40500000, 193),
            (1, DmaPeripheralDirection.TX): _uart(1, DmaPeripheralDirection.TX, 0x40501000, 194),
            (1, DmaPeripheralDirection.RX): _uart(1, DmaPeripheralDirection.RX, 0x40501000, 195),
            (2, DmaPeripheralDirection.TX): _uart(2, DmaPeripheralDirection.TX, 0x40502000, 196),
            (2, DmaPeripheralDirection.RX): _uart(2, DmaPeripheralDirection.RX, 0x40502000, 197),
        }
    )
)

# 兼容既有测试与外部导入；公共 Resolver 只读取 UART_DMA_MAPPINGS。
ET6801_UART_DMA_MAPPINGS = UART_DMA_MAPPINGS


# ET6801 CRC 输入寄存器的 DMA Request、地址和可用控制器/接口事实。
CRC_DMA_INPUT_MAPPING = DmaInputMapping(
    peripheral="crc",
    instance_id=0,
    peripheral_address=0x40206014,
    request_id=0,
    allowed_controllers=(0, 1),
    allowed_interfaces=tuple(range(8)),
    address_evidence="ET6801.svd:CRC.baseAddress+IR(0x14)",
    request_evidence=("firmware/chips/et6801/sdk/ET6x_Driver/Inc/et6x_sysctrl.h:DMAMUX_REQ_CRC"),
)

CRC_DMA_INPUT_MAPPINGS: Mapping[int, DmaInputMapping] = MappingProxyType(
    {CRC_DMA_INPUT_MAPPING.instance_id: CRC_DMA_INPUT_MAPPING}
)


# ET6801 AES 的 FIFO/寄存器双向 DMA 端点及 DMAMUX Request 事实。
AES_DMA_MAPPING = AesDmaMapping(
    instance_id=0,
    input_fifo_address=0x4020505C,
    output_fifo_address=0x40205074,
    input_register_address=0x4020504C,
    output_register_address=0x40205064,
    input_request_id=112,
    output_request_id=113,
    allowed_controllers=(0, 1),
    allowed_interfaces=tuple(range(8)),
    address_evidence=(
        "ET6801.svd:AES.baseAddress+DATA(0x5C)/RESULT(0x74)/DIN0(0x4C)/RESULT_DOUT0(0x64)"
    ),
    request_evidence=(
        "firmware/chips/et6801/sdk/ET6x_Driver/Inc/et6x_sysctrl.h:"
        "DMAMUX_REQ_AES_WR/DMAMUX_REQ_AES_RD"
    ),
)
