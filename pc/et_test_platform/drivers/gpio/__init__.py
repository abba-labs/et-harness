# GPIO公共Driver入口。
# 职责：导出稳定信号身份与原子配置接口。
# 边界：导入不访问硬件、不选择引脚或SPI实例。
# 依赖：本包契约及Driver。

from .contract import GPIO_SERVICE_ID, GpioFunction
from .driver import GpioDriver

__all__ = ["GPIO_SERVICE_ID", "GpioDriver", "GpioFunction"]
