# CORDIC P2 Formal Case。
#
# 职责：验证 CORDIC DMA 工作模式的输入、计算和结果输出搬运链路。
# 边界：DMA/SYSCTRL/Resource 的跨 IP 顺序只在本 Case 编排，CORDIC Driver 仍只负责 CORDIC。
# 依赖：CORDIC、DMA、SYSCTRL、Resource Driver 和当前芯片 Execution Mapping。

from __future__ import annotations

import struct
from collections.abc import Callable
from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction
from ...drivers.cordic import (
    CordicConfig,
    CordicFunction,
    CordicInputRange,
    CordicNumericMode,
    CordicResultCount,
    CordicStatus,
    CordicWidth,
    CordicWorkMode,
)
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
from ._support import CordicDmaSupport

pytestmark = [pytest.mark.hardware, pytest.mark.ip("cordic")]

_CORDIC_DMA_WORD_BYTES = 4
_CORDIC_DMA_INPUT_WORDS = 1
_CORDIC_DMA_RESULT_WORDS = 1
_CORDIC_DMA_TIMEOUT_S = 15.0
_CORDIC_Q31_FRACTION_BITS = 31
_CORDIC_Q31_MAXIMUM = (1 << _CORDIC_Q31_FRACTION_BITS) - 1
_CORDIC_Q31_QUARTER = 0x20000000


# 把数学单位值编码为 CORDIC 32-bit Q1.31 Raw 字；边界 1.0 饱和到最大正值。
def _q31_raw(value: float) -> int:

    if value >= 1.0:
        return _CORDIC_Q31_MAXIMUM
    if value <= -1.0:
        return 1 << _CORDIC_Q31_FRACTION_BITS
    return int(round(value * (1 << _CORDIC_Q31_FRACTION_BITS))) & 0xFFFFFFFF


