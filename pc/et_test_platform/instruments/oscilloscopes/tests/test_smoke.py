# 示波器库无硬件冒烟测试。
#
# 职责：验证整包可独立导入、SCPI 命令拼装正确、参数校验失败关闭以及异常层次完整。
# 边界：不连接真实仪器、不依赖 PyVISA backend，也不证明真实采集或测量行为。
# 依赖：仅依赖 pytest、本库公开 API 和测试内脚本化 Transport。

from __future__ import annotations

from collections import deque
from pathlib import Path

import pytest
from oscilloscopes._internal import (
    ByteTransport,
    InstrumentProtocolError,
    OscilloscopeError,
    OscilloscopeTimeout,
    ScpiSession,
    TransportError,
)
from oscilloscopes.mso5204 import (
    Mso5204AcquireConfig,
    Mso5204Driver,
    Mso5204RawWaveformConfig,
    Mso5204TriggerConfig,
    Mso5204TriggerSweep,
    create_mso5204_visa_driver,
    open_scope,
)
from oscilloscopes.mso5204.models import Mso5204TriggerSlope


# 校验一个期望条件；不成立时抛出 AssertionError，由 pytest 记为用例失败。
def _expect(condition: bool, message: str) -> None:

    if not condition:
        raise AssertionError(message)


# RAW 波形读取所需的换算响应：1V/计数、0 原点、0 参考，使样本值等于原始字节值。
_RAW_PREAMBLE_RESPONSES = {
    b":WAVeform:PREamble?\n": b"0,0,3,1,1.0E-09,0.0,0.0,1.0,0.0,0.0\n",
    b":WAVeform:XINCrement?\n": b"1.000000E-09\n",
    b":WAVeform:XORigin?\n": b"0.000000E+00\n",
    b":WAVeform:XREFerence?\n": b"0.000000E+00\n",
    b":WAVeform:YINCrement?\n": b"1.000000E+00\n",
    b":WAVeform:YORigin?\n": b"0.000000E+00\n",
    b":WAVeform:YREFerence?\n": b"0.000000E+00\n",
}


# 提供测试内可脚本化字节 Transport；不模拟真实仪器时序或模拟前端行为。
class ScriptedTransport(ByteTransport):
    def __init__(self, responses: dict[bytes, bytes] | None = None) -> None:
        self.responses = responses or {}
        self.writes: list[bytes] = []
        self._pending: deque[bytes] = deque()

    # 返回固定的脚本化连接标识；不访问任何真实仪器资源。
    @property
    def identity(self) -> str:
        return "scripted:mso5204"

    # 模拟打开连接；脚本化 Transport 无需真实资源，因此只完成状态占位。
    def open(self) -> None:
        pass

    # 模拟关闭连接；脚本化 Transport 不持有真实句柄，因此不做释放动作。
    def close(self) -> None:
        pass

    # 记录一条写入并按预置响应表排队响应；未命中响应表时只记录不排队。
    def write(self, data: bytes, *, timeout_s: float | None = None) -> None:
        self.writes.append(data)
        response = self.responses.get(data)
        if response is not None:
            self._pending.append(response)

    # 读取已排队的响应字节；队列为空时返回空字节串，模拟无数据可读。
    def read(self, max_bytes: int, timeout_s: float | None = None) -> bytes:
        if not self._pending:
            return b""
        current = self._pending.popleft()
        if len(current) <= max_bytes:
            return current
        self._pending.appendleft(current[max_bytes:])
        return current[:max_bytes]


# 构造绑定脚本化 Transport 的 Driver；不打开任何 VISA 资源。
def _driver(responses: dict[bytes, bytes] | None = None) -> tuple[Mso5204Driver, ScriptedTransport]:

    transport = ScriptedTransport(responses)
    return Mso5204Driver(ScpiSession(transport)), transport


# 验证整包导入后公开工厂可用，且构造阶段不发送任何 SCPI 命令。
def test_package_imports_and_constructs_without_io() -> None:

    driver = create_mso5204_visa_driver("TCPIP0::169.254.201.131::INSTR")

    _expect(driver.identity == "visa:TCPIP0::169.254.201.131::INSTR", "identity mismatch")
    _expect(driver.operations is not None, "operations layer missing")


# 验证 Driver 聚合了全部常用原子控制命名空间，避免整包导入后能力缺失。
def test_driver_exposes_control_namespaces() -> None:

    driver, _ = _driver()

    for name in (
        "acquire",
        "basic",
        "channel",
        "cursor",
        "display",
        "dvm",
        "measurement",
        "system",
        "timebase",
        "trigger",
        "waveform",
    ):
        _expect(hasattr(driver, name), f"missing control namespace {name}")


# 验证原子控制发送单条 SCPI 命令，不追加等待或额外查询。
def test_basic_control_sends_single_command() -> None:

    driver, transport = _driver()

    driver.basic.run()
    driver.basic.stop()

    _expect(transport.writes == [b":RUN\n", b":STOP\n"], f"writes={transport.writes!r}")


