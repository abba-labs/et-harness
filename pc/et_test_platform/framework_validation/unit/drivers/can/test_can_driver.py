# CAN Driver软件合同回归。
# 职责：验证Golden Wire、精确响应、显式动作和Deadline传递。
# 边界：不访问CAN盒子、不形成总线硬件测试结果。
# 依赖：pytest、真实CAN/GPIO/CRG Driver与最小Target替身。

import re
from dataclasses import replace
from pathlib import Path
from struct import pack
from types import SimpleNamespace

import pytest
from et_test_platform.core.errors import ProtocolError
from et_test_platform.drivers.can import (
    CanDriver,
    CanOptions,
    CanPhaseTiming,
    CanRamLayout,
    CanTiming,
    codec,
    contract,
)
from et_test_platform.drivers.can.contract import CanCommand
from et_test_platform.drivers.crg import CrgPeripheral
from et_test_platform.drivers.crg.codec import encode_reset
from et_test_platform.drivers.gpio import GpioDriver, GpioFunction

TIMING = CanTiming(CanPhaseTiming(2, 31, 8, 8), CanPhaseTiming(1, 15, 4, 4))
OPTIONS = CanOptions(True, True, True, False, False, True, False, 20, 10, 100)


# 只保存请求参数并返回显式安排的响应，不模拟期望硬件行为。
class TargetStub:
    # 独立响应队列避免请求自动生成期望，空队列为写命令空响应。
    def __init__(self, responses: list[bytes] | None = None) -> None:
        self.responses = list(responses or [])
        self.requests: list[dict] = []

    # 使用与TargetClient相同的返回形状，记录是否错误启用了写操作重试。
    def request(self, service, command, **kwargs):
        self.requests.append({"service": service, "command": command, **kwargs})
        return SimpleNamespace(body=self.responses.pop(0) if self.responses else b""), None


# 独立Golden为前缀实例2及八个实际计数，不借编码函数构造Expected。
def test_timing_golden_and_explicit_actions() -> None:
    target = TargetStub()
    driver = CanDriver(target, 2)
    assert target.requests == []
    driver.timing_set(TIMING, timeout_s=0.5)
    request = target.requests[0]
    assert request["service"] == 0x010C and request["command"] == 4
    assert request["instance_id"] == 2 and request["retry_safe"] is False
    assert request["timeout_s"] == 0.5
    assert request["body"] == bytes.fromhex(
        "02 02000000 1f000000 08000000 08000000 01000000 0f000000 04000000 04000000"
    )
    assert len(target.requests) == 1


# 身份和实际配置均来自响应，不能在Driver返回最后发送值。
def test_independent_readbacks_and_options_golden() -> None:
    target = TargetStub(
        [
            pack("<2I", 0x12345678, 0x87654321),
            pack("<8I", 2, 31, 8, 8, 1, 15, 4, 4),
            pack("<10I", 1, 1, 0, 0, 0, 1, 0, 20, 10, 100),
            pack("<3I", 127, 127, 255),
        ]
    )
    driver = CanDriver(target, 0)
    assert driver.identity_get().revision == 0x12345678
    assert driver.timing_get() == TIMING
    assert driver.options_get() == replace(OPTIONS, automatic_retry=False)
    assert driver.option_limits_get().ram_watchdog_cycles == 255
    assert all(item["retry_safe"] for item in target.requests)
    assert codec.option_words(OPTIONS) == (1, 1, 1, 0, 0, 1, 0, 20, 10, 100)


# 所有命令的短响应和长响应均失败；包括原本应返回空Body的写命令。
@pytest.mark.parametrize("command", list(CanCommand))
def test_response_exact_length(command: CanCommand) -> None:
    size = contract.RESPONSE_WORDS[command] * contract.WORD.size
    with pytest.raises(ProtocolError):
        codec.decode_response(command, bytes(size + 1))
    if size:
        with pytest.raises(ProtocolError):
            codec.decode_response(command, bytes(size - 1))


# 无效请求在Target接收前拒绝，避免协议整数截断或bool冒充计数。
@pytest.mark.parametrize("instance", [-1, 256, True, "0"])
def test_invalid_instance_has_no_io(instance) -> None:
    target = TargetStub()
    with pytest.raises(ValueError):
        CanDriver(target, instance)
    assert target.requests == []


