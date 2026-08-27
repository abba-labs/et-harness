# Framework Validation测试模块。
#
# 职责：验证test_case_cleanup 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import pytest

from et_test_platform.core.cleanup import OperationCleanupError
from et_test_platform.test_cases.case_cleanup import case_cleanup_scope


def test_case_cleanup_runs_all_actions_after_body_failure() -> None:
    calls: list[str] = []

    def fail_cleanup() -> None:
        calls.append("first")
        raise RuntimeError("cleanup failed")

    def finish_cleanup() -> None:
        calls.append("second")

    with (
        pytest.raises(OperationCleanupError) as exc_info,
        case_cleanup_scope(
            lambda: (
                ("first cleanup", fail_cleanup),
                ("second cleanup", finish_cleanup),
            )
        ),
    ):
        raise ValueError("body failed")

    assert calls == ["first", "second"]
    assert isinstance(exc_info.value.primary_error, ValueError)
    assert [item.stage for item in exc_info.value.cleanup_failures] == ["first cleanup"]


def test_case_cleanup_failure_turns_success_into_failure() -> None:
    def fail_cleanup() -> None:
        raise RuntimeError("bad")

    with (
        pytest.raises(OperationCleanupError) as exc_info,
        case_cleanup_scope(lambda: (("cleanup", fail_cleanup),)),
    ):
        pass

    assert "Case body completed" in str(exc_info.value.primary_error)
