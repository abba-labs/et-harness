# CRC P3 Formal Case。
#
# 职责：验证 CRC 长稳、CPU 目标计时和 DMA 目标计时 Feature。
# 边界：最终性能判断只在 PC Case；不使用 ET-Frame 往返时间代替目标周期。
# 依赖：仅依赖 CRC/DMA/SYSCTRL/Resource Driver、已审核 Route 和结果记录器。

from __future__ import annotations

import statistics
from collections.abc import Callable
from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction
from ...drivers.crc import CrcConfig, CrcMode
from ...drivers.crg import CrgPeripheral
from ...drivers.dma import (
    DmaAddressMode,
    DmaConfig,
    DmaIrqEvent,
    DmaTransferType,
    DmaWidth,
)
from ...drivers.sysctrl import DmaRequestRoute
from ...results.recorder import write_json_result
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import (
    CrcDmaSupport,
    CrcSupportFactory,
    calculate_crc_reference,
    make_crc_pattern,
)

pytestmark = [pytest.mark.hardware, pytest.mark.ip("crc")]

_PERFORMANCE_LENGTHS = (256, 4096)
_PERFORMANCE_REPEATS = 3


# =============================================================================
# 长稳与组合稳定性
# =============================================================================


# 测试 Feature：
# CRC 在连续确定性输入和配置变化下的长期稳定性。
#
# 测试方法：
# 1. 固定生成规则构造 20 轮不同长度、Seed 和 CRC32 配置。
# 2. 同一 Module 生命周期内逐轮重新 Configure、Calculate 并记录结果。
# 3. 每轮立即比较独立 Golden 和 Length 终态，首个错误直接终止并保留轮次参数。
#
# 通过条件：
# 1. 20 轮硬件结果全部精确等于各自 PC Golden。
# 2. 每轮 Remaining Input Count 都为零，首个差异由 pytest 保留现场。
# 3. 轮次、长度、Seed、配置和结果全部进入结构化证据，可按固定规则复现失败。
def test_crc_p3_001_deterministic_long_stability(
    crc_support_for: CrcSupportFactory,
    crc_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：固定轮数和 Payload 最大长度，保证压力有界可复现。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CRC, instance=crc_instance_id)
    resource_driver.reset()

    support = crc_support_for(crc_instance_id)
    rounds = 20
    maximum_length = 257
    records: list[dict[str, object]] = []
    resource_ready = False
    crc_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if crc_enabled:
            actions.append(("CRC module disable", support.crc.disable))
        if resource_ready:
            actions.append(("Resource pool reset", support.resource.reset))
        return tuple(actions)

    try:
        with case_cleanup_scope(cleanup_actions):
            # 资源：重置独占池并创建足够大的 Buffer，逐轮覆盖实际输入范围。
            support.resource.reset()
            resource_ready = True
            source = support.resource.create(maximum_length, alignment=4)

            # 生命周期：显式启用 CRC，整个稳定性 Case 复用同一模块会话。
            support.crc.enable()
            crc_enabled = True

            # 遍历：每轮从 index 确定生成配置、长度和 Payload。
            for index in range(rounds):
                length_bytes = 17 + ((index * 37) % (maximum_length - 16))
                payload = make_crc_pattern(length_bytes, seed=0xC3000000 + index)
                config = CrcConfig(
                    mode=CrcMode.CRC32,
                    polynomial=(0x04C11DB7, 0x1EDC6F41)[index % 2],
                    initial_value=(0xFFFFFFFF, 0x13579BDF)[index % 2],
                    ref_in=bool(index & 1),
                    ref_out=bool(index & 2),
                    byte_swap=True,
                )
                expected = calculate_crc_reference(config, payload)

                # 执行：覆盖 Resource、重新配置并完成一轮同步计算。
                support.resource.write(source, payload)
                support.crc.configure(config)
                measured = support.crc.calculate(source.address, length_bytes)

                # 证据：本轮配置/Oracle与DUT Result/LENGTH在断言前完整保存。
                record_property("round_index", index)
                record_property("length_bytes", length_bytes)
                record_property("polynomial", config.polynomial)
                record_property("initial_value", config.initial_value)
                record_property("expected_crc", expected)
                record_observation(
                    record_property,
                    key="actual_crc",
                    value=measured.result,
                    source="dut",
                    endpoint="RESULT.CRC",
                )
                record_observation(
                    record_property,
                    key="remaining_input_count",
                    value=measured.remaining_input_count,
                    source="dut",
                    endpoint="LENGTH.REMAINING_INPUT_COUNT",
                )
                records.append(
                    {
                        "index": index,
                        "length_bytes": length_bytes,
                        "polynomial": config.polynomial,
                        "initial_value": config.initial_value,
                        "expected": expected,
                        "actual": measured.result,
                        "remaining_input_count": measured.remaining_input_count,
                    }
                )

                # 断言：每轮立即执行强 Oracle，首个失败不会被后续轮覆盖。
                assert measured.result == expected
                assert measured.remaining_input_count == 0
    finally:
        # Evidence Closure：中途失败也发布一次已形成的完整轮次 Snapshot。
        write_json_result(
            et_artifact_dir / "crc_p3_001_deterministic_long_stability.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "crc_p3_001",
                "rounds": rounds,
                "completed_rounds": len(records),
                "records": records,
            },
        )


