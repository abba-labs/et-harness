# CAN时间戳Case独立Wire回归。
# 职责：校验关闭、锁存、回卷、W1C和清零的首错判据及清理。
# 边界：固定向量不模拟真实计数速度，不产生硬件PASS。
# 依赖：真实Case/Driver、独立响应队列和PC窗口时钟替身。

from itertools import count
from struct import pack

import pytest
from et_test_platform.framework_validation.unit.drivers.can.test_can_case_flow import (
    assert_case_report,
    dependencies,
)
from et_test_platform.test_cases.can import test_can_p1_timestamp as timestamp_case


# 测试Feature：三个分频独立执行全部阶段，拒绝自然回卷冒充清零。
# 测试方法：固定Wire注入关闭非零、错误锁存、缺IRQ、W1C失败、清零无效等。
# 通过条件：正常完整消费响应且只清零一次；所有坏值失败并复位资源。
@pytest.mark.parametrize("divisor", (1, 2, 16))
@pytest.mark.parametrize(
    "fault",
    (
        None,
        "config",
        "disabled",
        "stamp",
        "frame",
        "wrap_irq",
        "clear_irq",
        "reset_noop",
        "reset_wrap",
        "window",
        "reset_window",
    ),
)
def test_timestamp_case_vectors(divisor, fault, monkeypatch, tmp_path):
    support, resource, target, calls = dependencies()
    target.responses = []
    for internal in (False, True):
        target.responses += [b"", pack("<I", 1)] + [b""] * 7
        target.responses += [
            pack(
                "<11I",
                1,
                0,
                divisor,
                0 if fault == "config" else int(internal),
                0,
                1000,
                0,
                1,
                1,
                2,
                2,
            ),
            b"",
            pack("<I", 0),
        ]
        if internal:
            target.responses += [b"", b""]
        for index in range(2 if internal else 1):
            before = 100 + index * 100 if internal else int(fault == "disabled")
            after = 150 + index * 100 if internal else 0
            stamp = 125 + index * 100 if internal else 0
            if internal and fault == "stamp":
                stamp = 999
            payload = bytes(((49 + 17 * i) % 256) ^ (255 if index else 0) for i in range(8))
            if internal and fault == "frame":
                payload = bytes(8)
            target.responses += [
                pack("<I", before),
                b"",
                b"",
                pack("<7I", 0, 1, 0, 1, 0, 0, 0),
                pack("<5I", 1, index, index + 1, 0, 0),
                pack("<8I", 0x123, 0, 8, stamp, 0, 0, 8, index) + payload + bytes(56),
                pack("<I", after),
                b"",
            ]
    target.responses += [
        b"",
        pack("<I", 65520),
        pack("<I", 16),
        pack("<4I", 0 if fault == "wrap_irq" else 1 << 16, 0, 0, 1),
        b"",
        pack("<4I", 1 << 16 if fault == "clear_irq" else 0, 0, 0, 1),
        pack("<I", 32768),
        pack(
            "<2I", 65000 if fault == "reset_wrap" else 34000, 34000 if fault == "reset_noop" else 3
        ),
    ]
    clock = count()

    # Case使用11次monotonic：前六次锁存、三次回卷、末两次清零。
    def now():
        index = next(clock)
        return index * (10.0 if fault == "window" else 0.001) + (
            0.2 if fault == "reset_window" and index == 10 else 0
        )

    monkeypatch.setattr(timestamp_case, "monotonic", now)
    properties = []
    args = (support, resource, lambda k, v: properties.append((k, v)), divisor)
    if fault:
        with pytest.raises(AssertionError):
            timestamp_case.test_can_p1_013_internal_timestamp(*args)
    else:
        timestamp_case.test_can_p1_013_internal_timestamp(*args)
        assert not target.responses
        commands = [request["command"] for request in target.requests]
        assert commands.count(63) == 1 and commands.count(31) == 1
        assert commands.count(38) == 3 and commands.count(17) == 3
        assert commands[-1] == 63
        assert dict(properties)["reset_snapshot"]["after"] == 3
        assert len(dict(properties)["timestamp"]) == 3
    expected_stages = 2 if fault == "disabled" else 3
    assert_case_report(properties, "CAN_P1_013", "FAIL" if fault else "PASS", tmp_path)
    assert calls == [("can", 0), ("resource",)] * expected_stages
