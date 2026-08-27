# FMAC P2 Formal Case。
#
# 职责：验证FMAC双向DMA Request Gate和Q15 FIR端到端数据路径。
# 边界：芯片地址和Request只来自执行映射；Case只编排公共Driver。
# 依赖：仅依赖FMAC、DMA、Resource Driver及注入的Execution Mapping。

from __future__ import annotations

from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction
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
from ...drivers.fmac import FmacDmaRequest, FmacFeature, FmacFunction
from ...drivers.sysctrl import DmaRequestRoute
from ...scheduling.run_context import record_evidence
from ..case_cleanup import case_cleanup_scope
from ._support import require_fmac_features
from .fmac_helpers import (
    default_config,
    pack_q15,
    record_result,
    unpack_q15,
)
from .fmac_helpers import (
    record_fmac_observation as record_observation,
)

pytestmark = [pytest.mark.hardware, pytest.mark.ip("fmac")]

FMAC_DMA_COEFFICIENTS = (0x4000, 0x2000, 0x1000, 0x0800)
FMAC_DMA_SAMPLES = (0x2000,) * 16
FMAC_DMA_EXPECTED_STEADY = 0x1E00
FMAC_DMA_GATE_SAMPLES = 4
FMAC_Q15_ITEM_SIZE_BYTES = 2


# 构造FMAC固定FIFO端点的双向16-bit DMA Channel配置。
def _build_dma_configs(
    *,
    route,
    input_channel: int,
    output_channel: int,
    source_address: int,
    destination_address: int,
    item_count: int,
) -> tuple[DmaConfig, DmaConfig]:

    input_config = DmaConfig(
        channel=input_channel,
        source_address=source_address,
        destination_address=route.fifo_address,
        transfer_count=item_count,
        transfer_type=DmaTransferType.MEMORY_TO_PERIPHERAL,
        source_width=DmaWidth.BITS_16,
        destination_width=DmaWidth.BITS_16,
        source_address_mode=DmaAddressMode.INCREMENT,
        destination_address_mode=DmaAddressMode.FIXED,
        source_burst=DmaBurst.ITEMS_1,
        destination_burst=DmaBurst.ITEMS_1,
        destination_interface=route.input_interface,
    )
    output_config = DmaConfig(
        channel=output_channel,
        source_address=route.fifo_address,
        destination_address=destination_address,
        transfer_count=item_count,
        transfer_type=DmaTransferType.PERIPHERAL_TO_MEMORY,
        source_width=DmaWidth.BITS_16,
        destination_width=DmaWidth.BITS_16,
        source_address_mode=DmaAddressMode.FIXED,
        destination_address_mode=DmaAddressMode.INCREMENT,
        source_burst=DmaBurst.ITEMS_1,
        destination_burst=DmaBurst.ITEMS_1,
        source_interface=route.output_interface,
    )
    return input_config, output_config


