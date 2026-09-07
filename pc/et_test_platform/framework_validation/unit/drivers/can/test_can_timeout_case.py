# CAN Timeout四源Case的独立Wire回归。
# 职责：验证自然IRQ、源隔离、重装和禁止窗口的强断言。
# 边界：软件向量不模拟真实计时或ISR，不构成硬件PASS。
# 依赖：真实Case/Driver与独立响应流。

from struct import pack
from types import SimpleNamespace

import pytest
from et_test_platform.drivers.can import CanTimeoutSource
from et_test_platform.framework_validation.unit.drivers.can.test_can_case_flow import (
    assert_case_report,
    dependencies,
)
from et_test_platform.test_cases.can import test_can_p1_timeout as timeout_case


# 测试Feature：四种控制源完整链路和各阶段首错拒绝。
# 测试方法：分别污染配置、到期计数、ISR源、禁用IRQ、非目标FIFO和重装值。
# 通过条件：四种正常场景完整消费向量；各坏值触发失败且执行IRQ停止/复位。
@pytest.mark.parametrize(
    "source,fault",
    [
        (source, fault)
        for source in CanTimeoutSource
        for fault in (
            None,
            "config",
            "expired",
            "latched",
            "negative_irq",
            "negative_count",
            "leak",
            "reload",
        )
    ]
    + [
        (source, "frame")
        for source in (CanTimeoutSource.TX_EVENT, CanTimeoutSource.RX0, CanTimeoutSource.RX1)
    ],
)
def test_timeout_case_vectors(source, fault, monkeypatch, tmp_path):
    support, resource, target, calls = dependencies()
    support.mapping.CAN_EXT_FILTER_BYTES = 8
    target.responses = [b"", pack("<I", 1)] + [b""] * 6
    irq = 1 << 18
    for stage in ("baseline", "enabled", "disabled"):
        enabled = stage == "enabled"
        actual_source = (int(source) + 1) % 4 if fault == "config" and enabled else int(source)
        target.responses += [
            b"",
            b"",
            pack("<I", 1),
            b"",
            pack("<11I", 1, 0, 1, 1, actual_source, 1000, int(enabled), 1, 1, 2, 2),
            b"",
            pack("<I", 0),
            b"",
        ]
        if enabled:
            target.responses.append(pack("<2I", 0, 997) if source == 0 else pack("<I", 1000))
        target.responses.append(b"")
        stimulated = source != 0 and stage != "baseline"
        if stimulated:
            target.responses += [b"", b"", pack("<7I", 0, 1, 0, 1, 0, 0, 0)]
        fills = [
            int(stimulated and source == 2),
            int(stimulated and source == 3),
            int(stimulated and source == 1),
        ]
        if fault == "leak" and enabled:
            fills[1 if source == 2 else 0] = 1
        target.responses += [pack("<5I", fill, 0, fill, 0, 0) for fill in fills]
        if enabled:
            target.responses += [
                pack("<4I", irq, 0, 0, 1),
                pack("<8I", irq, irq, 0 if fault == "latched" else irq, 1, 0, 0, 1, 0),
                pack(
                    "<I",
                    (1001 if fault == "expired" else 642)
                    if source == 0
                    else int(fault == "expired"),
                ),
            ]
        else:
            target.responses += [
                pack("<I", 1000),
                pack("<4I", irq if fault == "negative_irq" and stage == "disabled" else 0, 0, 0, 1),
                bytes(32),
                pack("<I", 999 if fault == "negative_count" and stage == "disabled" else 1000),
            ]
        if stimulated:
            if source == 1:
                target.responses += [
                    pack(
                        "<7I",
                        0x123,
                        0,
                        8,
                        0,
                        2,
                        0x5B if fault == "frame" and stage == "disabled" else 0x5A,
                        0,
                    ),
                    b"",
                ]
            else:
                payload = bytes(
                    ((49 + 17 * i) % 256) ^ (255 if stage == "disabled" else 0) for i in range(8)
                )
                if fault == "frame" and stage == "disabled":
                    payload = payload[:-1] + bytes([payload[-1] ^ 1])
                target.responses += [
                    pack("<8I", 0x123, 0, 8, 0, 0, 0, 8, 0) + payload + bytes(56),
                    b"",
                ]
        if enabled:
            target.responses.append(
                pack("<2I", 0, 0 if fault == "reload" else 997)
                if source == 0
                else pack("<I", 999 if fault == "reload" else 1000)
            )
    original = target.request

    # 停止动作始终返回独立空响应，不让失败后的剩余向量干扰清理动作验证。
    def request(service, command, **kwargs):
        if command == 40:
            target.requests.append({"service": service, "command": command, **kwargs})
            return SimpleNamespace(body=b""), None
        return original(service, command, **kwargs)

    target.request = request
    clock = iter((0.0, 0.01, 1.0, 1.01))
    monkeypatch.setattr(timeout_case, "monotonic", lambda: next(clock))
    properties = []
    args = (support, resource, lambda k, v: properties.append((k, v)), source)
    if fault:
        with pytest.raises(AssertionError):
            timeout_case.test_can_p1_014_timeout_sources(*args)
    else:
        timeout_case.test_can_p1_014_timeout_sources(*args)
        assert not target.responses
        commands = [r["command"] for r in target.requests]
        assert commands.count(49) == 3 and commands.count(41) == 3
        assert commands.count(62) == (2 if source == 0 else 0)
        assert commands.count(17) == (0 if source == 0 else 2)
        assert commands[-1] == 40
        for r in target.requests:
            if r["command"] == 17:
                # STORE_EVENT只能用于Event源，RX源不得同时填充Event FIFO。
                assert int.from_bytes(r["body"][9:13], "little") == (32 if source == 1 else 0)
        assert dict(properties)["irq"][1]["event_count"] == 1
    assert calls == [("can", 0), ("resource",), ("can", 0), ("resource",)]
    assert_case_report(properties, "CAN_P1_014", "FAIL" if fault else "PASS", tmp_path)
