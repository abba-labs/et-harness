# Framework Validation测试模块。
#
# 职责：验证test_framework_communication_measurements 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

from et_test_platform.results.communication import (
    FrameworkCommunicationStressResult,
    LatencySummary,
    PayloadClassSummary,
)


def test_framework_measurement_attachment_has_no_case_conclusion() -> None:
    result = FrameworkCommunicationStressResult(
        transport="fake",
        chip_id="et6801",
        firmware_build_id="fw-test",
        rounds=1,
        transactions=1,
        elapsed_seconds=0.1,
        payload_bytes_round_trip=32,
        payload_throughput_bytes_per_second=320.0,
        error_count=0,
        classes=(
            PayloadClassSummary(
                name="small",
                payload_size=16,
                transactions=1,
                retry_count=0,
                latency=LatencySummary(0.1, 0.1, 0.1, 0.1),
            ),
        ),
    )

    measurements = result.to_measurements()

    assert "status" not in measurements
    assert "failure_reason" not in measurements
    assert measurements["measurement_schema"] == "et.measurement.v1"
    assert measurements["transactions"] == 1
    assert measurements["error_count"] == 0
