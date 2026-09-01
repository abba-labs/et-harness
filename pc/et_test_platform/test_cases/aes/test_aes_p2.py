# AES P2 Formal Case。
#
# 职责：验证 AES DMA Request Gate、REGISTER 路径和 FIFO 路径。
# 边界：跨 IP 顺序只在 Case 中编排，各 Driver 保持单 IP。
# 依赖：AES、DMA、SYSCTRL、Resource Driver 和已审核执行映射。

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
from ._support import require_aes_config_supported, require_aes_dma_supported
from .aes_helpers import record_result
from .aes_reference import aes_golden

pytestmark = [pytest.mark.hardware, pytest.mark.ip("aes")]

_KEY128 = bytes.fromhex("2b7e151628aed2a6abf7158809cf4f3c")
_BLOCK = bytes.fromhex("6bc1bee22e409f96e93d7e117393172a")
_GATE_CLOSED_STATUS_SAMPLES = 8


# 生成两条 DMA Channel 配置；只组装数据，不执行硬件动作或测试结论。
def _build_dma_configs(
    *,
    route,
    input_channel: int,
    output_channel: int,
    source_address: int,
    destination_address: int,
    transfer_bytes: int,
    register_mode: bool,
) -> tuple[DmaConfig, DmaConfig]:

    input_address = route.input_register_address if register_mode else route.input_fifo_address
    output_address = route.output_register_address if register_mode else route.output_fifo_address
    input_address_mode = DmaAddressMode.INCREMENT if register_mode else DmaAddressMode.FIXED
    output_address_mode = DmaAddressMode.INCREMENT if register_mode else DmaAddressMode.FIXED

    output_config = DmaConfig(
        channel=output_channel,
        source_address=output_address,
        destination_address=destination_address,
        transfer_count=transfer_bytes // 4,
        transfer_type=DmaTransferType.PERIPHERAL_TO_MEMORY,
        source_width=DmaWidth.BITS_32,
        destination_width=DmaWidth.BITS_32,
        source_address_mode=output_address_mode,
        destination_address_mode=DmaAddressMode.INCREMENT,
        source_burst=DmaBurst.ITEMS_4,
        destination_burst=DmaBurst.ITEMS_4,
        source_interface=route.output_interface,
    )
    input_config = DmaConfig(
        channel=input_channel,
        source_address=source_address,
        destination_address=input_address,
        transfer_count=transfer_bytes // 4,
        transfer_type=DmaTransferType.MEMORY_TO_PERIPHERAL,
        source_width=DmaWidth.BITS_32,
        destination_width=DmaWidth.BITS_32,
        source_address_mode=DmaAddressMode.INCREMENT,
        destination_address_mode=input_address_mode,
        source_burst=DmaBurst.ITEMS_4,
        destination_burst=DmaBurst.ITEMS_4,
        destination_interface=route.input_interface,
    )
    return input_config, output_config


# 生成本 Case 对应的 DMAMUX 逆序清理动作，不执行清理。
def _route_cleanup_actions(sysctrl, route) -> tuple[CleanupAction, ...]:

    return (
        (
            "SYSCTRL AES output route release",
            lambda: sysctrl.release_dma_request(route.controller, route.output_interface),
        ),
        (
            "SYSCTRL AES input route release",
            lambda: sysctrl.release_dma_request(route.controller, route.input_interface),
        ),
    )


