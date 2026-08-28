# ET6801 CORDIC DMA 执行映射。
#
# 职责：保存 CORDIC SQRT 输入端点、结果端点和双向 DMA Request 事实。
# 边界：只提供 ET6801 数据，不访问 TargetClient，也不执行测试流程。
# 依赖：仅依赖标准库不可变容器。

from types import MappingProxyType

# CORDIC_P2_001 固定验证 SQRT(0.25)，因此输入端点使用当前 ET6801 的 SQRT_CAL；
# 输出端点使用第一个结果寄存器 RES1_RPT。ET6801 验证工程把 CORDIC_RX=40
# 用于 Memory-to-Peripheral 输入，把 CORDIC_TX=39 用于 Peripheral-to-Memory 输出；
# 端点地址以当前 ET6801 SVD/CMSIS 为准。
CORDIC_DMA_MAPPING = MappingProxyType(
    {
        0: MappingProxyType(
            {
                "controller": 0,
                "input_interface": 0,
                "output_interface": 1,
                "input_request_id": 40,
                "output_request_id": 39,
                "input_endpoint": 0x50000024,
                "output_endpoint": 0x50000050,
                "address_evidence": ("ET6801.svd:CORDIC.baseAddress+SQRT_CAL(0x24)/RES1_RPT(0x50)"),
                "request_evidence": (
                    "et6801-verification/DFP/Test/Coremark/DFP/Drivers/ET6x_Driver/Inc/"
                    "et6x_sysctrl.h:DMAMUX_REQ_CORDIC_TX/DMAMUX_REQ_CORDIC_RX"
                ),
            }
        )
    }
)
