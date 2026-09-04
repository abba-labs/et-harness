# Formal Case平台级IP注册表。
#
# 职责：显式组合允许进入正式执行集合的IP及其Case白名单。
# 边界：不发现Case、不执行pytest、不访问Capability、Runtime Service或硬件。
# 依赖：仅依赖通用注册模型和各IP的静态Case ID元组。

from ..scheduling.test_registry import IpRegistration

# from .aes.case_registry import AES_CASE_REGISTRY
# from .cordic.case_registry import CORDIC_CASE_REGISTRY
# from .crc.case_registry import CRC_CASE_REGISTRY
# from .dma.case_registry import DMA_CASE_REGISTRY
# from .fmac.case_registry import FMAC_CASE_REGISTRY
# from .framework_communication.case_registry import FRAMEWORK_COMMUNICATION_CASE_REGISTRY
# from .ipcm.case_registry import IPCM_CASE_REGISTRY
from .spi.case_registry import SPI_CASE_REGISTRY

# from .spinlock.case_registry import SPINLOCK_CASE_REGISTRY
# from .stimer.case_registry import STIMER_CASE_REGISTRY
# from .syscnt.case_registry import SYSCNT_CASE_REGISTRY
# from .uart.case_registry import UART_CASE_REGISTRY
# from .wdg.case_registry import WDG_CASE_REGISTRY

# 本轮按用户指定仅执行SPI；其他IP注册定义保留，测试后恢复原选择。
IP_REGISTRY = (IpRegistration(ip_id="spi", case_ids=SPI_CASE_REGISTRY),)
