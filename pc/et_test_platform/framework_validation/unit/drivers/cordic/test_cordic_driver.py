# CORDIC Contract/Codec/Driver 单元测试。
#
# 职责：固定命令、枚举、Wire 布局、Runtime Capability 和原子 Driver 行为。
# 边界：不访问真实硬件，不实现数值 Golden，不替代 Formal HIL Case。
# 依赖：仅依赖 pytest、测试替身和 CORDIC Driver package。

from __future__ import annotations

import struct

import pytest

from et_test_platform.communication.protocols.et_message import ServiceMessage
from et_test_platform.core.errors import ProtocolError
from et_test_platform.drivers.cordic import (
    CordicConfig,
    CordicDriver,
    CordicFeature,
    CordicFunction,
    CordicInputRange,
    CordicIrqEvent,
    CordicNumericMode,
    CordicResultCount,
    CordicStatus,
    CordicWidth,
    CordicWorkMode,
)
from et_test_platform.drivers.cordic.codec import (
    ARGUMENT,
    CAPABILITIES,
    CONFIG,
    IRQ_SNAPSHOT,
    RESULT,
    TIMED_RESULT,
    UINT32,
    ZERO_OVERHEAD,
    decode_capabilities,
    encode_config,
)
from et_test_platform.drivers.cordic.contract import (
    CORDIC_CAPABILITIES_SIZE,
    CORDIC_SERVICE_ID,
    CordicCommand,
)


class _Target:
    def __init__(self) -> None:

        self.calls: list[tuple[int, int, int, bytes, bool]] = []

    def request(
        self,
        service_id: int,
        command_id: int,
        *,
        instance_id: int = 0,
        body: bytes = b"",
        retry_safe: bool = False,
        timeout_s: float | None = None,
    ):

        del timeout_s
        self.calls.append((service_id, command_id, instance_id, body, retry_safe))
        responses = {
            int(CordicCommand.CAPABILITIES_GET): CAPABILITIES.pack(
                1,
                CORDIC_CAPABILITIES_SIZE,
                int(sum(CordicFeature)),
                (1 << len(CordicFunction)) - 1,
                7,
                8,
                int(CordicIrqEvent.ALL),
            ),
            int(CordicCommand.RESULT_GET): RESULT.pack(0x11223344, 0x55667788),
            int(CordicCommand.STATUS_GET): UINT32.pack(int(CordicStatus.COMPLETE)),
            int(CordicCommand.ARGUMENT_COUNT_GET): UINT32.pack(1),
            int(CordicCommand.CONVERSION_STATUS_GET): UINT32.pack(0),
            int(CordicCommand.IRQ_SNAPSHOT_GET): IRQ_SNAPSHOT.pack(2, 2, 3, 2, 2),
            int(CordicCommand.ZERO_OVERHEAD_EXECUTE): RESULT.pack(0xAABBCCDD, 0),
            int(CordicCommand.TEST_EXECUTE_TIMED): TIMED_RESULT.pack(0x12345678, 0x9ABCDEF0, 37),
        }
        return (
            ServiceMessage(
                service_id=service_id,
                command_id=command_id,
                instance_id=instance_id,
                body=responses.get(command_id, b""),
            ),
            object(),
        )


# CORDIC 命令、枚举和位掩码必须与 Firmware 已发布合同保持一致。
def test_cordic_numeric_contract() -> None:

    # 断言：命令连续且所有公开枚举使用稳定数值，禁止重排造成 Wire 漂移。
    assert [int(command) for command in CordicCommand] == list(range(0x0001, 0x0013))
    assert [int(function) for function in CordicFunction] == list(range(9))
    assert [int(mode) for mode in CordicNumericMode] == [0, 1]
    assert [int(width) for width in CordicWidth] == [16, 32]
    assert [int(value) for value in CordicInputRange] == [0, 1]
    assert [int(value) for value in CordicResultCount] == [1, 2]
    assert [int(value) for value in CordicWorkMode] == [0, 1, 2, 3]
    assert int(CordicIrqEvent.ALL) == 0x07


# CORDIC 请求和响应必须保持固定尺寸、字段顺序及小端编码。
def test_cordic_wire_layout_contract() -> None:

    # 断言：Python struct size 与 Firmware Wire 常量一致。
    assert CAPABILITIES.size == CORDIC_CAPABILITIES_SIZE == 16
    assert CONFIG.size == 12
    assert ARGUMENT.size == 8
    assert RESULT.size == 8
    assert UINT32.size == 4
    assert IRQ_SNAPSHOT.size == 20
    assert ZERO_OVERHEAD.size == 12
    assert TIMED_RESULT.size == 12

    # 准备：使用非默认字段固定 CONFIGURE 的每个偏移。
    config = CordicConfig(
        numeric_mode=CordicNumericMode.FLOAT32,
        argument_width=CordicWidth.BITS_16,
        result_width=CordicWidth.BITS_32,
        input_range=CordicInputRange.DIRECT_ANGLE,
        scale=7,
        precision_cycles=8,
        sincos_result_count=CordicResultCount.ONE,
        phase_modulus_result_count=CordicResultCount.TWO,
        hsincos_result_count=CordicResultCount.ONE,
        work_mode=CordicWorkMode.ZERO_OVERHEAD,
    )

    # 断言：尾部两个 reserved byte 保持零，所有字段按冻结顺序编码。
    assert encode_config(config) == struct.pack("<10B2x", 1, 16, 32, 1, 7, 8, 1, 2, 1, 2)


