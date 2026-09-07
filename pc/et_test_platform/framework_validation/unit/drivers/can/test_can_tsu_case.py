# CAN TSU Formal Case的软件合同回归。
# 职责：用独立固定响应验证New/Lost、单槽读清、输入/ATB/TS0三点比较和清理。
# 边界：不模拟片内真实连接或物理计数速度，不产生HIL证据。
# 依赖：真实Case/CanDriver及严格命令替身。

from dataclasses import replace
from struct import pack, unpack
from types import SimpleNamespace

import pytest
from et_test_platform.drivers.can import CanDriver
from et_test_platform.framework_validation.unit.drivers.can.test_can_case_flow import dependencies
from et_test_platform.test_cases.can.test_can_p1_tsu import test_can_p1_018_tsu_capture as run_case


# 固定向量独立于TX请求；只接受本Case已定义命令，未知操作立即失败。
class TsuTarget:
    def __init__(self, timebase, fault, sof):
        self.external = timebase != "internal"
        self.vector = timebase if isinstance(timebase, int) else 20
        self.fault = fault
        self.sof_support = sof
        self.sof = 0
        self.initializing = 1
        self.tx_count = 0
        self.consumed = 0
        self.atb_reads = 0
        self.vector_reads = 0
        self.requests = []
        self.config_count = 0
        self.rate = False
        self.divisor = 4

    # 响应遵守真实Driver的Wire长度；不回显配置作为硬件值。
    def request(self, service, command, **kwargs):
        assert service == 0x010C and kwargs["body"][0] == 0
        self.requests.append({"command": int(command), **kwargs})
        body = kwargs["body"][1:]
        values = ()
        if command == 1:
            self.initializing = unpack("<I", body)[0]
        elif command == 2:
            values = (self.initializing,)
        elif command == 66:
            values = (4, 1, int(self.sof_support))
        elif command == 64:
            enabled, external, self.sof, self.divisor = unpack("<4I", body)
            assert (enabled, external) == (1, int(self.external))
            assert self.divisor in (4, 16)
            self.config_count += 1
            self.rate = self.config_count > (2 if self.sof_support else 1)
            assert not self.external or not self.rate
            self.tx_count = self.consumed = self.atb_reads = 0
        elif command == 65:
            values = (
                0 if self.fault == "config" else 1,
                int(self.external),
                self.sof,
                self.divisor,
            )
        elif command == 95:
            assert self.initializing == 1
            assert unpack("<I", body)[0] in (self.vector, 0x76543210)
        elif command == 96:
            self.vector_reads += 1
            values = (
                0x76543210 if self.vector_reads == 1 else self.vector ^ int(self.fault == "vector"),
            )
        elif command == 18:
            assert body == pack("<I", 1)
            self.tx_count += 1
        elif command == 19:
            values = (0, 1, 0, 1, 0, 0, 0)
        elif command == 67:
            values = self.flags_response()
        elif command == 68:
            if self.rate:
                rate_after = 2000 if self.divisor == 4 or self.fault == "divider" else 1250
                values = ((1000, rate_after)[self.atb_reads],)
            else:
                values = (
                    (self.vector ^ int(self.fault == "atb"))
                    if self.external
                    else (100, 150, 200, 250)[self.atb_reads],
                )
            self.atb_reads += 1
        elif command == 69:
            assert self.tx_count in (2, 10)
            values = (self.vector if self.external else (125, 225)[self.consumed],)
            if self.fault == "timestamp":
                values = ((self.vector ^ 1) if self.external else 999,)
            self.consumed += 1
        else:
            assert command in (4, 6, 10, 12, 14, 17, 25, 59)
        return SimpleNamespace(body=pack(f"<{len(values)}I", *values)), None

    # 独立的槽分配/覆盖响应状态机；不从待测Case的Expected反向生成标志。
    def flags_response(self):
        if self.tx_count == 0:
            values = (0, 0)
        elif self.consumed == 0:
            values = (
                8 if self.tx_count == 1 or self.fault == "new" else 9,
                1 if self.fault == "early_lost" else 0,
            )
        elif self.consumed == 1 and self.tx_count == 2:
            values = (8, 0)
        elif self.consumed == 1:
            assert self.tx_count == 10
            values = (15, 0 if self.fault == "lost" else 15)
        else:
            values = (14, 14)
        if self.consumed and self.tx_count == 2 and self.fault == "clear":
            values = (9, 0)
        if self.consumed and self.tx_count == 2 and self.fault == "other_clear":
            values = (0, 0)
        return values


