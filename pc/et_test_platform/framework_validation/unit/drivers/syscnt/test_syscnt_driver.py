# SYSCNT软件合同回归。
# 职责：逐命令检查实际Wire、严格边界、原子语义和计时Oracle。
# 边界：无硬件操作，不能作为HIL证据。
# 依赖：SYSCNT Driver、消息Model和纯数学辅助。

from collections import deque
from pathlib import Path

import pytest

from et_test_platform.communication.protocols.et_message import ServiceMessage
from et_test_platform.core.errors import ProtocolError
from et_test_platform.drivers.syscnt import (
    SyscntDriver,
    SyscntHaltPolicy,
    SyscntReferenceSample,
    SyscntView,
    codec,
    contract,
)
from et_test_platform.results.case_report import _human_report_note, _load_specs
from et_test_platform.test_cases.syscnt.syscnt_helpers import halted_counter, timing_bounds


# 严格匹配预定命令，不允许额外配置、隐式复位或写操作重试。
class Target:
    def __init__(self, steps):
        self.steps = deque(steps)

    def request(self, service_id, command_id, *, instance_id, body, timeout_s, retry_safe):
        command, expected, response, safe = self.steps.popleft()
        assert (service_id, instance_id, command_id, body, retry_safe, timeout_s) == (
            contract.SYSCNT_SERVICE_ID,
            2,
            command,
            b"\x02" + expected,
            safe,
            0.5,
        )
        return ServiceMessage(service_id, command_id, instance_id, body=response), object()


# 测试 Feature：九条命令与固件Golden布局一致。
# 测试方法：严格逐项消费真实Driver请求，再核对固件头文件编号。
# 通过条件：无额外命令，字节序、实例前缀、空响应和重试资格完全一致。
def test_syscnt_all_atomic_commands_and_firmware_contract() -> None:
    target = Target(
        [
            (0, b"", bytes.fromhex("3f00000040032020"), True),
            (1, b"\x00", b"", False),
            (2, bytes.fromhex("8877665544332211"), b"", False),
            (3, b"\x01", bytes.fromhex("8877665544332211"), True),
            (4, b"", bytes.fromhex("00010000404b4c00"), True),
            (5, b"\x01", b"", False),
            (6, bytes.fromhex("404b4c00"), b"", False),
            (8, b"\x01", b"", False),
            (7, b"", contract.REFERENCE.pack(5, 8, 10), True),
        ]
    )
    counter = SyscntDriver(target, 2)
    assert counter.capabilities_get(timeout_s=0.5).counter_bits == 64
    counter.enable_set(False, timeout_s=0.5)
    counter.value_load(0x1122334455667788, timeout_s=0.5)
    assert counter.count_get(SyscntView.READ, timeout_s=0.5) == 0x1122334455667788
    assert counter.control_get(timeout_s=0.5).frequency_id_hz == 5_000_000
    counter.halt_policy_set(SyscntHaltPolicy.PAUSE, timeout_s=0.5)
    counter.frequency_id_set(5_000_000, timeout_s=0.5)
    counter.reference_enable_set(True, timeout_s=0.5)
    assert counter.reference_sample_get(timeout_s=0.5) == SyscntReferenceSample(5, 8, 10)
    assert not target.steps
    root = Path(__file__).resolve().parents[6]
    header = (root / "firmware/services/include/et_syscnt_service.h").read_text(encoding="utf-8")
    for command in contract.SyscntCommand:
        assert f"ET_SYSCNT_COMMAND_{command.name} = {int(command)}u" in header


# 测试 Feature：非法参数在发送前失败关闭。
# 测试方法：逐项传入bool、负值、越界值或非枚举配置。
# 通过条件：ValueError且Target未收到任何命令。
@pytest.mark.parametrize(
    "method,value",
    (
        ("value_load", True),
        ("value_load", -1),
        ("value_load", 1 << 64),
        ("frequency_id_set", 0),
        ("frequency_id_set", 1 << 32),
        ("enable_set", 1),
        ("reference_enable_set", None),
        ("halt_policy_set", True),
        ("count_get", 0),
    ),
)
def test_syscnt_rejects_invalid_parameters(method, value) -> None:
    counter = SyscntDriver(Target([]), 2)
    with pytest.raises(ValueError):
        getattr(counter, method)(value, timeout_s=0.5)


