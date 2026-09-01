# AES P3 Formal Case。
#
# 职责：验证 AES 长稳、CPU 目标端计时和 DMA 目标端计时能力。
# 边界：Case 显式编排跨 IP Driver，不使用 PC 往返时间代替目标周期。
# 依赖：AES、DMA、SYSCTRL、Resource Driver 及独立 AES Golden。

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction
from ...drivers.aes import (
    AesConfig,
    AesDirection,
    AesDmaTransferMode,
    AesEndian,
    AesFeature,
    AesKeySize,
    AesMode,
)
from ...drivers.crg import CrgPeripheral
from ...drivers.dma import (
    DmaAddressMode,
    DmaBurst,
    DmaConfig,
    DmaFeature,
    DmaIrqEvent,
    DmaTransferType,
    DmaWidth,
)
from ...drivers.sysctrl import DmaRequestRoute
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import require_aes_config_supported, require_aes_features_supported
from .aes_helpers import record_result
from .aes_reference import aes_golden

pytestmark = [pytest.mark.hardware, pytest.mark.ip("aes")]

_KEY128 = bytes.fromhex("2b7e151628aed2a6abf7158809cf4f3c")


# 测试 Feature：固定输入集合下 AES 多轮运行的确定性和状态隔离。
#
# 测试方法：
# 1. 固定生成 ECB/CBC/CTR、AES-128/256 共八组输入。
# 2. 每轮重新配置 Key/IV，使用独立 Resource 执行一次 PROCESS。
# 3. 每轮立即比较完整输出、长度和 FINISH，不把错误留到循环结束。
#
# 通过条件：
# 1. 八轮输出均精确等于独立 Golden，produced_bytes 与期望长度一致。
# 2. 每轮 FINISH 均有效，前一轮状态不会污染后一轮。
def test_aes_p3_001_deterministic_long_stability(
    aes_support,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：能力门禁和固定 seed 均在 Case 中可见。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.AES, instance=aes_support.instance_id)
    resource_driver.reset()

    support = aes_support
    require_aes_features_supported(
        support,
        AesFeature.CPU_REGISTER_PATH | AesFeature.STATUS,
    )
    seed = 0x0A350001
    results: list[dict[str, object]] = []
    resource_ready = False
    aes_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if aes_enabled:
            actions.append(("AES module disable", support.aes.disable))
        if resource_ready:
            actions.append(("Resource pool reset", support.resource.reset))
        return tuple(actions)

    try:
        with case_cleanup_scope(cleanup_actions):
            # 资源：重置独占池，循环内为每轮创建独立输入和输出 Buffer。
            support.resource.reset()
            resource_ready = True

            # 遍历：每个 index 对应一组可复现且独立闭合的模式与密钥组合。
            for index in range(8):
                key_size = AesKeySize.AES128 if index % 2 == 0 else AesKeySize.AES256
                mode = (AesMode.ECB, AesMode.CBC, AesMode.CTR)[index % 3]
                key = _KEY128 if key_size is AesKeySize.AES128 else bytes(range(32))
                iv = (
                    None
                    if mode is AesMode.ECB
                    else bytes(((seed + index + item) & 0xFF) for item in range(16))
                )
                config = AesConfig(
                    AesDirection.ENCRYPT,
                    key_size,
                    mode,
                    endian=AesEndian.BIG,
                    ctr_counter=0xFCFDFEFF + index if mode is AesMode.CTR else 0,
                )
                require_aes_config_supported(support, config)

                # 输入：每轮创建独立、可复现的一个 AES Block。
                payload = bytes(((seed + index * 17 + item) & 0xFF) for item in range(16))
                expected = aes_golden(payload, key, iv, config)
                source = support.resource.create(len(payload), alignment=4)
                destination = support.resource.create(len(expected), alignment=4)
                support.resource.write(source, payload)

                # 配置：每轮重新启用 AES，并完整写入配置、Key 和可选 IV。
                support.aes.enable()
                aes_enabled = True
                support.aes.configure(config)
                support.aes.key_set(key, config.key_size)
                if iv is not None:
                    support.aes.iv_set(iv)

                # 刺激：执行当前轮 PROCESS，并只读取真实产生范围。
                result = support.aes.process(
                    source.handle,
                    0,
                    destination.handle,
                    0,
                    len(payload),
                    destination_capacity=destination.size,
                )

                # 观测：每轮硬件输出和 FINISH 在单轮断言前进入 Canonical Result。
                actual = support.resource.read(destination, result.produced_bytes)
                results.append(
                    {
                        "index": index,
                        "key_size": key_size.name,
                        "mode": mode.name,
                        "expected": expected,
                        "actual": actual,
                        "produced_bytes": result.produced_bytes,
                        "finish": result.status.finish,
                    }
                )
                record_property("round_index", index)
                record_property("round_expected_output", expected.hex())
                record_property("round_produced_bytes", result.produced_bytes)
                record_observation(
                    record_property,
                    key="round_actual_output",
                    value=actual.hex(),
                    source="dut",
                    endpoint="RESULT_DOUT[0..3]",
                )
                record_observation(
                    record_property,
                    key="round_finish_status",
                    value=result.status.finish,
                    source="dut",
                    endpoint="STATUS.FINISH",
                )

                # 断言：每轮立即闭合独立 Golden、长度和 FINISH。
                assert actual == expected, f"seed={seed:#x}, index={index}, config={config!r}"
                assert result.produced_bytes == len(expected)
                assert result.status.finish

                # 恢复：当前轮成功后关闭 AES，下一轮从新生命周期开始。
                support.aes.disable()
                aes_enabled = False
    finally:
        # Evidence Closure：无论中途 PASS/FAIL，都只发布一次当前已完成轮次 Snapshot。
        record_result(
            et_artifact_dir,
            "aes_p3_001",
            seed=seed,
            results=results,
            round_count=len(results),
        )