# STIMER样本来自预先安排的两个读值，不从CAN写入反向生成。
class TimerSample:
    def __init__(self, timebase=None, fault=None):
        self.calls = []
        if timebase == "internal":
            samples = (100, 110, 1110, 1120)
            if fault == "timer_wrap":
                samples = (100, 110, 1110, 10)
            elif fault == "uncertainty":
                samples = (100, 900, 1110, 2000)
            self.values = iter(samples * 2)
        else:
            self.values = iter((10, 20))

    def stop(self):
        self.calls.append("stop")

    def configure(self, config):
        assert config.period_ticks == 0xFFFFFFFF
        self.calls.append("configure")

    def clear(self):
        self.calls.append("clear")

    def start(self):
        self.calls.append("start")

    def live_count_get(self):
        self.calls.append("read")
        return next(self.values)


# 完整正常矩阵及每个决定性坏值；错误仍恢复向量并尝试所有清理。
@pytest.mark.parametrize("timebase", ["internal", 0x12345678, 0x89ABCDEF, "stimer"])
@pytest.mark.parametrize("sof", [False, True])
@pytest.mark.parametrize(
    "fault", [None, "config", "new", "timestamp", "lost", "early_lost", "clear", "other_clear"]
)
def test_tsu_case_decisive_vectors(timebase, sof, fault):
    support, resource, _, calls = dependencies()
    target = TsuTarget(timebase, fault, sof)
    support = replace(support, can=CanDriver(target, 0))
    timer = TimerSample(timebase)
    properties = []
    args = (
        support,
        (0, timer, SimpleNamespace(maximum_period_ticks=0xFFFFFFFF)),
        resource,
        lambda k, v: properties.append((k, v)),
        timebase,
    )
    if fault:
        with pytest.raises(AssertionError):
            run_case(*args)
    else:
        run_case(*args)
        commands = [item["command"] for item in target.requests]
        rounds = 2 if sof else 1
        assert commands.count(69) == 2 * rounds
        assert commands.count(18) == 10 * rounds + (16 if timebase == "internal" else 0)
        assert commands.count(64) == rounds + (2 if timebase == "internal" else 0)
        assert commands.count(67) == 6 * rounds
        assert dict(properties)["ts0"] != "NOT_OBSERVED"
        assert dict(properties)["flags"]["after"] == (14, 14)
        if timebase == "stimer":
            assert timer.calls[:7] == [
                "stop",
                "configure",
                "clear",
                "start",
                "read",
                "stop",
                "read",
            ]
    assert timer.calls[-1] == "stop"
    assert [item["command"] for item in target.requests[-3:]] == [1, 2, 95]
    assert target.requests[-1]["body"] == bytes.fromhex("00 10 32 54 76")
    assert calls[-1] == ("resource",)


# 相对分频判据必须拒绝分频不生效、参考回卷及过宽的不确定度区间。
@pytest.mark.parametrize("fault", ["divider", "timer_wrap", "uncertainty"])
def test_tsu_relative_rate_rejects_invalid_evidence(fault):
    support, resource, _, calls = dependencies()
    target = TsuTarget("internal", fault, False)
    support = replace(support, can=CanDriver(target, 0))
    timer = TimerSample("internal", fault)
    properties = []
    with pytest.raises(AssertionError):
        run_case(
            support,
            (0, timer, SimpleNamespace(maximum_period_ticks=0xFFFFFFFF)),
            resource,
            lambda k, v: properties.append((k, v)),
            "internal",
        )
    assert target.rate
    assert timer.calls[-1] == "stop" and calls[-1] == ("resource",)


# 外部向量实读与ATB是独立关卡；错误连接不得到达TX捕获。
@pytest.mark.parametrize("fault", ["vector", "atb"])
def test_tsu_external_route_mismatch_fails_before_capture(fault):
    support, resource, _, calls = dependencies()
    target = TsuTarget(0x12345678, fault, False)
    support = replace(support, can=CanDriver(target, 0))
    timer = TimerSample()
    with pytest.raises(AssertionError):
        run_case(
            support,
            (0, timer, SimpleNamespace(maximum_period_ticks=0xFFFFFFFF)),
            resource,
            lambda k, v: None,
            0x12345678,
        )
    assert 18 not in [item["command"] for item in target.requests]
    assert 69 not in [item["command"] for item in target.requests]
    assert calls[-1] == ("resource",)
