# Framework Validation测试模块。
#
# 职责：验证test_cleanup 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import pytest

from et_test_platform.core.cleanup import (
    OperationCleanupError,
    raise_with_cleanup,
    run_cleanup,
)


def test_cleanup_runs_all_actions_and_preserves_ordered_failures() -> None:
    calls: list[str] = []
    first = RuntimeError("stop failed")
    second = ValueError("deconfigure failed")

    def fail_stop() -> None:
        calls.append("stop")
        raise first

    def succeed_cancel() -> None:
        calls.append("cancel")

    def fail_deconfigure() -> None:
        calls.append("deconfigure")
        raise second

    failures = run_cleanup(
        (
            ("stop", fail_stop),
            ("cancel", succeed_cancel),
            ("deconfigure", fail_deconfigure),
        )
    )

    assert calls == ["stop", "cancel", "deconfigure"]
    assert [failure.stage for failure in failures] == ["stop", "deconfigure"]
    assert failures[0].error is first
    assert failures[1].error is second


def test_aggregate_error_keeps_primary_and_cleanup_objects() -> None:
    primary = TimeoutError("DMA deadline expired")
    cleanup = RuntimeError("DMA stop failed")

    def fail_cleanup() -> None:
        raise cleanup

    failures = run_cleanup((("stop", fail_cleanup),))

    with pytest.raises(OperationCleanupError) as captured:
        raise_with_cleanup(primary, failures)

    assert captured.value.primary_error is primary
    assert captured.value.cleanup_failures[0].error is cleanup
    assert captured.value.__cause__ is primary


def test_primary_error_is_rethrown_when_cleanup_succeeds() -> None:
    primary = RuntimeError("primary")

    with pytest.raises(RuntimeError) as captured:
        raise_with_cleanup(primary, run_cleanup((("cleanup", lambda: None),)))

    assert captured.value is primary


def test_cleanup_records_base_exception_without_skipping_later_actions() -> None:
    calls: list[str] = []

    def stop_with_interrupt() -> None:
        calls.append("stop")
        raise KeyboardInterrupt("operator interrupt")

    def deconfigure() -> None:
        calls.append("deconfigure")

    failures = run_cleanup(
        (
            ("stop", stop_with_interrupt),
            ("deconfigure", deconfigure),
        )
    )

    assert calls == ["stop", "deconfigure"]
    assert len(failures) == 1
    assert isinstance(failures[0].error, KeyboardInterrupt)
