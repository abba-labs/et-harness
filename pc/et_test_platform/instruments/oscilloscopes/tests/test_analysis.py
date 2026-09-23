# 波形分析层无硬件测试。
#
# 职责：验证电平估计、边沿检测、周期/占空比、相位对齐、死区和脉冲计数等纯计算结果。
# 边界：不连接真实仪器、不做 PASS/FAIL 阈值判定，也不证明真实采集数据正确。
# 依赖：仅依赖 pytest 与本库 analysis 公开 API。

from __future__ import annotations

import math

import pytest
from oscilloscopes.mso5204 import (
    Wave,
    burst_pulse_count,
    count_edges,
    dead_time_s,
    edge_offset_s,
    edge_position_s,
    high_level_v,
    low_level_v,
)
from oscilloscopes.mso5204.models import (
    Mso5204RawWaveform,
    Mso5204Waveform,
    Mso5204WaveformPreamble,
)


# 校验一个期望条件；不成立时抛出 AssertionError，由 pytest 记为用例失败。
def _expect(condition: bool, message: str) -> None:

    if not condition:
        raise AssertionError(message)


# 按给定周期与高电平点数生成方波采样；用于构造可预测的分析输入。
def _square(
    *,
    periods: int,
    samples_per_period: int,
    high_fraction: float,
    low_v: float = 0.0,
    high_v: float = 3.3,
    x_increment_s: float = 1e-6,
) -> Wave:
    samples: list[float] = []
    high_count = int(round(samples_per_period * high_fraction))
    for _ in range(periods):
        samples.extend([high_v] * high_count)
        samples.extend([low_v] * (samples_per_period - high_count))
    return Wave(samples=tuple(samples), x_increment_s=x_increment_s)


# 验证空波形在取电平时失败关闭，不返回误导性的 (0, 0)。
def test_levels_reject_empty_waveform() -> None:

    with pytest.raises(ValueError):
        Wave(samples=(), x_increment_s=1e-6).levels()


# 验证电平估计使用原始极值；低占空比场景下分位数法会失效，极值法必须仍然正确。
def test_levels_use_extremes_for_low_duty() -> None:

    wave = _square(periods=4, samples_per_period=100, high_fraction=0.02)

    low, high = wave.levels()

    _expect(low == 0.0, f"low={low}")
    _expect(high == 3.3, f"high={high}")


# 验证周期与频率由相邻上升沿间隔的中位数给出，且与构造参数一致。
def test_period_and_frequency_match_construction() -> None:

    wave = _square(periods=5, samples_per_period=100, high_fraction=0.5, x_increment_s=1e-6)

    period = wave.period_s()
    freq = wave.frequency_hz()

    _expect(period is not None and math.isclose(period, 100e-6, rel_tol=1e-9), f"period={period}")
    _expect(freq is not None and math.isclose(freq, 10000.0, rel_tol=1e-9), f"freq={freq}")


# 验证占空比按中点判据统计高电平采样点，50% 方波应给出 50%。
def test_duty_percent_of_square_wave() -> None:

    wave = _square(periods=4, samples_per_period=100, high_fraction=0.5)

    _expect(math.isclose(wave.duty_percent(), 50.0, abs_tol=0.01), f"{wave.duty_percent()}")


# 验证点数不足时占空比返回 None，而不是给出不可靠的估计值。
def test_duty_percent_needs_enough_points() -> None:

    _expect(Wave(samples=(0.0, 3.3, 0.0), x_increment_s=1e-6).duty_percent() is None, "short wave")


# 验证恒定电平波形没有可判定边沿，周期与占空比都返回 None 而不是抛异常。
def test_flat_waveform_has_no_edges() -> None:

    flat = Wave(samples=tuple([1.0] * 50), x_increment_s=1e-6)

    # 恒定直流的极值相等，中点判据会退化成"起点即穿越"而凭空产生一个边沿，
    # 因此必须显式返回空边沿，否则 burst_pulse_count 会把直流当成 1 个脉冲。
    _expect(len(flat.edges()) == 0, "flat wave must have no edges")
    _expect(flat.period_s() is None, "flat wave must have no period")
    _expect(flat.duty_percent() is None, "flat wave must have no duty")
    _expect(burst_pulse_count(flat) == 0, "flat wave must have no pulses")


# 验证起点即高电平的脉冲被计入上升沿；否则首脉冲会被系统性漏掉。
def test_leading_high_sample_counts_as_rising_edge() -> None:

    wave = Wave(samples=(3.3, 3.3, 3.3, 0.0, 0.0), x_increment_s=1e-6)

    rising = wave.crossings(1.65, rising=True)

    _expect(rising == [0], f"leading edge missing: {rising}")


