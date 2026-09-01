# STIMER Contract、Codec和Driver单元测试。
#
# 职责：固定命令、Wire布局、严格Capability解码和原子Driver调用。
# 边界：不访问真实硬件，不替代Formal HIL Case。
# 依赖：仅依赖 pytest、STIMER Driver 和可控 Fake Target。

from __future__ import annotations

import pytest

from et_test_platform.communication.protocols.et_message import ServiceMessage
from et_test_platform.core.errors import ProtocolError
from et_test_platform.drivers.stimer import (
    STIMER_SERVICE_ID,
    StimerCommand,
    StimerConfig,
    StimerDebugHaltPolicy,
    StimerDriver,
    StimerFeature,
    StimerIrqEvent,
    StimerMode,
)
from et_test_platform.drivers.stimer.codec import (
    decode_capabilities,
    encode_config,
    encode_debug_halt_policy,
)
from et_test_platform.drivers.stimer.contract import (
    CAPABILITIES_STRUCT,
    COMPARE_STRUCT,
    CONFIG_STRUCT,
    DEBUG_HALT_POLICY_STRUCT,
    EVENT_PULSE_WIDTH_STRUCT,
    IRQ_SNAPSHOT_STRUCT,
    STIMER_SERVICE_API_VERSION,
    UINT32_STRUCT,
)


class _Target:
    def __init__(self) -> None:

        self.calls: list[tuple[int, int, int, bytes, bool]] = []

    def request(
        self,
        service_id: int,
        command_id: int,
        *,
        instance_id: int = 0,
        body: bytes = b"",
        retry_safe: bool = False,
        timeout_s: float | None = None,
    ):

        del timeout_s
        self.calls.append((service_id, command_id, instance_id, body, retry_safe))
        responses = {
            int(StimerCommand.CAPABILITIES_GET): CAPABILITIES_STRUCT.pack(
                STIMER_SERVICE_API_VERSION,
                CAPABILITIES_STRUCT.size,
                int(sum(StimerFeature)),
                0xFFFFFFFF,
                0xFFFF,
                4,
                2,
                int(StimerIrqEvent.ALL),
            ),
            int(StimerCommand.LIVE_COUNT_GET): UINT32_STRUCT.pack(123),
            int(StimerCommand.LATCHED_COUNT_GET): UINT32_STRUCT.pack(120),
            int(StimerCommand.STATUS_GET): UINT32_STRUCT.pack(0x10),
            int(StimerCommand.IRQ_SNAPSHOT_GET): IRQ_SNAPSHOT_STRUCT.pack(1, 1, 1, 2, 1, 1),
        }
        return (
            ServiceMessage(
                service_id=service_id,
                command_id=command_id,
                instance_id=instance_id,
                body=responses.get(command_id, b""),
            ),
            object(),
        )


# STIMER命令、枚举、掩码和Wire尺寸必须与Firmware合同一致。
def test_stimer_numeric_and_wire_contract() -> None:

    # 断言：命令连续且固定Struct尺寸不漂移。
    assert [int(command) for command in StimerCommand] == list(range(0x0001, 0x001A))
    assert [int(mode) for mode in StimerMode] == [0, 1]
    assert int(StimerIrqEvent.ALL) == 0x1F
    assert CAPABILITIES_STRUCT.size == 20
    assert CONFIG_STRUCT.size == 12
    assert COMPARE_STRUCT.size == 8
    assert EVENT_PULSE_WIDTH_STRUCT.size == 8
    assert DEBUG_HALT_POLICY_STRUCT.size == 4
    assert IRQ_SNAPSHOT_STRUCT.size == 24


# STIMER Capability解码必须拒绝未知Feature和IRQ位。
def test_stimer_capabilities_are_strictly_decoded() -> None:

    # 观察：有效Capability恢复硬件边界和拓扑。
    body = CAPABILITIES_STRUCT.pack(
        STIMER_SERVICE_API_VERSION,
        20,
        int(sum(StimerFeature)),
        0xFFFFFFFF,
        0xFFFF,
        4,
        2,
        0x1F,
    )
    capabilities = decode_capabilities(body)
    assert capabilities.maximum_period_ticks == 0xFFFFFFFF
    assert capabilities.compare_channel_count == 4
    assert capabilities.instance_count == 2

    # 拒绝：未知位和空拓扑不得静默进入Driver。
    with pytest.raises(ProtocolError, match="invalid features or limits"):
        decode_capabilities(
            CAPABILITIES_STRUCT.pack(STIMER_SERVICE_API_VERSION, 20, 1 << 31, 1, 1, 4, 2, 0x1F)
        )
    with pytest.raises(ProtocolError, match="invalid topology or IRQ"):
        decode_capabilities(
            CAPABILITIES_STRUCT.pack(STIMER_SERVICE_API_VERSION, 20, 0, 1, 1, 0, 2, 0x1F)
        )


