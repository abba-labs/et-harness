# CPU/NMI Owner Contract、Codec 和 Driver 单元测试。
# 职责：固定命令、Wire 布局、严格能力解码和原子 Driver 调用。
# 边界：不访问真实硬件，不触发 WDG，也不替代跨 Owner Formal Case。
# 依赖：pytest、测试替身和 CPU Driver package。

from __future__ import annotations

import pytest
from et_test_platform.communication.protocols.et_message import ServiceMessage
from et_test_platform.core.errors import ProtocolError
from et_test_platform.drivers.cpu import CPU_SERVICE_ID, CpuCommand, CpuDriver
from et_test_platform.drivers.cpu.codec import decode_capabilities, encode_nmi_configure
from et_test_platform.drivers.cpu.contract import (
    CAPABILITIES_STRUCT,
    CONFIG_STRUCT,
    SNAPSHOT_STRUCT,
)


class _Target:
    def __init__(self, event_counts: tuple[int, ...] = (3,)) -> None:

        self.calls: list[tuple[int, int, int, bytes, bool]] = []
        self._event_counts = list(event_counts)

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

        if command_id == int(CpuCommand.CAPABILITIES_GET):
            response = CAPABILITIES_STRUCT.pack(1, CAPABILITIES_STRUCT.size, 0x03)
        elif command_id == int(CpuCommand.NMI_SNAPSHOT_GET):
            event_count = (
                self._event_counts.pop(0) if len(self._event_counts) > 1 else self._event_counts[0]
            )
            response = SNAPSHOT_STRUCT.pack(0x01, 0x01, 0x03, 0x01, event_count)
        else:
            response = b""

        return (
            ServiceMessage(
                service_id=service_id,
                command_id=command_id,
                instance_id=instance_id,
                body=response,
            ),
            object(),
        )


# CPU Owner 命令与固定 Wire 尺寸必须和 Firmware 公开 Contract 保持一致。
def test_cpu_numeric_and_wire_contract() -> None:

    # 断言：命令连续，所有 Request/Response 都保持冻结的小端固定布局。
    assert [int(command) for command in CpuCommand] == list(range(0x0001, 0x0005))
    assert CAPABILITIES_STRUCT.size == 8
    assert CONFIG_STRUCT.size == 4
    assert SNAPSHOT_STRUCT.size == 20


# CPU Capability 解码必须拒绝错误版本、错误长度、空源和超出公共宽度的源掩码。
def test_cpu_capability_decode_is_strict() -> None:

    # 观察：合法响应只发布稳定的 NMI Source mask。
    capabilities = decode_capabilities(CAPABILITIES_STRUCT.pack(1, 8, 0x03))
    assert capabilities.source_mask == 0x03

    # 拒绝：不兼容版本、空能力和超宽掩码不得进入 Driver 运行时状态。
    with pytest.raises(ProtocolError, match="version or size"):
        decode_capabilities(CAPABILITIES_STRUCT.pack(2, 8, 0x03))
    with pytest.raises(ProtocolError, match="invalid NMI source mask"):
        decode_capabilities(CAPABILITIES_STRUCT.pack(1, 8, 0x00))
    with pytest.raises(ProtocolError, match="invalid NMI source mask"):
        decode_capabilities(CAPABILITIES_STRUCT.pack(1, 8, 0x100))


# CPU Driver 必须按所选实例发送原子命令，并只对只读命令声明安全重试。
def test_cpu_driver_atomic_command_flow() -> None:

    target = _Target()
    cpu = CpuDriver(target, instance_id=1)  # type: ignore[arg-type]

    # 执行：读取能力、配置源、读取快照并清除 Service 事件计数。
    capabilities = cpu.capabilities_get()
    cpu.nmi_configure(0x01)
    snapshot = cpu.nmi_snapshot_get()
    cpu.nmi_event_clear()

    # 断言：实例和 Wire 不漂移，只有能力与快照读取允许安全重试。
    assert capabilities.source_mask == 0x03
    assert snapshot.event_count == 3 and snapshot.nmi_status == 0x01
    assert target.calls[1][3] == encode_nmi_configure(0x01)
    assert all(call[0] == CPU_SERVICE_ID and call[2] == 1 for call in target.calls)
    assert [call[-1] for call in target.calls] == [True, False, True, False]


# CPU Driver 的有界等待必须消费真实 ISR 事件计数，并在 I/O 前拒绝未知源位。
def test_cpu_driver_wait_and_validation() -> None:

    target = _Target(event_counts=(0, 1, 2))
    cpu = CpuDriver(target)  # type: ignore[arg-type]
    cpu.capabilities_get()

    # 执行：轮询到真实事件计数达到目标，不用固定次数冒充完成条件。
    snapshot = cpu.wait_nmi(2, timeout_s=0.1, poll_interval_s=0.0001)
    assert snapshot.event_count == 2

    # 拒绝：Runtime Capability 未发布的源位不得发送给 Firmware。
    before = len(target.calls)
    with pytest.raises(ValueError, match="unsupported source bits"):
        cpu.nmi_configure(0x04)
    assert len(target.calls) == before