# =============================================================================
# CPU 目标侧性能
# =============================================================================


# 测试 Feature：
# CRC32 CPU 输入路径的目标侧 DWT 周期测量。
#
# 测试方法：
# 1. 为 256/4096 Byte 输入分别执行三次 Firmware 原子计时命令。
# 2. 每次同时核对 CRC Golden、Measured Bytes 和正周期，再计算中位数。
# 3. 保存六次目标侧原始周期，不用 PC 串口往返时间或单次极值替代性能事实。
#
# 通过条件：
# 1. 六次 CRC 均精确正确，Cycles>0 且 Measured Bytes 等于请求。
# 2. 4096 Byte 中位周期大于 256 Byte，不设置跨芯片绝对阈值。
# 3. 每档三次测量均有效，不允许以部分成功或零周期样本参与中位数计算。
def test_crc_p3_002_cpu_throughput(
    crc_support_for: CrcSupportFactory,
    crc_instance_id: int,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：固定 CRC32 配置和两档确定性输入。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.CRC, instance=crc_instance_id)
    resource_driver.reset()

    support = crc_support_for(crc_instance_id)
    assert support.runtime.max_calculate_bytes >= max(_PERFORMANCE_LENGTHS)
    config = CrcConfig(
        mode=CrcMode.CRC32,
        polynomial=0x04C11DB7,
        initial_value=0xFFFFFFFF,
        byte_swap=True,
    )
    measurements: dict[int, list[int]] = {}
    records: list[dict[str, object]] = []
    short_median: float | None = None
    long_median: float | None = None
    resource_ready = False
    crc_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if crc_enabled:
            actions.append(("CRC module disable", support.crc.disable))
        if resource_ready:
            actions.append(("Resource pool reset", support.resource.reset))
        return tuple(actions)

    try:
        with case_cleanup_scope(cleanup_actions):
            # 资源：重置独占池，两档输入分别创建对齐 Resource。
            support.resource.reset()
            resource_ready = True

            # 生命周期：显式启用 CRC，整个性能 Case 共享同一模块会话。
            support.crc.enable()
            crc_enabled = True
            support.crc.configure(config)

            # 遍历：先长度后重复次数，所有输入和 Golden 都可复现。
            for length_bytes in _PERFORMANCE_LENGTHS:
                payload = make_crc_pattern(length_bytes, seed=0xC3020000 + length_bytes)
                expected = calculate_crc_reference(config, payload)
                source = support.resource.create(length_bytes, alignment=4)
                support.resource.write(source, payload)
                cycles: list[int] = []
                measurements[length_bytes] = cycles

                # 重复：三次调用都由目标 DWT 返回硬件执行周期。
                for repeat in range(_PERFORMANCE_REPEATS):
                    measured = support.crc.calculate_timed(source.address, length_bytes)

                    # 证据：功能结果和目标侧周期在决定性断言前进入Canonical Result。
                    record_property("length_bytes", length_bytes)
                    record_property("repeat", repeat)
                    record_property("expected_crc", expected)
                    record_property("measured_bytes", measured.measured_bytes)
                    record_observation(
                        record_property,
                        key="actual_crc",
                        value=measured.result,
                        source="dut",
                        endpoint="RESULT.CRC",
                    )
                    record_observation(
                        record_property,
                        key="elapsed_cycles",
                        value=measured.elapsed_cycles,
                        source="dut",
                        endpoint="TIMING.CYCLE_COUNT",
                    )
                    cycles.append(measured.elapsed_cycles)
                    records.append(
                        {
                            "length_bytes": length_bytes,
                            "repeat": repeat,
                            "expected": expected,
                            "actual": measured.result,
                            "measured_bytes": measured.measured_bytes,
                            "elapsed_cycles": measured.elapsed_cycles,
                            "cycles_per_byte": measured.elapsed_cycles / length_bytes,
                        }
                    )

                    # 断言：每次计时同时保持功能正确和测量边界有效。
                    assert measured.result == expected
                    assert measured.measured_bytes == length_bytes
                    assert measured.elapsed_cycles > 0

        # 汇总断言：两档必须各有三次有效样本，且长输入中位周期更大。
        assert all(
            len(measurements.get(length, ())) == _PERFORMANCE_REPEATS
            for length in _PERFORMANCE_LENGTHS
        )
        short_median = statistics.median(measurements[_PERFORMANCE_LENGTHS[0]])
        long_median = statistics.median(measurements[_PERFORMANCE_LENGTHS[1]])
        record_property("median_cycles_256", short_median)
        record_property("median_cycles_4096", long_median)
        assert long_median > short_median
    finally:
        # Evidence Closure：两个中位数字段始终存在，失败路径使用null而不是删除报告路径。
        median_cycles: dict[str, float | None] = {
            str(_PERFORMANCE_LENGTHS[0]): short_median,
            str(_PERFORMANCE_LENGTHS[1]): long_median,
        }
        write_json_result(
            et_artifact_dir / "crc_p3_002_cpu_throughput.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "crc_p3_002",
                "records": records,
                "median_cycles": median_cycles,
            },
        )


