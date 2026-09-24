# 封装层波形分析。
#
# 职责：把已采集的采样点换算成可判定的物理量（电平、边沿、周期、占空比、相位、死区）。
# 边界：纯计算，不做设备 I/O、不决定 PASS/FAIL、不持有测量阈值。
# 依赖：仅依赖 Python 标准库和厂商模型层的已换算波形结果类型。

from __future__ import annotations

from dataclasses import dataclass

from ..mso5204.models import Mso5204Waveform
from .models import Mso5204RawWaveform

# 中值滤波的默认窗口；窗口越大抑噪越强，但也越容易削掉低占空比窄脉冲。
_DEFAULT_DENOISE_WINDOW = 5


# 表示一个已定位的边沿：采样点下标与对应的绝对时间（秒）。
@dataclass(frozen=True, slots=True)
class Edge:
    index: int
    time_s: float


# 表示一段采样波形及其时间基准；所有分析方法都是纯计算，不访问仪器。
@dataclass(frozen=True, slots=True)
class Wave:
    samples: tuple[float, ...]
    x_increment_s: float
    x_origin_s: float = 0.0
    channel: int = 1

    # 返回采样点个数；不触发任何计算或设备访问。
    def __len__(self) -> int:
        return len(self.samples)

    # 返回整段波形覆盖的时间跨度，单位 s；按点数与采样间隔计算，不含原点偏移。
    @property
    def duration_s(self) -> float:
        return len(self.samples) * self.x_increment_s

    # 返回第 index 个采样点的绝对时间，单位 s；越界下标不做截断，由调用方判断。
    def time_at(self, index: int) -> float:
        return self.x_origin_s + index * self.x_increment_s

    # 返回 (低电平, 高电平) 估计值；只用原始极值，不用分位数。
    def levels(self) -> tuple[float, float]:
        # 不使用分位数法：占空比低于 10% 时 p90 仍落在低电平上，
        # 判据中点会退化为 0 导致边沿检测完全失效，而死区/窄脉冲/Burst 恰是低占空比场景。
        # 极值法不受占空比影响，噪声由 denoise() 预先抑制。
        if not self.samples:
            raise ValueError("empty waveform")
        return min(self.samples), max(self.samples)

    # 返回中值滤波后的新波形；窗口过小或点数不足时原样返回，不修改自身。
    def denoise(self, window: int = _DEFAULT_DENOISE_WINDOW) -> Wave:
        # 低占空比窄脉冲在窗口过大时会被整体削掉，因此默认窗口取 5 而不是更大。
        if window < 3 or len(self.samples) < window:
            return self
        half = window // 2
        count = len(self.samples)
        smoothed: list[float] = []
        for index in range(count):
            start = max(0, index - half)
            end = min(count, index + half + 1)
            segment = sorted(self.samples[start:end])
            smoothed.append(segment[len(segment) // 2])
        return Wave(
            samples=tuple(smoothed),
            x_increment_s=self.x_increment_s,
            x_origin_s=self.x_origin_s,
            channel=self.channel,
        )

    # 返回穿越给定电平的采样点下标；按 rising 选择上升沿或下降沿。
    def crossings(self, level: float, *, rising: bool = True) -> list[int]:
        # 起点即高电平的脉冲必须被记为一个上升沿，否则首脉冲会被漏掉；
        # 后续判据统一用 previous < level <= current（下降沿对称）。
        if not self.samples:
            return []
        out: list[int] = []

        first = self.samples[0]
        if rising and first >= level or not rising and first <= level:
            out.append(0)

        for index in range(1, len(self.samples)):
            previous = self.samples[index - 1]
            current = self.samples[index]
            if rising and previous < level <= current or not rising and previous > level >= current:
                out.append(index)
        return out

    # 返回以中点为判据的全部边沿；rising 选择上升沿或下降沿，不做去抖。
    def edges(self, *, rising: bool = True) -> list[Edge]:
        low, high = self.levels()
        # 无电平摆幅（恒定直流或全平波形）时不存在真实边沿。
        # 若继续套用中点判据，中点会正好等于信号电平，起点被判成穿越而凭空多出一个边沿，
        # 使 burst_pulse_count() 对直流返回 1；此处失败关闭，返回空边沿列表。
        if high <= low:
            return []
        mid = (high + low) / 2.0
        return [
            Edge(index=index, time_s=self.time_at(index))
            for index in self.crossings(mid, rising=rising)
        ]

    # 返回高电平采样点占比（%）；点数不足或电平无区分度时返回 None。
    def duty_percent(self) -> float | None:
        if len(self.samples) < 4:
            return None
        low, high = self.levels()
        if high <= low:
            return None
        mid = (high + low) / 2.0
        above = sum(1 for value in self.samples if value >= mid)
        return above * 100.0 / len(self.samples)

    # 返回相邻上升沿间隔的中位数，单位 s；边沿不足 2 个时返回 None。
    def period_s(self) -> float | None:
        rises = self.edges(rising=True)
        if len(rises) < 2:
            return None
        gaps = sorted(rises[i + 1].time_s - rises[i].time_s for i in range(len(rises) - 1))
        return gaps[len(gaps) // 2] if gaps else None

    # 返回由周期中位数换算的频率，单位 Hz；周期不可测或非正时返回 None。
    def frequency_hz(self) -> float | None:
        period = self.period_s()
        return None if not period or period <= 0 else 1.0 / period

    # 从屏幕模式读取结果构造分析对象；沿用 preamble 的采样间隔与时间原点。
    @classmethod
    def from_screen(cls, waveform: Mso5204Waveform) -> Wave:
        return cls(
            samples=tuple(waveform.samples),
            x_increment_s=waveform.preamble.x_increment_s,
            x_origin_s=waveform.preamble.x_origin_s,
        )

    # 从 RAW 深存储读取结果构造分析对象；深存储点数可达百万级，只引用元组不复制。
    @classmethod
    def from_raw(cls, waveform: Mso5204RawWaveform) -> Wave:
        return cls(
            samples=tuple(waveform.samples),
            x_increment_s=waveform.x_increment_s,
            x_origin_s=waveform.x_origin_s,
            channel=waveform.channel,
        )


# 返回两路边沿的时间差（B - A），按周期对齐选取同一周期内的边沿。
def edge_offset_s(
    wave_a: Wave,
    wave_b: Wave,
    *,
    rising_a: bool = True,
    rising_b: bool = True,
    nth: int = 0,
) -> float | None:
    # 不能直接取第 nth 个边沿相减：采集起点相位不同会让 B[0] 落在 A[0] 之前，
    # 差值会凭空带上整数个周期。这里以 A 的第 nth 个边沿为基准，
    # 在 B 中选时间上最接近它的边沿，从而得到同一周期内的真实相位差。
    a_edges = wave_a.edges(rising=rising_a)
    b_edges = wave_b.edges(rising=rising_b)
    if len(a_edges) <= nth or not b_edges:
        return None

    reference = a_edges[nth].time_s
    closest = min(b_edges, key=lambda edge: abs(edge.time_s - reference))
    return closest.time_s - reference


# 返回互补 PWM 死区：A 边沿到紧随其后的 B 边沿的时间间隔，单位 s。
def dead_time_s(
    wave_a: Wave,
    wave_b: Wave,
    *,
    direction: str = "a_fall_to_b_rise",
    max_gap_s: float | None = None,
) -> float | None:
    # 取最小值而不是中位数：死区是每个周期重复出现的最短间隔。
    # 若某个 A 边沿之后恰好跨过了 B 的高电平区，配对会落到下一周期的 B 边沿，
    # 得到远大于死区的值；这类异常配对只影响部分样本，取最小值仍能稳定命中真实死区。
    if abs(wave_a.x_increment_s - wave_b.x_increment_s) > 1e-15:
        return None

    if direction == "a_fall_to_b_rise":
        starts = wave_a.edges(rising=False)
        ends = wave_b.edges(rising=True)
    elif direction == "a_rise_to_b_fall":
        starts = wave_a.edges(rising=True)
        ends = wave_b.edges(rising=False)
    else:
        raise ValueError(f"unsupported direction {direction!r}")

    # 搜索窗口优先用调用方给定值，否则按周期推断；周期不可测时不做窗口限制。
    window = max_gap_s
    if window is None:
        period = wave_a.period_s()
        if period and period > 0:
            window = period / 4.0

    gaps: list[float] = []
    for start in starts:
        for end in ends:
            delta = end.time_s - start.time_s
            if delta <= 0:
                continue
            if window is not None and delta > window:
                break  # ends 按时间升序，后续只会更大
            gaps.append(delta)
            break

    if not gaps:
        return None
    return min(gaps)


# 返回指定方向的边沿数量；不区分周期归属，只做计数。
def count_edges(wave: Wave, *, rising: bool = True) -> int:
    return len(wave.edges(rising=rising))


# 返回脉冲串中的脉冲个数；以上升沿计数，起点即高电平时同样计入首脉冲。
def burst_pulse_count(wave: Wave) -> int:
    return count_edges(wave, rising=True)


# 返回高电平估计值，单位 V；等价于 levels() 的第二个元素。
def high_level_v(wave: Wave) -> float:
    return wave.levels()[1]


# 返回低电平估计值，单位 V；等价于 levels() 的第一个元素。
def low_level_v(wave: Wave) -> float:
    return wave.levels()[0]


# 返回第 nth 个边沿的绝对时间，单位 s；用于比较细调前后同一边沿的位移。
def edge_position_s(wave: Wave, *, rising: bool = True, nth: int = 0) -> float | None:
    edges = wave.edges(rising=rising)
    if len(edges) <= nth:
        return None
    return edges[nth].time_s


__all__ = [
    "Edge",
    "Wave",
    "burst_pulse_count",
    "count_edges",
    "dead_time_s",
    "edge_offset_s",
    "edge_position_s",
    "high_level_v",
    "low_level_v",
]
