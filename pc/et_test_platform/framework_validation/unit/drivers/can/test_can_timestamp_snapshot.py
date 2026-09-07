# CAN时间戳清零快照的固定Wire验证。
# 职责：相邻真实读值、写重试边界和响应范围检查。
# 边界：软件向量不提供计数精度或清零延迟的硬件结论。
# 依赖：真实CanDriver和独立Target替身。

from struct import pack

import pytest
from et_test_platform.core.errors import ProtocolError
from et_test_platform.drivers.can import CanDriver
from et_test_platform.framework_validation.unit.drivers.can.test_can_driver import TargetStub


# 测试Feature：一次清零前后实读值和固定命令。
# 测试方法：注入高计数到非零低计数的Wire，验证不是返回常量零。
# 通过条件：只有一条不可重试命令，完整返回两个实读值。
def test_timestamp_snapshot_golden():
    target = TargetStub([pack("<2I", 0x9234, 3)])
    assert CanDriver(target, 1).timestamp_reset_snapshot(timeout_s=0.2) == (0x9234, 3)
    assert len(target.requests) == 1
    request = target.requests[0]
    assert request["command"] == 63 and request["body"] == b"\x01"
    assert request["timeout_s"] == 0.2 and request["retry_safe"] is False


# 测试Feature：禁止截断16-bit以外的读回或容忍错误长度。
# 测试方法：分别污染两个计数与响应长度。
# 通过条件：所有非法响应均触发协议错误，不能充当硬件低计数。
@pytest.mark.parametrize("words", ((65536, 1), (1, 65536), (1,), (1, 2, 3)))
def test_timestamp_snapshot_invalid(words):
    target = TargetStub([pack(f"<{len(words)}I", *words)])
    with pytest.raises(ProtocolError):
        CanDriver(target, 0).timestamp_reset_snapshot()