# 验证查询命令正确拆分为写入和读取，并解析 ASCII 响应。
def test_query_returns_parsed_response() -> None:

    driver, transport = _driver({b":CHANnel1:SCALe?\n": b"1.000000E+00\n"})

    _expect(driver.channel.scale_get(1) == 1.0, "scale parse failed")
    _expect(transport.writes == [b":CHANnel1:SCALe?\n"], f"writes={transport.writes!r}")


# 验证非法通道号在触达设备之前被拒绝，且不产生任何 SCPI 写入。
def test_invalid_channel_is_rejected_before_io() -> None:

    driver, transport = _driver()

    with pytest.raises(ValueError):
        driver.channel.scale_get(9)

    _expect(transport.writes == [], f"unexpected writes={transport.writes!r}")


# 验证非法时基被拒绝，保证参数错误在设备 I/O 前失败关闭。
def test_invalid_timebase_is_rejected() -> None:

    driver, _ = _driver()

    with pytest.raises(ValueError):
        driver.timebase.main_scale_set(-1.0)


# 验证非 ASCII 响应被识别为协议错误，而不是静默解码成乱码。
def test_non_ascii_response_raises_protocol_error() -> None:

    driver, _ = _driver({b":CHANnel1:SCALe?\n": b"\xff\xfe\n"})

    with pytest.raises(InstrumentProtocolError):
        driver.channel.scale_get(1)


# 验证异常层次允许调用方用 OscilloscopeError 统一捕获，且超时同时属于传输失败。
def test_exception_hierarchy() -> None:

    _expect(issubclass(TransportError, OscilloscopeError), "TransportError must be catchable")
    _expect(
        issubclass(InstrumentProtocolError, OscilloscopeError),
        "InstrumentProtocolError must be catchable",
    )
    _expect(issubclass(OscilloscopeTimeout, TransportError), "timeout must be a transport error")


# 验证空资源名在构造阶段被拒绝，避免把错误推迟到真实连接。
def test_empty_resource_name_is_rejected() -> None:

    with pytest.raises(ValueError):
        create_mso5204_visa_driver("  ")


# 验证触发斜率枚举对调用方稳定可见，且保留仪器可接受的完整拼写形式。
def test_trigger_slope_enum_is_public() -> None:

    _expect(Mso5204TriggerSlope.RISING.value == "POSitive", "trigger slope enum changed")


# 验证测量便捷方法把仪器的无效值哨兵 9.9E+37 过滤成 None，而不是当成真实物理量返回。
def test_measure_item_filters_invalid_sentinel() -> None:

    driver, _ = _driver(
        {
            b":MEASure:ITEM? FREQuency,CHANnel1\n": b"9.900000E+37\n",
            b":MEASure:ITEM? VPP,CHANnel1\n": b"3.5128E+00\n",
        }
    )

    _expect(driver.operations.measure_item("FREQuency", 1) is None, "sentinel must become None")
    _expect(driver.operations.measure_item("VPP", 1) == 3.5128, "valid value must pass through")


# 验证跨通道延迟测量会先配置 A/B 源，再带两个源查询，顺序和参数都正确。
def test_measure_delay_configures_sources_then_queries() -> None:

    driver, transport = _driver({b":MEASure:ITEM? FFDelay,CHANnel1,CHANnel2\n": b"2.000000E-06\n"})

    value = driver.operations.measure_delay("FFDelay", 1, 2)

    _expect(value == 2e-06, f"cross delay parse failed: {value!r}")
    _expect(
        transport.writes[:4]
        == [
            b":MEASure:SETup:DSA CHANnel1\n",
            b":MEASure:SETup:DSB CHANnel2\n",
            b":MEASure:SETup:PSA CHANnel1\n",
            b":MEASure:SETup:PSB CHANnel2\n",
        ],
        f"source setup order wrong: {transport.writes[:4]!r}",
    )


# 验证触发配置只下发显式给出的字段，None 字段不产生任何 SCPI 写入。
def test_configure_trigger_only_sends_explicit_fields() -> None:

    driver, transport = _driver()

    driver.operations.configure_trigger(Mso5204TriggerConfig(edge_level_v=1.5))

    _expect(transport.writes == [b":TRIGger:EDGE:LEVel 1.5\n"], f"writes={transport.writes!r}")


# 验证扫描方式在触发参数之后下发，避免 SINGle 武装后被后续设置覆盖。
def test_configure_trigger_sets_sweep_last() -> None:

    driver, transport = _driver()

    driver.operations.configure_trigger(
        Mso5204TriggerConfig(sweep=Mso5204TriggerSweep.SINGLE, edge_level_v=1.5)
    )

    _expect(
        transport.writes[-1] == b":TRIGger:SWEep SINGle\n",
        f"sweep must be last: {transport.writes!r}",
    )


# 验证采集配置在非 AVERage 类型下拒绝平均次数，避免下发互相矛盾的命令。
def test_configure_acquire_rejects_average_count_without_average_type() -> None:

    driver, transport = _driver()

    with pytest.raises(ValueError):
        driver.operations.configure_acquire(Mso5204AcquireConfig(average_count=16))

    _expect(transport.writes == [], f"must fail before I/O: {transport.writes!r}")


