# CRC P2 Formal Case。
#
# 职责：验证 CRC 通过 DMA 输入端点接收数据并产生正确结果。
# 边界：跨 IP 顺序只在 Case 中显式编排，各 Driver 仍保持单 IP。
# 依赖：仅依赖 CRC/DMA/SYSCTRL/Resource Driver、已审核 Route 和 Cleanup。

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction
from ...drivers.crc import CrcConfig, CrcMode
from ...drivers.crg import CrgPeripheral
from ...drivers.dma import (
    DmaAddressMode,
    DmaConfig,
    DmaTransferType,
    DmaWidth,
)
from ...drivers.sysctrl import DmaRequestRoute
from ...results.recorder import write_json_result
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import CrcDmaSupport, calculate_crc_reference, make_crc_pattern

pytestmark = [pytest.mark.hardware, pytest.mark.ip("crc")]


# 测试 Feature：
# CRC8/CRC16/CRC32 通过 DMA Memory-to-Peripheral 输入获得正确结果。
#
# 测试方法：
# 1. 从 Capability/执行映射取得 CRC IR、Request ID、DMA Controller/Interface，并准备 Resource Payload。
# 2. PC 显式配置 CRC、SYSCTRL Route、DMA Controller/Channel，再启动 DMA 并等待终态。
# 3. DMA 完成后读取 Channel Free、CRC Result 和 Remaining Input Count，并记录实际 Route。
#
# 通过条件：
# 1. DMA Channel 最终 Free，CRC Remaining Input Count 为零。
# 2. 三种模式的 CRC Result 都精确等于独立 PC Golden。
# 3. CRC8/16/32 的 DMA Width 与模式自然宽度一致，Case 中不存在具体芯片地址或 Request ID 常量。
@pytest.mark.parametrize(
    ("mode", "width"),
    (
        (CrcMode.CRC8, DmaWidth.BITS_8),
        (CrcMode.CRC16, DmaWidth.BITS_16),
        (CrcMode.CRC32, DmaWidth.BITS_32),
    ),
)
def test_crc_p2_001_dma_input_equivalence(
    crc_dma_support: CrcDmaSupport,
    et_artifact_dir: Path,
    mode: CrcMode,
    width: DmaWidth,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：从已 Gate Support 取得四个单 IP Driver 和芯片执行映射。
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
    unit_bytes = int(mode) // 8
    payload = make_crc_pattern(32, seed=0xD0000000 + int(mode))
    config = CrcConfig(
        mode=mode,
        polynomial={
            CrcMode.CRC8: 0x07,
            CrcMode.CRC16: 0x1021,
            CrcMode.CRC32: 0x04C11DB7,
        }[mode],
        initial_value={
            CrcMode.CRC8: 0xFF,
            CrcMode.CRC16: 0xFFFF,
            CrcMode.CRC32: 0xFFFFFFFF,
        }[mode],
        byte_swap=mode is not CrcMode.CRC8,
    )
    expected = calculate_crc_reference(config, payload)
    resource_ready = False
    crc_enabled = False
    controller_enabled = False
    route_configured = False
    channel_configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if channel_configured:
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

    with case_cleanup_scope(cleanup_actions):
        # 资源：重置独占池，申请对齐源 Buffer，并写入确定性 Payload。
        resource.reset()
        resource_ready = True
        source = resource.create(len(payload), alignment=4)
        resource.write(source, payload)
        channel = dma.find_free_channel()

        # CRC：显式启用模块，再配置算法和本次输入长度。
        crc.enable()
        crc_enabled = True
        crc.configure(config)
        crc.data_length_set(len(payload))

        # DMA：显式启用 Controller，并配置经能力映射取得的请求路由。
        dma.controller_enable()
        controller_enabled = True
        sysctrl.configure_route(
            DmaRequestRoute(route.controller, route.interface, route.request_id)
        )
        route_configured = True
        dma_config = DmaConfig(
            channel=channel,
            source_address=source.address,
            destination_address=route.peripheral_address,
            transfer_count=len(payload) // unit_bytes,
            transfer_type=DmaTransferType.MEMORY_TO_PERIPHERAL,
            source_width=width,
            destination_width=width,
            source_address_mode=DmaAddressMode.INCREMENT,
            destination_address_mode=DmaAddressMode.FIXED,
            destination_interface=route.interface,
        )
        dma.configure(dma_config)
        channel_configured = True

        # 刺激：启动单 Channel，并等待硬件回到 Free 终态。
        dma.start(channel)
        channel_status = dma.wait_channel_free(channel)

        # 观测：DMA 完成后读取 CRC Result 和剩余输入计数。
        actual = crc.result_get()
        remaining = crc.remaining_input_count_get()

        # 证据：Route/Width是配置事实，Channel/CRC Result/LENGTH是DUT硬件事实。
        record_property("mode", mode.name)
        record_property("dma_width", width.name)
        record_property("expected_crc", expected)
        record_observation(
            record_property,
            key="channel_free",
            value=channel_status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FREE",
        )
        record_observation(
            record_property,
            key="remaining_input_count",
            value=remaining,
            source="dut",
            endpoint="LENGTH.REMAINING_INPUT_COUNT",
        )
        record_observation(
            record_property,
            key="actual_crc",
            value=actual,
            source="dut",
            endpoint="RESULT.CRC",
        )

        # 断言：DMA 终态和 CRC 独立 Golden 必须同时满足。
        assert channel_status.is_free
        assert remaining == 0
        assert actual == expected

    # 记录：保存 Route、DMA 配置和 CRC 精确结果。
    write_json_result(
        et_artifact_dir / f"crc_p2_001_{mode.name.lower()}.json",
        {
            "measurement_schema": "et.measurement.v1",
            "case_id": "crc_p2_001",
            "mode": mode.name,
            "controller": route.controller,
            "channel": channel,
            "interface": route.interface,
            "request_id": route.request_id,
            "peripheral_address": route.peripheral_address,
            "address_evidence": route.address_evidence,
            "request_evidence": route.request_evidence,
            "length_bytes": len(payload),
            "expected": expected,
            "actual": actual,
            "remaining_input_count": remaining,
            "channel_free": channel_status.is_free,
        },
    )