# 关键语义边界：Boolean不得取2，时序不得为0或让SJW超过段长。
def test_invalid_configuration_has_no_io() -> None:
    target = TargetStub()
    driver = CanDriver(target, 0)
    for phase in (CanPhaseTiming(0, 3, 2, 1), CanPhaseTiming(1, 3, 2, 4)):
        with pytest.raises(ValueError):
            driver.timing_set(CanTiming(phase, TIMING.data))
    with pytest.raises(ValueError):
        driver.options_set(replace(OPTIONS, fd_enabled=2))
    with pytest.raises(ValueError):
        driver.initializing_set(1)
    assert target.requests == []


# 读取非法状态必须暴露ProtocolError，不把任意非零值解释成True。
def test_invalid_response_flags_are_rejected() -> None:
    driver = CanDriver(TargetStub([pack("<I", 2)]), 0)
    with pytest.raises(ProtocolError):
        driver.initializing_get()
    with pytest.raises(ProtocolError):
        codec.decode_options((2, 0, 0, 0, 0, 0, 0, 0, 0, 0))
    with pytest.raises(ProtocolError):
        codec.decode_timing((0,) * 8)


# 等待只读INIT，两次读取共享剩余预算，不重新发START/INIT命令。
def test_wait_uses_one_budget_and_only_queries() -> None:
    target = TargetStub([pack("<I", 0), pack("<I", 1)])
    CanDriver(target, 0).wait_initializing(True, timeout_s=0.5)
    assert [item["command"] for item in target.requests] == [2, 2]
    assert 0 < target.requests[1]["timeout_s"] <= target.requests[0]["timeout_s"] <= 0.5


# 真实C头文件与PC命令号逐个一致，不修改公共Frame定义。
def test_command_ids_match_firmware_header() -> None:
    root = next(
        parent for parent in Path(__file__).resolve().parents if (parent / "firmware").is_dir()
    )
    source = (root / "firmware/services/include/et_can_service.h").read_text(encoding="utf-8")
    found = dict(re.findall(r"ET_CAN_COMMAND_(\w+)\s*=\s*(\d+)u", source))
    assert {name: int(value) for name, value in found.items()} == {
        item.name: item.value for item in CanCommand
    }
    assert "#define ET_CAN_SERVICE_ID 0x010Cu" in source


# GPIO和CRG保持独立Service；连接中的物理值不会被CAN Driver私自设置。
def test_can_support_signals_keep_own_service_wire() -> None:
    target = TargetStub()
    gpio = GpioDriver(target)
    gpio.validate_signal(58, GpioFunction.CAN_RX, 0)
    gpio.configure_signal(59, GpioFunction.CAN_TX, 0)
    assert target.requests[0]["service"] == 0x0014
    assert target.requests[0]["body"] == bytes.fromhex("3a00 0700 0000")
    assert target.requests[1]["body"] == bytes.fromhex("3b00 0800 0000")
    assert int(CrgPeripheral.CAN) == 10
    assert encode_reset(int(CrgPeripheral.CAN), 0) == bytes.fromhex("0a000000")


# RAM配置Golden顺序独立列出；GET使用不同的硬件返回，证明没有请求缓存。
def test_ram_layout_codec_and_independent_readback() -> None:
    words = (0, 2, 8, 2, 24, 2, 0, 0, 64, 168, 2, 1, 184, 4, 2, 0, 472, 4, 2, 1, 760, 64, 64, 64)
    layout = CanRamLayout(
        0,
        2,
        8,
        2,
        24,
        2,
        0,
        False,
        64,
        168,
        2,
        1,
        184,
        4,
        2,
        False,
        472,
        4,
        2,
        True,
        760,
        64,
        64,
        64,
    )
    observed = list(words)
    observed[1] = 1
    target = TargetStub([b"", pack("<24I", *observed), pack("<7I", 16384, 128, 64, 32, 64, 32, 64)])
    driver = CanDriver(target, 2)

    driver.ram_layout_set(layout, timeout_s=0.7)
    assert target.requests[0]["body"] == b"\x02" + pack("<24I", *words)
    assert target.requests[0]["command"] == 10
    assert target.requests[0]["retry_safe"] is False
    assert driver.ram_layout_get().std_count == 1
    assert driver.ram_limits_get().ram_bytes == 16384
    assert len(target.requests) == 3

    with pytest.raises(ValueError):
        driver.ram_layout_set(replace(layout, tx_queue=2))
    assert len(target.requests) == 3
    observed[7] = 2
    with pytest.raises(ProtocolError):
        codec.decode_ram_layout(tuple(observed))