# 测试 Feature：AES CPU 路径的目标端周期测量能力。
#
# 测试方法：
# 1. 对 256-byte 和 1024-byte 输入分别执行一次 TIMED_PROCESS。
# 2. 每档同时读取目标周期、measured_bytes 和完整密文。
# 3. 用独立 Golden 闭合功能正确性，不使用 PC wall-clock。
#
# 通过条件：
# 1. 两档密文均正确，elapsed_cycles 大于零，measured_bytes 等于请求长度。
# 2. 1024-byte 周期大于 256-byte 周期，且 FINISH 有效。
def test_aes_p3_002_cpu_throughput(
    aes_support,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：运行时必须明确声明 CPU、计时和测试扩展能力。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.AES, instance=aes_support.instance_id)
    resource_driver.reset()

    support = aes_support
    require_aes_features_supported(
        support,
        AesFeature.CPU_REGISTER_PATH | AesFeature.TIMED_PROCESS | AesFeature.TEST_EXTENSIONS,
    )
    if not support.runtime.timed_process_supported:
        pytest.skip("skip_by_runtime_feature: timed_process unsupported")
    config = AesConfig(
        AesDirection.ENCRYPT,
        AesKeySize.AES128,
        AesMode.ECB,
        endian=AesEndian.BIG,
    )
    require_aes_config_supported(support, config)
    measurements: dict[int, int] = {}
    details: dict[int, dict[str, object]] = {}
    resource_ready = False
    aes_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if aes_enabled:
            actions.append(("AES module disable", support.aes.disable))
        if resource_ready:
            actions.append(("Resource pool reset", support.resource.reset))
        return tuple(actions)

    try:
        with case_cleanup_scope(cleanup_actions):
            # 资源：重置独占池，两档输入分别使用独立 Buffer。
            support.resource.reset()
            resource_ready = True

            # 遍历：每档使用独立 AES 生命周期，避免上一事务的完成态污染下一档。
            for length in (256, 1024):
                payload = bytes((item * 7 + length) & 0xFF for item in range(length))
                expected = aes_golden(payload, _KEY128, None, config)
                source = support.resource.create(length, alignment=4)
                destination = support.resource.create(len(expected), alignment=4)
                support.resource.write(source, payload)

                # 配置：为当前数据长度重新启用、配置并装载 Key。
                support.aes.enable()
                aes_enabled = True
                support.aes.configure(config)
                support.aes.key_set(_KEY128, config.key_size)

                # 刺激：目标端完成处理并返回硬件周期。
                timed = support.aes.timed_process(
                    source.handle,
                    0,
                    destination.handle,
                    0,
                    length,
                )

                # 观测：每档功能、FINISH 和周期事实先进入 Canonical Result，再做强断言。
                actual = support.resource.read(destination, timed.produced_bytes)
                measurements[length] = timed.elapsed_cycles
                details[length] = {
                    "expected": expected,
                    "actual": actual,
                    "produced_bytes": timed.produced_bytes,
                    "measured_bytes": timed.measured_bytes,
                    "finish": timed.status.finish,
                    "elapsed_cycles": timed.elapsed_cycles,
                }
                record_property("timed_length", length)
                record_property("timed_expected_output", expected.hex())
                record_property("timed_produced_bytes", timed.produced_bytes)
                record_property("timed_measured_bytes", timed.measured_bytes)
                record_observation(
                    record_property,
                    key="timed_actual_output",
                    value=actual.hex(),
                    source="dut",
                    endpoint="RESULT_DOUT[0..3]",
                )
                record_observation(
                    record_property,
                    key="timed_finish_status",
                    value=timed.status.finish,
                    source="dut",
                    endpoint="STATUS.FINISH",
                )
                record_observation(
                    record_property,
                    key="timed_elapsed_cycles",
                    value=timed.elapsed_cycles,
                    source="dut",
                    endpoint="TIMING.CYCLE_COUNT",
                )

                assert actual == expected
                assert timed.elapsed_cycles > 0
                assert timed.measured_bytes == length
                assert timed.status.finish

                # 恢复：当前档测量完成后关闭模块，再进入下一档独立事务。
                support.aes.disable()
                aes_enabled = False
    finally:
        # Evidence Closure：即使某档失败，也发布一次当前已形成的完整测量 Snapshot。
        throughput_order = (
            256 in measurements and 1024 in measurements and measurements[1024] > measurements[256]
        )
        record_result(
            et_artifact_dir,
            "aes_p3_002",
            measurements=measurements,
            details=details,
            throughput_order=throughput_order,
        )

    assert measurements[1024] > measurements[256]


