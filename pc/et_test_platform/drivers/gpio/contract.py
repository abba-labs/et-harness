# GPIO信号配置的公共Wire合同。
# 职责：保留已有功能编号，声明独立GPIO Service的命令。
# 边界：功能是信号身份，不是芯片mux编码，不包含Board默认值。
# 依赖：标准库Enum。

from enum import IntEnum

GPIO_SERVICE_ID = 0x0014


# 编号与固件GPIO Wrap公开契约一致；不随对测角色交换而改变。
class GpioFunction(IntEnum):
    GPIO = 0
    UART_TX = 1
    UART_RX = 2
    SPI_CLK = 3
    SPI_CS = 4
    SPI_MOSI = 5
    SPI_MISO = 6


# VALIDATE只查询映射，CONFIGURE只执行单引脚配置。
class GpioCommand(IntEnum):
    VALIDATE_SIGNAL = 1
    CONFIGURE_SIGNAL = 2
