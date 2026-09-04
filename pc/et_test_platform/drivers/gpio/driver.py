# GPIO单引脚操作。
# 职责：校验逻辑参数、编码请求并检查空响应。
# 边界：不加载连接文件、不配置SPI，不隐式复位其他IP。
# 依赖：TargetClient、公共协议异常及GPIO合同。

from struct import pack

from ...clients.target import TargetClient
from ...core.errors import ProtocolError
from .contract import GPIO_SERVICE_ID, GpioCommand, GpioFunction


# 将调用方提供的逻辑引脚、信号和外设实例传给独立GPIO Service。
# 构造不操作硬件，不保存引脚配置缓存，不调用其他IP Driver。
class GpioDriver:
    # 保存共享通信对象，不创建额外Transport或重试机制。
    def __init__(self, target: TargetClient) -> None:
        self._target = target

    # 查询完整信号组合是否合法；只等待本次响应，不修改任何Pad或外设。
    # 不支持、请求超时和异常响应直接上抛，不退回默认引脚。
    def validate_signal(
        self,
        gpio_id: int,
        function: GpioFunction,
        instance_id: int,
        *,
        timeout_s: float | None = None,
    ) -> None:
        self._request(GpioCommand.VALIDATE_SIGNAL, gpio_id, function, instance_id, timeout_s)

    # 执行一个GPIO的默认Pad与信号复用配置；不改变对应外设的工作模式。
    # 只等待接受响应；失败不重发，配置成功不等于实际通信通过。
    def configure_signal(
        self,
        gpio_id: int,
        function: GpioFunction,
        instance_id: int,
        *,
        timeout_s: float | None = None,
    ) -> None:
        self._request(GpioCommand.CONFIGURE_SIGNAL, gpio_id, function, instance_id, timeout_s)

    # 三个u16LE字段与GPIO Service严格对齐，外设实例在body内而非Service实例内。
    def _request(
        self,
        command: GpioCommand,
        gpio_id: int,
        function: GpioFunction,
        instance_id: int,
        timeout_s: float | None,
    ) -> None:
        for name, value in (("gpio_id", gpio_id), ("instance_id", instance_id)):
            if type(value) is not int or not 0 <= value <= 0xFFFF:
                raise ValueError(f"{name} must be an unsigned 16-bit integer")
        if not isinstance(function, GpioFunction):
            raise ValueError("function must be a GpioFunction")
        message, _ = self._target.request(
            GPIO_SERVICE_ID,
            int(command),
            instance_id=0,
            body=pack("<HHH", gpio_id, int(function), instance_id),
            timeout_s=timeout_s,
            retry_safe=command == GpioCommand.VALIDATE_SIGNAL,
        )
        if message.body:
            raise ProtocolError("GPIO response must be empty")
