# pyright: reportMissingImports=none
# CAN ECC中断链测试。
# 职责：Force故障注入、屏蔽、选择性清除与重复投递。
# 边界：不注入RAM物理故障，不配置全局ECC寄存器。
# 依赖：CAN Driver、pytest与选定实例句柄。

import pytest  # pyright: ignore[reportMissingImports] # type: ignore

from ...drivers.can import CanEccSource

pytestmark = [pytest.mark.hardware, pytest.mark.ip("can")]


# 测试 Feature：
# ECC两类源(可纠正/不可纠正)的Force注入、屏蔽解除、中断捕获、单源清除及重复投递。
#
# 测试方法：
# 1. 显式调用can_handle.reset()，建立干净硬件初态。
# 2. 捕获目标源并Force故障，解除Mask等待首次真实ISR事件。
# 3. 执行单源清除并校验状态清零；二次Force验证中断计数递增与同代保持。
#
# 通过条件：
# 1. 首次触发只命中目标源，事件计数为1且无Fault标志。
# 2. 清除后状态复原，二次投递事件计数递增至2且generation不变。
@pytest.mark.parametrize("source", (CanEccSource.CORRECTED, CanEccSource.UNCORRECTED))
def test_can_p2_003_ecc_interrupt_chain(can0, source) -> None:
    # 1）复位：一键重置当前CAN硬件、固件上下文与资源池
    can_handle = can0
    can_handle.reset()

    # 2）IP 配置与激励：捕获目标源、强制注入故障并开启屏蔽
    can_handle.ecc_capture_start(source)
    can_handle.ecc_force(source)
    can_handle.ecc_mask_set(source, False)

    # 3）获取并判断结果：首次投递、选择性清除与二次投递验证
    event1 = can_handle.wait_ecc_event(0, timeout_s=5.0)
    assert event1.event_count == 1 and event1.latched_events == source
    assert event1.fault_flags == event1.unexpected_count == event1.overflow_count == 0

    # 清除目标源
    can_handle.ecc_clear(source)
    state = can_handle.ecc_snapshot_get()
    assert state.status == CanEccSource.NONE

    # 二次投递验证计数递增与同代保持
    can_handle.ecc_force(source)
    event2 = can_handle.wait_ecc_event(1, timeout_s=5.0)
    assert event2.event_count == 2 and event2.latched_events == source
    assert event2.generation == event1.generation
