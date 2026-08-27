# ET6801 CORDIC DMA 执行映射。
#
# 职责：保存 CORDIC SINCOS 输入端点、结果端点和双向 DMA Request 事实。
# 边界：只提供 ET6801 数据，不访问 TargetClient，也不执行测试流程。
# 依赖：仅依赖标准库不可变容器。

from __future__ import annotations

from types import MappingProxyType


# CORDIC_P2_001 固定验证 SINCOS(0)，因此输入端点使用当前 ET6801 的 SINCOS_CAL；
# 输出端点使用第一个结果寄存器 RES1_RPT。Request 39/40 来自 ET6801 验证工程中
# 仍实际执行 CORDIC DMA 的 SYSCTRL 枚举，端点地址则以当前 ET6801 SVD/CMSIS 为准。
CORDIC_DMA_MAPPING = MappingProxyType(
    {
        0: MappingProxyType(
            {
                "controller": 0,
                "input_interface": 0,
                "output_interface": 1,
                "input_request_id": 39,
                "output_request_id": 40,
                "input_endpoint": 0x50000008,
                "output_endpoint": 0x50000050,
                "address_evidence": (
                    "ET6801.svd:CORDIC.baseAddress+SINCOS_CAL(0x08)/RES1_RPT(0x50)"
                ),
                "request_evidence": (
                    "et6801-verification/DFP/Test/Coremark/DFP/Drivers/ET6x_Driver/Inc/"
                    "et6x_sysctrl.h:DMAMUX_REQ_CORDIC_TX/DMAMUX_REQ_CORDIC_RX"
                ),
            }
        )
    }
)
