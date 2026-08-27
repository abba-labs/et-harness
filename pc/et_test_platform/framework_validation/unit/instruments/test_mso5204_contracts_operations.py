# RIGOL MSO5204 参数契约与 Operations 易用层无硬件测试。
#
# 职责：验证 Programming Guide 核心离散/范围契约、Typed Operations 组合顺序和常用测量结果。
# 边界：只证明软件命令契约，不模拟真实示波器采集、触发、测量精度或 HIL 行为。
# 依赖：仅依赖 MSO5204 公共 API、公共 ScpiSession 和测试内 ScriptedTransport。

from __future__ import annotations

from collections import deque

import pytest

from et_test_platform.communication.transport import ByteTransport
from et_test_platform.instruments.common.scpi import ScpiSession
from et_test_platform.instruments.oscilloscopes.mso5204 import (
    Mso5204AcquireType,
    Mso5204AnalogChannel,
    Mso5204BandwidthLimit,
    Mso5204ChannelCoupling,
    Mso5204ChannelUnit,
    Mso5204Driver,
    Mso5204EdgeCaptureConfig,
    Mso5204MemoryDepth,
    Mso5204TriggerSlope,
    Mso5204TriggerSweep,
    Mso5204WaveformReadConfig,
)


# 提供本组契约测试所需的脚本化字节 Transport；不模拟真实示波器状态机。
class ScriptedTransport(ByteTransport):
    def __init__(self, responses: dict[bytes, bytes] | None = None) -> None:
        self.responses = responses or {}
        self.writes: list[bytes] = []
        self._pending = deque[bytes]()

    @property
    def identity(self) -> str:
        return "scripted:mso5204-contracts"

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    def write(self, data: bytes, *, timeout_s: float | None = None) -> None:
        self.writes.append(data)
        response = self.responses.get(data)
        if response is not None:
            self._pending.append(response)

    def read(self, max_bytes: int, timeout_s: float | None = None) -> bytes:
        if not self._pending:
            return b""
        current = self._pending.popleft()
        if len(current) <= max_bytes:
            return current
        self._pending.appendleft(current[max_bytes:])
        return current[:max_bytes]


def _driver(
    responses: dict[bytes, bytes] | None = None,
) -> tuple[Mso5204Driver, ScriptedTransport]:
    transport = ScriptedTransport(responses)
    return Mso5204Driver(ScpiSession(transport)), transport


# 验证采集、通道、时基和触发核心手册参数会在写入前完成离散值/静态范围校验。
def test_core_manual_parameter_contracts_reject_invalid_values_before_write() -> None:
    driver, transport = _driver()

    with pytest.raises(ValueError):
        driver.acquire.averages_set(3)
    with pytest.raises(ValueError):
        driver.acquire.memory_depth_set("2M")
    with pytest.raises(ValueError):
        driver.channel.probe_ratio_set(1, 3.0)
    with pytest.raises(ValueError):
        driver.channel.units_set(1, "dBm")
    with pytest.raises(ValueError):
        driver.channel.position_set(1, 100.1)
    with pytest.raises(ValueError):
        driver.channel.time_calibration_set(1, 101e-9)
    with pytest.raises(ValueError):
        driver.timebase.main_scale_set(1e-9)
    with pytest.raises(ValueError):
        driver.timebase.reference_mode_set("LEFT")
    with pytest.raises(ValueError):
        driver.trigger.holdoff_set(7e-9)
    with pytest.raises(ValueError):
        driver.trigger.edge_source_set("EXT")
    with pytest.raises(ValueError):
        driver.measurement.threshold_source_set("D0")
    with pytest.raises(ValueError):
        driver.measurement.threshold_max_set(101)
    with pytest.raises(ValueError):
        driver.measurement.item_get("NOT_A_MEASUREMENT", "CHANnel1")

    assert transport.writes == []


# 验证合法参数会归一为手册规范 SCPI 形式，同时兼容常用短形式和整数存储深度输入。
def test_core_manual_parameter_contracts_normalize_valid_values() -> None:
    driver, transport = _driver()

    driver.acquire.averages_set(65536)
    driver.acquire.memory_depth_set(Mso5204MemoryDepth.PTS_25M)
    driver.acquire.memory_depth_set(100_000_000)
    driver.channel.probe_ratio_set(2, 10)
    driver.channel.units_set(2, Mso5204ChannelUnit.VOLTAGE)
    driver.trigger.edge_source_set("CHAN2")
    driver.measurement.item_enable("FREQ", "CHAN2")

    assert transport.writes == [
        b":ACQuire:AVERages 65536\n",
        b":ACQuire:MDEPth 25M\n",
        b":ACQuire:MDEPth 100M\n",
        b":CHANnel2:PROBe 10\n",
        b":CHANnel2:UNITs VOLTage\n",
        b":TRIGger:EDGE:SOURce CHANnel2\n",
        b":MEASure:ITEM FREQuency,CHANnel2\n",
    ]


