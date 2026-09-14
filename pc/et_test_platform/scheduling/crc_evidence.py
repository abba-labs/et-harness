# CRC 计算结果的运行层记录适配。
# 职责：保存 Driver 已返回的事实及复位完成状态，不执行额外设备动作。
# 边界：不提供测试向量、不计算 Expected、不判断 PASS/FAIL。
# 依赖：CRC Driver、不可变结果类型和现有 Observation 接口。
from __future__ import annotations

from collections.abc import Callable

from ..clients.target import TargetClient
from ..drivers.crc.driver import CrcDriver
from ..drivers.crc.models import CrcCalculateResult
from .run_context import record_observation


class RecordedCrcDriver(CrcDriver):
    """Record one stable reference calculation; not an IRQ/timing observer."""

    def __init__(
        self, target: TargetClient, instance_id: int, record: Callable[[str, object], None]
    ) -> None:
        super().__init__(target, instance_id)
        self._record = record
        self.calculation: CrcCalculateResult | None = None
        self.readback: int | None = None
        self.reset_attempted = False
        self.reset_completed = False

    # 只记录调用结果；复位动作全部复用公开 Driver，不补发或重试。
    def reset(self) -> None:
        self.reset_attempted = True
        self.reset_completed = False
        super().reset()
        self.reset_completed = True

    def calculate(
        self, source_address: int, length_bytes: int, *, timeout_s: float | None = None
    ) -> CrcCalculateResult:
        actual = super().calculate(source_address, length_bytes, timeout_s=timeout_s)
        self.calculation = actual
        record_observation(
            self._record, key="actual_crc", value=actual.result,
            source="dut", endpoint="RESULT.CRC",
        )
        record_observation(
            self._record, key="remaining_input_count", value=actual.remaining_input_count,
            source="dut", endpoint="LENGTH.REMAINING_INPUT_COUNT",
        )
        return actual

    def result_get(self) -> int:
        actual = super().result_get()
        self.readback = actual
        record_observation(
            self._record, key="result_readback", value=actual,
            source="dut", endpoint="RESULT.CRC",
        )
        return actual
