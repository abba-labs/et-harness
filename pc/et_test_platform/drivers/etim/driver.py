# ETIM基础原子动作Driver。
# 职责：运行时边界、单次总Deadline与目标错误观测。
# 边界：不编排Case、不隐式启动计数、不建立IRQ投递会话。
# 依赖：本IPCodec/Model、TargetClient及公共Deadline/错误。

from ...clients.target import TargetClient
from ...core.deadline import OperationDeadline, require_positive_seconds
from ...core.errors import TargetRejected
from . import codec, validation
from .contract import ETIM_SERVICE_ID, EtimCommand
from .models import (
    EtimCapabilities,
    EtimCount,
    EtimCountObservation,
    EtimEnable,
    EtimIrq,
    EtimIrqSnapshot,
    EtimOperationError,
    EtimTimebase,
)


# 一个对象选择一个逻辑timer通道；初始化无设备副作用。
class EtimDriver:
    _READ_ONLY = frozenset(
        {
            EtimCommand.CAPABILITIES_GET,
            EtimCommand.TIMEBASE_GET,
            EtimCommand.ENABLE_GET,
            EtimCommand.COUNT_GET,
            EtimCommand.IRQ_SNAPSHOT_GET,
        }
    )

    def __init__(self, target: TargetClient, instance_id: int, *, timeout_s: float = 2.0) -> None:
        self._target = target
        self.instance_id = validation.integer(instance_id, "instance_id", 0, 0xFFFF)
        self._timeout_s = require_positive_seconds(timeout_s, "timeout_s")
        self._capabilities: EtimCapabilities | None = None

    # 强制刷新当前Service的能力；缓存只用于后续参数上限检查。
    # 查询失败不替换已有缓存，异常返回给调用者。
    def capabilities_get(self) -> EtimCapabilities:
        deadline = self._deadline("capabilities_get")
        self._capabilities = codec.decode_capabilities(
            self._request(EtimCommand.CAPABILITIES_GET, b"", deadline)
        )
        return self._capabilities

    # 按运行时上限配置实际分频和完整周期；不改变任何使能状态。
    # 等待配置Ack，失败不自动重发或追加读回动作。
    def timebase_configure(self, config: EtimTimebase) -> None:
        body = codec.encode_timebase(config)
        deadline = self._deadline("timebase_configure")
        caps = self._runtime_capabilities(deadline)
        if config.divider > caps.maximum_divider or config.period_ticks > caps.maximum_period_ticks:
            raise ValueError("ETIM timebase exceeds runtime capability")
        codec.decode_ack(self._request(EtimCommand.TIMEBASE_CONFIGURE, body, deadline))

    # 读取目标真实分频和完整周期，不返回本地配置缓存或推测时钟频率。
    # 只等待本次响应，不等待计数器达到指定相位。
    def timebase_get(self) -> EtimTimebase:
        return codec.decode_timebase(
            self._request(EtimCommand.TIMEBASE_GET, b"", self._deadline("timebase_get"))
        )

    # 仅改变选定控制位；调用者显式提供Boolean状态。
    # 拒绝非Boolean参数，响应成功也不等待计数或输出波形变化。
    def enable_set(self, control: EtimEnable, enabled: bool) -> None:
        if not isinstance(enabled, bool):
            raise ValueError("enabled must be bool")
        codec.decode_ack(
            self._request(
                EtimCommand.ENABLE_SET,
                codec.encode_enable(control, enabled),
                self._deadline("enable_set"),
            )
        )

    # 读取显式选定的单个使能控制位，不推导或修改其他控制状态。
    # 只等待寄存器状态响应，非法Boolean读回作为协议错误上抛。
    def enable_get(self, control: EtimEnable) -> bool:
        return codec.decode_enable(
            self._request(
                EtimCommand.ENABLE_GET, codec.encode_enable(control), self._deadline("enable_get")
            )
        )

    # 获取live与latched独立快照；不发锁存脉冲。
    # 不等待值变化，latched可能属于此前动作。
    def count_get(self) -> EtimCount:
        return codec.decode_count(
            self._request(EtimCommand.COUNT_GET, b"", self._deadline("count_get"))
        )

    # 发出一次锁存动作；忙/超时异常携带目标实际观测，不自动重试。
    def count_latch(self, polls: int) -> EtimCountObservation:
        return self._count_action(EtimCommand.COUNT_LATCH, polls)

    # 发出一次有界清零动作并返回实际观测；不会隐式启用模块或计数器。
    # 忙或超时异常保留末次真实值，不能将未完成动作返回为零。
    def count_clear(self, polls: int) -> EtimCountObservation:
        return self._count_action(EtimCommand.COUNT_CLEAR, polls)

    # 配置源使能与屏蔽，不清状态，不启用NVIC投递。
    # 等待配置Ack，不等待pending消失，也不隐式重试部分配置。
    def irq_configure(self, enabled: EtimIrq, masked: EtimIrq) -> None:
        body = codec.encode_irq_config(enabled, masked)
        deadline = self._deadline("irq_configure")
        self._require_irq(enabled | masked, deadline)
        codec.decode_ack(self._request(EtimCommand.IRQ_CONFIGURE, body, deadline))

    # 获取使能、屏蔽、原始和有效IRQ源四个独立字段，不推算CPU投递次数。
    # 不等待中断源出现，各字段是顺序采样而非原子快照。
    def irq_snapshot_get(self) -> EtimIrqSnapshot:
        return codec.decode_irq_snapshot(
            self._request(EtimCommand.IRQ_SNAPSHOT_GET, b"", self._deadline("irq_snapshot_get"))
        )

    # 强制运行时支持的选定源一次；动作成功不代表IRQ已经送达CPU。
    # 只等待写入Ack，超时不能自动重发同一激励。
    def irq_force(self, sources: EtimIrq) -> None:
        body = codec.encode_irq(sources)
        deadline = self._deadline("irq_force")
        self._require_irq(sources, deadline)
        codec.decode_ack(self._request(EtimCommand.IRQ_FORCE, body, deadline))

    # 直接清除运行时支持的选定源，不改变其他中断配置，不假设清后状态。
    # 等待动作Ack，不等待RAW/STATUS清零；其后状态由调用者显式查询。
    def irq_clear(self, sources: EtimIrq) -> None:
        body = codec.encode_irq(sources)
        deadline = self._deadline("irq_clear")
        self._require_irq(sources, deadline)
        codec.decode_ack(self._request(EtimCommand.IRQ_CLEAR, body, deadline))

    def _deadline(self, operation: str) -> OperationDeadline:
        return OperationDeadline.start(
            self._timeout_s, label=f"ETIM {operation} instance={self.instance_id}"
        )

    def _runtime_capabilities(self, deadline: OperationDeadline) -> EtimCapabilities:
        if self._capabilities is None:
            self._capabilities = codec.decode_capabilities(
                self._request(EtimCommand.CAPABILITIES_GET, b"", deadline)
            )
        return self._capabilities

    def _require_irq(self, sources: EtimIrq, deadline: OperationDeadline) -> None:
        if int(sources) & ~int(self._runtime_capabilities(deadline).irq_sources):
            raise ValueError("ETIM sources exceed runtime capability")

    def _count_action(self, command: EtimCommand, polls: int) -> EtimCountObservation:
        body = codec.encode_polls(polls)
        deadline = self._deadline(command.name.lower())
        if polls > self._runtime_capabilities(deadline).maximum_count_polls:
            raise ValueError("ETIM polls exceed runtime capability")
        return codec.decode_observation(self._request(command, body, deadline))

    def _request(self, command: EtimCommand, body: bytes, deadline: OperationDeadline) -> bytes:
        try:
            message, _ = self._target.request(
                ETIM_SERVICE_ID,
                int(command),
                instance_id=self.instance_id,
                body=body,
                timeout_s=deadline.remaining_s(),
                retry_safe=command in self._READ_ONLY,
            )
        except TargetRejected as error:
            detail, observation = codec.decode_error(command, error.status, error.body)
            raise EtimOperationError(
                command.name.lower(), self.instance_id, error.status, detail, observation
            ) from error
        return message.body
