# ET6801 已人工核对的 STIMER DMA 执行映射。
#
# 职责：保存 STIMER 计数周期寄存器、DMAMUX Request ID 和可用接口事实。
# 边界：只提供 ET6801 数据，不访问 TargetClient、不执行硬件命令，也不包含公共 Resolver 逻辑。
# 依赖：仅依赖芯片无关的 DMA 输入映射公共模型。

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from ....programmers import HaltSampleSpec
from ..dma_routes import DmaInputMapping

# ET6801 六个 STIMER 实例的计数周期寄存器 DMA 读端点与 Request 事实。
STIMER_DMA_INPUT_MAPPINGS: Mapping[int, DmaInputMapping] = MappingProxyType(
    {
        instance_id: DmaInputMapping(
            peripheral="stimer",
            instance_id=instance_id,
            peripheral_address=0x4040600C + (instance_id * 0x1000),
            request_id=104 + instance_id,
            allowed_controllers=(0, 1),
            allowed_interfaces=tuple(range(8)),
            address_evidence=(f"ET6801.svd:STIMER{instance_id}.baseAddress+TCYC(0x0C)"),
            request_evidence=(
                "firmware/chips/et6801/sdk/ET6x_Driver/Inc/et6x_sysctrl.h:"
                f"DMAMUX_REQ_STIMER{instance_id}"
            ),
        )
        for instance_id in range(6)
    }
)

# ET6801 CMSIS core_cm7.h：DHCSR.S_HALT=bit17，读取不会清除该状态位。
# ET6801.svd：STIMER0基址0x40406000，各实例间隔0x1000；CNT_RPT偏移0x68、STM_SET偏移0x04。
# 采样顺序固定为实时计数、策略配置；两个寄存器均无read-to-clear副作用。
STIMER_HALT_SAMPLE_SPECS: Mapping[int, HaltSampleSpec] = MappingProxyType(
    {
        instance_id: HaltSampleSpec(
            status_address=0xE000EDF0,
            halted_mask=1 << 17,
            register_addresses=(
                0x40406068 + instance_id * 0x1000,
                0x40406004 + instance_id * 0x1000,
            ),
        )
        for instance_id in range(6)
    }
)

# ET6801.svd STM_SET.STM_CPUHALT_MODE_R bit7：0=停核时暂停，1=停核时继续计数。
STIMER_RUN_FREE_MASK = 1 << 7