# 测试 Feature：AES input/output DMA Request Gate 的真实请求传递。
#
# 测试方法：
# 1. 显式读取 DMA Capability 并选择两条空闲 Channel。
# 2. 通过已验证的 REGISTER 数据路径启动双向 DMA，在 Gate 关闭期间连续采样 Channel 状态。
# 3. 打开 AES Request Gate，等待两条 Channel 结束并比较完整输出与独立 Golden。
#
# 通过条件：
# 1. Gate 关闭观测窗口内输入、输出 DMA Channel 始终未完成且没有 ERROR。
# 2. Gate 打开后两条 Channel 均回到 Free，输出 16 字节精确等于 Golden。
def test_aes_p2_001_dma_request_gate(
    aes_dma_support,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：能力门禁和运行时资源决策都在 Case 中可见。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=aes_dma_support.route.controller)
    crg_driver.reset(
        CrgPeripheral.AES,
        instance=aes_dma_support.aes_support.instance_id,
    )
    resource_driver.reset()

    support = aes_dma_support
    config = AesConfig(
        AesDirection.ENCRYPT,
        AesKeySize.AES128,
        AesMode.ECB,
        endian=AesEndian.LITTLE,
        dma_transfer_mode=AesDmaTransferMode.REGISTER,
    )
    require_aes_config_supported(support.aes_support, config)
    require_aes_dma_supported(support.aes_support, config.dma_transfer_mode)
    dma_capabilities = support.dma.capabilities_get()
    required = DmaFeature.MEMORY_TO_PERIPHERAL | DmaFeature.PERIPHERAL_TO_MEMORY
    if dma_capabilities.features & required != required:
        pytest.skip("skip_by_runtime_feature: bidirectional DMA is unavailable")
    free_channels = tuple(
        channel
        for channel in range(dma_capabilities.channel_count)
        if support.dma.channel_status(channel).is_free
    )
    if len(free_channels) < 2:
        pytest.skip("skip_by_runtime_resource: AES DMA needs two free channels")
    input_channel, output_channel = free_channels[:2]
    expected = aes_golden(_BLOCK, _KEY128, None, config)
    resource_ready = False
    aes_enabled = False
    dma_request_enabled = False
    controller_enabled = False
    input_route_configured = False
    output_route_configured = False
    output_channel_configured = False
    input_channel_configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if input_channel_configured:
            actions.append(("DMA input channel stop", lambda: support.dma.stop(input_channel)))
            actions.append(
                ("DMA input channel deconfigure", lambda: support.dma.deconfigure(input_channel))
            )
        if output_channel_configured:
            actions.append(("DMA output channel stop", lambda: support.dma.stop(output_channel)))
            actions.append(
                ("DMA output channel deconfigure", lambda: support.dma.deconfigure(output_channel))
            )
        if output_route_configured:
            actions.append(_route_cleanup_actions(support.sysctrl, support.route)[0])
        if input_route_configured:
            actions.append(_route_cleanup_actions(support.sysctrl, support.route)[1])
        if controller_enabled:
            actions.append(("DMA controller disable", support.dma.controller_disable))
        if dma_request_enabled:
            actions.append(
                (
                    "AES DMA request disable",
                    lambda: support.aes_support.aes.dma_request_set(False, False),
                )
            )
        if aes_enabled:
            actions.append(("AES module disable", support.aes_support.aes.disable))
        if resource_ready:
            actions.append(("Resource pool reset", support.aes_support.resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 资源：重置独占池，并创建输入和输出 Buffer。
        support.aes_support.resource.reset()
        resource_ready = True
        source = support.aes_support.resource.create(len(_BLOCK), alignment=4)
        destination = support.aes_support.resource.create(len(expected), alignment=4)
        support.aes_support.resource.write(source, _BLOCK)
        support.aes_support.resource.fill(destination, 0xA5)
        input_config, output_config = _build_dma_configs(
            route=support.route,
            input_channel=input_channel,
            output_channel=output_channel,
            source_address=source.address,
            destination_address=destination.address,
            transfer_bytes=len(_BLOCK),
            register_mode=True,
        )

        # AES：显式启用模块，配置 REGISTER Mode、Key 和 Length。
        support.aes_support.aes.enable()
        aes_enabled = True
        support.aes_support.aes.configure(config)
        support.aes_support.aes.key_set(_KEY128)
        support.aes_support.aes.data_length_set(len(_BLOCK))

        # DMA：启用 Controller，并配置输入、输出两条执行映射 Route。
        support.dma.controller_enable()
        controller_enabled = True
        support.sysctrl.configure_route(
            DmaRequestRoute(
                support.route.controller,
                support.route.input_interface,
                support.route.input_request_id,
            )
        )
        input_route_configured = True
        support.sysctrl.configure_route(
            DmaRequestRoute(
                support.route.controller,
                support.route.output_interface,
                support.route.output_request_id,
            )
        )
        output_route_configured = True

        # Channel：先配置输出再配置输入，启动时同样保证输出先就绪。
        support.dma.configure(output_config)
        output_channel_configured = True
        support.dma.configure(input_config)
        input_channel_configured = True

        # Gate 关闭观测：启动两条 Channel，但保持 AES DMA Request 关闭并形成有界状态窗口。
        support.dma.start(output_channel)
        support.dma.start(input_channel)
        gate_closed_samples: list[dict[str, object]] = []

        # 状态采样：在固定次数的有界窗口内记录两条 Channel 的 FREE 与错误事件。
        for sample_index in range(_GATE_CLOSED_STATUS_SAMPLES):
            gated_input_status = support.dma.channel_status(input_channel)
            gated_output_status = support.dma.channel_status(output_channel)
            sample = {
                "index": sample_index,
                "input_free": gated_input_status.is_free,
                "output_free": gated_output_status.is_free,
                "input_events": int(gated_input_status.interrupt_events),
                "output_events": int(gated_output_status.interrupt_events),
            }
            gate_closed_samples.append(sample)
            record_property("gate_closed_sample", sample)

        gate_closed_input_active = all(not bool(item["input_free"]) for item in gate_closed_samples)
        gate_closed_output_active = all(
            not bool(item["output_free"]) for item in gate_closed_samples
        )
        gate_closed_no_error = all(
            not (int(item["input_events"]) & int(DmaIrqEvent.ERROR))
            and not (int(item["output_events"]) & int(DmaIrqEvent.ERROR))
            for item in gate_closed_samples
        )
        record_observation(
            record_property,
            key="gate_closed_input_active",
            value=gate_closed_input_active,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.INPUT",
        )
        record_observation(
            record_property,
            key="gate_closed_output_active",
            value=gate_closed_output_active,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.OUTPUT",
        )
        record_observation(
            record_property,
            key="gate_closed_no_error",
            value=gate_closed_no_error,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.INPUT_OUTPUT",
        )
        assert gate_closed_input_active and gate_closed_output_active
        assert gate_closed_no_error

        # Gate 打开刺激：只改变 AES Request Gate，然后等待原 Channel 完成。
        support.aes_support.aes.dma_request_set(True, True)
        dma_request_enabled = True
        input_status = support.dma.wait_channel_free(input_channel)
        output_status = support.dma.wait_channel_free(output_channel)

        # 观测：读取完整 AES 输出，而不是用命令 ACK 代替数据结果。
        actual = support.aes_support.resource.read(destination, len(expected))
        record_property("expected_output", expected.hex())
        record_observation(
            record_property,
            key="gate_open_input_free",
            value=input_status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.INPUT",
        )
        record_observation(
            record_property,
            key="gate_open_output_free",
            value=output_status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.OUTPUT",
        )
        record_observation(
            record_property,
            key="actual_output",
            value=actual.hex(),
            source="dut",
            endpoint="DMA_DESTINATION<-RESULT_DOUT[0..3]",
        )

    # 记录：单次发布完整 Gate 关闭窗口、开启后终态和数据结果。
    record_result(
        et_artifact_dir,
        "aes_p2_001",
        expected=expected,
        actual=actual,
        gate_closed={
            "sample_count": len(gate_closed_samples),
            "input_active": gate_closed_input_active,
            "output_active": gate_closed_output_active,
            "no_error": gate_closed_no_error,
            "samples": gate_closed_samples,
        },
        gate_open={
            "input_free": input_status.is_free,
            "output_free": output_status.is_free,
            "input_events": int(input_status.interrupt_events),
            "output_events": int(output_status.interrupt_events),
        },
    )
    assert input_status.is_free and output_status.is_free
    assert not (input_status.interrupt_events & DmaIrqEvent.ERROR)
    assert not (output_status.interrupt_events & DmaIrqEvent.ERROR)
    assert actual == expected


# 测试 Feature：AES DMA REGISTER Mode 的四个递增 32-bit 寄存器端点。
#
# 测试方法：
# 1. 选择 REGISTER Mode 并显式使用执行映射中的寄存器起始地址。
# 2. 通过双向 DMA 传输一个完整 AES Block，端点按四个寄存器递增。
# 3. 等待 Channel 结束并比较 16 字节输出与独立 Golden。
#
# 通过条件：
# 1. 两条 DMA Channel 均正常完成。
# 2. REGISTER Mode 输出精确等于 Golden。
def test_aes_p2_002_dma_register_mode(
    aes_dma_support,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：使用运行时 Capability 和映射，不写入芯片地址或请求号。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=aes_dma_support.route.controller)
    crg_driver.reset(
        CrgPeripheral.AES,
        instance=aes_dma_support.aes_support.instance_id,
    )
    resource_driver.reset()

    support = aes_dma_support
    config = AesConfig(
        AesDirection.ENCRYPT,
        AesKeySize.AES128,
        AesMode.ECB,
        endian=AesEndian.LITTLE,
        dma_transfer_mode=AesDmaTransferMode.REGISTER,
    )
    require_aes_config_supported(support.aes_support, config)
    require_aes_dma_supported(support.aes_support, config.dma_transfer_mode)
    dma_capabilities = support.dma.capabilities_get()
    required = DmaFeature.MEMORY_TO_PERIPHERAL | DmaFeature.PERIPHERAL_TO_MEMORY
    if dma_capabilities.features & required != required:
        pytest.skip("skip_by_runtime_feature: bidirectional DMA is unavailable")
    free_channels = tuple(
        channel
        for channel in range(dma_capabilities.channel_count)
        if support.dma.channel_status(channel).is_free
    )
    if len(free_channels) < 2:
        pytest.skip("skip_by_runtime_resource: AES DMA needs two free channels")
    input_channel, output_channel = free_channels[:2]
    expected = aes_golden(_BLOCK, _KEY128, None, config)
    resource_ready = False
    aes_enabled = False
    dma_request_enabled = False
    controller_enabled = False
    input_route_configured = False
    output_route_configured = False
    output_channel_configured = False
    input_channel_configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if input_channel_configured:
            actions.append(("DMA input channel stop", lambda: support.dma.stop(input_channel)))
            actions.append(
                ("DMA input channel deconfigure", lambda: support.dma.deconfigure(input_channel))
            )
        if output_channel_configured:
            actions.append(("DMA output channel stop", lambda: support.dma.stop(output_channel)))
            actions.append(
                ("DMA output channel deconfigure", lambda: support.dma.deconfigure(output_channel))
            )
        if output_route_configured:
            actions.append(_route_cleanup_actions(support.sysctrl, support.route)[0])
        if input_route_configured:
            actions.append(_route_cleanup_actions(support.sysctrl, support.route)[1])
        if controller_enabled:
            actions.append(("DMA controller disable", support.dma.controller_disable))
        if dma_request_enabled:
            actions.append(
                (
                    "AES DMA request disable",
                    lambda: support.aes_support.aes.dma_request_set(False, False),
                )
            )
        if aes_enabled:
            actions.append(("AES module disable", support.aes_support.aes.disable))
        if resource_ready:
            actions.append(("Resource pool reset", support.aes_support.resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 资源：重置独占池，并创建输入和输出 Buffer。
        support.aes_support.resource.reset()
        resource_ready = True
        source = support.aes_support.resource.create(len(_BLOCK), alignment=4)
        destination = support.aes_support.resource.create(len(expected), alignment=4)
        support.aes_support.resource.write(source, _BLOCK)
        support.aes_support.resource.fill(destination, 0xA5)
        input_config, output_config = _build_dma_configs(
            route=support.route,
            input_channel=input_channel,
            output_channel=output_channel,
            source_address=source.address,
            destination_address=destination.address,
            transfer_bytes=len(_BLOCK),
            register_mode=True,
        )

        # AES：显式启用模块，配置 REGISTER Mode、Key、Length 和双向 DMA Request。
        support.aes_support.aes.enable()
        aes_enabled = True
        support.aes_support.aes.configure(config)
        support.aes_support.aes.key_set(_KEY128)
        support.aes_support.aes.data_length_set(len(_BLOCK))

        # DMA：启用 Controller，并配置输入、输出两条执行映射 Route。
        support.dma.controller_enable()
        controller_enabled = True
        support.sysctrl.configure_route(
            DmaRequestRoute(
                support.route.controller,
                support.route.input_interface,
                support.route.input_request_id,
            )
        )
        input_route_configured = True
        support.sysctrl.configure_route(
            DmaRequestRoute(
                support.route.controller,
                support.route.output_interface,
                support.route.output_request_id,
            )
        )
        output_route_configured = True

        # Channel：按 REGISTER 递增端点配置输出和输入 Channel。
        support.dma.configure(output_config)
        output_channel_configured = True
        support.dma.configure(input_config)
        input_channel_configured = True

        # 刺激：先启动输出 Channel，再启动输入 Channel，并等待两者 Free。
        support.dma.start(output_channel)
        support.dma.start(input_channel)
        support.aes_support.aes.dma_request_set(True, True)
        dma_request_enabled = True
        input_status = support.dma.wait_channel_free(input_channel)
        output_status = support.dma.wait_channel_free(output_channel)

        # 观测：读取完整输出，验证四个寄存器端点的拼接语义。
        actual = support.aes_support.resource.read(destination, len(expected))
        record_property("expected_output", expected.hex())
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
            endpoint="DMA_DESTINATION<-RESULT_DOUT[0..3]",
        )

    record_result(
        et_artifact_dir,
        "aes_p2_002",
        expected=expected,
        actual=actual,
        channel_status={
            "input_free": input_status.is_free,
            "output_free": output_status.is_free,
        },
    )
    assert input_status.is_free and output_status.is_free
    assert actual == expected


# 测试 Feature：AES DMA FIFO Mode 的双向固定地址路径。
#
# 测试方法：
# 1. 构造一个确定性 AES Block，选择执行映射中的 FIFO 固定地址。
# 2. 先打开输入 Request 完成 Memory→AES，再打开输出 Request 完成 AES→Memory。
# 3. 等待两条 Channel 结束，比较完整 Block 与独立 Golden。
#
# 通过条件：
# 1. 两条 DMA Channel 均正常完成。
# 2. 固定地址 FIFO 的完整输出精确等于独立 Golden。
def test_aes_p2_003_dma_fifo_mode(
    aes_dma_support,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：单 Block 隔离验证固定 FIFO 的输入、输出端点。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=aes_dma_support.route.controller)
    crg_driver.reset(
        CrgPeripheral.AES,
        instance=aes_dma_support.aes_support.instance_id,
    )
    resource_driver.reset()

    support = aes_dma_support
    payload = _BLOCK
    config = AesConfig(
        AesDirection.ENCRYPT,
        AesKeySize.AES128,
        AesMode.ECB,
        endian=AesEndian.LITTLE,
        dma_transfer_mode=AesDmaTransferMode.FIFO,
    )
    require_aes_config_supported(support.aes_support, config)
    require_aes_dma_supported(support.aes_support, config.dma_transfer_mode)
    dma_capabilities = support.dma.capabilities_get()
    required = DmaFeature.MEMORY_TO_PERIPHERAL | DmaFeature.PERIPHERAL_TO_MEMORY
    if dma_capabilities.features & required != required:
        pytest.skip("skip_by_runtime_feature: bidirectional DMA is unavailable")
    free_channels = tuple(
        channel
        for channel in range(dma_capabilities.channel_count)
        if support.dma.channel_status(channel).is_free
    )
    if len(free_channels) < 2:
        pytest.skip("skip_by_runtime_resource: AES DMA needs two free channels")
    input_channel, output_channel = free_channels[:2]
    expected = aes_golden(payload, _KEY128, None, config)
    resource_ready = False
    aes_enabled = False
    dma_request_enabled = False
    controller_enabled = False
    input_route_configured = False
    output_route_configured = False
    output_channel_configured = False
    input_channel_configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if input_channel_configured:
            actions.append(("DMA input channel stop", lambda: support.dma.stop(input_channel)))
            actions.append(
                ("DMA input channel deconfigure", lambda: support.dma.deconfigure(input_channel))
            )
        if output_channel_configured:
            actions.append(("DMA output channel stop", lambda: support.dma.stop(output_channel)))
            actions.append(
                ("DMA output channel deconfigure", lambda: support.dma.deconfigure(output_channel))
            )
        if output_route_configured:
            actions.append(_route_cleanup_actions(support.sysctrl, support.route)[0])
        if input_route_configured:
            actions.append(_route_cleanup_actions(support.sysctrl, support.route)[1])
        if controller_enabled:
            actions.append(("DMA controller disable", support.dma.controller_disable))
        if dma_request_enabled:
            actions.append(
                (
                    "AES DMA request disable",
                    lambda: support.aes_support.aes.dma_request_set(False, False),
                )
            )
        if aes_enabled:
            actions.append(("AES module disable", support.aes_support.aes.disable))
        if resource_ready:
            actions.append(("Resource pool reset", support.aes_support.resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 资源：重置独占池，并创建单 Block 的输入和输出 Buffer。
        support.aes_support.resource.reset()
        resource_ready = True
        source = support.aes_support.resource.create(len(payload), alignment=4)
        destination = support.aes_support.resource.create(len(expected), alignment=4)
        support.aes_support.resource.write(source, payload)
        support.aes_support.resource.fill(destination, 0xA5)
        input_config, output_config = _build_dma_configs(
            route=support.route,
            input_channel=input_channel,
            output_channel=output_channel,
            source_address=source.address,
            destination_address=destination.address,
            transfer_bytes=len(payload),
            register_mode=False,
        )

        # AES：显式启用模块，配置 FIFO Mode、Key、Length 和双向 DMA Request。
        support.aes_support.aes.enable()
        aes_enabled = True
        support.aes_support.aes.configure(config)
        support.aes_support.aes.key_set(_KEY128)
        support.aes_support.aes.data_length_set(len(payload))

        # DMA：启用 Controller，并配置输入、输出两条执行映射 Route。
        support.dma.controller_enable()
        controller_enabled = True
        support.sysctrl.configure_route(
            DmaRequestRoute(
                support.route.controller,
                support.route.input_interface,
                support.route.input_request_id,
            )
        )
        input_route_configured = True
        support.sysctrl.configure_route(
            DmaRequestRoute(
                support.route.controller,
                support.route.output_interface,
                support.route.output_request_id,
            )
        )
        output_route_configured = True

        # Channel：以固定 FIFO 端点配置输出和输入 Channel。
        support.dma.configure(output_config)
        output_channel_configured = True
        support.dma.configure(input_config)
        input_channel_configured = True

        # 输入 FIFO：只启动输入 Channel 和 AES 输入 Request，避免引入并发时序。
        support.dma.start(input_channel)
        support.aes_support.aes.dma_request_set(True, False)
        dma_request_enabled = True
        input_status = support.dma.wait_channel_free(input_channel)

        # 输出 FIFO：输入完成后启动输出 Channel，再切换到输出 Request。
        support.dma.start(output_channel)
        support.aes_support.aes.dma_request_set(False, True)
        output_status = support.dma.wait_channel_free(output_channel)

        # 观测：读取完整 Block，不以 Channel 完成代替密文校验。
        actual = support.aes_support.resource.read(destination, len(expected))
        record_property("expected_output", expected.hex())
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
        "aes_p2_003",
        expected=expected,
        actual=actual,
        channel_status={
            "input_free": input_status.is_free,
            "output_free": output_status.is_free,
        },
    )
    assert input_status.is_free and output_status.is_free
    assert actual == expected