# 测试 Feature：严格响应长度、布尔值和保留字节。
# 测试方法：分别注入截断、尾随字节和未知保留值。
# 通过条件：全部抛ProtocolError，不生成看似正常的硬件状态。
@pytest.mark.parametrize(
    "body",
    (b"", bytes(7), bytes(9), bytes.fromhex("0000000100000000"), bytes.fromhex("0200000000000000")),
)
def test_syscnt_control_rejects_bad_wire(body: bytes) -> None:
    with pytest.raises(ProtocolError):
        codec.decode_control(body)


# 测试 Feature：双端夹取计时与参考回绕。
# 测试方法：参考从32-bit末尾跨界，构造精确计时间隔，再注入多次回绕可能性。
# 通过条件：精确间隔落在夹取区间，多回绕歧义明确拒绝。
def test_syscnt_reference_wrap_and_halt_coherence() -> None:
    start = (1 << 32) - 100
    first = SyscntReferenceSample(start, 50, start + 10)
    last = SyscntReferenceSample(
        (start + 25_000_000) % (1 << 32), 12_500_050, (start + 25_000_010) % (1 << 32)
    )
    measured, error, uncertainty = timing_bounds(first, last, 32, 64, 25_000_000, 12_500_000, 1.1)
    assert measured == 1.0 and error < 0.000001 and uncertainty < 0.000001
    with pytest.raises(ValueError, match="wrapped more than once"):
        timing_bounds(first, last, 32, 64, 25_000_000, 12_500_000, 200)
    assert halted_counter((1, 2, 1, 2, 3), 32) == ((1 << 32) | 2, 2, 3)
    with pytest.raises(ValueError, match="torn"):
        halted_counter((1, 2, 2, 2, 3), 32)


# 测试 Feature：SYSCNT备注的数组和参数化聚合形状。
# 测试方法：加载正式文档，分别输入三笔频率、两种暂停参数和20轮计数。
# 通过条件：三类备注可格式化，保留实际值，不出现嵌套数组或缺少Observation。
def test_syscnt_report_real_value_shapes() -> None:
    root = Path(__file__).resolve().parents[6]
    specs = {item["case_id"]: item for item in _load_specs(root / "test_case_doc/syscnt/syscnt.md")}

    # 单次Execution中的数组不应再用all包成二维数组。
    frequency = [12_500_000, 6_250_000, 12_500_000]
    result = {
        "status": "PASS",
        "measurements": {"expected_frequency_id": frequency},
        "observations": [
            {"key": "frequency_id", "value": frequency},
            {"key": "count", "value": [0, 0, 0]},
            {"key": "enabled", "value": [False, False, False]},
        ],
    }
    note = _human_report_note(specs["SYSCNT_P1_002"], [result])
    assert "0x00BEBC20" in note and "0x005F5E10" in note

    # 两个Execution各自一个标量，使用all保留PAUSE和RUN_FREE结果。
    halted = []
    for paused in (True, False):
        halted.append(
            {
                "status": "PASS",
                "observations": [
                    {"key": "cpu_halted", "value": True},
                    {"key": "debug_halted", "value": paused},
                    {"key": "halted_count_before", "value": 100},
                    {"key": "halted_count_after", "value": 100 if paused else 200},
                ],
            }
        )
    assert "0x00000000000000C8" in _human_report_note(specs["SYSCNT_P2_002"], halted)

    # P3完成轮数为标量；同一Observation只出现一次，包含各轮计数。
    repeat = {
        "status": "PASS",
        "measurements": {"round_count": 20},
        "observations": [{"key": "final_count", "value": list(range(1, 21))}],
    }
    assert "0x0000000000000014" in _human_report_note(specs["SYSCNT_P3_001"], [repeat])
