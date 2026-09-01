# WDG Contract、Codec和Driver单元测试。
#
# 职责：固定命令、Wire布局、严格Capability解码和原子Driver调用。
# 边界：不访问真实硬件，不替代Formal HIL Case。
# 依赖：pytest、测试替身和WDG Driver package。

from __future__ import annotations

import pytest

from et_test_platform.communication.protocols.et_message import ServiceMessage
from et_test_platform.core.errors import ProtocolError
from et_test_platform.drivers.wdg import (
    WDG_SERVICE_ID,
    WdgCommand,
    WdgConfig,
    WdgDriver,
    WdgFeature,
    WdgIrqEvent,
    WdgMode,
    WdgRecord,
    WdgWorkMode,
)
from et_test_platform.drivers.wdg.codec import decode_capabilities, encode_config
from et_test_platform.drivers.wdg.contract import (
    CAPABILITIES_STRUCT,
    CONFIG_STRUCT,
    IRQ_SNAPSHOT_STRUCT,
    RECORD_STRUCT,
    STATUS_STRUCT,
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
            int(WdgCommand.CAPABILITIES_GET): CAPABILITIES_STRUCT.pack(
                1,
                CAPABILITIES_STRUCT.size,
                int(sum(WdgFeature)),
                0xFFFFFFFF,
                0xFFFFFFFF,
                0x03,
                0x03,
                int(WdgIrqEvent.ALL),
                2,
            ),
            int(WdgCommand.CONFIG_GET): CONFIG_STRUCT.pack(1000, 0, 0, 1, 0, 0, 1),
            int(WdgCommand.STATUS_GET): STATUS_STRUCT.pack(1, 900),
            int(WdgCommand.IRQ_SNAPSHOT_GET): IRQ_SNAPSHOT_STRUCT.pack(1, 1, 1, 2, 1),
            int(WdgCommand.RECORD_GET): RECORD_STRUCT.pack(0, 1),
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


# WDG命令、枚举和固定Wire尺寸必须与Firmware公开合同一致。
def test_wdg_numeric_and_wire_contract() -> None:

    # 断言：命令连续，公开模式和掩码使用冻结数值。
    assert [int(command) for command in WdgCommand] == list(range(0x0001, 0x0014))
    assert [int(mode) for mode in WdgMode] == [0, 1]
    assert [int(mode) for mode in WdgWorkMode] == [0, 1]
    assert int(WdgIrqEvent.ALL) == 0x01
    assert int(WdgRecord.ALL) == 0x03

    # 断言：PC struct尺寸与Firmware Wire常量保持一致。
    assert CAPABILITIES_STRUCT.size == 20
    assert CONFIG_STRUCT.size == 16
    assert STATUS_STRUCT.size == 8
    assert IRQ_SNAPSHOT_STRUCT.size == 20
    assert RECORD_STRUCT.size == 4


# WDG Capability解码必须拒绝未知Feature、空模式和未知IRQ位。
def test_wdg_capabilities_are_strictly_decoded() -> None:

    # 观察：完整Capability恢复两个模式、两个工作模式和实例数。
    body = CAPABILITIES_STRUCT.pack(1, 20, int(sum(WdgFeature)), 0xFFFFFFFF, 0xFFFFFFFF, 3, 3, 1, 2)
    capabilities = decode_capabilities(body)
    assert capabilities.modes == tuple(WdgMode)
    assert capabilities.work_modes == tuple(WdgWorkMode)
    assert capabilities.instance_count == 2

    # 拒绝：当前Driver不得静默接受未来未知位或空能力。
    with pytest.raises(ProtocolError, match="invalid features or limits"):
        decode_capabilities(CAPABILITIES_STRUCT.pack(1, 20, 1 << 31, 1, 1, 3, 3, 1, 2))
    with pytest.raises(ProtocolError, match="invalid mode bits"):
        decode_capabilities(CAPABILITIES_STRUCT.pack(1, 20, 0, 1, 1, 0, 3, 1, 2))
    with pytest.raises(ProtocolError, match="invalid IRQ or instance"):
        decode_capabilities(CAPABILITIES_STRUCT.pack(1, 20, 0, 1, 1, 3, 3, 2, 2))


# WDG Driver必须按选中实例发送原子命令并严格解码硬件返回。
def test_wdg_driver_atomic_command_flow() -> None:

    target = _Target()
    wdg = WdgDriver(target, instance_id=1)  # type: ignore[arg-type]
    config = WdgConfig(reload_count=1000)

    # 配置：先取得Runtime Capability，再执行各类原子动作。
    capabilities = wdg.capabilities_get()
    wdg.unlock()
    wdg.configure(config)
    readback = wdg.config_get()
    wdg.enable()
    status = wdg.status_get()
    wdg.feed()
    wdg.irq_enable()
    snapshot = wdg.irq_snapshot_get()
    records = wdg.record_get()

    # 断言：实例不漂移，配置编码稳定，只有只读命令允许安全重试。
    assert capabilities.instance_count == 2
    assert encode_config(config) == CONFIG_STRUCT.pack(1000, 0, 0, 1, 0, 0, 1)
    assert readback.reload_count == 1000
    assert status.enabled is True and status.counter == 900
    assert snapshot.event_count == 2 and snapshot.last_raw == WdgIrqEvent.TIMEOUT
    assert records.interrupt is True
    assert all(call[0] == WDG_SERVICE_ID and call[2] == 1 for call in target.calls)
    assert target.calls[0][-1] is True
    assert target.calls[1][-1] is False


# WDG Driver必须在I/O前拒绝非法配置、空事件和空记录掩码。
def test_wdg_driver_rejects_invalid_semantics_before_io() -> None:

    target = _Target()
    wdg = WdgDriver(target, instance_id=0)  # type: ignore[arg-type]
    wdg.capabilities_get()

    # 拒绝：零Reload、失真的窗口关系和空掩码均不得到达Firmware。
    with pytest.raises(ValueError, match="non-zero"):
        wdg.configure(WdgConfig(reload_count=0))
    with pytest.raises(ValueError, match="low <= high"):
        wdg.configure(WdgConfig(reload_count=100, window_low_count=80, window_high_count=50))
    with pytest.raises(ValueError, match="non-zero WDG IRQ"):
        wdg.irq_enable(WdgIrqEvent.NONE)
    with pytest.raises(ValueError, match="non-zero WDG record"):
        wdg.record_clear(WdgRecord.NONE)


# WDG Driver必须由Profile显式选择逻辑实例，禁止静默回落到实例0。
def test_wdg_driver_requires_explicit_instance() -> None:

    target = _Target()

    # 拒绝：调用方未提供逻辑实例时，构造阶段直接失败且不得发生I/O。
    with pytest.raises(TypeError):
        WdgDriver(target)  # type: ignore[call-arg,arg-type]

    assert target.calls == []
