# IPCM 单 IP 原子动作 Driver。
# 职责：发送语义命令、严格解码并有界等待 Service 事件。
# 边界：不调用 CRG/其他 IP，不实现消息应答流程或最终 Case 断言。
# 依赖：本 IP Codec/Model、TargetClient、公共 Deadline 和异常。

from time import monotonic

from ...clients.target import TargetClient
from ...core.deadline import OperationDeadline, require_positive_seconds
from ...core.errors import EtPlatformError, ProtocolError, RequestTimeout
from . import codec
from .contract import IPCM_SERVICE_ID, IpcmCommand
from .models import (
    IpcmCapabilities,
    IpcmCaptureEvent,
    IpcmCaptureState,
    IpcmConfig,
    IpcmEventStage,
    IpcmMailboxSnapshot,
    IpcmPendingSnapshot,
)


# 采样执行失败保留完整现场，不能被调用方误认为“没有中断”。
class IpcmCaptureError(EtPlatformError):
    # 保存原始 Service 事件，供 Case 在失败前后记录同一组证据。
    def __init__(self, instance_id: int, slot: int, event: IpcmCaptureEvent) -> None:

        self.event = event
        super().__init__(
            f"IPCM instance={instance_id} slot={slot} capture fault=0x{event.fault_flags:08x} "
            f"raw=0x{event.raw_status:08x} masked=0x{event.masked_status:08x}"
        )