# 验证起点即低电平时下降沿同样被补记，保持与上升沿对称的判定语义。
def test_leading_low_sample_counts_as_falling_edge() -> None:

    wave = Wave(samples=(0.0, 0.0, 3.3, 3.3), x_increment_s=1e-6)

    falling = wave.crossings(1.65, rising=False)

    _expect(falling == [0], f"leading falling edge missing: {falling}")


# 验证中值滤波是单点毛刺的必要前置步骤：毛刺会污染极值法电平估计并破坏边沿检测。
def test_denoise_removes_single_sample_spike() -> None:
    # 每周期 20 点、前 10 点高；index 15 位于低电平区，在此制造单点毛刺。
    # 该毛刺同时成为新的最大值，使中点判据整体抬高，真实边沿大面积漏检。
    clean = _square(periods=3, samples_per_period=20, high_fraction=0.5)
    spiked = list(clean.samples)
    spiked[15] = 9.9
    noisy = Wave(samples=tuple(spiked), x_increment_s=clean.x_increment_s)

    _expect(noisy.levels()[1] == 9.9, "spike must dominate the extremum-based levels")
    _expect(
        len(noisy.edges()) < len(clean.edges()),
        "spike-shifted midpoint must drop real edges",
    )
    # 先滤波再分析是约定用法，滤波后电平与边沿必须完全恢复。
    filtered = noisy.denoise()
    _expect(filtered.levels() == clean.levels(), "denoise must restore true levels")
    _expect(len(filtered.edges()) == len(clean.edges()), "denoise must restore edge count")


# 验证中值滤波在窗口非法或点数不足时原样返回，不抛异常也不改变数据。
def test_denoise_is_noop_when_inapplicable() -> None:

    wave = _square(periods=2, samples_per_period=10, high_fraction=0.5)

    _expect(wave.denoise(window=1) is wave, "small window must be a no-op")
    _expect(
        Wave(samples=(1.0, 2.0), x_increment_s=1e-6).denoise(window=5).samples == (1.0, 2.0),
        "short wave must be returned unchanged",
    )


# 验证默认窗口保留 3 采样点宽的窄脉冲；更宽的窗口会把它整体削掉。
def test_denoise_preserves_narrow_pulse() -> None:
    # 3 点宽的脉冲恰好能被宽度 5 的中值窗口保住；这是默认窗口取 5 而非更大的原因。
    samples = [0.0] * 10 + [3.3] * 3 + [0.0] * 9
    wave = Wave(samples=tuple(samples), x_increment_s=1e-6)

    filtered = wave.denoise(window=5)

    _expect(max(filtered.samples) == 3.3, "3-point narrow pulse was removed by denoise")


# 验证死区取最小间隔；跨周期误配产生的大间隔不得污染结果。
def test_dead_time_uses_minimum_gap() -> None:
    # A 下降沿在 t=0,10,20us；B 上升沿紧随其后 1us。
    inc = 1e-6
    a_samples = [3.3] * 5 + [0.0] * 5  # 下降沿在 index 5 -> 5us，周期 10us
    wave_a = Wave(samples=tuple(a_samples * 3), x_increment_s=inc)
    b_samples = [0.0] * 6 + [3.3] * 4  # 上升沿在 index 6 -> 6us，晚 1us
    wave_b = Wave(samples=tuple(b_samples * 3), x_increment_s=inc)

    dead = dead_time_s(wave_a, wave_b)

    _expect(dead is not None, "dead time must be measurable")
    _expect(math.isclose(dead, 1e-6, abs_tol=1e-9), f"dead={dead}")


# 验证采样间隔不一致时死区测量失败关闭，避免比较不同时间基准的数据。
def test_dead_time_rejects_mismatched_timebase() -> None:

    wave_a = _square(periods=2, samples_per_period=20, high_fraction=0.5, x_increment_s=1e-6)
    wave_b = _square(periods=2, samples_per_period=20, high_fraction=0.5, x_increment_s=2e-6)

    _expect(dead_time_s(wave_a, wave_b) is None, "mismatched timebase must be rejected")


# 验证不支持的死区方向被显式拒绝，而不是静默返回 None 掩盖调用错误。
def test_dead_time_rejects_unknown_direction() -> None:

    wave_a = _square(periods=2, samples_per_period=20, high_fraction=0.5)
    wave_b = _square(periods=2, samples_per_period=20, high_fraction=0.5)

    with pytest.raises(ValueError):
        dead_time_s(wave_a, wave_b, direction="b_fall_to_a_rise")