# 测试 Feature：
# CORDIC DMA工作模式的输入搬运、计算完成和结果搬运等价性。
#
# 测试方法：
# 1. 从当前Chip Capability/Execution Mapping取得CORDIC输入/输出Endpoint、Request、Interface和DMA Controller。
# 2. 先使用Polling路径执行一个Q1.31 SQRT(0.25)基线，再以同一输入和独立Golden配置DMA模式。
# 3. 创建输入/输出Resource，配置两条DMA Channel和SYSCTRL Request Route，先武装结果通道再启动输入通道。
# 4. 有界等待两个Channel进入Free，读取DMA目标Buffer、CORDIC完成状态和Channel错误位。
# 5. 将DMA结果同时与CPU基线和Q1.31独立Golden比较，记录真实Route和原始结果。
#
# 通过条件：
# 1. 当前芯片存在完整且已审核的CORDIC DMA Execution Mapping；缺失时只报告运行期Mapping skip。
# 2. 输入/输出DMA Channel均在有界时间内Free，且没有DMA ERROR事件。
# 3. DMA目标Buffer的Raw结果与CPU基线及独立Q1.31 Golden完全一致，CORDIC只产生COMPLETE状态。
def test_cordic_p2_001_dma_mode_equivalence(
    cordic_dma_support: CordicDmaSupport,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：读取已经通过静态/Runtime Gate的单IP Driver、Resource和Execution Mapping。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=cordic_dma_support.route.controller)
    crg_driver.reset(
        CrgPeripheral.CORDIC,
        instance=cordic_dma_support.cordic_support.instance_id,
    )
    resource_driver.reset()

    support = cordic_dma_support
    cordic_support = support.cordic_support
    cordic = cordic_support.cordic
    dma = support.dma
    resource = support.resource
    sysctrl = support.sysctrl
    route = support.route

    # 配置：固定使用ET6801历史DMA Case已验证过的SQRT(0.25) Q1.31节点。
    cpu_config = CordicConfig(
        numeric_mode=CordicNumericMode.FIXED,
        argument_width=CordicWidth.BITS_32,
        result_width=CordicWidth.BITS_32,
        input_range=CordicInputRange.NORMALIZED,
        precision_cycles=cordic_support.runtime.maximum_precision_cycles,
        sincos_result_count=CordicResultCount.ONE,
        work_mode=CordicWorkMode.POLLING,
    )
    dma_config = CordicConfig(
        numeric_mode=cpu_config.numeric_mode,
        argument_width=cpu_config.argument_width,
        result_width=cpu_config.result_width,
        input_range=cpu_config.input_range,
        precision_cycles=cpu_config.precision_cycles,
        sincos_result_count=cpu_config.sincos_result_count,
        work_mode=CordicWorkMode.DMA,
    )
    expected_words = [_q31_raw(0.5)]

    # 执行资格：在第一次硬件变更前确认本Case需要的两个DMA Channel同时可用。
    input_channel = dma.find_free_channel()
    output_channel: int | None = None

    # 资源选择：Case主体显式查询其第二条DMA Channel，不把硬件I/O隐藏进Helper。
    for candidate in range(support.dma_capabilities.channel_count):
        if candidate == input_channel:
            continue

        if dma.channel_status(candidate).is_free:
            output_channel = candidate
            break

    if output_channel is None:
        pytest.skip("skip_by_runtime_capability: two free DMA channels are unavailable")

    # 资源与硬件状态：所有状态标志用于确保Cleanup只释放本Case已取得的资源。
    resource_ready = False
    controller_enabled = False
    input_route_configured = False
    output_route_configured = False
    input_channel_configured = False
    output_channel_configured = False
    cordic_configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if input_channel_configured:
            actions.append(("CORDIC DMA input channel stop", lambda: dma.stop(input_channel)))
            actions.append(
                ("CORDIC DMA input channel deconfigure", lambda: dma.deconfigure(input_channel))
            )
        if output_channel_configured:
            actions.append(("CORDIC DMA output channel stop", lambda: dma.stop(output_channel)))
            actions.append(
                (
                    "CORDIC DMA output channel deconfigure",
                    lambda: dma.deconfigure(output_channel),
                )
            )
        if input_route_configured:
            actions.append(
                (
                    "CORDIC DMA input route release",
                    lambda: sysctrl.release_dma_request(
                        route.controller,
                        route.input_interface,
                    ),
                )
            )
        if output_route_configured:
            actions.append(
                (
                    "CORDIC DMA output route release",
                    lambda: sysctrl.release_dma_request(
                        route.controller,
                        route.output_interface,
                    ),
                )
            )
        if controller_enabled:
            actions.append(("CORDIC DMA controller disable", dma.controller_disable))
        if cordic_configured:
            actions.append(
                (
                    "CORDIC restore polling configuration",
                    lambda: cordic.configure(cpu_config),
                )
            )
        if resource_ready:
            actions.append(("CORDIC DMA Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # CPU基线：先清除历史状态，再提交0.25并读取SQRT Polling结果。
        resource.reset()
        resource_ready = True
        cordic.configure(cpu_config)
        cordic_configured = True
        cordic.status_clear(CordicStatus.ALL)
        cordic.argument_submit(CordicFunction.SQRT, _CORDIC_Q31_QUARTER)
        cpu_status, _ = cordic.wait_status(CordicStatus.COMPLETE)
        cpu_result = cordic.result_get()
        cpu_words = [cpu_result.primary_raw]
        cordic.status_clear(CordicStatus.COMPLETE)
        cpu_cleared = cordic.status_get()

        # 资源：输入和输出Buffer各保存一个32-bit Q1.31字。
        input_resource = resource.create(
            _CORDIC_DMA_INPUT_WORDS * _CORDIC_DMA_WORD_BYTES,
            alignment=_CORDIC_DMA_WORD_BYTES,
        )
        output_resource = resource.create(
            _CORDIC_DMA_RESULT_WORDS * _CORDIC_DMA_WORD_BYTES,
            alignment=_CORDIC_DMA_WORD_BYTES,
        )
        resource.write(input_resource, struct.pack("<I", _CORDIC_Q31_QUARTER))
        resource.fill(output_resource, 0xA5)

        # DMA：使用门禁阶段选出的两个空闲Channel，避免绑定固定Channel编号。
        dma.controller_enable()
        controller_enabled = True

        # 路由：分别配置CORDIC输入/输出Request，禁止用旧资料中的隐式Request ID。
        sysctrl.configure_route(
            DmaRequestRoute(
                route.controller,
                route.input_interface,
                route.input_request_id,
            )
        )
        input_route_configured = True
        sysctrl.configure_route(
            DmaRequestRoute(
                route.controller,
                route.output_interface,
                route.output_request_id,
            )
        )
        output_route_configured = True

        # CORDIC：保持Polling模式并清除CPU基线状态，最后才切换DMA模式产生请求。
        cordic.status_clear(CordicStatus.ALL)

        # DMA：先配置输出P2M Channel，使结果端点在输入刺激前处于接收状态。
        dma.configure(
            DmaConfig(
                channel=output_channel,
                source_address=route.output_endpoint,
                destination_address=output_resource.address,
                transfer_count=_CORDIC_DMA_RESULT_WORDS,
                transfer_type=DmaTransferType.PERIPHERAL_TO_MEMORY,
                source_width=DmaWidth.BITS_32,
                destination_width=DmaWidth.BITS_32,
                source_address_mode=DmaAddressMode.FIXED,
                destination_address_mode=DmaAddressMode.INCREMENT,
                source_interface=route.output_interface,
            )
        )
        output_channel_configured = True

        # DMA：配置输入M2P Channel，将Resource中的单个Q1.31字送入CORDIC输入端点。
        dma.configure(
            DmaConfig(
                channel=input_channel,
                source_address=input_resource.address,
                destination_address=route.input_endpoint,
                transfer_count=_CORDIC_DMA_INPUT_WORDS,
                transfer_type=DmaTransferType.MEMORY_TO_PERIPHERAL,
                source_width=DmaWidth.BITS_32,
                destination_width=DmaWidth.BITS_32,
                source_address_mode=DmaAddressMode.INCREMENT,
                destination_address_mode=DmaAddressMode.FIXED,
                destination_interface=route.input_interface,
            )
        )
        input_channel_configured = True

        # 激励：先启动两条Channel，最后切换CORDIC DMA模式，避免首个Request在Channel武装前丢失。
        dma.start(output_channel)
        dma.start(input_channel)
        cordic.configure(dma_config)
        channel_statuses = dma.wait_channels_free(
            (input_channel, output_channel),
            timeout_s=_CORDIC_DMA_TIMEOUT_S,
        )

        # 观测：读取DMA目标Buffer和CORDIC完成状态，保留原始32-bit字及Channel事件位。
        actual_bytes = resource.read(output_resource)
        dma_words = list(struct.unpack("<I", actual_bytes))
        dma_status = cordic.status_get()
        channel_summary = {
            str(channel): {
                "is_free": status.is_free,
                "fifo_empty": status.fifo_empty,
                "interrupt_events": int(status.interrupt_events),
            }
            for channel, status in channel_statuses.items()
        }
        input_status = channel_statuses[input_channel]
        output_status = channel_statuses[output_channel]

        # 证据：在断言前记录独立Golden、CPU基线、DMA Channel硬件状态和结果Buffer。
        record_property("expected_dma_words", expected_words)
        record_property("cpu_baseline_words", cpu_words)
        record_property("dma_channel_status", channel_summary)
        record_observation(
            record_property,
            key="dma_input_channel_free",
            value=input_status.is_free,
            source="dut",
            endpoint="DMA.INPUT_CHANNEL.FREE",
        )
        record_observation(
            record_property,
            key="dma_input_channel_fifo_empty",
            value=input_status.fifo_empty,
            source="dut",
            endpoint="DMA.INPUT_CHANNEL.FIFO_EMPTY",
        )
        record_observation(
            record_property,
            key="dma_input_channel_irq_status",
            value=int(input_status.interrupt_events),
            source="dut",
            endpoint="DMA.INPUT_CHANNEL.IRQ_STATUS",
        )
        record_observation(
            record_property,
            key="dma_output_channel_free",
            value=output_status.is_free,
            source="dut",
            endpoint="DMA.OUTPUT_CHANNEL.FREE",
        )
        record_observation(
            record_property,
            key="dma_output_channel_fifo_empty",
            value=output_status.fifo_empty,
            source="dut",
            endpoint="DMA.OUTPUT_CHANNEL.FIFO_EMPTY",
        )
        record_observation(
            record_property,
            key="dma_output_channel_irq_status",
            value=int(output_status.interrupt_events),
            source="dut",
            endpoint="DMA.OUTPUT_CHANNEL.IRQ_STATUS",
        )
        record_observation(
            record_property,
            key="dma_destination",
            value=dma_words,
            source="dut",
            endpoint="DMA.DESTINATION_BUFFER",
        )
        record_observation(
            record_property,
            key="cordic_status",
            value=int(dma_status),
            source="dut",
            endpoint="STATUS.COMPLETE",
        )
        write_json_result(
            et_artifact_dir / "cordic_p2_001_dma_mode_equivalence.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "cordic_p2_001",
                "route": {
                    "controller": route.controller,
                    "input_interface": route.input_interface,
                    "output_interface": route.output_interface,
                    "input_request_id": route.input_request_id,
                    "output_request_id": route.output_request_id,
                    "input_endpoint": route.input_endpoint,
                    "output_endpoint": route.output_endpoint,
                    "address_evidence": route.address_evidence,
                    "request_evidence": route.request_evidence,
                },
                "expected": expected_words,
                "cpu_baseline": cpu_words,
                "dma_destination": dma_words,
                "dma_channel_status": channel_summary,
                "cordic_status": {
                    "before_clear": int(dma_status),
                    "cpu_before_clear": int(cpu_status),
                    "cpu_after_clear": int(cpu_cleared),
                },
            },
        )

        # 断言：DMA双通道、CORDIC完成状态和CPU/独立Golden等价性必须同时成立。
        assert input_status.is_free
        assert output_status.is_free
        assert not input_status.interrupt_events & DmaIrqEvent.ERROR
        assert not output_status.interrupt_events & DmaIrqEvent.ERROR
        assert dma_words == expected_words
        assert dma_words == cpu_words
        assert dma_status == CordicStatus.COMPLETE
        assert cpu_cleared == CordicStatus(0)
