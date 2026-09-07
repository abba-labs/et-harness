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
    CanEventFormat,
    CanFilter,
    CanHighPriorityStatus,
    CanIdentity,
    CanIrqEvent,
    CanIrqSnapshot,
    CanIrqSource,
    CanLoopback,
    CanOptionLimits,
    CanOptions,
    CanPhaseTiming,
    CanProtocolStatus,
    CanRamLayout,
    CanRamLimits,
    CanRxBufferStatus,
    CanRxFifoStatus,
    CanRxFrame,
    CanRxSource,
    CanTiming,
    CanTxEvent,
    CanTxEventDetails,
    CanTxEventStatus,
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

    # 本次受保护写显式保留硬件权限；普通timing_set的自动解锁行为不变。
    # 只等待本次响应，timeout_s传到底层；失败上抛，不重试写入或改变INIT。
    def configuration_write_set(self, enabled: bool, *, timeout_s: float | None = None) -> None:
        self._request(
            CanCommand.CONFIGURATION_WRITE_SET, (codec.boolean(enabled),), timeout_s=timeout_s
        )

    # 独立读取当前配置权限；单次响应失败直接上抛，不修改INIT。
    def configuration_write_get(self, *, timeout_s: float | None = None) -> bool:
        return codec.status_boolean(
            self._request(CanCommand.CONFIGURATION_WRITE_GET, timeout_s=timeout_s)[0]
        )

    # 尝试写入仲裁位时序，不打开配置权限；返回不代表硬件接受，须另行读回。
    # 一次请求在timeout_s内完成，通信错误直接上抛，不执行Case比较或重试。
    def nominal_timing_write(
        self, timing: CanPhaseTiming, *, timeout_s: float | None = None
    ) -> None:
        words = codec.timing_words(CanTiming(timing, timing))[: len(contract.PHASE_FIELDS)]
        self._request(CanCommand.NOMINAL_TIMING_WRITE, words, timeout_s=timeout_s)

    # 显式选择Marker位宽与TSU使用；不进入INIT或配置TSU计数源。
    # 写入只执行一次，timeout_s传递到底层；失败不重试，配置须独立读回。
    def event_format_set(self, config: CanEventFormat, *, timeout_s: float | None = None) -> None:
        self._request(
            CanCommand.EVENT_FORMAT_SET, codec.event_format_words(config), timeout_s=timeout_s
        )

    # 读取实际有效格式；一次请求失败上抛，不返回缓存或消耗事件。
    def event_format_get(self, *, timeout_s: float | None = None) -> CanEventFormat:
        return codec.decode_event_format(
            self._request(CanCommand.EVENT_FORMAT_GET, timeout_s=timeout_s)
        )

    # 读取当前事件及有效性；宽Marker不伪造内部时间戳，TSU槽仅表示指针。
    # 一次请求受timeout_s约束，失败上抛；不Ack、不轮询、不读取TSU捕获寄存器。
    def tx_event_details_read(self, *, timeout_s: float | None = None) -> CanTxEventDetails:
        return codec.decode_tx_event_details(
            self._request(CanCommand.TX_EVENT_DETAILS_READ, timeout_s=timeout_s)
        )

    # 连续模式下重装一次并返回相邻的实际前后计数；不清IRQ，不改变配置。
    # 一次请求受timeout_s约束，失败上抛且不重试；不含PC等待或假定读回等于TOP。
    def timeout_reload(self, *, timeout_s: float | None = None) -> tuple[int, int]:
        before, after = self._request(CanCommand.TIMEOUT_RELOAD, timeout_s=timeout_s)
        if before > 0xFFFF or after > 0xFFFF:
            raise ProtocolError("CAN timeout reload returned an invalid 16-bit count")
        return before, after

    # 在已进入INIT的控制器上选择FD编码；不进入INIT，不隐式重发。
    # timeout_s约束一次命令，失败直接上抛；模式生效须独立读回。
    def non_iso_set(self, enabled: bool, *, timeout_s: float | None = None) -> None:
        self._request(CanCommand.NON_ISO_SET, (codec.boolean(enabled),), timeout_s=timeout_s)

    # 读取实际FD编码选择；非法Boolean失败关闭，不返回请求缓存。
    def non_iso_get(self, *, timeout_s: float | None = None) -> bool:
        return codec.status_boolean(self._request(CanCommand.NON_ISO_GET, timeout_s=timeout_s)[0])

    # 连续消费一次协议状态和错误计数；读清字段会被确认，不允许自动重试。
    # 失败上抛，调用者应保存首个读回；返回值不是同时发生的原子快照。
    def protocol_status_consume(self, *, timeout_s: float | None = None) -> CanProtocolStatus:
        return codec.decode_protocol_status(
            self._request(CanCommand.PROTOCOL_STATUS_CONSUME, timeout_s=timeout_s)
        )

    # 单次读取计时值，不配置时钟源或预分频；命令超时直接上抛。
    def timestamp_get(self, *, timeout_s: float | None = None) -> int:
        return self._request(CanCommand.TIMESTAMP_GET, timeout_s=timeout_s)[0]

    # 单次清零时间戳；不读回、不插入延时，不假定下一次查询仍为零。
    # 只等待本次响应；超时或设备失败直接上抛，不自动再清一次。
    def timestamp_reset(self, *, timeout_s: float | None = None) -> None:
        self._request(CanCommand.TIMESTAMP_RESET, timeout_s=timeout_s)

    # 单次读取超时计数，不重装、不改变Timeout来源；通信失败直接上抛。
    def timeout_counter_get(self, *, timeout_s: float | None = None) -> int:
        return self._request(CanCommand.TIMEOUT_COUNTER_GET, timeout_s=timeout_s)[0]

    # 设置或撤回Clock Stop请求；不把命令接受当作CSA生效，不自动清INIT。
    # 只等待命令响应；失败原样上抛，应答等待由Case另行决定。
    def clock_stop_set(self, requested: bool, *, timeout_s: float | None = None) -> None:
        self._request(CanCommand.CLOCK_STOP_SET, (codec.boolean(requested),), timeout_s=timeout_s)

    # 单次读取Clock Stop Ack；非法Boolean失败，不据此宣称独立时钟真的停振。
    def clock_stop_ack_get(self, *, timeout_s: float | None = None) -> bool:
        (value,) = self._request(CanCommand.CLOCK_STOP_ACK_GET, timeout_s=timeout_s)
        if value not in (0, 1):
            raise ProtocolError(f"CAN clock stop acknowledgement is not Boolean: {value}")
        return bool(value)

    # 在一个Deadline内等待实际Clock Stop Ack；不写请求、不改变INIT或CRG。
    # 超时保留最后读值，禁止把已发送的请求当作硬件应答。
    def wait_clock_stop_ack(self, acknowledged: bool, *, timeout_s: float) -> bool:
        codec.boolean(acknowledged)
        deadline = OperationDeadline.start(timeout_s, label=f"CAN clock stop {self.instance_id}")
        last = None
        try:
            while True:
                last = self.clock_stop_ack_get(timeout_s=deadline.remaining_s())
                if last is acknowledged:
                    return last
                deadline.sleep(contract.POLL_INTERVAL_S)
        except RequestTimeout as error:
            raise RequestTimeout(f"CAN clock stop expected={acknowledged}, last={last}") from error

    # 直接使能或屏蔽公共CAN中断源；仅用于未启动托管Capture时的寄存器语义测试。
    # 不绑定NVIC、不选择中断线，非法位图和非Boolean在发命令前拒绝。
    def irq_mask_set(
        self, sources: CanIrqSource, enabled: bool, *, timeout_s: float | None = None
    ) -> None:
        self._request(
            CanCommand.IRQ_MASK_SET,
            (codec.irq_sources(sources), codec.boolean(enabled)),
            timeout_s=timeout_s,
        )

    # 把指定公共事件选择到控制器Line0或Line1；物理IRQn始终由固件映射。
    # 只接受0/1且不启用事件，便于Case将路由读回与事件投递分开断言。
    # 仅等待本次配置响应；超时或设备失败直接上抛，不自动改选另一条Line。
    def irq_line_select_set(
        self, sources: CanIrqSource, line: int, *, timeout_s: float | None = None
    ) -> None:
        if type(line) is not int or line not in (0, 1):
            raise ValueError(f"CAN interrupt line must be 0 or 1: {line!r}")
        self._request(
            CanCommand.IRQ_LINE_SELECT_SET,
            (codec.irq_sources(sources), line),
            timeout_s=timeout_s,
        )

    # 非破坏读取IR/IE/ILS/ILE公共事实；不清Pending、不消费Service事件证据。
    # 在调用者Deadline内执行一次只读查询；协议或通信失败直接上抛。
    def irq_snapshot_get(self, *, timeout_s: float | None = None) -> CanIrqSnapshot:
        return codec.decode_irq_snapshot(
            self._request(CanCommand.IRQ_SNAPSHOT_GET, timeout_s=timeout_s)
        )

    # 在单个Deadline内等待任一指定Raw源；不读清PSR，不使能或清除IRQ。
    # 超时包含最近快照；调用者可在返回后立即保存首次协议错误码。
    def wait_irq_pending(self, sources: CanIrqSource, *, timeout_s: float) -> CanIrqSnapshot:
        mask = codec.irq_sources(sources)
        if not mask:
            raise ValueError("CAN pending wait requires nonzero sources")
        deadline = OperationDeadline.start(timeout_s, label=f"CAN IRQ pending {self.instance_id}")
        last = None
        try:
            while True:
                last = self.irq_snapshot_get(timeout_s=deadline.remaining_s())
                if last.raw_status & mask:
                    return last
                deadline.sleep(contract.POLL_INTERVAL_S)
        except RequestTimeout as error:
            raise RequestTimeout(f"CAN IRQ expected any={mask:#x}, last={last}") from error

    # 显式W1C清除所选CAN源；不清Service已经锁存的回调证据。
    # Level条件未解除时硬件可再次置位，Case必须独立观测该事实。
    # 仅等待本次清除响应；超时或设备失败直接上抛，不重复W1C。
    def irq_clear(self, sources: CanIrqSource, *, timeout_s: float | None = None) -> None:
        self._request(CanCommand.IRQ_CLEAR, (codec.irq_sources(sources),), timeout_s=timeout_s)

    # 建立一个托管中断Capture；line1_sources必须是sources的子集。
    # 固件负责源清理、逻辑路由和固定ISR证据，不产生测试结论。
    # 不轮询事件；启动失败由固件回退本次路由，错误直接上抛。
    def irq_capture_start(
        self,
        sources: CanIrqSource,
        *,
        line1_sources: CanIrqSource = CanIrqSource.NONE,
        timeout_s: float | None = None,
    ) -> None:
        source_mask = codec.irq_sources(sources)
        line1_mask = codec.irq_sources(line1_sources)
        if source_mask == 0 or line1_mask & ~source_mask:
            raise ValueError("CAN capture sources must be nonzero and contain the Line1 subset")
        self._request(
            CanCommand.IRQ_CAPTURE_START,
            (source_mask, line1_mask),
            timeout_s=timeout_s,
        )

    # 先屏蔽CAN源，再关闭控制器输出并释放IRQ Manager路由；保留已采集证据。
    # 仅等待本次停止响应；失败直接上抛，调用者仍可读取故障Evidence。
    def irq_capture_stop(self, *, timeout_s: float | None = None) -> None:
        self._request(CanCommand.IRQ_CAPTURE_STOP, timeout_s=timeout_s)

    # 原子复制固定ISR证据；只读不清硬件Pending或软件计数。
    # 在调用者Deadline内执行一次只读查询；协议或通信失败直接上抛。
    def irq_event_get(self, *, timeout_s: float | None = None) -> CanIrqEvent:
        return codec.decode_irq_event(self._request(CanCommand.IRQ_EVENT_GET, timeout_s=timeout_s))

    # 在Capture停止后开启新的空证据代次；不触碰CAN硬件。
    # 仅等待本次复位响应；活动Capture会明确失败，不自动停止它。
    def irq_event_reset(self, *, timeout_s: float | None = None) -> None:
        self._request(CanCommand.IRQ_EVENT_RESET, timeout_s=timeout_s)

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

    # 读回软件持有的TX槽，不返回上次写入请求的缓存，不发起发送。
    # 只等待本次响应；占用槽或非法响应直接报错，不自动等待槽释放。
    def tx_read(self, index: int, *, timeout_s: float | None = None) -> CanTxFrame:
        words = self._request(CanCommand.TX_READ, (codec.uint32(index),), timeout_s=timeout_s)
        return codec.decode_tx_frame(index, words)

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

    # 写一个已经配置的过滤器槽；只等待单次响应，失败直接上抛。
    # 调用者先进入INIT并设置RAM布局，本接口不扩大列表、不复位其他过滤器。
    def filter_set(
        self, index: int, config: CanFilter, *, extended: bool, timeout_s: float | None = None
    ) -> None:
        words = (codec.boolean(extended), codec.uint32(index)) + codec.filter_words(
            extended, config
        )
        self._request(CanCommand.FILTER_SET, words, timeout_s=timeout_s)

    # 独立读取过滤器RAM；只等待本次响应，不返回SET缓存或消费接收FIFO。
    # 超出列表范围或未知编码直接失败，不自动切换标准/扩展格式。
    def filter_get(
        self, index: int, *, extended: bool, timeout_s: float | None = None
    ) -> CanFilter:
        return codec.decode_filter(
            self._request(
                CanCommand.FILTER_GET,
                (codec.boolean(extended), codec.uint32(index)),
                timeout_s=timeout_s,
            )
        )

    # 设置扩展ID全局AND掩码；只等待本次响应，失败不重试。
    # 调用者先进入INIT；不更改单条过滤器或未匹配帧接收策略。
    def extended_mask_set(self, mask: int, *, timeout_s: float | None = None) -> None:
        if codec.uint32(mask) > contract.EXTENDED_ID_MAX:
            raise ValueError("CAN extended mask exceeds protocol identifier width")
        self._request(CanCommand.EXTENDED_MASK_SET, (mask,), timeout_s=timeout_s)

    # 读取实际扩展ID掩码；只等待单次响应，不清除任何中断或接收数据。
    # 响应越过协议ID宽度时作为错误，不能静默截断。
    def extended_mask_get(self, *, timeout_s: float | None = None) -> int:
        (mask,) = self._request(CanCommand.EXTENDED_MASK_GET, timeout_s=timeout_s)
        if mask > contract.EXTENDED_ID_MAX:
            raise ProtocolError(f"CAN extended mask is invalid: {mask:#x}")
        return mask

    # 读取最后一个High Priority Message状态；不读取帧、不Ack FIFO或清除IRQ。
    # 返回Filter列表、索引和实际存储位置，失败直接上抛。
    def high_priority_status_get(self, *, timeout_s: float | None = None) -> CanHighPriorityStatus:
        return codec.decode_high_priority_status(
            self._request(CanCommand.HIGH_PRIORITY_STATUS_GET, timeout_s=timeout_s)
        )

    # 读取TX Event FIFO的fill/get/put/full/lost；不读取或Ack当前事件。
    # 只等待本次请求，超时或设备失败直接上抛；Boolean非法时作为协议错误。
    def tx_event_status_get(self, *, timeout_s: float | None = None) -> CanTxEventStatus:
        words = self._request(CanCommand.TX_EVENT_STATUS_GET, timeout_s=timeout_s)
        return CanTxEventStatus(*words[:3], *(codec.status_boolean(value) for value in words[3:]))

    # 读取当前TX Event FIFO头；不Ack、不改变后续事件或TX状态。
    # 只等待本次请求，超时或设备失败直接上抛；返回实际Get Index供显式Ack。
    def tx_event_read(self, *, timeout_s: float | None = None) -> CanTxEvent:
        return codec.decode_tx_event(self._request(CanCommand.TX_EVENT_READ, timeout_s=timeout_s))

    # 只Ack调用者指定的当前TX Event FIFO头，不循环排空或清除IRQ。
    # 只等待本次请求，超时或设备失败直接上抛；写操作不安全重试。
    def tx_event_ack(self, index: int, *, timeout_s: float | None = None) -> None:
        self._request(CanCommand.TX_EVENT_ACK, (codec.uint32(index),), timeout_s=timeout_s)

    # 设置指定TX槽的完成事件开关；不隐式开启全局中断源或IRQ Line。
    # 参数：index为当前已分配槽，enabled为布尔值；失败由目标端原样上抛。
    def tx_buffer_irq_set(
        self, index: int, enabled: bool, *, timeout_s: float | None = None
    ) -> None:
        self._request(
            CanCommand.TX_BUFFER_IRQ_SET,
            (codec.uint32(index), codec.boolean(enabled)),
            timeout_s=timeout_s,
        )

    # 保留已置位Raw后绑定并开放IRQ；与清历史状态的irq_capture_start明确分开。
    # 只等待本次命令响应，不轮询ISR；超时及绑定失败直接上抛，写操作不重试。
    def irq_capture_pending(
        self,
        sources: CanIrqSource,
        *,
        line1_sources: CanIrqSource = CanIrqSource.NONE,
        timeout_s: float | None = None,
    ) -> None:
        source_mask = codec.irq_sources(sources)
        line1_mask = codec.irq_sources(line1_sources)
        if source_mask == 0 or line1_mask & ~source_mask:
            raise ValueError("CAN capture sources must be nonzero and contain the Line1 subset")
        self._request(
            CanCommand.IRQ_CAPTURE_PENDING,
            (source_mask, line1_mask),
            timeout_s=timeout_s,
        )

    # 查询实际ISR投递线路的源锁存；返回Line0、Line1，不把Service证据冒充寄存器。
    # 在调用者timeout_s内执行一次查询；协议或通信失败直接上抛，不清计数。
    def irq_line_events_get(
        self, *, timeout_s: float | None = None
    ) -> tuple[CanIrqSource, CanIrqSource]:
        words = self._request(CanCommand.IRQ_LINE_EVENTS_GET, timeout_s=timeout_s)
        return CanIrqSource(words[0]), CanIrqSource(words[1])

    # Message RAM按公共word数组访问；三种操作共用只做编解码的边界检查。
    # 请求在timeout_s内完成，通信错误直接上抛，不重试写或交换，不自动推进RAM测试。
    def ram_words_read(
        self,
        offset: int,
        count: int,
        *,
        descending: bool = False,
        timeout_s: float | None = None,
    ) -> tuple[int, ...]:
        return self._ram_access(CanCommand.RAM_WORDS_READ, offset, count, (), descending, timeout_s)

    # 写指定相对偏移的word数组；INIT前置条件由目标验证，失败不改变其他IP。
    # 不等待CAN收发，也不执行比较；命令超时直接上抛，禁止自动重发。
    def ram_words_write(
        self,
        offset: int,
        values: tuple[int, ...],
        *,
        descending: bool = False,
        timeout_s: float | None = None,
    ) -> None:
        self._ram_access(
            CanCommand.RAM_WORDS_WRITE, offset, len(values), values, descending, timeout_s
        )

    # 对每个word先读后写，再访问下一个word；返回旧值，数组仍按地址升序排列。
    # descending只改变硬件访问顺序；单次timeout_s内完成，不隐式重试或比较Expected。
    # 目标状态错误或通信超时直接上抛，不自动复位控制器。
    def ram_words_exchange(
        self,
        offset: int,
        values: tuple[int, ...],
        *,
        descending: bool = False,
        timeout_s: float | None = None,
    ) -> tuple[int, ...]:
        return self._ram_access(
            CanCommand.RAM_WORDS_EXCHANGE, offset, len(values), values, descending, timeout_s
        )

    # 纯协议边界：校验word对齐、固定批大小及零填充，容量由目标发布并独立验证。
    def _ram_access(self, command, offset, count, values, descending, timeout_s):
        codec.uint32(offset)
        codec.uint32(count)
        if offset % contract.WORD.size or not 1 <= count <= contract.RAM_ACCESS_WORDS:
            raise ValueError("CAN Message RAM access requires aligned offset and 1..64 words")
        words = (offset, count, codec.boolean(descending))
        if command != CanCommand.RAM_WORDS_READ:
            words += tuple(codec.uint32(value) for value in values)
            words += (0,) * (contract.RAM_ACCESS_WORDS - count)
        response = self._request(command, words, timeout_s=timeout_s)
        if command == CanCommand.RAM_WORDS_WRITE:
            return ()
        if any(response[count:]):
            raise ProtocolError("CAN Message RAM response has nonzero padding")
        return response[:count]

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