# STIMER Driver必须按选中实例发送原子命令并严格解码返回。
def test_stimer_driver_atomic_command_flow() -> None:

    target = _Target()
    stimer = StimerDriver(target, instance_id=1)  # type: ignore[arg-type]
    config = StimerConfig(period_ticks=1000)

    # 配置与激励：覆盖配置、生命周期、计数、Compare和IRQ原子动作。
    capabilities = stimer.capabilities_get()
    stimer.configure(config)
    stimer.start()
    live = stimer.live_count_get()
    latched = stimer.latched_count_get()
    stimer.compare_set(3, 800)
    stimer.event_pulse_width_set(StimerIrqEvent.COMPARE3, 256)
    stimer.dma_request_select(StimerIrqEvent.COMPARE3)
    stimer.debug_halt_policy_set(StimerDebugHaltPolicy.PAUSE)
    stimer.irq_enable(StimerIrqEvent.COMPARE3)
    snapshot = stimer.irq_snapshot_get()
    raw_snapshot = stimer.wait_irq_raw(StimerIrqEvent.COMPARE0)
    stimer.stop()

    # 断言：实例不漂移、配置编码稳定，只有读取命令安全重试。
    assert capabilities.instance_count == 2
    assert encode_config(config) == CONFIG_STRUCT.pack(1000, 1, 0, 0)
    assert encode_debug_halt_policy(StimerDebugHaltPolicy.PAUSE) == b"\x00\x00\x00\x00"
    assert live == 123 and latched == 120
    assert snapshot.event_count == 2
    assert raw_snapshot.raw == StimerIrqEvent.COMPARE0
    assert all(call[0] == STIMER_SERVICE_ID and call[2] == 1 for call in target.calls)
    assert target.calls[0][-1] is True
    assert target.calls[1][-1] is False


# STIMER Driver必须在I/O前拒绝越界Period、Divider、Compare和空IRQ。
def test_stimer_driver_rejects_invalid_semantics_before_io() -> None:

    target = _Target()
    stimer = StimerDriver(target, instance_id=0)  # type: ignore[arg-type]
    stimer.capabilities_get()

    # 拒绝：所有非法公共参数均不得到达Firmware。
    with pytest.raises(ValueError, match="period_ticks"):
        stimer.configure(StimerConfig(period_ticks=0))
    with pytest.raises(ValueError, match="prescaler_divider"):
        stimer.configure(StimerConfig(period_ticks=1, prescaler_divider=0))
    with pytest.raises(ValueError, match="compare channel"):
        stimer.compare_set(4, 10)
    with pytest.raises(ValueError, match="non-zero STIMER IRQ"):
        stimer.irq_enable(StimerIrqEvent.NONE)
    with pytest.raises(ValueError, match="exactly one STIMER source"):
        stimer.event_pulse_width_set(
            StimerIrqEvent.COMPARE0 | StimerIrqEvent.COMPARE1,
            16,
        )
    with pytest.raises(ValueError, match="width_cycles"):
        stimer.event_pulse_width_set(StimerIrqEvent.COMPARE0, 257)
    with pytest.raises(ValueError, match="exactly one STIMER source"):
        stimer.dma_request_select(StimerIrqEvent.COMPARE0 | StimerIrqEvent.COMPARE1)


# STIMER Driver必须由Profile显式选择逻辑实例，禁止静默回落到实例0。
def test_stimer_driver_requires_explicit_instance() -> None:

    target = _Target()

    # 拒绝：调用方未提供逻辑实例时，构造阶段直接失败且不得发生I/O。
    with pytest.raises(TypeError):
        StimerDriver(target)  # type: ignore[call-arg,arg-type]

    assert target.calls == []
