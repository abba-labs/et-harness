# WDG P2 Formal Case。
#
# 职责：验证需要 CRG 时基和 CPU/NMI Owner 共同提供证据的 WDG Feature。
# 边界：Case 只编排 WDG、CRG 和 CPU Driver；不访问寄存器、J-Link、串口或仪器。
# 依赖：WDG/CRG/CPU Driver、Runtime Capability、公共证据工具和 pytest。

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from statistics import median

import pytest

from ...drivers.crg import CrgDriver, CrgPeripheral, CrgWdgClockSource
from ...drivers.wdg import WdgConfig, WdgFeature, WdgIrqEvent, WdgRecord
from ...results.recorder import write_json_result
from ...scheduling.run_context import record_observation
from ._support import CpuNmiSupportFactory, WdgSupportFactory, require_wdg_runtime_feature

pytestmark = [pytest.mark.hardware, pytest.mark.ip("wdg")]

WDG_CLOCK_SAMPLE_INTERVAL_S = 0.05
WDG_CLOCK_SAMPLE_DIVIDERS = (0, 1, 1, 0, 0, 1, 1, 0)
WDG_CLOCK_RELOAD_COUNT = 5_000_000
# Divider 0/1 的公共语义是 /1 与 /2；保留 25% 误差余量后，实测速率比仍必须达到 1.5。
WDG_CLOCK_MIN_RATE_RATIO = 1.5
WDG_NMI_TIMEOUT_S = 2.0
NMI_ALL_SOURCES_UNMASKED = 0


