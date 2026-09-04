# SPI静态Case注册表。
# 职责：登记已经落地并与SPEC绑定的稳定Case ID。
# 边界：不扫描文件，不访问设备，不包含物理实例或引脚。
# 依赖：按P级分类的本IP正式测试函数。

SPI_CASE_REGISTRY = (
    "spi_p0_001",
    "spi_p0_002",
)