# 测试 Feature：
# 1. FMAC输入写Request Gate和输出读Request Gate。
# 2. 双向16-bit DMA驱动FMAC Q15 FIR端到端处理。
#
# 测试方法：
# 1. 从芯片执行映射取得FIFO地址、双向Request、Controller和两个接口。
# 2. 先启动输入/输出DMA并保持FMAC Gate关闭，采样确认Channel尚未完成。
# 3. FMAC保持idle时打开双向Gate，再启动FIR并等待两条Channel完成。
#
# 通过条件：
# 1. Gate关闭窗口内两条Channel均保持活动且无ERROR。
# 2. Gate打开后两条Channel均回到Free且无ERROR。
# 3. DMA输出稳态末4项全部为0x1E00。
def test_fmac_p2_001_bidirectional_dma_fir(
    fmac_dma_support,
    et_artifact_dir: Path,
    record_property,
) -> None:

    # 准备：从运行时DMA能力中选择两条空闲Channel。
    # 隔离：本 Case 配置前先复位辅助 DMA；随后沿用既有 FMAC 和 Resource 复位。
    fmac_dma_support.fmac_support.crg.reset(
        CrgPeripheral.DMA,
        instance=fmac_dma_support.route.controller,
    )

    support = fmac_dma_support
    support.fmac_support.crg.reset(
        CrgPeripheral.FMAC,
        instance=support.fmac_support.instance_id,
    )
    support.fmac_support.fmac.state_reset()
    support.fmac_support.resource.reset()
    fmac = support.fmac_support.fmac
    resource = support.fmac_support.resource
    dma = support.dma
    route = support.route
    require_fmac_features(
        support.fmac_support,
        FmacFeature.FIXED_Q15 | FmacFeature.FIR | FmacFeature.DMA_REQUEST,
    )
    dma_capabilities = dma.capabilities_get()
    required = DmaFeature.MEMORY_TO_PERIPHERAL | DmaFeature.PERIPHERAL_TO_MEMORY
    if dma_capabilities.features & required != required:
        pytest.skip("skip_by_runtime_feature: bidirectional DMA is unavailable")
    free_channels = tuple(
        channel
        for channel in range(dma_capabilities.channel_count)
        if dma.channel_status(channel).is_free
    )
    if len(free_channels) < 2:
        pytest.skip("skip_by_runtime_resource: FMAC DMA needs two free channels")
    input_channel, output_channel = free_channels[:2]

    # 清理状态：只释放本Case实际取得的FMAC、DMA、DMAMUX和Resource资源。
    resource_ready = False
    controller_enabled = False
    input_route_configured = False
    output_route_configured = False
    input_channel_configured = False
    output_channel_configured = False
    dma_request_enabled = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        # FMAC Request Gate只能在idle修改，因此必须先Stop再关闭Gate。
        actions: list[CleanupAction] = [("FMAC stop", fmac.stop)]
        if dma_request_enabled:
            actions.append(
                (
                    "FMAC DMA request disable",
                    lambda: fmac.dma_request_set(FmacDmaRequest.NONE),
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
        if input_route_configured:
            actions.append(
                (
                    "SYSCTRL FMAC input route release",
                    lambda: support.sysctrl.release_dma_request(
                        route.controller, route.input_interface
                    ),
                )
            )
        if output_route_configured:
            actions.append(
                (
                    "SYSCTRL FMAC output route release",
                    lambda: support.sysctrl.release_dma_request(
                        route.controller, route.output_interface
                    ),
                )
            )
        if controller_enabled:
            actions.append(("DMA controller disable", dma.controller_disable))
        actions.append(("FMAC clear", fmac.clear))
        if resource_ready:
            actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 资源：创建确定性系数、输入和带哨兵的输出Buffer。
        resource_ready = True
        coefficient_payload = pack_q15(FMAC_DMA_COEFFICIENTS)
        history_payload = pack_q15((0,) * len(FMAC_DMA_COEFFICIENTS))
        source_payload = pack_q15(FMAC_DMA_SAMPLES)
        coefficients = resource.create(len(coefficient_payload), alignment=4)
        history = resource.create(len(history_payload), alignment=4)
        source = resource.create(len(source_payload), alignment=4)
        destination = resource.create(len(source_payload), alignment=4)
        resource.write(coefficients, coefficient_payload)
        resource.write(history, history_payload)
        resource.write(source, source_payload)
        resource.fill(destination, 0xA5)

        # FMAC：建立完整配置、装载系数并保持双向DMA Gate关闭。
        fmac.configure(default_config(x1_size=32, x2_size=16, y_size=32))
        fmac.coefficients_load(coefficients.handle, 0, len(FMAC_DMA_COEFFICIENTS))
        fmac.x1_preload(history.handle, 0, len(FMAC_DMA_COEFFICIENTS))
        fmac.dma_request_set(FmacDmaRequest.NONE)

        # DMAMUX：配置执行映射中的输入和输出Request。
        dma.controller_enable()
        controller_enabled = True
        support.sysctrl.configure_route(
            DmaRequestRoute(route.controller, route.input_interface, route.input_request_id)
        )
        input_route_configured = True
        support.sysctrl.configure_route(
            DmaRequestRoute(route.controller, route.output_interface, route.output_request_id)
        )
        output_route_configured = True

        # Channel：使用同一固定FIFO地址配置16-bit双向搬运。
        input_config, output_config = _build_dma_configs(
            route=route,
            input_channel=input_channel,
            output_channel=output_channel,
            source_address=source.address,
            destination_address=destination.address,
            item_count=len(FMAC_DMA_SAMPLES),
        )
        dma.configure(output_config)
        output_channel_configured = True
        dma.configure(input_config)
        input_channel_configured = True

        # Gate关闭观测：DMA已启动，但FMAC Request尚未打开。
        dma.start(output_channel)
        dma.start(input_channel)
        gate_closed_samples: list[dict[str, object]] = []

        # 短窗口采样：证明Gate关闭时两条Channel都没有伪完成或错误终态。
        for sample_index in range(FMAC_DMA_GATE_SAMPLES):
            input_status = dma.channel_status(input_channel)
            output_status = dma.channel_status(output_channel)
            gate_closed_samples.append(
                {
                    "index": sample_index,
                    "input_free": input_status.is_free,
                    "output_free": output_status.is_free,
                    "input_events": int(input_status.interrupt_events),
                    "output_events": int(output_status.interrupt_events),
                }
            )
        gate_closed_payload = resource.read(destination, len(source_payload))
        gate_closed_unchanged = gate_closed_payload == bytes((0xA5,)) * len(source_payload)

        # Gate打开刺激：FMAC保持idle时先打开双向Request，再启动FIR处理。
        fmac.dma_request_set(FmacDmaRequest.ALL)
        dma_request_enabled = True
        fmac.start(FmacFunction.FIR, feedforward_taps=len(FMAC_DMA_COEFFICIENTS))
        input_status = dma.wait_channel_free(input_channel)
        output_status = dma.wait_channel_free(output_channel)
        actual = unpack_q15(resource.read(destination, len(source_payload)))

        # 观测：记录Gate窗口、DMA终态和硬件稳态输出。
        record_observation(
            record_property,
            key="actual_output",
            value=actual[-4:],
            source="dut",
            endpoint="DMA_DESTINATION_SEQUENCE",
        )
        record_result(
            et_artifact_dir,
            "fmac_p2_001",
            gate_closed=gate_closed_samples,
            channel_status={
                "input_free": input_status.is_free,
                "output_free": output_status.is_free,
                "input_events": int(input_status.interrupt_events),
                "output_events": int(output_status.interrupt_events),
            },
            steady_tail=actual[-4:],
            gate_closed_unchanged=gate_closed_unchanged,
        )

        # 断言：Gate控制、DMA终态和FIR Golden三类证据必须全部成立。
        assert all(
            not bool(sample["input_free"])
            and not bool(sample["output_free"])
            and not int(sample["input_events"]) & int(DmaIrqEvent.ERROR)
            and not int(sample["output_events"]) & int(DmaIrqEvent.ERROR)
            for sample in gate_closed_samples
        )
        assert gate_closed_unchanged
        assert input_status.is_free and output_status.is_free
        assert not input_status.interrupt_events & DmaIrqEvent.ERROR
        assert not output_status.interrupt_events & DmaIrqEvent.ERROR
        assert actual[-4:] == (FMAC_DMA_EXPECTED_STEADY,) * 4

    record_evidence(record_property, "dut")