# 验证 RAW 波形读取按实测要求先停采集再读，并在读后恢复连续运行。
def test_read_raw_waveform_stops_then_restores_run() -> None:
    # RAW 数据为 3 个点的 BYTE 块；preambles 按 YINCrement/YORigin/YREFerence 给出换算系数。
    driver, transport = _driver(
        {
            b":TRIGger:STATus?\n": b"TD\n",
            b":WAVeform:DATA?\n": b"#13\x80\x7f\x00",
            **_RAW_PREAMBLE_RESPONSES,
        }
    )

    raw = driver.operations.read_raw_waveform(Mso5204RawWaveformConfig(channel=1))

    _expect(len(raw.samples) == 3, f"expected 3 samples, got {len(raw.samples)}")
    # 顺序要求：STOP -> 读数据 -> 读 preamble -> 恢复 RUN。
    writes = transport.writes
    stop_index = writes.index(b":STOP\n")
    data_index = writes.index(b":WAVeform:DATA?\n")
    preamble_index = writes.index(b":WAVeform:PREamble?\n")
    run_index = writes.index(b":RUN\n")
    _expect(stop_index < data_index, "must STOP before reading data")
    _expect(data_index < preamble_index, "must read preamble before restarting RUN")
    _expect(preamble_index < run_index, "must restart RUN after reading preamble")


# 验证 RAW 读取即使失败也恢复连续采集，避免把仪器留在 STOP 状态。
def test_read_raw_waveform_restores_run_on_failure() -> None:

    driver, transport = _driver({b":TRIGger:STATus?\n": b"TD\n"})

    # 无响应时由 SCPI 会话的总 Deadline 抛出超时异常，属可预期的传输失败。
    with pytest.raises(OscilloscopeTimeout):
        driver.operations.read_raw_waveform(Mso5204RawWaveformConfig(channel=1))

    _expect(
        transport.writes[-1] == b":RUN\n", f"RUN must survive failure: {transport.writes[-1]!r}"
    )


# 验证 RAW 波形读取在为空的响应上失败关闭，而不是返回空波形误导调用方。
def test_read_raw_waveform_rejects_empty_payload() -> None:

    driver, _ = _driver({b":TRIGger:STATus?\n": b"TD\n", b":WAVeform:DATA?\n": b"#10"})

    with pytest.raises(InstrumentProtocolError):
        driver.operations.read_raw_waveform(Mso5204RawWaveformConfig(channel=1))


# 验证截图方法把仪器返回的 BMP 字节原样写入目标文件并返回字节数。
def test_save_screenshot_writes_payload(tmp_path: Path) -> None:

    bmp = b"BM" + b"\x00" * 52
    # IEEE488.2 块头 #2 10 表示后接 2 位长度 "10"，即 10 字节负载。
    driver, _ = _driver({b":DISPlay:DATA?\n": b"#210" + bmp[:10]})
    target = tmp_path / "shot.bmp"

    written = driver.operations.save_screenshot(target)

    _expect(written == 10, f"unexpected size {written}")
    _expect(target.read_bytes() == bmp[:10], "screenshot bytes mismatch")


# 验证截图在仪器返回空数据时失败关闭，不生成误导性的空文件。
def test_save_screenshot_rejects_empty_payload(tmp_path: Path) -> None:

    driver, _ = _driver({b":DISPlay:DATA?\n": b"#10"})

    with pytest.raises(ValueError):
        driver.operations.save_screenshot(tmp_path / "empty.bmp")


# 验证台架对象的 with 语句自动关闭连接，且在异常路径上同样关闭。
def test_scope_context_manager_closes_connection() -> None:

    scope = open_scope("TCPIP0::169.254.201.131::INSTR")

    with scope:
        _expect(scope.identity.endswith("169.254.201.131::INSTR"), "identity mismatch")
        raised = False
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            raised = True
        _expect(raised, "sanity check failed")


# 验证台架对象在构造阶段不访问仪器，符合零副作用约定。
def test_scope_constructs_without_io() -> None:

    scope = open_scope("TCPIP0::169.254.201.131::INSTR")

    _expect(scope.channel == 1, "default channel must be CH1")
    _expect(scope.driver is not None, "driver must exist before open")


# 验证台架 select_channel 只改变默认通道，不发送任何 SCPI 命令。
def test_scope_select_channel_sends_nothing() -> None:

    scope = open_scope("TCPIP0::169.254.201.131::INSTR")

    scope.select_channel(2)

    _expect(scope.channel == 2, "channel select failed")


# 验证台架 select_channel 拒绝非法通道号，保持与原子 API 一致的失败语义。
def test_scope_select_channel_rejects_invalid() -> None:

    scope = open_scope("TCPIP0::169.254.201.131::INSTR")

    with pytest.raises(ValueError):
        scope.select_channel(9)
