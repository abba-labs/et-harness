# DMA P0 Formal Case。
#
# 职责：验证 DMA Runtime/Component身份、基础生命周期和最小M2M恢复。
# 边界：只通过稳定 Driver API 操作设备，不访问 Codec/Transport/Register。
# 依赖：仅依赖 DMA Case Fixture、本地 Support、Resource Driver 和结果记录器。

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction
from ...drivers.crg import CrgPeripheral
from ...drivers.dma import DmaAccessView, DmaConfig, DmaFeature
from ...profiles.capabilities import ChipCapabilities
from ...results.recorder import write_json_result
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import DmaSupportFactory, require_dma_m2m_capability

pytestmark = [pytest.mark.hardware, pytest.mark.ip("dma")]


# =============================================================================
# 控制器能力与身份
# =============================================================================


# 测试 Feature：
# DMA 全部声明实例的运行时能力、组件身份和逐 Channel 静态参数一致性。
#
# 测试方法：
# 1. 从 Capability/Runtime 交集取得全部 DMA 实例并逐个读取 Runtime Capability。
# 2. 读取 NORMAL Component Snapshot，核对组件身份、Channel 数和静态 max_block_size。
# 3. 决定性能力事实先进入 Canonical Evidence，再发布完整 Controller Snapshot。
#
# 通过条件：
# 1. 全部静态实例均有 Runtime Service，Channel Count/Max Transfer/M2M 能力合法。
# 2. Component ID 有效，Channel 参数数量与 Channel Count 一致。
# 3. 每个 Channel 的静态 max_block_size 与 Runtime Max Transfer Count 一致。
def test_dma_p0_001_controller_capabilities(
    target_capabilities: ChipCapabilities,
    dma_support_for: DmaSupportFactory,
    dma_instance_ids: tuple[int, ...],
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
) -> None:

    # 准备：静态实例数是本 Case 的执行全集 Expected。
    # 只读 Case：仅核对静态/运行时能力，不执行 Feature 配置，无需前置复位。

    instances = target_capabilities.instances("dma")
    record_property("expected_instance_count", len(instances))
    results: list[dict[str, object]] = []
    validations: list[dict[str, object]] = []

    # 遍历：逐 Controller 收集 Runtime Capability 与 Component 硬件事实。
    for instance_id, instance in zip(dma_instance_ids, instances, strict=True):
        dma = dma_support_for(instance_id).dma
        dynamic = dma.capabilities_get()
        snapshot = dma.component_snapshot_get(DmaAccessView.NORMAL)

        record_observation(
            record_property,
            key="actual_channel_count",
            value=dynamic.channel_count,
            source="dut",
            endpoint="DMA_CAPABILITIES.CHANNEL_COUNT",
        )
        record_observation(
            record_property,
            key="actual_component_id",
            value=snapshot.component_id,
            source="dut",
            endpoint="DMA_COMPONENT.COMPONENT_ID",
        )
        record_observation(
            record_property,
            key="actual_channel_params",
            value=list(snapshot.channel_params),
            source="dut",
            endpoint="DMA_COMPONENT.CHANNEL_PARAMS",
        )

        max_block_matches = [
            target_capabilities.parameter(
                "dma",
                "max_block_size",
                instance=instance,
                member=f"channel_{channel}",
            )
            == dynamic.max_transfer_count
            for channel in range(dynamic.channel_count)
        ]
        validations.append(
            {
                "instance": instance,
                "channel_count_valid": dynamic.channel_count > 0,
                "max_transfer_valid": dynamic.max_transfer_count > 0,
                "m2m_supported": bool(dynamic.features & DmaFeature.MEMORY_TO_MEMORY),
                "component_id_valid": snapshot.component_id not in (0, 0xFFFFFFFF),
                "channel_param_count_match": (
                    len(snapshot.channel_params) == dynamic.channel_count
                ),
                "channel_params_nonzero": any(snapshot.channel_params),
                "max_block_matches": all(max_block_matches),
            }
        )
        results.append(
            {
                "instance": instance,
                "features": int(dynamic.features),
                "channel_count": dynamic.channel_count,
                "max_transfer_count": dynamic.max_transfer_count,
                "max_gather_scatter_interval": dynamic.max_gather_scatter_interval,
                "max_gather_scatter_count": dynamic.max_gather_scatter_count,
                "irq_events": int(dynamic.irq_events),
                "component_snapshot": {
                    "dma_id": snapshot.dma_id,
                    "component_id": snapshot.component_id,
                    "channel_params": list(snapshot.channel_params),
                    "multi_block_params": snapshot.multi_block_params,
                    "max_block_size_params": snapshot.max_block_size_params,
                },
            }
        )

    # Evidence：完整 Snapshot 只发布一次；FIFO exact-depth只保留静态事实。
    record_property("instance_count", len(results))
    write_json_result(
        et_artifact_dir / "dma_p0_001_controller_capabilities.json",
        {
            "measurement_schema": "et.measurement.v1",
            "controllers": results,
            "validations": validations,
        },
    )

    # 判定：全部决定性事实已经记录后再执行强断言。
    assert instances
    assert len(instances) == len(dma_instance_ids)
    assert validations
    assert all(bool(item["channel_count_valid"]) for item in validations), validations
    assert all(bool(item["max_transfer_valid"]) for item in validations), validations
    assert all(bool(item["m2m_supported"]) for item in validations), validations
    assert all(bool(item["component_id_valid"]) for item in validations), validations
    assert all(bool(item["channel_param_count_match"]) for item in validations), validations
    assert all(bool(item["channel_params_nonzero"]) for item in validations), validations
    assert all(bool(item["max_block_matches"]) for item in validations), validations