# =============================================================================
# DMA 目标侧性能
# =============================================================================


# 测试 Feature：
# CRC32 DMA 输入路径从 Channel Start 到 Transfer IRQ 的目标侧 DWT 周期。
#
# 测试方法：
# 1. 显式配置 CRC、SYSCTRL、DMA Channel 和 TRANSFER_DONE IRQ。
# 2. 对 256/4096 Byte 各执行三次 Timed Start，读取 DMA Timing 和 CRC Result。
# 3. 每轮重置 Length 和 IRQ 结果，并同时保存 DMA 终态、CRC 结果和目标侧周期。
#
# 通过条件：
# 1. 六次 DMA 均完成、Channel Free、CRC 等于 Golden且周期大于零。
# 2. 4096 Byte 中位周期大于 256 Byte，不减固定 ISR 修正常数。
# 3. Timing Snapshot 必须属于当前 Channel，且跨 IP Route 在 Case 退出时按逆序释放。
def test_crc_p3_003_dma_throughput(
    crc_dma_support: CrcDmaSupport,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：取得已审核 Route 和四个单 IP Driver。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=crc_dma_support.route.controller)
    crg_driver.reset(
        CrgPeripheral.CRC,
        instance=crc_dma_support.crc_support.instance_id,
    )
    resource_driver.reset()

    support = crc_dma_support
    crc_support = support.crc_support
    resource = crc_support.resource
    crc = crc_support.crc
    dma = support.dma
    sysctrl = support.sysctrl
    route = support.route
    config = CrcConfig(
        mode=CrcMode.CRC32,
        polynomial=0x04C11DB7,
        initial_value=0xFFFFFFFF,
        byte_swap=True,
    )
    measurements: dict[int, list[int]] = {}
    records: list[dict[str, object]] = []
    short_median: float | None = None
    long_median: float | None = None
    channel: int | None = None
    resource_ready = False
    crc_enabled = False
    controller_enabled = False
    route_configured = False
    channel_configured = False
    irq_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if irq_enabled:
            actions.append(
                (
                    "DMA timing IRQ disable",
                    lambda: dma.irq_disable(DmaIrqEvent.TRANSFER_DONE),
                )
            )
        if channel_configured and channel is not None:
            actions.append(("DMA channel stop", lambda: dma.stop(channel)))
            actions.append(("DMA channel deconfigure", lambda: dma.deconfigure(channel)))
        if route_configured:
            actions.append(
                (
                    "SYSCTRL CRC DMA route release",
                    lambda: sysctrl.release_dma_request(route.controller, route.interface),
                )
            )
        if controller_enabled:
            actions.append(("DMA controller disable", dma.controller_disable))
        if crc_enabled:
            actions.append(("CRC module disable", crc.disable))
        if resource_ready:
            actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    try:
        with case_cleanup_scope(cleanup_actions):
            # 资源：重置独占池，并为两档 Payload 创建独立对齐 Buffer。
            resource.reset()
            resource_ready = True
            sources = {}

            # 准备输入：两档 Payload 各自写入独立对齐 Resource。
            for length_bytes in _PERFORMANCE_LENGTHS:
                payload = make_crc_pattern(length_bytes, seed=0xC3030000 + length_bytes)
                source = resource.create(length_bytes, alignment=4)
                resource.write(source, payload)
                sources[length_bytes] = (
                    source,
                    payload,
                    calculate_crc_reference(config, payload),
                )

            channel = dma.find_free_channel()

            # 生命周期：显式启用 CRC 和 DMA Controller。
            crc.enable()
            crc_enabled = True
            crc.configure(config)
            dma.controller_enable()
            controller_enabled = True

            # 路由：配置经能力映射取得的 DMA 请求路由。
            sysctrl.configure_route(
                DmaRequestRoute(route.controller, route.interface, route.request_id)
            )
            route_configured = True

            # 遍历：每档长度独立配置 DMA Transfer Count。
            for length_bytes in _PERFORMANCE_LENGTHS:
                source, _payload, expected = sources[length_bytes]
                dma_config = DmaConfig(
                    channel=channel,
                    source_address=source.address,
                    destination_address=route.peripheral_address,
                    transfer_count=length_bytes // 4,
                    transfer_type=DmaTransferType.MEMORY_TO_PERIPHERAL,
                    source_width=DmaWidth.BITS_32,
                    destination_width=DmaWidth.BITS_32,
                    source_address_mode=DmaAddressMode.INCREMENT,
                    destination_address_mode=DmaAddressMode.FIXED,
                    destination_interface=route.interface,
                )
                cycles: list[int] = []
                measurements[length_bytes] = cycles

                # 重复：每轮重建 Channel 和 IRQ，避免继承上轮硬件状态。
                for repeat in range(_PERFORMANCE_REPEATS):
                    crc.configure(config)
                    crc.data_length_set(length_bytes)
                    dma.irq_result_clear()
                    dma.configure(dma_config)
                    channel_configured = True
                    dma.irq_enable(
                        channel,
                        DmaIrqEvent.TRANSFER_DONE,
                        priority=4,
                    )
                    irq_enabled = True

                    # 刺激：目标侧开始计时并等待同一 Channel 的完成与 Free 终态。
                    dma.start_timed(channel)
                    timing = dma.wait_timing_complete(channel)
                    channel_status = dma.wait_channel_free(channel)
                    actual = crc.result_get()

                    # 观测完成后立即撤销本轮 IRQ 与 Channel，下一轮从干净状态开始。
                    dma.irq_disable(DmaIrqEvent.TRANSFER_DONE)
                    irq_enabled = False
                    dma.stop(channel)
                    dma.deconfigure(channel)
                    channel_configured = False

                    # 证据：目标周期、DMA终态和CRC Result在断言前按来源分开保存。
                    record_property("length_bytes", length_bytes)
                    record_property("repeat", repeat)
                    record_property("expected_crc", expected)
                    record_observation(
                        record_property,
                        key="timing_complete",
                        value=timing.complete,
                        source="dut",
                        endpoint="DMA_TIMING.COMPLETE",
                    )
                    record_observation(
                        record_property,
                        key="channel_free",
                        value=channel_status.is_free,
                        source="dut",
                        endpoint="DMA_CHANNEL_STATUS.FREE",
                    )
                    record_observation(
                        record_property,
                        key="actual_crc",
                        value=actual,
                        source="dut",
                        endpoint="RESULT.CRC",
                    )
                    record_observation(
                        record_property,
                        key="elapsed_cycles",
                        value=timing.elapsed_cycles,
                        source="dut",
                        endpoint="TIMING.CYCLE_COUNT",
                    )
                    cycles.append(timing.elapsed_cycles)
                    records.append(
                        {
                            "length_bytes": length_bytes,
                            "repeat": repeat,
                            "timing_complete": timing.complete,
                            "channel_free": channel_status.is_free,
                            "expected": expected,
                            "actual": actual,
                            "elapsed_cycles": timing.elapsed_cycles,
                            "cycles_per_byte": timing.elapsed_cycles / length_bytes,
                        }
                    )

                    # 断言：功能、终态和计时事实必须在同一轮成立。
                    assert timing.complete
                    assert timing.elapsed_cycles > 0
                    assert channel_status.is_free
                    assert actual == expected

        # 汇总断言：两档必须各有三次有效样本，且长输入中位周期更大。
        assert all(
            len(measurements.get(length, ())) == _PERFORMANCE_REPEATS
            for length in _PERFORMANCE_LENGTHS
        )
        short_median = statistics.median(measurements[_PERFORMANCE_LENGTHS[0]])
        long_median = statistics.median(measurements[_PERFORMANCE_LENGTHS[1]])
        record_property("median_cycles_256", short_median)
        record_property("median_cycles_4096", long_median)
        assert long_median > short_median
    finally:
        # Evidence Closure：两个中位数字段始终存在，失败路径使用null而不是删除报告路径。
        median_cycles: dict[str, float | None] = {
            str(_PERFORMANCE_LENGTHS[0]): short_median,
            str(_PERFORMANCE_LENGTHS[1]): long_median,
        }
        write_json_result(
            et_artifact_dir / "crc_p3_003_dma_throughput.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "crc_p3_003",
                "controller": route.controller,
                "channel": channel,
                "interface": route.interface,
                "request_id": route.request_id,
                "peripheral_address": route.peripheral_address,
                "address_evidence": route.address_evidence,
                "request_evidence": route.request_evidence,
                "records": records,
                "median_cycles": median_cycles,
            },
        )