# 测试 Feature：AES FIFO 与 DMA 双向请求的目标端计时数据路径。
#
# 测试方法：
# 1. 从 Capability 和执行映射取得 DMA Controller、Channel 数量及 DMAMUX Route。
# 2. 配置 1024-byte Memory→AES→Memory 流程，输出 Channel 使用目标端计时启动。
# 3. 等待两条 Channel 结束，读取完整输出并与独立 Golden 比较。
#
# 通过条件：
# 1. DMA 计时完成且 elapsed_cycles 大于零，两条 Channel 均回到 Free。
# 2. 1024-byte 输出精确等于 Golden，不以命令 ACK 代替数据验证。
def test_aes_p3_003_dma_throughput(
    aes_dma_support,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：能力决策显式位于 Case，缺失时不执行硬件配置。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=aes_dma_support.route.controller)
    crg_driver.reset(
        CrgPeripheral.AES,
        instance=aes_dma_support.aes_support.instance_id,
    )
    resource_driver.reset()

    support = aes_dma_support
    aes = support.aes_support.aes
    resource = support.aes_support.resource
    dma = support.dma
    sysctrl = support.sysctrl
    route = support.route
    dma_capabilities = dma.capabilities_get()
    required = (
        DmaFeature.PERIPHERAL_TO_MEMORY | DmaFeature.MEMORY_TO_PERIPHERAL | DmaFeature.INTERRUPTS
    )
    if dma_capabilities.features & required != required:
        pytest.skip("skip_by_runtime_feature: DMA timing prerequisites are unavailable")

    # 资源门禁：本 Case 需要两条真实空闲 Channel。
    free_channels = tuple(
        channel
        for channel in range(dma_capabilities.channel_count)
        if dma.channel_status(channel).is_free
    )
    if len(free_channels) < 2:
        pytest.skip("skip_by_runtime_resource: AES timing needs two free DMA channels")
    input_channel, output_channel = free_channels[:2]

    # 输入：单次 1024-byte 测量即可直接验证目标计时 Feature。
    config = AesConfig(
        AesDirection.ENCRYPT,
        AesKeySize.AES128,
        AesMode.ECB,
        endian=AesEndian.LITTLE,
        dma_transfer_mode=AesDmaTransferMode.FIFO,
    )
    payload = bytes((index * 7) & 0xFF for index in range(1024))
    expected = aes_golden(payload, _KEY128, None, config)
    resource_ready = False
    aes_enabled = False
    dma_request_enabled = False
    controller_enabled = False
    input_route_configured = False
    output_route_configured = False
    output_channel_configured = False
    input_channel_configured = False
    irq_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if irq_enabled:
            actions.append(
                (
                    "DMA AES timing IRQ disable",
                    lambda: dma.irq_disable(DmaIrqEvent.TRANSFER_DONE),
                )
            )
        if input_channel_configured:
            actions.append(("DMA input channel stop", lambda: dma.stop(input_channel)))
            actions.append(
                ("DMA input channel deconfigure", lambda: dma.deconfigure(input_channel))
            )
        if output_channel_configured:
            actions.append(("DMA output channel stop", lambda: dma.stop(output_channel)))
            actions.append(
                ("DMA output channel deconfigure", lambda: dma.deconfigure(output_channel))
            )
        if output_route_configured:
            actions.append(
                (
                    "SYSCTRL AES output route release",
                    lambda: sysctrl.release_dma_request(route.controller, route.output_interface),
                )
            )
        if input_route_configured:
            actions.append(
                (
                    "SYSCTRL AES input route release",
                    lambda: sysctrl.release_dma_request(route.controller, route.input_interface),
                )
            )
        if controller_enabled:
            actions.append(("DMA controller disable", dma.controller_disable))
        if dma_request_enabled:
            actions.append(("AES DMA request disable", lambda: aes.dma_request_set(False, False)))
        if aes_enabled:
            actions.append(("AES module disable", aes.disable))
        if resource_ready:
            actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 资源：重置独占池，并创建 1024-byte 输入和输出 Buffer。
        resource.reset()
        resource_ready = True
        source = resource.create(len(payload), alignment=4)
        destination = resource.create(len(expected), alignment=4)
        resource.write(source, payload)
        resource.fill(destination, 0xA5)

        # AES：显式启用模块，配置 FIFO Mode、Key、Length 和双向 DMA Request。
        aes.enable()
        aes_enabled = True
        aes.configure(config)
        aes.key_set(_KEY128, config.key_size)
        aes.data_length_set(len(payload))

        # DMA：启用 Controller，并配置输入、输出两条 DMAMUX Route。
        dma.controller_enable()
        controller_enabled = True
        sysctrl.configure_route(
            DmaRequestRoute(route.controller, route.input_interface, route.input_request_id)
        )
        input_route_configured = True
        sysctrl.configure_route(
            DmaRequestRoute(route.controller, route.output_interface, route.output_request_id)
        )
        output_route_configured = True

        # Channel：构造固定 FIFO 端点的双向 1024-byte 传输。
        output_config = DmaConfig(
            channel=output_channel,
            source_address=route.output_fifo_address,
            destination_address=destination.address,
            transfer_count=len(expected) // 4,
            transfer_type=DmaTransferType.PERIPHERAL_TO_MEMORY,
            source_width=DmaWidth.BITS_32,
            destination_width=DmaWidth.BITS_32,
            source_address_mode=DmaAddressMode.FIXED,
            destination_address_mode=DmaAddressMode.INCREMENT,
            source_burst=DmaBurst.ITEMS_4,
            destination_burst=DmaBurst.ITEMS_4,
            source_interface=route.output_interface,
        )
        input_config = DmaConfig(
            channel=input_channel,
            source_address=source.address,
            destination_address=route.input_fifo_address,
            transfer_count=len(payload) // 4,
            transfer_type=DmaTransferType.MEMORY_TO_PERIPHERAL,
            source_width=DmaWidth.BITS_32,
            destination_width=DmaWidth.BITS_32,
            source_address_mode=DmaAddressMode.INCREMENT,
            destination_address_mode=DmaAddressMode.FIXED,
            source_burst=DmaBurst.ITEMS_4,
            destination_burst=DmaBurst.ITEMS_4,
            destination_interface=route.input_interface,
        )
        dma.configure(output_config)
        output_channel_configured = True
        dma.configure(input_config)
        input_channel_configured = True

        # IRQ：只启用输出 Channel 的 TRANSFER_DONE 目标计时事件。
        dma.irq_enable(output_channel, DmaIrqEvent.TRANSFER_DONE, priority=4)
        irq_enabled = True

        # 刺激：先启动计时输出 Channel，再启动输入 Channel。
        dma.start_timed(output_channel)
        dma.start(input_channel)
        aes.dma_request_set(True, True)
        dma_request_enabled = True
        timing = dma.wait_timing_complete(output_channel)
        input_status = dma.wait_channel_free(input_channel)
        output_status = dma.wait_channel_free(output_channel)

        # 观测：资源池释放前读取完整输出，并在断言前记录目标计时、Channel 与数据事实。
        actual = resource.read(destination, len(expected))
        record_property("expected_output", expected.hex())
        record_observation(
            record_property,
            key="timing_complete",
            value=timing.complete,
            source="dut",
            endpoint="DMA_IRQ.TRANSFER_DONE",
        )
        record_observation(
            record_property,
            key="elapsed_cycles",
            value=timing.elapsed_cycles,
            source="dut",
            endpoint="DMA_TIMING.CYCLE_COUNT",
        )
        record_observation(
            record_property,
            key="input_channel_free",
            value=input_status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.INPUT",
        )
        record_observation(
            record_property,
            key="output_channel_free",
            value=output_status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.OUTPUT",
        )
        record_observation(
            record_property,
            key="actual_output",
            value=actual.hex(),
            source="dut",
            endpoint="DMA_DESTINATION<-RESULT",
        )

    record_result(
        et_artifact_dir,
        "aes_p3_003",
        timing={
            "complete": timing.complete,
            "elapsed_cycles": timing.elapsed_cycles,
        },
        expected=expected,
        actual=actual,
        data_match=actual == expected,
        input_free=input_status.is_free,
        output_free=output_status.is_free,
        input_events=int(input_status.interrupt_events),
        output_events=int(output_status.interrupt_events),
    )
    assert timing.complete
    assert timing.elapsed_cycles > 0
    assert input_status.is_free and output_status.is_free
    assert not (input_status.interrupt_events & DmaIrqEvent.ERROR)
    assert not (output_status.interrupt_events & DmaIrqEvent.ERROR)
    assert actual == expected