# 验证完整 EDGE Config 只组合调用显式原子 API，并按可读顺序发送配置命令。
def test_typed_edge_capture_operation_applies_explicit_configuration() -> None:
    driver, transport = _driver()

    driver.operations.configure_edge_capture(
        Mso5204EdgeCaptureConfig(
            channel=Mso5204AnalogChannel.CH2,
            vertical_scale_v=0.5,
            time_scale_s=1e-6,
            trigger_level_v=0.8,
            trigger_slope=Mso5204TriggerSlope.FALLING,
            coupling=Mso5204ChannelCoupling.AC,
            probe_ratio=10,
            bandwidth_limit=Mso5204BandwidthLimit.MHZ_100,
            vertical_offset_v=0.1,
            time_offset_s=2e-6,
            acquire_type=Mso5204AcquireType.AVERAGE,
            average_count=128,
            trigger_sweep=Mso5204TriggerSweep.NORMAL,
        )
    )

    assert transport.writes == [
        b":CHANnel2:DISPlay ON\n",
        b":CHANnel2:PROBe 10\n",
        b":CHANnel2:COUPling AC\n",
        b":CHANnel2:BWLimit 100M\n",
        b":CHANnel2:SCALe 0.5\n",
        b":CHANnel2:OFFSet 0.1\n",
        b":TIMebase:MODE MAIN\n",
        b":TIMebase:MAIN:SCALe 1e-06\n",
        b":TIMebase:MAIN:OFFSet 2e-06\n",
        b":ACQuire:TYPE AVERages\n",
        b":ACQuire:AVERages 128\n",
        b":TRIGger:MODE EDGE\n",
        b":TRIGger:EDGE:SOURce CHANnel2\n",
        b":TRIGger:EDGE:SLOPe NEGative\n",
        b":TRIGger:EDGE:LEVel 0.8\n",
        b":TRIGger:SWEep NORMal\n",
    ]


# 验证 Operations 在任何写入前检查组合契约，避免平均模式和触发电平的明显错误配置落到仪器。
def test_typed_edge_capture_operation_rejects_invalid_combinations_before_write() -> None:
    driver, transport = _driver()

    with pytest.raises(ValueError):
        driver.operations.configure_edge_capture(
            Mso5204EdgeCaptureConfig(
                channel=1,
                vertical_scale_v=0.5,
                time_scale_s=1e-6,
                trigger_level_v=3.0,
            )
        )
    with pytest.raises(ValueError):
        driver.operations.configure_edge_capture(
            Mso5204EdgeCaptureConfig(
                channel=1,
                vertical_scale_v=0.5,
                time_scale_s=1e-6,
                trigger_level_v=0.5,
                acquire_type=Mso5204AcquireType.NORMAL,
                average_count=16,
            )
        )

    assert transport.writes == []


# 验证常用测量快照返回稳定强类型字段，调用方无需重复拼写七个 MEASure:ITEM 参数名。
def test_signal_measurement_operation_returns_typed_snapshot() -> None:
    responses = {
        b":MEASure:ITEM? FREQuency,CHANnel1\n": b"1.000000E+6\n",
        b":MEASure:ITEM? PERiod,CHANnel1\n": b"1.000000E-6\n",
        b":MEASure:ITEM? PDUTy,CHANnel1\n": b"5.000000E+1\n",
        b":MEASure:ITEM? VPP,CHANnel1\n": b"3.300000E+0\n",
        b":MEASure:ITEM? VRMS,CHANnel1\n": b"1.650000E+0\n",
        b":MEASure:ITEM? RTIMe,CHANnel1\n": b"2.000000E-9\n",
        b":MEASure:ITEM? FTIMe,CHANnel1\n": b"3.000000E-9\n",
    }
    driver, transport = _driver(responses)

    result = driver.operations.measure_signal(1)

    assert result.frequency_hz == pytest.approx(1e6)
    assert result.period_s == pytest.approx(1e-6)
    assert result.duty_cycle_percent == pytest.approx(50.0)
    assert result.vpp_v == pytest.approx(3.3)
    assert result.vrms_v == pytest.approx(1.65)
    assert result.rise_time_s == pytest.approx(2e-9)
    assert result.fall_time_s == pytest.approx(3e-9)
    assert len(transport.writes) == 7


# 验证屏幕波形 Operation 固定 NORMal 1..1000 点契约，超出范围时不会写入示波器。
def test_screen_waveform_operation_enforces_normal_mode_point_contract() -> None:
    driver, transport = _driver()

    with pytest.raises(ValueError):
        driver.operations.read_screen_waveform(Mso5204WaveformReadConfig(channel=1, stop=1001))
    with pytest.raises(ValueError):
        driver.operations.read_screen_waveform(
            Mso5204WaveformReadConfig(channel=1, start=500, stop=499)
        )

    assert transport.writes == []


# 验证 Driver 构造时只建立原子 Control 和 Operations 命名空间，不发生任何隐式硬件访问。
def test_driver_construction_exposes_operations_without_io() -> None:
    driver, transport = _driver()

    assert driver.operations is not None
    assert transport.writes == []
