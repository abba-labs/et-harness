# Formal Case平台级IP注册表。
#
# 职责：显式组合允许进入正式执行集合的IP及其Case白名单。
# 边界：不发现Case、不执行pytest、不访问Capability、Runtime Service或硬件。
# 依赖：仅依赖通用注册模型和各IP的静态Case ID元组。

from ..scheduling.test_registry import IpRegistration
from .aes.case_registry import AES_CASE_REGISTRY
from .can.case_registry import CAN_CASE_REGISTRY
from .cordic.case_registry import CORDIC_CASE_REGISTRY
from .crc.case_registry import CRC_CASE_REGISTRY
from .dma.case_registry import DMA_CASE_REGISTRY
from .fmac.case_registry import FMAC_CASE_REGISTRY
from .ipcm.case_registry import IPCM_CASE_REGISTRY
from .spi.case_registry import SPI_CASE_REGISTRY
from .spinlock.case_registry import SPINLOCK_CASE_REGISTRY
from .stimer.case_registry import STIMER_CASE_REGISTRY
from .syscnt.case_registry import SYSCNT_CASE_REGISTRY
from .uart.case_registry import UART_CASE_REGISTRY
from .wdg.case_registry import WDG_CASE_REGISTRY

# 2026-09-09 用户指令：已完成开发测试的13个IP全量硬件回归（与Codex各轮基线对比）。
# 回归完成后按用户指示恢复原CAN-only选择。
IP_REGISTRY = (
    IpRegistration(ip_id="can", case_ids=CAN_CASE_REGISTRY),
    IpRegistration(ip_id="spi", case_ids=SPI_CASE_REGISTRY),
    IpRegistration(ip_id="stimer", case_ids=STIMER_CASE_REGISTRY),
    IpRegistration(ip_id="syscnt", case_ids=SYSCNT_CASE_REGISTRY),
    IpRegistration(ip_id="ipcm", case_ids=IPCM_CASE_REGISTRY),
    IpRegistration(ip_id="dma", case_ids=DMA_CASE_REGISTRY),
    IpRegistration(ip_id="crc", case_ids=CRC_CASE_REGISTRY),
    IpRegistration(ip_id="fmac", case_ids=FMAC_CASE_REGISTRY),
    IpRegistration(ip_id="cordic", case_ids=CORDIC_CASE_REGISTRY),
    IpRegistration(ip_id="aes", case_ids=AES_CASE_REGISTRY),
    IpRegistration(ip_id="wdg", case_ids=WDG_CASE_REGISTRY),
    IpRegistration(ip_id="spinlock", case_ids=SPINLOCK_CASE_REGISTRY),
    IpRegistration(ip_id="uart", case_ids=UART_CASE_REGISTRY),
)
