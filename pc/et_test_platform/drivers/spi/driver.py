# SPI单IP业务动作。
# 职责：隐藏命令编码、响应校验及统一Deadline内的有界等待。
# 边界：不初始化其他IP、不编排收发对测、不判断Feature通过。
# 依赖：本IPCodec/Model、TargetClient及公共Deadline。

from collections.abc import Sequence

from ...clients.target import TargetClient
from ...core.deadline import OperationDeadline
from ...core.errors import EtPlatformError, ProtocolError, RequestTimeout
from . import codec, contract
from .contract import SpiCommand
from .models import (
    SpiConfig,
    SpiErrorStatus,
    SpiFifoLimits,
    SpiIrq,
    SpiIrqEvent,
    SpiLimits,
    SpiSnapshot,
)


# 捕获错误保留完整事件，Case仍可记录第一次硬件现场。
class SpiCaptureError(EtPlatformError):
    # Service故障不是无事件，也不能被当作正常超时忽略。
    def __init__(self, instance_id: int, event: SpiIrqEvent) -> None:
        self.event = event
        super().__init__(f"SPI instance={instance_id} capture failed: {event!r}")


# 实例由Capability/Resolver注入，不选择物理SPI或引脚。
class SpiDriver:
    # 构造不执行硬件动作。
    def __init__(self, target: TargetClient, instance_id: int) -> None:
        codec.encode_request(SpiCommand.LIMITS_GET, instance_id, ())
        self._target = target
        self.instance_id = instance_id

    # 查询可编程边界，不以范围读回代替完整Capability语义；仅等待本次响应。
    def limits_get(self, *, timeout_s: float | None = None) -> SpiLimits:
        return codec.decode_limits(self._request(SpiCommand.LIMITS_GET, timeout_s=timeout_s))

    # 独立读取IRQ、启动及DMA阈值上限，不从FIFO容量猜测。
    # 仅等待本次响应；超时和非法返回直接上抛，不轮询硬件水位。
    def fifo_limits_get(self, *, timeout_s: float | None = None) -> SpiFifoLimits:
        return codec.decode_fifo_limits(
            self._request(SpiCommand.FIFO_LIMITS_GET, timeout_s=timeout_s)
        )

    # 仅在关闭状态写入完整配置；不隐式关模块、清FIFO或选中CS。
    # 等待单次接受响应；已启用、参数非法或传输失败均直接上抛。
    def configure(self, config: SpiConfig, *, timeout_s: float | None = None) -> None:
        self._request(SpiCommand.CONFIGURE, codec.config_words(config), timeout_s=timeout_s)

    # 获取实际硬件配置，不返回请求缓存；非法读回立即抛ProtocolError。
    # 只等待配置查询响应，不等待数据路径完成。
    def config_get(self, *, timeout_s: float | None = None) -> SpiConfig:
        return codec.decode_config(self._request(SpiCommand.CONFIG_GET, timeout_s=timeout_s))

    # 启停模块；关闭会丢弃FIFO数据，Case必须先保存所需观测。
    # 等待控制命令响应，不等待总线空闲。
    def enable_set(self, enabled: bool, *, timeout_s: float | None = None) -> None:
        self._request(SpiCommand.ENABLE_SET, (codec.boolean(enabled),), timeout_s=timeout_s)

    # 显式清空两个FIFO，不承担CRG或资源池复位。
    # 只等待本次复位响应，失败不自动追加第二次复位。
    def fifo_reset(self, *, timeout_s: float | None = None) -> None:
        self._request(SpiCommand.FIFO_RESET, timeout_s=timeout_s)

    # 设置精确分频，目标拒绝不可表示值；不会自动量化或重新启动SPI。
    def divider_set(self, divider: int, *, timeout_s: float | None = None) -> None:
        self._request(SpiCommand.DIVIDER_SET, (divider,), timeout_s=timeout_s)

    # 帧数为真实数量，不是减一编码；目标负责检查当前状态和上限。
    # 等待设置响应；目标忙时不隐式停止SPI。
    def frame_count_set(self, count: int, *, timeout_s: float | None = None) -> None:
        self._request(SpiCommand.FRAME_COUNT_SET, (count,), timeout_s=timeout_s)

    # 选中或释放CS，不配置GPIO，不改变SPI使能。
    # 只等待选择命令响应，不等待收发完成。
    def cs_set(self, selected: bool, *, timeout_s: float | None = None) -> None:
        self._request(SpiCommand.CS_SET, (codec.boolean(selected),), timeout_s=timeout_s)

    # 只在关闭状态改变内部回环；Target仍需要外部SCLK和CS。
    # 等待单次响应，目标忙时保留现场并上抛。
    def loopback_set(self, enabled: bool, *, timeout_s: float | None = None) -> None:
        self._request(SpiCommand.LOOPBACK_SET, (codec.boolean(enabled),), timeout_s=timeout_s)

    # 三个独立阈值以帧为单位，目标统一检查后写入，避免部分更新。
    # 等待设置响应，不等待FIFO到达水位。
    def fifo_thresholds_set(
        self, tx: int, rx: int, start: int, *, timeout_s: float | None = None
    ) -> None:
        self._request(SpiCommand.FIFO_THRESHOLDS_SET, (tx, rx, start), timeout_s=timeout_s)

    # 读取不会清除错误的FIFO/IRQ/DMA事实；仅等待单次响应。
    def snapshot_get(self, *, timeout_s: float | None = None) -> SpiSnapshot:
        return codec.decode_snapshot(self._request(SpiCommand.SNAPSHOT_GET, timeout_s=timeout_s))

    # 等待RX积累到指定水位，不读FIFO、不消费有读清副作用的SR。
    # 每次查询共用总Deadline；超时消息保留最后快照，不复位或重试传输。
    def wait_rx_level(self, minimum: int, *, timeout_s: float) -> SpiSnapshot:
        codec.uint32(minimum)
        deadline = OperationDeadline.start(timeout_s, label=f"SPI RX level {self.instance_id}")
        last = None
        try:
            while True:
                last = self.snapshot_get(timeout_s=deadline.remaining_s())
                if last.rx_level >= minimum:
                    return last
                deadline.sleep(contract.POLL_INTERVAL_S)
        except RequestTimeout as error:
            raise RequestTimeout(f"SPI RX level expected>={minimum}, last={last!r}") from error

    # 等待TX预装完成；只看Level，不产生CS或发送数据，适用于DMA预装Target。
    # 共用总Deadline，失败保留最后快照，不复位或重新启动DMA。
    def wait_tx_level(self, minimum: int, *, timeout_s: float) -> SpiSnapshot:
        codec.uint32(minimum)
        deadline = OperationDeadline.start(timeout_s, label=f"SPI TX level {self.instance_id}")
        last = None
        try:
            while True:
                last = self.snapshot_get(timeout_s=deadline.remaining_s())
                if last.tx_level >= minimum:
                    return last
                deadline.sleep(contract.POLL_INTERVAL_S)
        except RequestTimeout as error:
            raise RequestTimeout(f"SPI TX level expected>={minimum}, last={last!r}") from error

    # 等待指定Raw中断条件成立，不开放NVIC、不清中断、不排空FIFO。
    # 查询共享总Deadline；超时保留最后快照，不通过读SR改变错误状态。
    def wait_irq_raw(self, sources: SpiIrq, *, timeout_s: float) -> SpiSnapshot:
        mask = self._source_mask(sources)
        if not mask:
            raise ValueError("SPI IRQ wait requires a nonzero source")
        deadline = OperationDeadline.start(timeout_s, label=f"SPI Raw {self.instance_id}")
        last = None
        try:
            while True:
                last = self.snapshot_get(timeout_s=deadline.remaining_s())
                if int(last.irq_raw) & mask == mask:
                    return last
                deadline.sleep(contract.POLL_INTERVAL_S)
        except RequestTimeout as error:
            raise RequestTimeout(f"SPI Raw expected={mask}, last={last!r}") from error

    # 明确消费一次可能读清的状态，返回同一次的raw和flags，禁止自动重试。
    # 只等待这次读数；超时后不能用再次读取补造首次状态。
    def error_status_read(self, *, timeout_s: float | None = None) -> SpiErrorStatus:
        return codec.decode_error(self._request(SpiCommand.ERROR_STATUS_READ, timeout_s=timeout_s))

    # 尝试写一帧，不等FIFO空位；True仅表示入FIFO，不表示线上完成。
    # 等待本次接受数量响应；失败不会重复写入同一帧。
    def try_write_frame(self, frame: int, *, timeout_s: float | None = None) -> bool:
        (count,) = self._request(SpiCommand.WRITE_FRAME, (frame,), timeout_s=timeout_s)
        if count not in (0, 1):
            raise ProtocolError("SPI write returned invalid accepted count")
        return bool(count)

    # 尝试读一帧；空FIFO返回None，帧值0仍是有效数据。
    # 等待单次读取响应；超时不会再次消费FIFO。
    def try_read_frame(self, *, timeout_s: float | None = None) -> int | None:
        count, frame = self._request(SpiCommand.READ_FRAME, timeout_s=timeout_s)
        if count not in (0, 1) or (count == 0 and frame != 0):
            raise ProtocolError("SPI read returned invalid count/empty value")
        return frame if count else None

    # 本次尽可能写入给定帧，遇满即返回；完整输入先校验，避免中途发现非法数据。
    # 所有请求共享总Deadline，超时保留失败而不重放整段数据。
    def write_frames(
        self, frames: Sequence[int], *, timeout_s: float = contract.DEFAULT_TIMEOUT_S
    ) -> int:
        checked = tuple(codec.uint32(frame) for frame in frames)
        deadline = OperationDeadline.start(
            timeout_s, label=f"SPI write instance={self.instance_id}"
        )
        completed = 0
        for frame in checked:
            if not self.try_write_frame(frame, timeout_s=deadline.remaining_s()):
                break
            completed += 1
        return completed

    # 本次最多取max_frames帧，遇空即返回；不等待未来的数据。
    def read_frames(
        self, max_frames: int, *, timeout_s: float = contract.DEFAULT_TIMEOUT_S
    ) -> tuple[int, ...]:
        codec.uint32(max_frames)
        deadline = OperationDeadline.start(timeout_s, label=f"SPI read instance={self.instance_id}")
        frames = []
        for _ in range(max_frames):
            frame = self.try_read_frame(timeout_s=deadline.remaining_s())
            if frame is None:
                break
            frames.append(frame)
        return tuple(frames)

    # 等待指定数量，不启动任何发送；全部读取共享一个Deadline，超时保留已接收数量。
    def read_exact(self, count: int, *, timeout_s: float) -> tuple[int, ...]:
        codec.uint32(count)
        frames = []
        deadline = OperationDeadline.start(
            timeout_s, label=f"SPI read_exact instance={self.instance_id}"
        )
        try:
            while len(frames) < count:
                frame = self.try_read_frame(timeout_s=deadline.remaining_s())
                if frame is None:
                    deadline.sleep(contract.POLL_INTERVAL_S)
                else:
                    frames.append(frame)
        except RequestTimeout as error:
            raise RequestTimeout(
                f"SPI instance={self.instance_id} received={len(frames)}/{count}, frames={frames!r}"
            ) from error
        return tuple(frames)

    # 强制一次FIFO写入，仅用于满FIFO错误刺激，正常数据路径不得替换成此动作。
    def test_fifo_write_once(self, frame: int, *, timeout_s: float | None = None) -> None:
        self._request(SpiCommand.TEST_FIFO_WRITE_ONCE, (frame,), timeout_s=timeout_s)

    # 强制一次FIFO读取，可产生空读错误；只等待响应且不重试。
    def test_fifo_read_once(self, *, timeout_s: float | None = None) -> int:
        return self._request(SpiCommand.TEST_FIFO_READ_ONCE, timeout_s=timeout_s)[0]

    # 只配置本SPI的DMA请求，通道和缓冲区由Case调用独立DMA/Resource Driver。
    # 等待设置响应，不等待DMA搬运完成。
    def dma_configure(
        self,
        tx_enabled: bool,
        rx_enabled: bool,
        tx_threshold: int,
        rx_threshold: int,
        *,
        timeout_s: float | None = None,
    ) -> None:
        self._request(
            SpiCommand.DMA_CONFIGURE,
            (codec.boolean(tx_enabled), codec.boolean(rx_enabled), tx_threshold, rx_threshold),
            timeout_s=timeout_s,
        )

    # 查询数据端点供已解析的DMA映射核对；不直接访问返回的地址。
    # 等待查询响应，地址宽度由两个固定u32字段完整保留。
    def dma_endpoint_get(self, *, timeout_s: float | None = None) -> int:
        low, high = self._request(SpiCommand.DMA_ENDPOINT_GET, timeout_s=timeout_s)
        return low | high << 32

    # 只改变SPI源屏蔽，不建立NVIC路由；允许Raw/Mask的独立验证。
    # 等待屏蔽命令响应，不等待中断发生或消失。
    def irq_mask_set(
        self, sources: SpiIrq, enabled: bool, *, timeout_s: float | None = None
    ) -> None:
        self._request(
            SpiCommand.IRQ_MASK_SET,
            (self._source_mask(sources), codec.boolean(enabled)),
            timeout_s=timeout_s,
        )

    # 清锁存源；仍有效的FIFO电平不能靠此命令消除。
    # 只等待清除命令响应，不通过重试掩盖持续的中断条件。
    def irq_clear(self, sources: SpiIrq, *, timeout_s: float | None = None) -> None:
        self._request(SpiCommand.IRQ_CLEAR, (self._source_mask(sources),), timeout_s=timeout_s)

    # 创建新ISR证据代次并绑定投递；sources声明预期来源，不改变SPI源屏蔽、不清锁存状态。
    # Case通过irq_mask_set和irq_clear显式控制硬件；绑定时已有效的源可以立即投递。
    # 等待绑定响应；失败保留目标错误，不擅自启动第二个会话。
    def irq_capture_start(self, sources: SpiIrq, *, timeout_s: float | None = None) -> None:
        mask = self._source_mask(sources)
        if not mask:
            raise ValueError("SPI capture requires a nonzero source mask")
        self._request(SpiCommand.IRQ_CAPTURE_START, (mask,), timeout_s=timeout_s)

    # 按关SPI源、解绑路由的顺序停止；失败上抛，原事件继续保留。
    def irq_capture_stop(self, *, timeout_s: float | None = None) -> None:
        self._request(SpiCommand.IRQ_CAPTURE_STOP, timeout_s=timeout_s)

    # 原子读取ISR软件快照；不消费FIFO、SR或IRQ源。
    # 只等待当前快照响应，不等事件计数增加。
    def irq_event_get(self, *, timeout_s: float | None = None) -> SpiIrqEvent:
        return codec.decode_event(self._request(SpiCommand.IRQ_EVENT_GET, timeout_s=timeout_s))

    # 未绑定时清零软件证据并增加代次；不清硬件状态，绑定期间由固件明确返回BUSY。
    # 等待重置响应；失败不自动解绑正在运行的捕获。
    def irq_event_reset(self, *, timeout_s: float | None = None) -> None:
        self._request(SpiCommand.IRQ_EVENT_RESET, timeout_s=timeout_s)

    # 在同一Deadline内等至少一条事件；故障与超时分别报告，保留最后快照。
    def irq_wait(self, *, timeout_s: float) -> SpiIrqEvent:
        deadline = OperationDeadline.start(timeout_s, label=f"SPI IRQ instance={self.instance_id}")
        last = None
        try:
            while True:
                last = self.irq_event_get(timeout_s=deadline.remaining_s())
                if last.fault_flags:
                    raise SpiCaptureError(self.instance_id, last)
                if last.event_count:
                    return last
                deadline.sleep(contract.POLL_INTERVAL_S)
        except RequestTimeout as error:
            raise RequestTimeout(
                f"SPI instance={self.instance_id} IRQ timeout, last={last!r}"
            ) from error

    # Source只能来自公共枚举且不得包含未知位。
    @staticmethod
    def _source_mask(sources: SpiIrq) -> int:
        if not isinstance(sources, SpiIrq) or int(sources) & ~int(SpiIrq.ALL):
            raise ValueError("SPI requires known SpiIrq sources")
        return int(sources)

    # 所有响应都严格按命令长度解码；仅无副作用查询允许既有安全重试。
    def _request(
        self, command: SpiCommand, words: tuple[int, ...] = (), *, timeout_s: float | None = None
    ) -> tuple[int, ...]:
        message, _ = self._target.request(
            contract.SPI_SERVICE_ID,
            int(command),
            instance_id=self.instance_id,
            body=codec.encode_request(command, self.instance_id, words),
            timeout_s=timeout_s,
            retry_safe=command
            in (
                SpiCommand.LIMITS_GET,
                SpiCommand.FIFO_LIMITS_GET,
                SpiCommand.CONFIG_GET,
                SpiCommand.SNAPSHOT_GET,
                SpiCommand.DMA_ENDPOINT_GET,
                SpiCommand.IRQ_EVENT_GET,
            ),
        )
        return codec.decode_response(command, message.body)