# 验证相位差按周期对齐；B 整体滞后半个周期时应得到半周期而不是整数倍偏移。
def test_edge_offset_aligns_within_period() -> None:
    # A 高 5 低 5（周期 10 点）；B 相对 A 延迟 5 点即半周期。
    inc = 1e-6
    wave_a = Wave(samples=tuple(([3.3] * 5 + [0.0] * 5) * 4), x_increment_s=inc)
    wave_b = Wave(samples=tuple(([0.0] * 5 + [3.3] * 5) * 4), x_increment_s=inc)

    offset = edge_offset_s(wave_a, wave_b)

    _expect(offset is not None, "offset must be measurable")
    _expect(abs(offset) <= 5e-6 + 1e-9, f"offset escaped one period: {offset}")


# 验证边沿不足时相位差与边沿位置返回 None，不抛异常也不猜测。
def test_edge_helpers_return_none_when_insufficient() -> None:

    flat = Wave(samples=tuple([1.0] * 20), x_increment_s=1e-6)

    _expect(edge_offset_s(flat, flat) is None, "flat offset must be None")
    _expect(edge_position_s(flat) is None, "flat position must be None")
    _expect(edge_position_s(flat, nth=5) is None, "out-of-range nth must be None")


# 验证电平辅助函数与 levels() 一致，避免两条路径给出不同结论。
def test_level_helpers_match_levels() -> None:

    wave = _square(periods=3, samples_per_period=20, high_fraction=0.5)

    low, high = wave.levels()

    _expect(low_level_v(wave) == low, "low_level_v mismatch")
    _expect(high_level_v(wave) == high, "high_level_v mismatch")


# 验证边沿计数与脉冲串计数一致，且起点即高电平时首脉冲被计入。
def test_edge_and_burst_counts_include_leading_pulse() -> None:

    wave = Wave(samples=tuple([3.3] * 3 + [0.0] * 3), x_increment_s=1e-6)

    _expect(count_edges(wave, rising=True) == 1, "expected one rising edge")
    _expect(burst_pulse_count(wave) == 1, "leading pulse must be counted")
    # 起点不再穿越（已在低电平），末尾高到低构成唯一一个下降沿。
    _expect(count_edges(wave, rising=False) == 1, "expected one falling edge at the end")


# 验证从 RAW 结果构造分析对象时沿用其采样间隔与时间原点。
def test_wave_from_raw_keeps_timebase() -> None:

    raw = Mso5204RawWaveform(
        channel=1,
        samples=(0.0, 1.0, 0.0, 1.0),
        x_increment_s=2.5e-10,
        x_origin_s=1e-7,
    )

    wave = Wave.from_raw(raw)

    _expect(wave.x_increment_s == 2.5e-10, "increment not preserved")
    _expect(wave.x_origin_s == 1e-7, "origin not preserved")
    _expect(wave.channel == 1, "channel not preserved")
    _expect(math.isclose(wave.time_at(1), 1e-7 + 2.5e-10), "time_at mismatch")


# 验证从屏幕波形构造分析对象时使用 preamble 的采样间隔与时间原点。
def test_wave_from_screen_uses_preamble() -> None:

    preamble = Mso5204WaveformPreamble(
        format_code=0,
        type_code=0,
        points=4,
        count=1,
        x_increment_s=5e-7,
        x_origin_s=0.0,
        x_reference=0.0,
        y_increment_v=0.01,
        y_origin=0.0,
        y_reference=0.0,
    )
    screen = Mso5204Waveform(
        preamble=preamble,
        samples=(0.0, 1.0, 0.0, 1.0),
        times_s=(0.0, 5e-7, 1e-6, 1.5e-6),
    )

    wave = Wave.from_screen(screen)

    _expect(wave.x_increment_s == 5e-7, "preamble increment not used")
    _expect(len(wave) == 4, "sample count mismatch")
    _expect(math.isclose(wave.duration_s, 2e-6), f"duration={wave.duration_s}")


# 验证滤波后的波形仍保留时间基准与通道号，不丢失元数据。
def test_denoise_preserves_metadata() -> None:

    raw = Mso5204RawWaveform(
        channel=3,
        samples=tuple([0.0] * 10 + [1.0] * 10),
        x_increment_s=1e-9,
        x_origin_s=4e-9,
    )

    filtered = Wave.from_raw(raw).denoise()

    _expect(filtered.channel == 3, "channel lost")
    _expect(filtered.x_increment_s == 1e-9, "increment lost")
    _expect(filtered.x_origin_s == 4e-9, "origin lost")
