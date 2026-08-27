# RIGOL MSO5204 无硬件协议单元测试。
#
# 职责：验证核心原子 API 的 SCPI 映射、二进制块、波形换算、参数校验和当前 API Inventory。
# 边界：只验证软件命令契约，不模拟或证明真实 MSO5204 采集、触发或测量硬件行为。
# 依赖：仅依赖 MSO5204 Driver、公共 ScpiSession 和测试内 ScriptedTransport。

from __future__ import annotations

from collections import deque

import pytest

from et_test_platform.communication.transport import ByteTransport
from et_test_platform.instruments.common.scpi import ScpiSession
from et_test_platform.instruments.oscilloscopes.mso5204.driver import Mso5204Driver
from et_test_platform.instruments.oscilloscopes.mso5204.models import (
    Mso5204AcquireType,
    Mso5204BandwidthLimit,
    Mso5204TimebaseMode,
    Mso5204TriggerSlope,
)
from et_test_platform.instruments.oscilloscopes.mso5204.operations import (
    configure_edge_capture,
    read_screen_waveform,
)


# 提供测试内可脚本化字节 Transport；不模拟真实示波器采集时序或模拟输入。
class ScriptedTransport(ByteTransport):
    def __init__(self, responses: dict[bytes, bytes] | None = None) -> None:
        self.responses = responses or {}
        self.writes: list[bytes] = []
        self._pending = deque[bytes]()

    @property
    def identity(self) -> str:
        return "scripted:mso5204"

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


def _public_methods(control: object) -> set[str]:
    return {
        name
        for name in dir(control)
        if not name.startswith("_") and callable(getattr(control, name))
    }


# 验证顶层、IEEE488.2、采集和模拟通道命令都保持单命令映射。
def test_basic_common_acquire_and_channel_mapping() -> None:
    responses = {
        b"*IDN?\n": b"RIGOL TECHNOLOGIES,MSO5204,MSO5A123456789,00.01.02.SP5\n",
        b":ACQuire:SRATe?\n": b"2.500000E+9\n",
        b":CHANnel2:SCALe?\n": b"5.000000E-1\n",
        b":CHANnel2:BWLimit?\n": b"100M\n",
    }
    driver, transport = _driver(responses)

    driver.basic.stop()
    assert driver.common.identity_get().model == "MSO5204"
    driver.acquire.type_set(Mso5204AcquireType.NORMAL)
    assert driver.acquire.sample_rate_get() == pytest.approx(2.5e9)
    driver.channel.bandwidth_limit_set(2, Mso5204BandwidthLimit.MHZ_100)
    assert driver.channel.bandwidth_limit_get(2) == "100M"
    driver.channel.scale_set(2, 0.5)
    assert driver.channel.scale_get(2) == pytest.approx(0.5)

    assert transport.writes == [
        b":STOP\n",
        b"*IDN?\n",
        b":ACQuire:TYPE NORMal\n",
        b":ACQuire:SRATe?\n",
        b":CHANnel2:BWLimit 100M\n",
        b":CHANnel2:BWLimit?\n",
        b":CHANnel2:SCALe 0.5\n",
        b":CHANnel2:SCALe?\n",
    ]


# 验证时基、EDGE 触发和测量项查询不会隐式追加其他配置命令。
def test_timebase_trigger_and_measurement_mapping() -> None:
    responses = {
        b":TIMebase:MODE?\n": b"MAIN\n",
        b":TRIGger:EDGE:LEVel?\n": b"1.250000E+0\n",
        b":MEASure:ITEM? FREQuency,CHANnel1\n": b"1.000000E+6\n",
        b":MEASure:STATistic:ITEM? MAXimum,VPP,CHANnel1\n": b"3.410000E+0\n",
    }
    driver, transport = _driver(responses)

    driver.timebase.mode_set(Mso5204TimebaseMode.YT)
    assert driver.timebase.mode_get() == "MAIN"
    driver.trigger.edge_slope_set(Mso5204TriggerSlope.RISING)
    driver.trigger.edge_level_set(1.25)
    assert driver.trigger.edge_level_get() == pytest.approx(1.25)
    assert driver.measurement.item_get("FREQuency", "CHANnel1") == pytest.approx(1e6)
    assert driver.measurement.statistics_item_get("MAXimum", "VPP", "CHANnel1") == pytest.approx(
        3.41
    )

    assert transport.writes == [
        b":TIMebase:MODE MAIN\n",
        b":TIMebase:MODE?\n",
        b":TRIGger:EDGE:SLOPe POSitive\n",
        b":TRIGger:EDGE:LEVel 1.25\n",
        b":TRIGger:EDGE:LEVel?\n",
        b":MEASure:ITEM? FREQuency,CHANnel1\n",
        b":MEASure:STATistic:ITEM? MAXimum,VPP,CHANnel1\n",
    ]