# 测试 Feature：
# CRG对WDG时钟源和APB1分频的选择，以及选择变化对WDG Counter速率的影响。
#
# 测试方法：
# 1. 通过CRG Driver读回原始时钟配置，按交错顺序切换APB1 divider=0/1。
# 2. 每个Divider使用相同Reload和PC时间窗口采样四轮Counter速率，以中位数抑制串口调度抖动。
# 3. 保存每轮CRG读回和Counter原始样本，最后恢复进入Case前的时钟源设置。
#
# 通过条件：
# 1. 每轮CRG读回均与本轮APB1 Divider配置一致，说明源与分频字段确实到达硬件。
# 2. 所有Counter样本均真实递减，divider=0与divider=1的中位速率比不低于1.5。
# 3. Case结束后WDG被关闭，且CRG时钟配置恢复到原始选择。
def test_wdg_p2_001_clock_source_divider_and_counter_rate(
    wdg_support_for: WdgSupportFactory,
    wdg_instance_id: int,
    crg_driver: CrgDriver,
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    resource_driver,
) -> None:

    # 准备：构造当前代表WDG实例的单IP Driver和负责时基的CRG Owner Driver。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.WDG, instance=wdg_instance_id)
    resource_driver.reset()

    support = wdg_support_for(wdg_instance_id)
    require_wdg_runtime_feature(support.runtime, WdgFeature.ENABLE)
    crg = crg_driver
    original_clock = crg.wdg_clock_get(wdg_instance_id)
    event = WdgIrqEvent.TIMEOUT
    samples_by_divider: dict[int, list[dict[str, int | float | str]]] = {0: [], 1: []}

    try:
        # 基线清理：关闭WDG并清除可能影响本轮计数观测的历史超时状态。
        support.wdg.unlock()
        support.wdg.disable()
        support.wdg.irq_disable(event)
        support.wdg.irq_clear(event)

        # 交错采样：相邻轮次反转Divider顺序，避免温漂或串口负载单向偏置某一配置。
        for sample_index, divider in enumerate(WDG_CLOCK_SAMPLE_DIVIDERS):
            support.wdg.disable()
            crg.wdg_clock_set(
                wdg_instance_id,
                source=CrgWdgClockSource.APB1,
                divider=divider,
            )
            clock_readback = crg.wdg_clock_get(wdg_instance_id)
            support.wdg.configure(WdgConfig(reload_count=WDG_CLOCK_RELOAD_COUNT))
            support.wdg.enable()

            # 单轮观测：使用独立PC单调时钟和两个真实COUNTER.CURRENT样本计算速率。
            counter_before = support.wdg.status_get().counter
            sample_started = time.monotonic()
            time.sleep(WDG_CLOCK_SAMPLE_INTERVAL_S)
            counter_after = support.wdg.status_get().counter
            elapsed = time.monotonic() - sample_started
            counter_delta = counter_before - counter_after
            counter_rate = counter_delta / elapsed if elapsed > 0.0 else 0.0
            support.wdg.disable()

            samples_by_divider[divider].append(
                {
                    "sample_index": sample_index,
                    "source": clock_readback.source.name,
                    "divider": clock_readback.divider,
                    "before": counter_before,
                    "after": counter_after,
                    "delta": counter_delta,
                    "elapsed_s": elapsed,
                    "rate": counter_rate,
                }
            )

        divider_zero_samples = samples_by_divider[0]
        divider_one_samples = samples_by_divider[1]
        rate_divider_zero = median(float(item["rate"]) for item in divider_zero_samples)
        rate_divider_one = median(float(item["rate"]) for item in divider_one_samples)
        rate_ratio = rate_divider_zero / rate_divider_one if rate_divider_one > 0.0 else 0.0

        # 证据：在断言前保存每轮CRG读回、Counter两点值和独立PC时间窗口。
        record_observation(
            record_property,
            key="crg_clock_source_samples",
            value=[item["source"] for item in divider_zero_samples + divider_one_samples],
            source="dut",
            endpoint="CRG.WDG_CLOCK_SOURCE",
        )
        record_observation(
            record_property,
            key="crg_clock_divider_samples",
            value=[item["divider"] for item in divider_zero_samples + divider_one_samples],
            source="dut",
            endpoint="CRG.WDG_CLOCK_DIVIDER",
        )
        record_observation(
            record_property,
            key="counter_samples_divider_zero",
            value=[
                {"before": item["before"], "after": item["after"]} for item in divider_zero_samples
            ],
            source="dut",
            endpoint="COUNTER.CURRENT",
        )
        record_observation(
            record_property,
            key="counter_samples_divider_one",
            value=[
                {"before": item["before"], "after": item["after"]} for item in divider_one_samples
            ],
            source="dut",
            endpoint="COUNTER.CURRENT",
        )
        record_property("counter_rate_divider_zero", rate_divider_zero)
        record_property("counter_rate_divider_one", rate_divider_one)
        record_property("counter_rate_ratio", rate_ratio)
        record_property("counter_rate_min_ratio", WDG_CLOCK_MIN_RATE_RATIO)
        record_property(
            "counter_elapsed_divider_zero_s",
            [item["elapsed_s"] for item in divider_zero_samples],
        )
        record_property(
            "counter_elapsed_divider_one_s",
            [item["elapsed_s"] for item in divider_one_samples],
        )
        record_property(
            "expected_clock_behavior",
            {
                "source": "APB1",
                "divider_zero_faster_than_divider_one": True,
                "minimum_rate_ratio": WDG_CLOCK_MIN_RATE_RATIO,
            },
        )
        write_json_result(
            et_artifact_dir / "wdg_p2_001_clock_source_divider_and_counter_rate.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "wdg_p2_001",
                "clock": {
                    "divider_zero": {
                        "source": divider_zero_samples[0]["source"],
                        "divider": divider_zero_samples[0]["divider"],
                    },
                    "divider_one": {
                        "source": divider_one_samples[0]["source"],
                        "divider": divider_one_samples[0]["divider"],
                    },
                    "original": {
                        "source": original_clock.source.name,
                        "divider": original_clock.divider,
                    },
                },
                "counter_rate": {
                    "divider_zero": rate_divider_zero,
                    "divider_one": rate_divider_one,
                    "ratio": rate_ratio,
                    "minimum_ratio": WDG_CLOCK_MIN_RATE_RATIO,
                },
                "samples": {
                    "divider_zero": divider_zero_samples,
                    "divider_one": divider_one_samples,
                },
            },
        )

        # 断言：每轮硬件读回和Counter变化都有效，中位速率比必须证明实际分频效果。
        assert all(item["source"] == CrgWdgClockSource.APB1.name for item in divider_zero_samples)
        assert all(item["source"] == CrgWdgClockSource.APB1.name for item in divider_one_samples)
        assert all(item["divider"] == 0 for item in divider_zero_samples)
        assert all(item["divider"] == 1 for item in divider_one_samples)
        assert all(int(item["delta"]) > 0 for item in divider_zero_samples)
        assert all(int(item["delta"]) > 0 for item in divider_one_samples)
        assert rate_ratio >= WDG_CLOCK_MIN_RATE_RATIO
    finally:
        # 清理：先关闭WDG，再清除本轮IRQ，最后恢复原CRG时钟选择。
        support.wdg.disable()
        support.wdg.irq_disable(event)
        support.wdg.irq_clear(event)
        support.wdg.record_clear(WdgRecord.INTERRUPT)
        crg.wdg_clock_set(
            wdg_instance_id,
            source=original_clock.source,
            divider=original_clock.divider
            if original_clock.source == CrgWdgClockSource.APB1
            else 0,
        )


