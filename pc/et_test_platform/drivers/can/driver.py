# CAN单IP直接动作。
# 职责：调用稳定命令、严格解码并在统一Deadline内等待硬件状态。
# 边界：不操作GPIO、CRG或CAN盒子，不编排完整Case，不判断PASS。
# 依赖：TargetClient、公共Deadline和本IPCodec/Model。

from ...clients.target import TargetClient
from ...core.deadline import OperationDeadline
from ...core.errors import ProtocolError, RequestTimeout
from . import codec, contract
from .contract import CanCommand
from .models import CanIdentity, CanOptionLimits, CanOptions, CanRamLayout, CanRamLimits, CanTiming


# 一个对象绑定一个逻辑CAN实例；构造不配置硬件或选择物理引脚。
class CanDriver:
    # 校验实例的Wire表示范围，不擅自回退到其他Controller。
    def __init__(self, target: TargetClient, instance_id: int) -> None:
        codec.encode_request(CanCommand.IDENTITY_GET, instance_id, ())
        self._target = target
        self.instance_id = instance_id

    # 查询真实只读身份；只等待本次响应，通信失败直接上抛。
    def identity_get(self, *, timeout_s: float | None = None) -> CanIdentity:
        return CanIdentity(*self._request(CanCommand.IDENTITY_GET, timeout_s=timeout_s))

    # 请求进入/离开INIT；命令接受不代表已完成总线同步，必须另行查询。
    # 不轮询、不改变引脚或时钟；写命令失败不自动重试。
    def initializing_set(self, initializing: bool, *, timeout_s: float | None = None) -> None:
        self._request(
            CanCommand.INITIALIZING_SET, (codec.boolean(initializing),), timeout_s=timeout_s
        )

    # 单次读取INIT真实状态；非法非Boolean响应属于协议错误。
    def initializing_get(self, *, timeout_s: float | None = None) -> bool:
        (value,) = self._request(CanCommand.INITIALIZING_GET, timeout_s=timeout_s)
        if value not in (0, 1):
            raise ProtocolError(f"CAN initialization state is not Boolean: {value}")
        return bool(value)

    # 在一个Deadline内等待指定INIT状态，不隐式发状态切换命令。
    # 超时保留最后读值，不复位IP或改写时序以掩盖同步问题。
    def wait_initializing(self, initializing: bool, *, timeout_s: float) -> None:
        codec.boolean(initializing)
        deadline = OperationDeadline.start(timeout_s, label=f"CAN INIT {self.instance_id}")
        last = None
        try:
            while True:
                last = self.initializing_get(timeout_s=deadline.remaining_s())
                if last is initializing:
                    return
                deadline.sleep(contract.POLL_INTERVAL_S)
        except RequestTimeout as error:
            raise RequestTimeout(f"CAN INIT expected={initializing}, last={last}") from error

    # 查询实际计数编码上限；不据此猜测输入时钟或总线速率。
    # 仅等待单次命令响应，超时或非法响应直接上抛，不补默认值。
    def timing_limits_get(self, *, timeout_s: float | None = None) -> CanTiming:
        return codec.decode_timing(self._request(CanCommand.TIMING_LIMITS_GET, timeout_s=timeout_s))

    # 仅设置两阶段时序；调用者先显式进入INIT，失败不会隐式停止CAN。
    # 等待设置响应，不等待收发完成；非法参数或状态错误直接上抛。
    def timing_set(self, timing: CanTiming, *, timeout_s: float | None = None) -> None:
        self._request(CanCommand.TIMING_SET, codec.timing_words(timing), timeout_s=timeout_s)

    # 从控制器读取实际配置，不返回先前请求对象；仅等待本次响应。
    def timing_get(self, *, timeout_s: float | None = None) -> CanTiming:
        return codec.decode_timing(self._request(CanCommand.TIMING_GET, timeout_s=timeout_s))

    # 设置完整核心选项，保持RAM布局、过滤和时序不变。
    # 只等待本次响应；前提为INIT，不自动修复缺少的前置步骤。
    def options_set(self, options: CanOptions, *, timeout_s: float | None = None) -> None:
        self._request(CanCommand.OPTIONS_SET, codec.option_words(options), timeout_s=timeout_s)

    # 实际硬件选项读回，非法响应失败关闭；不清除协议错误或FIFO。
    def options_get(self, *, timeout_s: float | None = None) -> CanOptions:
        return codec.decode_options(self._request(CanCommand.OPTIONS_GET, timeout_s=timeout_s))

    # 查询TDC和Watchdog可编程周期上限；不作为性能或物理时钟测量。
    # 仅等待单次命令响应，超时或解码失败直接上抛，不重配置硬件。
    def option_limits_get(self, *, timeout_s: float | None = None) -> CanOptionLimits:
        return CanOptionLimits(*self._request(CanCommand.OPTION_LIMITS_GET, timeout_s=timeout_s))

    # 查询实例的RAM容量和区域上限；只等待单次响应，失败直接上抛。
    # 不根据这些上限自动分配布局，不操作资源池。
    def ram_limits_get(self, *, timeout_s: float | None = None) -> CanRamLimits:
        return CanRamLimits(*self._request(CanCommand.RAM_LIMITS_GET, timeout_s=timeout_s))

    # 设置明确的完整RAM布局，调用者须先进入INIT。
    # 只等待设置响应；参数/状态错误直接上抛，不清空RAM或隐式复位。
    def ram_layout_set(self, layout: CanRamLayout, *, timeout_s: float | None = None) -> None:
        self._request(
            CanCommand.RAM_LAYOUT_SET, codec.ram_layout_words(layout), timeout_s=timeout_s
        )

    # 从硬件读取全部RAM布局，只等待单次响应，非法编码作为协议失败。
    # 不返回本地布局对象；无读取数据、FIFO Ack或资源释放副作用。
    def ram_layout_get(self, *, timeout_s: float | None = None) -> CanRamLayout:
        return codec.decode_ram_layout(
            self._request(CanCommand.RAM_LAYOUT_GET, timeout_s=timeout_s)
        )

    # 集中单次请求和精确长度检查；只读查询才声明可安全重试。
    def _request(
        self, command: CanCommand, words: tuple[int, ...] = (), *, timeout_s: float | None = None
    ) -> tuple[int, ...]:
        body = codec.encode_request(command, self.instance_id, words)
        message, _ = self._target.request(
            contract.CAN_SERVICE_ID,
            int(command),
            instance_id=self.instance_id,
            body=body,
            timeout_s=timeout_s,
            retry_safe=command in contract.READ_ONLY_COMMANDS,
        )
        return codec.decode_response(command, message.body)
