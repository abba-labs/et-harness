# Formal Case本地Support模块。
#
# 职责：聚合本测试域的只读事实、Driver构造和小粒度复用操作。
# 边界：不隐藏完整Case、不拥有最终断言，也不改变公共Scheduling。
# 依赖：仅依赖本IP Driver、Profile事实和稳定公共工具。

from __future__ import annotations

from dataclasses import dataclass

from ...drivers.dma import DmaCapabilities, DmaDriver
from ...drivers.resource import ResourceDriver
from ...drivers.sysctrl import SysctrlDriver
from ...drivers.uart import UartDriver
from ...profiles.bench import DmaPeripheralPairConfig
from ...profiles.resolvers.dma_routes import DmaPeripheralRoute


# 保存 UART DMA Case 使用的 DMA Controller 及其 Driver，不执行测试动作。
@dataclass(frozen=True, slots=True)
class DmaExecutionSupport:
    controller: int
    resource: ResourceDriver
    dma: DmaDriver
    sysctrl: SysctrlDriver


# 保存单方向 UART DMA Case 已核对的 Driver 与 Route 事实。
@dataclass(frozen=True, slots=True)
class UartDmaSupport:
    resource: ResourceDriver
    dma: DmaDriver
    sysctrl: SysctrlDriver
    uart_dut: UartDriver
    uart_peer: UartDriver
    pair: DmaPeripheralPairConfig
    route: DmaPeripheralRoute


# 保存 UART DMA 双向 Case 的两条 Route 与 DMA Runtime Capability。
@dataclass(frozen=True, slots=True)
class UartDmaFullDuplexSupport:
    resource: ResourceDriver
    dma: DmaDriver
    sysctrl: SysctrlDriver
    uart_dut: UartDriver
    uart_peer: UartDriver
    pair: DmaPeripheralPairConfig
    tx_route: DmaPeripheralRoute
    rx_route: DmaPeripheralRoute
    dma_capabilities: DmaCapabilities