# =============================================================================
# 控制器与通道基础生命周期
# =============================================================================


# 测试 Feature：
# DMA Controller/Channel 空闲分配、基础生命周期和重新使能后的 M2M 恢复。
#
# 测试方法：
# 1. 读取 Free Channel 与初始 FREE/FIFO_EMPTY，完成第一轮 8 Byte M2M。
# 2. Stop/Deconfigure/Disable 后重新 Enable，用不同 Payload 完成第二轮 M2M。
# 3. 记录第二轮数据、FREE/FIFO_EMPTY 和再次可分配事实后执行最终断言。
#
# 通过条件：
# 1. 初始 Free Channel 合法且目标 Channel FREE/FIFO_EMPTY 均为真。
# 2. 两轮不同 Payload 的目标数据均正确。
# 3. 第二轮结束后 Channel FREE/FIFO_EMPTY，并可再次取得合法 Free Channel。
def test_dma_p0_002_module_channel_lifecycle(
    dma_support_for: DmaSupportFactory,
    target_capabilities: ChipCapabilities,
    et_artifact_dir: Path,
    instance_id: int,
    channel: int,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：解析 Controller/Channel 能力并生成两组不同 Payload。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.DMA, instance=instance_id)
    resource_driver.reset()

    support = dma_support_for(instance_id)
    resource = support.resource
    dma = support.dma
    first_payload = bytes((instance_id * 61 + channel * 17 + index) & 0xFF for index in range(8))
    second_payload = bytes((value ^ 0x5A) for value in first_payload)
    require_dma_m2m_capability(
        target_capabilities,
        instance_id=instance_id,
        channel=channel,
        transfer_count=len(first_payload),
    )
    dynamic = dma.capabilities_get()

    resource_pool_owned = False
    controller_enabled = False
    channel_configured = False

    def cleanup_actions() -> tuple[CleanupAction, ...]:
        actions: list[CleanupAction] = []
        if channel_configured:
            actions.append(("DMA channel stop", lambda: dma.stop(channel)))
            actions.append(("DMA channel deconfigure", lambda: dma.deconfigure(channel)))
        if controller_enabled:
            actions.append(("DMA controller disable", dma.controller_disable))
        if resource_pool_owned:
            actions.append(("Resource pool reset", resource.reset))
        return tuple(actions)

    with case_cleanup_scope(cleanup_actions):
        # 初始观测：在任何 Feature Mutation 前读取可分配 Channel 与状态。
        resource.reset()
        resource_pool_owned = True
        initial_free_channel = dma.find_free_channel()
        initial_status = dma.channel_status(channel)
        record_property("initial_free_channel", initial_free_channel)
        record_observation(
            record_property,
            key="initial_free",
            value=initial_status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FREE",
        )
        record_observation(
            record_property,
            key="initial_fifo_empty",
            value=initial_status.fifo_empty,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FIFO_EMPTY",
        )

        # 第一轮：使用独立源/目标 Buffer 完成最小 M2M。
        first_source = resource.create(len(first_payload), alignment=4)
        first_destination = resource.create(len(first_payload), alignment=4)
        resource.write(first_source, first_payload)
        resource.fill(first_destination, 0xA5)
        dma.controller_enable()
        controller_enabled = True
        dma.configure(
            DmaConfig(
                channel=channel,
                source_address=first_source.address,
                destination_address=first_destination.address,
                transfer_count=len(first_payload),
            )
        )
        channel_configured = True
        dma.start(channel)
        dma.wait_channel_free(channel)
        first_actual = resource.read(first_destination)
        first_status = dma.channel_status(channel)
        record_property("first_data_match", first_actual == first_payload)

        # 重新进入：显式结束第一轮 Controller/Channel 生命周期。
        dma.stop(channel)
        dma.deconfigure(channel)
        channel_configured = False
        dma.controller_disable()
        controller_enabled = False
        resource.reset()

        # 第二轮：重新 Enable/Configure，使用不同 Payload 排除旧数据残留。
        second_source = resource.create(len(second_payload), alignment=4)
        second_destination = resource.create(len(second_payload), alignment=4)
        resource.write(second_source, second_payload)
        resource.fill(second_destination, 0xA5)
        dma.controller_enable()
        controller_enabled = True
        dma.configure(
            DmaConfig(
                channel=channel,
                source_address=second_source.address,
                destination_address=second_destination.address,
                transfer_count=len(second_payload),
            )
        )
        channel_configured = True
        dma.start(channel)
        dma.wait_channel_free(channel)
        second_actual = resource.read(second_destination)
        final_status = dma.channel_status(channel)
        final_free_channel = dma.find_free_channel()

        second_data_match = second_actual == second_payload
        record_observation(
            record_property,
            key="second_actual_data",
            value=second_actual,
            source="dut",
            endpoint="DMA_DESTINATION_DATA",
        )
        record_property("second_data_match", second_data_match)
        record_observation(
            record_property,
            key="final_free",
            value=final_status.is_free,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FREE",
        )
        record_observation(
            record_property,
            key="final_fifo_empty",
            value=final_status.fifo_empty,
            source="dut",
            endpoint="DMA_CHANNEL_STATUS.FIFO_EMPTY",
        )
        record_property("final_free_channel", final_free_channel)

        # Artifact：单次发布两轮完整生命周期事实。
        write_json_result(
            et_artifact_dir / f"dma_p0_002_dma{instance_id}_channel{channel}.json",
            {
                "measurement_schema": "et.measurement.v1",
                "controller": instance_id,
                "channel": channel,
                "initial_free_channel": initial_free_channel,
                "initial_free": initial_status.is_free,
                "initial_fifo_empty": initial_status.fifo_empty,
                "first_data_match": first_actual == first_payload,
                "first_free": first_status.is_free,
                "first_fifo_empty": first_status.fifo_empty,
                "second_data_match": second_data_match,
                "final_free": final_status.is_free,
                "final_fifo_empty": final_status.fifo_empty,
                "final_free_channel": final_free_channel,
            },
        )

        # 判定：所有决定性 Evidence 已进入 Canonical Result。
        assert 0 <= initial_free_channel < dynamic.channel_count
        assert initial_status.is_free
        assert initial_status.fifo_empty
        assert first_actual == first_payload
        assert first_status.is_free
        assert first_status.fifo_empty
        assert second_data_match
        assert final_status.is_free
        assert final_status.fifo_empty
        assert 0 <= final_free_channel < dynamic.channel_count
