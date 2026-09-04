# CAN单IP直接动作。
# 职责：调用稳定命令、严格解码并在统一Deadline内等待硬件状态。
# 边界：不操作GPIO、CRG或CAN盒子，不编排完整Case，不判断PASS。
# 依赖：TargetClient、公共Deadline和本IPCodec/Model。

from ...clients.target import TargetClient
from ...core.deadline import OperationDeadline
from ...core.errors import ProtocolError, RequestTimeout
from . import codec, contract
from .contract import CanCommand
from .models import (
    CanBusConfig,
    CanBusLimits,
    CanIdentity,
    CanLoopback,
    CanOptionLimits,
    CanOptions,
    CanRamLayout,
    CanRamLimits,
    CanRxBufferStatus,
    CanRxFifoStatus,
    CanRxFrame,
    CanRxSource,
    CanTiming,
    CanTxFrame,
    CanTxStatus,
)


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

    # 设置明确的总线、全局过滤和计时配置；调用者先进入INIT。
    # 只等待本次响应，失败上抛，不配置回环或隐式启动控制器。
    def bus_config_set(self, config: CanBusConfig, *, timeout_s: float | None = None) -> None:
        self._request(
            CanCommand.BUS_CONFIG_SET, codec.bus_config_words(config), timeout_s=timeout_s
        )

    # 读取真实总线配置，只等待单次响应；未知选择器返回协议错误。
    # 不清除错误计数，也不返回上一次SET缓存。
    def bus_config_get(self, *, timeout_s: float | None = None) -> CanBusConfig:
        return codec.decode_bus_config(
            self._request(CanCommand.BUS_CONFIG_GET, timeout_s=timeout_s)
        )

    # 查询实际计时字段上限，只等待单次响应，失败直接上抛。
    def bus_limits_get(self, *, timeout_s: float | None = None) -> CanBusLimits:
        return CanBusLimits(*self._request(CanCommand.BUS_LIMITS_GET, timeout_s=timeout_s))

    # 在INIT状态设置回环；关闭内部回环会退出MON隔离，不配置IO。
    # 只等待命令响应，失败不重试、不复位、不启动控制器。
    def loopback_set(self, mode: CanLoopback, *, timeout_s: float | None = None) -> None:
        if not isinstance(mode, CanLoopback):
            raise ValueError("CAN loopback requires CanLoopback")
        self._request(CanCommand.LOOPBACK_SET, (int(mode),), timeout_s=timeout_s)

    # 读取有效回环状态，只等待本次响应，未知状态直接作为协议错误。
    def loopback_get(self, *, timeout_s: float | None = None) -> CanLoopback:
        (value,) = self._request(CanCommand.LOOPBACK_GET, timeout_s=timeout_s)
        try:
            return CanLoopback(value)
        except ValueError as error:
            raise ProtocolError(f"CAN loopback mode is invalid: {value}") from error

    # 只把帧写入指定TX槽，不发TX请求；只等待本次响应，非法帧在发送命令前拒绝。
    # 槽被占用或配置不足时固件返回错误，不隐式等待、复位或扩大RAM。
    def tx_write(self, index: int, frame: CanTxFrame, *, timeout_s: float | None = None) -> None:
        self._request(CanCommand.TX_WRITE, codec.tx_frame_words(index, frame), timeout_s=timeout_s)

    # 一次提交显式非零TX Buffer位图；只等待接受响应，不代表总线完成。
    # 失败直接上抛且不重试；帧准备和完成检查由调用者分开执行。
    def tx_request(self, mask: int, *, timeout_s: float | None = None) -> None:
        if codec.uint32(mask) == 0:
            raise ValueError("CAN TX mask must not be zero")
        self._request(CanCommand.TX_REQUEST, (mask,), timeout_s=timeout_s)

    # 非破坏读取TX状态，只等待本次响应；非法长度或Boolean直接作为协议错误。
    # 不读取TX Event，也不清除已完成/已取消状态。
    def tx_status_get(self, *, timeout_s: float | None = None) -> CanTxStatus:
        words = self._request(CanCommand.TX_STATUS_GET, timeout_s=timeout_s)
        return CanTxStatus(*words[:-1], codec.status_boolean(words[-1]))

    # 单一Deadline内等待指定请求全部完成，不重发帧；超时保留最后TX事实。
    # 这是硬件等待，不代表ID、数据或测试Feature已经通过。
    def wait_tx_complete(self, mask: int, *, timeout_s: float) -> CanTxStatus:
        if codec.uint32(mask) == 0:
            raise ValueError("CAN TX mask must not be zero")
        deadline = OperationDeadline.start(timeout_s, label=f"CAN TX {self.instance_id}")
        last = None
        try:
            while True:
                last = self.tx_status_get(timeout_s=deadline.remaining_s())
                if last.completed & mask == mask:
                    return last
                deadline.sleep(contract.POLL_INTERVAL_S)
        except RequestTimeout as error:
            raise RequestTimeout(f"CAN TX mask={mask:#010x}, last={last}") from error

    # 查询指定FIFO的真实fill/get/put/full/lost；只等待单次响应，不Ack或清状态。
    # 参数或响应无效直接失败，不自动回退到另一个FIFO。
    def rx_fifo_status_get(self, fifo: int, *, timeout_s: float | None = None) -> CanRxFifoStatus:
        words = self._request(
            CanCommand.RX_FIFO_STATUS_GET, (codec.uint32(fifo),), timeout_s=timeout_s
        )
        return CanRxFifoStatus(*words[:-2], *(codec.status_boolean(value) for value in words[-2:]))

    # 在统一Deadline内等待FIFO达到指定最小填充数，不读取帧或隐式Ack。
    # 超时给出最后状态，不扩大超时掩盖无接收；最终内容比较仍由Case执行。
    def wait_rx_available(
        self, fifo: int, *, minimum: int = 1, timeout_s: float
    ) -> CanRxFifoStatus:
        if codec.uint32(minimum) == 0:
            raise ValueError("CAN RX minimum must be positive")
        deadline = OperationDeadline.start(timeout_s, label=f"CAN RX {self.instance_id}/{fifo}")
        last = None
        try:
            while True:
                last = self.rx_fifo_status_get(fifo, timeout_s=deadline.remaining_s())
                if last.fill >= minimum:
                    return last
                deadline.sleep(contract.POLL_INTERVAL_S)
        except RequestTimeout as error:
            raise RequestTimeout(f"CAN RX minimum={minimum}, last={last}") from error

    # 读取Dedicated Buffer或FIFO当前头，只等待单次响应，不做Ack。
    # 空接收区原样返回设备错误；FIFO参数index必须为0，实际索引在返回帧中。
    def rx_read(
        self, source: CanRxSource, index: int = 0, *, timeout_s: float | None = None
    ) -> CanRxFrame:
        if not isinstance(source, CanRxSource):
            raise ValueError("CAN receive source requires CanRxSource")
        codec.uint32(index)
        if source is not CanRxSource.BUFFER and index != 0:
            raise ValueError("CAN FIFO reads use the current head, index argument must be zero")
        return codec.decode_rx_frame(
            self._request(CanCommand.RX_READ, (int(source), index), timeout_s=timeout_s)
        )

    # 显式Ack已读取的FIFO头索引；只等待本次响应，过期索引或空FIFO直接失败。
    # 不循环清空后续帧，也不在失败时复位控制器。
    def rx_fifo_ack(self, fifo: int, index: int, *, timeout_s: float | None = None) -> None:
        self._request(
            CanCommand.RX_FIFO_ACK, (codec.uint32(fifo), codec.uint32(index)), timeout_s=timeout_s
        )

    # 非破坏读取两组Dedicated Buffer新数据位图，只等待响应，失败直接上抛。
    def rx_buffer_status_get(self, *, timeout_s: float | None = None) -> CanRxBufferStatus:
        return CanRxBufferStatus(
            *self._request(CanCommand.RX_BUFFER_STATUS_GET, timeout_s=timeout_s)
        )

    # 只清除调用者指定的两组新数据位图；只等待本次响应，失败不自动重试。
    # 不读取帧、不清FIFO，也不把资源池复位混入CAN命令。
    def rx_buffer_ack(self, low: int, high: int, *, timeout_s: float | None = None) -> None:
        self._request(
            CanCommand.RX_BUFFER_ACK, (codec.uint32(low), codec.uint32(high)), timeout_s=timeout_s
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
