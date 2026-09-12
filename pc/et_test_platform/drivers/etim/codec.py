# ETIM纯Wire编解码。
# 职责：严格长度、结果前缀和公共语义检查。
# 边界：不执行I/O、重试、等待或测试断言。
# 依赖：本IP契约、模型、校验及公共ProtocolError。

from ...core.errors import ProtocolError
from . import contract, validation
from .models import (
    EtimCapabilities,
    EtimCount,
    EtimCountObservation,
    EtimEnable,
    EtimIrq,
    EtimIrqSnapshot,
    EtimTimebase,
)


def _success(body: bytes, size: int) -> None:
    if len(body) != size or contract.DETAIL.unpack_from(body)[0] != 0:
        raise ProtocolError(f"ETIM success body invalid: expected {size} bytes and zero detail")


# 完整时基请求不携带通道，逻辑通道由Service instance指定。
def encode_timebase(config: EtimTimebase) -> bytes:
    checked = validation.timebase(config)
    return contract.TIMEBASE.pack(checked.divider, checked.period_ticks)


# 编码独立控制选择及Boolean值；保留位固定零，None只用于GET的无值请求。
def encode_enable(control: EtimEnable, enabled: bool | None = None) -> bytes:
    validation.control(control)
    if enabled is not None and not isinstance(enabled, bool):
        raise ValueError("enabled must be bool")
    return contract.ENABLE.pack(int(control), int(enabled) if enabled is not None else 0)


# 编码显式正整数采样预算，拒绝溢出和Boolean，不引入固件默认轮询数。
def encode_polls(polls: int) -> bytes:
    return contract.WORD.pack(validation.integer(polls, "polls", 1, 0xFFFFFFFF))


# 编码源使能与屏蔽两个独立位集合，允许空集但拒绝公共契约以外的位。
def encode_irq_config(enabled: EtimIrq, masked: EtimIrq) -> bytes:
    return contract.IRQ_CONFIG.pack(int(validation.irq(enabled)), int(validation.irq(masked)))


# 为force/clear编码显式非空源集合，不把未知位截断为受支持的子集。
def encode_irq(sources: EtimIrq) -> bytes:
    return contract.WORD.pack(int(validation.irq(sources, nonempty=True)))


# 解码成功Ack；必须恰好包含零详细状态，拒绝额外数据与非零错误码。
def decode_ack(body: bytes) -> None:
    _success(body, contract.DETAIL.size)


# 解码当前通道能力，版本、布局和非零数值上限必须同时有效。
def decode_capabilities(body: bytes) -> EtimCapabilities:
    _success(body, contract.CAPABILITIES.size)
    _, version, size, divider, period, polls, irq = contract.CAPABILITIES.unpack(body)
    if version != contract.ETIM_API_VERSION or size != contract.CAPABILITIES.size:
        raise ProtocolError("ETIM capabilities version or size mismatch")
    if not divider or not period or not polls or irq & ~int(EtimIrq.ALL):
        raise ProtocolError("ETIM capabilities contain invalid limits or IRQ bits")
    return EtimCapabilities(divider, period, polls, EtimIrq(irq))


# 解码完整64位时基读回，拒绝无效零周期或零分频，不采用本地默认值。
def decode_timebase(body: bytes) -> EtimTimebase:
    _success(body, contract.TIMEBASE_RESPONSE.size)
    _, divider, period = contract.TIMEBASE_RESPONSE.unpack(body)
    if not divider or not period:
        raise ProtocolError("ETIM timebase contains zero divider or period")
    return EtimTimebase(divider, period)


# 使能读回严格为Boolean，不能把任意非零值吞成True。
def decode_enable(body: bytes) -> bool:
    _success(body, contract.ENABLE_RESPONSE.size)
    _, value = contract.ENABLE_RESPONSE.unpack(body)
    if value not in (0, 1):
        raise ProtocolError("ETIM enable value is not Boolean")
    return bool(value)


# 解码并独立保留live与latched采样值，不假设两者来自同一时刻。
def decode_count(body: bytes) -> EtimCount:
    _success(body, contract.COUNT.size)
    _, live, latched = contract.COUNT.unpack(body)
    return EtimCount(live, latched)


# 成功动作返回五个实际采样字段，不在Codec推导成功条件。
def decode_observation(body: bytes) -> EtimCountObservation:
    _success(body, contract.OBSERVATION.size)
    _, before, previous, latched, live, polls = contract.OBSERVATION.unpack(body)
    return EtimCountObservation(before, previous, latched, live, polls)


# 四个IRQ字段独立校验，禁止由raw与mask推算status。
def decode_irq_snapshot(body: bytes) -> EtimIrqSnapshot:
    _success(body, contract.IRQ_SNAPSHOT.size)
    _, enabled, masked, raw, status = contract.IRQ_SNAPSHOT.unpack(body)
    if (enabled | masked | raw | status) & ~int(EtimIrq.ALL):
        raise ProtocolError("ETIM snapshot contains unknown IRQ bits")
    return EtimIrqSnapshot(EtimIrq(enabled), EtimIrq(masked), EtimIrq(raw), EtimIrq(status))


# Framework错误允许无Body；本IP错误必须保持状态映射与观测长度一致。
def decode_error(
    command: contract.EtimCommand,
    status: int,
    body: bytes,
) -> tuple[int | None, EtimCountObservation | None]:
    if not body:
        return None, None
    if len(body) < contract.DETAIL.size:
        raise ProtocolError("ETIM error detail is truncated")
    detail = contract.DETAIL.unpack_from(body)[0]
    expected_status = {-1: 3, -2: 4, -3: 5, -4: 6, -5: 6, -6: 6, -7: 6}
    if detail not in expected_status or expected_status[detail] != status:
        raise ProtocolError("ETIM error detail disagrees with protocol status")
    observed = command in (contract.EtimCommand.COUNT_LATCH, contract.EtimCommand.COUNT_CLEAR)
    if observed and detail in (-3, -6):
        if len(body) != contract.OBSERVATION.size:
            raise ProtocolError("ETIM count error observation is truncated")
        _, before, previous, latched, live, polls = contract.OBSERVATION.unpack(body)
        return detail, EtimCountObservation(before, previous, latched, live, polls)
    if len(body) != contract.DETAIL.size:
        raise ProtocolError("ETIM error body has unexpected data")
    return detail, None