# Runtime Capability 解码必须拒绝未知 Feature、函数和 IRQ 位。
def test_cordic_capabilities_are_strictly_decoded() -> None:

    # 观察：完整有效 Capability 恢复全部函数和硬件上限。
    body = CAPABILITIES.pack(
        1,
        16,
        int(sum(CordicFeature)),
        (1 << len(CordicFunction)) - 1,
        7,
        8,
        int(CordicIrqEvent.ALL),
    )
    capabilities = decode_capabilities(body)
    assert capabilities.functions == tuple(CordicFunction)
    assert capabilities.maximum_scale == 7
    assert capabilities.maximum_precision_cycles == 8

    # 拒绝：未来未知位不能被当前 Driver 静默解释为已支持能力。
    with pytest.raises(ProtocolError, match="unknown feature bits"):
        decode_capabilities(CAPABILITIES.pack(1, 16, 1 << 31, 1, 7, 8, 0x07))
    with pytest.raises(ProtocolError, match="invalid function bits"):
        decode_capabilities(CAPABILITIES.pack(1, 16, 0, 1 << 15, 7, 8, 0x07))
    with pytest.raises(ProtocolError, match="invalid limits or IRQ bits"):
        decode_capabilities(CAPABILITIES.pack(1, 16, 0, 1, 7, 8, 0x80))


# Driver 必须按选中实例发送原子命令，并仅允许只读命令安全重试。
def test_cordic_driver_command_flow() -> None:

    target = _Target()
    cordic = CordicDriver(target, instance_id=2)  # type: ignore[arg-type]

    # 配置：先读取真实能力，再应用完整配置。
    capabilities = cordic.capabilities_get()
    cordic.configure(CordicConfig())

    # 激励：分别执行参数、结果、状态、中断、零开销和目标侧计时操作。
    cordic.argument_submit(CordicFunction.SINCOS, 0x40000000)
    result = cordic.result_get()
    status = cordic.status_get()
    waited_status, poll_count = cordic.wait_status(CordicStatus.COMPLETE)
    cordic.status_clear(CordicStatus.COMPLETE)
    cordic.irq_enable(CordicIrqEvent.CALCULATION_COMPLETE)
    snapshot = cordic.irq_snapshot_get()
    delivered = cordic.wait_irq(
        CordicIrqEvent.CALCULATION_COMPLETE,
        minimum_event_count=3,
    )
    zero_result = cordic.zero_overhead_execute(CordicFunction.ARCTAN, (0x20000000,))
    timed_result = cordic.execute_timed(CordicFunction.SQRT, (0x3F800000,), 128)

    # 断言：结果严格解码，实例不漂移，只有读取类命令携带 retry_safe。
    assert capabilities.functions == tuple(CordicFunction)
    assert result.primary_raw == 0x11223344
    assert status == CordicStatus.COMPLETE
    assert waited_status == CordicStatus.COMPLETE
    assert poll_count == 1
    assert snapshot.event_count == 3
    assert delivered.event_count == 3
    assert zero_result.primary_raw == 0xAABBCCDD
    assert timed_result.primary_raw == 0x12345678
    assert timed_result.elapsed_cycles == 37
    assert all(call[0] == CORDIC_SERVICE_ID and call[2] == 2 for call in target.calls)
    assert target.calls[0][-1] is True
    assert target.calls[1][-1] is False


# Driver 必须在发出硬件请求前拒绝裸整数、越界配置和错误参数数量。
def test_cordic_driver_rejects_invalid_semantics_before_io() -> None:

    target = _Target()
    cordic = CordicDriver(target, instance_id=0)  # type: ignore[arg-type]
    cordic.capabilities_get()

    # 拒绝：枚举类型、硬件上限和操作生命周期必须先在 PC 端闭合。
    with pytest.raises(TypeError, match="numeric_mode"):
        cordic.configure(CordicConfig(numeric_mode=0))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="scale"):
        cordic.configure(CordicConfig(scale=8))
    with pytest.raises(RuntimeError, match="configured"):
        cordic.result_get()

    cordic.configure(CordicConfig())
    with pytest.raises(ValueError, match="requires 2 raw argument"):
        cordic.zero_overhead_execute(CordicFunction.PHASE_MODULUS, (1,))
    with pytest.raises(ValueError, match="unsigned 32-bit"):
        cordic.argument_submit(CordicFunction.SINCOS, -1)


# Driver构造必须由Capability/Fixture显式传入逻辑实例，禁止静默绑定实例0。
def test_cordic_driver_requires_explicit_instance() -> None:

    with pytest.raises(TypeError, match="instance_id"):
        CordicDriver(_Target())  # type: ignore[call-arg]
