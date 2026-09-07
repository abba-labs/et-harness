# CAN TSU原语的软件合同回归。
# 职责：核对独立Wire向量、非法值和读清命令重试属性。
# 边界：不模拟物理时间基或声明FPGA捕获成功。
# 依赖：pytest、真实CAN Driver和最小Target替身。

from struct import pack

import pytest
from et_test_platform.core.errors import ProtocolError
from et_test_platform.drivers.can import CanDriver, CanTsuConfig, CanTsuLimits
from et_test_platform.framework_validation.unit.drivers.can.test_can_driver import TargetStub


# Watchdog当前计数和配置周期是两个不同字段，不把配置回显当当前值。
def test_ram_watchdog_snapshot_golden() -> None:
    target = TargetStub([bytes.fromhex("10 00 00 00 07 00 00 00")])
    driver = CanDriver(target, 2)
    assert driver.ram_watchdog_get(timeout_s=0.25) == (16, 7)
    assert target.requests[0]["command"] == 97
    assert target.requests[0]["body"] == b"\x02"
    assert target.requests[0]["retry_safe"] is True
    assert target.requests[0]["timeout_s"] == 0.25


# 外部向量SET不重试，GET实读；使用独立常量而非请求回显生成预期。
def test_external_vector_golden() -> None:
    target = TargetStub([b"", bytes.fromhex("EF CD AB 89")])
    driver = CanDriver(target, 2)
    driver.external_vector_set(0x12345678, timeout_s=0.25)
    assert driver.external_vector_get(timeout_s=0.5) == 0x89ABCDEF
    assert [item["command"] for item in target.requests] == [95, 96]
    assert [item["body"] for item in target.requests] == [
        bytes.fromhex("02 78 56 34 12"),
        b"\x02",
    ]
    assert [item["retry_safe"] for item in target.requests] == [False, True]
    assert [item["timeout_s"] for item in target.requests] == [0.25, 0.5]


# 32-bit输入的类型/范围在传输前拒绝，不允许bool伪装计数。
@pytest.mark.parametrize("value", [-1, 0x100000000, True, 1.0])
def test_external_vector_invalid_no_io(value) -> None:
    target = TargetStub()
    with pytest.raises(ValueError):
        CanDriver(target, 0).external_vector_set(value)
    assert target.requests == []


# 每条原语有独立Golden；不使用请求数据生成目标读回。
def test_tsu_golden_and_consume_retry_policy() -> None:
    target = TargetStub(
        [
            b"",
            pack("<4I", 1, 0, 0, 4),
            pack("<3I", 8, 1, 0),
            pack("<2I", 0xA5, 0x81),
            pack("<I", 0x89ABCDEF),
            pack("<I", 0x12345678),
        ]
    )
    driver = CanDriver(target, 2)
    driver.tsu_config_set(CanTsuConfig(True, False, True, 256), timeout_s=0.25)
    assert driver.tsu_config_get() == CanTsuConfig(True, False, False, 4)
    assert driver.tsu_limits_get() == CanTsuLimits(8, True, False)
    assert driver.tsu_flags_get() == (0xA5, 0x81)
    assert driver.tsu_timebase_get() == 0x89ABCDEF
    assert driver.tsu_slot0_consume(timeout_s=0.125) == 0x12345678
    assert [item["command"] for item in target.requests] == [64, 65, 66, 67, 68, 69]
    assert [item["body"] for item in target.requests] == [
        bytes.fromhex("02 01000000 00000000 01000000 00010000"),
        b"\x02",
        b"\x02",
        b"\x02",
        b"\x02",
        b"\x02",
    ]
    assert [item["retry_safe"] for item in target.requests] == [
        False,
        True,
        True,
        True,
        True,
        False,
    ]
    assert target.requests[0]["timeout_s"] == 0.25
    assert target.requests[-1]["timeout_s"] == 0.125


# 非法输入必须在I/O之前失败，包括bool伪装整数分频。
@pytest.mark.parametrize(
    "config",
    [
        CanTsuConfig(1, False, False, 4),
        CanTsuConfig(True, 1, False, 4),
        CanTsuConfig(True, False, 1, 4),
        CanTsuConfig(True, False, False, 0),
        CanTsuConfig(True, False, False, 257),
        CanTsuConfig(True, False, False, True),
        CanTsuConfig(True, False, False, 4.0),
    ],
)
def test_tsu_invalid_input_no_io(config) -> None:
    target = TargetStub()
    with pytest.raises(ValueError):
        CanDriver(target, 0).tsu_config_set(config)
    assert target.requests == []


# 非法实际响应不被解释成默认能力或空标志。
@pytest.mark.parametrize(
    "method,words",
    [
        ("tsu_config_get", (2, 0, 0, 4)),
        ("tsu_config_get", (1, 2, 0, 4)),
        ("tsu_config_get", (1, 0, 2, 4)),
        ("tsu_config_get", (1, 0, 0, 0)),
        ("tsu_config_get", (1, 0, 0, 257)),
        ("tsu_limits_get", (0, 1, 0)),
        ("tsu_limits_get", (32, 1, 0)),
        ("tsu_limits_get", (8, 2, 0)),
        ("tsu_limits_get", (8, 1, 2)),
        ("tsu_flags_get", (0x10000, 0)),
        ("tsu_flags_get", (0, 0x10000)),
        ("tsu_slot0_consume", ()),
    ],
)
def test_tsu_invalid_response(method, words) -> None:
    target = TargetStub([pack(f"<{len(words)}I", *words)])
    with pytest.raises(ProtocolError):
        getattr(CanDriver(target, 0), method)()
    assert len(target.requests) == 1
