# ET6801 SPI DMA执行事实。
# 职责：声明SDK DMAMUX请求号、数据端点及合法Controller/Interface。
# 边界：不操作硬件，不包含Case激励和判定。
# 依赖：标准库；事实依据为et6801.h的SPIx_BASE/DR[0]及et6x_sysctrl.h的DMAMUX_REQ_SPIx_TX/RX。

from types import MappingProxyType

# DR是32-bit寄存器；每次访问携带一个SPI帧，线上有效位数由DFS确定。
SPI_DMA_ACCESS_BITS = 32
SPI_DMA_CONTROLLERS = (0, 1)
SPI_DMA_INTERFACES = tuple(range(8))

# 每项依次为DR[0]地址、TX请求号、RX请求号；SDK的SPI请求枚举从214连续排列。
SPI_DMA_ENDPOINTS = MappingProxyType(
    {
        0: (0x4050B060, 214, 215),
        1: (0x4050C060, 216, 217),
        2: (0x4050D060, 218, 219),
        3: (0x4050E060, 220, 221),
    }
)