# 验证 BYTE 波形 definite-length block 会去除块头，并按手册 Y 参数公式换算电压值。
def test_waveform_binary_block_and_conversion() -> None:
    responses = {
        b":WAVeform:PREamble?\n": b"0,0,2,1,1.000000E-6,0.000000E+0,0.000000E+0,1.000000E-2,0,128\n",
        b":WAVeform:DATA?\n": b"#12\x80\x81\n",
    }
    driver, transport = _driver(responses)

    waveform = read_screen_waveform(driver, 1, start=1, stop=2)

    assert waveform.samples == pytest.approx((0.0, 0.01))
    assert waveform.times_s == pytest.approx((0.0, 1e-6))
    assert transport.writes == [
        b":WAVeform:SOURce CHANnel1\n",
        b":WAVeform:MODE NORMal\n",
        b":WAVeform:FORMat BYTE\n",
        b":WAVeform:STARt 1\n",
        b":WAVeform:STOP 2\n",
        b":WAVeform:PREamble?\n",
        b":WAVeform:DATA?\n",
    ]


# 验证截图和系统设置查询能够消费 IEEE488.2 definite-length 二进制数据块。
def test_display_and_system_binary_blocks() -> None:
    responses = {
        b":DISPlay:DATA?\n": b"#14BM12\n",
        b":SYSTem:SETup?\n": b"#15SETUP\n",
    }
    driver, transport = _driver(responses)

    assert driver.display.screenshot_get() == b"BM12"
    assert driver.system.setup_get() == b"SETUP"
    driver.system.setup_set(b"ABC")

    assert transport.writes == [
        b":DISPlay:DATA?\n",
        b":SYSTem:SETup?\n",
        b":SYSTem:SETup #13ABC\n",
    ]


# 验证常用 EDGE 捕获 Operation 只按显式顺序组合公开原子 API。
def test_edge_capture_operation_is_visible_composition() -> None:
    driver, transport = _driver()

    configure_edge_capture(
        driver,
        2,
        vertical_scale_v=0.5,
        time_scale_s=1e-6,
        trigger_level=1.0,
    )

    assert transport.writes == [
        b":CHANnel2:DISPlay ON\n",
        b":CHANnel2:COUPling DC\n",
        b":CHANnel2:SCALe 0.5\n",
        b":TIMebase:MODE MAIN\n",
        b":TIMebase:MAIN:SCALe 1e-06\n",
        b":TRIGger:MODE EDGE\n",
        b":TRIGger:EDGE:SOURce CHANnel2\n",
        b":TRIGger:EDGE:SLOPe POSitive\n",
        b":TRIGger:EDGE:LEVel 1\n",
    ]


# 验证关键范围错误会在任何写入发生前被拒绝，避免把明显非法参数发送到真实示波器。
def test_validation_rejects_invalid_parameters_before_write() -> None:
    driver, transport = _driver()

    with pytest.raises(ValueError):
        driver.channel.scale_set(5, 1.0)
    with pytest.raises(ValueError):
        driver.timebase.reference_position_set(501)
    with pytest.raises(ValueError):
        driver.measurement.cursor_a_position_set(-1)
    with pytest.raises(ValueError):
        driver.counter.digits_set(7)
    with pytest.raises(ValueError):
        driver.display.grid_brightness_set(0)

    assert transport.writes == []


# 固化当前核心 MSO5204 Typed API 的 214 个原子方法，防止重构静默删减已建模能力。
def test_mso5204_core_public_api_inventory() -> None:
    driver, _ = _driver()
    expected_counts = {
        "basic": 6,
        "common": 15,
        "acquire": 11,
        "channel": 22,
        "timebase": 18,
        "trigger": 17,
        "measurement": 38,
        "waveform": 20,
        "display": 16,
        "dvm": 7,
        "counter": 12,
        "system": 32,
    }
    actual = {group: len(_public_methods(getattr(driver, group))) for group in expected_counts}
    assert actual == expected_counts
    assert sum(actual.values()) == 214
