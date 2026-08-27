# DMA P3 Formal Case。
#
# 职责：验证跨实例与多参数混合 M2M 的短时稳定性和Evidence生命周期。
# 边界：不把20轮功能压力冒充长期可靠性或当前真机HIL结论。
# 依赖：仅依赖 DMA/Resource公共Driver、纯数据Helper与Canonical Evidence接口。

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from ...core.cleanup import CleanupAction
from ...drivers.crg import CrgPeripheral
from ...drivers.dma import DmaAddressMode, DmaBurst, DmaConfig, DmaFifoMode, DmaWidth
from ...profiles.capabilities import ChipCapabilities
from ...results.recorder import write_json_result
from ...scheduling.run_context import record_observation
from ..case_cleanup import case_cleanup_scope
from ._support import DmaSupportFactory, require_dma_m2m_capability
from .dma_helpers import (
    DMA_DESTINATION_FILL,
    DMA_GUARD_SIZE,
    DMA_GUARD_VALUE,
    build_dma_m2m_vector,
    dma_m2m_measurement,
)

pytestmark = [pytest.mark.hardware, pytest.mark.ip("dma")]


# 测试 Feature：
# 同一软件 Session 内20轮跨可用DMA Instance/Channel/Count/Width/Burst/FIFO混合M2M稳定性。
#
# 测试方法：
# 1. 20轮确定性轮换Controller、Channel、Count、Width、Burst和FIFO Mode。
# 2. 每轮独立准备带Guard Buffer，Start/Wait后先记录实际数据/Guard/FREE，再执行断言。
# 3. 每轮完成后单调增加completed_rounds；最终只发布一次完整Artifact。
#
# 通过条件：
# 1. 20/20轮都形成决定性Evidence。
# 2. 每轮Destination正确、Source与Guard不变。
# 3. 每轮Channel Free且Cleanup成功；中途失败时前序Canonical Evidence不丢失。
def test_dma_p3_007_long_run_mixed_transfer(
    dma_support_for: DmaSupportFactory,
    target_capabilities: ChipCapabilities,
    dma_instance_ids: tuple[int, ...],
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    for reset_instance_id in dma_instance_ids:
        crg_driver.reset(CrgPeripheral.DMA, instance=reset_instance_id)
    resource_driver.reset()

    supports = {instance_id: dma_support_for(instance_id) for instance_id in dma_instance_ids}
    runtime_capabilities = {
        instance_id: support.dma.capabilities_get() for instance_id, support in supports.items()
    }
    results: list[dict[str, object]] = []
    planned_rounds = 20
    record_property("planned_rounds", planned_rounds)

    # 遍历本Case声明的参数或资源集合，逐项形成可追溯硬件证据。
    for index in range(planned_rounds):
        instance_id = dma_instance_ids[index % len(dma_instance_ids)]
        dynamic = runtime_capabilities[instance_id]
        channel = index % dynamic.channel_count
        transfer_count = min((1, 7, 32, 63, 128, 257)[index % 6], dynamic.max_transfer_count)
        width = DmaWidth(index % len(DmaWidth))
        source_burst = DmaBurst(index % 4)
        destination_burst = DmaBurst((index + 1) % 4)
        fifo_mode = DmaFifoMode(index & 1)
        support = supports[instance_id]
        resource = support.resource
        dma = support.dma
        vector = build_dma_m2m_vector(
            transfer_count,
            width,
            DmaAddressMode.INCREMENT,
            DmaAddressMode.INCREMENT,
        )
        require_dma_m2m_capability(
            target_capabilities,
            instance_id=instance_id,
            channel=channel,
            transfer_count=transfer_count,
        )

        cleanup_state = {"controller_enabled": False, "channel_configured": False}

        def cleanup_actions(
            *,
            state: dict[str, bool] = cleanup_state,
            dma_driver=dma,
            owned_channel: int = channel,
            resource_driver=resource,
        ) -> tuple[CleanupAction, ...]:
            actions: list[CleanupAction] = []
            if state["channel_configured"]:
                actions.append(("DMA channel stop", lambda: dma_driver.stop(owned_channel)))
                actions.append(
                    ("DMA channel deconfigure", lambda: dma_driver.deconfigure(owned_channel))
                )
            if state["controller_enabled"]:
                actions.append(("DMA controller disable", dma_driver.controller_disable))
            actions.append(("Resource pool reset", resource_driver.reset))
            return tuple(actions)

        with case_cleanup_scope(cleanup_actions):
            resource.reset()
            allocation_size = len(vector.source_data) + 2 * DMA_GUARD_SIZE
            source = resource.create(allocation_size, alignment=4)
            destination = resource.create(allocation_size, alignment=4)
            resource.fill(source, DMA_GUARD_VALUE)
            resource.fill(destination, DMA_GUARD_VALUE)
            resource.write(source, vector.source_data, offset=DMA_GUARD_SIZE)
            resource.fill(
                destination,
                DMA_DESTINATION_FILL,
                size=len(vector.expected_destination),
                offset=DMA_GUARD_SIZE,
            )
            dma.controller_enable()
            cleanup_state["controller_enabled"] = True
            dma.configure(
                DmaConfig(
                    channel=channel,
                    source_address=source.address + DMA_GUARD_SIZE,
                    destination_address=destination.address + DMA_GUARD_SIZE,
                    transfer_count=transfer_count,
                    source_width=width,
                    destination_width=width,
                    source_burst=source_burst,
                    destination_burst=destination_burst,
                    fifo_mode=fifo_mode,
                )
            )
            cleanup_state["channel_configured"] = True
            dma.start(channel)
            dma.wait_channel_free(channel)
            source_raw = resource.read(source)
            destination_raw = resource.read(destination)
            guard = bytes([DMA_GUARD_VALUE]) * DMA_GUARD_SIZE
            actual = destination_raw[DMA_GUARD_SIZE:-DMA_GUARD_SIZE]
            status = dma.channel_status(channel)

            source_intact = (
                source_raw[:DMA_GUARD_SIZE] == guard
                and source_raw[DMA_GUARD_SIZE:-DMA_GUARD_SIZE] == vector.source_data
                and source_raw[-DMA_GUARD_SIZE:] == guard
            )
            destination_guards_intact = (
                destination_raw[:DMA_GUARD_SIZE] == guard
                and destination_raw[-DMA_GUARD_SIZE:] == guard
            )
            data_match = actual == vector.expected_destination

            # Evidence：每轮决定性事实在Assert前进入Canonical Result。
            record_property("round_index", index)
            record_property("round_data_match", data_match)
            record_property("round_source_intact", source_intact)
            record_property("round_destination_guards_intact", destination_guards_intact)
            record_observation(
                record_property,
                key="round_actual_data",
                value=actual,
                source="dut",
                endpoint="DMA_DESTINATION_DATA",
            )
            record_observation(
                record_property,
                key="round_channel_free",
                value=status.is_free,
                source="dut",
                endpoint="DMA_CHANNEL_STATUS.FREE",
            )

            result = dma_m2m_measurement(
                instance_id=instance_id,
                channel=channel,
                transfer_count=transfer_count,
                width=width,
                source_mode=DmaAddressMode.INCREMENT,
                destination_mode=DmaAddressMode.INCREMENT,
                source_burst=source_burst,
                destination_burst=destination_burst,
                fifo_mode=fifo_mode,
                vector=vector,
                actual=actual,
            )
            result.update(
                {
                    "round_index": index,
                    "source_intact": source_intact,
                    "destination_guards_intact": destination_guards_intact,
                    "channel_free": status.is_free,
                }
            )
            results.append(result)
            record_property("completed_rounds", len(results))

            assert dynamic.channel_count > 0
            assert dynamic.max_transfer_count > 0
            assert source_intact
            assert destination_guards_intact
            assert data_match
            assert status.is_free

    all_data_match = all(bool(item["data_match"]) for item in results)
    all_channels_free = all(bool(item["channel_free"]) for item in results)
    record_property("all_data_match", all_data_match)
    record_property("all_channels_free", all_channels_free)
    record_property("last_data_match", bool(results[-1]["data_match"]))
    record_property("last_channel_free", bool(results[-1]["channel_free"]))

    # Artifact：只发布一次最终完整Snapshot。
    write_json_result(
        et_artifact_dir / "dma_p3_007_long_run_mixed_transfer.json",
        {
            "measurement_schema": "et.measurement.v1",
            "planned_rounds": planned_rounds,
            "completed_rounds": len(results),
            "all_data_match": all_data_match,
            "all_channels_free": all_channels_free,
            "subcases": results,
        },
    )

    assert len(results) == planned_rounds
    assert all_data_match
    assert all_channels_free