# 公开方法只代表一个本 IP 动作，不隐式复位、ACK、清除或配 Peer。
class IpcmDriver:
    _READ_ONLY = frozenset(
        {
            IpcmCommand.CAPABILITIES_GET,
            IpcmCommand.MAILBOX_SNAPSHOT_GET,
            IpcmCommand.PENDING_SNAPSHOT_GET,
            IpcmCommand.PAYLOAD_READ,
            IpcmCommand.CAPTURE_GET,
        }
    )
    _POLL_INTERVAL_S = 0.001

    # 绑定已有通信连接及逻辑实例，不执行任何硬件操作。
    def __init__(self, target: TargetClient, instance_id: int) -> None:

        self._target = target
        self.instance_id = codec.checked_u16(instance_id, "instance_id")

    # 读取实际硬件容量与独立的软件采样预算；不推断芯片型号。
    # 仅等待本次查询响应；超时、版本不符或容量字段矛盾均上抛。
    def capabilities_get(self, *, timeout_s: float | None = None) -> IpcmCapabilities:

        return codec.decode_capabilities(
            self._request(IpcmCommand.CAPABILITIES_GET, timeout_s=timeout_s)
        )

    # 配置 Mailbox 或连续链；只接受公共路由与 ACK/Link 模式。
    # 等待配置命令响应，不等待消息；非法路由、忙状态或请求超时由异常返回。
    def configure(self, config: IpcmConfig, *, timeout_s: float | None = None) -> None:

        self._action(IpcmCommand.CONFIGURE, codec.encode_config(config), timeout_s=timeout_s)

    # 释放指定范围；硬件是否清空配置由独立 snapshot_get 观测，不在这里假定。
    # 仅等待释放命令响应，失败上抛；不隐式等待或重试传输。
    def mailbox_release(
        self, first_mailbox: int, mailbox_count: int, *, timeout_s: float | None = None
    ) -> None:

        self._action(
            IpcmCommand.MAILBOX_RELEASE,
            codec.encode_pair(first_mailbox, mailbox_count),
            timeout_s=timeout_s,
        )

    # 读取真实路由及模式；返回值不使用缓存的 configure 参数。
    # 等待一次查询响应，超时或非法响应上抛，不使用旧快照兜底。
    def mailbox_snapshot_get(
        self, mailbox: int, *, timeout_s: float | None = None
    ) -> IpcmMailboxSnapshot:

        return codec.decode_mailbox(
            self._request(
                IpcmCommand.MAILBOX_SNAPSHOT_GET, codec.encode_id(mailbox), timeout_s=timeout_s
            )
        )

    # 读取完整即时 Pending 集合；不代替 CAPTURE_GET 的历史事件。
    # 只等待一次查询，通信失败上抛；返回零仅表示此次有效采样没有 Pending。
    def pending_snapshot_get(
        self, endpoint: int, *, timeout_s: float | None = None
    ) -> IpcmPendingSnapshot:

        return codec.decode_pending(
            self._request(
                IpcmCommand.PENDING_SNAPSHOT_GET, codec.encode_id(endpoint), timeout_s=timeout_s
            )
        )

    # 精确写入有效 Payload；SEND 必须由 Case 另行调用。
    # 等待写入命令响应，不等待接收方；长度错误或超时上抛，不自动重写。
    def payload_write(
        self,
        first_mailbox: int,
        mailbox_count: int,
        payload: bytes,
        *,
        timeout_s: float | None = None,
    ) -> None:

        self._action(
            IpcmCommand.PAYLOAD_WRITE,
            codec.encode_payload(first_mailbox, mailbox_count, payload),
            timeout_s=timeout_s,
        )

    # 读取指定有效字节；不因读取而 ACK、释放或补齐尾部。
    # 等待一次读取，超时或字节数不匹配上抛，不返回截断数据。
    def payload_read(self, mailbox: int, length: int, *, timeout_s: float | None = None) -> bytes:

        body = self._request(
            IpcmCommand.PAYLOAD_READ, codec.encode_pair(mailbox, length), timeout_s=timeout_s
        )
        if len(body) != length:
            raise ProtocolError(
                f"IPCM PAYLOAD_READ mailbox={mailbox}: expected {length} bytes, got {len(body)}"
            )
        return body

    # 启动已经准备好的消息；不等待 ACK，不自动重发非幂等动作。
    def message_send(self, mailbox: int, *, timeout_s: float | None = None) -> None:

        self._action(IpcmCommand.MESSAGE_SEND, codec.encode_id(mailbox), timeout_s=timeout_s)

    # 显式 ACK，不隐式改模式或改写 Payload。
    # 只等待命令响应，不等待来源端 IRQ；请求失败上抛，不自动重复 ACK。
    def ack_send(self, mailbox: int, *, timeout_s: float | None = None) -> None:

        self._action(IpcmCommand.ACK_SEND, codec.encode_id(mailbox), timeout_s=timeout_s)

    # 只清当前消息/ACK Pending，不执行 Destination 释放。
    # 只等待清除命令响应，失败上抛；是否清除成功由独立快照判定。
    def interrupt_clear(self, mailbox: int, *, timeout_s: float | None = None) -> None:

        self._action(IpcmCommand.INTERRUPT_CLEAR, codec.encode_id(mailbox), timeout_s=timeout_s)

    # 只释放一个逻辑 Destination，AUTO ACK 后果由硬件快照验证。
    # 等待释放命令响应，不等待 ACK；超时上抛，不自动重复释放。
    def destination_release(
        self, mailbox: int, endpoint: int, *, timeout_s: float | None = None
    ) -> None:

        self._action(
            IpcmCommand.DESTINATION_RELEASE,
            codec.encode_pair(mailbox, endpoint),
            timeout_s=timeout_s,
        )

    # 启动一次采样；IRQ/Polling、有效长度和消息/ACK阶段都由 Case 明确选择。
    # 只等待武装响应，不等待事件；占用冲突、非法配置或请求失败均上抛。
    def capture_arm(
        self,
        slot: int,
        endpoint: int,
        mailbox: int,
        length: int,
        *,
        irq: bool,
        stage: IpcmEventStage,
        timeout_s: float | None = None,
    ) -> None:

        self._action(
            IpcmCommand.CAPTURE_ARM,
            codec.encode_capture_arm(slot, endpoint, mailbox, length, irq=irq, stage=stage),
            timeout_s=timeout_s,
        )

    # 取得保留事件，包括 WAITING/FAULT；不重读已清除的硬件现场。
    # 等待一次查询响应；通信或格式失败上抛，采样故障保留在返回事件内。
    def capture_get(self, slot: int, *, timeout_s: float | None = None) -> IpcmCaptureEvent:

        return codec.decode_event(
            self._request(IpcmCommand.CAPTURE_GET, codec.encode_id(slot), timeout_s=timeout_s)
        )

    # 等待 READY；请求超时与捕获故障均上抛，保留最后可见状态，禁止当作无中断通过。
    def capture_wait(self, slot: int, *, timeout_s: float) -> IpcmCaptureEvent:

        deadline = OperationDeadline.start(
            timeout_s, label=f"IPCM instance={self.instance_id} slot={slot}"
        )
        last: IpcmCaptureEvent | None = None
        try:
            while True:
                last = self.capture_get(slot, timeout_s=deadline.remaining_s())
                if last.state is IpcmCaptureState.FAULT or last.fault_flags:
                    raise IpcmCaptureError(self.instance_id, slot, last)
                if last.state is IpcmCaptureState.READY:
                    return last
                if last.state is IpcmCaptureState.IDLE:
                    raise ProtocolError(f"IPCM slot={slot} was not armed")
                deadline.sleep(self._POLL_INTERVAL_S)
        except RequestTimeout as error:
            raise RequestTimeout(
                f"IPCM instance={self.instance_id} slot={slot} wait timed out; "
                f"state={last.state.name if last else 'UNOBSERVED'} "
                f"raw={hex(last.raw_status) if last else 'UNOBSERVED'}"
            ) from error

    # 观测完整负向时间窗；通讯失败仍然上抛，只有有效响应组成的时间窗才允许返回。
    def capture_observe(self, slot: int, *, window_s: float, timeout_s: float) -> IpcmCaptureEvent:

        deadline = OperationDeadline.start(timeout_s, label=f"IPCM observation slot={slot}")
        window = require_positive_seconds(window_s, "window_s")
        if window >= timeout_s:
            raise ValueError("IPCM observation deadline must leave time for the final query")
        end = monotonic() + window
        while True:
            # 必须在时间窗结束后再发起一次有效查询，不能返回窗结束前的旧快照。
            window_complete = monotonic() >= end
            last = self.capture_get(slot, timeout_s=deadline.remaining_s())
            if last.state is IpcmCaptureState.FAULT or last.fault_flags:
                raise IpcmCaptureError(self.instance_id, slot, last)
            if last.state is IpcmCaptureState.READY:
                return last
            if last.state is IpcmCaptureState.IDLE:
                raise ProtocolError(f"IPCM slot={slot} was not armed")
            if window_complete:
                return last
            deadline.sleep(self._POLL_INTERVAL_S)

    # 终止一个采样会话，保留 Mailbox 及原始 Pending 供后续显式操作。
    # 等待终止命令响应；解除绑定或请求失败上抛，不当作已终止。
    def capture_abort(self, slot: int, *, timeout_s: float | None = None) -> None:

        self._action(IpcmCommand.CAPTURE_ABORT, codec.encode_id(slot), timeout_s=timeout_s)

    # 停止本核 Service 的所有采样并清软件状态；不是 CRG 或资源池复位。
    # 等待复位命令响应，失败上抛；不代替 Case 对 IPCM 硬件执行复位。
    def state_reset(self, *, timeout_s: float | None = None) -> None:

        self._action(IpcmCommand.STATE_RESET, timeout_s=timeout_s)

    # 控制动作要求空响应，不接受旧固件或错误命令的多余返回数据。
    def _action(
        self, command: IpcmCommand, body: bytes = b"", *, timeout_s: float | None = None
    ) -> None:

        codec.require_empty(self._request(command, body, timeout_s=timeout_s))

    # 复用 Target 的事务关联和错误校验；仅无副作用读取允许安全重试。
    def _request(
        self, command: IpcmCommand, body: bytes = b"", *, timeout_s: float | None = None
    ) -> bytes:

        message, _ = self._target.request(
            IPCM_SERVICE_ID,
            int(command),
            instance_id=self.instance_id,
            body=body,
            timeout_s=timeout_s,
            retry_safe=command in self._READ_ONLY,
        )
        return message.body