# 测试 Feature：
# WDG自然超时到CPU NMI路由，以及CPU Owner独立ISR事件计数。
#
# 测试方法：
# 1. 通过CPU Owner读取NMI源能力，配置mask=0并清零CPU ISR事件计数。
# 2. 通过WDG配置不复位模式并使能真实timeout IRQ，让WDG自然到期；WDG Service负责清理自己的源。
# 3. 分别读取CPU NMI与WDG IRQ事实，并确认CPU Owner在首次NMI后自动屏蔽全部已发布Source。
#
# 通过条件：
# 1. CPU NMI事件计数相对基线增加，证明NMI向量确实执行过。
# 2. WDG timeout IRQ事件也有真实交付，且两者均来自本轮自然超时。
# 3. CPU首次交付后Mask等于Runtime发布的Source全集，协议线程仍能读取WDG IRQ结果。
def test_wdg_p2_002_natural_timeout_to_cpu_nmi(
    wdg_support_for: WdgSupportFactory,
    wdg_instance_id: int,
    cpu_nmi_support_for: CpuNmiSupportFactory,
    cpu_nmi_instance_ids: tuple[int, ...],
    et_artifact_dir: Path,
    record_property: Callable[[str, object], None],
    crg_driver,
    resource_driver,
) -> None:

    # 准备：组合一个代表WDG和当前CPU Owner实例，保持跨IP顺序留在Case主体。
    # 隔离：本 Case 配置前复位参与 IP 和 Resource Pool，避免前序 Case 状态污染。
    crg_driver.reset(CrgPeripheral.WDG, instance=wdg_instance_id)
    resource_driver.reset()

    support = wdg_support_for(wdg_instance_id)
    if not cpu_nmi_instance_ids:
        pytest.skip("skip_by_chip_capability: no CPU instance is declared")
    cpu_support = cpu_nmi_support_for(cpu_nmi_instance_ids[0])
    if not cpu_support.available or cpu_support.runtime is None:
        pytest.skip("skip_by_runtime_service: CPU NMI Owner service is not available")
    require_wdg_runtime_feature(support.runtime, WdgFeature.INTERRUPTS)
    event = WdgIrqEvent.TIMEOUT

    try:
        # 基线：清除WDG历史事件和CPU软件ISR计数，再开放CPU全部NMI源。
        support.wdg.unlock()
        support.wdg.disable()
        support.wdg.irq_disable(event)
        support.wdg.irq_clear(event)
        support.wdg.record_clear(WdgRecord.INTERRUPT)
        cpu_support.cpu.nmi_configure(NMI_ALL_SOURCES_UNMASKED)
        cpu_support.cpu.nmi_event_clear()
        cpu_before = cpu_support.cpu.nmi_snapshot_get()
        wdg_before = support.wdg.irq_snapshot_get()

        # 激励：启动无系统复位的短Reload，让硬件自然产生WDG timeout而非软件Force。
        support.wdg.configure(WdgConfig(reload_count=WDG_CLOCK_RELOAD_COUNT))
        support.wdg.irq_unmask(event)
        support.wdg.irq_enable(event)
        support.wdg.enable()

        # 观测：分别等待CPU NMI ISR和WDG IRQ ISR，保留两条真实事件计数。
        cpu_after = cpu_support.cpu.wait_nmi(
            cpu_before.event_count + 1,
            timeout_s=WDG_NMI_TIMEOUT_S,
        )
        wdg_after = support.wdg.wait_irq(
            minimum_event_count=wdg_before.event_count + 1,
            timeout_s=WDG_NMI_TIMEOUT_S,
        )

        # 证据：分别记录CPU硬件端点，避免把Raw、Masked、Mask和Status伪装成一个端点。
        record_observation(
            record_property,
            key="cpu_nmi_source_raw",
            value=cpu_after.source_raw,
            source="dut",
            endpoint="NMI_ROUTE.SOURCE_RAW",
        )
        record_observation(
            record_property,
            key="cpu_nmi_source_masked",
            value=cpu_after.source_masked,
            source="dut",
            endpoint="NMI_ROUTE.SOURCE_MASKED",
        )
        record_observation(
            record_property,
            key="cpu_nmi_mask",
            value=cpu_after.nmi_mask,
            source="dut",
            endpoint="NMI_ROUTE.MASK",
        )
        record_observation(
            record_property,
            key="cpu_nmi_status",
            value=cpu_after.nmi_status,
            source="dut",
            endpoint="NMI_ROUTE.STATUS",
        )
        record_observation(
            record_property,
            key="wdg_irq_raw",
            value=int(wdg_after.last_raw),
            source="dut",
            endpoint="IRQ_RAW.TIMEOUT",
        )
        record_property(
            "cpu_nmi_event_count",
            {"before": cpu_before.event_count, "after": cpu_after.event_count},
        )
        record_property(
            "wdg_irq_event_count",
            {"before": wdg_before.event_count, "after": wdg_after.event_count},
        )
        record_property(
            "expected_nmi_chain",
            {
                "natural_wdg_timeout": True,
                "cpu_nmi_event_delta_at_least": 1,
                "automatic_mask": cpu_support.runtime.source_mask,
            },
        )
        write_json_result(
            et_artifact_dir / "wdg_p2_002_natural_timeout_to_cpu_nmi.json",
            {
                "measurement_schema": "et.measurement.v1",
                "case_id": "wdg_p2_002",
                "cpu": {
                    "instance": cpu_support.instance_name,
                    "event_count_before": cpu_before.event_count,
                    "event_count_after": cpu_after.event_count,
                    "source_raw_after": cpu_after.source_raw,
                    "source_masked_after": cpu_after.source_masked,
                    "nmi_mask_after": cpu_after.nmi_mask,
                    "nmi_status_after": cpu_after.nmi_status,
                },
                "wdg": {
                    "event_count_before": wdg_before.event_count,
                    "event_count_after": wdg_after.event_count,
                    "last_raw_after": int(wdg_after.last_raw),
                },
            },
        )

        # 断言：双端事件均真实发生，CPU Owner自动屏蔽后协议线程仍完成WDG观测。
        assert cpu_after.event_count > cpu_before.event_count
        assert cpu_after.nmi_mask == cpu_support.runtime.source_mask
        assert wdg_after.event_count > wdg_before.event_count
        assert wdg_after.last_raw & event == event
    finally:
        # 清理：先停止WDG源，再清除IRQ/记录，最后恢复CPU NMI全屏蔽状态。
        support.wdg.disable()
        support.wdg.irq_disable(event)
        support.wdg.irq_clear(event)
        support.wdg.record_clear(WdgRecord.INTERRUPT)
        cpu_support.cpu.nmi_configure(cpu_support.runtime.source_mask)
