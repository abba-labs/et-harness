# Framework Validation 测试模块。
# 职责：验证 DMA 目标计时命令的 PC Driver Wire 和 Deadline 轮询合同。
# 边界：不访问真实 DMA 硬件，不判断 CRC 性能通过条件。
# 依赖：仅依赖测试替身以及 DMA Driver 和 Wire Model。
from __future__ import annotations

import struct

from et_test_platform.communication.protocols.et_message import ServiceMessage
from et_test_platform.drivers.dma import DMA_SERVICE_ID, DmaCommand, DmaDriver


class _Target:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int, int, bytes, bool]] = []
        self.snapshots = iter(
            (
                b"\x00\x03\x00\x00\x00\x00\x00\x00",
                struct.pack("<BB2xI", 1, 3, 456),
            )
        )

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
        response = next(self.snapshots) if command_id == DmaCommand.TIMING_SNAPSHOT_GET else b""
        return (
            ServiceMessage(
                service_id=service_id,
                command_id=command_id,
                instance_id=instance_id,
                body=response,
            ),
            object(),
        )


# DMA Timed Start 必须使用专用命令，并轮询只读 Snapshot 直到目标 Channel 完成。
def test_dma_timing_driver_contract() -> None:

    now = 0.0

    def clock() -> float:
        return now

    def sleep(duration: float) -> None:
        nonlocal now
        now += duration

    target = _Target()
    dma = DmaDriver(  # type: ignore[arg-type]
        target,
        instance_id=1,
        clock=clock,
        sleep=sleep,
    )
    dma.start_timed(3)
    timing = dma.wait_timing_complete(3, timeout_s=0.1, poll_interval_s=0.01)

    assert timing.complete
    assert timing.channel == 3
    assert timing.elapsed_cycles == 456
    assert target.calls == [
        (
            DMA_SERVICE_ID,
            int(DmaCommand.CHANNEL_START_TIMED),
            1,
            b"\x03\x00\x00\x00",
            False,
        ),
        (DMA_SERVICE_ID, int(DmaCommand.TIMING_SNAPSHOT_GET), 1, b"", True),
        (DMA_SERVICE_ID, int(DmaCommand.TIMING_SNAPSHOT_GET), 1, b"", True),
    ]
