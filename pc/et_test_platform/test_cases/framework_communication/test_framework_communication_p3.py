# Formal Case测试模块。
#
# 职责：按测试等级承载可执行Feature流程、证据和最终断言。
# 边界：不直接调用Codec、Transport或芯片专有接口。
# 依赖：仅依赖Fixture、公共Driver及Case本地Support。

from __future__ import annotations

import time
from pathlib import Path

import pytest

from ...drivers.framework import FrameworkDriver
from ...results.communication import (
    FrameworkCommunicationStressResult,
    LatencySummary,
    PayloadClassSummary,
)
from ...results.recorder import write_json_result
from .stress_case import FORMAL_STRESS_PLAN, payload_for_round, percentile


# 测试 Feature：
# Framework ECHO 在小、中、大载荷下的长时间稳定性、数据完整性与重试可观测性。
#
# 测试方法：
# 1. 按计划执行 20 轮，每轮依次发送 16、256、2048 Byte 的确定性 Payload。
# 2. 每笔请求逐字节核对响应，并统计各载荷的延迟、重试次数和往返字节数。
#
# 通过条件：
# 1. 每笔 ECHO Response 与 Request 完全一致，所有计划事务均执行完成。
# 2. 实际事务数和往返字节数等于由 FORMAL_STRESS_PLAN 唯一推导的期望值。
@pytest.mark.hardware
@pytest.mark.ip("framework_communication")
@pytest.mark.framework_communication
def test_framework_communication_p3_001_echo_mixed_payload_stress(
    framework_communication: FrameworkDriver,
    et_artifact_dir: Path,
    record_property,
) -> None:

    # 准备：按唯一计划创建分载荷统计容器，并由计划推导总事务数和往返字节数。
    latencies: dict[str, list[float]] = {
        item.name: [] for item in FORMAL_STRESS_PLAN.payload_classes
    }
    retries: dict[str, int] = {item.name: 0 for item in FORMAL_STRESS_PLAN.payload_classes}
    bytes_per_class: dict[str, int] = {item.name: 0 for item in FORMAL_STRESS_PLAN.payload_classes}
    expected_transactions = FORMAL_STRESS_PLAN.rounds * len(FORMAL_STRESS_PLAN.payload_classes)
    expected_total_bytes = FORMAL_STRESS_PLAN.rounds * sum(
        payload_class.size * 2 for payload_class in FORMAL_STRESS_PLAN.payload_classes
    )
    started = time.monotonic()

    # 执行：遍历全部轮次和载荷类别；每笔请求立即核对响应并累计真实测量值。
    for round_index in range(FORMAL_STRESS_PLAN.rounds):
        # 子项：每轮依次覆盖小、中、大三类Payload并独立核对响应。
        for class_index, payload_class in enumerate(FORMAL_STRESS_PLAN.payload_classes):
            request = payload_for_round(
                round_index,
                class_index,
                payload_class.size,
            )
            exchange = framework_communication.echo(request)
            assert exchange.response == request
            latencies[payload_class.name].append(exchange.latency_ms)
            retries[payload_class.name] += exchange.retry_count
            bytes_per_class[payload_class.name] += len(request) * 2
        if (round_index + 1) % 10 == 0:
            print(f"framework communication progress={round_index + 1}/{FORMAL_STRESS_PLAN.rounds}")

    # 汇总：按载荷类别生成延迟、事务数和重试统计，确保每类完成全部计划轮次。
    elapsed = time.monotonic() - started
    summaries: list[PayloadClassSummary] = []

    # 汇总：逐载荷类别计算延迟分位数、事务数和重试次数。
    for payload_class in FORMAL_STRESS_PLAN.payload_classes:
        values = latencies[payload_class.name]
        assert len(values) == FORMAL_STRESS_PLAN.rounds
        summaries.append(
            PayloadClassSummary(
                name=payload_class.name,
                payload_size=payload_class.size,
                transactions=len(values),
                retry_count=retries[payload_class.name],
                latency=LatencySummary(
                    minimum_ms=round(min(values), 3),
                    p50_ms=round(percentile(values, 0.50), 3),
                    p95_ms=round(percentile(values, 0.95), 3),
                    maximum_ms=round(max(values), 3),
                ),
            )
        )

    transactions = sum(len(values) for values in latencies.values())
    total_bytes = sum(bytes_per_class.values())
    assert transactions == expected_transactions
    assert total_bytes == expected_total_bytes

    # 记录：保存本次真实测量结果；Fixture 负责关闭通信会话与 Transport。
    result = FrameworkCommunicationStressResult(
        transport=framework_communication.transport_identity,
        chip_id=framework_communication.chip_id,
        firmware_build_id=framework_communication.firmware_build_id,
        rounds=FORMAL_STRESS_PLAN.rounds,
        transactions=transactions,
        elapsed_seconds=round(elapsed, 3),
        payload_bytes_round_trip=total_bytes,
        payload_throughput_bytes_per_second=(
            round(total_bytes / elapsed, 1) if elapsed > 0.0 else 0.0
        ),
        error_count=0,
        classes=tuple(summaries),
    )
    output = write_json_result(
        et_artifact_dir / "framework_communication_stress_20.json",
        result.to_measurements(),
    )
    record_property("framework_communication_result", str(output))
    record_property("transactions", result.transactions)
    record_property("payload_bytes_round_trip", result.payload_bytes_round_trip)
