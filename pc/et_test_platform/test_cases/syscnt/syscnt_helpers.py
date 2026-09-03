# SYSCNT纯计算辅助。
# 职责：展开参考模数、计算时间误差边界和拼接已取得的停核读数。
# 边界：无I/O、无硬件配置、无PASS断言。
# 依赖：稳定采样Model与标准库。

from ...drivers.syscnt import SyscntReferenceSample


# 双端夹取给出真实读取时间的区间；PC包围时间仅排除参考计数多次回绕。
def timing_bounds(
    first: SyscntReferenceSample,
    last: SyscntReferenceSample,
    reference_bits: int,
    counter_bits: int,
    reference_hz: int,
    counter_hz: int,
    host_elapsed_s: float,
) -> tuple[float, float, float]:
    modulus = 1 << reference_bits
    if host_elapsed_s * reference_hz >= modulus:
        raise ValueError("reference may have wrapped more than once within the host envelope")
    b0, a1, b1 = (
        (value - first.reference_before) % modulus
        for value in (first.reference_after, last.reference_before, last.reference_after)
    )
    if not 0 <= b0 < a1 <= b1:
        raise ValueError("reference did not advance coherently between samples")
    minimum = (a1 - b0) / reference_hz
    maximum = b1 / reference_hz
    counter_time = ((last.count - first.count) % (1 << counter_bits)) / counter_hz
    return (
        counter_time,
        max(abs(counter_time - minimum), abs(counter_time - maximum)),
        maximum - minimum,
    )


# Mapping按高、低、高、状态、控制顺序采样；跨字不一致直接暴露，不能拼出伪计数。
def halted_counter(words: tuple[int, ...], word_bits: int) -> tuple[int, int, int]:
    high_before, low, high_after, status, control = words
    if high_before != high_after:
        raise ValueError(f"halted counter read is torn: {words!r}")
    return (high_before << word_bits) | low, status, control
